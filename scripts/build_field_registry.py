"""P1: build the field registry and print the per-district stats table for the interim report.

Usage: uv run python scripts/build_field_registry.py
Writes data/processed/fields.parquet and data/processed/field_registry_stats.csv.
First run downloads ~2 WorldCover COG windows per district (a few minutes), then caches them.
"""

from pathlib import Path

import yaml

from rice_fallow_radar.registry import fields

cfg = yaml.safe_load(Path("configs/districts.yaml").read_text())
out = Path("data/processed/fields.parquet")

reg = fields.build(list(cfg["districts"]), Path("data/raw"), out)
s = fields.stats(reg)
print(f"\n{len(reg):,} fields -> {out}\n")
print(s.to_string())
s.to_csv("data/processed/field_registry_stats.csv")
print("\nwrote data/processed/field_registry_stats.csv")
