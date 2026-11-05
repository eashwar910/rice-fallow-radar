# Models

What each component is for, what the proposal committed to, and the alternatives worth keeping in mind. "Current choice" means the starting point, not the answer — if experiments point elsewhere, follow them and record it in `DECISIONS.md`.

All four components are built in this project; the methods they use are published and cited (see proposal Table 5 and References).

---

## M1 — Harvest forecaster

**Question it answers:** given everything observed about a field up to today, how many days until it's harvested, and how sure are we?

| | |
|---|---|
| Objective / RQ | O1 / RQ1 · gap G1 |
| Inputs | Sentinel-1 VV, VH, VH/VV ratio series (per field, with time since last pass); weather (rainfall, temperature, evaporation); optionally Sentinel-2 indices when cloud-free; calendar features (day of year) |
| Target | Days to harvest at issue date, evaluated at 7, 14, 21-day horizons |
| Training data | SICKLE (Tamil Nadu): ~388 plots with field-recorded harvest dates, 2018–2021 → roughly 350 labelled seasons |
| Current choice | LightGBM on engineered time-series features + compact temporal CNN (Pelletier et al., 2019); LSTM as comparison (as used by Mimić et al., 2025) |
| Uncertainty | Conformalised quantile regression (Romano et al., 2019) → prediction interval per field |
| Baselines | Average harvest date; phenology rule (stage read from radar curve) |
| Success criterion (proposal) | MAE ≤ 7 days at the 14-day horizon on held-out SICKLE years |
| Reference point | Brinkhoff et al. (2025): ~6.5 days RMSE with optical data on irrigated Australian rice |

**Why these models:** ~350 labelled seasons is small. Gradient-boosted trees are strong on small tabular data; a compact CNN can learn shape features of the backscatter curve without many parameters. An LSTM is the natural comparison because the closest prior work used one.

**Feature ideas worth trying:** rolling slopes and curvature of VH; days since VH peak; cumulative growing degree days; rainfall in last N days; VH/VV ratio trend; fraction of valid pixels (quality flag).

**Alternatives worth considering if the above underperforms:**
- Survival / time-to-event framing (harvest as an event with censoring) — natural for "days until", gives hazard-based intervals.
- Multi-horizon single model (horizon as an input) vs. one model per horizon.
- Pretrained time-series encoders or AlphaEarth-style embeddings as features.
- Simple curve-fitting (double logistic on VH) plus extrapolation — a strong interpretable baseline.

**Things to watch:** SICKLE is one irrigated delta, so the model may learn irrigation-specific cues (see M2's hypothesis). Small test sets → bootstrap CIs are wide; report them.

---

## M2 — Cross-region transfer (Tamil Nadu → Odisha)

**Question it answers:** how much does M1 degrade when moved to rainfed Odisha, how much can adaptation recover, and why does the rest stay lost?

| | |
|---|---|
| Objective / RQ | O1 / RQ1 · gaps G2, G3 |
| Source domain | SICKLE (labelled) |
| Target domain | Bolangir + Baleswar fields (unlabelled, except hand-labelled test set) |
| Current choice | Pseudo-labelling (Lee, 2013) from a radar harvest detector validated on Odisha hand labels; temporal-shift estimation (TimeMatch, Nyborg et al., 2022); few-shot fine-tuning on hand-labelled fields |
| Uncertainty under shift | Recalibrate conformal intervals on Odisha labels; compare coverage before/after (Tibshirani et al., 2019 explains why the guarantee breaks under shift) |
| Explainability | SHAP (trees) and integrated gradients (CNN), checked with deletion tests (Samek et al., 2017) |
| Diagnostic ablation | Hypothesis: TN models rely on soil drying after irrigation stops 10–15 days before harvest. Masking that period should shrink the 7-day transfer gap |
| Comparison | Zero-shot M1 (no adaptation) vs. in-region vs. adapted |
| Success criterion (proposal) | Odisha interval coverage within 5 points of nominal; transfer gap reported with 95% CIs |

**Why TimeMatch-style shift estimation:** the main difference between the regions is likely the crop calendar (when things happen), which temporal-shift estimation models directly. Climate-indicator correction (Wang et al., 2025) targets spectral shift and is a reasonable alternative or addition.

**Alternatives worth considering:**
- Importance weighting / weighted conformal prediction using a domain classifier.
- Domain-adversarial training for the CNN.
- Using phenology-anchored time (days since VH peak) instead of calendar time, which may make the shift smaller by construction.
- Source-free adaptation if SICKLE licensing limits joint training (check).

**The research payoff:** "how much is lost, how much is recovered, and here's evidence for why" is the most publishable piece. Keep it clean even if other parts shrink.

---

## M3 — Sowing window

**Question it answers:** for each field and week, is it too wet, workable, or too dry — and when does that change?

| | |
|---|---|
| Objective / RQ | O2 / RQ2a · gap G5 |
| Opens (wet edge) | Field harvested (from M1 / harvest detector) and not waterlogged — waterlogging read from Sentinel-1 backscatter, as in trafficability monitoring (Carranza et al., 2019). Field-level (10 m) |
| Closes (dry edge) | FAO-56 soil-water balance (Allen et al., 1998) falls below the crop's establishment threshold. Initialised from NISAR (200 m) / SMAP (9 km), driven by forecast/observed weather. Landscape-level (200 m – 9 km) |
| Current choice | Rules + physically-based water balance, because no establishment labels exist to learn from |
| Evaluation | Share of fields whose predicted state matches state observed later (waterlogging in Sentinel-2; dryness in NISAR) |
| Baseline | Fixed 1 Nov – 15 Dec window |

**Open pieces:** the crop establishment moisture threshold(s) need a source (agronomy literature for lentil/black gram); how relay sowing (before harvest) vs. zero-till (after) changes the opening edge; the scale mismatch between 10 m fields and 200 m–9 km moisture (terrain position and drainage class may help carry within-pixel variation).

**Alternatives worth considering:** a learned waterlogging classifier trained on Sentinel-2 water labels and applied to Sentinel-1 (cloud-free proxy labels); probabilistic edges (probability of workable) rather than hard states, propagating M1's interval.

---

## M4 — Winter-crop success (PU learning)

**Question it answers:** which fields are most likely to succeed with a winter crop, and why?

| | |
|---|---|
| Objective / RQ | O2 / RQ2b · gap G4 |
| Positives | Rice-mask fields that greened up in past winters (Sentinel-2), excluding irrigated wheat and mustard |
| Unlabelled | All other rice-mask fields — an empty field may be suitable but held back by seed, labour or grazing |
| Current choice | Non-negative PU risk (Kiryo et al., 2017); Elkan & Noto (2008) as simpler comparison |
| Class prior | Estimated, with sensitivity analysis (Bekker & Davis, 2020) |
| Features | Previous-year green-up history, moisture, M1 harvest estimate, terrain/drainage, AlphaEarth embeddings (**previous year only** — year Y includes year Y's winter crop) |
| Explanations | SHAP reason codes, e.g. "ranked low: waterlogged in three of the last four winters" |
| Validation | AgriFieldNet lentil/gram vs. fallow (fallow treated as negative for validation only) → precision@k and AUC, read as lower bounds |
| Baseline | SMAP moisture classes (30% / 35%) |

**The known weakness:** PU assumes labelled positives are a random sample of all positives (SCAR). Here they aren't — sown fields are likely closer to roads, irrigation, seed suppliers. This is a limitation to state and, ideally, probe: e.g., compare positives vs. unlabelled on access proxies, or try a SAR-aware (selected-at-random-not-assumed) PU method from Bekker & Davis's survey.

**Alternatives worth considering:** two-stage reliable-negative methods (PUL-SITS, Desloires et al., 2022); propensity-weighted PU; plain ranking with a one-class model as a sanity check.

---

## Alerts and dashboard

Not a model, but part of O3.

- Alert text from templates grounded in the state's official crop guidelines; Odia and English; generated, not sent.
- Streamlit dashboard: field map coloured by window state; click a field → forecast with interval, M4 rank with reason codes, history.
- Seed-demand table for farmer producer organisations (fields entering window × typical seed rate).
- Tested with unit and data-validation tests.

**Room for improvement:** a usability walkthrough with someone unfamiliar with the project; uncertainty communication in plain language ("likely harvested between 18 and 26 Nov").
