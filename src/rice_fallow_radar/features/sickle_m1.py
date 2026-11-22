"""M1 feature table for SICKLE: one row per (sample, issue date).

Design choices worth defending:

* **Issue dates are a weekly calendar grid, not offsets from the harvest date.** If rows were
  built at `harvest - h` the target would be the constant `h` and the model would learn nothing.
  So issue dates run every `EVERY` days through the season and the target is the true days to
  harvest at that date; the 7/14/21-day "horizons" of the proposal are lead-time *buckets* at
  evaluation (`LEAD_BUCKETS`).
* **Every feature is computed from scenes dated on or before `as_of`** (`LOOKBACK_D` of history).
  SICKLE patches run ~2 scenes past harvest, so an untruncated series leaks the answer.
* **Rows are conditioned on the field not yet being harvested** (`lead >= MIN_LEAD`). M1 answers
  "how long until harvest", and deciding whether a field is still standing is the harvest
  detector's job, not M1's. State this when quoting M1 numbers.
* **Weather is regional** (per MGRS tile, D-023), flagged by `weather_regional` so the same
  table can hold Odisha's per-field weather later.
* **Optical features are opt-in and row-preserving** (`s2=`). Passing S2 adds columns and never
  adds or drops a row, so the S1-only vs S1+S2 ablation compares models on identical rows.
  Only scenes that pass SICKLE's cloud mask count, and every S2 row of the current table has at
  least 2 of them (median 9), so nothing is lost. MNDWI gets two columns rather than the full
  battery: it measured flat across harvest (DATA.md, 22 Nov), so it is a waterlogging feature.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from rice_fallow_radar.ingest.sickle import best_per_date

EVERY = 7  # days between issue dates
LOOKBACK_D = 120  # days of S1 history a row may use
MIN_LEAD, MAX_LEAD = 1, 60  # days to harvest covered by the training rows
LEAD_BUCKETS = {7: (4, 10), 14: (11, 17), 21: (18, 24)}
SEASON_START_MONTH = {
    "jan": 1,
    "feb": 2,
    "may": 5,
    "jun": 6,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}
RAIN_W = (7, 14, 30)
PEAK_W = 45  # days; window the VH peak search (see _s1_row)
GDD_BASE = 10.0  # degC, standard for rice growing-degree days
# Feature blocks for the point-C ablation. `block_of` is checked column-by-column by
# test_every_feature_belongs_to_exactly_one_block: one optical column left in the S1-only arm,
# or one sensor column left in the calendar arm, silently voids the ablation.
S2_PREFIXES = ("ndvi", "ndwi", "mndwi", "n_scenes_s2", "days_since_clear_s2", "days_since_ndvi")
WEATHER_PREFIXES = ("rain_", "gdd_", "soil_", "t2m_", "evap_", "pet_", "water_balance_")
S1_PREFIXES = (
    "vh_",
    "vv_",
    "ratio_",
    "angle_",
    "px_",
    "n_scenes",
    "days_since_scene",
    "days_since_vh",
)
# what the model knows without any satellite: where in the season it is, and how big the plot is
BASE_COLS = ("days_since_season_start", "doy_sin", "doy_cos", "area_acres")


def block_of(col: str) -> str:
    """Which ablation block a feature column belongs to: base, s1, weather, s2 or unknown."""
    if col in BASE_COLS:
        return "base"
    if col.startswith(S2_PREFIXES):  # before s1: `n_scenes_s2` would match `n_scenes`
        return "s2"
    if col.startswith(WEATHER_PREFIXES):
        return "weather"
    if col.startswith(S1_PREFIXES):
        return "s1"
    return "unknown"


def block_columns(df: pd.DataFrame, blocks: tuple[str, ...]) -> list[str]:
    """The feature columns of `df` belonging to any of `blocks`."""
    return [c for c in feature_columns(df) if block_of(c) in blocks]


def _slope(days: np.ndarray, y: np.ndarray) -> float:
    """Units of `y` per day, least squares. Needs two distinct dates."""
    if len(days) < 2 or np.ptp(days) == 0:
        return np.nan
    return float(np.polyfit(days, y, 1)[0])


def _s1_row(h: pd.DataFrame, as_of: pd.Timestamp) -> dict:
    """S1 features from the scenes of one sample up to `as_of` (already filtered)."""
    age = (as_of - h.date).dt.days.to_numpy()  # days before as_of, 0 = today
    t = -age.astype(float)  # increasing with time, for slopes
    vh, vv = h.vh_db.to_numpy(), h.vv_db.to_numpy()
    imax, imin = int(np.argmax(vh)), int(np.argmin(vh))
    f = {
        "n_scenes": len(h),
        "days_since_scene": int(age[-1]),
        "vh_last": vh[-1],
        "vv_last": vv[-1],
        "ratio_last": vh[-1] - vv[-1],  # dB difference = log of the VH/VV ratio
        "angle_last": h.angle.to_numpy()[-1],
        "px_valid_last": h.n_valid.to_numpy()[-1],
        "px_plot": int(h.n_px.iloc[0]),
        "vh_max": vh.max(),
        "vh_min": vh.min(),
        "vh_last_minus_max": vh[-1] - vh.max(),
        "days_since_vh_max": int(age[imax]),
        "days_since_vh_min": int(age[imin]),
    }
    # peak of a 3-scene smoothed curve, searched in a short window: with a 120-day lookback the
    # highest VH in the multi-cropped Cauvery delta is often the *previous* crop's canopy peak
    for w in (PEAK_W,):
        m = age <= w
        sm = pd.Series(vh[m]).rolling(3, center=True, min_periods=1).mean().to_numpy()
        f[f"days_since_vh_max_{w}"] = int(age[m][int(np.argmax(sm))]) if m.any() else np.nan
        f[f"vh_max_sm_{w}"] = float(sm.max()) if m.any() else np.nan
        f[f"vh_last_minus_max_sm_{w}"] = vh[-1] - sm.max() if m.any() else np.nan
    for w in (30, 60):
        m = age <= w
        f[f"vh_mean_{w}"] = vh[m].mean() if m.any() else np.nan
        f[f"vv_mean_{w}"] = vv[m].mean() if m.any() else np.nan
        f[f"vh_sd_{w}"] = vh[m].std() if m.sum() > 1 else np.nan
        f[f"vh_slope_{w}"] = _slope(t[m], vh[m])
        f[f"n_scenes_{w}"] = int(m.sum())
    return f


def _s2_row(h: pd.DataFrame, as_of: pd.Timestamp) -> dict:
    """Optical features from the clear S2 scenes of one sample up to `as_of` (already filtered)."""
    age = (as_of - h.date).dt.days.to_numpy()
    t = -age.astype(float)
    ndvi, ndwi, mndwi = h.ndvi.to_numpy(), h.ndwi.to_numpy(), h.mndwi.to_numpy()
    f = {
        "n_scenes_s2": len(h),
        "days_since_clear_s2": int(age[-1]),  # a stale NDVI is worth less than a fresh one
        "ndvi_last": ndvi[-1],
        "ndvi_delta": ndvi[-1] - ndvi[-2] if len(ndvi) > 1 else np.nan,
        "ndwi_last": ndwi[-1],
        "mndwi_last": mndwi[-1],
    }
    # the greenest scene over a 120-day lookback is often the *previous* crop's canopy in the
    # multi-cropped delta, so the green peak is searched in a short window (same trap as VH)
    m = age <= PEAK_W
    sm = pd.Series(ndvi[m]).rolling(3, center=True, min_periods=1).mean().to_numpy()
    f[f"days_since_ndvi_max_{PEAK_W}"] = int(age[m][int(np.argmax(sm))]) if m.any() else np.nan
    f[f"ndvi_max_sm_{PEAK_W}"] = float(sm.max()) if m.any() else np.nan
    f[f"ndvi_last_minus_max_sm_{PEAK_W}"] = ndvi[-1] - sm.max() if m.any() else np.nan
    for w in (30, 60):
        m = age <= w
        f[f"ndvi_mean_{w}"] = ndvi[m].mean() if m.any() else np.nan
        f[f"ndvi_slope_{w}"] = _slope(t[m], ndvi[m])
    m = age <= 30
    f["ndwi_slope_30"] = _slope(t[m], ndwi[m])
    f["mndwi_mean_30"] = mndwi[m].mean() if m.any() else np.nan
    return f


def _weather_row(w: pd.DataFrame, as_of: pd.Timestamp, season_start: pd.Timestamp) -> dict:
    """Rain, heat and moisture summaries for one tile-series up to `as_of`."""
    past = w[w.date <= as_of]
    if past.empty:
        return {}
    age = (as_of - past.date).dt.days
    since = past[past.date >= season_start]
    tmean = (past.temperature_2m_max + past.temperature_2m_min) / 2 - 273.15
    f = {
        "rain_season_mm": float(since.precipitation.sum()),
        "gdd_season": float(np.clip(tmean[since.index] - GDD_BASE, 0, None).sum()),
        "soil_w1_last": float(past.volumetric_soil_water_layer_1.iloc[-1]),
    }
    for d in RAIN_W:
        m = age <= d
        f[f"rain_{d}d_mm"] = float(past.precipitation[m].sum())
        f[f"t2m_mean_{d}d"] = float(tmean[m].mean())
    f["evap_30d_mm"] = float(-past.total_evaporation_sum[age <= 30].sum() * 1000)
    f["pet_30d_mm"] = float(-past.potential_evaporation_sum[age <= 30].sum() * 1000)
    f["water_balance_30d"] = f["rain_30d_mm"] - f["pet_30d_mm"]
    return f


def build(
    labels: pd.DataFrame,
    series: pd.DataFrame,
    weather: pd.DataFrame | None = None,
    tiles: pd.Series | None = None,
    s2: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """One row per (sample, issue date). `series` is `ingest.sickle.s1_series` output,
    `s2` is `ingest.sickle.s2_series` output (optional; adds columns, never rows)."""
    s = series[~series.edge_clipped].dropna(subset=["vh_db"])
    by_id = {k: v.sort_values("date") for k, v in s.groupby("unique_id")}
    s2_by = {}
    if s2 is not None:
        clear = s2[s2.clear & ~s2.edge_clipped].dropna(subset=["ndvi", "ndwi", "mndwi"])
        s2_by = {k: v for k, v in best_per_date(clear).groupby("unique_id")}
    wx = (
        {k: v.sort_values("date") for k, v in weather.groupby("tile")}
        if weather is not None
        else {}
    )
    rows = []
    for r in labels.itertuples():
        h = by_id.get(r.UNIQUE_ID)
        if h is None:
            continue
        start = pd.Timestamp(
            year=int(r.YEAR), month=SEASON_START_MONTH[r.STANDARD_SEASON[:3]], day=1
        )
        # issue dates land on the same weekday every season, counting back from harvest
        for lead in range(MIN_LEAD, MAX_LEAD + 1):
            if (lead - MIN_LEAD) % EVERY:
                continue
            as_of = r.harvest - pd.Timedelta(days=lead)
            if as_of < start:
                continue
            past = h[(h.date <= as_of) & (h.date > as_of - pd.Timedelta(days=LOOKBACK_D))]
            if len(past) < 3:
                continue
            row = dict(
                unique_id=r.UNIQUE_ID,
                plot_id=r.PLOT_ID,
                group=getattr(r, "group", np.nan),
                season=r.STANDARD_SEASON,
                year=int(r.YEAR),
                as_of=as_of,
                harvest=r.harvest,
                lead=lead,
                days_since_season_start=(as_of - start).days,
                doy_sin=np.sin(2 * np.pi * as_of.day_of_year / 365.25),
                doy_cos=np.cos(2 * np.pi * as_of.day_of_year / 365.25),
                area_acres=r.AREA,
            )
            row.update(_s1_row(past, as_of))
            if s2 is not None:
                h2 = s2_by.get(r.UNIQUE_ID)
                win = pd.Timedelta(days=LOOKBACK_D)
                past2 = (
                    h2[(h2.date <= as_of) & (h2.date > as_of - win)]
                    if h2 is not None
                    else pd.DataFrame()
                )
                row["n_scenes_s2"] = 0  # keep the column defined when cloud left nothing
                if len(past2):
                    row.update(_s2_row(past2, as_of))
            if wx and tiles is not None:
                ts = [t for t in tiles.get(r.UNIQUE_ID, []) if t in wx]
                parts = [_weather_row(wx[t], as_of, start) for t in ts]
                parts = [p for p in parts if p]
                if parts:  # a sample on two tiles gets the mean of both regional series
                    row.update(pd.DataFrame(parts).mean().to_dict())
                row["weather_regional"] = True
                row["weather_tiles"] = ",".join(ts)
            rows.append(row)
    out = pd.DataFrame(rows)
    assert (out.lead >= MIN_LEAD).all(), "a row was built on or after its harvest date"
    return out


def feature_columns(df: pd.DataFrame) -> list[str]:
    drop = {
        "unique_id",
        "plot_id",
        "group",
        "season",
        "year",
        "as_of",
        "harvest",
        "lead",
        "weather_regional",
        "weather_tiles",
    }
    return [c for c in df.columns if c not in drop]
