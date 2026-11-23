"""Build the CSISA Odisha calendar prior (D-033) -> data/processed/csisa_odisha_calendar.parquet.

An alternative to SICKLE's calendar for the M2 "Odisha-calendar" ablation arm. Writes one row per
district scope and prints the comparison against SICKLE's 10.0 d transplanting spread (D-031).

Deliberately does NOT score anything against the Odisha hand labels: D-031 requires the
transplanting-spread measurement before any Odisha harvest model is tuned.

Usage: uv run python scripts/csisa_odisha_calendar.py
"""

from pathlib import Path

import pandas as pd

from rice_fallow_radar.features import odisha_calendar as oc

SRC = Path("data/processed/csisa_rice.parquet")
DEST = Path("data/processed/csisa_odisha_calendar.parquet")
SCOPES = (
    None,
    "Balasore",
    "Bhadrak",
    "Jajpur",
    "Jagatsinghpur",
    "Cuttack",
    "Khordha",
    "Mayurbhanj",
)


def main() -> None:
    csisa = pd.read_parquet(SRC)
    rows = [oc.prior(csisa, s) for s in SCOPES]
    out = pd.DataFrame([r for r in rows if r.n >= oc.MIN_VARIETY_N])
    DEST.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(DEST)

    show = ["district", "n", "villages", "transplant_q50", "transplant_sd", "transplant_robust_sd"]
    show += ["duration_q50", "harvest_q50", "harvest_sd", "transplant_sd_vs_sickle"]
    print(f"wrote {DEST}\n")
    print(out[show].to_string(index=False, float_format=lambda v: f"{v:.1f}"))
    print(
        "\n(transplant/harvest quantiles are days since 1 Jun; "
        f"SICKLE transplanting SD = {oc.SICKLE_TRANSPLANT_SD} d)"
    )

    bal = out[out.district == "Balasore"].squeeze()
    zs = oc.zero_shot_harvest(bal, year=2025)
    print(
        f"\nBaleswar zero-shot arm for the 2025-26 season: harvest {zs['harvest_date']:%d %b %Y}, "
        f"90% interval {zs['lower']:%d %b} - {zs['upper']:%d %b} ({zs['width_days']:.0f} d wide)"
    )
    print("\nper-variety durations, Balasore (diagnosis + the secondary eval set only)")
    print(oc.variety_durations(csisa, "Balasore").to_string(index=False))


if __name__ == "__main__":
    main()
