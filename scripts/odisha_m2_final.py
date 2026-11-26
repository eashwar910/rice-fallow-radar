"""P3 step 4 (EVALUATION.md §M2 protocol): the **one unlock** of the Odisha locked 60%, and the
CSISA Balasore 2018 secondary set. Numbers drawn here are spent.

Every arm in `configs/m2_arms.json` (frozen by `odisha_m2_adapt.py` and tagged `m2-arms-frozen`
before this script ever ran) is scored once, with no choice made after seeing a locked number:

* models train exactly as in development, except that few-shot arms see **all** free 40% hand
  rows (development held one fold out);
* Odisha interval recalibration uses all free 40% rows as the calibration set (their quantiles
  out of sample: cross-validated for few-shot arms, never-seen for the rest), applied to the
  locked rows by accumulation stratum; 'before' is the SICKLE-calibrated interval;
* the detector, the clock shift and `W_HAND` are read from the frozen file, not re-derived.

CSISA Balasore (secondary, provisional on the licence, OQ #14): unit = 3-dp cell, label = the
cell's median reported harvest date `d` as `[d - tau, d + tau]`, tau in {0, 3, 5, 7, 10}, headline
tau = 7; CIs bootstrap **villages**; coverage corrected by the bias of intersection coverage for
width 2 tau, re-measured on SICKLE dev (rule 2). The Odisha-calendar arm is built from this same
survey, so on this set it is in-sample: a ceiling for "one date per district", not a baseline.
Usage:
    uv run python scripts/odisha_m2_final.py
Writes runs/odisha_m2_final*.csv and runs/odisha_m2_final_rows.parquet.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from odisha_m2_adapt import (
    ARMS,
    ARMS_FILE,
    N_FOLDS,
    ODISHA_CAT,
    PSEUDO,
    ZERO_SHOT_REF,
    odisha_rows,
    run_arm,
    sickle_frames,
)
from odisha_m2_sensors import SENSORS
from odisha_m2_zero_shot import CALENDAR_PRIOR, COV_BIAS, CSISA, LABELS, score
from sklearn.model_selection import GroupKFold

from rice_fallow_radar.eval import interval_scoring as S
from rice_fallow_radar.features import odisha_calendar as OC
from rice_fallow_radar.features import odisha_m1 as O
from rice_fallow_radar.features import sickle_m1 as F
from rice_fallow_radar.models import m1_baselines as B
from rice_fallow_radar.models import m1_conformal as C
from rice_fallow_radar.models import m1_lightgbm as L
from rice_fallow_radar.models import m2_adapt as A

RESULTS = Path("runs/odisha_m2_final.csv")
CSISA_DIR = Path("data/interim/csisa_balasore")
TAUS, TAU = (0, 3, 5, 7, 10), 7


def calendar(rows: pd.DataFrame, csisa: pd.DataFrame, prior_of) -> pd.DataFrame:
    out = pd.DataFrame(index=rows.index, columns=["pred", "lo", "hi"], dtype=float)
    yr = rows.last_green.map(lambda d: d.year if d.month >= 6 else d.year - 1)
    for (dist, y), g in rows.groupby([rows.district, yr]):
        f = OC.zero_shot_harvest(OC.prior(csisa, prior_of[dist]), int(y))
        for k, key in (("pred", "harvest_date"), ("lo", "lower"), ("hi", "upper")):
            out.loc[g.index, k] = (f[key] - g.as_of).dt.days
    return out


def offsets(free: pd.DataFrame, q_lo, q_hi) -> pd.Series:
    mid = ((free.lead_lo + free.lead_hi) / 2).to_numpy()
    return C.offsets_by_stratum(q_lo, q_hi, mid, C.acc_stratum(free.n_acc.to_numpy()))


def widen(rows: pd.DataFrame, q_lo, q_hi, tbl: pd.Series) -> np.ndarray:
    q = np.column_stack([q_lo, (q_lo + q_hi) / 2, q_hi])
    return C.widen(q, C.apply_offsets(tbl, C.acc_stratum(rows.n_acc.to_numpy())))


def calibration(dev, free, pseudo_rows, cats, delta, folds) -> dict:
    """Out-of-sample quantiles on the free 40% for every arm: the Odisha calibration set."""
    jobs = [delayed(run_arm)(n, dev, free, free, pseudo_rows, cats, delta, folds) for n in ARMS]
    return dict(Parallel(n_jobs=-1)(jobs))


def forecast(target, cal, dev, free, pseudo_rows, cats, delta):
    """Every arm on `target`: pooled point, 'before' interval, Odisha-recalibrated interval."""
    jobs = [delayed(run_arm)(n, dev, free, target, pseudo_rows, cats, delta) for n in ARMS]
    tgt = dict(Parallel(n_jobs=-1)(jobs))
    free = free.assign(n_acc=cal[ZERO_SHOT_REF]["n_acc"])
    target = target.assign(n_acc=tgt[ZERO_SHOT_REF]["n_acc"])
    for n in ARMS:
        c, t = cal[n], tgt[n]
        tbl = offsets(free, c["after_q_lo"], c["after_q_hi"])
        ivl = widen(target, t["after_q_lo"], t["after_q_hi"], tbl)
        target[f"{n} pred"], target[f"{n} lo"], target[f"{n} hi"] = t["pred"], ivl[:, 0], ivl[:, 2]
        if "before_lo" in t:
            target[f"{n} [before] pred"] = t["pred"]
            target[f"{n} [before] lo"], target[f"{n} [before] hi"] = t["before_lo"], t["before_hi"]
    target["vh_peak_rule pred"] = L.pool_predictions(target, B.vh_peak_rule(dev, target)).pooled
    return target


def cov_bias_for_width(tau: float, draws: int = 50) -> float:
    """Intersection-coverage bias (points) for labels `[d - tau, d + tau]`,
    d = truth + U(-tau, tau), measured on SICKLE dev with D-032's published intervals
    (EVALUATION rule 2)."""
    r = pd.read_parquet("runs/sickle_m1_conformal_rows.parquet")
    lo, hi, y = r["pooled + by n_acc lo"], r["pooled + by n_acc hi"], r.lead
    exact = ((lo <= y) & (y <= hi)).mean()
    rng = np.random.default_rng(20261126)
    got = [
        S.covered(lo, hi, (d := y + rng.uniform(-tau, tau, len(y))) - tau, d + tau).mean()
        for _ in range(draws)
    ]
    return 100 * (float(np.mean(got)) - exact)


def csisa_rows(cells: pd.DataFrame, csisa: pd.DataFrame) -> pd.DataFrame:
    c = OC.kharif_transplanted(csisa, "Balasore")
    c = c[c.year == 2018].assign(
        field_id=[f"csisa-{a:.3f}-{b:.3f}" for a, b in zip(c.lat, c.lon, strict=True)]
    )
    per = (
        c.groupby("field_id")
        .agg(
            d=("harvest_date", "median"),
            village=("village", "first"),
            n_farmers=("harvest_date", "size"),
        )
        .reset_index()
    )
    per["d"] = per.d.dt.round("D")
    lab = per.assign(
        district="baleswar",
        stratum="C",
        block=per.village,
        eval_lock=False,
        status="ok",
        last_green=per.d,
        first_brown=per.d,
        midpoint=per.d,
    )
    assert set(lab.field_id) <= set(cells.field_id), "a CSISA cell was not pulled"
    return lab


def subsets(df):
    yield "all leads", df
    for d, g in df.groupby("district"):
        yield f"district {d}", g
    for h, (lo, hi) in F.LEAD_BUCKETS.items():
        yield f"lead {h}d", df[df.lead.between(lo, hi)]


def main() -> None:
    frozen = json.loads(ARMS_FILE.read_text())
    assert set(frozen["arms"]) == set(ARMS), "the arm list changed after the freeze"
    labels, csisa = pd.read_parquet(LABELS), pd.read_parquet(CSISA)
    s1, s2 = (pd.read_parquet(SENSORS / f"{k}.parquet") for k in ("s1", "s2"))
    ps1, ps2 = (pd.read_parquet(PSEUDO / f"{k}.parquet") for k in ("s1", "s2"))
    pseudo = pd.read_parquet(PSEUDO / "pseudo_labels.parquet")
    delta = pd.Series(frozen["shift_days"])
    dev, _ = sickle_frames()
    cats = list(dev.season.astype("category").cat.categories) + [ODISHA_CAT]

    free = odisha_rows(labels, s1, s2)
    built = O.build(labels, include_locked=True)  # the unlock: the only call with include_locked
    locked_lab = labels[labels.eval_lock.astype(bool)]
    locked = O.add_sensors(built[built.eval_lock].reset_index(drop=True), s1, s2)
    locked = A.add_days_since_flood(locked, s1[s1.orbit_pass == "DESCENDING"], "field_id")
    locked = locked.assign(unique_id=locked.field_id, group=locked.block.astype(str))
    assert not set(locked.field_id) & set(free.field_id), "free and locked fields overlap"
    pseudo_rows = odisha_rows(pseudo, ps1, ps2)
    assert not set(pseudo_rows.block) & set(labels.block), "a pseudo field shares a labelled block"
    folds = pd.Series(0, index=free.index)
    for k, (_, te) in enumerate(GroupKFold(N_FOLDS).split(free, groups=free.block)):
        folds.iloc[te] = k
    print(
        f"unlock: {locked.field_id.nunique()} locked fields ({locked_lab.field_id.nunique()} "
        f"labelled ok), {locked.block.nunique()} blocks, {len(locked)} rows"
    )

    cal_q = calibration(dev, free, pseudo_rows, cats, delta, folds)
    od = forecast(locked, cal_q, dev, free, pseudo_rows, cats, delta)
    cal = calendar(od, csisa, CALENDAR_PRIOR)
    for c in ("pred", "lo", "hi"):
        od[f"Odisha-calendar {c}"] = cal[c]
    names = list(ARMS) + [f"{a} [before]" for a in ARMS if f"{a} [before] pred" in od]
    names += ["Odisha-calendar", "vh_peak_rule"]
    res = pd.DataFrame(
        [dict(subset=s, **score(g, a)) for s, g in subsets(od) for a in names if len(g)]
    )
    ref = pd.read_csv("runs/odisha_m2_adapt.csv")[["arm", "subset", "sickle_mid", "mae"]]
    ref = ref.rename(columns={"mae": "free40_mae"})
    res = res.merge(ref, on=["arm", "subset"], how="left")
    res["transfer_gap"] = res.mae - res.sickle_mid
    zs = res[res.arm == ZERO_SHOT_REF].set_index("subset").mae
    res["gap_recovered"] = (zs.reindex(res.subset).to_numpy() - res.mae) / (
        zs.reindex(res.subset).to_numpy() - res.sickle_mid
    )

    head, best_zs = frozen["headline_adapted"], frozen["best_zero_shot"]
    pairs = []
    for s, g in subsets(od):
        for x, y in [
            (head, ZERO_SHOT_REF),
            (head, best_zs),
            (head, "Odisha-calendar"),
            (best_zs, ZERO_SHOT_REF),
            (best_zs, "Odisha-calendar"),
        ] + [(a, ZERO_SHOT_REF) for a in ARMS if a not in (head, best_zs, ZERO_SHOT_REF)]:
            ex, ey = (S.midpoint_error(g[f"{a} pred"], g.lead_lo, g.lead_hi) for a in (x, y))
            d = B.bootstrap_mean(ex - ey, g.block)
            pairs.append(dict(subset=s, comparison=f"{x} - {y}", diff=d[0], lo=d[1], hi=d[2]))
    pairs = pd.DataFrame(pairs)

    # ---- CSISA Balasore 2018, secondary
    cells = pd.read_parquet(CSISA_DIR / "cells.parquet")
    cs1, cs2 = (pd.read_parquet(CSISA_DIR / f"{k}.parquet") for k in ("s1", "s2"))
    clab = csisa_rows(cells, csisa)
    crow = O.add_sensors(O.build(clab), cs1, cs2)
    crow = A.add_days_since_flood(crow, cs1[cs1.orbit_pass == "DESCENDING"], "field_id")
    crow = crow.assign(unique_id=crow.field_id, group=crow.block.astype(str))
    crow = forecast(crow, cal_q, dev, free, pseudo_rows, cats, delta)
    ccal = calendar(crow, csisa, {"baleswar": "Balasore"})
    for c in ("pred", "lo", "hi"):
        crow[f"Odisha-calendar {c}"] = ccal[c]
    cres = []
    for tau in TAUS:
        bias = cov_bias_for_width(tau)
        g = crow.assign(lead_lo=crow.lead - tau, lead_hi=crow.lead + tau)
        for s, sub in subsets(g):
            if s.startswith("district"):
                continue
            for a in [n for n in names if "[before]" not in n]:
                r = score(sub, a)  # applies the Odisha 3.0-point correction; replaced below
                if "coverage" in r:
                    for k in ("coverage", "cov_lo", "cov_hi"):
                        r[k] = r[k] + COV_BIAS - bias
                cres.append(dict(tau=tau, cov_bias=bias, subset=s, **r))
    cres = pd.DataFrame(cres)
    print(
        f"CSISA Balasore 2018: {crow.field_id.nunique()} cells, {crow.block.nunique()} villages, "
        f"{len(crow)} rows"
    )

    res.round(2).to_csv(RESULTS, index=False)
    pairs.round(2).to_csv(RESULTS.with_name(RESULTS.stem + "_pairs.csv"), index=False)
    cres.round(2).to_csv(RESULTS.with_name(RESULTS.stem + "_csisa.csv"), index=False)
    od.to_parquet(RESULTS.with_name(RESULTS.stem + "_rows.parquet"))
    crow.to_parquet(RESULTS.with_name(RESULTS.stem + "_csisa_rows.parquet"))

    pd.set_option("display.width", 250)
    order = list(frozen["per_horizon_mean_mae_free40"]) + [
        n for n in names if n not in frozen["per_horizon_mean_mae_free40"]
    ]
    fmt = "{0.mae:5.1f} [{0.mae_lo:.1f},{0.mae_hi:.1f}]"
    piv = res.assign(v=res.apply(fmt.format, axis=1)).pivot(
        index="arm", columns="subset", values="v"
    )
    print("\nLOCKED 60%: midpoint MAE (d) [block CI]\n")
    print(piv.reindex([o for o in order if o in piv.index]).to_string())
    cv = res[
        res.coverage.notna() & res.subset.isin(["all leads", "lead 7d", "lead 14d", "lead 21d"])
    ]
    cv = cv.assign(
        v=cv.apply(
            lambda r: f"{r.coverage:5.1f} [{r.cov_lo:.0f},{r.cov_hi:.0f}] ({r.mean_width:4.1f} d)",
            axis=1,
        )
    )
    print(f"\nLOCKED 60%: coverage (intersection - {COV_BIAS} pts, target 90) [CI] (mean width)\n")
    print(cv.pivot(index="arm", columns="subset", values="v").to_string())
    tg = res[
        res.sickle_mid.notna() & res.subset.isin(["all leads", "lead 7d", "lead 14d", "lead 21d"])
    ]
    print("\nLOCKED 60%: transfer gap (d) and share of the zero-shot gap recovered\n")
    print(
        tg.pivot(index="arm", columns="subset", values=["transfer_gap", "gap_recovered"])
        .round(2)
        .to_string()
    )
    print("\nLOCKED 60%: paired midpoint-error differences (negative = first arm better)\n")
    keyp = pairs[pairs.comparison.str.startswith((head, best_zs))]
    print(keyp.pivot(index="comparison", columns="subset", values="diff").round(2).to_string())
    pp = keyp.assign(v=keyp.apply(lambda r: f"{r['diff']:+.1f} [{r.lo:+.1f},{r.hi:+.1f}]", 1))
    print(pp.pivot(index="comparison", columns="subset", values="v").to_string())
    h = cres[(cres.tau == TAU)]
    hv = h.assign(v=h.apply(fmt.format, axis=1)).pivot(index="arm", columns="subset", values="v")
    print(f"\nCSISA Balasore 2018 (secondary), tau = {TAU}: midpoint MAE (d) [village CI]\n")
    print(hv.reindex([o for o in order if o in hv.index]).to_string())
    hc = h[h.coverage.notna() & (h.subset == "all leads")][
        ["arm", "coverage", "cov_lo", "cov_hi", "mean_width"]
    ]
    print("\nCSISA coverage, all leads, tau = 7 (corrected for width 14 d)\n")
    print(hc.round(1).to_string(index=False))
    print(f"\nheadline adapted arm (frozen): {head}; best zero-shot (frozen): {best_zs}")
    print(f"wrote {RESULTS} (+ _pairs, _csisa, _rows, _csisa_rows)")


if __name__ == "__main__":
    sys.exit(main())
