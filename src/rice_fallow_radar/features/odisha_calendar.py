"""An Odisha crop-calendar prior built from CSISA, as an alternative to SICKLE's calendar.

Why this exists. M1's point model is four calendar features and no satellite data (D-030), and it
works because harvest date in the Cauvery delta is a scheduled quantity (D-031). Moving that model
to Odisha zero-shot carries *Tamil Nadu's* schedule with it, which is the one part of M1 we have
positive reason to think does not transfer. CSISA gives a second, independent calendar for the
target region -- farmer-reported, 2017/2018, and for Baleswar at the right district.

A "prior" here is the distribution of kharif **transplanting** season-day plus the distribution of
**duration** (transplanting -> harvest); the two compose into a harvest-date distribution. Both are
measured transplanted-only and in-season; see `reports/csisa_calendar_stats.md` §9 for why the
second filter is not optional (one summer-rice field doubles Balasore's apparent spread).

What it is *not*: a per-field feature. CSISA points are 3-dp cells shared by up to 7 farmers, and
variety is unknown for registry fields, so the deployable prior is **district-level**. Per-variety
durations are kept for diagnosing *why* a transfer gap is the size it is, and for the secondary
Balasore evaluation set, where variety is known.

This module reads CSISA only. It does not touch SICKLE, its features, or its locked test groups.
"""

import numpy as np
import pandas as pd

SEASON_ORIGIN = (6, 1)  # 1 June: the season clock both domains are measured on
SEASON_WINDOW = (0, 180)  # a kharif establishment date lands in here; see module docstring
MIN_VARIETY_N = 5
QUANTILES = (0.05, 0.25, 0.5, 0.75, 0.95)
# D-031's SICKLE figure, carried here so the comparison is in the artefact rather than in prose
SICKLE_TRANSPLANT_SD = 10.0


def season_day(dates: pd.Series, year: pd.Series) -> pd.Series:
    """Days since 1 June of the survey year -- a clock that does not wrap at new year."""
    m, d = SEASON_ORIGIN
    origin = pd.to_datetime(pd.DataFrame({"year": year, "month": m, "day": d}))
    return (dates - origin).dt.days


def kharif_transplanted(csisa: pd.DataFrame, district: str | None = None) -> pd.DataFrame:
    """The rows a calendar prior may be built from: transplanted, in-season, Odisha."""
    df = csisa[(csisa.state == "Odisha") & csisa.transplanted].copy()
    if district is not None:
        df = df[df.district == district]
    df["transplant_sd"] = season_day(df.estab_date, df.year)
    df["harvest_sd"] = season_day(df.harvest_date, df.year)
    df = df[df.transplant_sd.between(*SEASON_WINDOW)]
    return df.dropna(subset=["transplant_sd", "harvest_sd", "duration_days"]).reset_index(drop=True)


def prior(csisa: pd.DataFrame, district: str | None = None) -> pd.Series:
    """District-level calendar prior: transplanting, duration and the harvest date they imply.

    `harvest_*` are measured directly rather than composed from the two marginals, because
    transplanting date and duration are negatively correlated here (a late transplanter picks a
    shorter variety), so composing the marginals would overstate the harvest spread.
    """
    df = kharif_transplanted(csisa, district)
    out = {
        "district": district or "Odisha (all)",
        "n": len(df),
        "years": "/".join(str(y) for y in sorted(df.year.unique())),
        "villages": df.village.nunique(),
    }
    for name, col in (
        ("transplant", "transplant_sd"),
        ("duration", "duration_days"),
        ("harvest", "harvest_sd"),
    ):
        v = df[col].to_numpy(float)
        out[f"{name}_mean"] = float(v.mean())
        out[f"{name}_sd"] = float(v.std(ddof=1))
        out[f"{name}_robust_sd"] = 1.4826 * float(np.median(np.abs(v - np.median(v))))
        for q in QUANTILES:
            out[f"{name}_q{int(q * 100):02d}"] = float(np.quantile(v, q))
    out["transplant_sd_vs_sickle"] = out["transplant_sd"] - SICKLE_TRANSPLANT_SD
    return pd.Series(out)


def variety_durations(csisa: pd.DataFrame, district: str | None = None) -> pd.DataFrame:
    """Median duration per variety, for varieties with at least MIN_VARIETY_N rows."""
    df = kharif_transplanted(csisa, district)
    t = df.groupby("var_name_norm").duration_days.agg(n="size", median="median", sd="std")
    t = t[t.n >= MIN_VARIETY_N].sort_values("n", ascending=False)
    return t.reset_index().rename(columns={"var_name_norm": "variety"})


def zero_shot_harvest(p: pd.Series, year: int, level: float = 0.90) -> dict:
    """The Odisha-calendar arm's forecast: one harvest date and interval for every field.

    Deliberately field-independent -- that is the point of the arm. It is the floor any
    transferred M1 has to beat on Odisha: if a per-field model cannot beat one date read off a
    farmer survey, the sensors are not carrying the forecast (the Odisha analogue of the
    calendar-only arm that beat every sensor arm on SICKLE, D-030).
    """
    lo_q, hi_q = round((1 - level) / 2, 4), round(1 - (1 - level) / 2, 4)
    assert {lo_q, hi_q} <= set(QUANTILES), f"prior holds {QUANTILES}, not level {level}"
    m, d = SEASON_ORIGIN
    origin = pd.Timestamp(year=year, month=m, day=d)
    lo, hi = (int(q * 100) for q in (lo_q, hi_q))

    # a harvest forecast is a date: round the fractional quantile days rather than emit a timestamp
    def day(key):
        return origin + pd.Timedelta(days=round(float(p[key])))

    return {
        "harvest_date": day("harvest_q50"),
        "lower": day(f"harvest_q{lo:02d}"),
        "upper": day(f"harvest_q{hi:02d}"),
        "width_days": (day(f"harvest_q{hi:02d}") - day(f"harvest_q{lo:02d}")).days,
    }
