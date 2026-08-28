"""Tests for deterministic reduction of raw telemetry events into SST snapshots."""

from __future__ import annotations

import copy
from scac_harness.events import RawTelemetryEvent
from scac_harness.reducer import DeterministicReducer
from scac_harness.validator import validate_snapshot


def test_deterministic_reduction_identical_output() -> None:
    """The reducer must produce byte-identical output given identical ordered input events."""
    reducer1 = DeterministicReducer()
    reducer2 = DeterministicReducer()

    events = [
        RawTelemetryEvent(
            timestamp_ms=1000,
            source="cgroup_v2",
            topic="memory",
            payload={"current_bytes": 134217728, "max_bytes": 268435456, "events_delta": {"high": 1, "max": 0, "oom": 0, "oom_kill": 0}},
        ),
        RawTelemetryEvent(
            timestamp_ms=1050,
            source="tool_wrapper",
            topic="tool_span",
            payload={"tool_id": "api_fetch", "latency_ms": 120.0, "success": True},
        ),
    ]

    snap1 = reducer1.reduce(trajectory_id="traj-test", seq=1, events=events)
    snap2 = reducer2.reduce(trajectory_id="traj-test", seq=1, events=copy.deepcopy(events))

    assert snap1 == snap2
    assert snap1["snapshot_id"] == snap2["snapshot_id"]
    assert validate_snapshot(snap1).valid is True


def test_reducer_memory_pressure_state_transitions() -> None:
    """Reducer correctly computes memory headroom ratio and updates state to PRESSURED and CRITICAL."""
    reducer = DeterministicReducer()

    # 1. OK state (75% headroom)
    ev_ok = [
        RawTelemetryEvent(
            timestamp_ms=1000,
            source="cgroup_v2",
            topic="memory",
            payload={"current_bytes": 67108864, "max_bytes": 268435456, "events_delta": {"high": 0, "max": 0, "oom": 0, "oom_kill": 0}},
        )
    ]
    s_ok = reducer.reduce(trajectory_id="traj-mem", seq=1, events=ev_ok)
    assert s_ok["hardware"]["memory"]["state"] == "OK"
    assert s_ok["hardware"]["memory"]["headroom_ratio"] == 0.75

    # 2. PRESSURED state (10% headroom, high events)
    ev_pressured = [
        RawTelemetryEvent(
            timestamp_ms=2000,
            source="cgroup_v2",
            topic="memory",
            payload={"current_bytes": 241591910, "max_bytes": 268435456, "events_delta": {"high": 3, "max": 0, "oom": 0, "oom_kill": 0}},
        )
    ]
    s_pressured = reducer.reduce(trajectory_id="traj-mem", seq=2, events=ev_pressured, prior_snapshot=s_ok)
    assert s_pressured["hardware"]["memory"]["state"] == "PRESSURED"
    assert any("avoid new allocations" in c for c in s_pressured.get("recommended_constraints", []))

    # 3. CRITICAL state (OOM event)
    ev_critical = [
        RawTelemetryEvent(
            timestamp_ms=3000,
            source="cgroup_v2",
            topic="memory",
            payload={"current_bytes": 268435456, "max_bytes": 268435456, "events_delta": {"high": 5, "max": 1, "oom": 1, "oom_kill": 0}},
        )
    ]
    s_critical = reducer.reduce(trajectory_id="traj-mem", seq=3, events=ev_critical, prior_snapshot=s_pressured)
    assert s_critical["hardware"]["memory"]["state"] == "CRITICAL"
    assert any("memory critical" in c for c in s_critical.get("recommended_constraints", []))


def test_reducer_tool_circuit_breaker() -> None:
    """Tool failures trip circuit breaker from CLOSED to OPEN upon reaching consecutive failure limit."""
    reducer = DeterministicReducer(circuit_consecutive_failure_limit=3)

    # Initial success
    ev1 = [
        RawTelemetryEvent(
            timestamp_ms=1000,
            source="tool_wrapper",
            topic="tool_span",
            payload={"tool_id": "remote_service", "latency_ms": 100.0, "success": True},
        )
    ]
    s1 = reducer.reduce("traj-circuit", 1, ev1)
    assert s1["tools"]["remote_service"]["circuit"] == "CLOSED"

    # 3 consecutive failures
    ev2 = [
        RawTelemetryEvent(
            timestamp_ms=2000,
            source="tool_wrapper",
            topic="tool_span",
            payload={"tool_id": "remote_service", "latency_ms": 500.0, "success": False, "error_class": "HTTP_503", "retry_after_ms": 3000},
        ),
        RawTelemetryEvent(
            timestamp_ms=2100,
            source="tool_wrapper",
            topic="tool_span",
            payload={"tool_id": "remote_service", "latency_ms": 500.0, "success": False, "error_class": "HTTP_503", "retry_after_ms": 3000},
        ),
        RawTelemetryEvent(
            timestamp_ms=2200,
            source="tool_wrapper",
            topic="tool_span",
            payload={"tool_id": "remote_service", "latency_ms": 500.0, "success": False, "error_class": "HTTP_503", "retry_after_ms": 3000},
        ),
    ]
    s2 = reducer.reduce("traj-circuit", 2, ev2, prior_snapshot=s1)
    assert s2["tools"]["remote_service"]["circuit"] == "OPEN"
    assert s2["tools"]["remote_service"]["consecutive_failures"] == 3
    assert s2["tools"]["remote_service"]["last_error"] == "HTTP_503"
    assert any("do not call remote_service" in c for c in s2.get("recommended_constraints", []))


def test_reducer_audit_linkage_to_raw_event_hashes() -> None:
    """Every generated snapshot links to the exact SHA-256 hashes of its contributing raw events."""
    reducer = DeterministicReducer()
    ev1 = RawTelemetryEvent(timestamp_ms=1000, source="cgroup_v2", topic="cpu", payload={"nr_throttled_delta": 4})
    ev2 = RawTelemetryEvent(timestamp_ms=1010, source="cgroup_v2", topic="memory", payload={"current_bytes": 1024})

    snap = reducer.reduce("traj-audit", 1, [ev1, ev2])
    assert set(snap["raw_event_hashes"]) == {ev1.event_id, ev2.event_id}
