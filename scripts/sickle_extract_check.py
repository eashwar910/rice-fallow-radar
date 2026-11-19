"""P2 step 1: does SICKLE extract into usable per-plot radar series?

Builds the per-plot S1 table (rice_fallow_radar.sickle.s1_series), then checks the things that
would quietly break M1: patch/mask alignment, no-data, how many scenes land inside the 7-21 day
forecast window, and whether the VH curve actually shows the harvest drop the model needs.

Usage: uv run python scripts/sickle_extract_check.py [sickle_dataset]
Writes data/interim/sickle_s1_series.parquet (reused by the M1 feature table).
"""

import sys
from pathlib import Path

import pandas as pd

from rice_fallow_radar.ingest import sickle

root = sys.argv[1] if len(sys.argv) > 1 else sickle.ROOT
OUT = Path("data/interim/sickle_s1_series.parquet")

ex = sickle.exact_labels(root)
s = sickle.s1_series(root, ex)
print(f"== extraction ==\n{len(ex)} samples, {ex.PLOT_ID.nunique()} plots, {len(s)} scene rows")

print("\n== patch/mask alignment ==")
print("scene shape offset from mask (px):", s.shape_off.value_counts().sort_index().to_dict())
print(
    f"edge-clipped scenes dropped (>{sickle.SHAPE_TOL} px off): "
    f"{s.edge_clipped.sum()} ({s.edge_clipped.mean():.1%})"
)
good = s[~s.edge_clipped].copy()

print("\n== no-data and plot size ==")
print("plot pixels at 10 m:", good.groupby("unique_id").n_px.first().describe().round(1).to_dict())
print(f"samples with < 10 plot px: {good.groupby('unique_id').n_px.first().lt(10).mean():.0%}")
print(f"scenes losing any plot pixel to zeros: {good.eval('n_valid < n_px').mean():.1%}")
print(f"scenes with no valid pixel at all: {good.vh_db.isna().sum()}")
print(f"scenes with no incidence angle: {good.angle.isna().sum()}")
print("VV dB", good.vv_db.describe().round(1).to_dict())
print("VH dB", good.vh_db.describe().round(1).to_dict())

print("\n== time coverage per sample (scenes before harvest) ==")
cov = (
    good[good.lead_days >= 0]
    .groupby("unique_id")
    .lead_days.agg(
        n="size", first="max", last="min", in_7_21=lambda x: int(((x >= 7) & (x <= 21)).sum())
    )
)
print(cov.describe().round(1).T[["mean", "min", "50%", "max"]].to_string())
print(f"samples with no scene at all in the 7-21 day window: {cov.in_7_21.eq(0).sum()}/{len(cov)}")
print(f"samples with no scene >= 21 days out: {cov.first.lt(21).sum()}/{len(cov)}")

print("\n== harvest signature (mean VH by lead time, pooled) ==")
b = good.assign(bin=pd.cut(good.lead_days, [-60, -20, -1, 7, 14, 21, 30, 45, 60, 90, 200]))
sig = b.groupby("bin", observed=True).agg(n=("vh_db", "size"), vh=("vh_db", "mean"))
print(sig.round(2).to_string())
# per sample: VH in the 30 days before harvest vs the 30 days after
pre = good[good.lead_days.between(0, 30)].groupby("unique_id").vh_db.mean()
post = good[good.lead_days.between(-30, -1)].groupby("unique_id").vh_db.mean()
drop = (pre - post).dropna()
print(
    f"\nper-sample VH drop across harvest (mean 0-30 d before minus 1-30 d after): n={len(drop)}, "
    f"median {drop.median():.2f} dB, {drop.gt(0).mean():.0%} of samples drop"
)
px = good.groupby("unique_id").n_px.first()
d = pd.DataFrame(dict(drop=drop, px=px)).dropna(subset=["drop"])
d = d.join(good.groupby("unique_id").season.first())
agg = dict(
    n=("drop", "size"),
    median_drop=("drop", "median"),
    frac_drop=("drop", lambda x: x.gt(0).mean()),
)
print("\nby plot size (px):")
print(d.groupby(pd.cut(d.px, [0, 10, 16, 24, 100]), observed=True).agg(**agg).round(2).to_string())
print("\nby season:")
print(d.groupby("season").agg(**agg).round(2).to_string())
print(f"samples with no usable scene: {s.unique_id.nunique() - good.unique_id.nunique()}")
assert len(good) > 5000 and good.vh_db.between(-30, 0).mean() > 0.99, "VH out of plausible dB range"
assert drop.median() > 0, "no harvest drop in VH: extraction or masking is wrong"

OUT.parent.mkdir(parents=True, exist_ok=True)
s.to_parquet(OUT)
print(f"\nwrote {OUT} ({len(s)} rows)")
