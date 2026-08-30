"""Deterministic, compact model-visible renderer for SCAC SST snapshots with strict unavailability rendering."""

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
        "Severity states: OK, PRESSURED, THROTTLED, DEGRADED, CRITICAL, UNAVAILABLE, UNKNOWN.\n"
        "Missing/unsupported metrics are explicitly marked UNAVAILABLE (never represented as zero or healthy defaults).\n"
        "================================================"
    )


def render_tier2_envelope(snapshot: dict[str, Any], max_chars: int = 2000) -> str:
    """Render the deterministic Tier 2 dynamic turn envelope for model decision context."""
    lines: list[str] = []

    seq = snapshot.get("seq")
    seq_str = str(seq) if seq is not None else "UNAVAILABLE"
    kind = snapshot.get("kind", "full_checkpoint")
    snap_id = snapshot.get("snapshot_id", "")[:8]
    obs_ms = snapshot.get("observed_at_ms")
    obs_str = f"{obs_ms}ms" if obs_ms is not None else "UNAVAILABLE"
    fresh_ms = snapshot.get("fresh_for_ms")
    fresh_str = f"{fresh_ms}ms" if fresh_ms is not None else "UNAVAILABLE"
    base_id = snapshot.get("base_snapshot_id")
    base_str = f" base={base_id[:8]}" if base_id else ""

    lines.append(f"=== HOST TELEMETRY [seq={seq_str} kind={kind}{base_str} id={snap_id} obs={obs_str} fresh={fresh_str}] ===")

    # 1. Hardware section
    # 1. Hardware section
    hw = snapshot.get("hardware", {})
    if hw:
        hw_lines: list[str] = ["[HARDWARE]"]

        mem = hw.get("memory", {})
        if mem:
            cur_b = mem.get("current_bytes")
            cur_str = f"{cur_b}B" if cur_b is not None else "UNAVAILABLE"
            max_b = mem.get("max_bytes")
            max_str = f"{max_b}B" if max_b is not None else "UNLIMITED"
            headroom = mem.get("headroom_ratio")
            headroom_str = str(headroom) if headroom is not None else "UNAVAILABLE"
            mem_state = mem.get("state", "UNKNOWN")
            psi_some = mem.get("psi_some_avg10")
            psi_str = f"{psi_some}%" if psi_some is not None else "UNAVAILABLE"
            ev_delta = mem.get("events_delta")
            if ev_delta:
                high_cnt = ev_delta.get("high", "UNAVAILABLE")
                oom_cnt = ev_delta.get("oom", 0) + ev_delta.get("oom_kill", 0) if "oom" in ev_delta else "UNAVAILABLE"
                ev_str = f"events_delta(high={high_cnt},oom={oom_cnt})"
            else:
                ev_str = "events_delta=UNAVAILABLE"
            hw_lines.append(
                f"  memory: cur={cur_str} max={max_str} headroom={headroom_str} state={mem_state} "
                f"psi_some_avg10={psi_str} {ev_str}"
            )

        cpu = hw.get("cpu", {})
        if cpu:
            quota = cpu.get("quota_cores")
            quota_str = f"{quota}cores" if quota is not None else "UNLIMITED"
            throttled_usec = cpu.get("throttled_usec_delta")
            throttled_str = f"{throttled_usec}us" if throttled_usec is not None else "UNAVAILABLE"
            cpu_state = cpu.get("state", "UNKNOWN")
            cpu_psi = cpu.get("psi_some_avg10")
            cpu_psi_str = f"{cpu_psi}%" if cpu_psi is not None else "UNAVAILABLE"
            hw_lines.append(
                f"  cpu: quota={quota_str} throttled_usec_delta={throttled_str} psi_some_avg10={cpu_psi_str} state={cpu_state}"
            )

        disk = hw.get("ephemeral_disk", {})
        if disk:
            free_b = disk.get("free_bytes")
            free_str = f"{free_b}B" if free_b is not None else "UNAVAILABLE"
            disk_state = disk.get("state", "UNKNOWN")
            used_ratio = disk.get("used_ratio")
            used_ratio_str = str(used_ratio) if used_ratio is not None else "UNAVAILABLE"
            hw_lines.append(f"  disk: free={free_str} used_ratio={used_ratio_str} state={disk_state}")

        gpu = hw.get("gpu", {})
        if gpu:
            avail = gpu.get("available", False)
            if avail:
                gpu_state = gpu.get("state", "OK")
                vram_used = gpu.get("vram_used_bytes")
                vram_used_str = f"{vram_used}B" if vram_used is not None else "UNAVAILABLE"
                vram_tot = gpu.get("vram_total_bytes")
                vram_tot_str = f"{vram_tot}B" if vram_tot is not None else "UNAVAILABLE"
                hw_lines.append(f"  gpu: available=true vram={vram_used_str}/{vram_tot_str} state={gpu_state}")
            else:
                hw_lines.append("  gpu: available=false (UNAVAILABLE)")

        if len(hw_lines) > 1:
            lines.extend(hw_lines)

    # 2. Tools section
    tools = snapshot.get("tools", {})
    if tools:
        tool_lines: list[str] = ["[TOOLS]"]
        tool_observed = snapshot.get("subsystem_observed_at_ms", {}).get("tool_span")
        tool_age_ms = (obs_ms - tool_observed) if isinstance(obs_ms, int) and isinstance(tool_observed, int) else None
        tool_age_str = f" age={tool_age_ms}ms" if tool_age_ms is not None else " age=UNAVAILABLE"
        for tool_id in sorted(tools.keys()):
            t = tools[tool_id]
            win = t.get("window_n")
            win_str = str(win) if win is not None else "UNAVAILABLE"
            succ = t.get("successes")
            succ_str = str(succ) if succ is not None else "UNAVAILABLE"
            consec_fail = t.get("consecutive_failures")
            consec_str = str(consec_fail) if consec_fail is not None else "UNAVAILABLE"
            ewma = t.get("latency_ewma_ms")
            ewma_str = f"{ewma}ms" if ewma is not None else "UNAVAILABLE"
            last_err = t.get("last_error", "NONE")
            circuit = t.get("circuit", "UNKNOWN")
            retry_ms = t.get("retry_after_ms")
            retry_str = f" retry_after={retry_ms}ms" if retry_ms is not None else ""
            tool_lines.append(
                f"  {tool_id}: window={win_str} succ={succ_str} consec_fail={consec_str} "
                f"latency_ewma={ewma_str} last_err={last_err} circuit={circuit}{tool_age_str}{retry_str}"
            )
        lines.extend(tool_lines)

    # 3. Runtime section
    rt = snapshot.get("runtime", {})
    if rt:
        rt_lines: list[str] = ["[RUNTIME]"]
        wall = rt.get("wall_remaining_ms")
        wall_str = f"{wall}ms" if wall is not None else "UNLIMITED"
        step = rt.get("step")
        step_str = str(step) if step is not None else "UNAVAILABLE"
        pids = rt.get("pids_current")
        pids_str = str(pids) if pids is not None else "UNAVAILABLE"
        pids_max = rt.get("pids_max")
        pids_max_str = str(pids_max) if pids_max is not None else "UNLIMITED"
        net = rt.get("network", "UNKNOWN")
        last_exit = rt.get("last_exit")
        if last_exit:
            exit_class = last_exit.get("class", "NONE")
            exit_code = last_exit.get("code", 0)
            exit_str = f"last_exit={exit_class}(code={exit_code})"
        else:
            exit_str = "last_exit=UNAVAILABLE"
        rt_lines.append(
            f"  step={step_str} wall_remaining={wall_str} pids={pids_str}/{pids_max_str} "
            f"network={net} {exit_str}"
        )
        lines.extend(rt_lines)

    # 4. Economics section
    econ = snapshot.get("economics", {})
    if econ:
        econ_lines: list[str] = ["[ECONOMICS]"]
        ctx_rem = econ.get("context_tokens_remaining")
        ctx_rem_str = str(ctx_rem) if ctx_rem is not None else "UNAVAILABLE"
        traj_tok = econ.get("trajectory_tokens")
        traj_tok_str = str(traj_tok) if traj_tok is not None else "UNAVAILABLE"
        cost = econ.get("estimated_cost_usd")
        cost_str = f"${cost:.4f}" if cost is not None else "UNAVAILABLE"
        budget = econ.get("budget_remaining_usd")
        budget_str = f"${budget:.4f}" if budget is not None else "UNLIMITED"
        rate_rem = econ.get("rate_limit_remaining")
        rate_rem_str = str(rate_rem) if rate_rem is not None else "UNAVAILABLE"
        rate_rst = econ.get("rate_limit_reset_ms")
        rate_rst_str = f"{rate_rst}ms" if rate_rst is not None else "UNAVAILABLE"
        econ_state = econ.get("state", "UNKNOWN")
        econ_lines.append(
            f"  context_tokens_rem={ctx_rem_str} traj_tokens={traj_tok_str} cost_usd={cost_str} "
            f"budget_rem_usd={budget_str} rate_limit_rem={rate_rem_str} "
            f"rate_limit_reset_ms={rate_rst_str} state={econ_state}"
        )
        lines.extend(econ_lines)

    # 5. Unavailable fields
    unavail = snapshot.get("unavailable_fields", [])
    if unavail:
        lines.append(f"[UNAVAILABLE_FIELDS] {', '.join(sorted(unavail))}")

    lines.append("=========================================")
    rendered = "\n".join(lines)

    if len(rendered) > max_chars:
        raise ValueError(
            f"Rendered telemetry envelope exceeded size bound ({len(rendered)} chars > {max_chars} chars max)."
        )

    return rendered
