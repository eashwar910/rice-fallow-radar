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
S2_SERIES = "data/interim/sickle_s2_series.parquet"
pytestmark = pytest.mark.skipif(
    not pd.io.common.file_exists(SERIES), reason="needs scripts/sickle_extract_check.py output"
)
needs_s2 = pytest.mark.skipif(
    not pd.io.common.file_exists(S2_SERIES),
    reason="needs scripts/sickle_s2_extract_check.py output",
)


def _labels_and_series(n: int = 25, with_s2: bool = False):
    from rice_fallow_radar.ingest import sickle

    ex = splits.with_groups(sickle.exact_labels())
    s = pd.read_parquet(SERIES)
    keep = ex.UNIQUE_ID.head(n)
    out = [ex[ex.UNIQUE_ID.isin(keep)], s[s.unique_id.isin(keep)]]
    if with_s2:
        s2 = pd.read_parquet(S2_SERIES)
        out.append(s2[s2.unique_id.isin(keep)])
    return tuple(out)


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


@needs_s2
def test_s2_features_ignore_scenes_after_as_of():
    lab, s, s2 = _labels_and_series(with_s2=True)
    clean = F.build(lab, s, s2=s2)
    assert clean.n_scenes_s2.gt(0).all(), "fixture rows have no clear S2 scene to leak from"
    poisoned = s2.copy()
    after = poisoned.lead_days < F.MIN_LEAD
    assert after.any(), "fixture has no post-as_of S2 scenes, so this test would prove nothing"
    poisoned.loc[after, ["ndvi", "ndwi", "mndwi"]] = -999.0
    out = F.build(lab, s, s2=poisoned)
    cols = F.feature_columns(clean)
    pd.testing.assert_frame_equal(clean[cols], out[cols])


@needs_s2
def test_s2_adds_columns_but_never_rows():
    """The feature-set ablation is only honest if both arms score the same rows."""
    lab, s, s2 = _labels_and_series(with_s2=True)
    s1_only, both = F.build(lab, s), F.build(lab, s, s2=s2)
    pd.testing.assert_frame_equal(s1_only, both[s1_only.columns])
    added = set(F.feature_columns(both)) - set(F.feature_columns(s1_only))
    assert added and all(c.startswith(F.S2_PREFIXES) for c in added), added
    # a stale optical read must be visible to the model, not silently passed off as fresh
    assert both.days_since_clear_s2.max() > 10


@needs_s2
def test_every_feature_belongs_to_exactly_one_block():
    """The point-C ablation picks columns by block, so an unclassified column would silently
    leak into the wrong arm -- an optical column into S1-only, or a sensor into calendar-only."""
    lab, s, s2 = _labels_and_series(with_s2=True)
    f = F.build(lab, s, s2=s2)
    cols = F.feature_columns(f)
    assert [c for c in cols if F.block_of(c) == "unknown"] == []
    blocks = ("base", "s1", "weather", "s2")
    assert sorted(F.block_columns(f, blocks)) == sorted(cols)
    # the blocks partition: no column appears in two of them
    assert sum(len(F.block_columns(f, (b,))) for b in blocks) == len(cols)
    assert F.block_columns(f, ("base",)) and F.block_columns(f, ("s2",))
    # the fallback branch must not be a catch-all for typos
    assert all(c.startswith(F.S1_PREFIXES) for c in F.block_columns(f, ("s1",)))


def test_folds_keep_every_issue_date_of_a_sample_together():
    lab, s = _labels_and_series()
    f = F.build(lab, s)
    fold = splits.assign_folds(f, n=3)
    assert fold.notna().all()
    assert (
        f.groupby(f.unique_id)
        .apply(lambda g: fold[g.index].nunique(), include_groups=False)
        .eq(1)
        .all()
    )
    assert f.groupby(fold).group.nunique().gt(0).all()
    # a plot's neighbour group must not straddle folds either (D-022 spatial blocking)
    assert (
        f.groupby("group")
        .apply(lambda g: fold[g.index].nunique(), include_groups=False)
        .eq(1)
        .all()
    )


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
