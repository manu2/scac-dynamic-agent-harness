"""Deterministic host-controlled Reducer producing validated SST snapshots."""

from __future__ import annotations

from typing import Any

from scac_harness.events import RawTelemetryEvent
from scac_harness.identity import compute_snapshot_id
from scac_harness.validator import validate_snapshot


class DeterministicReducer:
    """Pure, deterministic state reducer transforming raw telemetry events into validated SST snapshots."""

    def __init__(
        self,
        name: str = "scac-deterministic-reducer",
        version: str = "0.1.0",
        default_fresh_for_ms: int = 2000,
        ewma_alpha: float = 0.2,
        circuit_consecutive_failure_limit: int = 3,
    ) -> None:
        self.name = name
        self.version = version
        self.default_fresh_for_ms = default_fresh_for_ms
        self.ewma_alpha = ewma_alpha
        self.circuit_consecutive_failure_limit = circuit_consecutive_failure_limit

    def reduce(
        self,
        trajectory_id: str,
        seq: int,
        events: list[RawTelemetryEvent],
        prior_snapshot: dict[str, Any] | None = None,
        kind: str = "full_checkpoint",
        observed_at_ms: int | None = None,
        fresh_for_ms: int | None = None,
    ) -> dict[str, Any]:
        """Deterministically reduce raw events and prior state into a validated SST snapshot."""
        if not events and prior_snapshot is None:
            raise ValueError("Cannot reduce snapshot with empty events and no prior snapshot.")

        # Determine observation timestamp
        if observed_at_ms is None:
            if events:
                observed_at_ms = max(e.timestamp_ms for e in events)
            elif prior_snapshot:
                observed_at_ms = prior_snapshot["observed_at_ms"]
            else:
                observed_at_ms = 0

        validity_fresh_for_ms = fresh_for_ms if fresh_for_ms is not None else self.default_fresh_for_ms

        # Extract event hashes for immutable audit linkage
        raw_event_hashes = [e.event_id for e in events]
        if not raw_event_hashes and prior_snapshot:
            # Inherit last event hashes if no new events
            raw_event_hashes = prior_snapshot.get("raw_event_hashes", [])

        # Start with default state or copy from prior snapshot
        hardware = self._init_hardware(prior_snapshot)
        tools = self._init_tools(prior_snapshot)
        runtime = self._init_runtime(prior_snapshot)
        economics = self._init_economics(prior_snapshot)
        unavailable_fields: set[str] = set(prior_snapshot.get("unavailable_fields", [])) if prior_snapshot else set()

        # Fold events in strict chronological order
        sorted_events = sorted(events, key=lambda e: (e.timestamp_ms, e.event_id))
        for ev in sorted_events:
            self._apply_event(ev, hardware, tools, runtime, economics, unavailable_fields)

        # Recompute derived metrics, states, and constraints
        self._finalize_hardware(hardware)
        self._finalize_tools(tools)
        self._finalize_runtime(runtime)
        self._finalize_economics(economics)
        recommended_constraints = self._derive_constraints(hardware, tools, runtime, economics)

        # Base snapshot id for delta snapshots
        base_snapshot_id = None
        if kind == "delta":
            if prior_snapshot is None or "snapshot_id" not in prior_snapshot:
                raise ValueError("Delta snapshot requires a prior snapshot with a valid snapshot_id.")
            base_snapshot_id = prior_snapshot["snapshot_id"]

        snapshot: dict[str, Any] = {
            "schema": "scac-sst-v0.1",
            "trajectory_id": trajectory_id,
            "seq": seq,
            "kind": kind,
            "base_snapshot_id": base_snapshot_id,
            "observed_at_ms": observed_at_ms,
            "fresh_for_ms": validity_fresh_for_ms,
            "reducer": {
                "name": self.name,
                "version": self.version,
            },
            "raw_event_hashes": raw_event_hashes,
            "hardware": hardware,
            "tools": tools,
            "runtime": runtime,
            "economics": economics,
        }

        if recommended_constraints:
            snapshot["recommended_constraints"] = recommended_constraints

        if unavailable_fields:
            snapshot["unavailable_fields"] = sorted(list(unavailable_fields))

        # Compute deterministic snapshot_id
        snapshot["snapshot_id"] = compute_snapshot_id(snapshot)

        # Validate snapshot against schema and invariants
        val_res = validate_snapshot(snapshot)
        val_res.raise_for_errors()

        return snapshot

    def _init_hardware(self, prior: dict[str, Any] | None) -> dict[str, Any]:
        if prior and "hardware" in prior:
            import copy
            return copy.deepcopy(prior["hardware"])
        return {
            "memory": {
                "current_bytes": 0,
                "state": "OK",
                "events_delta": {"high": 0, "max": 0, "oom": 0, "oom_kill": 0},
            },
            "cpu": {
                "state": "OK",
            },
            "gpu": {
                "available": False,
            },
            "ephemeral_disk": {
                "free_bytes": 1073741824,
                "state": "OK",
            },
        }

    def _init_tools(self, prior: dict[str, Any] | None) -> dict[str, Any]:
        if prior and "tools" in prior:
            import copy
            return copy.deepcopy(prior["tools"])
        return {}

    def _init_runtime(self, prior: dict[str, Any] | None) -> dict[str, Any]:
        if prior and "runtime" in prior:
            import copy
            return copy.deepcopy(prior["runtime"])
        return {
            "network": "ENABLED",
        }

    def _init_economics(self, prior: dict[str, Any] | None) -> dict[str, Any]:
        if prior and "economics" in prior:
            import copy
            return copy.deepcopy(prior["economics"])
        return {}

    def _apply_event(
        self,
        event: RawTelemetryEvent,
        hardware: dict[str, Any],
        tools: dict[str, Any],
        runtime: dict[str, Any],
        economics: dict[str, Any],
        unavailable_fields: set[str],
    ) -> None:
        topic = event.topic
        p = event.payload

        if topic == "memory":
            mem = hardware["memory"]
            if "current_bytes" in p:
                mem["current_bytes"] = p["current_bytes"]
            if "peak_bytes" in p:
                mem["peak_bytes"] = p["peak_bytes"]
            if "max_bytes" in p:
                mem["max_bytes"] = p["max_bytes"]
            if "events_delta" in p:
                mem["events_delta"] = p["events_delta"]
            if "events_local_delta" in p:
                mem["events_local_delta"] = p["events_local_delta"]
            if "psi_some_avg10" in p:
                mem["psi_some_avg10"] = p["psi_some_avg10"]
            if "psi_full_avg10" in p:
                mem["psi_full_avg10"] = p["psi_full_avg10"]
            if "psi_some_total_usec_delta" in p:
                mem["psi_some_total_usec_delta"] = p["psi_some_total_usec_delta"]
            if "psi_full_total_usec_delta" in p:
                mem["psi_full_total_usec_delta"] = p["psi_full_total_usec_delta"]

        elif topic == "cpu":
            cpu = hardware["cpu"]
            if "quota_cores" in p:
                cpu["quota_cores"] = p["quota_cores"]
            if "period_usec" in p:
                cpu["period_usec"] = p["period_usec"]
            if "nr_throttled_delta" in p:
                cpu["nr_throttled_delta"] = p["nr_throttled_delta"]
            if "throttled_usec_delta" in p:
                cpu["throttled_usec_delta"] = p["throttled_usec_delta"]
            if "usage_usec_delta" in p:
                cpu["usage_usec_delta"] = p["usage_usec_delta"]
            if "psi_some_avg10" in p:
                cpu["psi_some_avg10"] = p["psi_some_avg10"]
            if "psi_full_avg10" in p:
                cpu["psi_full_avg10"] = p["psi_full_avg10"]

        elif topic == "gpu":
            gpu = hardware["gpu"]
            if "available" in p:
                gpu["available"] = p["available"]
            if "device_count" in p:
                gpu["device_count"] = p["device_count"]
            if "vram_used_bytes" in p:
                gpu["vram_used_bytes"] = p["vram_used_bytes"]
            if "vram_total_bytes" in p:
                gpu["vram_total_bytes"] = p["vram_total_bytes"]
            if "utilization_ratio" in p:
                gpu["utilization_ratio"] = p["utilization_ratio"]
            if not gpu.get("available", False):
                gpu["state"] = "UNAVAILABLE"
            else:
                gpu["state"] = "OK"

        elif topic == "ephemeral_disk":
            disk = hardware["ephemeral_disk"]
            if "free_bytes" in p:
                disk["free_bytes"] = p["free_bytes"]
            if "used_bytes" in p:
                disk["used_bytes"] = p["used_bytes"]
            if "total_bytes" in p:
                disk["total_bytes"] = p["total_bytes"]
            if "used_ratio" in p:
                disk["used_ratio"] = p["used_ratio"]

        elif topic == "tool_span":
            tool_id = p["tool_id"]
            if tool_id not in tools:
                tools[tool_id] = {
                    "window_n": 0,
                    "successes": 0,
                    "consecutive_failures": 0,
                    "latency_ewma_ms": float(p.get("latency_ms", 100.0)),
                    "circuit": "CLOSED",
                    "last_error": "NONE",
                }
            t_state = tools[tool_id]
            success = p.get("success", True)
            latency = float(p.get("latency_ms", 0.0))

            t_state["window_n"] = min(10, t_state["window_n"] + 1)
            if success:
                t_state["successes"] = min(t_state["window_n"], t_state["successes"] + 1)
                t_state["consecutive_failures"] = 0
                t_state["last_error"] = "NONE"
            else:
                t_state["consecutive_failures"] += 1
                t_state["last_error"] = p.get("error_class", "EXEC_ERROR")
                if "retry_after_ms" in p and p["retry_after_ms"] is not None:
                    t_state["retry_after_ms"] = p["retry_after_ms"]

            # Update EWMA latency
            prev_latency = t_state["latency_ewma_ms"]
            t_state["latency_ewma_ms"] = round(
                self.ewma_alpha * latency + (1.0 - self.ewma_alpha) * prev_latency, 2
            )

        elif topic == "runtime":
            for k in ["wall_remaining_ms", "step", "pids_current", "pids_max", "threads_current", "network", "filesystem"]:
                if k in p:
                    runtime[k] = p[k]
            if "last_exit" in p:
                runtime["last_exit"] = p["last_exit"]

        elif topic == "economics":
            for k in [
                "context_tokens_remaining",
                "trajectory_tokens",
                "input_tokens",
                "output_tokens",
                "cached_tokens",
                "estimated_cost_usd",
                "budget_remaining_usd",
                "rate_limit_remaining",
                "rate_limit_reset_ms",
            ]:
                if k in p:
                    economics[k] = p[k]

        elif topic == "unavailable_field":
            field_name = p.get("field")
            if field_name:
                unavailable_fields.add(field_name)

    def _finalize_hardware(self, hardware: dict[str, Any]) -> None:
        # Finalize Memory
        mem = hardware["memory"]
        cur = mem.get("current_bytes", 0)
        max_b = mem.get("max_bytes")
        if max_b is not None and max_b > 0:
            headroom = max(0.0, min(1.0, (max_b - cur) / max_b))
            mem["headroom_ratio"] = round(headroom, 4)
        else:
            mem["headroom_ratio"] = 1.0

        ev = mem.get("events_delta", {})
        oom_count = ev.get("oom", 0) + ev.get("oom_kill", 0)
        high_count = ev.get("high", 0)
        psi_some = mem.get("psi_some_avg10", 0.0)

        if oom_count > 0 or (max_b and cur >= max_b) or mem["headroom_ratio"] < 0.05:
            mem["state"] = "CRITICAL"
        elif high_count > 0 or mem["headroom_ratio"] < 0.20 or psi_some >= 2.0:
            mem["state"] = "PRESSURED"
        else:
            mem["state"] = "OK"

        # Finalize CPU
        cpu = hardware["cpu"]
        nr_throttled = cpu.get("nr_throttled_delta", 0)
        throttled_usec = cpu.get("throttled_usec_delta", 0)
        if throttled_usec > 500000:
            cpu["state"] = "CRITICAL"
        elif nr_throttled > 0 or throttled_usec > 0:
            cpu["state"] = "THROTTLED"
        else:
            cpu["state"] = "OK"

        # Finalize Disk
        disk = hardware["ephemeral_disk"]
        free_b = disk.get("free_bytes", 0)
        tot_b = disk.get("total_bytes")
        if tot_b and tot_b > 0:
            used_b = tot_b - free_b
            disk["used_bytes"] = used_b
            disk["used_ratio"] = round(max(0.0, min(1.0, used_b / tot_b)), 4)
        if free_b < 67108864:  # < 64 MiB
            disk["state"] = "CRITICAL"
        elif free_b < 268435456:  # < 256 MiB
            disk["state"] = "PRESSURED"
        else:
            disk["state"] = "OK"

    def _finalize_tools(self, tools: dict[str, Any]) -> None:
        for tool_id, t_state in tools.items():
            consec = t_state.get("consecutive_failures", 0)
            win = t_state.get("window_n", 0)
            succ = t_state.get("successes", 0)
            fail = win - succ

            if consec >= self.circuit_consecutive_failure_limit:
                t_state["circuit"] = "OPEN"
                t_state["state"] = "DEGRADED"
            elif win >= 3 and (fail / win) >= 0.4:
                t_state["circuit"] = "DEGRADED"
                t_state["state"] = "DEGRADED"
            else:
                t_state["circuit"] = "CLOSED"
                t_state["state"] = "OK"

    def _finalize_runtime(self, runtime: dict[str, Any]) -> None:
        wall = runtime.get("wall_remaining_ms")
        if wall is not None:
            if wall < 5000:
                runtime["state"] = "TERMINATING"
            else:
                runtime["state"] = "RUNNING"

    def _finalize_economics(self, economics: dict[str, Any]) -> None:
        rem_quota = economics.get("rate_limit_remaining")
        budget = economics.get("budget_remaining_usd")
        if (rem_quota is not None and rem_quota == 0) or (budget is not None and budget <= 0.0):
            economics["state"] = "EXHAUSTED"
        elif (rem_quota is not None and rem_quota <= 5) or (budget is not None and budget <= 0.05):
            economics["state"] = "WARN"
        else:
            economics["state"] = "OK"

    def _derive_constraints(
        self,
        hardware: dict[str, Any],
        tools: dict[str, Any],
        runtime: dict[str, Any],
        economics: dict[str, Any],
    ) -> list[str]:
        constraints: list[str] = []

        # Memory pressure rules
        mem = hardware.get("memory", {})
        mem_state = mem.get("state")
        if mem_state == "CRITICAL":
            constraints.append("memory critical: release intermediate buffers immediately")
        elif mem_state == "PRESSURED":
            constraints.append("avoid new allocations above 16 MiB")

        # CPU throttling rules
        cpu = hardware.get("cpu", {})
        if cpu.get("state") in ("THROTTLED", "CRITICAL"):
            constraints.append("cpu throttled: reduce concurrency or worker count")

        # Tool circuit rules
        for tool_id in sorted(tools.keys()):
            t_state = tools[tool_id]
            circuit = t_state.get("circuit")
            if circuit == "OPEN":
                retry_ms = t_state.get("retry_after_ms")
                if retry_ms:
                    constraints.append(f"do not call {tool_id} before circuit closes (wait {retry_ms}ms)")
                else:
                    constraints.append(f"do not call {tool_id} before circuit closes")

        # Quota rules
        rem_quota = economics.get("rate_limit_remaining")
        if rem_quota is not None and rem_quota <= 5:
            constraints.append(f"rate limit low: {rem_quota} calls remaining")

        # Wall time rules
        wall = runtime.get("wall_remaining_ms")
        if wall is not None and wall < 10000:
            constraints.append("wall time budget low: prioritize immediate checkpoint or finalization")

        return constraints[:16]
