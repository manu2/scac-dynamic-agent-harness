"""Snapshot and trajectory validation engine for SCAC SST v0.1."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from scac_harness.identity import compute_snapshot_id, verify_snapshot_id
from scac_harness.schema import get_sst_validator


@dataclass(frozen=True)
class SnapshotValidationResult:
    """Result of validating a single SST snapshot against schema and cryptographic invariants."""

    valid: bool
    errors: list[str] = field(default_factory=list)

    def raise_for_errors(self) -> None:
        if not self.valid:
            raise ValueError(f"Snapshot validation failed: {'; '.join(self.errors)}")


@dataclass(frozen=True)
class TrajectoryValidationResult:
    """Result of validating a sequence of SST snapshots in a multi-turn trajectory."""

    valid: bool
    errors: list[str] = field(default_factory=list)

    def raise_for_errors(self) -> None:
        if not self.valid:
            raise ValueError(f"Trajectory validation failed: {'; '.join(self.errors)}")


def _get_path_value(d: dict[str, Any], path: str) -> Any:
    """Retrieve value from a nested dict using dot notation."""
    parts = path.split(".")
    curr: Any = d
    for p in parts:
        if isinstance(curr, dict) and p in curr:
            curr = curr[p]
        else:
            return None
    return curr


def validate_snapshot(
    snapshot: dict[str, Any],
    verify_identity_hash: bool = True,
) -> SnapshotValidationResult:
    """Validate a single snapshot against JSON schema Draft 2020-12 and strict integrity rules."""
    errors: list[str] = []

    # 1. JSON Schema validation
    validator = get_sst_validator()
    schema_errors = sorted(validator.iter_errors(snapshot), key=lambda e: e.path)
    for err in schema_errors:
        path = ".".join(str(p) for p in err.path) if err.path else "root"
        errors.append(f"Schema violation at '{path}': {err.message}")

    # 2. Check kind and base_snapshot_id consistency
    kind = snapshot.get("kind")
    base_snapshot_id = snapshot.get("base_snapshot_id")
    if kind == "delta":
        if not base_snapshot_id or not isinstance(base_snapshot_id, str):
            errors.append("Delta snapshot must specify a non-empty 'base_snapshot_id'.")
    elif kind == "full_checkpoint":
        pass

    # 3. Explicit check: unavailable metrics must never be represented as zero
    unavail = snapshot.get("unavailable_fields", [])
    for field_path in unavail:
        val = _get_path_value(snapshot, field_path)
        # If val is 0 or 0.0 (and not a boolean False), it violates "missing must never be encoded as zero"
        if val == 0 and not isinstance(val, bool):
            errors.append(
                f"Unsupported metric '{field_path}' represented as 0 while declared in unavailable_fields."
            )

    # 4. Snapshot identity verification
    if verify_identity_hash and "snapshot_id" in snapshot:
        if not verify_snapshot_id(snapshot):
            expected = compute_snapshot_id(snapshot)
            actual = snapshot.get("snapshot_id")
            errors.append(
                f"Snapshot ID mismatch: declared '{actual}' but canonical hash is '{expected}'."
            )

    return SnapshotValidationResult(valid=len(errors) == 0, errors=errors)


def validate_trajectory(
    snapshots: list[dict[str, Any]],
    current_time_ms: int | None = None,
    verify_identity_hashes: bool = True,
) -> TrajectoryValidationResult:
    """Validate a temporal sequence of snapshots across a single trajectory."""
    if not snapshots:
        return TrajectoryValidationResult(valid=False, errors=["Empty trajectory: no snapshots provided."])

    errors: list[str] = []
    seen_snapshot_ids: set[str] = set()
    first_snapshot = snapshots[0]
    expected_trajectory_id = first_snapshot.get("trajectory_id")
    expected_reducer = first_snapshot.get("reducer")

    prev_seq: int | None = None
    prev_observed_at_ms: int | None = None

    for idx, snap in enumerate(snapshots):
        # 1. Validate snapshot individually
        res = validate_snapshot(snap, verify_identity_hash=verify_identity_hashes)
        if not res.valid:
            errors.extend([f"Step {idx} (seq {snap.get('seq')}): {e}" for e in res.errors])

        # 2. Check trajectory ID consistency
        traj_id = snap.get("trajectory_id")
        if traj_id != expected_trajectory_id:
            errors.append(
                f"Step {idx}: Trajectory ID mismatch ('{traj_id}' != expected '{expected_trajectory_id}')."
            )

        # 3. Check reducer consistency
        reducer = snap.get("reducer")
        if reducer != expected_reducer:
            errors.append(
                f"Step {idx}: Reducer mismatch ({reducer} != expected {expected_reducer})."
            )

        # 4. Monotonic sequence number check
        seq = snap.get("seq")
        if seq is not None and isinstance(seq, int):
            if prev_seq is not None and seq <= prev_seq:
                errors.append(
                    f"Step {idx}: Non-increasing sequence number (seq {seq} <= previous {prev_seq})."
                )
            prev_seq = seq

        # 5. Monotonic observation time check
        obs_ms = snap.get("observed_at_ms")
        if obs_ms is not None and isinstance(obs_ms, int):
            if prev_observed_at_ms is not None and obs_ms < prev_observed_at_ms:
                errors.append(
                    f"Step {idx}: Regressing observation timestamp ({obs_ms}ms < previous {prev_observed_at_ms}ms)."
                )
            prev_observed_at_ms = obs_ms

        # 6. Freshness check at evaluation / injection time if provided
        fresh_for_ms = snap.get("fresh_for_ms")
        if (
            current_time_ms is not None
            and obs_ms is not None
            and fresh_for_ms is not None
            and idx == len(snapshots) - 1
        ):
            if current_time_ms > (obs_ms + fresh_for_ms):
                errors.append(
                    f"Active snapshot at step {idx} is stale: current_time_ms={current_time_ms} > "
                    f"expiry={obs_ms + fresh_for_ms} (observed_at_ms={obs_ms}, fresh_for_ms={fresh_for_ms})."
                )

        # 7. Delta linkage check (checked BEFORE adding current snap_id to seen_snapshot_ids)
        kind = snap.get("kind")
        snap_id = snap.get("snapshot_id")
        if kind == "delta":
            if idx == 0 or len(seen_snapshot_ids) == 0:
                errors.append(f"Step {idx}: Delta snapshot cannot be the initial snapshot of a trajectory.")
            base_id = snap.get("base_snapshot_id")
            if not base_id:
                errors.append(f"Step {idx}: Delta snapshot missing 'base_snapshot_id'.")
            elif base_id == snap_id:
                errors.append(f"Step {idx}: Delta snapshot cannot be self-linked (base_snapshot_id == snapshot_id).")
            elif base_id not in seen_snapshot_ids:
                errors.append(
                    f"Step {idx}: Delta base_snapshot_id '{base_id}' was not previously seen in this trajectory."
                )

        if snap_id:
            seen_snapshot_ids.add(snap_id)

    return TrajectoryValidationResult(valid=len(errors) == 0, errors=errors)
