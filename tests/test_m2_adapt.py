"""M2 adaptation pieces on synthetic seasons: detectors find a planted harvest, the phenological
clock cannot see the future, and the clock shift moves the calendar columns consistently."""

import numpy as np
import pandas as pd

from rice_fallow_radar.features import odisha_m1 as O
from rice_fallow_radar.models import m2_adapt as A

FLOOD, HARVEST = pd.Timestamp("2025-07-20"), pd.Timestamp("2025-11-25")


def _vh(every: int = 6) -> pd.DataFrame:
    """Dry soil -> flood (-24 dB) -> canopy (-14 dB) -> harvest drop to -21 dB."""
    d = pd.date_range("2025-05-01", "2026-02-15", freq=f"{every}D")
    vh = np.where(d < FLOOD - pd.Timedelta(days=10), -17.0, -24.0)
    grow = (d >= FLOOD) & (d < HARVEST)
    vh = np.where(grow, -24 + 10 * np.clip((d - FLOOD).days / 60, 0, 1), vh)
    vh = np.where(d >= HARVEST, -21.0, vh)
    return pd.DataFrame({"field_id": "f", "date": d, "vh_db": vh, "vv_db": vh + 6,
                         "orbit_pass": "DESCENDING"})  # fmt: skip


def test_radar_detector_brackets_the_planted_harvest():
    lg, fb = A.harvest_radar(_vh(), 3.0, "2025-08-01", "2026-02-15")
    assert lg < HARVEST <= fb and (fb - lg).days <= 6


def test_s2_detector_brackets_the_largest_drop():
    d = pd.date_range("2025-08-01", "2026-02-15", freq="10D")
    ndvi = np.where(d < HARVEST, 0.75, 0.25)
    h = pd.DataFrame({"date": d, "ndvi": ndvi})
    lg, fb = A.harvest_s2(h, 0.5, "2025-08-01", "2026-02-15")
    assert lg < HARVEST <= fb
    assert A.harvest_s2(h.assign(ndvi=0.7), 0.5, "2025-08-01", "2026-02-15") is None
    dip = h.assign(ndvi=np.where(h.date == h.date[5], 0.2, h.ndvi))  # one cloudy scene mid-season
    assert A.harvest_s2(dip, 0.5, "2025-08-01", "2026-02-15") == (lg, fb)


def test_flood_rule_needs_the_canopy_rise():
    h = _vh()
    assert abs((A.flood_date(h) - FLOOD).days) <= 12
    flat = h.assign(vh_db=np.where(h.date >= FLOOD - pd.Timedelta(days=10), -24.0, -17.0))
    assert pd.isna(A.flood_date(flat))  # stays flooded: no canopy, not a transplanting


def test_days_since_flood_ignores_scenes_not_yet_available():
    h = _vh()
    rows = pd.DataFrame(
        {"field_id": "f", "as_of": pd.date_range("2025-07-01", "2025-11-20", freq="7D")}
    )
    clean = A.add_days_since_flood(rows, h, "field_id")[A.PHENO_COL]
    for i, as_of in enumerate(rows.as_of):
        poisoned = h.copy()
        late = poisoned.date > as_of - pd.Timedelta(days=3)  # S1's 3-day lag
        poisoned.loc[late, "vh_db"] = -40.0  # a fake deeper flood the row must not see
        got = A.add_days_since_flood(rows.iloc[[i]], poisoned, "field_id")[A.PHENO_COL].iloc[0]
        assert got == clean.iloc[i] or (np.isnan(got) and np.isnan(clean.iloc[i]))


def test_shift_clock_is_a_pure_translation():
    lab = pd.DataFrame({"field_id": ["a"], "district": ["baleswar"], "stratum": ["U"],
                        "block": ["1_1"], "eval_lock": [False], "status": ["ok"],
                        "last_green": [HARVEST], "first_brown": [HARVEST + pd.Timedelta(days=4)],
                        "midpoint": [HARVEST + pd.Timedelta(days=2)]})  # fmt: skip
    rows = O.build(lab)
    out = A.shift_clock(rows, 20.0)
    assert (rows.days_since_season_start - out.days_since_season_start == 20).all()
    back = O.build(lab.assign(last_green=HARVEST))  # same issue dates
    t = rows.as_of - pd.Timedelta(days=20)
    assert np.allclose(out.doy_sin, np.sin(2 * np.pi * t.dt.day_of_year / 365.25))
    assert len(back) == len(rows)
