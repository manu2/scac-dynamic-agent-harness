"""Schema loading helpers for versioned SST snapshots."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any


def load_sst_schema() -> dict[str, Any]:
    path = files("scac_harness.schemas").joinpath("scac-sst-v0.1.json")
    return json.loads(path.read_text(encoding="utf-8"))
