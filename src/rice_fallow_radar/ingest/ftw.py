"""Fields of The World (FTW) global field-boundary predictions for a study district.

Source: PRUE-model polygons from Sentinel-2, CC-BY-4.0, one GeoParquet per Indian state on
Source Cooperative. We read only row groups overlapping the district bbox, then clip to the
district boundary (FAO GAUL 2025, via Earth Engine).
"""

from pathlib import Path

import duckdb
import ee
import geopandas as gpd
from shapely.geometry import shape

FTW_URL = (
    "https://data.source.coop/ftw/global-data/predictions/vectors/alpha/"
    "results-by-admin-conf/admin:country_code=IN/IN_{state}.parquet"
)


def district_geometry(cfg: dict, key: str):
    b, d = cfg["boundaries"], cfg["districts"][key]
    fc = ee.FeatureCollection(b["gee_asset"]).filter(
        ee.Filter.eq(b["district_field"], d["gaul_name"])
    )
    return shape(fc.geometry().getInfo())


def fetch_district(cfg: dict, key: str, out_dir: Path, state: str = "OD") -> Path:
    geom = district_geometry(cfg, key)
    xmin, ymin, xmax, ymax = geom.bounds
    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial; INSTALL httpfs; LOAD httpfs;")
    df = con.sql(
        f"""
        SELECT id, ST_AsWKB(geometry) AS wkb, "metrics:area" AS area_m2,
               "metrics:perimeter" AS perimeter_m, confidence,
               "determination:datetime" AS determined
        FROM read_parquet('{FTW_URL.format(state=state)}')
        WHERE bbox.xmin <= {xmax} AND bbox.xmax >= {xmin}
          AND bbox.ymin <= {ymax} AND bbox.ymax >= {ymin}
        """
    ).df()
    gdf = gpd.GeoDataFrame(
        df.drop(columns="wkb"), geometry=gpd.GeoSeries.from_wkb(df.wkb.map(bytes)), crs=4326
    )
    gdf = gdf[gdf.representative_point().within(geom)].reset_index(drop=True)
    gdf["district"] = key
    out = out_dir / f"{key}.parquet"
    gdf.to_parquet(out)
    return out
