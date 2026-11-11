"""Profile the SICKLE release (P0 step 7). Prints the numbers quoted in docs/DATA.md §SICKLE.

Usage: uv run python scripts/sickle_profile.py [sickle_dataset] [runs/wacv_2024]
"""

import glob
import json
import os
import sys

import numpy as np
import pandas as pd
import rasterio

root = sys.argv[1] if len(sys.argv) > 1 else "sickle_dataset"
runs = sys.argv[2] if len(sys.argv) > 2 else "runs/wacv_2024"
SEASON_START = {
    "jan": 1,
    "feb": 2,
    "may": 5,
    "jun": 6,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

df = pd.read_csv(f"{root}/sickle_dataset_tabular.csv")
print("== tabular ==")
print(f"samples {len(df)}, plots {df.PLOT_ID.nunique()}, years {sorted(df.YEAR.dropna().unique())}")
print("split", df.SPLIT.value_counts().to_dict())
print(
    "test rows with any label:",
    int(
        df[df.SPLIT == "test"]
        .drop(columns=["UNIQUE_ID", "STANDARD_SEASON", "YEAR", "SPLIT"])
        .notna()
        .any(axis=1)
        .sum()
    ),
)
paddy = df[df.CROP == "Paddy"].copy()
print(f"paddy samples {len(paddy)} from {paddy.PLOT_ID.nunique()} plots")

# exact = yield recorded; rough = no yield, typical date repeated every year
paddy["H"] = pd.to_datetime(paddy.HARVESTING_DATE, format="%m/%d/%Y")
paddy["exact"] = paddy.YIELD > 0
paddy["md"] = paddy.H.dt.strftime("%m-%d")
for k, g in paddy.groupby("exact"):
    by = g.groupby(["PLOT_ID", "STANDARD_SEASON"]).md.agg(["size", "nunique"])
    same = by[by["size"] > 1]["nunique"].eq(1).mean()
    print(
        f"{'exact' if k else 'rough'}: {len(g)} samples, {g.PLOT_ID.nunique()} plots, years "
        f"{g.YEAR.value_counts().sort_index().to_dict()}, "
        f"split {g.SPLIT.value_counts().to_dict()}, "
        f"plot-seasons with one month-day across years {same:.0%}"
    )
ex = paddy[paddy.exact].copy()
print("exact seasons", ex.STANDARD_SEASON.value_counts().to_dict())
print("exact harvest month", ex.H.dt.month.value_counts().sort_index().to_dict())
start = pd.to_datetime(
    dict(year=ex.YEAR, month=ex.STANDARD_SEASON.str[:3].map(SEASON_START), day=1)
)
assert ((ex.H - start).dt.days + 1 == ex.HARVESTING_DAY).all(), (
    "*_DAY is not 1-indexed days since season start"
)
print("*_DAY = 1-indexed days since season start month (verified on exact set)")
print("sow->harvest days", ex.eval("HARVESTING_DAY - SOWING_DAY").describe().round(1).to_dict())
sd = ex.groupby(["STANDARD_SEASON", "YEAR"]).HARVESTING_DAY.agg(
    ["count", "std", lambda s: (s - s.mean()).abs().mean()]
)
sd.columns = ["n", "sd", "mae_vs_group_mean"]
print("within season-year spread (in-sample mean baseline):\n", sd.round(1))

print("\n== masks (bands 1,3,4,5 = plot_id, sow, transplant, harvest day; 2 and 6 unidentified) ==")
masks = {int(os.path.basename(p)[:-4]) for p in glob.glob(f"{root}/masks/10m/*.tif")}
test_ids = set(df[df.SPLIT == "test"].UNIQUE_ID)
print(f"10m masks {len(masks)}; test samples with a mask: {len(masks & test_ids)}")
split_of_plot = df.dropna(subset=["PLOT_ID"]).groupby("PLOT_ID").SPLIT.first()
rows, cross = [], 0
for r in ex.itertuples():
    with rasterio.open(f"{root}/masks/10m/{r.UNIQUE_ID}.tif") as m:
        a = m.read()
    own = a[0] == r.PLOT_ID
    assert np.all(a[4][own] == r.HARVESTING_DAY), r.UNIQUE_ID
    others = {p for p in np.unique(a[0]) if p not in (0, r.PLOT_ID)}
    cross += any(split_of_plot.get(p) not in (None, r.SPLIT) for p in others)
    s1 = sorted(
        pd.to_datetime(os.path.basename(f)[17:25])
        for f in glob.glob(f"{root}/images/S1/npy/{r.UNIQUE_ID}/*.npz")
    )
    s2 = len(glob.glob(f"{root}/images/S2/npy/{r.UNIQUE_ID}/*.npz"))
    before = [(r.H - d).days for d in s1 if d <= r.H]
    rows.append(
        dict(
            px=int(own.sum()),
            neighbours=len(others),
            n_s1=len(s1),
            n_s2=s2,
            s1_after_harvest=sum(d > r.H for d in s1),
            s1_first_lead=max(before, default=np.nan),
            s1_in_21d=sum(0 <= x <= 21 for x in before),
            last_gap=min(before, default=np.nan),
        )
    )
pr = pd.DataFrame(rows)
print("harvest-day band == tabular HARVESTING_DAY on every exact sample's plot pixels")
print("per exact sample:\n", pr.describe().round(1).T[["mean", "min", "50%", "max"]])
print(
    f"plots < 10 px at 10 m: {(pr.px < 10).mean():.0%}; exact samples whose patch contains a plot "
    f"from another split: {cross}/{len(ex)}"
)

print("\n== authors' harvest-date runs (best val MAE over epochs, days) ==")
for f in sorted(glob.glob(f"{runs}/harvesting_date/*/trainlog.json")):
    log = json.load(open(f))
    if len(log) > 10:
        best = min(log.values(), key=lambda e: e["val_mae"])
        print(
            f"  {f.split('/')[-2]:22s} val_mae {best['val_mae']:.1f}  rmse {best['val_rmse']:.1f}"
        )
