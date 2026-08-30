"""Tests for strict RFC 8785 (JCS) canonical serialization and SHA-256 identity hashing."""

from __future__ import annotations

import json
from scac_harness.identity import (
    canonical_json_bytes,
    canonical_json_dumps,
    compute_content_hash,
    compute_snapshot_id,
    rfc8785_canonical_dumps,
    verify_snapshot_id,
)


def test_rfc8785_ecmascript_number_representations() -> None:
    """RFC 8785 requires strict ECMAScript 7.1.12.1 number serialization."""
    # Negative zero must serialize to "0"
    assert canonical_json_dumps(-0.0) == "0"
    assert canonical_json_dumps(0.0) == "0"
    assert canonical_json_dumps({"val": -0.0}) == '{"val":0}'

    # Integer-valued floats must not have trailing ".0"
    assert canonical_json_dumps(10.0) == "10"
    assert canonical_json_dumps(10.5) == "10.5"

    # Exponential representations
    assert canonical_json_dumps(1e30) == "1e+30"
    assert canonical_json_dumps(1e-7) == "1e-7"


def test_rfc8785_utf16_key_sorting() -> None:
    """RFC 8785 requires property keys to be sorted by UTF-16 code units."""
    # Unicode code point order vs UTF-16 code unit order
    obj = {"\uffff": 1, "\U00010000": 2, "a": 3}
    canonical = canonical_json_dumps(obj)
    assert canonical.startswith('{"a":3')


def test_canonical_json_ordering_and_compactness() -> None:
    """Canonical dumps must be strictly key-sorted and whitespace-compacted."""
    obj1 = {"z": 1, "a": 2, "m": {"b": 3, "a": 4}}
    obj2 = {"a": 2, "m": {"a": 4, "b": 3}, "z": 1}

    dump1 = canonical_json_dumps(obj1)
    dump2 = canonical_json_dumps(obj2)

    assert dump1 == dump2
    assert dump1 == '{"a":2,"m":{"a":4,"b":3},"z":1}'
    assert canonical_json_bytes(obj1) == canonical_json_bytes(obj2)


def test_snapshot_id_computation_and_tamper_detection() -> None:
    """Snapshot ID must be deterministic and detect any field tampering."""
    snapshot = {
        "schema": "scac-sst-v0.1",
        "trajectory_id": "traj-001",
        "seq": 1,
        "kind": "full_checkpoint",
        "observed_at_ms": 1000,
        "fresh_for_ms": 2000,
        "hardware": {"memory": {"current_bytes": 1024}},
    }
    snap_id = compute_snapshot_id(snapshot)
    snapshot["snapshot_id"] = snap_id

    assert verify_snapshot_id(snapshot) is True

    # Tampering with any byte must invalidate the hash
    snapshot["seq"] = 2
    assert verify_snapshot_id(snapshot) is False

    snapshot["seq"] = 1
    snapshot["hardware"]["memory"]["current_bytes"] = 1025
    assert verify_snapshot_id(snapshot) is False


def test_snapshot_id_ignores_existing_snapshot_id_field() -> None:
    """compute_snapshot_id ignores the snapshot_id field itself so computation is idempotent."""
    snapshot = {
        "schema": "scac-sst-v0.1",
        "trajectory_id": "traj-001",
        "seq": 1,
        "hardware": {},
    }
    id1 = compute_snapshot_id(snapshot)
    snapshot["snapshot_id"] = "any_existing_value"
    id2 = compute_snapshot_id(snapshot)
    assert id1 == id2
