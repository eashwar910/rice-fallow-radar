"""P1b step 5: turn the labelling tool's CSV exports into the Odisha label table.

Reads every `data/interim/odisha_labels/labels_*.csv` (one per session, newest row per `row_id`
wins), joins the sampling frame from `selected.parquet`, splits off the self-agreement repeats,
and writes the 200 first-labellings with the 60/40 evaluation lock of D-018.

The lock is assigned here, before any model sees the labels, from the fixed config seed: 60% of
the `ok` rows (balanced over district x stratum) are `eval_lock = True` and must not be touched
until final evaluation; the other 40% are available for M2 fine-tuning and recalibration.

Usage: uv run python scripts/odisha_label_ingest.py
Writes data/processed/odisha_labels.parquet and prints the summary the protocol asks us to report.
"""

from pathlib import Path

import pandas as pd
import yaml

OUT = Path("data/interim/odisha_labels")
DEST = Path("data/processed/odisha_labels.parquet")
L = yaml.safe_load(Path("configs/districts.yaml").read_text())["labelling"]
LOCK_FRAC = 0.6  # D-018: locked for final evaluation; the rest is M2 fine-tuning/recalibration
FRAME = [
    "row_id",
    "field_id",
    "district",
    "stratum",
    "repeat_of",
    "block",
    "area_m2",
    "tercile",
    "n_clear",
    "kharif_signature",
    "lon",
    "lat",
]


def read_sessions() -> pd.DataFrame:
    files = sorted(OUT.glob("labels_*.csv"))
    assert files, f"no labels_*.csv in {OUT} -- download one from the labelling tool first"
    lab = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    lab = lab.sort_values("labelled_at").drop_duplicates("row_id", keep="last")
    for c in ("last_green", "first_brown"):
        lab[c] = pd.to_datetime(lab[c])
    print(f"{len(files)} session file(s), {len(lab)} labelled rows")
    return lab


def joined() -> pd.DataFrame:
    sel = pd.read_parquet(OUT / "selected.parquet")[FRAME]
    lab = read_sessions()
    assert set(sel.row_id) == set(lab.row_id), "queue not finished (or unknown row_ids in the CSV)"
    df = sel.merge(lab.drop(columns=["district", "field_id"]), on="row_id", validate="1:1")
    ok = df.status == "ok"
    assert (df.loc[ok, "first_brown"] > df.loc[ok, "last_green"]).all(), "interval not ordered"
    assert df.loc[~ok, ["last_green", "first_brown"]].isna().all().all(), "dates on a non-ok row"
    # recompute rather than trust the browser's arithmetic
    df["interval_days"] = (df.first_brown - df.last_green).dt.days
    df["midpoint"] = df.last_green + (df.first_brown - df.last_green) / 2
    return df


def self_agreement(df: pd.DataFrame) -> None:
    pairs = df[df.repeat_of.notna()].merge(
        df[df.repeat_of.isna()], on="field_id", suffixes=("_r", "_1"), validate="1:1"
    )
    both_ok = pairs[(pairs.status_r == "ok") & (pairs.status_1 == "ok")]
    dd = (both_ok.midpoint_r - both_ok.midpoint_1).abs().dt.days
    print(f"\nself-agreement over {len(pairs)} repeats (protocol s3)")
    print(
        f"  status agree {(pairs.status_r == pairs.status_1).mean():.0%}, "
        f"rice agree {(pairs.rice_r.fillna('') == pairs.rice_1.fillna('')).mean():.0%}"
    )
    print(
        f"  |midpoint1 - midpoint2| over {len(dd)} both-ok pairs: "
        f"median {dd.median():.0f} d, mean {dd.mean():.1f} d, max {dd.max():.0f} d"
    )
    print(
        f"  disagreements: "
        f"{[f'{a}/{b}' for a, b in zip(pairs.status_1, pairs.status_r, strict=True) if a != b]}"
    )


def main() -> None:
    df = joined()
    self_agreement(df)

    first = df[df.repeat_of.isna()].drop(columns="repeat_of").reset_index(drop=True)
    assert len(first) == L["n_label"], f"{len(first)} first-labellings, expected {L['n_label']}"
    ok = first[first.status == "ok"]
    locked = ok.groupby(["district", "stratum"]).sample(frac=LOCK_FRAC, random_state=L["seed"])
    first["eval_lock"] = first.index.isin(locked.index)

    print(f"\nstatus x district ({len(first)} fields)")
    print(pd.crosstab(first.status, first.district, margins=True))
    print("\nrice tick, stratum U only (the probability sample, D-025)")
    print(first[first.stratum == "U"].rice.value_counts(dropna=False))
    print(f"\nharvest intervals ({len(ok)} ok rows)")
    print(
        f"  width: median {ok.interval_days.median():.0f} d, mean {ok.interval_days.mean():.1f} d"
        f", max {ok.interval_days.max():.0f} d"
    )
    print(f"  mean half-width {ok.interval_days.mean() / 2:.1f} d  <- Odisha MAE floor")
    print(f"  midpoint: {ok.midpoint.min():%Y-%m-%d} to {ok.midpoint.max():%Y-%m-%d}")
    n_lock = int(first.eval_lock.sum())
    print(f"\neval lock: {n_lock} locked / {len(ok) - n_lock} free, of {len(ok)} ok rows")
    print(pd.crosstab(ok.district, [ok.stratum, first.loc[ok.index, "eval_lock"]]))

    DEST.parent.mkdir(parents=True, exist_ok=True)
    first.to_parquet(DEST)
    print(f"\nwrote {DEST} ({len(first)} rows, {first.shape[1]} cols)")


if __name__ == "__main__":
    main()
