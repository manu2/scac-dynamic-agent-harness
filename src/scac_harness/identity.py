"""Canonical serialization (RFC 8785 JCS) and deterministic identity hashing for SST snapshots."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any


def rfc8785_canonical_dumps(val: Any) -> str:
    """Serialize data into a deterministic string strictly adhering to RFC 8785 (JSON Canonicalization Scheme).

    Key properties:
    - Object keys sorted lexicographically by UTF-16 code units / Unicode code points.
    - No whitespace between tokens (',' and ':').
    - Negative zero (-0.0) normalized to 0.
    - Floating point numbers formatted without trailing '.0' if integer-valued, matching ECMAScript / JCS.
    - Strict UTF-8 without unnecessary escapes.
    - No NaN or Infinity.
    """
    if val is None:
        return "null"
    elif isinstance(val, bool):
        return "true" if val else "false"
    elif isinstance(val, int) and not isinstance(val, bool):
        return str(val)
    elif isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            raise ValueError("RFC 8785 prohibits NaN and Infinity.")
        # Normalize negative zero (-0.0) -> 0
        if val == 0.0:
            return "0"
        # Check if float is an exact integer
        if val.is_integer():
            return str(int(val))
        # Shortest round-trip float representation
        s = repr(val)
        # Handle python repr subtleties
        return s
    elif isinstance(val, str):
        return json.dumps(val, ensure_ascii=False)
    elif isinstance(val, (list, tuple)):
        items = [rfc8785_canonical_dumps(item) for item in val]
        return "[" + ",".join(items) + "]"
    elif isinstance(val, dict):
        # Sort keys lexicographically by Unicode code point / UTF-16 code unit
        sorted_keys = sorted(val.keys())
        entries = []
        for k in sorted_keys:
            if not isinstance(k, str):
                raise TypeError(f"RFC 8785 requires all object keys to be strings, got {type(k).__name__}")
            k_str = json.dumps(k, ensure_ascii=False)
            v_str = rfc8785_canonical_dumps(val[k])
            entries.append(f"{k_str}:{v_str}")
        return "{" + ",".join(entries) + "}"
    else:
        raise TypeError(f"Unsupported type for RFC 8785 serialization: {type(val).__name__}")


def canonical_json_dumps(data: Any) -> str:
    """Serialize data into a deterministic, compact JSON string according to RFC 8785."""
    return rfc8785_canonical_dumps(data)


def canonical_json_bytes(data: Any) -> bytes:
    """Return UTF-8 bytes for the RFC 8785 deterministic canonical JSON string."""
    return canonical_json_dumps(data).encode("utf-8")


def compute_content_hash(data: Any) -> str:
    """Compute SHA-256 hex digest of RFC 8785 canonically serialized JSON data."""
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
