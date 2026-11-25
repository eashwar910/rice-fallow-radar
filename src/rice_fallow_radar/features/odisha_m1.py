"""M1 rows for the Odisha hand labels: the target side of the M2 transfer.

One row per (labelled field, weekly issue date), carrying the same calendar columns as
`features.sickle_m1` (D-030's point model) so a SICKLE-trained model can score Odisha zero-shot,
plus an **interval-valued target**. Choices frozen in `EVALUATION.md` §M2 protocol (v1):

* **Issue dates are real Tuesdays** (the replay weekday), not offsets from the harvest: the
  harvest date is not known here, only an interval.
* **A row exists only while the field is visibly unharvested**: `as_of < last_green`. That is
  the Odisha analogue of SICKLE's `lead >= MIN_LEAD` -- deciding that a field is still standing
  is the harvest detector's job.
* **Targets** are `lead_lo = last_green - as_of` and `lead_hi = first_brown - as_of`, scored by
  §Interval quality rule 5 (`eval.interval_scoring`). `lead` is the midpoint, used only to put a
  row in a lead bucket and to cap rows at `MAX_LEAD`, exactly as SICKLE caps on true lead.
* **The SICKLE season the zero-shot model is told** is a pre-registered mapping, `HEADLINE_SEASON`.
  Odisha kharif is the main monsoon crop, long-duration, harvested Nov-Jan, which is the samba
  crop of the Cauvery delta -- SICKLE's `sep-feb`. `days_since_season_start` is then counted from
  SICKLE's own convention for that season (1 Sep), not from CSISA's 1 June. The other mappings
  are reported as a sensitivity and never selected (the clock ablation, MODELS.md §M2).
* **Eval-locked rows are excluded unless asked for by name** (`include_locked=True`), which only
  the final-evaluation script may do (D-018).

Sensor columns are not built here yet: they need the Odisha S1/S2 pulls (`ingest.s1`, P3) and
must go through `eval.availability.visible`, unlike SICKLE's hindcast table.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..eval import availability
from .sickle_m1 import MAX_LEAD, SEASON_START_MONTH

ISSUE_WEEKDAY = 1  # Tuesday: CHIRPS preliminary and ERA5-Land for the past week are in by then
HEADLINE_SEASON = "sep-feb"
SICKLE_SEASONS = ("may-sep", "jun-oct", "sep-feb", "oct-mar", "dec-may")
COLUMNS = (
    "field_id", "district", "stratum", "block", "eval_lock", "season", "as_of", "last_green",
    "first_brown", "lead_lo", "lead_hi", "lead", "days_since_season_start", "doy_sin", "doy_cos",
)  # fmt: skip


def season_start(last_green: pd.Timestamp, season: str) -> pd.Timestamp:
    """1st of the mapped SICKLE season's start month, in the kharif season the label belongs to."""
    kharif_year = last_green.year if last_green.month >= 6 else last_green.year - 1
    m = SEASON_START_MONTH[season[:3]]
    return pd.Timestamp(year=kharif_year + (m < 6), month=m, day=1)


def build(
    labels: pd.DataFrame, season: str = HEADLINE_SEASON, include_locked: bool = False
) -> pd.DataFrame:
    """Rows for every `ok` label. `labels` is `data/processed/odisha_labels.parquet`."""
    lab = labels[labels.status == "ok"]
    if not include_locked:
        lab = lab[~lab.eval_lock.astype(bool)]
    availability.check_cutoff(lab.first_brown)
    rows = []
    for r in lab.itertuples():
        start = season_start(r.last_green, season)
        first = max(start, r.midpoint - pd.Timedelta(days=MAX_LEAD))
        first += pd.Timedelta(days=(ISSUE_WEEKDAY - first.day_of_week) % 7)
        for as_of in pd.date_range(first, r.last_green - pd.Timedelta(days=1), freq="7D"):
            rows.append(
                dict(
                    field_id=r.field_id,
                    district=r.district,
                    stratum=r.stratum,
                    block=r.block,
                    eval_lock=bool(r.eval_lock),
                    season=season,
                    as_of=as_of,
                    last_green=r.last_green,
                    first_brown=r.first_brown,
                    lead_lo=(r.last_green - as_of).days,
                    lead_hi=(r.first_brown - as_of).days,
                    lead=(r.midpoint - as_of) / pd.Timedelta(days=1),
                    days_since_season_start=(as_of - start).days,
                    doy_sin=np.sin(2 * np.pi * as_of.day_of_year / 365.25),
                    doy_cos=np.cos(2 * np.pi * as_of.day_of_year / 365.25),
                )
            )
    out = pd.DataFrame(rows, columns=list(COLUMNS))  # a mapping can leave no rows (dec-may)
    if len(out):
        assert (out.as_of < out.last_green).all(), "a row was issued after the field turned brown"
        assert (out.as_of.dt.day_of_week == ISSUE_WEEKDAY).all(), "an issue date is off the weekday"
    return out
