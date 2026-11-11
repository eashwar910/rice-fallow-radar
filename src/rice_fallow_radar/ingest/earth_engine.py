"""Earth Engine session setup.

Uses a service-account key if present (no browser consent screen, works in Colab/CI),
otherwise falls back to credentials from `earthengine authenticate`.
"""

import json
import os
from pathlib import Path

import ee

PROJECT = os.environ.get("RFR_EE_PROJECT", "rice-fallow-radar")
KEY_FILE = Path(
    os.environ.get("RFR_EE_KEY", Path.home() / ".config" / "earthengine" / "rfr-sa.json")
)


def init() -> None:
    creds = None
    if KEY_FILE.exists():
        email = json.loads(KEY_FILE.read_text())["client_email"]
        creds = ee.ServiceAccountCredentials(email, key_file=str(KEY_FILE))
    ee.Initialize(creds, project=PROJECT)
