"""D-023: regional weather for the SICKLE plots, one series per Sentinel-2 MGRS tile.

SICKLE withholds plot coordinates and strips the mask georeferencing, so weather cannot be
sampled per plot. But the S2 patch filenames name the MGRS tile each plot's patch came from, and
the exact-label samples fall in just four tiles (T44PKS/PKT/PLS/PLT, the Cauvery basin in Tamil
Nadu, 78.6-80.2E 9.9-11.8N). A 110 km tile localises nothing about an individual plot, so this
refines D-023 option (a) -- regional weather, at tile rather than whole-study-area granularity --
without touching the plot-location question D-023 ruled out.

Usage: uv run python scripts/sickle_weather_pull.py
Writes data/interim/sickle_weather.parquet (one row per tile and day).
"""

import sys
from pathlib import Path

import ee
import pandas as pd

from rice_fallow_radar.ingest import sickle
from rice_fallow_radar.ingest.earth_engine import init

OUT = Path("data/interim/sickle_weather.parquet")
START, END = "2017-10-01", "2021-07-01"  # covers every SICKLE season with a margin
ERA5_BANDS = [
    "temperature_2m",
    "temperature_2m_min",
    "temperature_2m_max",
    "total_evaporation_sum",
    "potential_evaporation_sum",
    "volumetric_soil_water_layer_1",
]


def tile_regions(tiles: list[str]) -> ee.FeatureCollection:
    """One feature per MGRS tile, geometry = that tile's S2 footprint bounds."""
    feats = []
    for t in tiles:
        img = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filter(ee.Filter.eq("MGRS_TILE", t.lstrip("T")))
            .first()
        )
        feats.append(ee.Feature(ee.Feature(img).geometry().bounds(), {"tile": t}))
    return ee.FeatureCollection(feats)


def daily(fc: ee.FeatureCollection, col: ee.ImageCollection, bands, scale: int) -> pd.DataFrame:
    def per_image(img):
        out = img.select(bands).reduceRegions(fc, ee.Reducer.mean(), scale=scale)
        d = img.date().format("YYYY-MM-dd")
        return out.map(lambda f: f.setGeometry(None).set("date", d))

    table = col.map(per_image).flatten()
    df = ee.data.computeFeatures({"expression": table, "fileFormat": "PANDAS_DATAFRAME"})
    df = df.drop(columns=[c for c in ("geo",) if c in df])
    # a single-band reduceRegions names its output "mean", not after the band
    return df.rename(columns={"mean": bands[0]}) if len(bands) == 1 else df


def main() -> None:
    init()
    tiles = sorted(sickle.sample_tiles().explode().unique())
    print("tiles:", tiles)
    fc = tile_regions(tiles)
    chirps = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY").filterDate(START, END)
    era5 = ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR").filterDate(START, END)
    out = None
    for name, col, bands, scale in [
        ("chirps", chirps, ["precipitation"], 5566),
        ("era5", era5, ERA5_BANDS, 11132),
    ]:
        # a year at a time: one call over ~1300 images times 4 regions is slow and fragile
        frames = []
        for y in range(2017, 2022):
            sub = col.filterDate(f"{y}-01-01", f"{y + 1}-01-01")
            if sub.size().getInfo() == 0:
                continue
            frames.append(daily(fc, sub, bands, scale))
            print(f"  {name} {y}: {len(frames[-1])} rows", flush=True)
        df = pd.concat(frames, ignore_index=True)
        out = df if out is None else out.merge(df, on=["tile", "date"], how="outer")
    out["date"] = pd.to_datetime(out.date)
    out = out.sort_values(["tile", "date"], ignore_index=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(OUT)
    print(
        f"\nwrote {OUT}: {len(out)} rows, {out.tile.nunique()} tiles, "
        f"{out.date.min():%Y-%m-%d}..{out.date.max():%Y-%m-%d}"
    )
    print(out.describe().round(2).T.to_string())


if __name__ == "__main__":
    sys.exit(main())
