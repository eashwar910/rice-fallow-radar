# CLAUDE.md

Context for Claude (and any other collaborator) working in this repository.

**Read this first:** everything in this file and in `docs/` describes *the current plan and why it looks the way it does*. None of it is a rule. If you see a better model, a cleaner structure, a faster route, a flaw in the evaluation, or a reason to drop something, say so and make the case. The proposal was written before a single line of code existed, and some of it will turn out to be wrong. Improving on it is the point.

The only things that are genuinely fixed are external: university deadlines, the research questions and objectives as submitted (they can be reinterpreted or narrowed, with a note in the dissertation, but not silently replaced), and honest reporting of results.

---

## What this project is

**Rice Fallow Radar** — Final Year Project (COMP3025 Individual Dissertation, 2026/27), supervised by Dr. Tissa Chandesa.

Title: *Forecasting When Each Field Can Be Sown: Transferable, Explainable Machine Learning on Satellite Time Series for India's Rice Fallows.*

In one paragraph: about 11.65 million hectares of India's monsoon rice land sits idle through winter. Much of it could grow a pulse (lentil, black gram) on the moisture the rice leaves behind, but only inside a short per-field window that opens when the field is harvested and workable and closes when the soil dries. Nobody currently forecasts that window per field before harvest. This project builds an ML system that, every week, forecasts each field's harvest date 7/14/21 days ahead from radar + weather, transfers that forecaster from labelled Tamil Nadu plots to unlabelled Odisha, combines it with a soil-moisture forecast into a too-wet / workable / too-dry window, ranks fields by likely winter-crop success with positive-unlabelled learning, and explains its predictions.

Study districts: **Bolangir** (western uplands, dry edge dominates) and **Baleswar** (coastal plain, wet edge dominates).

### Why it is a computer science project
The supervisor's main critique of earlier drafts was that it read like agronomy. The CS contribution is four ML problems, and work should keep them visible:

1. **Forecasting from irregular, noisy time series** with calibrated uncertainty (M1).
2. **Domain adaptation** of a date regressor across regions, and whether conformal intervals survive the shift (M2).
3. **Explainability used diagnostically** — attributions that are tested for faithfulness and used to explain *why* transfer fails, not just decorate outputs.
4. **Positive-unlabelled learning** where the "labelled positives are a random sample" assumption is known to be violated (M4).

## Where to find things

| File | What's in it |
|---|---|
| `README.md` | Short public-facing overview and setup |
| `docs/ROADMAP.md` | Phases, dates, deliverables, current status |
| `docs/ARCHITECTURE.md` | Pipeline design, data flow, suggested repo layout |
| `docs/MODELS.md` | M1–M4 + alerts: what each does, current method choice, alternatives |
| `docs/DATA.md` | Every data source, what it's used for, known quirks |
| `docs/EVALUATION.md` | Splits, metrics, baselines, success criteria, replay protocol |
| `docs/DECISIONS.md` | Decisions made so far and the reasoning, so they can be revisited knowingly |
| `docs/OPEN_QUESTIONS.md` | Unresolved questions, risks, and ideas worth exploring |
| `docs/GLOSSARY.md` | Agriculture and remote-sensing terms in plain language |
| `docs/LOG.md` | Running progress log |

Source of truth for *claims made to the university* is the submitted proposal (`TC_20717304_proposal.pdf`). These docs elaborate on it; where they disagree, the proposal says what was promised and the docs say what we now think.

## How I'd like Claude to work with me

These are preferences, not constraints.

- **Challenge the plan.** If a method choice, metric, split or scope decision looks weak, say so with reasons, even if I didn't ask. Suggest the better option and what it would cost in time.
- **Explain the ML, not just write it.** I need to defend every choice in a viva and a dissertation. When you introduce a technique, give me the one-line intuition and the reference.
- **Think in terms of the dissertation.** Useful work produces a result, figure or table I can write about. Point out when something would make a good figure or ablation.
- **Keep the time budget honest.** The deadlines are tight (see `ROADMAP.md`). If something will blow the schedule, flag it and propose a cheaper version.
- **Update the docs when reality changes.** If we change a decision, add an entry to `DECISIONS.md`; if we learn something about a dataset, add it to `DATA.md`; log progress in `LOG.md`. Small, factual edits are better than rewrites.
- **Mark uncertainty.** If you're not sure a dataset, API or paper says what we think it says, say so rather than guessing. Several data facts here were checked in October 2026 and may have changed.

## Things that are easy to get wrong in this project

Not rules — just the traps most likely to quietly invalidate results:

- **Temporal leakage.** Every feature for a prediction at issue date `as_of` must come from data that existed on `as_of`. This includes final vs. preliminary products (CHIRPS), reanalysis lag (ERA5-Land), and annual products that summarise a whole year (AlphaEarth embeddings for year Y already contain year Y's winter crop — use Y−1).
- **Spatial leakage.** Neighbouring plots are correlated. Random row splits will flatter results; split by plot, year and spatial block.
- **The 2026–27 replay.** The evaluation protocol is meant to be frozen on 30 Nov 2026, before 2026–27 imagery is used to tune anything. If we deviate, document it.
- **PU labels are biased.** Fields that got sown are not a random sample of sowable fields (seed access, labour, irrigation). Read every M4 metric as a lower bound.
- **Calibration under shift.** Conformal intervals calibrated on Tamil Nadu do not guarantee coverage in Odisha. Recalibration on Odisha labels is part of the plan for that reason.

## Environment (current assumptions)

- Python; LightGBM, PyTorch, scikit-learn; Streamlit for the dashboard.
- Google Earth Engine (noncommercial tier) for heavy raster work; models train locally (MacBook M4 Pro) or on free Colab GPUs.
- Budget RM0–100. No paid messaging gateway — alerts are generated, not sent.
- No human participants: no farmers contacted, survey data used only under its licence and after ethics approval.

## About me

Eashwar. Comfortable with Python and ML; agriculture and remote sensing are newer, so plain-language explanations of domain terms help (see `GLOSSARY.md`). I prefer docs and guidance that leave room to improvise.
