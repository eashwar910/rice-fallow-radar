"""P3 step 1 (EVALUATION.md §M2 protocol, v1): D-031's measurement, before any Odisha model.

How spread out are kharif flooding (transplanting) dates across the Odisha registry? D-031
predicts materially more than SICKLE's 10.0 d, and is **falsified if the pooled robust SD is
under 15 d**. Every choice below is the frozen one; the sensitivities are reported, not selected.

    sample      2,000 fields per district, uniform over fields.parquet, seed 20261126
    signal      S1 VH, descending passes, 1 Jun - 30 Sep 2025 (`ingest.s1`)
    flood date  date of the VH minimum, kept if the minimum is below THRESHOLD and VH rises by
                RISE_DB within RISE_WINDOW days afterwards (flood, then canopy)
    statistic   SD and robust SD (1.4826 x MAD) of flood season-day, per district and pooled

Resumable: each chunk of fields is cached under data/interim/odisha_s1_2025/ and skipped when
present. Usage:
    uv run python scripts/odisha_transplant_spread.py            # the frozen run
    uv run python scripts/odisha_transplant_spread.py --n 10     # smoke test, not a result
Writes runs/odisha_transplant_spread.csv (only for the frozen sample size).
"""

import argparse
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from rice_fallow_radar.ingest import earth_engine, s1

CACHE = Path("data/interim/odisha_s1_2025")
RESULTS = Path("runs/odisha_transplant_spread.csv")
N_PER_DISTRICT, SEED = 2000, 20261126
START, END = "2025-06-01", "2025-10-01"
THRESHOLD, SENSITIVITY = -20.0, (-18.0, -22.0)
RISE_DB, RISE_WINDOW = 3.0, 60
FALSIFIED_BELOW = 15.0  # D-031's revisit clause, on the pooled robust SD
SICKLE_SD = 10.0


def sample(n: int) -> gpd.GeoDataFrame:
    reg = gpd.read_parquet("data/processed/fields.parquet")
    return pd.concat(
        g.sample(n=min(n, len(g)), random_state=SEED) for _, g in reg.groupby("district")
    ).reset_index(drop=True)


def pull(fields: gpd.GeoDataFrame, tag: str) -> pd.DataFrame:
    CACHE.mkdir(parents=True, exist_ok=True)
    frames = []
    for i in range(0, len(fields), s1.CHUNK):
        f = CACHE / f"{tag}_{i:05d}.parquet"
        if not f.exists():
            s1.series(fields.iloc[i : i + s1.CHUNK], START, END).to_parquet(f)
        frames.append(pd.read_parquet(f))
        print(f"  {min(i + s1.CHUNK, len(fields))}/{len(fields)} fields", flush=True)
    return pd.concat(frames, ignore_index=True)


def flood_dates(series: pd.DataFrame, threshold: float) -> pd.Series:
    """Season-day of each field's flood, NaN where the flood-then-canopy signature is absent."""
    out = {}
    for fid, g in series.groupby("field_id"):
        g = g.sort_values("date")
        i = int(np.argmin(g.vh_db.to_numpy()))
        low, when = g.vh_db.iloc[i], g.date.iloc[i]
        after = g[(g.date > when) & (g.date <= when + pd.Timedelta(days=RISE_WINDOW))]
        ok = low < threshold and len(after) and after.vh_db.max() - low >= RISE_DB
        out[fid] = (when - pd.Timestamp(START)).days if ok else np.nan
    return pd.Series(out, name="flood_sd")


def spread(v: pd.Series) -> dict:
    v = v.dropna().to_numpy(float)
    mad = 1.4826 * float(np.median(np.abs(v - np.median(v)))) if len(v) else np.nan
    return dict(n=len(v), sd=float(v.std(ddof=1)) if len(v) > 1 else np.nan, robust_sd=mad)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=N_PER_DISTRICT)
    n = ap.parse_args().n
    fields = sample(n)
    earth_engine.init()
    series = pull(fields, f"n{n}")
    desc = series[series.orbit_pass == "DESCENDING"]
    district = fields.set_index("field_id").district
    rows = []
    for passes, s in (("descending", desc), ("all", series)):
        for thr in (THRESHOLD, *SENSITIVITY):
            fd = flood_dates(s, thr)
            for name, v in [("pooled", fd), *fd.groupby(district.reindex(fd.index))]:
                rows.append(
                    dict(passes=passes, threshold=thr, district=name, sampled=n, **spread(v))
                )
    res = pd.DataFrame(rows).round(2)
    print(res.to_string(index=False))
    head = res[(res.passes == "descending") & (res.threshold == THRESHOLD)]
    pooled = head[head.district == "pooled"].iloc[0]
    verdict = "holds" if pooled.robust_sd >= FALSIFIED_BELOW else "is FALSIFIED"
    print(
        f"\nheadline: pooled robust SD {pooled.robust_sd:.1f} d (SD {pooled.sd:.1f}, n={pooled.n})"
        f" vs SICKLE {SICKLE_SD} d -> D-031 {verdict} (line at {FALSIFIED_BELOW} d)"
    )
    if n == N_PER_DISTRICT:
        RESULTS.parent.mkdir(exist_ok=True)
        res.to_csv(RESULTS, index=False)
        print(f"wrote {RESULTS}")
    else:
        print("smoke run: not a result, nothing written to runs/")


if __name__ == "__main__":
    sys.exit(main())
