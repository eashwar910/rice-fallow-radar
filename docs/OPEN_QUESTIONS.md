# Open questions, risks and ideas

Things that aren't settled. Some need an answer soon; some are just worth thinking about. Move resolved items to `DECISIONS.md` with the answer.

---

## Needs an answer soon (P0–P1)

1. **Is FTW usable in Bolangir and Baleswar?** Polygon quality on smallholder plots is the foundation of everything. Measure it in the first week.
2. **What exactly is in SICKLE?** Plot count vs. labelled seasons (388 plots vs. ~351 paddy seasons reported), coordinate precision, licence for derived data, which sensors are included.
3. **Which years should the Odisha hand labels cover?** Past seasons (e.g., 2023–25) keep them clean for model selection; 2026–27 labels would serve the replay. Probably both, kept separate.
4. **How does the protocol freeze interact with pipeline development?** P1 will naturally pull recent Sentinel-1 data over Odisha, which may include early 2026–27 passes. Decide whether pipeline debugging can touch post-Oct 2026 data (probably fine for plumbing, not for tuning) and write that into the protocol.
5. **Earth Engine compute budget.** Which tier, and how many EECU-hours a full district-season export costs.
6. **Exam and winter-break dates** — needed to make the Dec–Jan plan realistic.

## Method questions (worth experimenting on)

- **Regularising the radar series:** resample to a fixed grid (interpolation), keep irregular with time-since-last-pass, or use a model that handles irregular sampling natively? A small ablation would make a good dissertation paragraph.
- **Calendar time vs. phenological time:** expressing the series relative to an anchor (e.g., VH peak) instead of day-of-year might reduce the cross-region shift by itself.
- **One multi-horizon model or one per horizon?**
- **Harvest detector for pseudo-labels:** how accurate does it need to be before pseudo-labelling helps rather than hurts? A curve of M2 gain vs. detector error (simulated by corrupting labels) would answer this.
- **M3 weather in the replay:** use forecasts as issued (realistic) or observed weather (upper bound)? Possibly report both.
- **M3 establishment threshold:** which moisture value closes the window for lentil vs. black gram, and from which source?
- **M4 positives selection bias:** can we measure it (positives vs. unlabelled on distance to road/irrigation/market) and does a propensity-aware method help?
- **M4 class prior:** what range is plausible, and how much do rankings move across it?
- **Field size floor:** below what area does Sentinel-1 stop giving a usable signal?

## Risks

| Risk | Effect | Possible response |
|---|---|---|
| FTW polygons poor in study area | No reliable unit of analysis | Re-threshold FTW; S2 segmentation; grid cells as fallback |
| SICKLE too small / too different | M1 weak, transfer gap huge | Treat the gap as the finding; lean on few-shot with Odisha labels |
| Odisha labelling slower than expected | M2 test set thin | Prioritise held-out test set; reduce fine-tuning set |
| NISAR provisional data unreliable | M3 dry edge weak | SMAP / ISRO 100 m product; report as limitation |
| Earth Engine quota exceeded | Pipeline stalls | Export tables only; reduce time span; Contributor tier |
| Dec–Jan exams/break | Schedule slip on M2 | Protect gap measurement + ablation; drop model variants |
| Overfitting to small test sets | Optimistic claims | Grouped splits, bootstrap CIs, one final untouched test |

## Ideas that could make the project stronger (if time allows)

- Release the Odisha hand-labelled set and the TN→Odisha transfer split as a small open benchmark.
- An end-of-season report comparing what the system said each week with what happened — doubles as a dissertation figure.
- Test transfer to a third region (e.g., Bangladesh, which has similar rice fallows) as a portability check.
- A simple field-check form design for extension officers (stretch; no data collection, just the design).
- Compare against the IRRI–Odisha block-level suitability classes if obtainable — the most realistic "current practice" baseline.
