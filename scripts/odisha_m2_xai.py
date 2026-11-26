"""P3 diagnosis: *why* the transferred model fails, with attributions that are tested before use.

Three analyses, free 40% only, every model trained on all SICKLE dev (the zero-shot setting):

1. **TreeSHAP** (Lundberg et al., 2020; LightGBM's exact `pred_contrib`, no extra dependency) on
   `base+s1+s2` and on `base+s1`: share of mean |SHAP| per feature block on SICKLE rows vs Odisha
   rows, and the signed clock contribution per lead bucket. If the step-3 reading is right ("the
   trees trust the clock over the radar"), the base block should dominate on *both* domains and
   its Odisha contribution should carry the ~3-week bias.
2. **Deletion test** (region perturbation, Samek et al., 2017): replace a row's top-k features by
   |SHAP| with their SICKLE-dev median, k = 1..10, and compare the mean |change in prediction|
   with deleting k features in random order (20 orders). AOPC (area over the perturbation curve)
   above random = the attribution is faithful *to the model*. Then the diagnostic version:
   deleting the single top-attributed feature on Odisha -- does it *reduce* the Odisha error?
3. **Masking ablation** (MODELS.md §M2, hypothesis written in the proposal): Tamil Nadu models
   lean on the soil drying after irrigation stops 10-15 days before harvest. The mask is a
   **15-day latency**: every S1/S2 scene is delayed by `MASK_D` days on both domains, so a row
   sees only what existed 15 days before its `as_of`. At the 7-day horizon that hides exactly the
   pre-harvest drying window; at 21 days it hides nothing the hypothesis is about. Features
   rebuilt, models retrained. The hypothesis predicts the **7-day transfer gap shrinks more than
   the 21-day one**. (Removing the scenes in the 15 days before the *true* harvest, the obvious
   version, leaks: the hole's edge makes `days_since_scene` equal 16 - lead. Measured on 26 Nov:
   SICKLE's 21-day MAE "improved" by 1.1 d with no 21-day row losing a scene.)

Usage:
    uv run python scripts/odisha_m2_xai.py
Writes runs/odisha_m2_xai_{shap,deletion,masking}.csv.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from odisha_m2_sensors import SENSORS
from odisha_m2_zero_shot import LABELS, sickle_dev

from rice_fallow_radar.eval import interval_scoring as S
from rice_fallow_radar.eval import splits
from rice_fallow_radar.features import odisha_m1 as O
from rice_fallow_radar.features import sickle_m1 as F
from rice_fallow_radar.ingest import sickle
from rice_fallow_radar.models import m1_baselines as B
from rice_fallow_radar.models import m1_lightgbm as L

RUNS = Path("runs")
ARMS = {"base+s1+s2": ("base", "s1", "s2"), "base+s1": ("base", "s1"), "s1+s2": ("s1", "s2")}
MASK_D = 15
K_MAX, N_RANDOM = 10, 20


def cols_of(df, blocks):
    return F.block_columns(df, blocks) + (["season_cat"] if "base" in blocks else [])


def odisha(labels, s1, s2, cats):
    od = O.add_sensors(O.build(labels), s1, s2)
    od["unique_id"] = od.field_id
    od["season_cat"] = pd.Categorical(od.season, categories=cats)
    return od


def shap(model, X: pd.DataFrame) -> pd.DataFrame:
    """Exact TreeSHAP values (n, p); the last column LightGBM returns is the expected value."""
    v = model.booster_.predict(X, pred_contrib=True)
    return pd.DataFrame(v[:, :-1], columns=X.columns, index=X.index)


def block(c: str) -> str:
    return "base" if c == "season_cat" else F.block_of(c)


def bucket(lead: pd.Series) -> pd.Series:
    out = pd.Series("other", index=lead.index)
    for h, (lo, hi) in F.LEAD_BUCKETS.items():
        out[lead.between(lo, hi)] = f"{h}d"
    return out


def deletion(
    model, X: pd.DataFrame, sv: pd.DataFrame, bg: pd.Series, seed: int = 0
) -> pd.DataFrame:
    """Mean |pred change| after deleting the top-k (SHAP order) vs k random features."""
    rng = np.random.default_rng(seed)
    base = model.predict(X)
    order = np.argsort(-sv.abs().to_numpy(), axis=1)
    out = []
    for k in range(1, K_MAX + 1):
        Xs = X.copy()
        for j, c in enumerate(X.columns):
            hit = (order[:, :k] == j).any(axis=1)
            Xs.loc[hit, c] = bg[c]
        shap_d = np.abs(model.predict(Xs) - base).mean()
        rand = []
        for _ in range(N_RANDOM):
            pick = np.argsort(rng.random(X.shape), axis=1)[:, :k]
            Xr = X.copy()
            for j, c in enumerate(X.columns):
                Xr.loc[(pick == j).any(axis=1), c] = bg[c]
            rand.append(np.abs(model.predict(Xr) - base).mean())
        out.append(dict(k=k, shap_order=shap_d, random_order=float(np.mean(rand))))
    return pd.DataFrame(out)


def mask(series: pd.DataFrame) -> pd.DataFrame:
    """Every scene `MASK_D` days late: a row then sees the field as it was 15 days earlier.

    Target-free, so nothing about the harvest date can leak through where the data stops.
    """
    return series.assign(date=series.date + pd.Timedelta(days=MASK_D))


def main() -> None:
    labels = pd.read_parquet(LABELS)
    s1, s2 = (pd.read_parquet(SENSORS / f"{k}.parquet") for k in ("s1", "s2"))
    dev, _ = sickle_dev()
    cats = dev.season_cat.cat.categories
    od = odisha(labels, s1, s2, cats)
    assert not od.eval_lock.any(), "a locked row reached the diagnosis"
    models = {}
    for arm, blocks in ARMS.items():
        cols = cols_of(dev, blocks)
        models[arm] = (cols, L._fit(dev, cols, L._tune(dev, cols, splits.SEED), splits.SEED))

    # 1. SHAP block shares and the clock's signed contribution
    rows = []
    for arm in ("base+s1+s2", "base+s1"):
        cols, m = models[arm]
        for dom, df in (("SICKLE", dev), ("Odisha", od)):
            sv = shap(m, df[cols])
            share = sv.abs().T.groupby(block).sum().T
            share = share.div(share.sum(axis=1), axis=0)
            b = bucket(df.lead)
            for bk in ("all", "7d", "14d", "21d"):
                sel = np.ones(len(df), bool) if bk == "all" else (b == bk).to_numpy()
                r = dict(arm=arm, domain=dom, bucket=bk, n=int(sel.sum()))
                r |= {f"share_{k}": share.loc[sel, k].mean() for k in share.columns}
                r["clock_shap"] = sv.loc[sel, "days_since_season_start"].mean()
                r["base_shap"] = (
                    sv.loc[sel, [c for c in cols if block(c) == "base"]].sum(axis=1).mean()
                )
                r["s1_shap"] = sv.loc[sel, [c for c in cols if block(c) == "s1"]].sum(axis=1).mean()
                rows.append(r)
            top = sv.abs().mean().sort_values(ascending=False).head(5)
            print(f"{arm} on {dom}: top |SHAP| {top.round(2).to_dict()}")
    shap_res = pd.DataFrame(rows)

    # 2. deletion test, and whether deleting the top feature fixes Odisha
    cols, m = models["base+s1+s2"]
    bg = dev[cols].median(numeric_only=True)
    bg["season_cat"] = "sep-feb"
    dels = []
    for dom, df in (("SICKLE", dev), ("Odisha", od)):
        X = df[cols].copy()
        d = deletion(m, X, shap(m, X), bg)
        d["domain"] = dom
        dels.append(d)
    dels = pd.concat(dels)
    sv = shap(m, od[cols])
    top1 = sv.abs().idxmax(axis=1)
    X = od[cols].copy()
    for c in cols:
        X.loc[top1 == c, c] = bg[c]
    before = L.pool_predictions(od, m.predict(od[cols])).pooled
    after = L.pool_predictions(od, m.predict(X)).pooled
    fix = []
    for name, g in [("all leads", od)] + [
        (f"lead {h}d", od[od.lead.between(lo, hi)]) for h, (lo, hi) in F.LEAD_BUCKETS.items()
    ]:
        e0 = S.midpoint_error(before[g.index], g.lead_lo, g.lead_hi)
        e1 = S.midpoint_error(after[g.index], g.lead_lo, g.lead_hi)
        dd = B.bootstrap_mean(e1 - e0, g.block)
        fix.append(
            dict(
                subset=name,
                mae_before=e0.mean(),
                mae_after_top1_deleted=e1.mean(),
                diff=dd[0],
                lo=dd[1],
                hi=dd[2],
            )
        )
    fix = pd.DataFrame(fix)
    print(f"\ntop-1 attributed feature on Odisha rows: {top1.value_counts().head(5).to_dict()}")

    # 3. masking ablation
    ex = sickle.exact_labels()
    dev_lab = splits.dev_test(ex)[0]
    ss1 = pd.read_parquet("data/interim/sickle_s1_series.parquet")
    ss2 = pd.read_parquet("data/interim/sickle_s2_series.parquet")
    dev_m = F.build(dev_lab, mask(ss1), s2=mask(ss2))
    dev_m["season_cat"] = pd.Categorical(dev_m.season, categories=cats)
    od_m = odisha(labels, mask(s1), mask(s2), cats)
    # masking can leave a SICKLE row with < 3 S1 scenes, which `build` drops: compare on shared rows
    key = ["unique_id", "as_of"]
    shared = dev[key].merge(dev_m[key], on=key)
    print(
        f"\nmasking: SICKLE rows {len(dev)} -> {len(dev_m)} ({len(shared)} shared); "
        f"Odisha {len(od)} -> {len(od_m)}"
    )
    mrows = []
    for arm in ("base+s1+s2", "s1+s2"):
        blocks = ARMS[arm]
        for tag, d_, o_ in (("unmasked", dev, od), ("masked", dev_m, od_m)):
            d_ = d_.merge(shared, on=key).reset_index(drop=True)
            cols = cols_of(d_, blocks)
            fold = splits.assign_folds(d_)
            oof = L.pool_predictions(d_, L.oof_predict(d_, cols, fold)[0]).pooled
            mm = L._fit(d_, cols, L._tune(d_, cols, splits.SEED), splits.SEED)
            op = L.pool_predictions(o_, mm.predict(o_[cols])).pooled
            for h, (lo, hi) in F.LEAD_BUCKETS.items():
                sd = d_.lead.between(lo, hi)
                so = o_.lead.between(lo, hi)
                s_mae = float(np.abs(oof - d_.lead)[sd].mean())
                o_mae = float(S.midpoint_error(op[so], o_.lead_lo[so], o_.lead_hi[so]).mean())
                mrows.append(
                    dict(
                        arm=arm,
                        mask=tag,
                        horizon=f"{h}d",
                        sickle_mae=s_mae,
                        odisha_mae=o_mae,
                        gap=o_mae - s_mae,
                    )
                )
    masking = pd.DataFrame(mrows)

    shap_res.round(3).to_csv(RUNS / "odisha_m2_xai_shap.csv", index=False)
    dels.round(3).to_csv(RUNS / "odisha_m2_xai_deletion.csv", index=False)
    fix.round(2).to_csv(RUNS / "odisha_m2_xai_top1_fix.csv", index=False)
    masking.round(2).to_csv(RUNS / "odisha_m2_xai_masking.csv", index=False)
    pd.set_option("display.width", 220)
    print("\nSHAP block shares and signed contributions (d)\n")
    print(shap_res.round(2).to_string(index=False))
    aopc = dels.groupby("domain")[["shap_order", "random_order"]].mean()
    print("\ndeletion test: mean |pred change| (d) by k; AOPC by domain\n")
    print(
        dels.pivot(index="k", columns="domain", values=["shap_order", "random_order"])
        .round(2)
        .to_string()
    )
    print(aopc.round(2).to_string())
    print("\nOdisha error after deleting each row's top-1 attributed feature (negative = better)\n")
    print(fix.round(2).to_string(index=False))
    print(f"\nmasking ablation ({MASK_D}-day latency on every scene, both domains)\n")
    print(
        masking.pivot(
            index=["arm", "horizon"], columns="mask", values=["sickle_mae", "odisha_mae", "gap"]
        )
        .round(2)
        .to_string()
    )


if __name__ == "__main__":
    sys.exit(main())
