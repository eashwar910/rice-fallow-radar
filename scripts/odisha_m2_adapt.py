"""P3 adaptation (EVALUATION.md §M2 protocol step 3), developed on the free 40% only.

What can be recovered of the transfer gap, by which method, and does the interval survive?

    detectors   radar (VH drop below the smoothed peak, dB grid) / S2 (NDVI crossing from peak
                to floor, fraction grid) / fused, scored against the free hand labels.
                Selection rule, stated before scoring: lowest midpoint MAE among detectors
                that date >= 75% of free fields.
    pseudo      the chosen detector on 600 unlabelled flooded fields outside every labelled
                block (`odisha_pseudo_pull.py`) -> target-domain training rows (Lee, 2013)
    shift       TimeMatch-style: per-district calendar offset aligning the median S1 flood
                season-day of step 1's registry sample with SICKLE samba transplanting
    pheno       days since the field's own S1 flood replaces days since 1 Sep
    few-shot    free hand labels in the training folds (grouped 5-fold over 0.05 deg blocks),
                weight `W_HAND`; `in-region` is the same with no SICKLE rows at all

Adapted arms give Odisha rows their own `season_cat` ("odisha"), so the trees can learn an
Odisha clock beside the samba one instead of averaging the two. Zero-shot arms are told
`sep-feb` (pre-registered). All point forecasts pooled over issue dates (D-030).

Intervals: CQR quantiles (D-032). **before** = Mondrian offsets calibrated on held-out SICKLE
groups (the zero-shot interval); **after** = Odisha recalibration, cross-conformal over the
same block folds (each fold's offsets from the other folds' rows; Vovk 2015, Barber et al.
2021 CV+), conditioned on accumulation stratum, nonconformity on the label midpoint.

The headline adapted arm is chosen by a rule stated here before scoring: the lowest mean of the
three per-horizon (7/14/21 d) midpoint MAEs on the free 40%. It is a development choice; the
locked 60% decides whether it holds.
Usage:
    uv run python scripts/odisha_m2_adapt.py
Writes runs/odisha_m2_adapt*.csv, runs/odisha_m2_adapt_rows.parquet, configs/m2_arms.json.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from odisha_m2_sensors import SENSORS
from odisha_m2_zero_shot import COV_BIAS, LABELS, score, sickle_dev
from odisha_transplant_spread import CACHE
from odisha_transplant_spread import START as STEP1_START
from sklearn.model_selection import GroupKFold

from rice_fallow_radar.eval import interval_scoring as S
from rice_fallow_radar.eval import splits
from rice_fallow_radar.features import odisha_m1 as O
from rice_fallow_radar.features import sickle_m1 as F
from rice_fallow_radar.ingest import sickle
from rice_fallow_radar.models import m1_baselines as B
from rice_fallow_radar.models import m1_conformal as C
from rice_fallow_radar.models import m1_lightgbm as L
from rice_fallow_radar.models import m2_adapt as A

PSEUDO = Path("data/interim/odisha_pseudo")
RESULTS = Path("runs/odisha_m2_adapt.csv")
ARMS_FILE = Path("configs/m2_arms.json")
SEASON = ("2025-08-01", "2026-02-15")  # peak search start -> last possible harvest
RADAR_DB = (1.0, 2.0, 3.0, 4.0)
S2_FRAC = (0.3, 0.4, 0.5, 0.6)
MIN_DATED = 0.75
W_HAND = 3.0  # hand rows vs SICKLE rows: ~400 rows in training folds against 2,745
N_FOLDS = 5
ODISHA_CAT = "odisha"
FEATS = {
    "calendar-4": ("base",),
    "base+s1+s2": ("base", "s1", "s2"),
    "s1+s2": ("s1", "s2"),
    "pheno": ("s1", "s2", "pheno"),
}
# (feature set, training set, clock shift)
ARMS = {
    "zero-shot M1": ("calendar-4", "sickle", False),
    "zs base+s1+s2": ("base+s1+s2", "sickle", False),
    "zs s1+s2": ("s1+s2", "sickle", False),
    "zs pheno": ("pheno", "sickle", False),
    "shift calendar-4": ("calendar-4", "sickle", True),
    "shift base+s1+s2": ("base+s1+s2", "sickle", True),
    "pseudo base+s1+s2": ("base+s1+s2", "sickle+pseudo", False),
    "pseudo s1+s2": ("s1+s2", "sickle+pseudo", False),
    "pseudo pheno": ("pheno", "sickle+pseudo", False),
    "few base+s1+s2": ("base+s1+s2", "sickle+few", False),
    "few s1+s2": ("s1+s2", "sickle+few", False),
    "pseudo+few base+s1+s2": ("base+s1+s2", "sickle+pseudo+few", False),
    "pseudo+few s1+s2": ("s1+s2", "sickle+pseudo+few", False),
    "pseudo+few pheno": ("pheno", "sickle+pseudo+few", False),
    "in-region base+s1+s2": ("base+s1+s2", "few", False),
    "in-region s1+s2": ("s1+s2", "few", False),
    "pseudo-only base+s1+s2": ("base+s1+s2", "pseudo", False),
}
ZERO_SHOT_REF = "zero-shot M1"


# ---------------------------------------------------------------- inputs


def sickle_frames():
    """SICKLE dev rows with the phenological clock, and the SICKLE S1 series it came from."""
    dev, _ = sickle_dev()
    s1 = pd.read_parquet("data/interim/sickle_s1_series.parquet")
    s1 = s1[~s1.edge_clipped].dropna(subset=["vh_db"])
    dev = A.add_days_since_flood(dev, s1, "unique_id")
    dev["group"] = dev.group.astype(str)
    return dev, s1


def odisha_rows(labels, s1, s2) -> pd.DataFrame:
    od = O.add_sensors(O.build(labels), s1, s2)  # descending: the frozen headline
    od = A.add_days_since_flood(od, s1[s1.orbit_pass == "DESCENDING"], "field_id")
    return od.assign(unique_id=od.field_id, group=od.block.astype(str))


def cols_for(dev: pd.DataFrame, feat: str) -> list[str]:
    blocks = FEATS[feat]
    cols = F.block_columns(
        dev.drop(columns=[A.PHENO_COL]), tuple(b for b in blocks if b != "pheno")
    )
    cols += [A.PHENO_COL] if "pheno" in blocks else []
    return cols + (["season_cat"] if "base" in blocks else [])


def with_cat(df: pd.DataFrame, cats, own: bool) -> pd.DataFrame:
    """`season_cat` on a shared category list; Odisha rows get their own level when `own`."""
    s = pd.Series(ODISHA_CAT, index=df.index) if own else df.season
    return df.assign(season_cat=pd.Categorical(s, categories=cats))


# ---------------------------------------------------------------- detectors and shift


def detector_check(labels, s1, s2) -> tuple[pd.DataFrame, tuple]:
    free = labels[(labels.status == "ok") & ~labels.eval_lock.astype(bool)]
    cands = [("radar", np.nan, d) for d in RADAR_DB] + [("s2", f, np.nan) for f in S2_FRAC]
    cands += [("fused", f, d) for f in S2_FRAC for d in RADAR_DB]
    out = []
    for method, f, p in cands:
        det = A.detect(free, s1, s2, method, f, p, *SEASON)
        m = free.merge(
            det[["field_id", "last_green", "first_brown"]], on="field_id", suffixes=("", "_d")
        )
        mid = m.last_green + (m.first_brown - m.last_green) / 2
        mid_d = m.last_green_d + (m.first_brown_d - m.last_green_d) / 2
        err = ((mid_d - mid) / pd.Timedelta(days=1)).to_numpy()
        e = B.bootstrap_mean(np.abs(err), m.block) if len(m) else (np.nan,) * 3
        cov = (
            S.covered(
                m.last_green_d.map(pd.Timestamp.toordinal),
                m.first_brown_d.map(pd.Timestamp.toordinal),
                m.last_green.map(pd.Timestamp.toordinal),
                m.first_brown.map(pd.Timestamp.toordinal),
            ).mean()
            if len(m)
            else np.nan
        )
        out.append(
            dict(
                method=method,
                s2_frac=f,
                radar_db=p,
                dated=len(m) / len(free),
                n=len(m),
                mae=e[0],
                mae_lo=e[1],
                mae_hi=e[2],
                bias=np.median(err) if len(m) else np.nan,
                intersects=cov,
                width=float(m.interval_days.mean()) if len(m) else np.nan,
            )
        )
    res = pd.DataFrame(out)
    ok = res[res.dated >= MIN_DATED]
    best = ok.loc[ok.mae.idxmin()]
    return res, (best.method, best.s2_frac, best.radar_db)


def shifts(dev_labels: pd.DataFrame, pseudo: pd.DataFrame) -> pd.DataFrame:
    """Per-district clock offsets (days): flood alignment (headline) and harvest alignment."""
    from odisha_transplant_spread import THRESHOLD, flood_dates, sample

    reg = sample(2000)[["field_id", "district"]]
    cached = pd.concat(pd.read_parquet(p) for p in sorted(CACHE.glob("n2000_*.parquet")))
    fl = flood_dates(cached[cached.orbit_pass == "DESCENDING"], THRESHOLD)
    sep1 = (pd.Timestamp("2025-09-01") - pd.Timestamp(STEP1_START)).days
    od_flood = reg.assign(sd=reg.field_id.map(fl) - sep1)  # days since 1 Sep
    samba = dev_labels[dev_labels.STANDARD_SEASON == "sep-feb"]
    start = pd.to_datetime(dict(year=samba.YEAR.astype(int), month=9, day=1))
    src_tp = (samba.transplanting - start).dt.days
    src_hv = (samba.harvest - start).dt.days
    pmid = (pseudo.midpoint - pd.Timestamp("2025-09-01")).dt.days
    out = []
    for d, g in od_flood.groupby("district"):
        out.append(
            dict(
                district=d,
                flood_median_od=g.sd.median(),
                transplant_median_sickle=src_tp.median(),
                delta_flood=A.flood_shift(g.sd, src_tp),
                delta_harvest=A.flood_shift(pmid[pseudo.district == d], src_hv),
            )
        )
    return pd.DataFrame(out).set_index("district")


# ---------------------------------------------------------------- training


def fit_point(train: pd.DataFrame, cols: list[str]):
    train = train.reset_index(drop=True)
    return L._fit(train, cols, L._tune(train, cols, splits.SEED), splits.SEED)


def train_set(spec: str, dev, pseudo_rows, hand_tr) -> pd.DataFrame:
    parts = []
    if "sickle" in spec:
        parts.append(dev.assign(weight=1.0))
    if "pseudo" in spec:
        parts.append(pseudo_rows.assign(weight=1.0))
    if "few" in spec:
        parts.append(hand_tr.assign(weight=W_HAND))
    return pd.concat(parts, ignore_index=True)


def run_arm(name, dev, hand, target, pseudo_rows, cats, delta, folds=None):
    """Pooled point forecasts and CQR quantiles on `target` for one arm, plus 'before' offsets.

    Few-shot arms train on the hand-labelled Odisha rows `hand`. With `folds` (development),
    `hand` *is* `target` and every fold is predicted by a model that never saw it; without
    (the unlock), the model trains on all of `hand` and predicts `target`.
    """
    feat, spec, shift = ARMS[name]
    cols = cols_for(dev, feat)
    own = spec != "sickle"
    d = with_cat(dev, cats, False)
    p = with_cat(pseudo_rows, cats, own)
    o = with_cat(target, cats, own)
    h = with_cat(hand, cats, own)
    if shift:
        o = A.shift_clock(o, o.district.map(delta))
    point = np.full(len(o), np.nan)
    q = np.full((len(o), 3), np.nan)
    cv = "few" in spec and folds is not None
    for k in sorted(folds.unique()) if cv else [None]:
        te = (folds == k).to_numpy() if cv else np.ones(len(o), bool)
        tr = train_set(spec, d, p, h[~te] if cv else h)
        point[te] = fit_point(tr, cols).predict(o.loc[te, cols])
        q[te] = C.predict(C.fit(tr.reset_index(drop=True), cols), o[te], cols)
    out = {"pred": L.pool_predictions(o, point).pooled.to_numpy()}
    pq, n_acc = C.pooled(o, q)
    out |= {"q_lo": pq[:, 0], "q_hi": pq[:, 2], "n_acc": n_acc}
    if (
        "few" not in spec and "sickle" in spec
    ):  # 'before': quantiles on 2/3 of SICKLE groups, offsets on 1/3
        inner = splits.assign_folds(d, n=3, seed=splits.SEED + 1)
        tr_s, cal = d[inner != 0], d[inner == 0]
        tr = train_set(spec, tr_s, p, o.iloc[:0])
        qm = C.fit(tr.reset_index(drop=True), cols)
        pc, acc_c = C.pooled(cal, C.predict(qm, cal, cols))
        tbl = C.offsets_by_stratum(pc[:, 0], pc[:, 2], cal.lead.to_numpy(), C.acc_stratum(acc_c))
        pb, acc_b = C.pooled(o, C.predict(qm, o, cols))
        ivl = C.widen(pb, C.apply_offsets(tbl, C.acc_stratum(acc_b)))
        out |= {
            "before_lo": ivl[:, 0],
            "before_hi": ivl[:, 2],
            "after_q_lo": pb[:, 0],
            "after_q_hi": pb[:, 2],
        }
    else:
        out |= {"after_q_lo": pq[:, 0], "after_q_hi": pq[:, 2]}
    return name, out


def recalibrate(od: pd.DataFrame, q_lo, q_hi, folds: pd.Series) -> np.ndarray:
    """Cross-conformal Odisha offsets: each fold widened by offsets fitted on the other folds."""
    mid = ((od.lead_lo + od.lead_hi) / 2).to_numpy()
    strata = C.acc_stratum(od.n_acc.to_numpy())
    lo, hi = np.empty(len(od)), np.empty(len(od))
    q = np.column_stack([q_lo, (q_lo + q_hi) / 2, q_hi])
    for k in sorted(folds.unique()):
        te = (folds == k).to_numpy()
        tbl = C.offsets_by_stratum(q_lo[~te], q_hi[~te], mid[~te], np.asarray(strata)[~te])
        ivl = C.widen(q[te], C.apply_offsets(tbl, np.asarray(strata)[te]))
        lo[te], hi[te] = ivl[:, 0], ivl[:, 2]
    return np.column_stack([lo, hi])


# ---------------------------------------------------------------- SICKLE reference


def sickle_reference(dev: pd.DataFrame, cats, widths: np.ndarray, draws: int = 50) -> pd.DataFrame:
    """SICKLE out-of-fold pooled MAE per horizon, exact and under the same synthetic widening."""
    fold = splits.assign_folds(dev)
    d = with_cat(dev, cats, False)
    rng = np.random.default_rng(20261125)
    ids = d.unique_id.unique()
    out = []
    for feat in FEATS:
        pred = L.oof_predict(d, cols_for(dev, feat), fold)[0]
        pooled = L.pool_predictions(d, pred).pooled.to_numpy()
        mids = []
        for _ in range(draws):
            w = pd.Series(rng.choice(widths, len(ids)), index=ids)
            u = pd.Series(rng.uniform(0, 1, len(ids)), index=ids) * w
            mid = d.lead - d.unique_id.map(u).to_numpy() + d.unique_id.map(w).to_numpy() / 2
            mids.append(np.abs(pooled - mid))
        mid_err = np.mean(mids, axis=0)
        for name, m in subsets_mask(d):
            e = B.bootstrap_mean(mid_err[m], d.group[m])
            out.append(
                dict(
                    feat=feat,
                    subset=name,
                    sickle_exact=np.abs(pooled - d.lead)[m].mean(),
                    sickle_mid=e[0],
                    sickle_mid_lo=e[1],
                    sickle_mid_hi=e[2],
                )
            )
    return pd.DataFrame(out)


def subsets_mask(df: pd.DataFrame):
    yield "all leads", np.ones(len(df), bool)
    for h, (lo, hi) in F.LEAD_BUCKETS.items():
        yield f"lead {h}d", df.lead.between(lo, hi).to_numpy()


# ---------------------------------------------------------------- main


def main() -> None:
    labels = pd.read_parquet(LABELS)
    s1, s2 = (pd.read_parquet(SENSORS / f"{k}.parquet") for k in ("s1", "s2"))
    ps_fields = pd.read_parquet(PSEUDO / "fields.parquet")
    ps1, ps2 = (pd.read_parquet(PSEUDO / f"{k}.parquet") for k in ("s1", "s2"))

    det_res, (method, frac, db) = detector_check(labels, s1, s2)
    print("harvest detectors on the free hand labels (midpoint error, d):")
    print(det_res.round(2).to_string(index=False))
    print(f"chosen by the stated rule: {method} (S2 fraction {frac}, radar drop {db} dB)")
    pseudo = A.detect(ps_fields, ps1, ps2, method, frac, db, *SEASON)
    print(
        f"pseudo-labels: {len(pseudo)} of {len(ps_fields)} pool fields dated "
        f"({pseudo.source.value_counts().to_dict()}), "
        f"{pseudo.groupby('district').size().to_dict()}"
    )

    dev, sickle_s1 = sickle_frames()
    dev_labels = splits.dev_test(sickle.exact_labels())[0]
    sh = shifts(dev_labels, pseudo)
    print("\nclock offsets (days to subtract from the Odisha clock):")
    print(sh.round(1).to_string())
    delta = sh.delta_flood

    # does the S1 flood rule find SICKLE's transplanting? (validates the phenological clock)
    fl = {u: A.flood_date(g.sort_values("date")) for u, g in sickle_s1.groupby("unique_id")}
    tp = dev_labels.set_index("UNIQUE_ID").transplanting
    gap = pd.Series({u: (fl[u] - tp[u]).days for u in tp.index if u in fl and pd.notna(fl[u])})
    print(
        f"\nSICKLE dev: S1 flood found on {len(gap)}/{len(tp)} samples; flood - transplanting "
        f"median {gap.median():+.0f} d, |.| <= 15 d on {(gap.abs() <= 15).mean():.0%}"
    )

    od = odisha_rows(labels, s1, s2)
    pseudo_rows = odisha_rows(pseudo, ps1, ps2)
    assert not od.eval_lock.any(), "a locked row reached development"
    assert not set(pseudo_rows.block) & set(labels.block), "a pseudo field shares a labelled block"
    cats = list(dev.season.astype("category").cat.categories) + [ODISHA_CAT]
    blocks = od.block.to_numpy()
    folds = pd.Series(np.zeros(len(od), int), index=od.index)
    for k, (_, te) in enumerate(GroupKFold(N_FOLDS).split(od, groups=blocks)):
        folds.iloc[te] = k
    print(
        f"\nOdisha free 40%: {len(od)} rows, {od.field_id.nunique()} fields, "
        f"{od.block.nunique()} blocks in {N_FOLDS} folds; pseudo rows {len(pseudo_rows)} "
        f"from {pseudo_rows.field_id.nunique()} fields"
    )

    done = Parallel(n_jobs=-1, verbose=0)(
        delayed(run_arm)(n, dev, od, od, pseudo_rows, cats, delta, folds) for n in ARMS
    )
    for name, out in done:
        od[f"{name} pred"] = out["pred"]
        od["n_acc"] = out["n_acc"]
        after = recalibrate(od, out["after_q_lo"], out["after_q_hi"], folds)
        od[f"{name} lo"], od[f"{name} hi"] = after[:, 0], after[:, 1]
        if "before_lo" in out:
            od[f"{name} [before] pred"] = out["pred"]
            od[f"{name} [before] lo"], od[f"{name} [before] hi"] = (
                out["before_lo"],
                out["before_hi"],
            )
    zs = pd.read_parquet("runs/odisha_m2_zero_shot_rows.parquet")
    key = ["field_id", "as_of"]
    m = od[key].merge(
        zs[key + ["Odisha-calendar pred", "Odisha-calendar lo", "Odisha-calendar hi"]],
        on=key,
        how="left",
    )
    assert m["Odisha-calendar pred"].notna().all(), "step 2 rows do not match"
    for c in ("pred", "lo", "hi"):
        od[f"Odisha-calendar {c}"] = m[f"Odisha-calendar {c}"].to_numpy()
    od["vh_peak_rule pred"] = L.pool_predictions(od, B.vh_peak_rule(dev, od)).pooled

    names = list(ARMS) + [f"{a} [before]" for a in ARMS if f"{a} [before] pred" in od]
    names += ["Odisha-calendar", "vh_peak_rule"]
    subsets = [("all leads", od)] + [(f"district {d}", g) for d, g in od.groupby("district")]
    subsets += [
        (f"lead {h}d", od[od.lead.between(lo, hi)]) for h, (lo, hi) in F.LEAD_BUCKETS.items()
    ]
    res = pd.DataFrame([dict(subset=s, **score(g, a)) for s, g in subsets for a in names])

    widths = labels[
        (labels.status == "ok") & ~labels.eval_lock.astype(bool)
    ].interval_days.to_numpy()
    ref = sickle_reference(dev, cats, widths)
    res["feat"] = res.arm.map(lambda a: ARMS.get(a.replace(" [before]", ""), (None,))[0])
    res = res.merge(ref, on=["feat", "subset"], how="left")
    res["transfer_gap"] = res.mae - res.sickle_mid

    # paired: every arm against zero-shot M1, same rows
    pairs = []
    for s, g in subsets:
        e0 = S.midpoint_error(g[f"{ZERO_SHOT_REF} pred"], g.lead_lo, g.lead_hi)
        for a in [n for n in names if "[before]" not in n and n != ZERO_SHOT_REF]:
            e = S.midpoint_error(g[f"{a} pred"], g.lead_lo, g.lead_hi)
            dd = B.bootstrap_mean(e - e0, g.block)
            pairs.append(
                dict(subset=s, comparison=f"{a} - {ZERO_SHOT_REF}", diff=dd[0], lo=dd[1], hi=dd[2])
            )
    pairs = pd.DataFrame(pairs)

    horizon = res[res.subset.str.startswith("lead ") & ~res.arm.str.contains("before")]
    per_h = horizon.groupby("arm").mae.mean().sort_values()
    adapted = [a for a in per_h.index if a in ARMS and ARMS[a][1] != "sickle" or "shift" in a]
    headline = next(a for a in per_h.index if a in adapted)
    best_zs = next(
        a for a in per_h.index if a in ARMS and ARMS[a][1] == "sickle" and "shift" not in a
    )

    RESULTS.parent.mkdir(exist_ok=True)
    res.round(2).to_csv(RESULTS, index=False)
    pairs.round(2).to_csv(RESULTS.with_name(RESULTS.stem + "_pairs.csv"), index=False)
    det_res.round(2).to_csv(RESULTS.with_name(RESULTS.stem + "_detectors.csv"), index=False)
    sh.round(2).to_csv(RESULTS.with_name(RESULTS.stem + "_shift.csv"))
    od.to_parquet(RESULTS.with_name(RESULTS.stem + "_rows.parquet"))
    pseudo.to_parquet(PSEUDO / "pseudo_labels.parquet")
    frozen = dict(
        frozen_on=str(pd.Timestamp.now().date()),
        rule="headline adapted arm = lowest mean per-horizon (7/14/21 d) midpoint MAE, free 40%",
        detector=dict(
            method=method,
            s2_frac=None if pd.isna(frac) else float(frac),
            radar_db=None if pd.isna(db) else float(db),
        ),
        shift_days=sh.delta_flood.round(1).to_dict(),
        w_hand=W_HAND,
        headline_adapted=headline,
        best_zero_shot=best_zs,
        arms={a: dict(feat=v[0], train=v[1], shift=v[2]) for a, v in ARMS.items()},
        per_horizon_mean_mae_free40=per_h.round(2).to_dict(),
    )
    ARMS_FILE.write_text(json.dumps(frozen, indent=2) + "\n")

    pd.set_option("display.width", 250)
    fmt = "{0.mae:5.1f} [{0.mae_lo:.1f},{0.mae_hi:.1f}]"
    piv = res.assign(v=res.apply(fmt.format, axis=1)).pivot(
        index="arm", columns="subset", values="v"
    )
    print("\nmidpoint MAE (d) [block CI], free 40%\n")
    print(piv.loc[per_h.index.tolist() + [n for n in names if n not in per_h.index]].to_string())
    cov = res[
        res.coverage.notna() & (res.subset.isin(["all leads", "lead 7d", "lead 14d", "lead 21d"]))
    ]
    cv = cov.assign(v=cov.apply(lambda r: f"{r.coverage:5.1f} ({r.mean_width:4.1f} d)", axis=1))
    print(f"\ncoverage (intersection - {COV_BIAS} pts, target 90) and mean width\n")
    print(cv.pivot(index="arm", columns="subset", values="v").to_string())
    print("\ntransfer gap (Odisha midpoint MAE - SICKLE midpoint MAE, same feature set), d\n")
    tg = res[
        res.feat.notna()
        & ~res.arm.str.contains("before")
        & res.subset.isin(["all leads", "lead 7d", "lead 14d", "lead 21d"])
    ]
    print(tg.pivot(index="arm", columns="subset", values="transfer_gap").round(1).to_string())
    print(f"\nheadline adapted arm (stated rule): {headline}; best zero-shot arm: {best_zs}")
    print(f"wrote {RESULTS} (+ _pairs, _detectors, _shift, _rows), {ARMS_FILE}")


if __name__ == "__main__":
    sys.exit(main())
