"""Read the SICKLE release: exact harvest labels and per-plot Sentinel-1/-2 series.

Shared by scripts/sickle_extract_check.py and the M1 feature table (P2).

Patch/mask geometry (checked 19 Nov 2026, see docs/DATA.md §SICKLE): the georeferencing is
stripped from everything, so patch and mask can only be aligned by array index. Scene shapes
wobble by a pixel (32-34 px) around the 33x33 mask, so each scene is cropped to the top-left
overlap with its mask; scenes more than 1 px off are edge-clipped slices and are dropped.
"""

from __future__ import annotations

import glob
import os
import re

import numpy as np
import pandas as pd
import rasterio

ROOT = "sickle_dataset"
SHAPE_TOL = 1  # px; beyond this a scene is an edge-clipped slice, not an off-by-one
# S1 scene id: ..._1SDV_<start>T<time>_... -> start date at offset 17
_DATE = re.compile(r"_1S[DS]V_(\d{8})T")
# S2 scene id: <sense>T<time>_<proc>T<time>_<tile>
_S2_DATE = re.compile(r"^(\d{8})T")
# SCL classes kept as clear: 4 vegetation, 5 bare, 6 water, 7 unclassified. Dropped: no-data,
# saturated, shadow, cloud shadow, cloud med/high, cirrus, snow.
CLEAR_SCL = (4, 5, 6, 7)
CLDPRB_MAX = 40  # % from MSK_CLDPRB; above this a pixel is called cloudy even if SCL says clear
CLEAR_FRAC = 0.5  # a scene counts as clear when this share of the plot's pixels survive masking


def exact_labels(root: str = ROOT) -> pd.DataFrame:
    """The 319 paddy seasons with an observed harvest date (yield > 0; D-024)."""
    df = pd.read_csv(f"{root}/sickle_dataset_tabular.csv")
    ex = df[(df.CROP == "Paddy") & (df.YIELD > 0)].copy()
    ex["harvest"] = pd.to_datetime(ex.HARVESTING_DATE, format="%m/%d/%Y")
    ex["sowing"] = pd.to_datetime(ex.SOWING_DATE, format="%m/%d/%Y")
    ex["transplanting"] = pd.to_datetime(ex.TRANSPLANTING_DATE, format="%m/%d/%Y")
    return ex.reset_index(drop=True)


def s1_series(root: str = ROOT, labels: pd.DataFrame | None = None) -> pd.DataFrame:
    """Per-plot Sentinel-1 means, one row per (sample, scene date).

    Only pixels with `mask == PLOT_ID` count (patches contain neighbouring plots), and zeros
    are no-data in both the backscatter and the angle band.
    """
    ex = exact_labels(root) if labels is None else labels
    rows = []
    for r in ex.itertuples():
        with rasterio.open(f"{root}/masks/10m/{r.UNIQUE_ID}.tif") as m:
            own_full = m.read(1) == r.PLOT_ID
        for f in sorted(glob.glob(f"{root}/images/S1/npy/{r.UNIQUE_ID}/*.npz")):
            z = np.load(f)
            vv, vh = z["VV"], z["VH"]
            dr = vh.shape[0] - own_full.shape[0]
            dc = vh.shape[1] - own_full.shape[1]
            clipped = abs(dr) > SHAPE_TOL or abs(dc) > SHAPE_TOL
            rr = min(vh.shape[0], own_full.shape[0])
            cc = min(vh.shape[1], own_full.shape[1])
            own = own_full[:rr, :cc]
            valid = own & (vv[:rr, :cc] != 0) & (vh[:rr, :cc] != 0)
            angle = float(np.ravel(z["angle"])[0])
            rows.append(
                dict(
                    unique_id=r.UNIQUE_ID,
                    plot_id=r.PLOT_ID,
                    season=r.STANDARD_SEASON,
                    year=r.YEAR,
                    date=pd.Timestamp(_DATE.search(os.path.basename(f)).group(1)),
                    scene=os.path.basename(f)[:-4],
                    vv_db=float(vv[:rr, :cc][valid].mean()) if valid.any() else np.nan,
                    vh_db=float(vh[:rr, :cc][valid].mean()) if valid.any() else np.nan,
                    angle=angle if angle > 0 else np.nan,
                    n_px=int(own.sum()),
                    n_valid=int(valid.sum()),
                    shape_off=max(abs(dr), abs(dc)),
                    edge_clipped=clipped,
                )
            )
    s = pd.DataFrame(rows).sort_values(["unique_id", "date"], ignore_index=True)
    s["harvest"] = s.unique_id.map(ex.set_index("UNIQUE_ID").harvest)
    s["lead_days"] = (s.harvest - s.date).dt.days  # >0 before harvest
    return s


def _index_mean(a: np.ndarray, b: np.ndarray, m: np.ndarray) -> float:
    """Mean of the normalised difference (a-b)/(a+b) over mask `m`; zeros are no-data."""
    m = m & (a > 0) & (b > 0)
    return float(((a[m] - b[m]) / (a[m] + b[m])).mean()) if m.any() else np.nan


def s2_series(root: str = ROOT, labels: pd.DataFrame | None = None) -> pd.DataFrame:
    """Per-plot Sentinel-2 indices, one row per (sample, scene file).

    Same index-only mask alignment as `s1_series`. The 20 m bands (B11, SCL, MSK_CLDPRB) are
    nearest-neighbour upsampled 2x onto the 10 m grid before cropping, so every array shares the
    10 m mask's top-left origin. A pixel counts only if it belongs to the plot, is cloud-free by
    SCL and MSK_CLDPRB, and is non-zero in both bands of the index being computed.
    """
    ex = exact_labels(root) if labels is None else labels
    rows = []
    for r in ex.itertuples():
        with rasterio.open(f"{root}/masks/10m/{r.UNIQUE_ID}.tif") as m:
            own_full = m.read(1) == r.PLOT_ID
        for f in sorted(glob.glob(f"{root}/images/S2/npy/{r.UNIQUE_ID}/*.npz")):
            z = np.load(f)
            b3, b4, b8 = z["B3"], z["B4"], z["B8"]
            up = [np.repeat(np.repeat(z[k], 2, 0), 2, 1) for k in ("B11", "SCL", "MSK_CLDPRB")]
            dr = b4.shape[0] - own_full.shape[0]
            dc = b4.shape[1] - own_full.shape[1]
            clipped = abs(dr) > SHAPE_TOL or abs(dc) > SHAPE_TOL
            rr = min(own_full.shape[0], *(a.shape[0] for a in [b3, b4, b8, *up]))
            cc = min(own_full.shape[1], *(a.shape[1] for a in [b3, b4, b8, *up]))
            own, b3, b4, b8, b11, scl, cldprb = [a[:rr, :cc] for a in (own_full, b3, b4, b8, *up)]
            clear = own & np.isin(scl.astype(int), CLEAR_SCL) & (cldprb < CLDPRB_MAX)
            n_px, n_clear = int(own.sum()), int(clear.sum())
            rows.append(
                dict(
                    unique_id=r.UNIQUE_ID,
                    plot_id=r.PLOT_ID,
                    season=r.STANDARD_SEASON,
                    year=r.YEAR,
                    date=pd.Timestamp(_S2_DATE.match(os.path.basename(f)).group(1)),
                    scene=os.path.basename(f)[:-4],
                    tile=os.path.basename(f).split("_")[-1][:-4],
                    ndvi=_index_mean(b8, b4, clear),
                    ndwi=_index_mean(b3, b8, clear),
                    mndwi=_index_mean(b3, b11, clear),
                    n_px=n_px,
                    n_clear=n_clear,
                    cloud_frac=1 - n_clear / n_px if n_px else np.nan,
                    clear=n_px > 0 and n_clear >= CLEAR_FRAC * n_px,
                    shape_off=max(abs(dr), abs(dc)),
                    edge_clipped=clipped,
                )
            )
    s = pd.DataFrame(rows).sort_values(["unique_id", "date"], ignore_index=True)
    s["harvest"] = s.unique_id.map(ex.set_index("UNIQUE_ID").harvest)
    s["lead_days"] = (s.harvest - s.date).dt.days  # >0 before harvest
    return s


def best_per_date(s: pd.DataFrame) -> pd.DataFrame:
    """One S2 row per (sample, date): 121 of 305 samples sit in two MGRS tiles, so overlapping
    tiles ship the same acquisition twice. Keep the less-clouded copy (they agree to a median
    0.004 NDVI, max 0.19). Call this before building features, or those samples get double weight.
    """
    return (
        s.sort_values(["edge_clipped", "n_clear"], ascending=[True, False])
        .drop_duplicates(["unique_id", "date"])
        .sort_values(["unique_id", "date"], ignore_index=True)
    )


def sample_tiles(root: str = ROOT, labels: pd.DataFrame | None = None) -> pd.Series:
    """Sentinel-2 MGRS tile(s) each exact sample's patch came from, indexed by UNIQUE_ID.

    The only location information SICKLE ships. Used to attach regional weather (D-023).
    """
    ex = exact_labels(root) if labels is None else labels
    return pd.Series(
        {
            r.UNIQUE_ID: sorted(
                {
                    "T" + os.path.basename(f).split("_")[-1][1:-4]
                    for f in glob.glob(f"{root}/images/S2/npy/{r.UNIQUE_ID}/*.npz")
                }
            )
            for r in ex.itertuples()
        },
        name="tiles",
    )
