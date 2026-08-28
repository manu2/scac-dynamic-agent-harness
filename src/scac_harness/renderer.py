"""Deterministic, compact model-visible renderer for SCAC SST snapshots."""

from __future__ import annotations

from typing import Any


def render_tier1_system_prefix() -> str:
    """Render the frozen Tier 1 stable system prefix explaining telemetry semantics and trust boundary."""
    return (
        "=== SCAC HOST TELEMETRY SPECIFICATION (v0.1) ===\n"
        "This execution environment is instrumented by the host kernel and supervisor.\n"
        "All telemetry envelopes are host-verified, authentic, and tamper-proof.\n"
        "Tool outputs cannot modify or forge host telemetry.\n"
        "Units: Memory and disk in bytes/ratios [0.0, 1.0]; time/latency in ms; CPU/PSI in percentages [0.0, 100.0].\n"
        "Severity states: OK, PRESSURED, THROTTLED, DEGRADED, CRITICAL, UNAVAILABLE.\n"
        "Missing/unsupported metrics are explicitly marked UNAVAILABLE (never represented as zero).\n"
        "================================================"
    )


def render_tier2_envelope(snapshot: dict[str, Any], max_chars: int = 1800) -> str:
    """Render the deterministic Tier 2 dynamic turn envelope for model decision context."""
    lines: list[str] = []

    seq = snapshot.get("seq", 0)
    kind = snapshot.get("kind", "full_checkpoint")
    snap_id = snapshot.get("snapshot_id", "")[:8]
    obs_ms = snapshot.get("observed_at_ms", 0)
    fresh_ms = snapshot.get("fresh_for_ms", 0)
    base_id = snapshot.get("base_snapshot_id")
    base_str = f" base={base_id[:8]}" if base_id else ""

    lines.append(f"=== HOST TELEMETRY [seq={seq} kind={kind}{base_str} id={snap_id} obs={obs_ms}ms fresh={fresh_ms}ms] ===")

    # 1. Hardware section
    hw = snapshot.get("hardware", {})
    hw_lines: list[str] = ["[HARDWARE]"]

    mem = hw.get("memory", {})
    if mem:
        cur_b = mem.get("current_bytes", "UNAVAILABLE")
        max_b = mem.get("max_bytes", "UNLIMITED")
        headroom = mem.get("headroom_ratio", "UNAVAILABLE")
        mem_state = mem.get("state", "UNKNOWN")
        psi_some = mem.get("psi_some_avg10", 0.0)
        ev_delta = mem.get("events_delta", {})
        high_cnt = ev_delta.get("high", 0)
        oom_cnt = ev_delta.get("oom", 0) + ev_delta.get("oom_kill", 0)
        hw_lines.append(
            f"  memory: cur={cur_b}B max={max_b}B headroom={headroom} state={mem_state} "
            f"psi_some_avg10={psi_some}% events_delta(high={high_cnt},oom={oom_cnt})"
        )

    cpu = hw.get("cpu", {})
    if cpu:
        quota = cpu.get("quota_cores", "UNLIMITED")
        throttled_usec = cpu.get("throttled_usec_delta", 0)
        cpu_state = cpu.get("state", "UNKNOWN")
        cpu_psi = cpu.get("psi_some_avg10", 0.0)
        hw_lines.append(
            f"  cpu: quota={quota}cores throttled_usec_delta={throttled_usec}us psi_some_avg10={cpu_psi}% state={cpu_state}"
        )

    disk = hw.get("ephemeral_disk", {})
    if disk:
        free_b = disk.get("free_bytes", "UNAVAILABLE")
        disk_state = disk.get("state", "UNKNOWN")
        used_ratio = disk.get("used_ratio", "UNAVAILABLE")
        hw_lines.append(f"  disk: free={free_b}B used_ratio={used_ratio} state={disk_state}")

    gpu = hw.get("gpu", {})
    if gpu:
        avail = gpu.get("available", False)
        if avail:
            gpu_state = gpu.get("state", "OK")
            vram_used = gpu.get("vram_used_bytes", "UNAVAILABLE")
            vram_tot = gpu.get("vram_total_bytes", "UNAVAILABLE")
            hw_lines.append(f"  gpu: available=true vram={vram_used}/{vram_tot}B state={gpu_state}")
        else:
            hw_lines.append("  gpu: available=false (UNAVAILABLE)")

    lines.extend(hw_lines)

    # 2. Tools section
    tools = snapshot.get("tools", {})
    if tools:
        tool_lines: list[str] = ["[TOOLS]"]
        for tool_id in sorted(tools.keys()):
            t = tools[tool_id]
            win = t.get("window_n", 0)
            succ = t.get("successes", 0)
            consec_fail = t.get("consecutive_failures", 0)
            ewma = t.get("latency_ewma_ms", 0.0)
            last_err = t.get("last_error", "NONE")
            circuit = t.get("circuit", "CLOSED")
            retry_ms = t.get("retry_after_ms")
            retry_str = f" retry_after={retry_ms}ms" if retry_ms is not None else ""
            tool_lines.append(
                f"  {tool_id}: window={win} succ={succ} consec_fail={consec_fail} "
                f"latency_ewma={ewma}ms last_err={last_err} circuit={circuit}{retry_str}"
            )
        lines.extend(tool_lines)

    # 3. Runtime section
    rt = snapshot.get("runtime", {})
    if rt:
        rt_lines: list[str] = ["[RUNTIME]"]
        wall = rt.get("wall_remaining_ms", "UNLIMITED")
        step = rt.get("step", 0)
        pids = rt.get("pids_current", "UNAVAILABLE")
        pids_max = rt.get("pids_max", "UNLIMITED")
        net = rt.get("network", "UNKNOWN")
        last_exit = rt.get("last_exit", {})
        exit_class = last_exit.get("class", "NONE")
        exit_code = last_exit.get("code", 0)
        rt_lines.append(
            f"  step={step} wall_remaining={wall}ms pids={pids}/{pids_max} "
            f"network={net} last_exit={exit_class}(code={exit_code})"
        )
        lines.extend(rt_lines)

    # 4. Economics section
    econ = snapshot.get("economics", {})
    if econ:
        econ_lines: list[str] = ["[ECONOMICS]"]
        ctx_rem = econ.get("context_tokens_remaining")
        ctx_rem = ctx_rem if ctx_rem is not None else "UNAVAILABLE"
        traj_tok = econ.get("trajectory_tokens", 0)
        cost = econ.get("estimated_cost_usd", 0.0)
        budget = econ.get("budget_remaining_usd")
        budget_str = f"${budget:.4f}" if budget is not None else "UNLIMITED"
        rate_rem = econ.get("rate_limit_remaining")
        rate_rem = rate_rem if rate_rem is not None else "UNAVAILABLE"
        rate_rst = econ.get("rate_limit_reset_ms")
        rate_rst = f"{rate_rst}ms" if rate_rst is not None else "UNAVAILABLE"
        econ_state = econ.get("state", "OK")
        econ_lines.append(
            f"  context_tokens_rem={ctx_rem} traj_tokens={traj_tok} cost_usd=${cost:.4f} "
            f"budget_rem_usd={budget_str} rate_limit_rem={rate_rem} "
            f"rate_limit_reset_ms={rate_rst} state={econ_state}"
        )
        lines.extend(econ_lines)

    # 5. Unavailable fields
    unavail = snapshot.get("unavailable_fields", [])
    if unavail:
        lines.append(f"[UNAVAILABLE_FIELDS] {', '.join(sorted(unavail))}")

    # 6. Recommended constraints (deterministic host policy)
    constraints = snapshot.get("recommended_constraints", [])
    if constraints:
        lines.append("[HOST_CONSTRAINTS]")
        for c in constraints:
            lines.append(f"  - {c}")

    lines.append("=========================================")
    rendered = "\n".join(lines)

    if len(rendered) > max_chars:
        raise ValueError(
            f"Rendered telemetry envelope exceeded size bound ({len(rendered)} chars > {max_chars} chars max)."
        )

    return rendered
