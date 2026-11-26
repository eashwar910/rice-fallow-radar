"""Sentinel-2 per-field series and chips from Earth Engine (P1b labelling aid).

Cloud screening uses Cloud Score+ (`GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED`, Pasquarella et
al. 2023), joined to each S2 scene by index: `cs_cdf` is the probability a pixel is clear, so
`1 - cs_cdf` averaged over a field is how cloudy that field looked in that scene.
"""

from __future__ import annotations

import json

import ee
import pandas as pd

from ..eval import availability

S2 = "COPERNICUS/S2_SR_HARMONIZED"
CS = "GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED"
# Stretch tuned on the P1b pilot (19 Nov 2026): 300-2800 rendered standing rice almost black
# and 100-1600 saturated harvested fields to white. 150-2500 keeps both ends readable.
VIS = {"bands": ["B4", "B3", "B2"], "min": 150, "max": 2500}
CHIP_PX = 260


def collection(aoi: ee.Geometry, start: str, end: str) -> ee.ImageCollection:
    """S2 L2A over `aoi`, each image carrying an added `ndvi` and `cloud` band."""
    cs = ee.ImageCollection(CS)
    col = ee.ImageCollection(S2).filterBounds(aoi).filterDate(start, end)
    col = ee.ImageCollection(
        ee.Join.saveFirst("cs").apply(
            col, cs, ee.Filter.equals(leftField="system:index", rightField="system:index")
        )
    )

    def add(img):
        clear = ee.Image(img.get("cs")).select("cs_cdf")
        return img.addBands(
            [
                img.normalizedDifference(["B8", "B4"]).rename("ndvi"),
                ee.Image(1).subtract(clear).rename("cloud"),
            ]
        )

    return col.map(add)


def per_image(fc: ee.FeatureCollection, img: ee.Image, bands: list[str], scale: int = 10):
    """Mean + valid-pixel count of `bands` per feature, tagged with the image date."""
    red = ee.Reducer.mean().combine(ee.Reducer.count(), sharedInputs=True)
    out = img.select(bands).reduceRegions(collection=fc, reducer=red, scale=scale, tileScale=4)
    date = img.date().format("YYYY-MM-dd")
    sid = img.get("system:index")
    return out.map(lambda f: f.setGeometry(None).set("date", date, "scene", sid))


CS_CLEAR = 0.6  # Cloud Score+ cs_cdf at or above this: clear pixel (suggested cut)
CLEAR_FRAC = 0.5  # same scene-level rule as SICKLE (`ingest.sickle.CLEAR_FRAC`)


def _indices(img: ee.Image) -> ee.Image:
    """NDVI/NDWI/MNDWI on clear pixels only, plus a 1-band `px` footprint to count pixels."""
    clear = ee.Image(img.get("cs")).select("cs_cdf").gte(CS_CLEAR)
    idx = ee.Image.cat(
        img.normalizedDifference(["B8", "B4"]).rename("ndvi"),
        img.normalizedDifference(["B3", "B8"]).rename("ndwi"),
        img.normalizedDifference(["B3", "B11"]).rename("mndwi"),
    ).updateMask(clear)
    return idx.addBands(img.select("B4").gt(-1).rename("px")).copyProperties(
        img, ["system:time_start", "system:index"]
    )


def series(fields, start: str, end: str, replay: bool = False, chunk: int = 40):
    """One row per (field, scene) in SICKLE's S2 column names (`ingest.sickle.s2_series`).

    Indices are field means over Cloud Score+-clear pixels; `n_clear` counts those, `n_px` the
    whole footprint, and `clear` applies SICKLE's own scene rule (>= half the field clear). Cloud
    masking differs (Cloud Score+ here, SCL + MSK_CLDPRB in SICKLE), which is a disclosed shift.
    """
    availability.check_cutoff([start, pd.Timestamp(end) - pd.Timedelta(days=1)], replay=replay)
    frames = []
    for i in range(0, len(fields), chunk):
        sub = fields.iloc[i : i + chunk]
        fc = ee.FeatureCollection(json.loads(sub[["field_id", "geometry"]].to_json()))
        col = collection(ee.Geometry.Rectangle(list(sub.total_bounds)), start, end).map(_indices)
        table = col.map(
            lambda img, fc=fc: per_image(fc, img, ["ndvi", "ndwi", "mndwi", "px"])
        ).flatten()
        df = ee.data.computeFeatures({"expression": table, "fileFormat": "PANDAS_DATAFRAME"})
        frames.append(df.drop(columns=[c for c in ("geo",) if c in df]))
    s = pd.concat(frames, ignore_index=True)
    s = s.rename(columns={f"{b}_mean": b for b in ("ndvi", "ndwi", "mndwi")})
    s["date"] = pd.to_datetime(s.date)
    s["n_px"], s["n_clear"] = s.px_count, s.ndvi_count
    s = s[s.n_px > 0]  # scenes from MGRS tiles that do not cover the field
    s["clear"] = (s.n_px > 0) & (s.n_clear >= CLEAR_FRAC * s.n_px)
    keep = ["field_id", "date", "scene", "ndvi", "ndwi", "mndwi", "n_px", "n_clear", "clear"]
    return s[keep].sort_values(["field_id", "date"], ignore_index=True)


def chip_url(scenes: list[str], win: ee.Geometry, outline: ee.Geometry, px: int = CHIP_PX) -> str:
    """True-colour thumbnail of `win` with `outline` drawn on top.

    `scenes` are all the S2 scene ids of one date that touch the field: fields on an MGRS tile
    boundary need the same-day scenes mosaicked, or half the chip comes back blank white and
    reads as bare soil.
    """
    img = ee.ImageCollection([ee.Image(f"{S2}/{s}") for s in scenes]).mosaic()
    edge = (
        ee.FeatureCollection([ee.Feature(outline)])
        .style(color="FF00FF", fillColor="00000000", width=1)  # magenta: absent from farmland
        .visualize()
    )
    return (
        img.visualize(**VIS)
        .blend(edge)
        .getThumbURL({"region": win, "dimensions": px, "format": "png", "crs": "EPSG:3857"})
    )
