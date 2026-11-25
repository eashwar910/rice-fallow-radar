"""The five leakage checks of the frozen protocol (EVALUATION.md §Leakage tests), on synthetic data.

The SICKLE-backed versions in `test_m1_features.py` skip in CI because the data is never
committed, so they protect nothing on a fresh clone. These build their own tiny inputs and run
everywhere. Each check poisons what a row must not see and asserts the row does not move.

1. features at `as_of` ignore every input dated after it (S1, S2, weather)
2. train/test overlap is zero (SICKLE folds, the locked groups, the Odisha eval lock)
3. AlphaEarth for a season comes from strictly before the season
4. product availability lags and the D-019 cut-off are enforced
5. cross-issue-date aggregation reads only `as_of` at or before the row's own
   (pooling: `test_m1_pooling.py`; here, its use inside the conformal intervals)
"""

import numpy as np
import pandas as pd
import pytest

from rice_fallow_radar.eval import availability as A
from rice_fallow_radar.eval import splits
from rice_fallow_radar.features import odisha_m1 as O
from rice_fallow_radar.features import sickle_m1 as F
from rice_fallow_radar.models import m1_conformal as C

RNG = np.random.default_rng(0)
HARVESTS = {"s1": "2020-01-15", "s2": "2020-01-27"}


def _labels() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "UNIQUE_ID": list(HARVESTS),
            "PLOT_ID": [1, 2],
            "YEAR": [2019, 2019],
            "STANDARD_SEASON": ["sep-feb", "sep-feb"],
            "harvest": pd.to_datetime(list(HARVESTS.values())),
            "AREA": [0.4, 0.5],
            "group": [1, 2],
        }
    )


def _scenes(every: int, cols: dict) -> pd.DataFrame:
    dates = pd.date_range("2019-08-01", "2020-02-20", freq=f"{every}D")
    out = []
    for uid, h in HARVESTS.items():
        d = pd.DataFrame({"unique_id": uid, "date": dates})
        for c, (lo, hi) in cols.items():
            d[c] = RNG.uniform(lo, hi, len(d))
        d["lead_days"] = (pd.Timestamp(h) - d.date).dt.days
        out.append(d)
    return pd.concat(out, ignore_index=True)


def _inputs():
    s1 = _scenes(6, {"vh_db": (-22, -12), "vv_db": (-14, -6), "angle": (35, 38)})
    s1 = s1.assign(n_valid=16, n_px=16, edge_clipped=False)
    s2 = _scenes(5, {"ndvi": (0.1, 0.8), "ndwi": (-0.5, 0.2), "mndwi": (-0.5, 0.2)})
    s2 = s2.assign(clear=True, edge_clipped=False, n_clear=10)
    days = pd.date_range("2019-07-01", "2020-03-01")
    wx = pd.DataFrame({"tile": "T1", "date": days})
    for c, (lo, hi) in {
        "precipitation": (0, 0.02),
        "temperature_2m_max": (300, 308),
        "temperature_2m_min": (293, 298),
        "volumetric_soil_water_layer_1": (0.2, 0.4),
        "total_evaporation_sum": (-0.005, 0),
        "potential_evaporation_sum": (-0.008, 0),
    }.items():
        wx[c] = RNG.uniform(lo, hi, len(wx))
    tiles = pd.Series({uid: ["T1"] for uid in HARVESTS})
    return s1, s2, wx, tiles


def _build(s1, s2, wx, tiles):
    return F.build(_labels(), s1, weather=wx, tiles=tiles, s2=s2)


# 1 ------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "which,cols",
    [(0, ["vh_db", "vv_db"]), (1, ["ndvi", "ndwi", "mndwi"]), (2, ["precipitation"])],
    ids=["s1", "s2", "weather"],
)
def test_every_row_is_blind_to_inputs_after_its_own_as_of(which, cols):
    inputs = _inputs()
    clean = _build(*inputs)
    feats = F.feature_columns(clean)
    assert clean.n_scenes_s2.gt(0).all() and "rain_7d_mm" in clean, "fixture missed a block"
    for as_of in sorted(clean.as_of.unique()):
        poisoned = list(inputs)
        p = poisoned[which].copy()
        p.loc[p.date > as_of, cols] = 999.0
        poisoned[which] = p
        out = _build(*poisoned)
        rows = clean.as_of == as_of
        pd.testing.assert_frame_equal(
            clean.loc[rows, feats].reset_index(drop=True),
            out.loc[out.as_of == as_of, feats].reset_index(drop=True),
        )
        # the poison must reach later rows, or this test proves nothing
        if which < 2 and (clean.as_of > as_of).any():
            later = out.loc[out.as_of > as_of, feats].to_numpy(float)
            assert np.isclose(later, 999.0).any() or np.abs(np.nan_to_num(later)).max() > 100


def test_no_sickle_row_is_built_on_or_after_its_harvest():
    f = _build(*_inputs())
    assert len(f) and (f.as_of < f.harvest).all() and f.lead.min() >= F.MIN_LEAD


# 2 ------------------------------------------------------------------------------------------


def test_folds_never_split_a_sample_or_a_neighbour_group():
    n = 60
    feats = pd.DataFrame(
        {
            "unique_id": np.repeat([f"u{i}" for i in range(n)], 4),
            "group": np.repeat(np.arange(n) // 3, 4),
            "season": np.repeat(np.where(np.arange(n) % 2, "sep-feb", "oct-mar"), 4),
        }
    )
    fold = splits.assign_folds(feats)
    assert feats.groupby("unique_id").apply(lambda g: fold[g.index].nunique()).eq(1).all()
    assert feats.groupby("group").apply(lambda g: fold[g.index].nunique()).eq(1).all()


def test_locked_sickle_groups_never_reach_dev(monkeypatch):
    locked = splits.test_groups()  # the committed lock file: present in CI
    plots = pd.Series(range(60), index=range(60)) % 43
    monkeypatch.setattr(splits, "group_of_plot", lambda: plots)
    labels = pd.DataFrame({"PLOT_ID": range(60), "STANDARD_SEASON": "sep-feb"})
    dev, test = splits.dev_test(labels)
    assert set(test.group) <= set(locked) and not set(dev.group) & set(locked)
    assert not set(dev.PLOT_ID) & set(test.PLOT_ID)


def test_odisha_eval_lock_is_opt_in_by_name(odisha_labels):
    lab = odisha_labels
    assert "b" not in set(O.build(lab).field_id)
    assert "b" in set(O.build(lab, include_locked=True).field_id)


# 3 ------------------------------------------------------------------------------------------


def test_alphaearth_comes_from_before_the_season():
    assert A.alphaearth_year(2026) == 2025  # 2026's embedding contains the 2026 harvest
    usable = A.available_on("alphaearth", [pd.Timestamp("2025-06-30")]).iloc[0]
    # the embedding a season may use is published before that season's first issue date
    assert usable <= pd.Timestamp("2026-07-01")
    assert A.available_on("alphaearth", [pd.Timestamp("2026-01-01")]).iloc[0].year == 2027


# 4 ------------------------------------------------------------------------------------------


def test_availability_lags_hide_recent_observations():
    as_of = pd.Timestamp("2025-12-09")
    days = pd.DataFrame({"date": pd.date_range("2025-11-20", as_of)})
    for src, lag in A.LAG_DAYS.items():
        v = A.visible(days, src, as_of)
        assert v.date.max() == as_of - pd.Timedelta(days=lag), src
    # CHIRPS final for November is not out on 9 Dec; October's is
    v = A.visible(pd.DataFrame({"date": pd.to_datetime(["2025-10-31", "2025-11-01"])}),
                  "chirps_final", as_of)  # fmt: skip
    assert v.date.tolist() == [pd.Timestamp("2025-10-31")]
    with pytest.raises(KeyError):
        A.available_on("some_new_product", [as_of])


def test_cutoff_refuses_2026_27_outside_replay(odisha_labels):
    A.check_cutoff(["2026-05-31"])
    with pytest.raises(AssertionError, match="D-019"):
        A.check_cutoff(["2026-06-01"])
    A.check_cutoff(["2026-11-03"], replay=True)
    late = odisha_labels.assign(first_brown=pd.Timestamp("2026-06-02"))
    with pytest.raises(AssertionError, match="D-019"):
        O.build(late)


# 5 ------------------------------------------------------------------------------------------


def test_pooled_intervals_never_read_a_later_issue_date():
    """`C.pooled` feeds the published interval; poison the latest issue date of each field and
    every earlier row's interval must not move."""
    df = pd.DataFrame(
        {
            "unique_id": ["a"] * 4 + ["b"] * 3,
            "as_of": pd.to_datetime(
                ["2020-03-22", "2020-03-15", "2020-03-08", "2020-03-01"]
                + ["2020-03-15", "2020-03-08", "2020-03-01"]
            ),
        }
    )
    q = np.column_stack([np.arange(7.0), np.arange(7.0) + 5, np.arange(7.0) + 10])
    clean, _ = C.pooled(df, q)
    latest = df.groupby("unique_id").as_of.transform("max") == df.as_of
    poisoned = q.copy()
    poisoned[latest.to_numpy()] = 1e6
    out, n_acc = C.pooled(df, poisoned)
    assert np.allclose(clean[~latest.to_numpy()], out[~latest.to_numpy()])
    assert n_acc.tolist() == [4, 3, 2, 1, 3, 2, 1]
