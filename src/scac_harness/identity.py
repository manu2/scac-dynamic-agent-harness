"""Canonical serialization and deterministic identity hashing for SST snapshots."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json_dumps(data: Any) -> str:
    """Serialize data into a deterministic, compact JSON string according to RFC 8785 principles."""
    return json.dumps(
        data,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def canonical_json_bytes(data: Any) -> bytes:
    """Return UTF-8 bytes for the deterministic canonical JSON string."""
    return canonical_json_dumps(data).encode("utf-8")


def compute_content_hash(data: Any) -> str:
    """Compute SHA-256 hex digest of canonically serialized JSON data."""
    return hashlib.sha256(canonical_json_bytes(data)).hexdigest()


def compute_snapshot_id(snapshot: dict[str, Any]) -> str:
    """Compute the deterministic SHA-256 snapshot_id.

    The hash is computed over all fields in the snapshot *excluding* the 'snapshot_id' field itself.
    """
    body = {k: v for k, v in snapshot.items() if k != "snapshot_id"}
    return hashlib.sha256(canonical_json_bytes(body)).hexdigest()


def verify_snapshot_id(snapshot: dict[str, Any]) -> bool:
    """Verify that snapshot['snapshot_id'] matches the hash of its canonical body."""
    declared_id = snapshot.get("snapshot_id")
    if not declared_id or not isinstance(declared_id, str):
        return False
    expected_id = compute_snapshot_id(snapshot)
    return declared_id == expected_id
