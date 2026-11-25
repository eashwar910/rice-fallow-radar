"""Point F: measure rule 5 (interval-label scoring) before freezing it, on SICKLE, not Odisha.

Rule 5 was the one frozen interval rule with no measurement behind it. Odisha labels are
intervals, so it decides every M2 number -- but scoring it on Odisha before the freeze would
spend Odisha labels and break D-031's ordering. So: take SICKLE's *exact* harvest dates, widen
each into a synthetic interval drawn from the Odisha label widths (the free 40% only), with the
true date uniform inside it, and rescore the published out-of-fold predictions. Three questions:

1. How biased is each way of scoring an interval label?  Intersection (rule 5 as drafted),
   midpoint and uniform-expected, for MAE and coverage, against the exact-date numbers.
2. Does it keep the arm ranking?  Spearman over arms, per draw.
3. Does it keep the stratified O1 verdict?  The paired `base+s1+pool - calendar-4+pool` gap on
   unique-date plots, which is significant under exact scoring.

Reads runs/sickle_m1_{lightgbm,conformal}_rows.parquet (written by those scripts). Dev only.
Usage: uv run python scripts/interval_rule_check.py
Writes runs/interval_rule_check.csv.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from rice_fallow_radar.eval import interval_scoring as S
from rice_fallow_radar.models import m1_baselines as B

RUNS = Path("runs")
ARMS = ["calendar-4+pool", "base+s1+pool", "base+s1+weather+pool", "all+pool", "seasonal_mean"]
REF, CHALLENGER = "calendar-4+pool", "base+s1+pool"
IVL = "pooled + by n_acc"
DRAWS = 200
SEED = 20261125


def widths() -> np.ndarray:
    lab = pd.read_parquet("data/processed/odisha_labels.parquet")
    free = lab[(lab.status == "ok") & ~lab.eval_lock]  # widths only; never a model score
    return free.interval_days.to_numpy()


def main() -> None:
    pts = pd.read_parquet(RUNS / "sickle_m1_lightgbm_rows.parquet")
    ivl = pd.read_parquet(RUNS / "sickle_m1_conformal_rows.parquet")
    assert (pts.unique_id.to_numpy() == ivl.unique_id.to_numpy()).all()
    assert (pts.as_of.to_numpy() == ivl.as_of.to_numpy()).all(), "row order differs"
    w_pool = widths()
    print(f"Odisha free-label widths: n={len(w_pool)}, median {np.median(w_pool):.0f} d")

    ids = pts.unique_id.unique()
    rng = np.random.default_rng(SEED)
    exact_cov = ((ivl[f"{IVL} lo"] <= pts.lead) & (pts.lead <= ivl[f"{IVL} hi"])).mean()
    exact = {a: np.abs(pts[a] - pts.lead).mean() for a in ARMS}
    uni = ~pts.shared_date
    e_ref, e_ch = (np.abs(pts[a] - pts.lead) for a in (REF, CHALLENGER))
    exact_gap = B.bootstrap_mean((e_ch - e_ref)[uni], pts.group[uni])

    rows = []
    for d in range(DRAWS):
        w = pd.Series(rng.choice(w_pool, len(ids)), index=ids)
        u = pd.Series(rng.uniform(0, 1, len(ids)), index=ids) * w  # truth sits u days from lo
        lo = pts.lead - pts.unique_id.map(u).to_numpy()
        hi = lo + pts.unique_id.map(w).to_numpy()
        err = {a: S.point_error(pts[a].to_numpy(), lo, hi) for a in ARMS}
        exp = {a: S.expected_error(pts[a].to_numpy(), lo, hi) for a in ARMS}
        mid = (lo + hi) / 2
        midp = {a: S.midpoint_error(pts[a].to_numpy(), lo, hi) for a in ARMS}
        p_lo, p_hi = ivl[f"{IVL} lo"].to_numpy(), ivl[f"{IVL} hi"].to_numpy()
        cov = S.covered(p_lo, p_hi, lo, hi)
        e_cov = S.expected_coverage(p_lo, p_hi, lo, hi)
        m_cov = (p_lo <= mid) & (mid <= p_hi)
        gap = err[CHALLENGER][uni] - err[REF][uni]
        rows.append(
            dict(
                draw=d,
                coverage=cov.mean(),
                expected_coverage=e_cov.mean(),
                midpoint_coverage=m_cov.mean(),
                gap_unique_midpoint=(midp[CHALLENGER][uni] - midp[REF][uni]).mean(),
                gap_unique_expected=(exp[CHALLENGER][uni] - exp[REF][uni]).mean(),
                rank_rho=spearmanr([exact[a] for a in ARMS], [err[a].mean() for a in ARMS])[0],
                gap_unique=gap.mean(),
                **{f"mae {a}": err[a].mean() for a in ARMS},
                **{f"expected {a}": exp[a].mean() for a in ARMS},
                **{f"midpoint {a}": midp[a].mean() for a in ARMS},
            )
        )
    res = pd.DataFrame(rows)
    last_gap = B.bootstrap_mean(pd.Series(gap), pts.group[uni].reset_index(drop=True))
    RUNS.mkdir(exist_ok=True)
    res.to_csv(RUNS / "interval_rule_check.csv", index=False)

    def q(x: pd.Series, fmt: str) -> str:
        return f"{x.mean():{fmt}} [{x.quantile(0.025):{fmt}}, {x.quantile(0.975):{fmt}}]"

    print(f"\n{DRAWS} draws of synthetic interval labels on {len(pts)} SICKLE dev rows")
    print("(rule-5 figures: mean over draws [2.5%, 97.5% of draws])\n")
    for a in ARMS:
        m = res[f"mae {a}"]
        shrink = exact[a] - m.mean()
        print(f"  {a:<22} exact MAE {exact[a]:5.2f}  rule-5 {q(m, '.2f')}  shrink {shrink:.2f} d")
        e, m = q(res[f"expected {a}"], ".2f"), q(res[f"midpoint {a}"], ".2f")
        print(f"  {'':<22} midpoint {m}  expected-uniform {e}")
    print(f"\ncoverage of '{IVL}': exact {exact_cov:.1%}, rule-5 {q(res.coverage, '.1%')}")
    print(f"  expected (uniform truth)       {q(res.expected_coverage, '.1%')}")
    print(f"  midpoint                       {q(res.midpoint_coverage, '.1%')}")
    rho = res.rank_rho
    print(f"arm ranking: Spearman rho {q(rho, '.2f')}, identical in {(rho > 0.999).mean():.0%}")
    print(f"\nO1 verdict on unique-date plots ({CHALLENGER} - {REF}):")
    g = exact_gap
    print(f"  exact   {g[0]:+.2f} d [{g[1]:+.2f}, {g[2]:+.2f}] (group bootstrap)")
    g = last_gap
    print(f"  rule-5  {q(res.gap_unique, '+.2f')} d")
    print(f"  rule-5, last draw, group bootstrap: {g[0]:+.2f} [{g[1]:+.2f}, {g[2]:+.2f}]")
    print(f"  gap < 0 in {(res.gap_unique < 0).mean():.0%} of draws")
    print(f"  expected-error gap {q(res.gap_unique_expected, '+.2f')} d")
    print(f"  midpoint gap {q(res.gap_unique_midpoint, '+.2f')} d")
    print(f"\nwrote {RUNS / 'interval_rule_check.csv'}")


if __name__ == "__main__":
    sys.exit(main())
