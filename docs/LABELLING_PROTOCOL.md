# Odisha hand-labelling protocol (P1b)

Version 1, 19 Nov 2026. Frozen with `protocol-v1` (30 Nov). Decisions: D-018 (what is labelled),
D-020 (field unit), D-025 (sampling design). Written before any field was labelled.

This set is the only direct measurement of harvest dates in Odisha. It is the test set for M2
transfer and the reference that validates the radar harvest detector, so it has to be sampled and
recorded in a way that can be defended rather than in whatever way is quickest.

## 1. What is labelled

For each sampled field, in the **2025–26 kharif season**, the labeller records:

| Field | Values |
|---|---|
| `rice` | `yes` / `no` / `unsure` — was this field a kharif (monsoon) rice field in 2025? |
| `last_green` | date of the last image where the field is clearly a standing green crop |
| `first_brown` | date of the first image where the field is clearly harvested |
| `status` | `ok`, `not_rice`, `never_green`, `too_cloudy`, `cant_tell`, `not_a_field` |
| `notes` | free text |

The harvest label is the **interval** `(last_green, first_brown]`, not a single day. The point
estimate used in evaluation is the midpoint; the interval width is kept and reported, because it
is the precision floor on every Odisha error figure we quote.

### What counts as harvested

Harvested, in Sentinel-2 true colour at 10 m, is a **field-wide change from green to a uniform
pale brown/grey**, where the change:

- covers most of the polygon, not a strip or a corner;
- persists in the next available clear image (a one-image flicker is cloud shadow, haze or a
  mis-registration, not a harvest);
- is not accompanied by the field turning dark and smooth, which is standing water (flooding or
  re-puddling for a second crop), coded in `notes` and not treated as harvest.

The field-mean NDVI curve shown next to the chips should fall across the same interval. If the
chips say harvested and NDVI does not fall (or the reverse), the field is `cant_tell` — a
disagreement is a sign that the polygon does not match what is on the ground.

### Status codes

- `ok` — a harvest interval was identified. The only rows used as harvest labels.
- `not_rice` — a crop, but not kharif rice (`rice = no`). Kept: it validates the rice mask (D-021).
- `never_green` — bare or fallow all season; no harvest to label. Kept for M4.
- `too_cloudy` — fewer than two clear images in the Nov–Jan harvest window, or a gap longer than
  25 days spanning the change. Kept, with the gap recorded, so cloud-driven exclusion is reported
  rather than silent.
- `cant_tell` — clear images exist but the labeller cannot call it (mixed polygon, chips and NDVI
  disagree, change too gradual).
- `not_a_field` — the polygon is not farmland (FTW false positive, D-020 says ~2–3% of these).

**Never guess.** `cant_tell` costs one row; a guessed date silently biases the test set. The
dissertation reports the full code distribution, so unusable fields are evidence, not failure.

## 2. Sampling design (D-025)

Sampling frame: `data/processed/fields.parquet` — FTW polygons ≥ 0.1 ha in Bolangir and Baleswar.
No land-cover or rice filter is applied to the frame (D-020), so the frame includes non-fields.

Two strata, both drawn with a fixed seed from the same candidate pool, district-balanced and
spread over the 5 km blocks of the registry:

- **Stratum U (uniform, ~100 fields).** Drawn at random within district × field-size tercile ×
  spatial block. This is a probability sample of the frame, so it is the stratum that supports
  unbiased statements: rice prevalence, FTW false-positive rate, the share of fields too cloudy
  to label.
- **Stratum K (kharif-signature, ~100 fields).** Drawn the same way, but restricted to fields
  whose **Sentinel-2 NDVI** series shows a monsoon crop (green in Sep–Oct, brown by Jan). Its
  purpose is to buy enough harvest dates: Open-SARice suggests only ~20% of Bolangir fields are
  rice, so a uniform-only sample of 200 would yield very few Bolangir harvest dates.

**What actually happened (19 Nov 2026, after the pull).** The kharif criterion is
non-selective here: 88% of Bolangir and 94% of Baleswar pool fields pass it, as do 91% of the
fields drawn into stratum U, and the two strata match on every covariate. So the 200 fields are
**effectively one near-uniform sample** and are analysed that way: pooled for the headline, split
by stratum only as a check (D-025, amended). The reason is that an NDVI rise and fall marks *any*
monsoon crop, not rice — which is exactly why the `rice` tick below carries more weight than
originally planned. Cloud is also a smaller problem than feared: no pool field had fewer than 4
clear Sentinel-2 images (median 37–39).

Held out: after labelling, a fixed 60% of `ok` rows (seeded, stratum- and district-balanced) is
locked for final evaluation; 40% is available for M2 fine-tuning and conformal recalibration
(D-018). The lock is a column in the output, written before any model sees the labels.

## 3. Self-agreement

20 of the 200 fields are shown a second time, at the end of the queue, re-coded under new ids so
the labeller does not recognise them. This gives, over ~20 pairs:

- agreement on `rice` and on `status`;
- the distribution of `|midpoint1 − midpoint2|` in days, reported as the **labeller's own noise
  floor** alongside every Odisha MAE.

Only the first labelling of a repeated field enters the test set, so the repeats do not
double-weight those fields.

## 4. Procedure

1. Run `scripts/odisha_label_tool.py` (chips and NDVI are pre-generated; the tool is offline HTML).
2. Open `data/interim/odisha_labels/index.html`.
3. For each field: read the NDVI curve, then step through the chip strip. Tick `rice`, then click
   the **last clear green** chip and the **first clear brown** chip, or pick a status code.
4. Progress is saved in the browser (localStorage) after every action; the queue can be left and
   resumed. Download the CSV at the end of each session to
   `data/interim/odisha_labels/labels_<date>.csv`.
5. Do not look at any model output, the rice mask, or the radar curves while labelling.
6. Label in sessions of at most ~60 fields; fatigue shows up as drift towards the middle of the
   strip. Record the session boundaries (the CSV timestamps each row), so drift can be checked.

## 5. Known limitations (state these in the dissertation)

- **Precision floor.** Sentinel-2 revisit is 5 days and Nov–Jan in coastal Odisha is cloudy, so a
  typical interval is 5–15 days wide. Odisha MAEs below the mean interval half-width are not
  meaningful.
- **One labeller, no expert.** Eashwar is not an agronomist and has not visited the fields.
  Self-agreement measures consistency, not correctness; there is no inter-rater estimate.
- **Interpreting imagery, not ground truth.** The label is what a 10 m optical image shows, which
  is a proxy for "harvested and workable". M3's workability window is a different quantity.
- **Polygon error is label error.** A merged or split FTW polygon can mix two fields harvested
  weeks apart; the `cant_tell` and `notes` fields are where that shows up.
- **Stratum K is selected on visible phenology** (§2).
- **One season only** (2025–26), so season-to-season variation in Odisha is not measured. The
  2026–27 replay has no hand labels at all (D-018).
