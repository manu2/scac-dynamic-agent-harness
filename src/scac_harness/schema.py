"""Schema loading and validator caching for versioned SST snapshots."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any
import jsonschema
from jsonschema.validators import Draft202012Validator


_CACHED_SCHEMA: dict[str, Any] | None = None
_CACHED_VALIDATOR: Draft202012Validator | None = None


def load_sst_schema() -> dict[str, Any]:
    """Load the raw JSON Schema Draft 2020-12 definition for SST v0.1."""
    global _CACHED_SCHEMA
    if _CACHED_SCHEMA is None:
        path = files("scac_harness.schemas").joinpath("scac-sst-v0.1.json")
        _CACHED_SCHEMA = json.loads(path.read_text(encoding="utf-8"))
    return _CACHED_SCHEMA


def get_sst_validator() -> Draft202012Validator:
    """Return a cached jsonschema Draft202012Validator instance for SST v0.1."""
    global _CACHED_VALIDATOR
    if _CACHED_VALIDATOR is None:
        schema = load_sst_schema()
        Draft202012Validator.check_schema(schema)
        _CACHED_VALIDATOR = Draft202012Validator(schema)
    return _CACHED_VALIDATOR
