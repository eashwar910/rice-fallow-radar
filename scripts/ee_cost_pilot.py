"""P0 step 5: measure Earth Engine EECU cost of per-field exports on one 5 km block.

Exports to the service account's Drive: only the batch task's EECU report matters, and the
project asset root is not writable yet (P0 step 5). One-off; results go in docs/DATA.md.
"""

import json
import sys

import ee
import geopandas as gpd
from shapely.geometry import box

from rice_fallow_radar.ingest.earth_engine import init

BBOX = (83.43, 20.97, 83.475, 21.015)  # median-density 5 km cell in Bolangir
START, END = "2025-06-01", "2026-02-01"


def fields() -> ee.FeatureCollection:
    g = gpd.read_parquet("data/raw/ftw/bolangir.parquet")
    g = g[(g.area_m2 >= 1000) & g.representative_point().within(box(*BBOX))]
    gj = json.loads(g[["id", "geometry"]].to_json())
    return ee.FeatureCollection(gj), len(g)


def per_image(fc, img, scale, bands):
    red = ee.Reducer.mean().combine(ee.Reducer.count(), sharedInputs=True)
    date = img.date().format("YYYY-MM-dd'T'HH:mm")
    out = img.select(bands).reduceRegions(collection=fc, reducer=red, scale=scale, tileScale=2)
    return out.map(lambda f: f.setGeometry(None).set("t", date))


def main():
    init()
    fc, n = fields()
    print("fields:", n)
    aoi = ee.Geometry.Rectangle(BBOX)
    s1 = (
        ee.ImageCollection("COPERNICUS/S1_GRD")
        .filterBounds(aoi)
        .filterDate(START, END)
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
    )
    chirps = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY").filterDate(START, END)
    print("S1 scenes:", s1.size().getInfo(), "CHIRPS days:", chirps.size().getInfo())
    jobs = {
        "s1": s1.map(lambda i: per_image(fc, i, 10, ["VV", "VH", "angle"])).flatten(),
        "chirps": chirps.map(lambda i: per_image(fc, i, 5566, ["precipitation"])).flatten(),
    }
    for name, table in jobs.items():
        t = ee.batch.Export.table.toDrive(table, f"pilot_{name}", "p0_pilot", f"pilot_{name}")
        t.start()
        print(name, t.id)


if __name__ == "__main__":
    sys.exit(main())
