"""M2 adaptation pieces: harvest detectors, pseudo-labels, a phenological clock, a temporal shift.

Each answers one way the Tamil Nadu -> Odisha transfer can be helped, and each is the cheapest
defensible version of the method named in MODELS.md §M2:

* **Harvest detectors -> pseudo-labels** (Lee, 2013, "Pseudo-label"; the rule -> pseudo-label
  pattern of D-021/FARM). A detector reads a harvest date off a field's *whole* season, which a
  forecaster at `as_of` may not; on unlabelled Odisha fields that gives target-domain training
  rows. Two detectors: radar (VH falls a set number of dB below its smoothed season peak) and
  optical (the largest clear-scene NDVI drop after the green peak, which is what a human labeller
  reads). Both are validated on the free 40% hand labels before any pseudo-label is used.
* **Phenological clock** (`days_since_vh_flood`): days since the field's own transplanting flood,
  the D-031 flood-then-canopy signature, instead of days since a calendar date. Planting spread
  then stops being a domain shift by construction (MODELS.md §M2 alternatives).
* **Temporal shift** (TimeMatch, Nyborg et al., 2022, estimate the target's calendar offset with
  no target labels): here the offset that aligns the median flood season-day of Odisha's
  registry with SICKLE's samba fields, per district; the clock features are then shifted by it.

Every per-row feature reads only scenes visible on `as_of` (`eval.availability.visible`).
Detectors read the whole season by design: they make *labels*, never features.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..eval import availability

FLOOD_DB, RISE_DB, RISE_WINDOW = -20.0, 3.0, 60  # D-031's frozen flood rule (EVALUATION §M2)
FLOOD_LOOKBACK = 180  # days: one rice season, so a previous crop's flood is rarely in reach
PHENO_COL = "days_since_vh_flood"  # `days_since_vh` prefix -> the s1 block in `block_of`


def flood_date(h: pd.DataFrame) -> pd.Timestamp:
    """Date of the VH minimum if it is a flood followed by canopy, else NaT. `h` sorted by date."""
    if not len(h):
        return pd.NaT
    vh = h.vh_db.to_numpy()
    i = int(np.argmin(vh))
    when = h.date.iloc[i]
    after = vh[(h.date > when) & (h.date <= when + pd.Timedelta(days=RISE_WINDOW))]
    ok = vh[i] < FLOOD_DB and len(after) and after.max() - vh[i] >= RISE_DB
    return when if ok else pd.NaT


def add_days_since_flood(rows: pd.DataFrame, s1: pd.DataFrame, key: str) -> pd.DataFrame:
    """`rows` plus `PHENO_COL`, from the S1 scenes visible on each row's `as_of`.

    `key` names the field column in both frames (`unique_id` for SICKLE, `field_id` for Odisha).
    NaN where no flood is visible yet or the field never shows one (direct seeding).
    """
    by = {k: v.sort_values("date") for k, v in s1.groupby(key)}
    win = pd.Timedelta(days=FLOOD_LOOKBACK)
    out = []
    for fid, as_of in zip(rows[key], rows.as_of, strict=True):
        h = by.get(fid)
        if h is None:
            out.append(np.nan)
            continue
        h = availability.visible(h[h.date > as_of - win], "s1", as_of)
        d = flood_date(h)
        out.append(np.nan if pd.isna(d) else float((as_of - d).days))
    return rows.assign(**{PHENO_COL: out})


def harvest_radar(h: pd.DataFrame, drop_db: float, start, end) -> tuple | None:
    """(last standing scene, first harvested scene) from one field's season of VH, or None.

    Peak of the 3-scene smoothed VH inside `[start, end]`; harvest is the first later scene whose
    raw VH sits `drop_db` below that peak. The label is the interval between that scene and the
    one before it, exactly as a hand label brackets the harvest between two images.
    """
    h = h[(h.date >= pd.Timestamp(start)) & (h.date <= pd.Timestamp(end))].sort_values("date")
    if len(h) < 5:
        return None
    sm = h.vh_db.rolling(3, center=True, min_periods=1).mean().to_numpy()
    ip = int(np.argmax(sm))
    below = np.flatnonzero(h.vh_db.to_numpy()[ip + 1 :] <= sm[ip] - drop_db)
    if not len(below):
        return None
    j = ip + 1 + int(below[0])
    return h.date.iloc[j - 1], h.date.iloc[j]


def harvest_s2(h: pd.DataFrame, frac: float, start, end, max_gap: int = 30) -> tuple | None:
    """(last green, first brown) clear scenes where NDVI crosses from the season peak to its floor.

    `h` is one field's *clear* S2 scenes. Same-day scenes from overlapping tiles keep their
    maximum (residual cloud and shadow only ever lower NDVI). Peak and floor are taken on a
    3-scene rolling median, so one cloudy scene cannot make a harvest; the brown scene is the
    first after the peak at or below `floor + frac * (peak - floor)` **and followed by another
    one**, which a mid-season cloud dip is not. `max_gap` days between the two scenes at most.
    """
    h = h[(h.date >= pd.Timestamp(start)) & (h.date <= pd.Timestamp(end))]
    h = h.groupby("date", as_index=False).ndvi.max()
    if len(h) < 4:
        return None
    v = h.ndvi.to_numpy()
    sm = pd.Series(v).rolling(3, center=True, min_periods=1).median().to_numpy()
    ip = int(np.argmax(sm))
    floor = sm[ip:].min()
    if sm[ip] - floor < S2_MIN_AMPLITUDE:
        return None
    cut = floor + frac * (sm[ip] - floor)
    low = v <= cut
    for j in range(ip + 1, len(v) - 1):
        if low[j] and low[j + 1]:
            a, b = h.date.iloc[j - 1], h.date.iloc[j]
            return (a, b) if (b - a).days <= max_gap else None
    return None


def detect(
    fields: pd.DataFrame,
    s1: pd.DataFrame,
    s2: pd.DataFrame,
    method: str,
    s2_frac: float,
    radar_db: float,
    start,
    end,
) -> pd.DataFrame:
    """A labels-like frame (`features.odisha_m1.build` input) for every field the detector dates.

    `method` is `radar`, `s2`, or `fused` (S2 where it dates the field, radar otherwise: optical
    is the more direct read of a harvest, radar the one that sees through cloud).
    """
    s1 = s1[s1.orbit_pass == "DESCENDING"]
    by1 = {k: v for k, v in s1.groupby("field_id")}
    clear = s2[s2.clear].dropna(subset=["ndvi"])
    by2 = {k: v for k, v in clear.groupby("field_id")}
    out = []
    for r in fields.itertuples():
        got, src = None, None
        if method in ("s2", "fused") and r.field_id in by2:
            got, src = harvest_s2(by2[r.field_id], s2_frac, start, end), "s2"
        if got is None and method in ("radar", "fused") and r.field_id in by1:
            got, src = harvest_radar(by1[r.field_id], radar_db, start, end), "radar"
        if got is None:
            continue
        lg, fb = got
        out.append(
            dict(
                field_id=r.field_id,
                district=r.district,
                block=r.block,
                stratum="P",
                status="ok",
                eval_lock=False,
                last_green=lg,
                first_brown=fb,
                midpoint=lg + (fb - lg) / 2,
                interval_days=(fb - lg).days,
                source=src,
            )
        )
    return pd.DataFrame(out)


S2_MIN_AMPLITUDE = 0.2  # NDVI peak-to-floor: below this there was no crop to harvest


def flood_shift(target_sd: pd.Series, source_sd: pd.Series) -> float:
    """Days to subtract from the target's clock so its median flood lines up with the source's.

    Both are flood dates as days since the *same* season-start convention (1 Sep for `sep-feb`).
    The median, not the mean, because direct-seeded and pre-monsoon detections give a long tail.
    """
    return float(np.nanmedian(target_sd) - np.nanmedian(source_sd))


def shift_clock(rows: pd.DataFrame, delta: pd.Series | float) -> pd.DataFrame:
    """The calendar columns recomputed as if each row were issued `delta` days earlier."""
    d = pd.to_timedelta(np.asarray(delta, float) if np.ndim(delta) else delta, unit="D")
    t = rows.as_of - d
    return rows.assign(
        days_since_season_start=rows.days_since_season_start - np.asarray(delta, float),
        doy_sin=np.sin(2 * np.pi * t.dt.day_of_year / 365.25),
        doy_cos=np.cos(2 * np.pi * t.dt.day_of_year / 365.25),
    )
