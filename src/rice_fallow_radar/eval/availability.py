"""When each input becomes usable at an issue date: the data rule of the frozen protocol.

`EVALUATION.md` §Replay protocol (v1) points here rather than restating the numbers, so the table
the tests check and the table the dissertation quotes are the same object.

A source's value for day `d` may feed a forecast issued on `as_of` only if
`available_on(source, d) <= as_of`. Lags are **conservative estimates, not measurements**
(nothing here was timed against Earth Engine's ingest log); the protocol lets them be *raised*
after the freeze if replay ingest shows a longer real lag, never lowered, so any error in the
table can only make the replay harder, not leakier.

Two sources are not a fixed lag:
* **CHIRPS final** is released per month, about three weeks after the month ends.
* **AlphaEarth** embeddings are annual and summarise the whole calendar year, so year Y already
  contains year Y's kharif harvest and winter crop. The year rule (`alphaearth_year`) is
  stricter than the availability rule and both must hold.

D-019's cut-off lives here too: no date on or after `data_cutoff` may enter the pipeline outside
an explicit replay run, and replay is only legal once `protocol-v1` exists.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

CONFIG = Path(__file__).resolve().parents[3] / "configs" / "districts.yaml"

# days after the observation date that the value is usable; rounded *up* where unsure
LAG_DAYS = {
    "s1": 3,  # COPERNICUS/S1_GRD, typically ingested within 1-2 days
    "s2": 5,  # COPERNICUS/S2_SR_HARMONIZED + Cloud Score+, typically 2-4 days
    "era5_land": 8,  # ECMWF/ERA5_LAND/DAILY_AGGR, ~5 d reanalysis latency + ingest
    "chirps_prelim": 3,  # CHIRPS preliminary, per pentad, ~2 days after the pentad
    "nisar_sme2": 14,  # newest granule was ~2 weeks old on 6 Nov 2026 (DATA.md §NISAR)
    "smap": 3,  # L3/L4 soil moisture, ~2-3 days
}
CHIRPS_FINAL_DAYS_AFTER_MONTH = 25  # final monthly release ~3rd week of the next month
ALPHAEARTH_RELEASE = (7, 1)  # year Y assumed usable from 1 Jul of Y+1 (annual product)


def available_on(source: str, dates) -> pd.Series:
    """The first issue date on which each observation date of `source` may be used."""
    d = pd.Series(pd.to_datetime(dates))
    if source == "chirps_final":
        return d + pd.offsets.MonthEnd(0) + pd.Timedelta(days=CHIRPS_FINAL_DAYS_AFTER_MONTH)
    if source == "alphaearth":
        m, day = ALPHAEARTH_RELEASE
        return pd.to_datetime(pd.DataFrame({"year": d.dt.year + 1, "month": m, "day": day}))
    if source not in LAG_DAYS:
        raise KeyError(f"no availability rule for source {source!r}: add one before using it")
    return d + pd.Timedelta(days=LAG_DAYS[source])


def visible(df: pd.DataFrame, source: str, as_of, date_col: str = "date") -> pd.DataFrame:
    """The rows of `df` a forecast issued on `as_of` is allowed to read."""
    ok = available_on(source, df[date_col]).to_numpy() <= pd.Timestamp(as_of)
    return df[ok]


def alphaearth_year(season_start_year: int) -> int:
    """The newest embedding year a season may use: strictly before the season starts (D-013).

    The 2026-27 season starts in June 2026, and the 2026 embedding summarises Nov-Dec 2026 -- the
    harvest being forecast -- so the season may use 2025 at the latest.
    """
    return season_start_year - 1


def data_cutoff() -> pd.Timestamp:
    return pd.Timestamp(yaml.safe_load(CONFIG.read_text())["data_cutoff"])


def check_cutoff(dates, replay: bool = False) -> None:
    """D-019: refuse any date on or after the cut-off unless this is a declared replay run."""
    if replay:
        return
    late = pd.Series(pd.to_datetime(dates)) >= data_cutoff()
    assert not late.any(), (
        f"{int(late.sum())} date(s) on/after the D-019 cutoff {data_cutoff():%Y-%m-%d}; "
        "2026-27 data is only readable in replay mode (EVALUATION.md §Replay protocol)"
    )
