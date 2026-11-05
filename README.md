# Rice Fallow Radar

**Forecasting when each field can be sown: transferable, explainable machine learning on satellite time series for India's rice fallows.**

Final Year Project · COMP3025 Individual Dissertation · University of Nottingham Malaysia (School of Computer and Mathematical Sciences), 2026/27
Supervisor: Dr. Tissa Chandesa

---

## The problem

Around 11.65 million hectares of India's monsoon rice land (29%) lies fallow through winter, mostly in the eastern states. A winter pulse such as lentil or black gram can grow on the moisture left after rice — sown into the standing crop just before harvest (*paira*/relay sowing) or into unploughed soil just after (zero-till). Each field's window has two edges: it **opens** when the field is harvested and not waterlogged, and **closes** when the soil dries too far.

Current practice targets seed by administrative block using maps made after the season. Nothing tells an adviser when a particular field's window will open or close.

## What this project builds

| Component | Purpose |
|---|---|
| **M1** Harvest forecaster | Forecasts each field's harvest date 7, 14 and 21 days ahead from Sentinel-1 radar and weather, with calibrated intervals |
| **M2** Cross-region transfer | Adapts M1 from labelled Tamil Nadu plots (SICKLE) to Odisha, and diagnoses what accuracy is lost and why |
| **M3** Sowing window | Combines M1 with a soil-water balance into a per-field too-wet / workable / too-dry window |
| **M4** Winter-crop success | Ranks fields by likely success using positive-unlabelled learning, with checkable reason codes |
| Alerts and dashboard | Weekly Odia/English alert text (generated, not sent) and a Streamlit dashboard for district farm-advice centres |

Study area: Bolangir and Baleswar districts, Odisha.

## Repository status

Early development (November 2026). See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the plan and [`docs/LOG.md`](docs/LOG.md) for progress.

## Documentation

- [`CLAUDE.md`](CLAUDE.md) — context for AI-assisted development
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — phases and milestones
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system design
- [`docs/MODELS.md`](docs/MODELS.md) — model specifications
- [`docs/DATA.md`](docs/DATA.md) — data sources and caveats
- [`docs/EVALUATION.md`](docs/EVALUATION.md) — evaluation design
- [`docs/DECISIONS.md`](docs/DECISIONS.md) — decision log
- [`docs/OPEN_QUESTIONS.md`](docs/OPEN_QUESTIONS.md) — open questions and ideas
- [`docs/GLOSSARY.md`](docs/GLOSSARY.md) — terms explained

## Setup

_To be filled in once the environment is pinned._ Expected: Python 3.11+, an Earth Engine noncommercial project, and NASA Earthdata credentials for NISAR/SMAP.
