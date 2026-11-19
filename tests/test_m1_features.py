"""Leakage and split tests for the SICKLE M1 table (EVALUATION.md asks for these in CI).

The leakage test works by poisoning: every scene value after `as_of` is replaced with an absurd
number, and the features must come out identical. That catches an off-by-one in the `as_of`
filter in a way an eyeball over column names cannot.
"""

import numpy as np
import pandas as pd
import pytest

from rice_fallow_radar.eval import splits
from rice_fallow_radar.features import sickle_m1 as F
from rice_fallow_radar.models import m1_baselines as B

SERIES = "data/interim/sickle_s1_series.parquet"
pytestmark = pytest.mark.skipif(
    not pd.io.common.file_exists(SERIES), reason="needs scripts/sickle_extract_check.py output"
)


def _labels_and_series(n: int = 25):
    from rice_fallow_radar.ingest import sickle

    ex = splits.with_groups(sickle.exact_labels())
    s = pd.read_parquet(SERIES)
    keep = ex.UNIQUE_ID.head(n)
    return ex[ex.UNIQUE_ID.isin(keep)], s[s.unique_id.isin(keep)]


def test_features_ignore_scenes_after_as_of():
    lab, s = _labels_and_series()
    clean = F.build(lab, s)
    assert len(clean) > 0
    # no row may use a scene from the last MIN_LEAD days before its own harvest, or later
    poisoned = s.copy()
    after = poisoned.lead_days < F.MIN_LEAD
    assert after.any(), "fixture has no post-as_of scenes, so this test would prove nothing"
    poisoned.loc[after, ["vh_db", "vv_db"]] = 999.0
    out = F.build(lab, poisoned)
    cols = F.feature_columns(clean)
    pd.testing.assert_frame_equal(clean[cols], out[cols])


def test_every_row_predates_its_harvest():
    lab, s = _labels_and_series()
    f = F.build(lab, s)
    assert (f.as_of < f.harvest).all()
    assert ((f.harvest - f.as_of).dt.days == f.lead).all()
    assert f.lead.min() >= F.MIN_LEAD


def test_dev_and_test_groups_are_disjoint():
    from rice_fallow_radar.ingest import sickle

    dev, test = splits.dev_test(sickle.exact_labels())
    assert not set(dev.group) & set(test.group)
    assert not set(dev.PLOT_ID) & set(test.PLOT_ID)
    assert 0.1 < len(test) / (len(dev) + len(test)) < 0.3


def test_seasonal_mean_is_exact_when_a_season_has_one_harvest_date():
    lab, s = _labels_and_series(8)
    f = F.build(lab, s)
    one = f[f.unique_id == f.unique_id.iloc[0]].copy()
    train = one.copy()  # train and test on the same single sample
    pred = B.seasonal_mean(train, one)
    assert np.allclose(pred, one.lead.to_numpy(), atol=1e-6)


def test_bootstrap_mae_brackets_the_point_estimate():
    err = np.array([1.0, -2.0, 3.0, -4.0, 5.0, 0.0])
    g = np.array([1, 1, 2, 2, 3, 3])
    mae, lo, hi = B.bootstrap_mae(err, g, n=500, seed=1)
    assert mae == pytest.approx(2.5)
    assert lo <= mae <= hi
