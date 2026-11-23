"""Download the two CSISA rice surveys and build data/processed/csisa_rice.parquet.

Usage: uv run python scripts/csisa_ingest.py [--force]

Raw files land in data/raw/csisa/ (gitignored, and they carry no licence -- see DATA.md §CSISA,
so neither the raw files nor row-level derivatives leave this machine).
"""

import sys
from pathlib import Path

import pandas as pd
import yaml

from rice_fallow_radar.ingest import csisa

RAW = Path("data/raw/csisa")
DEST = Path("data/processed/csisa_rice.parquet")
CFG = Path("configs/districts.yaml")


def main() -> None:
    cutoff = pd.Timestamp(yaml.safe_load(CFG.read_text())["data_cutoff"])
    paths = csisa.download(RAW, force="--force" in sys.argv)
    print(f"{len(paths)} files in {RAW}, all md5-verified")

    df = csisa.build(RAW, DEST, cutoff=cutoff)
    print(f"\nwrote {DEST} ({len(df)} rows, {df.shape[1]} cols)")
    print("\nrows per year x state (top states)")
    print(pd.crosstab(df.state, df.year).sort_values(2018, ascending=False).head(10))
    od = df[df.state == "Odisha"]
    print(f"\nOdisha {len(od)} rows; districts by year")
    print(pd.crosstab(od.district, od.year))
    print(
        f"\ntransplanted: {df.transplanted.mean():.0%} overall, {od.transplanted.mean():.0%} Odisha"
    )
    print(f"coordinate precision: {df.groupby('year').coord_dp.first().to_dict()} decimal places")


if __name__ == "__main__":
    main()
