"""Read the SICKLE release: exact harvest labels and per-plot Sentinel-1 series.

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
