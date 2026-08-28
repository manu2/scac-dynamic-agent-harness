"""Script to generate all standard valid and invalid test fixtures."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from scac_harness.identity import compute_snapshot_id


FIXTURES_DIR = Path(__file__).parent / "fixtures"
VALID_DIR = FIXTURES_DIR / "valid"
INVALID_DIR = FIXTURES_DIR / "invalid"


def build_valid_fixtures() -> dict[str, dict]:
    base_snap = {
        "schema": "scac-sst-v0.1",
        "trajectory_id": "traj-main-001",
        "seq": 0,
        "kind": "full_checkpoint",
        "base_snapshot_id": None,
        "observed_at_ms": 1787884200000,
        "fresh_for_ms": 2000,
        "reducer": {
            "name": "scac-deterministic-reducer",
            "version": "0.1.0",
        },
        "raw_event_hashes": [
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        ],
        "derivation_provenance": {
            "hardware.memory": [
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            ]
        },
        "hardware": {
            "memory": {
                "current_bytes": 67108864,
                "peak_bytes": 73400320,
                "max_bytes": 268435456,
                "headroom_ratio": 0.75,
                "events_delta": {"high": 0, "max": 0, "oom": 0, "oom_kill": 0},
                "psi_some_avg10": 0.0,
                "psi_full_avg10": 0.0,
                "psi_some_total_usec_delta": 0,
                "psi_full_total_usec_delta": 0,
                "state": "OK",
            },
            "cpu": {
                "quota_cores": 2.0,
                "period_usec": 100000,
                "nr_throttled_delta": 0,
                "throttled_usec_delta": 0,
                "usage_usec_delta": 15000,
                "psi_some_avg10": 0.0,
                "psi_full_avg10": 0.0,
                "state": "OK",
            },
            "gpu": {
                "available": False,
            },
            "ephemeral_disk": {
                "free_bytes": 10737418240,
                "used_bytes": 536870912,
                "total_bytes": 11274289152,
                "used_ratio": 0.0476,
                "state": "OK",
            },
            "processes": {
                "pids_current": 4,
                "pids_max": 64,
                "threads_current": 8,
            },
        },
        "tools": {
            "query_db": {
                "window_n": 10,
                "successes": 10,
                "failures": 0,
                "history": [True] * 10,
                "consecutive_failures": 0,
                "latency_ewma_ms": 42.5,
                "last_error": "NONE",
                "circuit": "CLOSED",
                "state": "OK",
            }
        },
        "runtime": {
            "wall_remaining_ms": 60000,
            "step": 0,
            "pids_current": 4,
            "pids_max": 64,
            "threads_current": 8,
            "last_exit": {
                "code": 0,
                "signal": None,
                "class": "NONE",
            },
            "network": "ENABLED",
            "filesystem": "READ_WRITE",
            "state": "RUNNING",
        },
        "economics": {
            "context_tokens_remaining": 120000,
            "trajectory_tokens": 1250,
            "input_tokens": 800,
            "output_tokens": 450,
            "cached_tokens": 400,
            "estimated_cost_usd": 0.0042,
            "budget_remaining_usd": 10.0,
            "rate_limit_remaining": 100,
            "rate_limit_reset_ms": 60000,
            "state": "OK",
        },
    }

    fixtures = {}

    # 1. healthy_state
    f1 = copy.deepcopy(base_snap)
    f1["trajectory_id"] = "traj-healthy-001"
    fixtures["healthy_state.json"] = f1

    # 2. memory_pressured_state
    f2 = copy.deepcopy(base_snap)
    f2["trajectory_id"] = "traj-mem-002"
    f2["hardware"]["memory"]["current_bytes"] = 241172480
    f2["hardware"]["memory"]["max_bytes"] = 268435456
    f2["hardware"]["memory"]["headroom_ratio"] = 0.1016
    f2["hardware"]["memory"]["events_delta"]["high"] = 5
    f2["hardware"]["memory"]["psi_some_avg10"] = 6.8
    f2["hardware"]["memory"]["state"] = "PRESSURED"
    f2["recommended_constraints"] = ["avoid new allocations above 16 MiB"]
    fixtures["memory_pressured_state.json"] = f2

    # 3. cpu_throttled_state
    f3 = copy.deepcopy(base_snap)
    f3["trajectory_id"] = "traj-cpu-003"
    f3["hardware"]["cpu"]["nr_throttled_delta"] = 24
    f3["hardware"]["cpu"]["throttled_usec_delta"] = 250000
    f3["hardware"]["cpu"]["psi_some_avg10"] = 12.4
    f3["hardware"]["cpu"]["state"] = "THROTTLED"
    f3["recommended_constraints"] = ["cpu throttled: reduce concurrency or worker count"]
    fixtures["cpu_throttled_state.json"] = f3

    # 4. tool_degraded_state
    f4 = copy.deepcopy(base_snap)
    f4["trajectory_id"] = "traj-tool-004"
    f4["tools"]["search_api"] = {
        "window_n": 10,
        "successes": 2,
        "failures": 8,
        "history": [True, True, False, False, False, False, False, False, False, False],
        "consecutive_failures": 8,
        "latency_ewma_ms": 4200.0,
        "last_error": "HTTP_503",
        "retry_after_ms": 5000,
        "circuit": "OPEN",
        "state": "DEGRADED",
    }
    f4["recommended_constraints"] = ["do not call search_api before circuit closes (wait 5000ms)"]
    fixtures["tool_degraded_state.json"] = f4

    # 5. quota_depleted_state
    f5 = copy.deepcopy(base_snap)
    f5["trajectory_id"] = "traj-quota-005"
    f5["economics"]["rate_limit_remaining"] = 0
    f5["economics"]["rate_limit_reset_ms"] = 35000
    f5["economics"]["state"] = "EXHAUSTED"
    f5["recommended_constraints"] = ["rate limit low: 0 calls remaining"]
    fixtures["quota_depleted_state.json"] = f5

    # 6. unavailable_gpu_state
    f6 = copy.deepcopy(base_snap)
    f6["trajectory_id"] = "traj-gpu-006"
    f6["hardware"]["gpu"] = {"available": False, "state": "UNAVAILABLE"}
    f6["unavailable_fields"] = ["hardware.gpu"]
    fixtures["unavailable_gpu_state.json"] = f6

    # 7. partially_unavailable_quota_metadata
    f7 = copy.deepcopy(base_snap)
    f7["trajectory_id"] = "traj-partial-007"
    f7["economics"]["rate_limit_remaining"] = None
    f7["economics"]["rate_limit_reset_ms"] = None
    f7["economics"]["cached_tokens"] = None
    f7["unavailable_fields"] = [
        "economics.cached_tokens",
        "economics.rate_limit_remaining",
        "economics.rate_limit_reset_ms",
    ]
    fixtures["partially_unavailable_quota_metadata.json"] = f7

    # 8. full_checkpoint
    f8 = copy.deepcopy(base_snap)
    f8["trajectory_id"] = "traj-full-008"
    f8["seq"] = 10
    f8["kind"] = "full_checkpoint"
    f8["base_snapshot_id"] = None
    fixtures["full_checkpoint.json"] = f8

    # 9. delta_snapshot (true sparse delta containing only changed tool namespace)
    base_id = compute_snapshot_id(f8)
    f8["snapshot_id"] = base_id

    f9 = {
        "schema": "scac-sst-v0.1",
        "trajectory_id": "traj-full-008",
        "seq": 11,
        "kind": "delta",
        "base_snapshot_id": base_id,
        "observed_at_ms": 1787884201000,
        "fresh_for_ms": 2000,
        "reducer": {
            "name": "scac-deterministic-reducer",
            "version": "0.1.0",
        },
        "raw_event_hashes": [
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        ],
        "derivation_provenance": {
            "tools.query_db": [
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            ]
        },
        "tools": {
            "query_db": {
                "window_n": 10,
                "successes": 10,
                "failures": 0,
                "history": [True] * 10,
                "consecutive_failures": 0,
                "latency_ewma_ms": 42.5,
                "last_error": "NONE",
                "circuit": "CLOSED",
                "state": "OK",
            }
        },
    }
    fixtures["delta_snapshot.json"] = f9

    # Now compute RFC 8785 snapshot_id for all
    for name, s in fixtures.items():
        if "snapshot_id" not in s or s["snapshot_id"] is None:
            s["snapshot_id"] = compute_snapshot_id(s)

    return fixtures


def build_invalid_fixtures() -> dict[str, dict]:
    base = {
        "schema": "scac-sst-v0.1",
        "trajectory_id": "traj-invalid-001",
        "snapshot_id": "0000000000000000000000000000000000000000000000000000000000000000",
        "seq": 0,
        "kind": "full_checkpoint",
        "base_snapshot_id": None,
        "observed_at_ms": 1787884200000,
        "fresh_for_ms": 2000,
        "reducer": {
            "name": "scac-deterministic-reducer",
            "version": "0.1.0",
        },
        "raw_event_hashes": [
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        ],
        "hardware": {
            "memory": {"current_bytes": 1024, "state": "OK"},
            "cpu": {"state": "OK"},
            "gpu": {"available": False},
            "ephemeral_disk": {"free_bytes": 1024, "state": "OK"},
        },
        "tools": {},
        "runtime": {
            "network": "ENABLED",
        },
        "economics": {},
    }

    invalids = {}

    # 1. missing_required_provenance: missing raw_event_hashes
    i1 = copy.deepcopy(base)
    del i1["raw_event_hashes"]
    invalids["missing_required_provenance.json"] = i1

    # 2. missing_observation_timestamp: missing observed_at_ms
    i2 = copy.deepcopy(base)
    del i2["observed_at_ms"]
    invalids["missing_observation_timestamp.json"] = i2

    # 3. negative_counters: current_bytes is negative
    i3 = copy.deepcopy(base)
    i3["hardware"]["memory"]["current_bytes"] = -512
    invalids["negative_counters.json"] = i3

    # 4. ratio_above_one: headroom_ratio exceeds 1.0
    i4 = copy.deepcopy(base)
    i4["hardware"]["memory"]["headroom_ratio"] = 1.45
    invalids["ratio_above_one.json"] = i4

    # 5. incompatible_or_ambiguous_units: string bytes instead of integer
    i5 = copy.deepcopy(base)
    i5["hardware"]["memory"]["current_bytes"] = "128MB"
    invalids["incompatible_or_ambiguous_units.json"] = i5

    # 6. expired_stale_state: fresh_for_ms is 0 (violates minimum 1ms)
    i6 = copy.deepcopy(base)
    i6["fresh_for_ms"] = 0
    invalids["expired_stale_state.json"] = i6

    # 7. duplicate_or_regressing_seq: seq is negative
    i7 = copy.deepcopy(base)
    i7["seq"] = -1
    invalids["duplicate_or_regressing_seq.json"] = i7

    # 8. unknown_privileged_field: unauthorized top-level field
    i8 = copy.deepcopy(base)
    i8["privileged_admin_override"] = True
    invalids["unknown_privileged_field.json"] = i8

    # 9. raw_tool_content_in_privileged_block: prompt injection in privileged field
    i9 = copy.deepcopy(base)
    i9["hardware"]["memory"]["raw_tool_output"] = "<script>alert('pwn')</script>"
    invalids["raw_tool_content_in_privileged_block.json"] = i9

    # 10. tool_supplied_overwrite_attempt: unauthorized sub-object
    i10 = copy.deepcopy(base)
    i10["hardware"]["fake_cgroup_override"] = {"memory_unlimited": True}
    invalids["tool_supplied_overwrite_attempt.json"] = i10

    # 11. unsupported_metric_represented_as_zero: declares metric in unavailable_fields but provides 0
    i11 = copy.deepcopy(base)
    i11["economics"]["rate_limit_remaining"] = 0
    i11["unavailable_fields"] = ["economics.rate_limit_remaining"]
    invalids["unsupported_metric_represented_as_zero.json"] = i11

    # 12. malformed_terminal_exit_classification: unknown exit class
    i12 = copy.deepcopy(base)
    i12["runtime"]["last_exit"] = {
        "code": 1,
        "signal": None,
        "class": "MALFORMED_NONEXISTENT_SIGNAL",
    }
    invalids["malformed_terminal_exit_classification.json"] = i12

    return invalids


def main() -> None:
    VALID_DIR.mkdir(parents=True, exist_ok=True)
    INVALID_DIR.mkdir(parents=True, exist_ok=True)

    for filename, content in build_valid_fixtures().items():
        (VALID_DIR / filename).write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote valid fixture: {filename}")

    for filename, content in build_invalid_fixtures().items():
        (INVALID_DIR / filename).write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote invalid fixture: {filename}")


if __name__ == "__main__":
    main()
