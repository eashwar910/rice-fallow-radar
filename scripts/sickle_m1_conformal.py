"""P2 / FREEZE_PLAN point D: calibrated intervals for M1, and the conditional-coverage table.

`EVALUATION.md` promises intervals with measured coverage, not just a point forecast: a sowing
window is a decision under uncertainty and "harvest in 11 days" is worth little without "and we
are 90% sure it is 7-16". This script produces that table on the dev split only.

Three variants, same folds, same model, so the table shows what each ingredient buys:

    raw + marginal      CQR on one prediction per issue date, one offset for all rows
    pooled + marginal   CQR on D-030's pooled forecast, still one offset for all rows
    pooled + by n_acc   one offset per accumulation stratum (Mondrian) -- the recommended one

Nesting: each outer fold's calibration rows come from an inner, group-disjoint split of that
fold's *training* rows, so no row is ever calibrated on a model that saw it, and the locked test
groups are never read. Usage:
    uv run python scripts/sickle_m1_conformal.py
Writes runs/sickle_m1_conformal.csv (+ _rows.parquet).
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from rice_fallow_radar.eval import splits
from rice_fallow_radar.features import sickle_m1 as F
from rice_fallow_radar.ingest import sickle
from rice_fallow_radar.models import m1_baselines as B
from rice_fallow_radar.models import m1_conformal as C

FEAT = Path("data/processed/sickle_m1_features.parquet")
RESULTS = Path("runs/sickle_m1_conformal.csv")
VARIANTS = ("raw + marginal", "pooled + marginal", "pooled + by n_acc")


def table(name: str, df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for v in VARIANTS:
        lo, hi = df[f"{v} lo"], df[f"{v} hi"]
        covered = ((lo <= df.lead) & (df.lead <= hi)).astype(float)
        cov, c_lo, c_hi = B.bootstrap_mean(covered, df.group)
        mae, _, _ = B.bootstrap_mae(df[f"{v} mid"] - df.lead, df.group)
        rows.append(
            dict(
                variant=v,
                subset=name,
                n=len(df),
                coverage=round(100 * cov, 1),
                cov_lo=round(100 * c_lo, 1),
                cov_hi=round(100 * c_hi, 1),
                mean_width=round(float((hi - lo).mean()), 2),
                median_width=round(float((hi - lo).median()), 2),
                mae=round(mae, 2),
            )
        )
    return pd.DataFrame(rows)


def main() -> None:
    feats = pd.read_parquet(FEAT)
    dev_ids = splits.dev_test(sickle.exact_labels())[0].UNIQUE_ID
    dev = feats[feats.unique_id.isin(dev_ids)].reset_index(drop=True)
    dev["season_cat"] = dev.season.astype("category")
    dev["shared_date"] = F.shared_harvest_date(dev)
    # D-030's point model: the four calendar columns, no satellite data
    cols = F.block_columns(dev, ("base",)) + ["season_cat"]
    fold = splits.assign_folds(dev)
    for c in [f"{v} {k}" for v in VARIANTS for k in ("lo", "mid", "hi")] + ["n_acc"]:
        dev[c] = np.nan
    print(f"dev {dev.unique_id.nunique()} samples / {dev.group.nunique()} groups, {len(dev)} rows")
    print(f"features ({len(cols)}): {', '.join(cols)}")

    for k in sorted(fold.unique()):
        tr_all, te = dev[fold != k], dev[fold == k]
        inner = splits.assign_folds(tr_all, n=3, seed=splits.SEED + 1)
        tr, cal = tr_all[inner != 0], tr_all[inner == 0]
        assert not set(cal.group) & set(tr.group), "calibration and training groups overlap"
        assert not set(cal.group) & set(te.group), "calibration and test groups overlap"
        models = C.fit(tr, cols)
        qc, qt = C.predict(models, cal, cols), C.predict(models, te, cols)
        pc, acc_c = C.pooled(cal, qc)
        pt, acc_t = C.pooled(te, qt)
        dev.loc[te.index, "n_acc"] = acc_t

        for v, (q_cal, q_te) in {
            "raw + marginal": (qc, qt),
            "pooled + marginal": (pc, pt),
        }.items():
            off = C.offset(q_cal[:, 0], q_cal[:, 2], cal.lead.to_numpy())
            dev.loc[te.index, [f"{v} lo", f"{v} mid", f"{v} hi"]] = C.widen(q_te, off)
        tbl = C.offsets_by_stratum(pc[:, 0], pc[:, 2], cal.lead.to_numpy(), C.acc_stratum(acc_c))
        off = C.apply_offsets(tbl, C.acc_stratum(acc_t))
        v = "pooled + by n_acc"
        dev.loc[te.index, [f"{v} lo", f"{v} mid", f"{v} hi"]] = C.widen(pt, off)
        print(
            f"  fold {k}: train {len(tr)} / calibrate {len(cal)} / test {len(te)} rows, "
            f"offsets {tbl.round(2).to_dict()}"
        )

    assert dev[[f"{v} lo" for v in VARIANTS]].notna().all().all(), "a row got no interval"
    dev["acc"] = C.acc_stratum(dev.n_acc)

    out = [table("all leads", dev)]
    for h, (lo, hi) in F.LEAD_BUCKETS.items():
        out.append(table(f"lead {h}d ({lo}-{hi})", dev[dev.lead.between(lo, hi)]))
    for s, g in dev.groupby("season"):
        if len(g) >= 50:
            out.append(table(f"season {s}", g))
    for shared, g in dev.groupby("shared_date"):
        out.append(table("shared-date plots" if shared else "unique-date plots", g))
    for a, g in dev.groupby("acc", observed=True):
        out.append(table(f"n_acc {a}", g))
    res = pd.concat(out, ignore_index=True)

    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    res.to_csv(RESULTS, index=False)
    ivl = [f"{v} {k}" for v in VARIANTS for k in ("lo", "mid", "hi")]
    keep = ["unique_id", "group", "season", "as_of", "harvest", "lead", "shared_date", "n_acc"]
    dev[keep + ivl].to_parquet(RESULTS.with_name(RESULTS.stem + "_rows.parquet"))

    def fmt(r: pd.Series, field: str, unit: str) -> str:
        ci = f" [{r.cov_lo:.0f}, {r.cov_hi:.0f}]" if field == "coverage" else ""
        return f"{r[field]:5.1f}{unit}{ci}"

    for field, unit in (("coverage", "%"), ("mean_width", " d")):
        print(f"\n{field} ({100 * (1 - C.ALPHA):.0f}% target), dev split only:\n")
        piv = res.assign(v=res.apply(fmt, axis=1, field=field, unit=unit)).pivot(
            index="subset", columns="variant", values="v"
        )
        print(piv[list(VARIANTS)].to_string())
    print(f"\nwrote {RESULTS}")


if __name__ == "__main__":
    sys.exit(main())
