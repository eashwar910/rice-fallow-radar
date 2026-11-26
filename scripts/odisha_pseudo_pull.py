"""P3 adaptation: S1 + S2 season series for unlabelled Odisha fields, the pseudo-label pool.

Which fields: step 1's frozen registry sample (`odisha_transplant_spread.sample`, 2 x 2,000,
seed 20261126) filtered to those whose cached Jun-Sep VH shows D-031's flood-then-canopy
signature at -20 dB (likely kharif rice), then **every 0.05 deg block holding any hand-labelled
field (free or locked, any status) is removed**, so no pseudo-labelled field shares a block with
a field it could be scored against. `N_PER_DISTRICT` drawn at random from what is left.

The pool is selected on visible flooding, so it under-represents direct-seeded rice (~53% of
Odisha's): pseudo-labels are an easy-field sample, the same bias D-021 discloses.

Resumable per chunk under data/interim/odisha_pseudo/. Usage:
    uv run python scripts/odisha_pseudo_pull.py
Writes data/interim/odisha_pseudo/{fields,s1,s2}.parquet.
"""

import sys
from pathlib import Path

import pandas as pd
from odisha_sensor_pull import END, START
from odisha_transplant_spread import CACHE, THRESHOLD, flood_dates, sample

from rice_fallow_radar.ingest import earth_engine, s1, s2

OUT = Path("data/interim/odisha_pseudo")
N_PER_DISTRICT, SEED = 300, 20261127


def pool():
    reg = sample(2000)
    cached = pd.concat(pd.read_parquet(p) for p in sorted(CACHE.glob("n2000_*.parquet")))
    desc = cached[cached.orbit_pass == "DESCENDING"]
    flooded = flood_dates(desc, THRESHOLD).dropna().index
    labels = pd.read_parquet("data/processed/odisha_labels.parquet")
    f = reg[reg.field_id.isin(flooded) & ~reg.block.isin(labels.block)]
    assert not set(f.field_id) & set(labels.field_id), "a labelled field reached the pool"
    print(f"flooded {len(flooded)} of {len(reg)}; {len(f)} outside labelled blocks")
    f = pd.concat(
        g.sample(n=min(N_PER_DISTRICT, len(g)), random_state=SEED) for _, g in f.groupby("district")
    )
    return f.sort_values("field_id").reset_index(drop=True)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    f = pool()
    f.drop(columns="geometry").to_parquet(OUT / "fields.parquet")
    earth_engine.init()
    for src, pull in (("s1", s1.series), ("s2", s2.series)):
        (OUT / src).mkdir(exist_ok=True)
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
