"""Field registry: FTW polygons -> data/processed/fields.parquet.

One row per candidate field in Bolangir and Baleswar, with a stable `field_id` and the quality
columns the later stages need. Gates and columns follow D-016 (keep polygons >= 0.1 ha, keep the
pixel count as a quality flag) and D-020 (no land-cover filter; store the ESA WorldCover 2021
cropland fraction as a column instead).

Cropland fraction is computed locally: the two WorldCover tiles per district are read as remote
COGs over the district bbox (cached under data/raw/worldcover/), the polygons are rasterized onto
the same 10 m grid, and pixels are counted per field. That avoids ~550 Earth Engine chunks.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio import features
from rasterio.transform import from_origin
from rasterio.windows import from_bounds

MIN_AREA_M2 = 1000  # D-016: 0.1 ha
VINTAGE = 2025  # D-026: the FTW parquet stacks two annual layers; keep only one
WC_CROPLAND = 40  # ESA WorldCover class code
WC_RES = 1 / 12000  # WorldCover 10 m global grid
WC_URL = (
    "/vsicurl/https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/"
    "ESA_WorldCover_10m_2021_v200_{tile}_Map.tif"
)
BLOCK_DEG = 0.05  # ~5.5 km blocks, for the spatially blocked splits in EVALUATION.md


def field_id(district: str, wkb: bytes) -> str:
    """Stable id: district + a hash of the polygon geometry.

    Neither of the obvious keys works. FTW's own `id` is not unique (1902 ids appear twice in
    Baleswar with different geometries), and `representative_point()` collides for ~5k pairs of
    distinct neighbouring polygons because it snaps to a scan line. The geometry itself is unique
    once exact duplicates are dropped (`build`), and hashing it is stable across rebuilds.
    """
    return f"{district[:3]}-{hashlib.blake2s(wkb, digest_size=6).hexdigest()}"


def _tile_name(lon: int, lat: int) -> str:
    return f"{'N' if lat >= 0 else 'S'}{abs(lat):02d}{'E' if lon >= 0 else 'W'}{abs(lon):03d}"


def worldcover(bounds, cache: Path) -> tuple[np.ndarray, rasterio.Affine]:
    """WorldCover 2021 over `bounds`, mosaicked from the 3-degree tiles, snapped to its own grid."""
    if cache.exists():
        with rasterio.open(cache) as r:
            return r.read(1), r.transform
    xmin, ymin, xmax, ymax = bounds
    x0 = np.floor(xmin / WC_RES) * WC_RES
    y1 = np.ceil(ymax / WC_RES) * WC_RES
    w = int(np.ceil((xmax - x0) / WC_RES))
    h = int(np.ceil((y1 - ymin) / WC_RES))
    dst = from_origin(x0, y1, WC_RES, WC_RES)
    out = np.zeros((h, w), "uint8")
    for tlon in range(int(np.floor(xmin / 3)) * 3, int(np.floor(xmax / 3)) * 3 + 1, 3):
        for tlat in range(int(np.floor(ymin / 3)) * 3, int(np.floor(ymax / 3)) * 3 + 1, 3):
            with rasterio.open(WC_URL.format(tile=_tile_name(tlon, tlat))) as r:
                b = (max(xmin, tlon), max(ymin, tlat), min(xmax, tlon + 3), min(ymax, tlat + 3))
                src_w = from_bounds(*b, r.transform).round_offsets().round_lengths()
                a = r.read(1, window=src_w)
                d = from_bounds(*b, dst).round_offsets().round_lengths()
                out[
                    int(d.row_off) : int(d.row_off) + a.shape[0],
                    int(d.col_off) : int(d.col_off) + a.shape[1],
                ] = a
    cache.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        cache,
        "w",
        driver="GTiff",
        height=h,
        width=w,
        count=1,
        dtype="uint8",
        crs="EPSG:4326",
        transform=dst,
        compress="deflate",
    ) as f:
        f.write(out, 1)
    return out, dst


def cropland_fraction(
    geoms: gpd.GeoSeries, wc: np.ndarray, transform: rasterio.Affine
) -> pd.DataFrame:
    """Per-polygon 10 m pixel count and WorldCover cropland fraction.

    `wc_px` is the number of WorldCover pixels whose centre falls in the polygon, i.e. how many
    pixels the fraction was computed from -- not a usable count of Sentinel-1 pixels, which lives
    on a different grid and comes back with the S1 pull itself.

    shortcut: rasterizing gives each pixel to one polygon, so overlapping polygons steal pixels
    from each other. Safe only because `build` keeps a single FTW vintage (D-026), within which
    no two polygons overlap; re-check if that filter is ever dropped.
    """
    lab = features.rasterize(
        ((g, i) for i, g in enumerate(geoms, start=1)),
        out_shape=wc.shape,
        transform=transform,
        dtype="int32",
    )
    n = len(geoms) + 1
    total = np.bincount(lab.ravel(), minlength=n)[1:]
    crop = np.bincount(lab[wc == WC_CROPLAND].ravel(), minlength=n)[1:]
    with np.errstate(invalid="ignore"):
        frac = np.where(total > 0, crop / np.maximum(total, 1), np.nan)
    return pd.DataFrame({"wc_px": total, "wc_crop": frac.round(3)}, index=geoms.index)


def build(districts: list[str], raw_dir: Path, out: Path) -> gpd.GeoDataFrame:
    frames = []
    for d in districts:
        g = gpd.read_parquet(raw_dir / "ftw" / f"{d}.parquet")
        before = len(g), float(g.area_m2.sum())
        g = g[(g.area_m2 >= MIN_AREA_M2) & (g.determined.dt.year == VINTAGE)]
        wkb = g.geometry.to_wkb()
        n_dup = int(wkb.duplicated().sum())  # FTW ships a few hundred exact duplicates
        g = g[~wkb.duplicated()].reset_index(drop=True)
        pt = g.representative_point()  # a point guaranteed to lie inside the polygon
        g["lon"] = pt.x.round(6)
        g["lat"] = pt.y.round(6)
        g["field_id"] = [field_id(d, w) for w in g.geometry.to_wkb()]
        g["block"] = (
            (g.lat / BLOCK_DEG).astype(int).astype(str)
            + "_"
            + (g.lon / BLOCK_DEG).astype(int).astype(str)
        )
        g["compactness"] = (4 * np.pi * g.area_m2 / g.perimeter_m**2).round(3)
        wc, tr = worldcover(g.total_bounds, raw_dir / "worldcover" / f"{d}.tif")
        g = pd.concat([g, cropland_fraction(g.geometry, wc, tr)], axis=1)
        # polygons too small or thin to contain a pixel centre fall back to the pixel they sit on
        thin = g.wc_px == 0
        if thin.any():
            rows, cols = rasterio.transform.rowcol(tr, g.lon[thin], g.lat[thin])
            g.loc[thin, "wc_crop"] = (wc[rows, cols] == WC_CROPLAND).astype(float)
        g = g.rename(columns={"id": "ftw_id"}).drop(columns=["confidence", "determined"])
        print(
            f"{d}: {before[0]:,} polygons ({before[1] / 1e4:,.0f} ha) -> {len(g):,} "
            f">= {MIN_AREA_M2} m2, {VINTAGE} vintage ({g.area_m2.sum() / 1e4:,.0f} ha); "
            f"{n_dup} exact duplicate geometries dropped, "
            f"{int(thin.sum())} too thin for a pixel centre"
        )
        frames.append(g)
    reg = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs="EPSG:4326")
    dup = int(reg.field_id.duplicated().sum())
    assert dup == 0, f"{dup} duplicate field_ids"
    cols = [
        "field_id",
        "district",
        "ftw_id",
        "area_m2",
        "perimeter_m",
        "compactness",
        "lon",
        "lat",
        "block",
        "wc_px",
        "wc_crop",
        "geometry",
    ]
    reg = reg[cols]
    out.parent.mkdir(parents=True, exist_ok=True)
    reg.to_parquet(out)
    return reg


def stats(reg: gpd.GeoDataFrame) -> pd.DataFrame:
    """Per-district registry stats for the interim report."""
    g = reg.groupby("district")
    s = pd.DataFrame(
        {
            "fields": g.size(),
            "area_ha": (g.area_m2.sum() / 1e4).round(0),
            "ha_p25": (g.area_m2.quantile(0.25) / 1e4).round(3),
            "ha_median": (g.area_m2.median() / 1e4).round(3),
            "ha_p75": (g.area_m2.quantile(0.75) / 1e4).round(3),
            "px10m_est_median": (g.area_m2.median() / 100).round(0),
            "compactness_median": g.compactness.median().round(3),
            "wc_crop_median": g.wc_crop.median().round(2),
            "wc_crop_lt50_pct": (g.wc_crop.apply(lambda s: s.lt(0.5).mean()) * 100).round(1),
            "blocks_5km": g.block.nunique(),
            "fields_per_block_median": g.apply(
                lambda d: d.groupby("block").size().median(), include_groups=False
            ),
            "wc_px_zero_pct": (g.wc_px.apply(lambda s: s.eq(0).mean()) * 100).round(1),
        }
    )
    return s.T
