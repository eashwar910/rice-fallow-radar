"""P3 step 3: zero-shot *sensor* arms on the free 40%, against step 2's calendar arms.

Same rows, same scoring and same reference numbers as `odisha_m2_zero_shot.py` (imported from
it), so every arm in the two tables is comparable. All arms are trained on all SICKLE dev and
pooled over issue dates (D-030). Sensor features are SICKLE's own definitions, built from what was
available on each `as_of` (`features.odisha_m1.add_sensors`), descending passes (frozen headline;
all passes is the sensitivity).

    calendar-4      step 2's zero-shot M1, repeated here as the like-for-like reference
    base+s1         the clock plus radar (SICKLE's best sensor arm, D-031's prediction)
    base+s1+s2      the clock plus radar and optical
    s1 only         radar, no clock: cannot carry Tamil Nadu's calendar by construction
    s1+s2           radar and optical, no clock
    vh_peak_rule    harvest = VH peak + SICKLE's median peak-to-harvest lag (m1_baselines)

Weather is left out: no Odisha weather pull yet. The no-clock arms are development on the free
40%, not pre-registered; they are reported as the diagnostic for "was the gap the clock?".
Usage:
    uv run python scripts/odisha_m2_sensors.py
Writes runs/odisha_m2_sensors.csv (+ _pairs.csv, _rows.parquet).
"""

import sys
from pathlib import Path

import pandas as pd
from odisha_m2_zero_shot import LABELS, score, sickle_dev

from rice_fallow_radar.eval import interval_scoring as S
from rice_fallow_radar.eval import splits
from rice_fallow_radar.features import odisha_m1 as O
from rice_fallow_radar.features import sickle_m1 as F
from rice_fallow_radar.models import m1_baselines as B
from rice_fallow_radar.models import m1_lightgbm as L

SENSORS = Path("data/interim/odisha_sensors")
RESULTS = Path("runs/odisha_m2_sensors.csv")
ARMS = {
    "calendar-4": ("base",),
    "base+s1": ("base", "s1"),
    "base+s1+s2": ("base", "s1", "s2"),
    "s1 only": ("s1",),
    "s1+s2": ("s1", "s2"),
}
REF = "calendar-4"


def rows(labels, s1, s2, passes, cats) -> pd.DataFrame:
    od = O.add_sensors(O.build(labels), s1, s2, passes=passes)
    od["unique_id"] = od.field_id
    od["season_cat"] = pd.Categorical(od.season, categories=cats)
    return od


def main() -> None:
    labels = pd.read_parquet(LABELS)
    s1, s2 = (pd.read_parquet(SENSORS / f"{k}.parquet") for k in ("s1", "s2"))
    dev, _ = sickle_dev()
    cats = dev.season_cat.cat.categories
    models = {}
    for arm, blocks in ARMS.items():
        cols = F.block_columns(dev, blocks) + (["season_cat"] if "base" in blocks else [])
        models[arm] = (cols, L._fit(dev, cols, L._tune(dev, cols, splits.SEED), splits.SEED))
        print(f"  {arm}: {len(cols)} features, trained on {len(dev)} SICKLE dev rows")

    out, pairs, keep = [], [], None
    for passes, tag in (("DESCENDING", "descending"), (None, "all passes")):
        od = rows(labels, s1, s2, passes, cats)
        assert not od.eval_lock.any(), "a locked row reached the scoring"
        for arm, (cols, m) in models.items():
            missing = [c for c in cols if c not in od]
            assert not missing, f"{arm}: Odisha rows lack {missing}"
            od[f"{arm} pred"] = L.pool_predictions(od, m.predict(od[cols])).pooled
        od["vh_peak_rule pred"] = L.pool_predictions(od, B.vh_peak_rule(dev, od)).pooled
        print(f"\n{tag}: {len(od)} rows, S1 features missing on {od.vh_last.isna().mean():.1%}, "
              f"no clear S2 in lookback on {(od.n_scenes_s2 == 0).mean():.1%}")  # fmt: skip
        subsets = [("all leads", od)] + [(f"district {d}", g) for d, g in od.groupby("district")]
        subsets += [
            (f"lead {h}d ({lo}-{hi})", od[od.lead.between(lo, hi)])
            for h, (lo, hi) in F.LEAD_BUCKETS.items()
        ]
        names = [*ARMS, "vh_peak_rule"]
        for name, g in subsets:
            for arm in names:
                out.append(dict(passes=tag, subset=name, **score(g, arm)))
                if arm == REF:
                    continue
                e = [S.midpoint_error(g[f"{a} pred"], g.lead_lo, g.lead_hi) for a in (arm, REF)]
                d = B.bootstrap_mean(e[0] - e[1], g.block)
                pairs.append(dict(passes=tag, subset=name, comparison=f"{arm} - {REF}",
                                  diff=d[0], lo=d[1], hi=d[2]))  # fmt: skip
        keep = od if keep is None else keep  # descending rows are the headline
        # last-issue implied-date bias: does the arm forecast the right *date*, or the right lead?
        last = od.sort_values("as_of").groupby("field_id").tail(1)
        mid = (last.lead_lo + last.lead_hi) / 2
        for arm in names:
            b = (last[f"{arm} pred"] - mid).median()
            print(f"  {arm:<14} median implied-date bias at the last issue: {b:+.1f} d")

    res, pairs = pd.DataFrame(out), pd.DataFrame(pairs)
    RESULTS.parent.mkdir(exist_ok=True)
    res.round(2).to_csv(RESULTS, index=False)
    pairs.round(2).to_csv(RESULTS.with_name(RESULTS.stem + "_pairs.csv"), index=False)
    keep.to_parquet(RESULTS.with_name(RESULTS.stem + "_rows.parquet"))

    pd.set_option("display.width", 200)
    print("\nmidpoint MAE (d) [block-bootstrap CI]; point forecasts only, intervals come later\n")
    fmt = "{0.mae:5.1f} [{0.mae_lo:.1f}, {0.mae_hi:.1f}]"
    piv = res.assign(v=res.apply(fmt.format, axis=1))
    for tag, g in piv.groupby("passes", sort=False):
        print(f"-- {tag}")
        print(g.pivot(index="arm", columns="subset", values="v").loc[[*ARMS, "vh_peak_rule"]]
              .to_string())  # fmt: skip
    print(f"\npaired midpoint-error differences vs {REF} (negative = better than the clock)\n")
    p = pairs.assign(v=pairs.apply(lambda r: f"{r['diff']:+.1f} [{r.lo:+.1f}, {r.hi:+.1f}]", 1))
    for tag, g in p.groupby("passes", sort=False):
        print(f"-- {tag}")
        print(g.pivot(index="comparison", columns="subset", values="v").to_string())
    print(f"\nwrote {RESULTS} (+ _pairs, _rows)")


if __name__ == "__main__":
    sys.exit(main())
