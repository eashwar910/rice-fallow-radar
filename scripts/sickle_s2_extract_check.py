"""P2 step A: per-plot Sentinel-2 series from SICKLE, and is the optical harvest signal real?

Builds rice_fallow_radar.ingest.sickle.s2_series, then answers the two questions FREEZE_PLAN
point A exists for: how much of the S2 record survives cloud masking (DATA.md left this
unassessed), and whether NDVI collapses at harvest more cleanly than S1's VH does (+0.51 dB in
only 60% of samples, which is what motivated putting S2 into M1 at all).

Usage: uv run python scripts/sickle_s2_extract_check.py [sickle_dataset]
Writes data/interim/sickle_s2_series.parquet (consumed by features/sickle_m1.py).
"""

import sys
from pathlib import Path

import pandas as pd

from rice_fallow_radar.ingest import sickle

root = sys.argv[1] if len(sys.argv) > 1 else sickle.ROOT
OUT = Path("data/interim/sickle_s2_series.parquet")

ex = sickle.exact_labels(root)
s = sickle.s2_series(root, ex)
print(f"== extraction ==\n{len(ex)} samples, {ex.PLOT_ID.nunique()} plots, {len(s)} scene rows")
print(f"scenes per sample: {s.groupby('unique_id').size().describe().round(1).to_dict()}")
dups = s.duplicated(["unique_id", "date"]).sum()
print(f"duplicate (sample, date) rows from overlapping tiles: {dups}")

print("\n== patch/mask alignment ==")
print("scene shape offset from mask (px):", s.shape_off.value_counts().sort_index().to_dict())
print(f"edge-clipped scenes dropped: {s.edge_clipped.sum()} ({s.edge_clipped.mean():.1%})")
good = s[~s.edge_clipped].copy()

print(f"\n== cloud (SCL in {sickle.CLEAR_SCL}, MSK_CLDPRB < {sickle.CLDPRB_MAX}%) ==")
print(f"plot-pixel cloud fraction per scene: {good.cloud_frac.describe().round(2).to_dict()}")
print(f"scenes fully clouded (no clear plot pixel): {good.n_clear.eq(0).mean():.1%}")
print(f"scenes clear (>={sickle.CLEAR_FRAC:.0%} of plot pixels): {good.clear.mean():.1%}")
print(f"scenes with no computable NDVI: {good.ndvi.isna().mean():.1%}")
clear = good[good.clear].copy()
per = clear.groupby("unique_id").size()
per = per.reindex(good.unique_id.unique(), fill_value=0)
print(f"clear scenes per sample: {per.describe().round(1).to_dict()}")
print(f"samples with < 4 clear scenes: {per.lt(4).sum()}/{len(per)}")
print("NDVI", clear.ndvi.describe().round(2).to_dict())
print("NDWI", clear.ndwi.describe().round(2).to_dict())
print("MNDWI", clear.mndwi.describe().round(2).to_dict())

print("\n== time coverage per sample (clear scenes before harvest) ==")
cov = (
    clear[clear.lead_days >= 0]
    .groupby("unique_id")
    .lead_days.agg(
        n="size", first="max", last="min", in_7_21=lambda x: int(((x >= 7) & (x <= 21)).sum())
    )
    .reindex(good.unique_id.unique())
)
print(cov.describe().round(1).T[["mean", "min", "50%", "max"]].to_string())
no_win = cov.in_7_21.fillna(0).eq(0).sum()
print(f"samples with no clear scene in the 7-21 day window: {no_win}/{len(cov)}")

print("\n== harvest signature (mean NDVI by lead time, pooled over clear scenes) ==")
b = clear.assign(bin=pd.cut(clear.lead_days, [-60, -20, -1, 7, 14, 21, 30, 45, 60, 90, 200]))
print(
    b.groupby("bin", observed=True)
    .agg(n=("ndvi", "size"), ndvi=("ndvi", "mean"), mndwi=("mndwi", "mean"))
    .round(3)
    .to_string()
)
# same windows as the S1 check, so the two numbers are comparable
pre = clear[clear.lead_days.between(0, 30)].groupby("unique_id").ndvi.mean()
post = clear[clear.lead_days.between(-30, -1)].groupby("unique_id").ndvi.mean()
drop = (pre - post).dropna()
print(
    f"\nper-sample NDVI drop across harvest (mean 0-30 d before minus 1-30 d after): n={len(drop)},"
    f" median {drop.median():.3f}, {drop.gt(0).mean():.0%} of samples drop"
)
d = pd.DataFrame(dict(drop=drop)).join(clear.groupby("unique_id").season.first())
agg = dict(
    n=("drop", "size"), median_drop=("drop", "median"), frac_drop=("drop", lambda x: x.gt(0).mean())
)
print("\nby season:")
print(d.groupby("season").agg(**agg).round(3).to_string())

print("\n== tile-overlap duplicates ==")
pair = good.dropna(subset=["ndvi"])
spread = pair.groupby(["unique_id", "date"]).ndvi.agg(["size", "min", "max"])
spread = spread[spread["size"] > 1]
print(
    f"{len(spread)} same-date pairs with NDVI on both copies; "
    f"median spread {(spread['max'] - spread['min']).median():.4f}, "
    f"max {(spread['max'] - spread['min']).max():.3f}"
)
print(f"sickle.best_per_date -> {len(sickle.best_per_date(s))} rows from {len(s)}")

assert (spread["max"] - spread["min"]).median() < 0.02, "tile copies disagree; dedupe is not safe"
assert clear.ndvi.between(-1, 1).all() and clear.mndwi.between(-1, 1).all(), "index out of [-1,1]"
assert drop.median() > 0 and drop.gt(0).mean() > 0.6, (
    "no NDVI collapse at harvest: masking is wrong"
)

OUT.parent.mkdir(parents=True, exist_ok=True)
s.to_parquet(OUT)
print(f"\nwrote {OUT} ({len(s)} rows)")
