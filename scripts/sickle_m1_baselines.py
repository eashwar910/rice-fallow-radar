"""P2 step 1: build the SICKLE M1 feature table and score the two baselines out of fold.

5-fold StratifiedGroupKFold over neighbour groups, stratified by season (D-022), on the dev
split only -- the locked test groups in configs/sickle_test_groups.json are never touched here.
Errors are reported by lead-time bucket (the proposal's 7/14/21-day horizons) and by season,
with 95% bootstrap CIs resampled over groups.

Usage: uv run python scripts/sickle_m1_baselines.py
Writes data/processed/sickle_m1_features.parquet and runs/sickle_m1_baselines.csv.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from rice_fallow_radar.eval import splits
from rice_fallow_radar.features import sickle_m1 as F
from rice_fallow_radar.ingest import sickle
from rice_fallow_radar.models import m1_baselines as B

FEAT = Path("data/processed/sickle_m1_features.parquet")
RESULTS = Path("runs/sickle_m1_baselines.csv")
BASELINES = {"seasonal_mean": B.seasonal_mean, "vh_peak_rule": B.vh_peak_rule}


def table(name: str, df: pd.DataFrame, pred_cols: list[str]) -> pd.DataFrame:
    rows = []
    for m in pred_cols:
        mae, lo, hi = B.bootstrap_mae(df[m] - df.lead, df.group)
        rows.append(dict(subset=name, n=len(df), model=m, mae=mae, lo=lo, hi=hi))
    return pd.DataFrame(rows)


def main() -> None:
    ex = sickle.exact_labels()
    series = pd.read_parquet("data/interim/sickle_s1_series.parquet")
    weather = pd.read_parquet("data/interim/sickle_weather.parquet")
    s2 = pd.read_parquet("data/interim/sickle_s2_series.parquet")
    tiles = sickle.sample_tiles(labels=ex)
    dev, test = splits.dev_test(ex)
    print(
        f"dev {len(dev)} samples / {dev.group.nunique()} groups; "
        f"test (locked, untouched) {len(test)} / {test.group.nunique()}"
    )

    feats = F.build(pd.concat([dev, test]), series, weather, tiles, s2)
    FEAT.parent.mkdir(parents=True, exist_ok=True)
    feats.to_parquet(FEAT)
    dev_f = feats[feats.unique_id.isin(dev.UNIQUE_ID)].reset_index(drop=True)
    print(
        f"features: {len(feats)} rows x {len(F.feature_columns(feats))} features "
        f"({sum(c.startswith(F.S2_PREFIXES) for c in F.feature_columns(feats))} from S2), "
        f"{feats.unique_id.nunique()} samples ({len(dev_f)} dev rows); -> {FEAT}"
    )
    print(f"rows with no clear S2 scene in the lookback: {feats.n_scenes_s2.eq(0).sum()}")

    # one fold assignment per sample, so all issue dates of a sample stay on the same side
    per_sample = dev_f.drop_duplicates("unique_id")[["unique_id", "group", "season"]]
    cv = StratifiedGroupKFold(5, shuffle=True, random_state=splits.SEED)
    for k, (_, te) in enumerate(cv.split(per_sample, per_sample.season, per_sample.group)):
        dev_f.loc[dev_f.unique_id.isin(per_sample.unique_id.iloc[te]), "fold"] = k
    print(
        "fold sizes (samples):",
        per_sample.assign(
            f=dev_f.groupby("unique_id").fold.first().reindex(per_sample.unique_id).to_numpy()
        )
        .groupby("f")
        .size()
        .to_dict(),
    )

    for name in BASELINES:
        dev_f[name] = np.nan
    for k in sorted(dev_f.fold.unique()):
        tr, te = dev_f[dev_f.fold != k], dev_f[dev_f.fold == k]
        for name, fn in BASELINES.items():
            dev_f.loc[te.index, name] = fn(tr, te)

    cols = list(BASELINES)
    out = [table("all leads", dev_f, cols)]
    for h, (lo, hi) in F.LEAD_BUCKETS.items():
        out.append(table(f"lead {h}d ({lo}-{hi})", dev_f[dev_f.lead.between(lo, hi)], cols))
    for s, g in dev_f.groupby("season"):
        if len(g) >= 50:
            out.append(table(f"season {s}", g, cols))
    res = pd.concat(out, ignore_index=True)
    res[["mae", "lo", "hi"]] = res[["mae", "lo", "hi"]].round(1)
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    res.to_csv(RESULTS, index=False)

    print("\nout-of-fold MAE in days (95% CI over neighbour groups), dev split only:\n")
    piv = res.assign(v=res.apply(lambda r: f"{r.mae:5.1f} [{r.lo:.1f}, {r.hi:.1f}]", axis=1))
    print(piv.pivot(index="subset", columns="model", values="v").to_string())
    print("\nrows per subset:", res.drop_duplicates("subset").set_index("subset").n.to_dict())
    print(f"\nwrote {RESULTS}")


if __name__ == "__main__":
    sys.exit(main())
