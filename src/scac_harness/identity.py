"""Canonical serialization strictly adhering to RFC 8785 (JCS) and deterministic identity hashing."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping
import jcs


def _to_json_encodable(val: Any) -> Any:
    """Normalize mappings and sequences into standard dicts and lists for RFC 8785 canonicalization."""
    if isinstance(val, (dict, Mapping)):
        return {str(k): _to_json_encodable(v) for k, v in val.items()}
    elif isinstance(val, (list, tuple)):
        return [_to_json_encodable(v) for v in val]
    return val


def canonical_json_bytes(data: Any) -> bytes:
    """Serialize data into UTF-8 bytes strictly adhering to RFC 8785 (JSON Canonicalization Scheme)."""
    return jcs.canonicalize(_to_json_encodable(data))


def canonical_json_dumps(data: Any) -> str:
    """Serialize data into a deterministic string strictly adhering to RFC 8785 (JCS)."""
    return canonical_json_bytes(data).decode("utf-8")


def rfc8785_canonical_dumps(data: Any) -> str:
    """Alias for canonical_json_dumps conforming to RFC 8785."""
    return canonical_json_dumps(data)


def compute_content_hash(data: Any) -> str:
    """Compute SHA-256 hex digest of RFC 8785 canonically serialized data."""
    return hashlib.sha256(canonical_json_bytes(data)).hexdigest()


def compute_snapshot_id(snapshot: dict[str, Any]) -> str:
    """Compute the deterministic SHA-256 snapshot_id according to RFC 8785.

    The hash is computed over all fields in the snapshot *excluding* the 'snapshot_id' field itself.
    """
    body = {k: v for k, v in snapshot.items() if k != "snapshot_id"}
    return hashlib.sha256(canonical_json_bytes(body)).hexdigest()


def verify_snapshot_id(snapshot: dict[str, Any]) -> bool:
    """Verify that snapshot['snapshot_id'] matches the RFC 8785 hash of its canonical body."""
    declared_id = snapshot.get("snapshot_id")
    if not declared_id or not isinstance(declared_id, str):
        return False
    expected_id = compute_snapshot_id(snapshot)
    return declared_id == expected_id
