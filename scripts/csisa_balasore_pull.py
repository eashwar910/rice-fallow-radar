"""S1 + S2 series for the CSISA Balasore 2018 secondary set (EVALUATION.md §Secondary set).

Unit = the 3-dp cell (rule 1), pulled as a 110 m box (+/- 0.0005 deg) around the reported
coordinate, because there are no 2018 FTW polygons. A box mixes neighbouring fields: a reason
the set is secondary. Cells come from `odisha_calendar.kharif_transplanted` (rule 5's filter).
Window: the 2018 kharif season, 120 days of lookback before the first issue date (1 Sep).

Usage:
    uv run python scripts/csisa_balasore_pull.py
Writes data/interim/csisa_balasore/{cells,s1,s2}.parquet.
"""

import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import box

from rice_fallow_radar.features import odisha_calendar as OC
from rice_fallow_radar.ingest import earth_engine, s1, s2

OUT = Path("data/interim/csisa_balasore")
START, END = "2018-05-01", "2019-02-20"
HALF = 0.0005  # deg: half of a 3-dp cell


def cells() -> gpd.GeoDataFrame:
    c = OC.kharif_transplanted(pd.read_parquet("data/processed/csisa_rice.parquet"), "Balasore")
    c = c[c.year == 2018]
    cell = c[["lat", "lon"]].drop_duplicates().reset_index(drop=True)
    cell["field_id"] = [
        f"csisa-{la:.3f}-{lo:.3f}" for la, lo in zip(cell.lat, cell.lon, strict=True)
    ]
    geom = [
        box(lo - HALF, la - HALF, lo + HALF, la + HALF)
        for la, lo in zip(cell.lat, cell.lon, strict=True)
    ]
    return gpd.GeoDataFrame(cell, geometry=geom, crs="EPSG:4326")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    f = cells()
    f.drop(columns="geometry").to_parquet(OUT / "cells.parquet")
    earth_engine.init()
    for src, pull in (("s1", s1.series), ("s2", s2.series)):
        p = OUT / f"{src}.parquet"
        if not p.exists():
            pull(f, START, END).to_parquet(p)
        out = pd.read_parquet(p)
        print(f"{src}: {len(out)} rows, {out.field_id.nunique()} of {len(f)} cells")


if __name__ == "__main__":
    sys.exit(main())
