"""P3 step 2 (EVALUATION.md §M2 protocol, v1): the zero-shot arms, on the free 40% only.

Three arms, the same Odisha rows (`features.odisha_m1.build`, locked 60% excluded):

    zero-shot M1     D-030's `calendar-4+pool` (tuned L1 LightGBM) trained on all SICKLE dev,
                     with D-032's interval: CQR fitted on 2/3 of dev groups, Mondrian offsets by
                     accumulation stratum calibrated on the other 1/3 (block-disjoint)
    Odisha-calendar  D-033: one CSISA harvest date + 90% interval per district. CSISA surveyed
                     coastal districts only, so Baleswar uses Balasore 2018 and **Bolangir uses
                     the all-Odisha prior** -- a coastal calendar standing in for the uplands
    seasonal mean    SICKLE's `sep-feb` mean harvest date (m1_baselines.seasonal_mean)

Odisha is told it is SICKLE's `sep-feb` (pre-registered); the other mappings are the clock
sensitivity for the M1 arm, reported and never selected. Scored by §Interval quality rule 5:
midpoint MAE with bracket [point_error, expected_error], intersection coverage minus 3.0 points
with bracket [expected_coverage, covered], block-bootstrap 95% CIs, and the transfer gap against
SICKLE's midpoint MAE under the same synthetic widening (runs/interval_rule_check.csv).

Order of operations: refuses to run before step 1 (D-031's measurement) has written its result.
Usage:
    uv run python scripts/odisha_m2_zero_shot.py
Writes runs/odisha_m2_zero_shot.csv (+ _rows.parquet).
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from rice_fallow_radar.eval import interval_scoring as S
from rice_fallow_radar.eval import splits
from rice_fallow_radar.features import odisha_calendar as OC
from rice_fallow_radar.features import odisha_m1 as O
from rice_fallow_radar.features import sickle_m1 as F
from rice_fallow_radar.ingest import sickle
from rice_fallow_radar.models import m1_baselines as B
from rice_fallow_radar.models import m1_conformal as C
from rice_fallow_radar.models import m1_lightgbm as L

STEP1 = Path("runs/odisha_transplant_spread.csv")
FEAT = Path("data/processed/sickle_m1_features.parquet")
LABELS = Path("data/processed/odisha_labels.parquet")
CSISA = Path("data/processed/csisa_rice.parquet")
RULE_CHECK = Path("runs/interval_rule_check.csv")
RESULTS = Path("runs/odisha_m2_zero_shot.csv")
COV_BIAS = 3.0  # points: intersection coverage overstates exact coverage by this on SICKLE
CALENDAR_PRIOR = {"baleswar": "Balasore", "bolangir": None}  # None -> all-Odisha prior
ARMS = ("zero-shot M1", "Odisha-calendar", "seasonal mean")
SICKLE_REF = {"zero-shot M1": "calendar-4+pool", "seasonal mean": "seasonal_mean"}


def sickle_dev() -> tuple[pd.DataFrame, list[str]]:
    feats = pd.read_parquet(FEAT)
    dev_ids = splits.dev_test(sickle.exact_labels())[0].UNIQUE_ID
    dev = feats[feats.unique_id.isin(dev_ids)].reset_index(drop=True)
    dev["season_cat"] = dev.season.astype("category")
    return dev, F.block_columns(dev, ("base",)) + ["season_cat"]


def odisha_rows(labels: pd.DataFrame, season: str, cats) -> pd.DataFrame:
    od = O.build(labels, season=season)
    od["unique_id"] = od.field_id  # pooling and the SICKLE helpers key on unique_id
    od["season_cat"] = pd.Categorical(od.season, categories=cats)
    od["year"] = od.last_green.map(lambda d: d.year if d.month >= 6 else d.year - 1)
    return od


def m1_arm(point, dev: pd.DataFrame, cols: list[str], od: pd.DataFrame) -> pd.DataFrame:
    """Pooled point forecast from the tuned L1 model and the D-032 interval, both on `od`."""
    pooled = L.pool_predictions(od, point.predict(od[cols]))
    inner = splits.assign_folds(dev, n=3, seed=splits.SEED + 1)
    tr, cal = dev[inner != 0], dev[inner == 0]
    assert not set(tr.group) & set(cal.group), "calibration and training groups overlap"
    models = C.fit(tr, cols)
    pc, acc_c = C.pooled(cal, C.predict(models, cal, cols))
    po, acc_o = C.pooled(od, C.predict(models, od, cols))
    tbl = C.offsets_by_stratum(pc[:, 0], pc[:, 2], cal.lead.to_numpy(), C.acc_stratum(acc_c))
    ivl = C.widen(po, C.apply_offsets(tbl, C.acc_stratum(acc_o)))
    print(f"  CQR offsets by n_acc (calibrated on {cal.group.nunique()} SICKLE groups): "
          f"{tbl.round(2).to_dict()}")  # fmt: skip
    return pd.DataFrame(
        {"pred": pooled.pooled, "lo": ivl[:, 0], "hi": ivl[:, 2], "n_acc": pooled.n_acc},
        index=od.index,
    )


def calendar_arm(od: pd.DataFrame, csisa: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=od.index, columns=["pred", "lo", "hi"], dtype=float)
    for (district, year), g in od.groupby(["district", "year"]):
        f = OC.zero_shot_harvest(OC.prior(csisa, CALENDAR_PRIOR[district]), int(year))
        for k, key in (("pred", "harvest_date"), ("lo", "lower"), ("hi", "upper")):
            out.loc[g.index, k] = (f[key] - g.as_of).dt.days
    return out


def score(od: pd.DataFrame, arm: str) -> dict:
    p, a, b, grp = od[f"{arm} pred"], od.lead_lo, od.lead_hi, od.block
    mid = B.bootstrap_mean(S.midpoint_error(p, a, b), grp)
    out = dict(
        arm=arm,
        n_rows=len(od),
        n_fields=od.field_id.nunique(),
        mae=mid[0],
        mae_lo=mid[1],
        mae_hi=mid[2],
        bracket_lo=float(S.point_error(p, a, b).mean()),
        bracket_hi=float(S.expected_error(p, a, b).mean()),
    )
    if f"{arm} lo" in od:
        lo, hi = od[f"{arm} lo"], od[f"{arm} hi"]
        cov = B.bootstrap_mean(S.covered(lo, hi, a, b).astype(float), grp)
        out |= dict(
            coverage=100 * cov[0] - COV_BIAS,
            cov_lo=100 * cov[1] - COV_BIAS,
            cov_hi=100 * cov[2] - COV_BIAS,
            cov_bracket_lo=100 * float(S.expected_coverage(lo, hi, a, b).mean()),
            cov_bracket_hi=100 * float(S.covered(lo, hi, a, b).mean()),
            mean_width=float((hi - lo).mean()),
        )
    return out


def main() -> None:
    if not STEP1.exists():
        sys.exit(f"{STEP1} missing: step 1 (D-031) must finish before any Odisha arm is scored")
    labels, csisa = pd.read_parquet(LABELS), pd.read_parquet(CSISA)
    dev, cols = sickle_dev()
    cats = dev.season_cat.cat.categories
    od = odisha_rows(labels, O.HEADLINE_SEASON, cats)
    assert not od.eval_lock.any(), "a locked row reached the zero-shot scoring"
    print(f"SICKLE dev {dev.unique_id.nunique()} samples, {len(dev)} rows; features {cols}")
    print(f"Odisha free 40%: {od.field_id.nunique()} fields, {od.block.nunique()} blocks, "
          f"{len(od)} rows")  # fmt: skip

    point = L._fit(dev, cols, L._tune(dev, cols, splits.SEED), splits.SEED)  # D-030, all dev
    m1 = m1_arm(point, dev, cols, od)
    od["zero-shot M1 pred"], od["zero-shot M1 lo"], od["zero-shot M1 hi"] = m1.pred, m1.lo, m1.hi
    od["n_acc"] = m1.n_acc
    cal = calendar_arm(od, csisa)
    od["Odisha-calendar pred"], od["Odisha-calendar lo"], od["Odisha-calendar hi"] = (
        cal.pred, cal.lo, cal.hi
    )  # fmt: skip
    od["seasonal mean pred"] = B.seasonal_mean(dev, od)

    subsets = [("all leads", od)] + [(f"district {d}", g) for d, g in od.groupby("district")]
    subsets += [
        (f"lead {h}d ({lo}-{hi})", od[od.lead.between(lo, hi)])
        for h, (lo, hi) in F.LEAD_BUCKETS.items()
    ]
    res = pd.DataFrame(
        [dict(subset=name, **score(g, arm)) for name, g in subsets for arm in ARMS if len(g)]
    )
    ref = pd.read_csv(RULE_CHECK)
    res["sickle_mae"] = res.arm.map(lambda a: ref[f"midpoint {SICKLE_REF[a]}"].mean()
                                    if a in SICKLE_REF else np.nan)  # fmt: skip
    res["transfer_gap"] = res.mae - res.sickle_mae

    # O1-style paired comparisons, same rows: signed difference in midpoint error
    pairs = []
    for x, y in (("zero-shot M1", "Odisha-calendar"), ("zero-shot M1", "seasonal mean"),
                 ("Odisha-calendar", "seasonal mean")):  # fmt: skip
        for name, g in subsets[:3]:
            ex, ey = (S.midpoint_error(g[f"{a} pred"], g.lead_lo, g.lead_hi) for a in (x, y))
            d = B.bootstrap_mean(ex - ey, g.block)
            pairs.append(dict(subset=name, comparison=f"{x} - {y}", diff=d[0], lo=d[1], hi=d[2]))
    pairs = pd.DataFrame(pairs)

    # clock sensitivity: the other SICKLE season mappings, M1 point arm only, never selected
    clock = []
    for s in O.SICKLE_SEASONS:
        g = odisha_rows(labels, s, cats)
        if not len(g):
            clock.append(dict(season=s, n_rows=0, mae=np.nan))
            continue
        p = L.pool_predictions(g, point.predict(g[cols])).pooled
        m = B.bootstrap_mean(S.midpoint_error(p, g.lead_lo, g.lead_hi), g.block)
        clock.append(dict(season=s, n_rows=len(g), mae=m[0], lo=m[1], hi=m[2]))
    clock = pd.DataFrame(clock)

    RESULTS.parent.mkdir(exist_ok=True)
    res.round(2).to_csv(RESULTS, index=False)
    pairs.round(2).to_csv(RESULTS.with_name(RESULTS.stem + "_pairs.csv"), index=False)
    clock.round(2).to_csv(RESULTS.with_name(RESULTS.stem + "_clock.csv"), index=False)
    od.to_parquet(RESULTS.with_name(RESULTS.stem + "_rows.parquet"))

    pd.set_option("display.width", 200)
    show = ["subset", "arm", "n_rows", "mae", "mae_lo", "mae_hi", "bracket_lo", "bracket_hi",
            "coverage", "cov_lo", "cov_hi", "mean_width", "transfer_gap"]  # fmt: skip
    print("\nmidpoint MAE (d), block-bootstrap CI, bracket [point, expected]; coverage = "
          f"intersection - {COV_BIAS} pts (90% target)\n")  # fmt: skip
    print(res[show].round(2).to_string(index=False))
    print("\npaired midpoint-error differences (negative = first arm better)\n")
    print(pairs.round(2).to_string(index=False))
    print(f"\nclock sensitivity (headline mapping {O.HEADLINE_SEASON}, never selected)\n")
    print(clock.round(2).to_string(index=False))
    print(f"\nwrote {RESULTS} (+ _pairs, _clock, _rows)")


if __name__ == "__main__":
    sys.exit(main())
