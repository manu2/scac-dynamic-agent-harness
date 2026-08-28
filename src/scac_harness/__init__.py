"""Dynamic SCAC telemetry harness."""

from scac_harness.events import RawTelemetryEvent
from scac_harness.identity import (
    canonical_json_bytes,
    canonical_json_dumps,
    compute_content_hash,
    compute_snapshot_id,
    verify_snapshot_id,
)
from scac_harness.reducer import DeterministicReducer
from scac_harness.renderer import render_tier1_system_prefix, render_tier2_envelope
from scac_harness.schema import get_sst_validator, load_sst_schema
from scac_harness.validator import (
    SnapshotValidationResult,
    TrajectoryValidationResult,
    validate_snapshot,
    validate_trajectory,
)

__version__ = "0.1.0"

__all__ = [
    "RawTelemetryEvent",
    "DeterministicReducer",
    "SnapshotValidationResult",
    "TrajectoryValidationResult",
    "canonical_json_bytes",
    "canonical_json_dumps",
    "compute_content_hash",
    "compute_snapshot_id",
    "get_sst_validator",
    "load_sst_schema",
    "render_tier1_system_prefix",
    "render_tier2_envelope",
    "validate_snapshot",
    "validate_trajectory",
    "verify_snapshot_id",
]
