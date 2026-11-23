# Open questions, risks and ideas

Things that aren't settled. Some need an answer soon; some are just worth thinking about. Move resolved items to `DECISIONS.md` with the answer.

---

## Needs an answer soon (P0–P1)

1. ~~**Is FTW usable in Bolangir and Baleswar?**~~ *Answered 10 Nov:* partly. Dense cells usable, sparse cells contain false polygons. Field unit = FTW ≥ 0.1 ha (D-016), plus a cropland filter (see 7).
2. ~~**What exactly is in SICKLE?**~~ *Answered 6 Nov* (DATA.md §SICKLE): 319 exact labels / 131 plots / 2019–20; test split empty; coordinates withheld. Licence still open (see 10).
3. ~~**Which years should the Odisha hand labels cover?**~~ *Answered 17 Nov (D-018):* past seasons only (2025–26, some 2024–25), ~200 fields labelled by Eashwar. Reconsider adding 2026–27 for the replay in Jan 2027.

4. ~~**How does the protocol freeze interact with pipeline development?**~~ *Answered 17 Nov (D-019):* strict. Code refuses dates ≥ 1 Jun 2026 until `protocol-v1` is tagged.
5. ~~**Earth Engine compute budget.**~~ *Answered 6/13 Nov:* Community tier is enough (S1 ≈ 10 EECU-h per season for both districts); pull route is `computeFeatures` (D-017).
6. ~~**Exam and winter-break dates**~~ *Closed 17 Nov:* Eashwar: not needed; internal dates aren't binding.
7. ~~**Cropland filter for FTW**~~ *Answered 17 Nov (D-020):* no land-cover filter. After the 0.1 ha cut only ~2–3% of polygons are false, and WorldCover/Dynamic World drop more real fields than fakes. WorldCover fraction kept as a quality column; the rice mask (8) does the filtering.
8. ~~**Rice mask**~~ *Answered 17 Nov (D-021):* hybrid. Strict S1 rule → pseudo-labels + cluster check for direct-seeded rice → LightGBM, early-season data only. Literature and data leads in DATA.md §Rice mask. Email to IRRI Odisha (odisha@irri.org) sent 17 Nov asking for kharif ground-truth points; optional, blocks nothing.
9. ~~**SICKLE split**~~ *Answered 17 Nov (D-022):* 43 neighbour groups (largest 9% of dates); ~20% of groups locked as final test, 5-fold StratifiedGroupKFold (by season) on the rest.
10. **SICKLE licence and test set.** Email to authors sent; no reply as of 17 Nov. Plan as if no reply comes: no test set, no coordinates, no licence. Without a licence, derived data can't be redistributed (affects the "open benchmark" idea), and the dissertation should say the licence was requested and not received.
11. ~~**Weather for SICKLE plots without coordinates**~~ *Answered 19 Nov (D-023):* option (a) — one regional weather series per season for the SICKLE study area (Cauvery delta; exact districts still to confirm from the paper), with a column in the feature table marking regional vs per-field weather. No attempt to recover plot locations from the S1 scene IDs.
13. **The hand labels cannot validate the rice mask on their own.** Labelling (20 Nov) left 75 of 153 harvest-labelled fields as `rice = unsure`, and repeat agreement on the `rice` tick is 55% (DATA.md §Odisha hand labels). So kharif-rice prevalence from this sample is a range (40–82% of fields), not a number, and D-021's mask has no sharp reference to be scored against. Options: (a) accept it — report mask agreement only on the 77 confident `yes` and 13 `no` fields, with the `unsure` share stated; (b) re-tick `rice` on the `unsure` fields with the full S2 time series rather than the harvest-window chips (a kharif rice field floods before it greens — the dark-then-green signature was not shown to the labeller, which is probably *why* so many are unsure); (c) score the mask against Open-SARice 2024 instead and treat the hand labels as a sanity check only. (b) is cheap (~1 h, no new EE pull — the NDVI series is already in `ndvi.parquet`) and would also make the prevalence statement publishable; it does not touch any harvest date, so it is not a protocol change.

14. **CSISA licence and permission to use.** Both rice Landscape Diagnostic Surveys (2017, 2018) are published on CIMMYT Dataverse with **no licence** and the note *"made available without information on how it can be used… communicate with the Contact(s) before use"* (contact: Anurag Ajay, CIMMYT). Checked and downloaded 23 Nov 2026; **contact not yet made**. Same posture as 10: plan as if no reply comes. Consequences if permission is refused or never arrives — the Balasore secondary evaluation set (EVALUATION.md) is struck and the strike is recorded, the D-033 calendar prior comes out of M2's ablation, and D-005 stands as originally written. Consequences that hold either way: raw files and row-level derivatives stay in `data/` (gitignored), nothing is redistributed, and only group-level statistics appear in `reports/`. The dissertation states that permission was requested. **No step waits on the reply.**

12. ~~**Use of the 588 "rough" SICKLE dates**~~ *Answered 19 Nov (D-024):* excluded from M1 training, validation and test. Optional later ablation as down-weighted weak labels, reported separately.

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
