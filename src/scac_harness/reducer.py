"""Deterministic host-controlled Reducer producing validated SST snapshots with true sliding windows and provenance."""

from __future__ import annotations

import copy
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
        max_tool_window: int = 10,
    ) -> None:
        self.name = name
        self.version = version
        self.default_fresh_for_ms = default_fresh_for_ms
        self.ewma_alpha = ewma_alpha
        self.circuit_consecutive_failure_limit = circuit_consecutive_failure_limit
        self.max_tool_window = max_tool_window

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
            raw_event_hashes = prior_snapshot.get("raw_event_hashes", [])

        # Start with base state or copy from prior snapshot
        hardware = self._init_hardware(prior_snapshot)
        tools = self._init_tools(prior_snapshot)
        runtime = self._init_runtime(prior_snapshot)
        economics = self._init_economics(prior_snapshot)
        unavailable_fields: set[str] = set(prior_snapshot.get("unavailable_fields", [])) if prior_snapshot else set()

        # Track field-level derivation provenance
        derivation_prov: dict[str, list[str]] = (
            copy.deepcopy(prior_snapshot.get("derivation_provenance", {})) if prior_snapshot else {}
        )

        # Track which subsystems received events in this batch
        observed_topics: set[str] = set()

        # Fold events in strict chronological order, ties broken by event_id
        sorted_events = sorted(events, key=lambda e: (e.timestamp_ms, e.event_id))
        for ev in sorted_events:
            observed_topics.add(ev.topic)
            self._apply_event(
                ev, hardware, tools, runtime, economics, unavailable_fields, derivation_prov
            )

        # Finalize states without fabricating unobserved measurements
        self._finalize_hardware(hardware, unavailable_fields, has_prior=(prior_snapshot is not None))
        self._finalize_tools(tools)
        self._finalize_runtime(runtime, unavailable_fields)
        self._finalize_economics(economics, unavailable_fields)
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
            "derivation_provenance": derivation_prov,
            "hardware": hardware,
            "tools": tools,
            "runtime": runtime,
            "economics": economics,
        }

        if recommended_constraints:
            snapshot["recommended_constraints"] = recommended_constraints

        if unavailable_fields:
            snapshot["unavailable_fields"] = sorted(list(unavailable_fields))

        # Compute deterministic snapshot_id using RFC 8785 canonical hashing
        snapshot["snapshot_id"] = compute_snapshot_id(snapshot)

        # Validate snapshot against schema and invariants
        val_res = validate_snapshot(snapshot)
        val_res.raise_for_errors()

        return snapshot

    def _init_hardware(self, prior: dict[str, Any] | None) -> dict[str, Any]:
        if prior and "hardware" in prior:
            return copy.deepcopy(prior["hardware"])
        # Unobserved hardware baseline: state is UNKNOWN, no fabricated values
        return {
            "memory": {
                "state": "UNKNOWN",
            },
            "cpu": {
                "state": "UNKNOWN",
            },
            "gpu": {
                "available": False,
                "state": "UNAVAILABLE",
            },
            "ephemeral_disk": {
                "state": "UNKNOWN",
            },
        }

    def _init_tools(self, prior: dict[str, Any] | None) -> dict[str, Any]:
        if prior and "tools" in prior:
            return copy.deepcopy(prior["tools"])
        return {}

    def _init_runtime(self, prior: dict[str, Any] | None) -> dict[str, Any]:
        if prior and "runtime" in prior:
            return copy.deepcopy(prior["runtime"])
        return {
            "network": "UNKNOWN",
        }

    def _init_economics(self, prior: dict[str, Any] | None) -> dict[str, Any]:
        if prior and "economics" in prior:
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
        derivation_prov: dict[str, list[str]],
    ) -> None:
        topic = event.topic
        p = event.payload
        ev_id = event.event_id

        if topic == "memory":
            mem = hardware["memory"]
            derivation_prov.setdefault("hardware.memory", []).append(ev_id)
            unavailable_fields.discard("hardware.memory")
            for k in [
                "current_bytes",
                "peak_bytes",
                "max_bytes",
                "events_delta",
                "events_local_delta",
                "psi_some_avg10",
                "psi_full_avg10",
                "psi_some_total_usec_delta",
                "psi_full_total_usec_delta",
            ]:
                if k in p:
                    mem[k] = p[k]

        elif topic == "cpu":
            cpu = hardware["cpu"]
            derivation_prov.setdefault("hardware.cpu", []).append(ev_id)
            unavailable_fields.discard("hardware.cpu")
            for k in [
                "quota_cores",
                "period_usec",
                "nr_throttled_delta",
                "throttled_usec_delta",
                "usage_usec_delta",
                "psi_some_avg10",
                "psi_full_avg10",
            ]:
                if k in p:
                    cpu[k] = p[k]

        elif topic == "gpu":
            gpu = hardware["gpu"]
            derivation_prov.setdefault("hardware.gpu", []).append(ev_id)
            if "available" in p:
                gpu["available"] = p["available"]
            for k in ["device_count", "vram_used_bytes", "vram_total_bytes", "utilization_ratio"]:
                if k in p:
                    gpu[k] = p[k]
            if not gpu.get("available", False):
                gpu["state"] = "UNAVAILABLE"
                unavailable_fields.add("hardware.gpu")
            else:
                gpu["state"] = "OK"
                unavailable_fields.discard("hardware.gpu")

        elif topic == "ephemeral_disk":
            disk = hardware["ephemeral_disk"]
            derivation_prov.setdefault("hardware.ephemeral_disk", []).append(ev_id)
            unavailable_fields.discard("hardware.ephemeral_disk")
            for k in ["free_bytes", "used_bytes", "total_bytes", "used_ratio"]:
                if k in p:
                    disk[k] = p[k]

        elif topic == "tool_span":
            tool_id = p["tool_id"]
            prov_key = f"tools.{tool_id}"
            derivation_prov.setdefault(prov_key, []).append(ev_id)

            if tool_id not in tools:
                tools[tool_id] = {
                    "window_n": 0,
                    "successes": 0,
                    "failures": 0,
                    "history": [],
                    "consecutive_failures": 0,
                    "latency_ewma_ms": float(p.get("latency_ms", 100.0)),
                    "circuit": "CLOSED",
                    "last_error": "NONE",
                }
            t_state = tools[tool_id]
            success = bool(p.get("success", True))
            latency = float(p.get("latency_ms", 0.0))

            # Maintain true sliding window history
            history: list[bool] = list(t_state.get("history", []))
            history.append(success)
            if len(history) > self.max_tool_window:
                history = history[-self.max_tool_window:]
            t_state["history"] = history

            # Calculate window stats strictly from sliding history
            t_state["window_n"] = len(history)
            t_state["successes"] = history.count(True)
            t_state["failures"] = history.count(False)

            # Count trailing consecutive failures
            consec_fail = 0
            for item in reversed(history):
                if not item:
                    consec_fail += 1
                else:
                    break
            t_state["consecutive_failures"] = consec_fail

            if success:
                t_state["last_error"] = "NONE"
            else:
                t_state["last_error"] = p.get("error_class", "EXEC_ERROR")
                if "retry_after_ms" in p and p["retry_after_ms"] is not None:
                    t_state["retry_after_ms"] = p["retry_after_ms"]

            # Update EWMA latency
            prev_latency = t_state["latency_ewma_ms"]
            t_state["latency_ewma_ms"] = round(
                self.ewma_alpha * latency + (1.0 - self.ewma_alpha) * prev_latency, 2
            )

        elif topic == "runtime":
            derivation_prov.setdefault("runtime", []).append(ev_id)
            for k in [
                "wall_remaining_ms",
                "step",
                "pids_current",
                "pids_max",
                "threads_current",
                "network",
                "filesystem",
            ]:
                if k in p:
                    runtime[k] = p[k]
            if "last_exit" in p:
                runtime["last_exit"] = p["last_exit"]

        elif topic == "economics":
            derivation_prov.setdefault("economics", []).append(ev_id)
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

    def _finalize_hardware(
        self, hardware: dict[str, Any], unavailable_fields: set[str], has_prior: bool
    ) -> None:
        # Finalize Memory
        mem = hardware["memory"]
        cur = mem.get("current_bytes")
        max_b = mem.get("max_bytes")

        if cur is None and not has_prior:
            mem["state"] = "UNKNOWN"
            unavailable_fields.add("hardware.memory")
        else:
            if max_b is not None and max_b > 0 and cur is not None:
                headroom = max(0.0, min(1.0, (max_b - cur) / max_b))
                mem["headroom_ratio"] = round(headroom, 4)
            elif cur is not None:
                mem["headroom_ratio"] = 1.0

            ev = mem.get("events_delta", {})
            oom_count = ev.get("oom", 0) + ev.get("oom_kill", 0)
            high_count = ev.get("high", 0)
            psi_some = mem.get("psi_some_avg10", 0.0) or 0.0
            headroom_val = mem.get("headroom_ratio", 1.0) or 1.0

            if oom_count > 0 or (max_b and cur and cur >= max_b) or headroom_val < 0.05:
                mem["state"] = "CRITICAL"
            elif high_count > 0 or headroom_val < 0.20 or psi_some >= 2.0:
                mem["state"] = "PRESSURED"
            elif cur is not None:
                mem["state"] = "OK"
            else:
                mem["state"] = "UNKNOWN"

        # Finalize CPU
        cpu = hardware["cpu"]
        nr_throttled = cpu.get("nr_throttled_delta")
        throttled_usec = cpu.get("throttled_usec_delta")
        quota = cpu.get("quota_cores")

        if quota is None and nr_throttled is None and throttled_usec is None and not has_prior:
            cpu["state"] = "UNKNOWN"
            unavailable_fields.add("hardware.cpu")
        else:
            nr_throttled = nr_throttled or 0
            throttled_usec = throttled_usec or 0
            if throttled_usec > 500000:
                cpu["state"] = "CRITICAL"
            elif nr_throttled > 0 or throttled_usec > 0:
                cpu["state"] = "THROTTLED"
            else:
                cpu["state"] = "OK"

        # Finalize Disk
        disk = hardware["ephemeral_disk"]
        free_b = disk.get("free_bytes")
        tot_b = disk.get("total_bytes")
        if free_b is None and not has_prior:
            disk["state"] = "UNKNOWN"
            unavailable_fields.add("hardware.ephemeral_disk")
        else:
            if tot_b and tot_b > 0 and free_b is not None:
                used_b = tot_b - free_b
                disk["used_bytes"] = used_b
                disk["used_ratio"] = round(max(0.0, min(1.0, used_b / tot_b)), 4)
            if free_b is not None:
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
            fail = t_state.get("failures", 0)

            if consec >= self.circuit_consecutive_failure_limit:
                t_state["circuit"] = "OPEN"
                t_state["state"] = "DEGRADED"
            elif win >= 3 and (fail / win) >= 0.4:
                t_state["circuit"] = "DEGRADED"
                t_state["state"] = "DEGRADED"
            else:
                t_state["circuit"] = "CLOSED"
                t_state["state"] = "OK"

    def _finalize_runtime(self, runtime: dict[str, Any], unavailable_fields: set[str]) -> None:
        wall = runtime.get("wall_remaining_ms")
        if wall is not None:
            if wall < 5000:
                runtime["state"] = "TERMINATING"
            else:
                runtime["state"] = "RUNNING"
        if runtime.get("network") == "UNKNOWN":
            unavailable_fields.add("runtime.network")

    def _finalize_economics(self, economics: dict[str, Any], unavailable_fields: set[str]) -> None:
        rem_quota = economics.get("rate_limit_remaining")
        budget = economics.get("budget_remaining_usd")
        if (rem_quota is not None and rem_quota == 0) or (budget is not None and budget <= 0.0):
            economics["state"] = "EXHAUSTED"
        elif (rem_quota is not None and rem_quota <= 5) or (budget is not None and budget <= 0.05):
            economics["state"] = "WARN"
        elif rem_quota is not None or budget is not None:
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


def rehydrate_snapshot(delta_snapshot: dict[str, Any], base_snapshot: dict[str, Any]) -> dict[str, Any]:
    """Rehydrate a delta snapshot with its base checkpoint into a complete state snapshot."""
    if delta_snapshot.get("kind") != "delta":
        return copy.deepcopy(delta_snapshot)
    if base_snapshot.get("snapshot_id") != delta_snapshot.get("base_snapshot_id"):
        raise ValueError(
            f"Base snapshot ID mismatch: delta expects '{delta_snapshot.get('base_snapshot_id')}', "
            f"got base '{base_snapshot.get('snapshot_id')}'"
        )
    merged = copy.deepcopy(base_snapshot)
    merged["seq"] = delta_snapshot["seq"]
    merged["observed_at_ms"] = delta_snapshot["observed_at_ms"]
    merged["fresh_for_ms"] = delta_snapshot["fresh_for_ms"]
    merged["kind"] = "delta"
    merged["base_snapshot_id"] = delta_snapshot["base_snapshot_id"]
    merged["raw_event_hashes"] = delta_snapshot["raw_event_hashes"]

    for ns in ["hardware", "tools", "runtime", "economics", "derivation_provenance"]:
        if ns in delta_snapshot:
            merged[ns] = copy.deepcopy(delta_snapshot[ns])
    if "recommended_constraints" in delta_snapshot:
        merged["recommended_constraints"] = copy.deepcopy(delta_snapshot["recommended_constraints"])
    if "unavailable_fields" in delta_snapshot:
        merged["unavailable_fields"] = copy.deepcopy(delta_snapshot["unavailable_fields"])

    merged["snapshot_id"] = delta_snapshot["snapshot_id"]
    return merged
