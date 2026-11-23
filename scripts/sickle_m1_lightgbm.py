"""P2 / FREEZE_PLAN point C (+ C2): LightGBM on SICKLE as a feature-set ablation, not one model.

The question is not "can LightGBM beat 12.0 days" but "which inputs earn their place". Eight arms
on identical rows and identical folds:

    calendar-4      calendar position + season -- no satellite at all (D-030's point model)
    base-5          + plot size: point C's published arm, kept so the 7.41 d row stays in the
                    table after D-030 dropped `area_acres` from the base block
    base+s1         add the radar block
    base+s1+weather add regional CHIRPS/ERA5-Land
    base+s2+weather optical instead of radar (does S1 earn its place?)
    all             base+s1+s2+weather (D-028)
    s1 only         radar with no calendar at all
    sensors only    s1+s2+weather with no calendar -- separates "no signal" from "redundant
                    with the clock", which are very different findings

Every arm is also reported **pooled** (`+pool`): a field's ~9 weekly estimates of its one
harvest date averaged over the issue dates at or before `as_of` (D-030, `L.pool_predictions`).
And every subset is also cut by **shared vs unique harvest date** (C'), because the pooled MAE
averages a 5 d regime where the sensors are significantly worse with a 10 d regime where they
are significantly better. The cut conditions on the label: a diagnostic, never a selector.

`calendar-4` exists because `gdd_season` and `days_since_season_start` dominate every sensor feature
(Spearman 0.75 and 0.64 with lead), so a model given the clock alone can reproduce the seasonal-
mean baseline. Without this arm a "win" could contain no remote sensing. `season` is handed to
every arm as a categorical so no arm is less informed than the seasonal-mean baseline.

Dev split only; the locked test groups are never read. Usage:
    uv run python scripts/sickle_m1_lightgbm.py
Writes runs/sickle_m1_lightgbm.csv (+ _tuning.csv, _importance.csv).
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from rice_fallow_radar.eval import splits
from rice_fallow_radar.features import sickle_m1 as F
from rice_fallow_radar.ingest import sickle
from rice_fallow_radar.models import m1_baselines as B
from rice_fallow_radar.models import m1_lightgbm as L

FEAT = Path("data/processed/sickle_m1_features.parquet")
RESULTS = Path("runs/sickle_m1_lightgbm.csv")
ARMS = {
    "calendar-4": ("base",),
    "base-5": ("base", "area"),
    "base+s1": ("base", "s1"),
    "base+s1+weather": ("base", "s1", "weather"),
    "base+s2+weather": ("base", "s2", "weather"),
    "all": ("base", "s1", "weather", "s2"),
    # no-calendar arms: if the sensor blocks score well here but add nothing on top of `base`,
    # their signal is redundant with the clock rather than absent -- a different conclusion
    "s1 only": ("s1",),
    "sensors only": ("s1", "weather", "s2"),
}
REF = "calendar-4"  # the arm every sensor arm has to beat (FREEZE_PLAN F, EVALUATION O1)


def table(name: str, df: pd.DataFrame, pred_cols: list[str]) -> pd.DataFrame:
    rows = []
    for m in pred_cols:
        mae, lo, hi = B.bootstrap_mae(df[m] - df.lead, df.group)
        rows.append(dict(subset=name, n=len(df), model=m, mae=mae, lo=lo, hi=hi))
    return pd.DataFrame(rows)


def main() -> None:
    feats = pd.read_parquet(FEAT)
    dev_ids = splits.dev_test(sickle.exact_labels())[0].UNIQUE_ID
    dev = feats[feats.unique_id.isin(dev_ids)].reset_index(drop=True)
    # season as a categorical, so every arm knows at least what the seasonal-mean baseline knows
    dev["season_cat"] = dev.season.astype("category")
    fold = splits.assign_folds(dev)
    print(f"dev {dev.unique_id.nunique()} samples / {dev.group.nunique()} groups, {len(dev)} rows")
    print("fold sizes (samples):", dev.groupby(fold).unique_id.nunique().to_dict())

    dev["shared_date"] = F.shared_harvest_date(dev)
    print(
        f"shared harvest date: {dev.shared_date.mean():.1%} of rows, "
        f"{dev[dev.shared_date].unique_id.nunique()} of {dev.unique_id.nunique()} samples"
    )

    tuning = []
    for arm, blocks in ARMS.items():
        cols = F.block_columns(dev, blocks) + (["season_cat"] if "base" in blocks else [])
        dev[arm], chosen = L.oof_predict(dev, cols, fold)
        pooled = L.pool_predictions(dev, dev[arm])
        dev[arm + "+pool"], dev["n_acc"] = pooled.pooled, pooled.n_acc
        tuning += [dict(arm=arm, n_features=len(cols), fold=k, **p) for k, p in enumerate(chosen)]
        for name in (arm, arm + "+pool"):
            mae, lo, hi = B.bootstrap_mae(dev[name] - dev.lead, dev.group)
            print(f"  {name:<22} {len(cols):>2} features  MAE {mae:5.2f} [{lo:.2f}, {hi:.2f}]")

    # the baselines on the same folds, so the table is self-contained
    for name, fn in {"seasonal_mean": B.seasonal_mean, "vh_peak_rule": B.vh_peak_rule}.items():
        dev[name] = np.nan
        for k in sorted(fold.unique()):
            te = dev[fold == k]
            dev.loc[te.index, name] = fn(dev[fold != k], te)

    arms = list(ARMS) + [a + "+pool" for a in ARMS]
    cols = arms + ["seasonal_mean", "vh_peak_rule"]
    out = [table("all leads", dev, cols)]
    for h, (lo, hi) in F.LEAD_BUCKETS.items():
        out.append(table(f"lead {h}d ({lo}-{hi})", dev[dev.lead.between(lo, hi)], cols))
    for s, g in dev.groupby("season"):
        if len(g) >= 50:
            out.append(table(f"season {s}", g, cols))
    # the label-quality stratum (C'): the two halves are a 5 d and a 10 d error regime
    for shared, g in dev.groupby("shared_date"):
        out.append(table("shared-date plots" if shared else "unique-date plots", g, cols))
    for n, g in dev.groupby(dev.n_acc.clip(upper=5)):
        out.append(table(f"n_acc {int(n)}{'+' if n == 5 else ''}", g, cols))
    res = pd.concat(out, ignore_index=True)
    res[["mae", "lo", "hi"]] = res[["mae", "lo", "hi"]].round(2)

    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    res.to_csv(RESULTS, index=False)
    pd.DataFrame(tuning).to_csv(RESULTS.with_name(RESULTS.stem + "_tuning.csv"), index=False)
    imp = L.gain_importance(dev, F.block_columns(dev, ARMS["all"]) + ["season_cat"])
    imp.rename("gain").rename_axis("feature").reset_index().assign(
        block=lambda d: d.feature.map(F.block_of)
    ).to_csv(RESULTS.with_name(RESULTS.stem + "_importance.csv"), index=False)

    piv = res.assign(v=res.apply(lambda r: f"{r.mae:5.2f} [{r.lo:.2f}, {r.hi:.2f}]", axis=1)).pivot(
        index="subset", columns="model", values="v"
    )
    for label, group in {
        "raw (one prediction per issue date)": list(ARMS) + ["seasonal_mean", "vh_peak_rule"],
        "pooled (D-030)": [a + "+pool" for a in ARMS],
    }.items():
        print(f"\nout-of-fold MAE in days, {label} -- 95% CI over neighbour groups, dev only:\n")
        print(piv[group].to_string())
    err = {a: (dev[a] - dev.lead).abs() for a in cols}
    for ref in (REF, REF + "+pool"):
        print(f"\npaired differences vs {ref}, all leads (per-row absolute error, same rows):")
        for a in cols:
            if a == ref or a.endswith("+pool") != ref.endswith("+pool"):
                continue
            gap, lo, hi = B.bootstrap_mean(err[a] - err[ref], dev.group)
            verdict = "better" if hi < 0 else "worse" if lo > 0 else "not separated"
            print(f"  {a:<22} {gap:+6.2f} d [{lo:+.2f}, {hi:+.2f}]  {verdict}")
    print(f"\nthe same, on each half of the label-quality stratum, {REF} as reference:")
    for shared, g in dev.groupby("shared_date"):
        print(f"  {'shared' if shared else 'unique'}-date plots (n={len(g)}):")
        for a in arms:
            if a == REF:
                continue
            e = (g[a] - g.lead).abs() - (g[REF] - g.lead).abs()
            gap, lo, hi = B.bootstrap_mean(e, g.group)
            verdict = "better" if hi < 0 else "worse" if lo > 0 else "not separated"
            print(f"    {a:<22} {gap:+6.2f} d [{lo:+.2f}, {hi:+.2f}]  {verdict}")
    print("\ntop 12 by total gain (one fit on all dev rows, diagnostic only):")
    print(imp.head(12).round(0).to_string())
    print(
        "\nblock share of total gain:",
        (imp.groupby(imp.index.map(F.block_of)).sum() / imp.sum()).round(3).to_dict(),
    )
    print(f"\nwrote {RESULTS}")


if __name__ == "__main__":
    sys.exit(main())
