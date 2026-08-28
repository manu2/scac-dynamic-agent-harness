"""Tests for trajectory sequence validation and temporal invariant checks."""

from __future__ import annotations

import json
from pathlib import Path
from scac_harness.identity import compute_snapshot_id
from scac_harness.validator import validate_snapshot, validate_trajectory


FIXTURES_DIR = Path(__file__).parent / "fixtures"
VALID_DIR = FIXTURES_DIR / "valid"


def test_trajectory_monotonic_sequence_and_timestamps() -> None:
    """A valid trajectory with monotonically increasing sequence and timestamps must pass."""
    chk_data = json.loads((VALID_DIR / "full_checkpoint.json").read_text(encoding="utf-8"))
    delta_data = json.loads((VALID_DIR / "delta_snapshot.json").read_text(encoding="utf-8"))

    trajectory = [chk_data, delta_data]
    result = validate_trajectory(trajectory, current_time_ms=1787884201500)
    assert result.valid is True
    assert len(result.errors) == 0


def test_trajectory_rejects_regressing_sequence_numbers() -> None:
    """Trajectory validator must reject duplicate or decreasing sequence numbers."""
    snap1 = json.loads((VALID_DIR / "full_checkpoint.json").read_text(encoding="utf-8"))
    snap2 = json.loads((VALID_DIR / "delta_snapshot.json").read_text(encoding="utf-8"))
    snap2["seq"] = snap1["seq"]  # Duplicate seq

    result = validate_trajectory([snap1, snap2], verify_identity_hashes=False)
    assert result.valid is False
    assert any("Non-increasing sequence number" in err for err in result.errors)


def test_trajectory_rejects_regressing_timestamps() -> None:
    """Trajectory validator must reject regressing observation timestamps."""
    snap1 = json.loads((VALID_DIR / "full_checkpoint.json").read_text(encoding="utf-8"))
    snap2 = json.loads((VALID_DIR / "delta_snapshot.json").read_text(encoding="utf-8"))
    snap2["observed_at_ms"] = snap1["observed_at_ms"] - 500  # Regressing time

    result = validate_trajectory([snap1, snap2], verify_identity_hashes=False)
    assert result.valid is False
    assert any("Regressing observation timestamp" in err for err in result.errors)


def test_trajectory_rejects_stale_snapshot_at_injection_time() -> None:
    """Trajectory validator must reject an active snapshot whose fresh_for_ms window has expired."""
    snap1 = json.loads((VALID_DIR / "full_checkpoint.json").read_text(encoding="utf-8"))
    # snap1 has observed_at_ms=1787884200000, fresh_for_ms=2000 => expiry is 1787884202000
    current_time_ms = 1787884205000  # 3 seconds past expiry

    result = validate_trajectory([snap1], current_time_ms=current_time_ms)
    assert result.valid is False
    assert any("is stale" in err for err in result.errors)


def test_trajectory_rejects_unlinked_delta_snapshot() -> None:
    """Delta snapshot pointing to an unknown base_snapshot_id must be rejected."""
    delta_snap = json.loads((VALID_DIR / "delta_snapshot.json").read_text(encoding="utf-8"))
    delta_snap["base_snapshot_id"] = "f" * 64  # Not previously seen

    result = validate_trajectory([delta_snap], verify_identity_hashes=False)
    assert result.valid is False
    assert any("not previously seen in this trajectory" in err for err in result.errors)
