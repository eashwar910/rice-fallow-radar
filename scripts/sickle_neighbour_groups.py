"""Open question #9: neighbour groups for a spatially grouped SICKLE split.

Plots that appear in the same 320 m mask patch are neighbours. Connected components of that
graph (built from every mask, so unlabelled plots can link labelled ones) are candidate CV groups.
Reports how many groups the 131 exact-label plots fall into and how big they are.
Usage: uv run python scripts/sickle_neighbour_groups.py [sickle_dataset]
"""

import glob
import sys

import numpy as np
import pandas as pd
import rasterio

root = sys.argv[1] if len(sys.argv) > 1 else "sickle_dataset"
df = pd.read_csv(f"{root}/sickle_dataset_tabular.csv")
paddy = df[(df.CROP == "Paddy") & (df.YIELD > 0)]  # exact labels, as in sickle_profile.py

parent: dict[int, int] = {}


def find(x: int) -> int:
    parent.setdefault(x, x)
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


for path in glob.glob(f"{root}/masks/10m/*.tif"):
    with rasterio.open(path) as m:
        ids = [int(p) for p in np.unique(m.read(1)) if p > 0]
    for p in ids[1:]:
        parent[find(p)] = find(ids[0])

plots = paddy.groupby("PLOT_ID").agg(
    samples=("UNIQUE_ID", "size"),
    years=("YEAR", lambda s: ",".join(map(str, sorted(s.unique())))),
    seasons=("STANDARD_SEASON", lambda s: ",".join(sorted(s.unique()))),
    split=("SPLIT", "first"),
)
plots["group"] = [find(int(p)) for p in plots.index]
assert plots.index.isin(list(parent)).all(), "every exact plot should appear in some mask"

g = plots.groupby("group").agg(
    plots=("samples", "size"), samples=("samples", "sum"), splits=("split", "nunique")
)
g = g.sort_values("samples", ascending=False)
print(f"all plots in masks: {len(parent)}; components overall: {len({find(p) for p in parent})}")
print(f"exact-label plots: {len(plots)}, samples: {plots.samples.sum()}, groups: {len(g)}")
print(
    f"largest group: {g.plots.iloc[0]} plots / {g.samples.iloc[0]} samples "
    f"({g.samples.iloc[0] / plots.samples.sum():.0%} of samples)"
)
print("group size (plots) distribution:", g.plots.value_counts().sort_index().to_dict())
print(f"groups mixing official train/val: {(g.splits > 1).sum()}")
print("\ntop 10 groups:\n", g.head(10).to_string())
plots.to_csv("data/interim/sickle_neighbour_groups.csv")
print("\nwrote data/interim/sickle_neighbour_groups.csv")
