"""Shared synthetic fixtures: nothing here reads data/, so every test using them runs in CI."""

import pandas as pd
import pytest


@pytest.fixture
def odisha_labels() -> pd.DataFrame:
    lg = pd.to_datetime(["2025-11-20", "2025-12-10", "2026-01-05", "2025-12-01"])
    return pd.DataFrame(
        {
            "field_id": ["a", "b", "c", "d"],
            "district": ["baleswar", "baleswar", "bolangir", "bolangir"],
            "stratum": "U",
            "block": [1, 2, 3, 4],
            "status": ["ok", "ok", "ok", "cant_tell"],
            "last_green": lg.where([True, True, True, False]),
            "first_brown": (lg + pd.Timedelta(days=5)).where([True, True, True, False]),
            "eval_lock": [False, True, False, False],
        }
    ).assign(midpoint=lambda d: d.last_green + pd.Timedelta(days=2.5))
