"""Sentinel-1 per-field series from Earth Engine, for the Odisha side of M2 (P3).

Same product and the same per-field statistic as the SICKLE series (`ingest.sickle.s1_series`):
`COPERNICUS/S1_GRD`, IW mode, VV+VH, values already in dB, **mean of the dB pixels inside the
field** plus a valid-pixel count. Matching the statistic matters more than choosing the best
one: a linear-power mean on one side and a dB mean on the other would be a domain shift we
introduced ourselves.

Unlike SICKLE, orbit direction and relative orbit are kept per row (DATA.md §Sentinel-1: incidence
angle moves backscatter, and Odisha fields see more than one track). Pulled through
`computeFeatures` in chunks of fields (D-017), and refused past the D-019 cut-off.
"""

from __future__ import annotations

import json

import ee
import geopandas as gpd
import pandas as pd

from ..eval import availability
from .s2 import per_image

COLLECTION = "COPERNICUS/S1_GRD"
BANDS = ["VV", "VH", "angle"]
CHUNK = 40  # fields per computeFeatures call (D-017)


def collection(aoi: ee.Geometry, start: str, end: str) -> ee.ImageCollection:
    """IW, dual-pol VV+VH scenes over `aoi` in `[start, end)`."""
    return (
        ee.ImageCollection(COLLECTION)
        .filterBounds(aoi)
        .filterDate(start, end)
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
    )


def _with_orbit(fc: ee.FeatureCollection, img: ee.Image) -> ee.FeatureCollection:
    out = per_image(fc, img, BANDS)
    return out.map(
        lambda f: f.set(
            "orbit_pass",
            img.get("orbitProperties_pass"),
            "rel_orbit",
            img.get("relativeOrbitNumber_start"),
        )
    )


def series(
    fields: gpd.GeoDataFrame, start: str, end: str, replay: bool = False, chunk: int = CHUNK
) -> pd.DataFrame:
    """One row per (field, scene): `vv_db`, `vh_db`, `angle`, `n_valid`, orbit, date.

    `fields` needs `field_id` and a geometry in EPSG:4326. Call `ingest.earth_engine.init()`
    first. Rows come back in the SICKLE series' column names so `features.sickle_m1._s1_row`
    can be reused on them.
    """
    availability.check_cutoff([start, pd.Timestamp(end) - pd.Timedelta(days=1)], replay=replay)
    frames = []
    for i in range(0, len(fields), chunk):
        sub = fields.iloc[i : i + chunk]
        fc = ee.FeatureCollection(json.loads(sub[["field_id", "geometry"]].to_json()))
        col = collection(ee.Geometry.Rectangle(list(sub.total_bounds)), start, end)
        table = col.map(lambda img, fc=fc: _with_orbit(fc, img)).flatten()
        df = ee.data.computeFeatures({"expression": table, "fileFormat": "PANDAS_DATAFRAME"})
        frames.append(df.drop(columns=[c for c in ("geo",) if c in df]))
    s = pd.concat(frames, ignore_index=True).rename(
        columns={
            "VV_mean": "vv_db",
            "VH_mean": "vh_db",
            "angle_mean": "angle",
            "VH_count": "n_valid",
        }
    )
    s["date"] = pd.to_datetime(s.date)
    s = s.dropna(subset=["vh_db"])
    keep = ["field_id", "date", "scene", "orbit_pass", "rel_orbit", "vv_db", "vh_db"]
    return s[keep + ["angle", "n_valid"]].sort_values(["field_id", "date"], ignore_index=True)
