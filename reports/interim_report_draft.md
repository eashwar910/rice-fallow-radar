# Forecasting When Each Field Can Be Sown: Transferable, Explainable Machine Learning on Satellite Time Series for India's Rice Fallows

**Interim Report — COMP3025 Individual Dissertation, 2026/27**

Eashwar Siddha Satish Nath (20717304) · Supervisor: Dr Tissa Chandesa · School of Computer and Mathematical Sciences, University of Nottingham Malaysia

*Draft prepared 27 November 2026 for submission on 3 December 2026. Working reference, not the submitted text. Every number in it can be traced to a file in the project repository (see Appendix C).*

---

## Abstract

About 11.65 million hectares of India's monsoon rice land lies idle through the winter, although much of it could grow a pulse on the soil moisture left behind by the rice. Whether it can depends on a short window for each field. The window opens when the field is harvested and dry enough to work, and it closes when the soil dries out. No existing system forecasts this window field by field before harvest.

This project treats the problem as four machine-learning tasks:

1. forecasting a date from irregular satellite time series, with calibrated uncertainty;
2. transferring that forecaster from a labelled region to an unlabelled one;
3. using explainability to diagnose why the transfer fails;
4. learning from positive and unlabelled examples.

This interim report covers the first two tasks and part of the third, which together make up the project's primary objective.

**Data and tooling.** A per-field data pipeline has been built for two Odisha districts: 292,060 field polygons, with Sentinel-1 radar, Sentinel-2 optical and weather series. A harvest-date test set of 153 Odisha fields was hand-labelled under a written protocol, and the evaluation protocol was frozen as a git tag before any target-region model was scored.

**Results in the source region.** On the Tamil Nadu SICKLE dataset, a LightGBM forecaster with temporal pooling reaches a mean absolute error (MAE) of 6.32 days (95% CI 4.97–7.99), against 12.0 days for a seasonal-mean baseline. Its 90% conformal intervals cover the true harvest 92.3% of the time. A feature-set ablation shows the model's skill comes almost entirely from the crop calendar, and the report traces that to how scheduled harvests are in an irrigated delta.

**Transfer to Odisha.** Applied without adaptation, the model forecasts about three weeks late (20.6 days MAE at a 7-day lead), and its interval coverage falls to 81.5%. SHAP attributions, checked for faithfulness with a deletion test, place the failure on the season clock feature. A model adapted with a few Odisha hand labels reaches 4.9 days at a 7-day lead, with 90.3% coverage after recalibration.

The report also sets out the limitations of these results, the parts still to be built, and a revised plan to April 2027.

---

## 1. Introduction

### 1.1 Problem and motivation

India leaves about 11.65 million hectares of its monsoon (*kharif*) rice land fallow through the dry winter (*rabi*) season, roughly 29% of that land, most of it in the eastern states (Behera et al., 2020; Kumar et al., 2019). Fallowing has measurable human cost: in the Eastern Gangetic Plains it raised the probability of household food insecurity by 15 percentage points (Narayanarao et al., 2026). Odisha alone holds 2.0–2.2 million hectares of such fallow each year (Chandna & Mondal, 2020).

Much of this land could grow a winter pulse such as lentil or black gram on the moisture left in the soil after rice, but that moisture declines quickly around harvest (Subrahmaniyan et al., 2023). Seed is either broadcast into the standing crop just before harvest (relay sowing) or placed into unploughed soil just after it (zero-till sowing). Relay-sown lentil has yielded as well as or better than lentil sown after harvest (Malik et al., 2016).

Each field's opportunity therefore has two edges. It opens when the field is harvested and workable, which waterlogged coastal lowlands often are not. It closes when the soil becomes too dry, which happens fastest on uplands (A. Srivastava et al., 2025).

Current practice cannot see these windows. Odisha used satellite maps to place pulse and oilseed demonstrations on about 450,000 hectares in 2024–25, but it targets seed by administrative block, a unit spanning many villages (A. Srivastava et al., 2025). Research maps fallows after the season has ended (Chandna & Mondal, 2020). Nothing tells an extension officer, before harvest, when a particular field's window will open or close.

The project's position is that producing this forecast per field is a machine-learning problem rather than an agronomic one. It requires:

- a forecaster that predicts a date from irregular, noisy satellite series with calibrated uncertainty;
- a way to move that forecaster from the one region where harvest labels exist (Tamil Nadu) to the region where it is needed (Odisha);
- explanations that can be shown to be faithful, and that can be used to diagnose why a transferred model fails;
- a ranking model that learns from fields known to have been sown, with no reliable negatives.

These four problems are the computer-science core of the project. This report keeps them in front of the agronomy.

### 1.2 Aim, objectives and research questions

The aim, as submitted, is to develop and evaluate a transferable, explainable machine-learning system that forecasts when each field in two Odisha districts can be sown with a winter pulse. Table 1 restates the objectives and research questions. O1 is the primary objective; O2 and O3 are extensions.

**Table 1**
*Objectives, Research Questions and Status at the Interim Point*

| Objective | Research question | Status (27 Nov 2026) |
|---|---|---|
| O1 Forecast and transfer | RQ1: How accurately can harvest be forecast 7, 14 and 21 days ahead, and how much Tamil Nadu → Odisha transfer loss can pseudo-labelling and few-shot fine-tuning recover? | M1 complete on the development split; M2 complete, including the single locked-set evaluation; final SICKLE test scheduled for ~11 Dec |
| O2 Window and ranking | RQ2a: Does the two-edged window match observed field state better than a fixed 1 Nov–15 Dec window? RQ2b: Does PU ranking find fields that later grew a winter crop better than soil-moisture classes? | Not started (planned Dec–Feb) |
| O3 System and evaluation | RQ3: Using only data available at each weekly issue date of 2026–27, how closely do alerts match what was observed? | Replay protocol frozen; data-availability rules implemented and tested; replay itself scheduled Feb–Mar |

### 1.3 Progress at a glance

The proposal committed to having "the pipeline and an M1 baseline" ready by this report. Progress is ahead of that commitment on the primary objective:

- the data pipeline and a 292,060-field registry are built;
- the Odisha hand-labelled test set is complete;
- M1 has baselines, a tuned model and calibrated intervals;
- the evaluation protocol was frozen on 26 November, four days before the date promised;
- M2 (transfer, adaptation and explainability-based diagnosis), which was planned to start in mid-December, has been completed and scored once on its locked test set.

Two parts of the proposal have not been delivered as written. The temporal convolutional network has not been built, and the pseudo-label harvest detector is optical rather than radar. Both are discussed in Sections 5–7.

### 1.4 Structure of this report

- Section 2 updates the literature review with what has been learned since the proposal.
- Section 3 describes the data actually obtained, including where it differs from what was assumed.
- Section 4 describes the system design and the measures taken against leakage.
- Sections 5 and 6 report the methods and results for M1 and M2.
- Section 7 evaluates these results critically.
- Section 8 presents the revised plan.
- Section 9 covers professional and ethical issues.
- Section 10 concludes.

---

## 2. Background and Related Work

### 2.1 Mapping rice fallows

Existing work on rice fallows is retrospective and does not learn from what farmers actually grew. Chandna and Mondal (2020) mapped Odisha's fallows from Sentinel-1 and Landsat-8 at 84–85% accuracy. A. K. Srivastava et al. (2023) mapped Assam's fallows at 92.6% accuracy and identified 0.88 million hectares as suitable by soil moisture. Suitability is still scored with fixed moisture classes (A. Srivastava et al., 2025) or with expert-weighted multi-criteria analysis checked only against district statistics (Singh et al., 2021). None of this work forecasts.

### 2.2 Forecasting crop events from satellite time series

Synthetic-aperture radar suits monsoon rice because it sees through cloud, and its backscatter tracks the flooding and canopy growth of paddy (Singha et al., 2019; Torres et al., 2012). For classifying satellite image time series, temporal convolutional networks outperformed random forests and recurrent networks (Pelletier et al., 2019), but forecasting a future event is less studied.

The closest work is from irrigated Australian rice. Brinkhoff et al. (2025) forecast field grain moisture, and hence the harvest date, from Sentinel-2 and weather with a root-mean-square error of about 6.5 days. Jha et al. (2025) predicted rice phenological stages from remote sensing and weather. Both systems now run operationally (Brinkhoff et al., 2026). Mimić et al. (2025) used Sentinel-1 with an LSTM to detect and predict harvest for Serbian crops.

The SICKLE dataset (Sani et al., 2024) provides field-recorded harvest dates for smallholder rice in Tamil Nadu with multi-sensor imagery. Its benchmark task is estimating the date from a full season of imagery, not forecasting it in advance.

One finding from this project's first phase sharpens this gap. The SICKLE authors' published harvest-date baselines (8.7 days MAE for a Sentinel-1 3-D U-Net) are hindcasts. They see the whole season, including scenes after harvest, and they are validated on a split in which 137 of the 319 exactly dated samples have a neighbouring plot on the other side of the split (Section 3.2). They are therefore an optimistic upper reference, not a target that a forecaster at a 7–21-day lead must beat.

### 2.3 Cross-region transfer and uncertainty under shift

Models transferred across regions degrade, partly because crop calendars shift. TimeMatch estimates that temporal shift and uses it to pseudo-label the target region (Nyborg et al., 2022), building on the pseudo-labelling idea of Lee (2013). Climate-indicator correction raised cross-region crop-classification accuracy by over 11% (Wang et al., 2025). Both methods classify crop type rather than regress a date.

For uncertainty, conformalised quantile regression (CQR) produces prediction intervals with finite-sample coverage guarantees, provided calibration and test data are exchangeable (Romano et al., 2019). Exchangeability is exactly what a change of region breaks. Weighted conformal prediction can restore coverage under covariate shift (Tibshirani et al., 2019), but it needs a density ratio between the domains that is hard to estimate for long time series. This project therefore recalibrates on a small set of target-region labels.

A second consideration, raised by the project's own data, is that conformal guarantees are marginal. Mondrian (group-conditional) conformal prediction calibrates separately within strata, so that coverage holds within each group rather than only on average (Vovk, 2012).

### 2.4 Explainability as a diagnostic

SHAP (Lundberg & Lee, 2017) and integrated gradients (Sundararajan et al., 2017) attribute a prediction to its inputs. For tree ensembles, TreeSHAP computes exact Shapley values in polynomial time (Lundberg et al., 2020). Attributions are only useful if they are faithful to the model. Deletion (region-perturbation) tests check this by removing the top-ranked inputs first and measuring how fast the output degrades, compared with removing inputs at random (Samek et al., 2017).

The proposal noted that no study had used these tools to diagnose transfer failure. That remains true as far as the literature search has gone, and it is the use made of them in Section 6.4.

### 2.5 Positive-unlabelled learning

Positive-unlabelled (PU) learning trains a classifier from confirmed positives and unlabelled data (Elkan & Noto, 2008). The non-negative risk estimator of Kiryo et al. (2017) prevents flexible models from driving the estimated risk below zero and overfitting, and Bekker and Davis (2020) survey methods for estimating the class prior. Desloires et al. (2022) applied PU learning to crop mapping from satellite time series.

In this project, the standard assumption that labelled positives are a random sample of all positives is known to fail. Fields that were sown are not a random subset of sowable fields, because seed access, labour and irrigation decide which fields get sown (Narayanarao et al., 2026). This work is planned for Phase 4 (Section 8).

### 2.6 What has changed since the proposal

Four lessons from the project's own data now shape the literature argument.

1. **Calendar baselines are strong.** The literature compares forecasters with average-date baselines. On SICKLE, a model given only calendar features beats every satellite feature set (Section 5). Any claim that remote sensing improves harvest forecasting has to be made against the calendar, not against nothing.
2. **Optical can beat radar in this setting.** In Odisha, harvest leaves almost no signature in Sentinel-1 at the available 12-day revisit, while Sentinel-2 shows it clearly. This reverses the radar-first framing of the proposal for one component (Section 6.2).
3. **Label noise limits what can be measured.** Interval-valued labels move measured coverage by about 10 percentage points (Section 4.3). The proposal's criterion of coverage "within 5 points of nominal" can only be tested with an explicit correction for this.
4. **The calendar shift is large and visible to attribution.** The source and target harvest calendars differ by about two months. Section 6 shows that the transfer failure sits in a single feature, and that this can be located by attribution and confirmed by intervention.

---

## 3. Data and Study Design

### 3.1 Study area

The two study districts were chosen to cover both edges of the sowing window (A. Srivastava et al., 2025):

- **Bolangir**, in Odisha's western uplands, where lack of irrigation keeps land fallow and the dry edge dominates;
- **Baleswar** (Balasore), on the coastal plain, where waterlogging delays sowing and the wet edge dominates.

The source region is the Cauvery basin in Tamil Nadu, where SICKLE was collected. It is irrigated and centrally scheduled, which turns out to matter a great deal (Section 5.4).

### 3.2 SICKLE: what the release actually contains

The proposal described SICKLE as 388 Tamil Nadu plots with field-recorded harvest dates. The inspection made at the start of this project, reproduced by a profiling script, found a different picture:

- The release has 351 plots in total, of which 262 grew paddy.
- Only 319 plot-seasons, from 131 plots in 2019 and 2020, carry an observed harvest date.
- Another 588 dates are farmer-recalled "typical" dates: the same month and day every year, mostly month-ends. These were excluded from all training and evaluation (decision D-024), because they carry no information about the specific season.
- The official test split contains no labels, and plot coordinates are withheld.
- The official train/validation split leaks spatially: 137 of the 319 exactly dated samples have a plot from the other split inside their 320 m image patch.

Because coordinates are withheld, conventional spatial blocking was impossible. Instead, a neighbour graph was built from plot co-occurrence in the shipped masks. Plots that share any image patch are linked, and the connected components form 43 *neighbour groups*; the largest holds 9% of samples.

- Nine groups (64 samples), balanced by season, are locked as a final test set and have not been read by any training or tuning script.
- The remaining 34 groups (255 samples) form the development split, evaluated by five-fold grouped cross-validation stratified by season (D-022).

Grouped splitting of this kind follows standard advice for spatially structured data (Roberts et al., 2017). Its limitation is that it only captures neighbours within about 320 m.

### 3.3 Field registry

The unit of analysis is the field polygon from Fields of The World (FTW; Kerner et al., 2025). Three findings shaped the registry:

- **The FTW file stacks two years of predictions.** Polygons ≥ 0.1 ha overlapped each other in 41–53% of cases, and every overlap was between the 2024 and 2025 prediction layers, never within one. The two layers had been stacked in one file. Only the 2025 layer is kept (D-026).
- **FTW is fragmented on smallholder land.** The median polygon in the study districts is about 0.04 ha. A minimum size of 0.1 ha was set, which matches SICKLE plot scale and keeps compute within the Earth Engine Community tier (D-016).
- **A land-cover filter would do more harm than good.** The author rated 205 polygons ≥ 0.1 ha without seeing any filter output. Only about 2–3% were not fields, and both WorldCover and Dynamic World filters removed more real fields than false ones. The WorldCover cropland fraction is therefore kept as a quality column rather than used as a filter (D-020).

The final registry holds **292,060 fields** (Bolangir 159,005; Baleswar 133,055) covering 71,292 ha, with median areas of 0.16–0.17 ha. Each field has a stable identifier derived from its geometry and a 5 km block identifier for spatial splitting.

### 3.4 Odisha hand-labelled test set

There are no public harvest-date labels for kharif rice in the study districts, so a test set was made by hand under a protocol written before labelling began (`docs/LABELLING_PROTOCOL.md`):

- **Sample.** 200 fields from the 2025–26 season, drawn with a fixed random seed across district × field-size tercile × 5 km block, plus 20 hidden repeats for self-agreement.
- **Tool.** A purpose-built offline labelling tool shows each field as a date-ordered strip of Sentinel-2 image chips next to its NDVI curve.
- **Label.** Each harvest label is an interval: the last clear image showing a green crop to the first clear image showing a harvested field. Visual interpretation of imagery is a standard way to build reference data in remote sensing (Olofsson et al., 2014).
- **Effort.** Labelling took about six hours.

**Table 2**
*Outcome of Hand Labelling (2025–26 Season)*

| Quantity | Value |
|---|---|
| Fields labelled | 200 (plus 20 repeats) |
| Harvest interval found (`ok`) | 153 |
| Cannot tell / not rice / never green / not a field | 33 / 13 / 1 / 0 |
| Median interval width | 5 days (maximum 10) |
| Harvest midpoints span | 8 Nov 2025 – 9 Feb 2026 |
| Repeat agreement on status | 90% |
| Repeat disagreement in harvest midpoint | median 4 d, mean 8.8 d (6.1 d excluding one 49-day pair) |
| Locked for final evaluation / free for development | 92 / 61 fields |

Three findings from labelling matter for every later result:

- **The labeller is the main source of imprecision, not the imagery.** Self-agreement is worse than the interval widths suggest, so the honest floor on Odisha errors is about 6–9 days, not the 2.3-day half-width of a typical interval.
- **Bolangir is harder to label.** 24 of the 33 "cannot tell" calls were in Bolangir.
- **The rice yes/no tick is unreliable.** It agreed on only 55% of repeats, so kharif rice prevalence can only be stated as a range (40–82%). A three-annotator re-tick is planned (D-029).

The 60/40 split between locked and free fields was assigned from a seeded configuration before any model saw a label.

### 3.5 CSISA survey data

The proposal set aside the Cereal Systems Initiative for South Asia (CSISA) rice surveys, on the belief that the 2018 survey truncated coordinates to about 1 km (Ajay et al., 2022). Re-examination showed that belief was backwards:

- It is the 2017 survey that is coarse (Ajay et al., 2021).
- The 2018 survey carries coordinates to three decimal places (about 110 m), stored in two columns with empty headers, which is presumably why they were missed.
- All 185 Balasore farmers in it fall inside the Baleswar registry.

CSISA now has two provisional roles, neither of which displaces the hand labels (D-033):

1. **An Odisha crop-calendar prior.** It supplies a zero-shot "Odisha-calendar" baseline: one harvest date per district, read off the survey.
2. **An independent secondary test set.** The 118 Balasore 2018 survey cells are scored at cell level with village-level bootstrap.

The survey files carry no licence, so only group-level statistics are reported and every CSISA-based result is marked provisional.

### 3.6 Satellite and weather inputs

**Table 3**
*Inputs Used So Far*

| Source | Use so far | Notes |
|---|---|---|
| Sentinel-1 GRD (Torres et al., 2012) | Per-field VV/VH series, both regions | SICKLE: from shipped patches. Odisha: pulled per field from Earth Engine (Gorelick et al., 2017). Descending passes for the headline |
| Sentinel-2 L2A (Drusch et al., 2012) | NDVI/NDWI/MNDWI series; hand labels; harvest detector | Cloud removes ~52% of SICKLE scenes, but every sample keeps ≥ 10 clear scenes |
| CHIRPS (Funk et al., 2015) | Rainfall | SICKLE: per 110 km tile (D-027), as coordinates are withheld |
| ERA5-Land (Muñoz-Sabater et al., 2021) | Temperature, evaporation | As above |
| FTW (Kerner et al., 2025) | Field polygons | 2025 layer, ≥ 0.1 ha |
| NISAR, SMAP, AlphaEarth | Not yet used | Needed for M3/M4 (Section 8) |

---

## 4. System Design and Implementation

### 4.1 Pipeline

The pipeline follows the architecture in the proposal (Figure 1 there). For any set of fields and any issue date (`as_of`), it produces a feature table using only data that existed on that date.

- **Earth Engine work.** Heavy raster processing runs in Google Earth Engine on the noncommercial Community tier. Per-field tables are pulled directly with chunked, resumable `computeFeatures` calls, which proved more reliable than batch export under the project's service-account permissions (D-017).
- **Local work.** Modelling runs locally with Python 3.12, LightGBM (Ke et al., 2017), scikit-learn and SHAP.
- **Reproducibility.** The environment is pinned with a `uv` lockfile. Linting and a test suite of more than 50 tests run on every push through GitHub Actions. Study areas, label splits and model arm lists live in versioned configuration files.

**[Figure 1 — to produce: pipeline diagram. Inputs (S1, S2, weather, FTW) → per-field series → `build_features(field_ids, as_of)` → M1 → M2 → (M3, M4 planned) → replay. Mark which boxes are built (solid) and planned (dashed).]**

### 4.2 Leakage control, enforced in code

Leakage is the easiest way for a satellite forecasting study to produce results that are quietly too good. Five leakage checks run in CI on synthetic data. Each one "poisons" an input the row must not see and asserts that the row does not change.

1. Features at `as_of` ignore every input dated after it. This is tested for S1, S2 and weather, after every issue date in turn.
2. Training and test sets never share a sample or a neighbour group, and locked sets are unreachable unless requested by name.
3. Annual embeddings for a season come only from the year before (AlphaEarth's year-Y embedding already contains year Y's winter crop).
4. A product value is usable only after its publication lag. For example, Sentinel-2 becomes available 5 days after acquisition and ERA5-Land after 8 days. Any date on or after 1 June 2026 is refused outside replay mode (D-019).
5. Any aggregation across issue dates reads only issue dates at or before the row's own.

Each check was *mutation-tested*: deliberately injecting a three-day weather leak, a six-day radar leak, or an unsorted pooling step turns the suite red.

The fifth check exists because it caught a real bug. The first implementation of temporal pooling (Section 5.3) added predictions in table order to dates in sorted order, so most pooled values belonged to the wrong issue date. The headline error moved by only tenths of a day, so nothing looked wrong; a synthetic test in which pooling had to be a no-op failed immediately.

### 4.3 The evaluation protocol and its freeze

The proposal committed to freezing the evaluation protocol on 30 November 2026, before any 2026–27 imagery could influence a model. It was frozen on 26 November as the git tag `protocol-v1` (D-035). It fixes:

- the primary success criterion;
- the interval-scoring rules;
- the leakage checks;
- the secondary CSISA test set;
- the order of operations for M2;
- the 2026–27 replay: 13 Tuesday issue dates from 3 November 2026 to 26 January 2027, with a lag table that may only ever be raised.

One rule needed measuring before it could be frozen: how to score a point forecast and an interval against an *interval-valued* label. The method was to take SICKLE's exact dates, widen them into synthetic intervals with the same width distribution as the Odisha labels, and rescore the published predictions 200 times (Table 4).

**Table 4**
*Effect of the Scoring Rule on a Known Model (SICKLE, Calendar Model, 90% Interval)*

| Score | Exact labels | Intersection rule (draft) | Midpoint rule | Uniform-expected |
|---|---|---|---|---|
| MAE (days) | 6.32 | 4.74 (−1.58) | 6.58 (+0.26) | 6.73 (+0.41) |
| Coverage | 92.3% | 95.3% (+3.0) | 81.8% (−10.5) | 80.8% (−11.5) |

The drafted rule would have flattered MAE by 1.6 days, enough to decide the objective on its own. The frozen design is:

- error is scored against the label midpoint (bias +0.1 to +0.3 days);
- coverage is scored by intersection minus its measured three-point optimism;
- both are reported with a bracket that contains the exact value.

The wider lesson is that a ±2.5-day label moves the measured coverage of a 90% interval by about ten points. A coverage criterion with a five-point tolerance is therefore only testable after explicit label-noise correction.

Two transfer choices were also registered before any Odisha score was computed:

- **Season mapping.** Odisha kharif is mapped to SICKLE's September–February season, the main monsoon crop.
- **Pass direction.** Odisha radar features use descending passes only, because 96% of SICKLE's radar scenes are descending.

**Disclosure.** CSISA's farmer-reported Odisha transplanting spreads were computed seven days before the freeze. They pointed against one of the project's pre-registered predictions, and the prediction was kept unchanged. This is recorded in D-034 so that it is in the record rather than discovered later.

---

## 5. M1: Harvest Forecaster on SICKLE

### 5.1 Task formulation

Every week, for every field not yet harvested, M1 predicts the number of days until harvest. Rows are built on a weekly grid of issue dates. The target is the true remaining lead, so the proposal's 7/14/21-day horizons are scored as lead-time buckets (4–10, 11–17 and 18–24 days).

Building rows at exactly "harvest minus *h*" would have made the target a constant, which is why the horizons are buckets rather than offsets. M1 assumes the field is still standing; deciding that is the job of the harvest detector.

The development table has 2,745 rows from 305 samples. Fourteen of the 319 samples were lost because their image patches could not be aligned to the plot mask. Every reported confidence interval is a 95% bootstrap over neighbour groups, not rows (Efron & Tibshirani, 1993), because rows from one plot are not independent.

### 5.2 Baselines and a negative result

The two baselines promised in the proposal were built first:

- **Seasonal mean** (average harvest date per season): **12.0 days** MAE [9.9, 14.3].
- **Radar phenology rule** (harvest at a fixed lag after the VH backscatter peak): **17.1 days** [16.1, 18.2]. It *loses* to the calendar.

The reason the radar rule loses is informative. The Cauvery delta is multi-cropped, so searched over a 120-day window the highest VH value is often the *previous* crop's canopy, giving 31.8 days. Restricting the search to 45 days helps, but not enough.

LightGBM was then trained as a seven-arm feature-set ablation: identical rows, identical folds, hyperparameters tuned in an inner loop inside each outer training fold.

**Table 5**
*M1 Feature-Set Ablation (SICKLE Development Split, Out-of-Fold MAE in Days)*

| Arm | Features | MAE [95% CI] |
|---|---|---|
| Calendar + plot size + season ("base") | 5 | **7.41** [5.67, 9.26] |
| base + Sentinel-1 | 31 | 7.58 [6.33, 8.93] |
| base + Sentinel-1 + weather | 43 | 7.65 [6.31, 8.98] |
| base + Sentinel-2 + weather | 32 | 8.23 [6.94, 9.58] |
| All | 58 | 7.85 [6.45, 9.21] |
| Sentinel-1 only (no calendar) | 26 | 10.43 [9.19, 11.85] |
| Sensors only: S1 + S2 + weather (no calendar) | 53 | 7.86 [6.56, 9.18] |
| Seasonal mean (baseline) | — | 11.99 [9.87, 14.29] |

Every arm beats the seasonal mean by about 4.6 days. However, the best arm contains **no satellite data**, and no arm that adds satellite data separates from it.

This is not because the sensors are uninformative. With no calendar at all, sensors alone reach 7.86 days, statistically indistinguishable from the calendar's 7.41. Two independent information sources therefore reach the same accuracy, and combining them adds nothing: the sensors are redundant with the clock.

Without the calendar-only arm, "the 58-feature model gets 7.85 days against a 12.0-day baseline" would have looked like evidence that remote sensing works. The calendar arm is the control that makes this result interpretable.

### 5.3 Improving the point model

Rather than accepting the null, the follow-up work asked why it occurs.

**Feature selection.** Boruta shadow-feature selection (Kursa & Rudnicki, 2010), greedy forward selection and simulated annealing, each nested inside the outer folds, all lost to the five calendar columns. Even "leaky" searches that were allowed to select features using every development row reached only 6.7 days, against 6.3 days for the calendar with pooling. When a search that can see the answers cannot beat five calendar columns, the problem is not the search.

Boruta confirmed 26 features as carrying real signal, yet feeding exactly those 26 made the model worse than feeding five. This is a useful methods point: *relevance is not utility*. Association with the target does not mean a feature improves generalisation once the clock already explains the target.

**Temporal pooling.** What did help was pooling. Each field receives about nine weekly forecasts, and the original model predicted each independently, discarding eight estimates of the same quantity. Converting each forecast into an implied harvest date and taking the running mean over all issue dates up to `as_of` improved every feature set by 0.7–1.0 days.

Equal weighting beat every recency weighting tried. This is further evidence that the signal is the calendar rather than a ripening crop: older estimates are as good as recent ones.

**Plot area.** Dropping plot area as a feature also helped. It made the model worse in every subset tested.

The resulting point model (D-030) uses four calendar features — days since season start, day-of-year sine and cosine, and season — plus pooling. It scores **6.32 days [4.97, 7.99]**, and **6.16 / 6.16 / 6.08 days at the 7/14/21-day horizons**. This meets the proposal's target of 7 days or less at all three horizons.

Two caveats apply:

- About 0.2 days of this is optimistic, because the pooling rule and the area drop were chosen on development data without nesting.
- The model's inputs contain no Earth observation. The satellite still decides *which* fields are asked about and *when* the question expires (field boundaries, rice mask, whether the field is still standing), but it does not answer "how many days are left".

**[Figure 2 — to produce from `runs/sickle_m1_lightgbm.csv`: MAE per horizon for calendar-4, calendar-4+pool, all, all+pool and the seasonal mean, with CIs.]**

### 5.4 Why the satellite cannot help in the Cauvery delta

Two further analyses explain the null and turn it into a testable prediction.

**The labels collapse onto shared dates.** 58.5% of development rows belong to plots whose exact harvest date is shared with at least two other plots. Farmers appear to report a village-level date. These shared-date clusters span an average of 3.4 neighbour groups, so grouped folds do not contain them, and a model can learn "the September–February harvest is 8 February" and carry it to a held-out group.

Split the results on this property and the pooled null separates into two opposite effects:

- on shared-date plots, the calendar scores 4.9 days and every sensor arm is significantly worse;
- on unique-date plots, the sensors help before pooling: base + S1 improves by 1.44 days [0.22, 2.27].

After pooling, compared like for like, the unique-date gain shrinks to 0.90 days [−0.14, 1.76] and is no longer significant. This correction was made during the freeze, and the dissertation will not claim a significant pooled sensor gain on SICKLE. The split conditions on the label, so it is a diagnostic of label quality and never an operational selector.

**Harvest is set by planting decisions the satellite cannot see.** SICKLE's survey table records variety and transplanting date, neither of which was in the feature table. A simple rule, harvest = transplanting date + median duration for that season and variety, scores 6.39 days. Given both inputs, LightGBM reaches 4.60 days.

Neither input can be recovered from orbit in this delta:

- **Transplanting date.** It varies with a standard deviation of only 10.0 days because the delta is irrigated and centrally scheduled. A learned detector on the radar and optical curves (6.03 days) loses to simply predicting the season median (5.94 days).
- **Crop duration.** A coarse three-class duration classifier reaches 79.7% accuracy against a 63.5% majority class, but even a *perfect* classifier would gain only 0.52 days.

The conclusion is recorded in D-031: harvest date in the Cauvery delta is determined by variety and transplanting date, neither observable from orbit, and neither varying much there. This leads to a falsifiable prediction for Odisha, which is rainfed, so the monsoon should spread transplanting dates by weeks. The protocol pre-registered that **Odisha's transplanting-date spread would be materially larger than SICKLE's 10 days**, with a falsification line at 15 days, measured before any Odisha harvest model was tuned.

### 5.5 Calibrated intervals

M1 publishes 90% intervals using CQR (Romano et al., 2019): LightGBM quantile models at 0.05, 0.5 and 0.95, widened by a split-conformal offset learned on an inner, group-disjoint calibration split of each outer fold's training data.

Pooling creates a problem for conformal calibration. A forecast averaging one estimate and a forecast averaging nine have different error distributions, so they are not exchangeable. The offset is therefore calibrated separately for each accumulation stratum (1–2, 3–4 and 5+ estimates), a Mondrian design (Vovk, 2012; D-032).

**Table 6**
*M1 Interval Variants (SICKLE Development Split, 90% Target)*

| Variant | Coverage [95% CI] | Mean width |
|---|---|---|
| Unpooled + single offset | 91.2% [87, 95] | 39.0 d |
| Pooled + single offset | 97.2% [94, 100] | 31.6 d |
| **Pooled + offset per accumulation stratum** | **92.3% [89, 96]** | **24.8 d** |

Stratified calibration brings coverage back towards nominal and makes the interval 21% narrower. Two failures are reported rather than tuned away:

- Coverage at the 7-day horizon is 86.3% [81, 92], and two seasons sit near 84%. With 33 neighbour groups there is not enough calibration data to condition on lead, season and accumulation at once.
- Because pooling averages the interval *bounds*, intervals do not narrow as evidence accumulates. Pooling only the point forecast is the planned fix.

A more important result is that **the width is a property of the task, not the method.** The 90th percentile of absolute error is 15.3 days, and an oracle fixed-width interval would need 30.3 days, so CQR is already 18% narrower than that oracle. A 25-day interval is wider than the sowing window it is meant to inform. M3 should therefore consume the forecast distribution, not just its point.

Coverage is reported as measured, not guaranteed: rows cluster about nine per field, so the effective calibration size is fields, not rows.

---

## 6. M2: Transfer from Tamil Nadu to Odisha

### 6.1 Testing the pre-registered prediction

Following the frozen order of operations, the first M2 step measured the spread of transplanting-flood dates across the Odisha registry:

- **Sample.** 2,000 fields per district.
- **Detection.** Sentinel-1 VH backscatter, descending passes, June–September 2025. A flood is a VH minimum below −20 dB followed by a rise of at least 3 dB within 60 days.

**Result: the pooled robust standard deviation is 20.8 days** (n = 2,739 detected fields), above the 15-day falsification line and twice SICKLE's 10.0 days. Baleswar measures 17.8 days and Bolangir 35.6 days. Every sensitivity setting gives at least 17.8 days, so **the prediction holds**.

Two artefacts are disclosed alongside it:

- **Revisit quantisation.** The 12-day single-track revisit quantises the robust statistic.
- **Bolangir false detections.** Some Bolangir detections fall on the first acquisition, on dry pre-monsoon soil, which inflates Bolangir. Dropping those detections leaves the pooled standard deviation at 19.3 days, so the verdict does not depend on the artefact.

The CSISA survey reports a much smaller spread for Baleswar (5.7 days). The two sources measure different things: farmer-recalled dates on transplanted fields in 36 villages in 2018, against radar-observed floods over the whole registry in 2025. Reconciling them is a discussion point, not a blocker.

### 6.2 Zero-shot transfer and where it fails

Zero-shot arms were developed on the free 40% of Odisha labels (61 fields, 499 forecast rows). All arms were trained on SICKLE and scored by midpoint MAE.

- **Calendar model.** Transferred unchanged, it scores 10.2 days pooled across all leads. That headline is flattering: at the 7-day horizon it scores 21.2 days, worse than a single CSISA district date (14.4 days).
- **Uniform late bias.** M1 forecasts about 21 days late for every field. SICKLE's September–February season harvests in January–February, while Odisha kharif harvests in November–December.
- **Interval collapse.** Coverage falls to 78.6%, and to 13% at the 7-day horizon, because the interval keeps its SICKLE width while its centre moves three weeks late.

The most informative development result came from taking the clock away. Every arm that includes days-since-season-start forecasts about three weeks late, whether or not it also sees radar. Arms without the clock have a bias of only −3 to −4 days.

The radar peak rule, worst on SICKLE (19.4 days at 7 days), is best in Odisha (7.0 days). Where planting is scheduled, the calendar wins; where the monsoon spreads it, the canopy curve does. This is D-031 confirmed from the model side.

Section 6.4 shows why adding radar to the calendar model changes nothing: trained where the clock predicts harvest almost perfectly, the trees learned to ignore the sensors whenever the clock is present.

### 6.3 Adaptation

Three adaptation methods from the proposal were developed on the free 40%, and the arm list was frozen as a git tag (`m2-arms-frozen`) before the locked 60% was read (D-036).

**Pseudo-labelling.** The proposal specified a *radar* harvest detector to generate pseudo-labels. On the free hand labels, every VH-drop variant missed by 25–37 days, because Odisha VH barely changes at harvest at the available revisit. An optical rule on Sentinel-2 NDVI, selected by a rule written before scoring, reached 8.0 days and dated 98% of fields. It produced pseudo-labels for 579 unlabelled flooded fields outside every labelled block.

This is a documented deviation from the proposal, and it introduces a circularity: hand labels and pseudo-labels are both Sentinel-2 green-to-brown reads (Section 7.2).

**Temporal-shift estimation.** In the spirit of TimeMatch (Nyborg et al., 2022), the calendar shift was estimated per district by aligning median flood dates with SICKLE's transplanting dates: −71 days for Baleswar and −85 days for Bolangir. An independent alignment of harvest dates gave −79 and −78 days, so the offset is well identified.

**Few-shot fine-tuning.** SICKLE rows plus the free Odisha hand labels (weighted ×3, a fixed choice), with Odisha rows given their own season category.

**Recalibration.** All adapted arms are recalibrated with Mondrian split conformal on Odisha labels.

**Table 7**
*M2 Results on the Locked 60% (92 Fields, 81 Blocks, 757 Rows), Scored Once. Midpoint MAE in Days; Coverage After Odisha Recalibration, 90% Target*

| Arm | Trained on | 7 d | 14 d | 21 d | All leads | Coverage (width) |
|---|---|---|---|---|---|---|
| Zero-shot M1 (calendar) | SICKLE | 20.6 | 17.6 | 14.2 | 10.0 | 81.5% before → 96.3% after (23.8 d) |
| Zero-shot S1+S2 (no clock) | SICKLE | 7.7 | 9.4 | 11.5 | 16.3 | 96.2% (28.4 d) |
| Shifted clock, base+S1+S2 | SICKLE, shifted | 9.3 | 10.3 | 11.4 | 13.1 | 92.0% (29.6 d) |
| Pseudo-labels, base+S1+S2 | SICKLE + 579 pseudo | 7.1 | 7.8 | 8.3 | 9.2 | 86.6% (27.0 d) |
| **Few-shot S1+S2 (pre-registered headline)** | SICKLE + free hand labels | **4.9** | **5.8** | **6.9** | 9.3 | **90.3% [87, 93]** (31.6 d) |
| Few-shot base+S1+S2 | SICKLE + free hand labels | 5.5 | 6.0 | 6.3 | **6.6** | 91.5% (23.6 d) |
| In-region only, base+S1+S2 | Free hand labels only | 5.4 | 5.9 | 6.3 | 6.8 | 91.3% (25.4 d) |
| Odisha-calendar (CSISA) | One date per district | 13.0 | 13.0 | 13.0 | 12.9 | 71.2% (30.5 d) |

At the 7-day horizon, the pre-registered headline arm improves on zero-shot M1 by **15.7 days [14.2, 17.0]** (paired block bootstrap) and on the Odisha-calendar arm by 8.1 days [5.9, 10.3]. Against SICKLE's own error under the same scoring, the transfer gap is fully recovered at every horizon. Development-set numbers replicated on the locked set to within about a day throughout.

Four findings follow from the table.

1. **O1's coverage criterion is met only after recalibration.** The SICKLE-calibrated interval covers 81.5% in Odisha (23% at the 7-day horizon). After recalibration, the adapted arms sit at 90.3–91.5%, within five points of nominal. This is the outcome the proposal anticipated when it cited Tibshirani et al. (2019): conformal coverage does not survive a regional shift on its own. Recalibration over-corrects the zero-shot model to 96.3% because it widens an interval whose centre is still wrong.
2. **Hand labels do the work.** Few-shot and in-region-only arms are within 0.2 days of each other, so once 61 Odisha fields are available, the SICKLE rows add almost nothing. Without any hand labels, pseudo-labels recover most of the 7-day gap (20.6 → 7.1 days). Added *on top of* hand labels, they make things worse.
3. **A single calendar shift helps at short leads and hurts at long ones.** One offset per district cannot fix a district whose planting is spread by the monsoon. That spread is the 20.8-day measurement from Section 6.1.
4. **Bolangir stays harder.** All-lead MAE for the headline arm is 11.4 days in Bolangir against 7.5 in Baleswar. The arm that also learns an Odisha clock (few-shot base+S1+S2) evens this out at 6.6 days in each.

On the CSISA Balasore 2018 secondary set (118 cells, 35 villages, recall tolerance ±7 days), the few-shot base+S1+S2 arm scores 4.6 / 5.5 / 6.5 days at 7/14/21 days, against 20.6 / 18.2 / 15.3 for zero-shot M1. Coverage on this set is saturated by the wide labels, so it tests error, not calibration.

**[Figure 3 — to produce from `runs/odisha_m2_final.csv`: per-horizon MAE for zero-shot M1, zero-shot S1+S2, pseudo, few-shot and Odisha-calendar, with SICKLE's own per-horizon error as a reference line.]**

**[Figure 4 — coverage before and after Odisha recalibration, by arm.]**

### 6.4 Explainability: locating the failure

The proposal promised attributions that are tested for faithfulness and then used to explain *why* transfer fails. The analysis used TreeSHAP (Lundberg et al., 2020) on the zero-shot base+S1+S2 model, computed on SICKLE rows and on the free Odisha rows.

**Attribution.** The calendar block's share of total |SHAP| rises from 58% on SICKLE to 73% on Odisha. Days-since-season-start is the single most important feature on 491 of 499 Odisha rows. Its *signed* contribution at the 7-day horizon is −12.1 days on SICKLE and **+17.0 days on Odisha**. That is the three-week bias of Section 6.2, located in one feature.

**Faithfulness.** A deletion test (Samek et al., 2017) removes features in SHAP order and in random order and compares how fast the error grows (area over the perturbation curve):

- Odisha: SHAP order 19.7 against random 4.5;
- SICKLE: SHAP order 15.1 against random 3.3.

The attributions are therefore faithful to the model.

**Intervention.** Deleting each Odisha row's single top-ranked feature cuts the 7-day error from 19.6 to 8.9 days, an improvement of 10.7 days [9.1, 12.2]. It raises the 21-day error by 5.7 days, which shows the clock still carries useful information at long leads.

**Testing the proposal's hypothesis.** The proposal hypothesised that Tamil Nadu models rely on soil drying after irrigation stops 10–15 days before harvest, so masking that period should shrink the 7-day transfer gap. The masking ablation was redesigned before use: masking the 15 days before the *true* harvest leaks the date through the edge of the gap, and that first version was discarded before any result was used. The redesign applies a 15-day reporting latency to every scene instead.

Under the redesign, SICKLE's 7-day error barely moves (6.14 → 6.32 days), and the transfer gap shrinks by a similar ~1.7 days at *every* horizon, not specifically at 7 days. **The hypothesis is not supported.** Tamil Nadu models do not lean on the final fortnight, and the 7-day gap is caused by the clock.

**[Figure 5 — signed SHAP contribution of the clock feature by horizon, SICKLE vs Odisha; plus the deletion curves. From `runs/odisha_m2_xai_shap.csv` and `runs/odisha_m2_xai_deletion.csv`.]**

---

## 7. Critical Evaluation

### 7.1 Against the success criteria

**Table 8**
*Progress Against O1's Success Criteria*

| Criterion (proposal) | Status | Comment |
|---|---|---|
| MAE ≤ 7 d at 14-day horizon on held-out SICKLE | Met on development split (6.16 d); held-out test ~11 Dec | Reached without satellite inputs, so the operative test is beating the calendar arm like for like (frozen in `protocol-v1`) |
| Odisha interval coverage within 5 points of nominal | Met after recalibration (90.3% headline); not met zero-shot (81.5%) | Judged with the measured 3-point label-noise correction |
| Transfer gap reported with 95% CIs | Met | Paired block bootstrap on the locked set |

The first criterion deserves a candid comment. A target of 7 days that a calendar can meet does not, on its own, show that a remote-sensing forecaster works. The protocol therefore adds a like-for-like comparison against the calendar-only arm. This is a narrowing of the criterion, recorded in the decision log, not a replacement for it.

### 7.2 Threats to validity

1. **Possible circularity in the Odisha labels.** Odisha labels, pseudo-labels and the best features all come from Sentinel-2. The headline 7-day error (4.9 days) is *below* the labeller's own self-disagreement (6–9 days). This is consistent with a model that has partly learned how the labeller reads a green-to-brown transition rather than when harvest happened. The independent CSISA farmer-reported set (4.6 days at 7 days for the comparable arm) partly mitigates this, but it is from a different year and its licence is unconfirmed. Planned next: a sensor ablation scoring a radar-only few-shot arm, plus the three-annotator re-tick of D-029.
2. **Small samples.** The study uses 33 SICKLE neighbour groups and 61 + 92 Odisha fields. Bootstrap CIs are wide, and "not separated" means not separated at this sample size, not proven equal.
3. **One season in Odisha.** All Odisha labels are from 2025–26, so the adapted model has not been tested on an unseen year. The 2026–27 replay will have only detector-based "truth" unless roughly 50 replay-season fields are labelled in January (D-018, Option C).
4. **Weather resolution.** SICKLE weather is per 110 km tile because coordinates are withheld, so part of any transfer gap could be a difference in feature quality rather than climate (D-023, D-027).
5. **Selection optimism.** About 0.2 days of M1's 6.32 came from un-nested choices. M2's headline arm was chosen by a pre-written rule, but the alternative arm (few-shot base+S1+S2) is better on all-lead error and in Bolangir. Both are reported.

### 7.3 Deviations from the proposal

- **The temporal CNN has not been built**, so integrated gradients, which need a differentiable model, have not been applied. This is the most visible gap against the proposal and is scheduled first in Section 8.
- **The pseudo-label detector is optical, not radar**, for the measured reason given in Section 6.3.
- **CSISA has returned** as a calendar prior and a secondary test set after D-005 had excluded it.
- **SICKLE is smaller than stated in the proposal** (131 plots / 319 seasons with exact dates, not 388 plots).

Each deviation is recorded in the decision log with its date and reasoning.

### 7.4 Is this a computer-science contribution?

The supervisor's main criticism of early drafts was that the project read like agronomy. The results so far are framed as machine-learning findings:

- **Forecasting.** A feature-set ablation with a calendar control showed that a sensor model and a calendar model are redundant, and explained why. A temporal-pooling step improved every feature set. Mondrian CQR addressed non-exchangeability created by the model's own aggregation.
- **Transfer.** A pre-registered, falsifiable prediction was tested before tuning. Adapted forecasters recovered the full transfer gap, and coverage was measured before and after recalibration.
- **Explainability.** Attributions were shown to be faithful and then used diagnostically: they located the failure in a single feature, an intervention confirmed it, and a named hypothesis from the proposal was rejected.

---

## 8. Revised Plan

Progress on O1 is ahead of the proposal timeline, so the plan shifts effort towards completing O1's missing component (the CNN) and starting O2 earlier than planned.

**Table 9**
*Revised Plan, December 2026 – April 2027*

| Period | Work | Output |
|---|---|---|
| 28 Nov – 3 Dec | Interim report | This report |
| 4 – 10 Dec | Temporal CNN for M1 (Pelletier et al., 2019), LSTM comparison if time allows; freeze M1 arm list | Second model family; integrated gradients possible |
| ~11 Dec | Single unlock of the locked SICKLE test set | M1 held-out results per horizon |
| Dec | Integrated gradients + deletion test on the CNN; radar-only few-shot ablation (circularity check); three-annotator rice re-tick (D-029) | Complete XAI comparison; circularity bounded |
| Dec – Jan | 2026–27 ingestion for the replay (ingest only, no tuning); `replay-models` tag | Replay inputs ready |
| Jan 2027 | Decide whether to hand-label ~50 2026–27 fields (D-018, Option C) | Better replay reference, if done |
| Jan – Feb | M3 sowing window: S1 waterlogging (Carranza et al., 2019) + FAO-56 water balance (Allen et al., 1998), initialised from NISAR/SMAP (Entekhabi et al., 2010) | RQ2a vs fixed 1 Nov–15 Dec window |
| Jan – Feb | M4 PU ranking: nnPU (Kiryo et al., 2017) vs Elkan–Noto, class-prior sensitivity, SHAP reason codes | RQ2b vs SMAP classes |
| Feb – early Mar | Integration, alerts (generated, not sent), Streamlit dashboard, replay over 13 issue dates | RQ3 |
| 5 Mar | Model freeze | |
| Mar – 7 Apr | Dissertation writing | |
| 8 – 14 Apr | Buffer | |
| 15 Apr / 29 Apr | Final dissertation / presentation | |

**[Figure 6 — revised Gantt chart in the same style as the proposal's Figure 2, with M2 moved earlier and the CNN inserted before 11 Dec.]**

**Table 10**
*Main Risks and Responses*

| Risk | Response |
|---|---|
| CNN underfits on ~255 development samples | Report as a finding; try the 588 recalled dates as down-weighted weak labels (D-024's planned ablation) |
| Label circularity explains part of M2's headline | Radar-only few-shot arm, CSISA cross-check, three-annotator re-tick; state the bound |
| NISAR provisional soil moisture unreliable | Fall back to SMAP; report the dry edge at landscape scale |
| No licence reply (SICKLE, CSISA) | Plans assume no reply; CSISA results stay provisional and can be removed without touching the primary test |
| Replay has no 2026–27 hand labels | Detector-based reference, validated on past labels; optional January labelling |

---

## 9. Professional, Legal and Ethical Considerations

**Ethics approval and human participants.** An ethics application was submitted by the 12 November deadline. The project involves no human participants: no farmer or officer is contacted, and alerts are generated but never sent.

**Data and privacy.** All satellite data is public. SICKLE plot locations are withheld by its authors for privacy, and this project deliberately did not try to recover them from image metadata (D-023). The CSISA surveys carry no stated licence, so raw rows are not redistributed, only group-level statistics are reported, and results built on them are marked provisional.

**Security.** Credentials (the Earth Engine service-account key and the NASA Earthdata login) are kept outside the repository.

**Accuracy of claims.** Because outputs could influence where seed is distributed, the project reports uncertainty with every forecast and states what its tests cannot establish. Examples are the label-noise floor, the circularity risk and the single season.

**Cost.** The budget is RM0–100. All compute runs on Earth Engine's noncommercial tier and a personal laptop.

---

## 10. Conclusion

The primary objective is substantially complete ahead of schedule. The project has:

- a leakage-tested per-field pipeline for two Odisha districts;
- a hand-labelled target-region test set;
- an evaluation protocol frozen before the numbers it governs existed;
- a harvest forecaster that meets its accuracy target on Tamil Nadu development data.

The more interesting results are the explanations behind the numbers:

- **Tamil Nadu.** Harvest dates are set by schedule and variety, which the calendar captures and the satellite cannot add to.
- **Odisha.** The monsoon spreads planting by about three weeks, so a transferred model that trusts the calendar fails, and attributions shown to be faithful locate the failure in that feature.
- **Adaptation.** A small number of target-region labels recovers the whole gap, and recalibration restores interval coverage.

The next four months complete O1 with a neural forecaster and its attributions, run the held-out SICKLE test, and build the sowing-window and PU-ranking components that turn a harvest forecast into the field-level sowing advice the project set out to produce.

---

## References

Ajay, A., Craufurd, P., Kumar, V., Samaddar, A., Malik, R. K., Sharma, S., Ranjan, H., Singh, A. K., Paudel, G., Pundir, A. K., Poonia, S., Kumar, A., Kumar, P., Singh, D. K., Singh, M., Iftikar, W., Ignatius, M., Banik, N., Mohapatra, B., . . . McDonald, A. (2022). Large survey dataset of rice production practices applied by farmers on their largest farm plot during 2018 in India. *Data in Brief, 45*, Article 108625. https://doi.org/10.1016/j.dib.2022.108625

Ajay, A., Craufurd, P., Sharma, S., Ranjan, H., Samaddar, A., Poudel, G., Malik, R. K., Singh, B., Panneerselvam, P., Singh, A. K., Rai, A., Keil, A., & McDonald, A. (2021). *Data on farmers' rice production practices during 2017 monsoon season from eastern states of India* [Data set]. CIMMYT Research Data & Software Repository Network. https://hdl.handle.net/11529/10548605

Allen, R. G., Pereira, L. S., Raes, D., & Smith, M. (1998). *Crop evapotranspiration: Guidelines for computing crop water requirements* (FAO Irrigation and Drainage Paper No. 56). Food and Agriculture Organization of the United Nations.

Behera, B., Nanda, S. S., Gulati, J. M. L., Sahoo, B. K., Behura, A. K., Mohapatra, A. K., & Behera, S. D. (2020). Overview of agronomic research for greening rice (*Oryza sativa*)-fallows during winter in India. *Indian Journal of Agronomy, 65*(3), 243–263. https://doi.org/10.59797/ija.v65i3.2971

Bekker, J., & Davis, J. (2020). Learning from positive and unlabeled data: A survey. *Machine Learning, 109*(4), 719–760. https://doi.org/10.1007/s10994-020-05877-5

Brinkhoff, J., Dunn, B. W., Dunn, T., Schultz, A., & Hart, J. (2025). Forecasting field rice grain moisture content using Sentinel-2 and weather data. *Precision Agriculture, 26*(1), Article 28. https://doi.org/10.1007/s11119-025-10228-2

Brinkhoff, J., McGavin, S., Jha, S., & Groat, M. (2026). *Project snapshot: Real-time remote sensing-based monitoring for the rice industry* [Fact sheet]. AgriFutures Australia. https://agrifutures.com.au/product/project-snapshot-real-time-remote-sensing-based-monitoring-for-the-rice-industry/

Carranza, C., Benninga, H., van der Velde, R., & van der Ploeg, M. (2019). Monitoring agricultural field trafficability using Sentinel-1. *Agricultural Water Management, 224*, Article 105698. https://doi.org/10.1016/j.agwat.2019.105698

Chandna, P. K., & Mondal, S. (2020). Analyzing multi-year rice-fallow dynamics in Odisha using multi-temporal Landsat-8 OLI and Sentinel-1 data. *GIScience & Remote Sensing, 57*(4), 431–449. https://doi.org/10.1080/15481603.2020.1731074

Desloires, J., Ienco, D., Botrel, A., & Ranc, N. (2022). Positive unlabelled learning for satellite images' time series analysis: An application to cereal and forest mapping. *Remote Sensing, 14*(1), Article 140. https://doi.org/10.3390/rs14010140

Drusch, M., Del Bello, U., Carlier, S., Colin, O., Fernandez, V., Gascon, F., Hoersch, B., Isola, C., Laberinti, P., Martimort, P., Meygret, A., Spoto, F., Sy, O., Marchese, F., & Bargellini, P. (2012). Sentinel-2: ESA's optical high-resolution mission for GMES operational services. *Remote Sensing of Environment, 120*, 25–36. https://doi.org/10.1016/j.rse.2011.11.026

Efron, B., & Tibshirani, R. J. (1993). *An introduction to the bootstrap*. Chapman & Hall.

Elkan, C., & Noto, K. (2008). Learning classifiers from only positive and unlabeled data. In *Proceedings of the 14th ACM SIGKDD International Conference on Knowledge Discovery and Data Mining* (pp. 213–220). Association for Computing Machinery. https://doi.org/10.1145/1401890.1401920

Entekhabi, D., Njoku, E. G., O'Neill, P. E., Kellogg, K. H., Crow, W. T., Edelstein, W. N., Entin, J. K., Goodman, S. D., Jackson, T. J., Johnson, J., Kimball, J., Piepmeier, J. R., Koster, R. D., Martin, N., McDonald, K. C., Moghaddam, M., Moran, S., Reichle, R., Shi, J. C., . . . Van Zyl, J. (2010). The Soil Moisture Active Passive (SMAP) mission. *Proceedings of the IEEE, 98*(5), 704–716. https://doi.org/10.1109/JPROC.2010.2043918

Funk, C., Peterson, P., Landsfeld, M., Pedreros, D., Verdin, J., Shukla, S., Husak, G., Rowland, J., Harrison, L., Hoell, A., & Michaelsen, J. (2015). The climate hazards infrared precipitation with stations—A new environmental record for monitoring extremes. *Scientific Data, 2*, Article 150066. https://doi.org/10.1038/sdata.2015.66

Gorelick, N., Hancher, M., Dixon, M., Ilyushchenko, S., Thau, D., & Moore, R. (2017). Google Earth Engine: Planetary-scale geospatial analysis for everyone. *Remote Sensing of Environment, 202*, 18–27. https://doi.org/10.1016/j.rse.2017.06.031

Jha, S. K., Brinkhoff, J., Robson, A. J., & Dunn, B. W. (2025). Integrating remote sensing and weather time series for Australian irrigated rice phenology prediction. *Remote Sensing, 17*(17), Article 3050. https://doi.org/10.3390/rs17173050

Ke, G., Meng, Q., Finley, T., Wang, T., Chen, W., Ma, W., Ye, Q., & Liu, T.-Y. (2017). LightGBM: A highly efficient gradient boosting decision tree. In *Advances in Neural Information Processing Systems* (Vol. 30, pp. 3146–3154). Curran Associates.

Kerner, H., Chaudhari, S., Ghosh, A., Robinson, C., Ahmad, A., Choi, E., Jacobs, N., Holmes, C., Mohr, M., Dodhia, R., Lavista Ferres, J. M., & Marcus, J. (2025). Fields of The World: A machine learning benchmark dataset for global agricultural field boundary segmentation. *Proceedings of the AAAI Conference on Artificial Intelligence, 39*(27), 28151–28159. https://doi.org/10.1609/aaai.v39i27.35034

Kiryo, R., Niu, G., du Plessis, M. C., & Sugiyama, M. (2017). Positive-unlabeled learning with non-negative risk estimator. In *Advances in Neural Information Processing Systems* (Vol. 30, pp. 1675–1685). Curran Associates.

Kumar, R., Mishra, J. S., Upadhyay, P. K., & Hans, H. (2019). Rice fallows in the eastern India: Problems and prospects. *Indian Journal of Agricultural Sciences, 89*(4), 567–577. https://doi.org/10.56093/ijas.v89i4.88838

Kursa, M. B., & Rudnicki, W. R. (2010). Feature selection with the Boruta package. *Journal of Statistical Software, 36*(11), 1–13. https://doi.org/10.18637/jss.v036.i11

Lee, D.-H. (2013, June). *Pseudo-label: The simple and efficient semi-supervised learning method for deep neural networks* [Paper presentation]. ICML 2013 Workshop on Challenges in Representation Learning, Atlanta, GA, United States.

Lundberg, S. M., Erion, G., Chen, H., DeGrave, A., Prutkin, J. M., Nair, B., Katz, R., Himmelfarb, J., Bansal, N., & Lee, S.-I. (2020). From local explanations to global understanding with explainable AI for trees. *Nature Machine Intelligence, 2*(1), 56–67. https://doi.org/10.1038/s42256-019-0138-9

Lundberg, S. M., & Lee, S.-I. (2017). A unified approach to interpreting model predictions. In *Advances in Neural Information Processing Systems* (Vol. 30, pp. 4765–4774). Curran Associates.

Malik, A. I., Ali, M. O., Zaman, M. S., Flower, K., Rahman, M. M., & Erskine, W. (2016). Relay sowing of lentil (*Lens culinaris* subsp. *culinaris*) to intensify rice-based cropping. *The Journal of Agricultural Science, 154*(5), 850–857. https://doi.org/10.1017/S0021859614001324

Mimić, G., Mishra, A. K., Marković, M., Živaljević, B., Pavlović, D., & Marko, O. (2025). Machine learning-based harvest date detection and prediction using SAR data for the Vojvodina region (Serbia). *Sensors, 25*(7), Article 2239. https://doi.org/10.3390/s25072239

Muñoz-Sabater, J., Dutra, E., Agustí-Panareda, A., Albergel, C., Arduini, G., Balsamo, G., Boussetta, S., Choulga, M., Harrigan, S., Hersbach, H., Martens, B., Miralles, D. G., Piles, M., Rodríguez-Fernández, N. J., Zsoter, E., Buontempo, C., & Thépaut, J.-N. (2021). ERA5-Land: A state-of-the-art global reanalysis dataset for land applications. *Earth System Science Data, 13*(9), 4349–4383. https://doi.org/10.5194/essd-13-4349-2021

Narayanarao, B., Nandi, R., Jackson, T. M., Mitra, B., Ghosh, A., Karmacharya, S., Rana, G., Nisho, A. I., & Chaudhary, A. (2026). The hidden cost of land fallowing: Food insecurity in the Eastern Gangetic Plains. *Sustainable Futures, 11*, Article 101683. https://doi.org/10.1016/j.sftr.2026.101683

Nyborg, J., Pelletier, C., Lefèvre, S., & Assent, I. (2022). TimeMatch: Unsupervised cross-region adaptation by temporal shift estimation. *ISPRS Journal of Photogrammetry and Remote Sensing, 188*, 301–313. https://doi.org/10.1016/j.isprsjprs.2022.04.018

Olofsson, P., Foody, G. M., Herold, M., Stehman, S. V., Woodcock, C. E., & Wulder, M. A. (2014). Good practices for estimating area and assessing accuracy of land change. *Remote Sensing of Environment, 148*, 42–57. https://doi.org/10.1016/j.rse.2014.02.015

Pelletier, C., Webb, G. I., & Petitjean, F. (2019). Temporal convolutional neural network for the classification of satellite image time series. *Remote Sensing, 11*(5), Article 523. https://doi.org/10.3390/rs11050523

Roberts, D. R., Bahn, V., Ciuti, S., Boyce, M. S., Elith, J., Guillera-Arroita, G., Hauenstein, S., Lahoz-Monfort, J. J., Schröder, B., Thuiller, W., Warton, D. I., Wintle, B. A., Hartig, F., & Dormann, C. F. (2017). Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure. *Ecography, 40*(8), 913–929. https://doi.org/10.1111/ecog.02881

Romano, Y., Patterson, E., & Candès, E. (2019). Conformalized quantile regression. In *Advances in Neural Information Processing Systems* (Vol. 32, pp. 3543–3553). Curran Associates.

Samek, W., Binder, A., Montavon, G., Lapuschkin, S., & Müller, K.-R. (2017). Evaluating the visualization of what a deep neural network has learned. *IEEE Transactions on Neural Networks and Learning Systems, 28*(11), 2660–2673. https://doi.org/10.1109/TNNLS.2016.2599820

Sani, D., Mahato, S., Saini, S., Agarwal, H. K., Devshali, C. C., Anand, S., Arora, G., & Jayaraman, T. (2024). SICKLE: A multi-sensor satellite imagery dataset annotated with multiple key cropping parameters. In *Proceedings of the IEEE/CVF Winter Conference on Applications of Computer Vision* (pp. 5995–6004). IEEE.

Singh, R. K., Biradar, C., Sarker, A., Dogra, A., & Rizvi, J. (2021). Mapping areas for growing pulses in rice fallows using multi-criteria spatial decisions. In P. K. Shit, P. Das, G. S. Bhunia, & D. Dutta (Eds.), *Mapping, monitoring, and modeling land and water resources: Advanced techniques using open source software* (pp. 21–32). CRC Press. https://doi.org/10.1201/9781003181293-3

Singha, M., Dong, J., Zhang, G., & Xiao, X. (2019). High resolution paddy rice maps in cloud-prone Bangladesh and Northeast India using Sentinel-1 data. *Scientific Data, 6*, Article 26. https://doi.org/10.1038/s41597-019-0036-3

Srivastava, A., Yeggina, P., Challa, K., Variar, M., Patnaik, B., Rath, J., & Darshith, S. (2025, December 11). From pixels to production: How geospatial intelligence is driving sustainable intensification of rice fallows in Odisha. *Rice Today*. https://ricetoday.irri.org/from-pixels-to-production-how-geospatial-intelligence-is-driving-sustainable-intensification-of-rice-fallows-in-odisha/

Srivastava, A. K., Borah, S. B., Ghosh Dastidar, P., Sharma, A., Gogoi, D., Goswami, P., Deka, G., Khandai, S., Borgohain, R., Singh, S., & Bhattacharyya, A. (2023). Rice-fallow targeting for cropping intensification through geospatial technologies in the rice belt of northeast India. *Agriculture, 13*(8), Article 1509. https://doi.org/10.3390/agriculture13081509

Subrahmaniyan, K., Kumar, G. S., Subramanian, E., Raju, M., Veeramani, P., & Ravi, V. (2023). Crop establishment methods and moisture mitigation practices in rice fallow blackgram for productivity enhancement in Cauvery Delta Zone of Tamil Nadu. *Legume Research, 46*(4), 502–505. https://doi.org/10.18805/LR-4364

Sundararajan, M., Taly, A., & Yan, Q. (2017). Axiomatic attribution for deep networks. In *Proceedings of the 34th International Conference on Machine Learning* (Vol. 70, pp. 3319–3328). PMLR. https://proceedings.mlr.press/v70/sundararajan17a.html

Tibshirani, R. J., Foygel Barber, R., Candès, E., & Ramdas, A. (2019). Conformal prediction under covariate shift. In *Advances in Neural Information Processing Systems* (Vol. 32, pp. 2530–2540). Curran Associates.

Torres, R., Snoeij, P., Geudtner, D., Bibby, D., Davidson, M., Attema, E., Potin, P., Rommen, B., Floury, N., Brown, M., Navas Traver, I., Deghaye, P., Duesmann, B., Rosich, B., Miranda, N., Bruno, C., L'Abbate, M., Croci, R., Pietropaolo, A., . . . Rostan, F. (2012). GMES Sentinel-1 mission. *Remote Sensing of Environment, 120*, 9–24. https://doi.org/10.1016/j.rse.2011.05.028

Vovk, V. (2012). Conditional validity of inductive conformal predictors. In *Proceedings of the Asian Conference on Machine Learning* (Vol. 25, pp. 475–490). PMLR.

Wang, H., Yao, Y., Liu, J., Zhang, X., Zhao, Y., Li, S., Liu, Z., Zhang, X., & Zeng, Y. (2025). Unsupervised cross-regional and cross-year adaptation by climate indicator discrepancy for crop classification. *Journal of Remote Sensing, 5*, Article 0439. https://doi.org/10.34133/remotesensing.0439

---

## Appendix A. Decision Log Summary

| ID | Date | Decision |
|---|---|---|
| D-016 | 10 Nov | Field unit = FTW polygons ≥ 0.1 ha |
| D-017 | 13 Nov | Pull per-field tables with `computeFeatures`, chunked and resumable |
| D-018 | 17 Nov | Odisha hand labels: past season, ~200 fields, single labeller |
| D-019 | 17 Nov | No 2026–27 data before the freeze, enforced in code |
| D-020 | 17 Nov | No land-cover filter; WorldCover fraction kept as a column |
| D-022 | 17 Nov | SICKLE split by neighbour group, ~20% locked |
| D-024 | 19 Nov | Recalled "typical" SICKLE dates excluded |
| D-025 | 19 Nov | Two sampling strata (amended: in practice one near-uniform sample) |
| D-026 | 19 Nov | Keep one FTW vintage (2025) |
| D-028 | 22 Nov | Sentinel-2 in the feature table (later amended: out of M1's point model) |
| D-030 | 23 Nov | M1 = four calendar features + temporal pooling |
| D-031 | 23 Nov | Pre-registered prediction: Odisha transplanting spread ≫ 10 d |
| D-032 | 23 Nov | Mondrian CQR per accumulation stratum |
| D-033/34 | 23 Nov | CSISA returns; disclosure of pre-freeze evidence |
| D-035 | 26 Nov | Protocol frozen as `protocol-v1` |
| D-036 | 26 Nov | M2 arms frozen; optical pseudo-labels; one unlock spent |

## Appendix B. Glossary

- **Kharif / rabi.** Monsoon (June–November) and winter (November–March) cropping seasons.
- **Rice fallow.** Land that grew kharif rice and is left idle in rabi.
- **Relay / zero-till sowing.** Sowing into the standing crop before harvest, or into unploughed soil after it.
- **Backscatter (VV, VH).** Radar energy returned to the satellite in two polarisations; VH rises as a canopy grows.
- **NDVI.** Normalised difference vegetation index, an optical greenness measure.
- **Lead / horizon.** Days between the issue date and the harvest.
- **Issue date (`as_of`).** The date a forecast is made; no input may post-date it.
- **Coverage.** The share of true values that fall inside the prediction intervals.
- **Pooling (here).** Averaging the harvest dates implied by a field's forecasts up to the issue date.
- **Zero-shot / few-shot.** Applying a model to a new region with no target labels / with a small number of them.

## Appendix C. Reproducibility Pointers

| Result | Script | Output |
|---|---|---|
| M1 baselines | `scripts/sickle_m1_baselines.py` | `runs/sickle_m1_baselines.csv` |
| M1 ablation and pooling | `scripts/sickle_m1_lightgbm.py` | `runs/sickle_m1_lightgbm.csv` |
| M1 intervals | `scripts/sickle_m1_conformal.py` | `runs/sickle_m1_conformal.csv` |
| Scoring-rule check | `scripts/interval_rule_check.py` | `runs/interval_rule_check.csv` |
| Transplanting spread (D-031) | `scripts/odisha_transplant_spread.py` | `runs/odisha_transplant_spread.csv` |
| Zero-shot / sensor arms | `scripts/odisha_m2_zero_shot.py`, `odisha_m2_sensors.py` | `runs/odisha_m2_zero_shot.csv`, `odisha_m2_sensors.csv` |
| Adaptation, final unlock | `scripts/odisha_m2_adapt.py`, `odisha_m2_final.py` | `runs/odisha_m2_final.csv`, `_pairs.csv` |
| XAI | `scripts/odisha_m2_xai.py` | `runs/odisha_m2_xai_*.csv` |

Git tags: `protocol-v1` (evaluation protocol), `m2-arms-frozen` (M2 arm list before the unlock).
