"""Tests for deterministic reduction of raw telemetry events into SST snapshots."""

from __future__ import annotations

import copy
from scac_harness.events import RawTelemetryEvent
from scac_harness.reducer import DeterministicReducer, rehydrate_snapshot
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
            payload={
                "current_bytes": 134217728,
                "max_bytes": 268435456,
                "events_delta": {"high": 1, "max": 0, "oom": 0, "oom_kill": 0},
            },
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


def test_reducer_does_not_fabricate_unobserved_telemetry() -> None:
    """When only tool events are provided, hardware state is UNKNOWN and in unavailable_fields, not fabricated."""
    reducer = DeterministicReducer()
    tool_event = [
        RawTelemetryEvent(
            timestamp_ms=1000,
            source="tool_wrapper",
            topic="tool_span",
            payload={"tool_id": "query_db", "latency_ms": 50.0, "success": True},
        )
    ]
    snap = reducer.reduce(trajectory_id="traj-tool-only", seq=1, events=tool_event)

    # Must NOT fabricate 0 bytes memory, 1 GiB free disk, or ENABLED network
    assert snap["hardware"]["memory"]["state"] == "UNKNOWN"
    assert "current_bytes" not in snap["hardware"]["memory"]
    assert snap["hardware"]["cpu"]["state"] == "UNKNOWN"
    assert snap["hardware"]["ephemeral_disk"]["state"] == "UNKNOWN"
    assert "free_bytes" not in snap["hardware"]["ephemeral_disk"]
    assert "hardware.memory" in snap["unavailable_fields"]
    assert "hardware.cpu" in snap["unavailable_fields"]
    assert "hardware.ephemeral_disk" in snap["unavailable_fields"]


def test_tool_health_sliding_window_eviction() -> None:
    """10 successes followed by 10 failures must evict old successes, yielding 10 failures and OPEN circuit."""
    reducer = DeterministicReducer(circuit_consecutive_failure_limit=3, max_tool_window=10)

    # 1. 10 successes
    events_succ = [
        RawTelemetryEvent(
            timestamp_ms=1000 + i * 10,
            source="tool_wrapper",
            topic="tool_span",
            payload={"tool_id": "search_api", "latency_ms": 100.0, "success": True},
        )
        for i in range(10)
    ]
    s_succ = reducer.reduce("traj-sliding", 1, events_succ)
    assert s_succ["tools"]["search_api"]["window_n"] == 10
    assert s_succ["tools"]["search_api"]["successes"] == 10
    assert s_succ["tools"]["search_api"]["failures"] == 0
    assert s_succ["tools"]["search_api"]["circuit"] == "CLOSED"

    # 2. 10 failures
    events_fail = [
        RawTelemetryEvent(
            timestamp_ms=2000 + i * 10,
            source="tool_wrapper",
            topic="tool_span",
            payload={
                "tool_id": "search_api",
                "latency_ms": 500.0,
                "success": False,
                "error_class": "HTTP_503",
                "retry_after_ms": 5000,
            },
        )
        for i in range(10)
    ]
    s_fail = reducer.reduce("traj-sliding", 2, events_fail, prior_snapshot=s_succ)
    t_state = s_fail["tools"]["search_api"]
    assert t_state["window_n"] == 10
    assert t_state["successes"] == 0
    assert t_state["failures"] == 10
    assert t_state["consecutive_failures"] == 10
    assert t_state["circuit"] == "OPEN"
    assert t_state["state"] == "DEGRADED"


def test_reducer_memory_pressure_state_transitions() -> None:
    """Reducer correctly computes memory headroom ratio and updates state to PRESSURED and CRITICAL."""
    reducer = DeterministicReducer()

    # 1. OK state (75% headroom)
    ev_ok = [
        RawTelemetryEvent(
            timestamp_ms=1000,
            source="cgroup_v2",
            topic="memory",
            payload={
                "current_bytes": 67108864,
                "max_bytes": 268435456,
                "events_delta": {"high": 0, "max": 0, "oom": 0, "oom_kill": 0},
            },
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
            payload={
                "current_bytes": 241591910,
                "max_bytes": 268435456,
                "events_delta": {"high": 3, "max": 0, "oom": 0, "oom_kill": 0},
            },
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
            payload={
                "current_bytes": 268435456,
                "max_bytes": 268435456,
                "events_delta": {"high": 5, "max": 1, "oom": 1, "oom_kill": 0},
            },
        )
    ]
    s_critical = reducer.reduce(trajectory_id="traj-mem", seq=3, events=ev_critical, prior_snapshot=s_pressured)
    assert s_critical["hardware"]["memory"]["state"] == "CRITICAL"
    assert any("memory critical" in c for c in s_critical.get("recommended_constraints", []))


def test_reducer_field_level_derivation_provenance() -> None:
    """Every generated snapshot links each derived namespace to its contributing raw event hashes."""
    reducer = DeterministicReducer()
    ev1 = RawTelemetryEvent(timestamp_ms=1000, source="cgroup_v2", topic="cpu", payload={"nr_throttled_delta": 4})
    ev2 = RawTelemetryEvent(timestamp_ms=1010, source="cgroup_v2", topic="memory", payload={"current_bytes": 1024})

    snap = reducer.reduce("traj-audit", 1, [ev1, ev2])
    assert ev1.event_id in snap["derivation_provenance"]["hardware.cpu"]
    assert ev2.event_id in snap["derivation_provenance"]["hardware.memory"]


def test_delta_rehydration() -> None:
    """Rehydrating a delta snapshot with its base checkpoint produces a complete, coherent state."""
    reducer = DeterministicReducer()
    ev1 = [
        RawTelemetryEvent(
            timestamp_ms=1000,
            source="cgroup_v2",
            topic="memory",
            payload={"current_bytes": 67108864, "max_bytes": 268435456},
        )
    ]
    base = reducer.reduce("traj-rehydrate", 1, ev1, kind="full_checkpoint")

    ev2 = [
        RawTelemetryEvent(
            timestamp_ms=2000,
            source="tool_wrapper",
            topic="tool_span",
            payload={"tool_id": "fetch", "latency_ms": 80.0, "success": True},
        )
    ]
    delta = reducer.reduce("traj-rehydrate", 2, ev2, prior_snapshot=base, kind="delta")

    rehydrated = rehydrate_snapshot(delta, base)
    assert rehydrated["seq"] == 2
    assert rehydrated["hardware"]["memory"]["current_bytes"] == 67108864
    assert rehydrated["tools"]["fetch"]["successes"] == 1
