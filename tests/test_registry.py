"""Registry unit tests: the pixel bookkeeping in fields.cropland_fraction is easy to get
silently wrong (grid offsets, label indices), so it is checked against a hand-made raster."""

import geopandas as gpd
import numpy as np
from rasterio.transform import from_origin
from shapely.geometry import box

from rice_fallow_radar.registry import fields

RES = fields.WC_RES


def test_cropland_fraction_counts_pixels_and_classes():
    # 4x4 pixel grid; left half cropland (40), right half built (50)
    wc = np.where(np.arange(4) < 2, fields.WC_CROPLAND, 50).astype("uint8")
    wc = np.tile(wc, (4, 1))
    tr = from_origin(80.0, 20.0, RES, RES)
    geoms = gpd.GeoSeries(
        [
            box(80.0, 20.0 - 2 * RES, 80.0 + 2 * RES, 20.0),  # 2x2, all cropland
            box(80.0 + 2 * RES, 20.0 - 2 * RES, 80.0 + 4 * RES, 20.0),  # 2x2, no cropland
            box(80.0 + RES, 20.0 - 4 * RES, 80.0 + 3 * RES, 20.0 - 2 * RES),  # 2x2, half each
        ]
    )
    out = fields.cropland_fraction(geoms, wc, tr)
    assert out.wc_px.tolist() == [4, 4, 4]
    assert out.wc_crop.tolist() == [1.0, 0.0, 0.5]


def test_cropland_fraction_marks_subpixel_polygons_nan():
    wc = np.full((2, 2), fields.WC_CROPLAND, "uint8")
    tr = from_origin(80.0, 20.0, RES, RES)
    tiny = gpd.GeoSeries([box(80.0, 20.0 - RES / 10, 80.0 + RES / 10, 20.0)])
    out = fields.cropland_fraction(tiny, wc, tr)
    assert out.wc_px.iloc[0] == 0 and np.isnan(out.wc_crop.iloc[0])


def test_field_id_is_stable_and_geometry_specific():
    a, b = box(80, 20, 80.001, 20.001), box(80, 20, 80.002, 20.001)
    assert fields.field_id("bolangir", a.wkb) == fields.field_id("bolangir", a.wkb)
    assert fields.field_id("bolangir", a.wkb) != fields.field_id("bolangir", b.wkb)
    assert fields.field_id("bolangir", a.wkb) != fields.field_id("baleswar", a.wkb)
    assert fields.field_id("bolangir", a.wkb).startswith("bol-")


def test_tile_name():
    assert fields._tile_name(81, 18) == "N18E081"
    assert fields._tile_name(87, 21) == "N21E087"
