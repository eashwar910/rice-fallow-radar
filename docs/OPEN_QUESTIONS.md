# Open questions, risks and ideas

Things that aren't settled. Some need an answer soon; some are just worth thinking about. Move resolved items to `DECISIONS.md` with the answer.

---

## Needs an answer soon (P0–P1)

1. ~~**Is FTW usable in Bolangir and Baleswar?**~~ *Answered 10 Nov:* partly. Dense cells usable, sparse cells contain false polygons. Field unit = FTW ≥ 0.1 ha (D-016), plus a cropland filter (see 7).
2. ~~**What exactly is in SICKLE?**~~ *Answered 6 Nov* (DATA.md §SICKLE): 319 exact labels / 131 plots / 2019–20; test split empty; coordinates withheld. Licence still open (see 10).
3. **Which years should the Odisha hand labels cover?** Past seasons (e.g., 2023–25) keep them clean for model selection; 2026–27 labels would serve the replay. Probably both, kept separate.
4. **How does the protocol freeze interact with pipeline development?** P1 will naturally pull recent Sentinel-1 data over Odisha, which may include early 2026–27 passes. Decide whether pipeline debugging can touch post-Oct 2026 data (probably fine for plumbing, not for tuning) and write that into the protocol.
5. ~~**Earth Engine compute budget.**~~ *Answered 6/13 Nov:* Community tier is enough (S1 ≈ 10 EECU-h per season for both districts); pull route is `computeFeatures` (D-017).
6. **Exam and winter-break dates** — needed to make the Dec–Jan plan realistic.
7. **Cropland filter for FTW** (added 17 Nov). D-016 needs one; none chosen or tested. Candidates: ESA WorldCover 2021 (10 m, "cropland" class), Dynamic World (10 m, near-real-time, per-date class probabilities), or a radar rule (a flooded-then-growing VH signature also gives the rice mask, see 8). Test on the 12 rated FTW cells: does it remove the false polygons Eashwar flagged without dropping real fields?
8. **Rice mask** (added 17 Nov). Which polygons were kharif rice in a given year. Options: an S1 rule (VH dip at transplanting flood, then rise), an existing product if one covers Odisha at field scale (not yet checked), or a small classifier trained on hand-checked polygons. Needs its own accuracy check against the P1b labels.
9. **SICKLE split (proposed D-018, not yet decided).** Grouped CV by connected components of the plot co-occurrence graph built from the masks (DATA.md §SICKLE). To check before deciding: how many components there are and how big the largest is. If one giant component swallows most plots, fall back to leave-one-year-out plus season grouping.
10. **SICKLE licence and test set.** Email to authors drafted 5 Nov (licence, test set, coordinates, S1 pre-processing). Confirm it was sent; without a licence, derived data can't be redistributed (affects the "open benchmark" idea).
11. **Weather for SICKLE plots without coordinates** (added 17 Nov). M1 is meant to use radar + weather, but SICKLE plot locations are withheld and the mask GeoTIFFs have their georeferencing stripped, so CHIRPS/ERA5 can't be sampled per plot. Options: (a) one regional weather series for the SICKLE study area (Cauvery delta, Tamil Nadu; exact extent to confirm from the paper); since CHIRPS is ~5 km and ERA5-Land ~9 km, per-plot weather would barely differ from regional anyway, so the loss may be small; (b) recover approximate locations by matching the S1 patches against the GEE `COPERNICUS/S1_GRD` scenes they came from (scene IDs are in the filenames), which would also give per-plot weather and true spatial blocks, but is fiddly and may conflict with the authors' privacy intent, so ask them first; (c) drop weather from M1 and add it in M2/M3 only, as an ablation. Leaning (a), with (b) only if the authors agree.
12. **Use of the 588 "rough" SICKLE dates** (added 17 Nov). Typical recalled dates, not observations. Excluded from M1 training and evaluation for now; could be tried as weak labels (down-weighted) in an ablation.

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
