"""P3 step 3: S1 and S2 per-field series for every `ok` Odisha hand label (locked ones included).

Pulling a locked field's imagery is not scoring it: rows for the locked 60% are only ever built
by the final-evaluation script (D-018). Pulling everything once avoids a second Earth Engine run
at the unlock. Window: 120 days (`features.sickle_m1.LOOKBACK_D`) before the earliest issue date
(1 Sep 2025 under the `sep-feb` mapping) through the latest label.

Resumable per chunk under data/interim/odisha_sensors/. Usage:
    uv run python scripts/odisha_sensor_pull.py s1
    uv run python scripts/odisha_sensor_pull.py s2
Writes data/interim/odisha_sensors/{s1,s2}.parquet.
"""

import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

from rice_fallow_radar.ingest import earth_engine, s1, s2

OUT = Path("data/interim/odisha_sensors")
START, END = "2025-05-01", "2026-02-20"


def fields() -> gpd.GeoDataFrame:
    lab = pd.read_parquet("data/processed/odisha_labels.parquet")
    ids = lab[lab.status == "ok"].field_id
    reg = gpd.read_parquet("data/processed/fields.parquet")
    f = reg[reg.field_id.isin(ids)].sort_values("field_id").reset_index(drop=True)
    assert len(f) == len(ids), "a labelled field is missing from the registry"
    return f


def main() -> None:
    src = sys.argv[1]
    pull = {"s1": s1.series, "s2": s2.series}[src]
    f = fields()
    (OUT / src).mkdir(parents=True, exist_ok=True)
    earth_engine.init()
    frames = []
    for i in range(0, len(f), s1.CHUNK):
        p = OUT / src / f"{i:04d}.parquet"
        if not p.exists():
            pull(f.iloc[i : i + s1.CHUNK], START, END).to_parquet(p)
        frames.append(pd.read_parquet(p))
        print(f"  {src}: {min(i + s1.CHUNK, len(f))}/{len(f)} fields", flush=True)
    out = pd.concat(frames, ignore_index=True)
    out.to_parquet(OUT / f"{src}.parquet")
    print(f"wrote {OUT / f'{src}.parquet'}: {len(out)} rows, {out.field_id.nunique()} fields")


if __name__ == "__main__":
    sys.exit(main())
