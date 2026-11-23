"""Temporal pooling (D-030) must never average in an issue date later than the row's own.

The trap is real: `features.sickle_m1.build` emits a field's rows lead-ascending, which is
`as_of` *descending*, so a naive expanding mean down the table reads the future.
"""

import numpy as np
import pandas as pd

from rice_fallow_radar.models import m1_lightgbm as L


def _df() -> pd.DataFrame:
    # rows in build() order: lead ascending, so as_of descending within a field
    return pd.DataFrame(
        {
            "unique_id": ["a", "a", "a", "b", "b"],
            "as_of": pd.to_datetime(
                ["2020-03-15", "2020-03-08", "2020-03-01", "2020-03-15", "2020-03-08"]
            ),
            "lead": [1, 8, 15, 1, 8],
        }
    )


def test_pooling_never_reads_a_later_issue_date():
    df = _df()
    # field a: three estimates of the same harvest date (16 Mar), so pooling is a no-op.
    # field b: the late row says 25 Mar, the early row 8 Mar. The early row must not see 25 Mar.
    pred = np.array([1.0, 8.0, 15.0, 10.0, 0.0])
    out = L.pool_predictions(df, pred)
    assert np.allclose(out.pooled.to_numpy()[:3], [1.0, 8.0, 15.0])
    assert np.allclose(out.pooled.to_numpy()[3:], [1.5, 0.0])  # 0 would be mean(8 Mar, 25 Mar)
    assert out.n_acc.tolist() == [3, 2, 1, 2, 1]
    assert (out.index == df.index).all()


def test_pooling_is_identity_on_a_single_issue_date():
    df = _df().iloc[[2]]
    out = L.pool_predictions(df, np.array([15.0]))
    assert out.pooled.iloc[0] == 15.0 and out.n_acc.iloc[0] == 1
