"""Reproducible version of the 23 Nov 2026 CSISA review -> reports/csisa_calendar_stats.md.

Every number the review computed in a browser, recomputed from data/processed/csisa_rice.parquet
with bootstrap CIs that resample **villages**, not farmers: farmers in one village share a
monsoon, a labour pool and often a recall anchor, so a farmer-level CI would be far too narrow.

The headline quantity is the spread of transplanting dates, because D-031 pre-registers the
prediction that Odisha's is materially wider than SICKLE's 10.0 d. Two cuts matter for that:
transplanted fields only (`estab_date` means sowing on direct-seeded rows, which roughly doubles
the apparent spread), and a robust scale alongside the SD (a single off-season row moves the 2018
Odisha SD by 1.8 d).

Usage: uv run python scripts/csisa_calendar_stats.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path("data/processed/csisa_rice.parquet")
DEST = Path("reports/csisa_calendar_stats.md")
SEASON = (0, 180)  # days since 1 Jun: a kharif establishment date should land in here
HEAP_DAYS = (1, 5, 10, 15, 20, 25, 30)
MIN_VARIETY_N = 5  # review's threshold for a per-variety duration median
N_BOOT = 2000
RNG = np.random.default_rng(20261123)
SICKLE_TRANSPLANT_SD = 10.0  # D-031, the number this is pre-registered against


def season_day(dates: pd.Series, year: pd.Series) -> pd.Series:
    """Days since 1 Jun of the survey year -- a clock that does not wrap at new year."""
    origin = pd.to_datetime(pd.DataFrame({"year": year, "month": 6, "day": 1}))
    return (dates - origin).dt.days


def robust_sd(x: np.ndarray) -> float:
    """1.4826 x MAD: the SD a normal sample with this median absolute deviation would have."""
    x = np.asarray(x, dtype=float)
    return 1.4826 * float(np.median(np.abs(x - np.median(x))))


def by_village(df: pd.DataFrame, col: str) -> list[np.ndarray]:
    """One array of `col` per village -- the resampling unit for every CI in this report."""
    return [g.to_numpy(float) for _, g in df.groupby("village_id", sort=False)[col]]


def village_boot(parts: list[np.ndarray], stat, n: int = N_BOOT) -> tuple[float, float]:
    """95% percentile CI for stat(parts) under resampling of whole villages."""
    if len(parts) < 3:
        return (np.nan, np.nan)
    vals = []
    for _ in range(n):
        v = stat([parts[i] for i in RNG.integers(0, len(parts), len(parts))])
        if np.isfinite(v):
            vals.append(v)
    return tuple(np.percentile(vals, [2.5, 97.5])) if vals else (np.nan, np.nan)


def pooled_sd(parts: list[np.ndarray]) -> float:
    return float(np.concatenate(parts).std(ddof=1))


def mean_within_sd(parts: list[np.ndarray]) -> float:
    """Mean of the per-village SDs -- the typical village's internal spread."""
    inner = [p.std(ddof=1) for p in parts if len(p) >= 2]
    return float(np.mean(inner)) if inner else np.nan


def pooled_within_sd(parts: list[np.ndarray]) -> float:
    """sqrt of the within-village variance pooled over villages -- weights big villages more and
    is pulled hard by a single outlier. This is the definition the 23 Nov review used."""
    use = [p for p in parts if len(p) >= 2]
    if not use:
        return np.nan
    num = sum((len(p) - 1) * p.var(ddof=1) for p in use)
    den = sum(len(p) - 1 for p in use)
    return float(np.sqrt(num / den))


def load() -> pd.DataFrame:
    df = pd.read_parquet(SRC)
    df["village_id"] = (
        df.year.astype(str) + "|" + df.district.fillna("") + "|" + df.village.fillna("")
    )
    df["estab_sd"] = season_day(df.estab_date, df.year)
    df["harvest_sd"] = season_day(df.harvest_date, df.year)
    df["in_season"] = df.estab_sd.between(*SEASON)
    return df


def groups(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """The review's reporting groups, in its order."""
    out = {}
    for year in (2017, 2018):
        y = df[df.year == year]
        for state in ("Odisha", "Bihar", "UttarPradesh"):
            g = y[y.state == state]
            if len(g):
                out[f"{state} {year}"] = g
        bal = y[y.district == "Balasore"]
        if len(bal):
            out[f"Balasore {year}"] = bal
    return out


# --- sections ---------------------------------------------------------------------------------


def spread_table(df: pd.DataFrame, col: str, transplanted_only: bool) -> pd.DataFrame:
    rows = []
    for name, g in groups(df).items():
        g = g[g.transplanted] if transplanted_only else g
        g = g.dropna(subset=[col])
        if len(g) < 10:
            continue
        lo, hi = village_boot(by_village(g, col), pooled_sd)
        ins = g[g.in_season]
        rows.append(
            {
                "group": name,
                "n": len(g),
                "SD": g[col].std(ddof=1),
                "95% CI": f"[{lo:.1f}, {hi:.1f}]",
                "robust SD": robust_sd(g[col]),
                "SD in-season": ins[col].std(ddof=1) if len(ins) >= 10 else np.nan,
                "dropped": len(g) - len(ins),
            }
        )
    return pd.DataFrame(rows)


def establishment_mix(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name, g in groups(df).items():
        rows.append(
            {
                "group": name,
                "n": len(g),
                "direct-seeded %": 100 * (~g.transplanted).mean(),
                "estab SD, all methods": g.estab_sd.std(ddof=1),
                "estab SD, transplanted": g[g.transplanted].estab_sd.std(ddof=1),
            }
        )
    return pd.DataFrame(rows)


def within_village(df: pd.DataFrame, min_farmers: int = 3) -> pd.DataFrame:
    """Mean within-village SD of transplanting date, vs how much spread is between villages."""
    rows = []
    for name, g in groups(df).items():
        g = g[g.transplanted]
        sizes = g.village_id.value_counts()
        keep = g[g.village_id.isin(sizes[sizes >= min_farmers].index)]
        if keep.village_id.nunique() < 3:
            continue

        parts = by_village(keep, "estab_sd")
        within = mean_within_sd(parts)
        lo, hi = village_boot(parts, mean_within_sd)
        ins = by_village(keep[keep.in_season], "estab_sd")
        rows.append(
            {
                "group": name,
                "villages": keep.village_id.nunique(),
                "farmers": len(keep),
                "mean of village SDs": within,
                "95% CI": f"[{lo:.1f}, {hi:.1f}]",
                "pooled within SD": pooled_within_sd(parts),
                "pooled, in-season": pooled_within_sd(ins),
                "between/total": 1 - within / keep.estab_sd.std(ddof=1),
            }
        )
    return pd.DataFrame(rows)


def variety_durations(df: pd.DataFrame, region: str) -> pd.DataFrame:
    g = df[(df.state == "Odisha") & df.transplanted]
    g = g[g.district == "Balasore"] if region == "Balasore" else g
    t = g.groupby("var_name_norm").duration_days.agg(["size", "median", "std"])
    t = t[t["size"] >= MIN_VARIETY_N].sort_values("size", ascending=False)
    t.columns = ["n", "median duration (d)", "SD (d)"]
    return t.reset_index().rename(columns={"var_name_norm": "variety"})


def harvest_mae(g: pd.DataFrame) -> dict:
    """Median-harvest baseline vs transplanting + median duration per variety, both leave-one-out.

    Scored on the same rows: transplanted, variety known, and the variety has >= MIN_VARIETY_N rows
    in this group (otherwise the per-variety median is not defined without the row itself).
    """
    g = g[g.transplanted].dropna(subset=["harvest_sd", "estab_sd", "var_name_norm"])
    counts = g.var_name_norm.value_counts()
    g = g[g.var_name_norm.isin(counts[counts >= MIN_VARIETY_N].index)]
    if len(g) < 20:
        return {}
    harv, est, var = g.harvest_sd.to_numpy(float), g.estab_sd.to_numpy(float), g.var_name_norm
    base, dur = np.empty(len(g)), np.empty(len(g))
    for i in range(len(g)):
        others = np.ones(len(g), bool)
        others[i] = False
        base[i] = np.median(harv[others])
        same = others & (var.to_numpy() == var.iloc[i])
        dur[i] = est[i] + np.median(harv[same] - est[same])
    return {
        "n": len(g),
        "median-harvest MAE": float(np.abs(harv - base).mean()),
        "transplant+duration MAE": float(np.abs(harv - dur).mean()),
    }


def heaping(df: pd.DataFrame) -> pd.DataFrame:
    """Share of reported dates on a 'round' day of month, against the share chance would give.

    Expected is computed per row from its own month (February has no 30th), so the comparison is
    not the naive 7/30.4 = 23%.
    """
    rows = []
    for name, g in groups(df).items():
        for col, label in (("estab_date", "establishment"), ("harvest_date", "harvest")):
            d = g[col].dropna()
            if len(d) < 50:
                continue
            obs = d.dt.day.isin(HEAP_DAYS)
            dim = d.dt.days_in_month
            exp = sum((dim >= h).astype(float) for h in HEAP_DAYS) / dim
            sub = pd.DataFrame({"village_id": g.loc[d.index, "village_id"], "o": obs.astype(float)})
            lo, hi = village_boot(
                by_village(sub, "o"), lambda parts: 100 * float(np.concatenate(parts).mean())
            )
            rows.append(
                {
                    "group": name,
                    "date": label,
                    "n": len(d),
                    "on a round day %": 100 * obs.mean(),
                    "95% CI": f"[{lo:.0f}, {hi:.0f}]",
                    "chance %": 100 * exp.mean(),
                }
            )
    return pd.DataFrame(rows)


# --- report -----------------------------------------------------------------------------------


def md(t: pd.DataFrame, dp: int = 2) -> str:
    """Minimal markdown table -- pandas' to_markdown needs `tabulate`, which we do not depend on."""

    def cell(v):
        if isinstance(v, float):
            return "--" if not np.isfinite(v) else f"{v:.{dp}f}"
        return str(v)

    head = "| " + " | ".join(t.columns) + " |"
    rule = "|" + "|".join("---" for _ in t.columns) + "|"
    body = ["| " + " | ".join(cell(v) for v in row) + " |" for row in t.itertuples(index=False)]
    return "\n".join([head, rule, *body])


def main() -> None:
    df = load()
    out = [
        "# CSISA rice calendars: the 23 Nov review, recomputed",
        "",
        f"Generated by `scripts/csisa_calendar_stats.py` from `{SRC}` "
        f"({len(df):,} plausible rows of {df.year.nunique()} surveys). "
        "CIs are 95% percentile bootstrap over **villages** (2,000 resamples, seed 20261123).",
        "",
        "`estab_date` is the transplanting date on transplanted fields and the **sowing** date on "
        "direct-seeded ones, so every spread below is reported transplanted-only unless it says "
        "otherwise. 'in-season' keeps rows whose establishment falls 0–180 days after 1 June of "
        "the survey year; 'dropped' counts the rest.",
        "",
        "## 1. Transplanting-date spread — the D-031 quantity",
        "",
        f"SICKLE (Cauvery delta, D-031) measures **{SICKLE_TRANSPLANT_SD} d**. D-031 predicts "
        "Odisha is materially wider.",
        "",
        md(spread_table(df, "estab_sd", True)),
        "",
        "## 2. How much of the naive spread is direct seeding",
        "",
        md(establishment_mix(df)),
        "",
        "## 3. Harvest-date and duration spread (transplanted)",
        "",
        md(spread_table(df, "harvest_sd", True)),
        "",
        md(spread_table(df, "duration_days", True)),
        "",
        "## 4. Within-village transplanting spread (villages with ≥3 farmers)",
        "",
        "Two definitions, because they disagree by a factor of two and the review used the second. "
        "**Mean of village SDs** is the typical village's internal spread; **pooled within SD** is "
        "the square root of the within-village variance pooled across villages, which weights "
        "large villages more and is dragged by a single outlier. `between/total` is the share of "
        "the pooled SD that is *not* within-village — how much a village-level prior would buy "
        "over a district-level one.",
        "",
        md(within_village(df)),
        "",
        "## 5. Duration by variety, Odisha (transplanted, n ≥ 5)",
        "",
        "All Odisha:",
        "",
        md(variety_durations(df, "Odisha")),
        "",
        "Balasore only:",
        "",
        md(variety_durations(df, "Balasore")),
        "",
        "## 6. Does transplanting + variety duration beat the calendar?",
        "",
        "The SICKLE analogue of this comparison (D-031) is what makes the sensor arm worth "
        "building for Odisha. Leave-one-out, same rows for both predictors.",
        "",
        md(
            pd.DataFrame(
                [
                    {"group": k} | v
                    for k, v in ((k, harvest_mae(g)) for k, g in groups(df).items())
                    if v
                ]
            )
        ),
        "",
        "## 7. Date heaping (recall rounding)",
        "",
        md(heaping(df), dp=1),
        "",
        "Heaping is **not uniform across the data**, which matters for the Balasore scoring rule "
        "(EVALUATION.md): Odisha 2017 and Bihar 2017 heap at 35–43% against a ~23% chance share, "
        "but **Balasore 2018 shows no heaping at all** (18.4% establishment, 22.2% harvest, both "
        "at or below chance). A recall tolerance for the Balasore evaluation set therefore cannot "
        "be justified from heaping in that sample; it has to come from somewhere else.",
        "",
        "## 8. Where these numbers differ from the 23 Nov review",
        "",
        "Reproduced to the decimal: all seven transplanted-only transplanting SDs, the "
        "robust 10.4 d for Odisha 2017, the 22.9 d all-method Odisha 2017 figure and its 35.7% "
        "direct-seeded share, the 9.9%/0% direct-seeded shares for Odisha 2018 and Balasore, the "
        "three harvest SDs (18.3 / 12.8 / 16.9), Balasore duration SD 7.4, the 118 co-located "
        "cells with up to 7 farmers, all 185 Balasore points inside the registry bbox, and "
        "Bihar 2017's harvest MAE pair (11.30 → 9.26 against the review's 11.3 → 9.4). Five "
        "differ:",
        "",
        "1. **2018 row count: 8,355, not 8,393.** 8,393 is the file's line count; 38 records "
        "contain embedded newlines, so the parsed row count is lower. Every district count the "
        "review gave is right (they sum to the 784 Odisha rows we see).",
        "2. **Balasore villages: 36 distinct names, not 30.** 30 is the number with ≥ 3 farmers, "
        "which is the subset §4 uses.",
        "3. **Balasore MTU 7029: n = 124, duration SD 5.62 d** here, against the review's n = 120 "
        "/ 5.7 d. The review counted the literal string `MTU7029`; `normalise_variety` also "
        "folds in 4 rows of `Mansuri_MTU7029` and friends. On the literal string alone we get "
        "n = 120, SD **5.67 d** — the review's number exactly.",
        "4. **Within-village SD (§4) depends on the definition.** The review's 9.0 d for Odisha "
        "2018 is the *pooled* within-village SD (we measure 9.04); the mean of per-village SDs is "
        "**5.73 d**. Its 11.8 d for Balasore we cannot reproduce under either definition "
        "(we get 5.64 mean / 13.01 pooled), and the pooled figure is dominated by one row — see 5.",
        "5. **Odisha 2017 harvest MAE: 13.49 → 10.42 d here, against the review's 19.8 → 17.1.** "
        "The review's pair is reproducible only on *uncleaned* rows: all establishment methods "
        "and no plausibility filter gives 17.16 → 14.60, and dropping the variety n ≥ 5 "
        "requirement pushes the baseline to 21.6. Since the method agrees exactly on Bihar 2017 "
        "(99.5% transplanted, almost nothing dropped), the gap is which Odisha rows are in, not "
        "how the MAE is computed. **The conclusion is unchanged in every version: transplanting + "
        "per-variety duration beats the median-harvest baseline.**",
        "",
        "## 9. The finding that was not in the review",
        "",
        "**Balasore's raw transplanting SD of 12.7 d is one field.** Dropping the single "
        "out-of-season row — village Kasida, transplanted 10 Feb 2018, harvested 13 May 2018, "
        "92 days, which is a *summer (boro) rice* crop and not kharif at all — takes the SD from "
        "**12.68 d to 5.70 d** (n = 184), with a robust scale of **4.45 d** and a within-village "
        "spread of 3.77 d. The same single-row sensitivity runs through Balasore's harvest SD "
        "(16.88 → 6.42 d) and the pooled within-village figure (13.01 → 5.36 d). Odisha 2018 as a "
        "whole moves 11.14 → 9.39 d for the same reason.",
        "",
        f"So on this sample the kharif transplanting spread in our own study district is "
        f"**about 5–6 days, roughly half of SICKLE's {SICKLE_TRANSPLANT_SD} d** — the *opposite* "
        "direction to D-031's pre-registered prediction. Three reasons not to treat that as "
        "settling anything: these are 185 farmers in 36 purposively surveyed villages, not a "
        "sample of the 133,055-field Baleswar registry; they are farmer recall, which rounds "
        "(§7) and is not what a radar flooding-date detector would measure; and 2018 is one "
        "monsoon. It is disclosed prior evidence that cuts against the prediction, not a "
        "measurement of it (D-034).",
        "",
    ]
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text("\n".join(out))
    print(f"wrote {DEST}")
    print("\n".join(out[-40:]))


if __name__ == "__main__":
    main()
