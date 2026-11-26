# Models

What each component is for, what the proposal committed to, and the alternatives worth keeping in mind. "Current choice" means the starting point, not the answer — if experiments point elsewhere, follow them and record it in `DECISIONS.md`.

All four components are built in this project; the methods they use are published and cited (see proposal Table 5 and References).

---

## M1 — Harvest forecaster

**Question it answers:** given everything observed about a field up to today, how many days until it's harvested, and how sure are we?

| | |
|---|---|
| Objective / RQ | O1 / RQ1 · gap G1 |
| Inputs | Sentinel-1 VV, VH, VH/VV ratio series (per field, with time since last pass); weather (rainfall, temperature, evaporation); Sentinel-2 NDVI/NDWI/MNDWI (cloud-masked; part of the feature set since 22 Nov, D-028 — the optical pre-harvest decline is stronger and earlier than S1's); calendar features (day of year) |
| Target | Days to harvest at issue date, evaluated at 7, 14, 21-day horizons |
| Training data | SICKLE (Tamil Nadu): **319 exact harvest dates from 131 plots, 2019–2020** (D-024; the proposal's "~388 plots" is not in the release — DATA.md §SICKLE), of which 241 samples / 33 neighbour groups are the dev split. **56% of dev rows carry a harvest date shared with other plots** (farmer recall rounding to a village date), which caps what any per-field model can show here — D-031 |
| Current choice | **LightGBM on four calendar features (`days_since_season_start`, `doy_sin`, `doy_cos`, `season`) plus temporal pooling across issue dates — D-030, 23 Nov.** 6.32 d out of fold against 7.41 d for the previous best and 7.85 d for the full 57-feature table; **no satellite feature earns its place on SICKLE** (22 of 53 fail a Boruta shadow test, 14 are significantly worse added alone, and no nested subset search beats the clock — D-030, LOG 23 Nov). The sensor features stay in the extraction pipeline and the published ablation for the M2 transfer test, and because they *do* beat the calendar on the unique-harvest-date stratum. Compact temporal CNN (Pelletier et al., 2019) and LSTM (Mimić et al., 2025) remain the P3 comparisons, to be run with self-supervised pretraining given 241 dev fields |
| Uncertainty | Conformalised quantile regression (Romano et al., 2019) → prediction interval per field |
| Baselines | Average harvest date; phenology rule (stage read from radar curve) |
| Success criterion (proposal) | MAE ≤ 7 days at the 14-day horizon on held-out SICKLE years. **Restated 23 Nov (D-030/D-031, `EVALUATION.md` O1): beat the calendar-only arm on the same folds, reported separately on the shared- and unique-harvest-date strata.** An absolute day count cannot distinguish a forecaster from a calendar — 7.41 d was reached with no satellite data at all |
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

**Frozen protocol (26 Nov 2026, D-035):** the order of operations, the `sep-feb` season mapping for
zero-shot M1, descending-pass S1 and the interval-label scoring are in `EVALUATION.md` §M2 protocol
(v1). Code ready: `features/odisha_m1.py` (rows), `eval/interval_scoring.py`, `ingest/s1.py`,
`scripts/odisha_transplant_spread.py` (step 1).

**Result (26 Nov 2026, D-036, locked 60% scored once):** zero-shot M1 20.6 / 17.6 / 14.2 d at
7/14/21 d. The frozen headline `few s1+s2` (SICKLE + free hand labels, no clock) scores 4.9 / 5.8 / 6.9 d
with 90.3% coverage after Odisha recalibration (81.5% before). Optical pseudo-labels alone give
7.1 / 7.8 / 8.3 d. The radar harvest detector failed (25–37 d), so pseudo-labels are S2-based. The
Odisha-calendar arm scores 13.0 d. Reading: *Odisha-calendar ≫ zero-shot M1 at 7–14 d, and adapted M1
beats both*. TreeSHAP and a deletion test put the gap in `days_since_season_start` (+17 d at 7 d on
Odisha). The drying-period masking hypothesis is not supported. Integrated gradients was not run,
because there is no CNN. Full tables: LOG 26 Nov (evening).

### Design note — the "Odisha-calendar" ablation arm (D-033, added 23 Nov 2026)

**The problem this arm exists to expose.** M1's point model is four calendar features and no
satellite data (D-030). Transferring it zero-shot to Odisha therefore transfers *Tamil Nadu's
planting schedule*, which is the single component we have a positive reason to expect not to
survive (D-031). A plain zero-shot number then conflates two very different failures — "the model
does not transfer" and "the model's clock is set to the wrong region" — and attribution cannot
separate them, because both live in the same four columns.

**The arm.** Replace the SICKLE-learned calendar with a calendar measured *in the target region*
from CSISA — the district's transplanting-date distribution and its per-variety duration
distribution (`features/odisha_calendar.py`). Three arms on the same Odisha rows:

| arm | calendar from | sensors | what a win means |
|---|---|---|---|
| zero-shot M1 | SICKLE (Tamil Nadu) | per-field | the whole model transfers |
| **Odisha-calendar (zero-shot)** | **CSISA Baleswar** | **none — one date for every field** | **nothing per-field transferred; the gap was the clock** |
| adapted M1 | SICKLE + adaptation | per-field | adaptation recovered something |

`odisha_calendar.zero_shot_harvest` makes the middle arm deliberately **field-independent**: one
harvest date and one interval for the entire district, read off a 2018 farmer survey. It is a floor,
and a harsh one — it is the Odisha analogue of the calendar-only arm that beat every sensor arm on
SICKLE. The interesting outcome is the one where it wins.

**How the three readings differ.**
- *Odisha-calendar ≈ adapted M1* → the sensors contribute nothing in Odisha either, and the M2
  story becomes "the transferable part of this task is a calendar", which D-031 says should be
  reported, not hidden.
- *Odisha-calendar ≫ zero-shot M1, and adapted M1 beats both* → the transfer gap was substantially
  a calendar shift, and adaptation is doing real per-field work on top. This is the result the
  TimeMatch-style shift estimation predicts, and the arm is what makes the claim measurable rather
  than assertive.
- *zero-shot M1 beats the Odisha-calendar arm* → Tamil Nadu's calendar generalises better than a
  seven-year-old local survey, which is itself a finding about what "domain" means here.

**What it costs:** almost nothing to run (a table lookup), and it needs no Odisha labels to build,
only to score. The honest caveats are in D-033(c): 2017/2018 data against a 2025–26 label season,
so the arm assumes a stationary planting calendar — the assumption a rainfed district most
threatens. That assumption is itself worth an ablation if the replay ever makes it testable.

**Known risk, flagged before scoring.** The Baleswar prior's 90% harvest interval is ~21 days wide
(12 Dec ± ~10 d for a 2025–26 season), while the hand labels' harvest midpoints span about 13 weeks
(DATA.md §Odisha hand labels). A single district-wide date cannot cover that spread, so the arm will
probably lose on coverage while remaining competitive on MAE — which is the comparison that makes
it informative. **Not scored yet:** D-031 requires the registry transplanting-spread measurement
before any Odisha harvest model is tuned, so this arm is built and left unrun until P3.

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
