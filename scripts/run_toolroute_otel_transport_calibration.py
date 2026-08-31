"""Run model-free, socket-backed ToolRoute transport-replication controls.

This is not a provider runner.  It keeps the HTTP backends, Toxiproxy, OTel
instrumented monitor, snapshot reducer, and final action in one long-lived
coordinator process so a calibration cannot accidentally probe a dead backend.
Every artifact is reserved before the first local request and finalized with
content hashes.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import subprocess
from threading import Thread
import time
from typing import Callable, Literal
from uuid import uuid4

from scac_harness.http_tools import ToxiproxyClient
from scac_harness.otel_transport import OTelHTTPToolResult, OTelRequestsToolClient
from scac_harness.reducer import DeterministicReducer
from scac_harness.renderer import render_tier2_envelope
from scac_harness.scenarios.toolroute import ToolRouteOracle


Regime = Literal["latency", "connection_error", "http_error"]
Condition = Literal["A", "B", "C"]
_REGIMES: tuple[Regime, ...] = ("latency", "connection_error", "http_error")
_ACTIONS = ("tool_alpha", "tool_beta", "wait")
_PROBES_PER_TOOL = 3
_MIN_MARGIN_MS = 50.0


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _handler(status_code: int) -> type[BaseHTTPRequestHandler]:
    class FixedStatusHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            body = b'{"record":"C-042"}' if status_code == 200 else b'{"error":"scheduled"}'
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_: object) -> None:
            return

    return FixedStatusHandler


def _start_backend(status_code: int) -> tuple[ThreadingHTTPServer, Thread]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _handler(status_code))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _write_once(directory: Path, filename: str, value: object) -> None:
    destination = directory / filename
    if destination.exists():
        raise FileExistsError(destination)
    temporary = directory / f".{filename}.{uuid4().hex}.tmp"
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.link(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _finalize(directory: Path, classification: str) -> None:
    hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(directory.glob("*.json"))}
    _write_once(directory, "finalization.json", {"classification": classification, "artifact_sha256": hashes})


def _wait_ready(base_url: str, process: subprocess.Popen[bytes]) -> None:
    import urllib.request

    for _ in range(50):
        if process.poll() is not None:
            raise RuntimeError("toxiproxy-server exited before becoming ready")
        try:
            with urllib.request.urlopen(base_url + "/version", timeout=0.2):  # nosec B310: local Toxiproxy only
                return
        except OSError:
            time.sleep(0.1)
    raise TimeoutError("toxiproxy-server did not become ready")


def _task() -> str:
    return (
        "Task: retrieve customer record C-042. tool_alpha and tool_beta expose the same read-only record API. "
        "Return exactly one listed action label and no other text.\n"
        "Options: tool_alpha, tool_beta, wait\n"
    )


def _neutral_telemetry(rendered: str) -> str:
    lines: list[str] = []
    for line in rendered.splitlines():
        if line.startswith("  tool_alpha:") or line.startswith("  tool_beta:"):
            tool = line.split(":", 1)[0].strip()
            lines.append(
                f"  {tool}: window=3 succ=3 consec_fail=0 latency_ewma=1000.0ms "
                "last_err=NONE circuit=CLOSED age=10ms"
            )
        else:
            lines.append(line)
    return "\n".join(lines)


def _condition_inputs(snapshot: dict[str, object]) -> dict[str, dict[str, object]]:
    task = _task()
    rendered = render_tier2_envelope(snapshot)
    return {
        "A": {"prompt": task, "visible_snapshot": None},
        "B": {"prompt": task + _neutral_telemetry(rendered), "visible_snapshot": None},
        "C": {"prompt": task + rendered, "visible_snapshot": snapshot},
    }


DecisionCallback = Callable[[Condition, dict[str, object], Path], str]


def _run_regime(
    *, regime: Regime, toxiproxy_server: Path, experiments_root: Path,
    condition: Condition = "C", decision_callback: DecisionCallback | None = None,
    run_kind: str = "model_free_calibration",
) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    directory = experiments_root / "g2-calibrations" / "toolroute-otel-transport" / f"{stamp}-{regime}-{uuid4().hex}"
    directory.mkdir(parents=True, mode=0o700)
    alpha_status = 200
    beta_status = 503 if regime == "http_error" else 200
    alpha_backend, _ = _start_backend(alpha_status)
    beta_backend, _ = _start_backend(beta_status)
    admin_port, alpha_port, beta_port = _free_port(), _free_port(), _free_port()
    admin_url = f"http://127.0.0.1:{admin_port}"
    process: subprocess.Popen[bytes] | None = None
    client = ToxiproxyClient(admin_url)
    classification = "FAILED"
    raised: Exception | None = None
    try:
        manifest = {
            "kind": f"toolroute_otel_transport_{run_kind}_v0.1",
            "scenario": "ToolRoute-OTel-Transport-v0.1",
            "regime": regime,
            "not_provider_evidence": True,
            "not_pooled_with_toolroute_v1.0": True,
            "coordinator": "single_process_persistent_backend_toxiproxy_otel_v0.1",
            "instrumentation": "opentelemetry-instrumentation-requests",
            "reducer_source_required": "otel_requests_http_client_span_v1",
            "probes_per_tool": _PROBES_PER_TOOL,
            "condition": condition,
            "fault_schedule": {
                "latency": {"proxy": "alpha", "latency_ms": 300},
                "connection_error": {"proxy": "alpha", "enabled": False},
                "http_error": {"backend": "beta", "http_status": 503},
            }[regime],
            "primary_oracle": "observable_monitor_cost_v0.6",
        }
        _write_once(directory, "manifest.json", manifest)
        process = subprocess.Popen(
            [str(toxiproxy_server), "-host", "127.0.0.1", "-port", str(admin_port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _wait_ready(admin_url, process)
        client.create_proxy(name="alpha", listen=f"127.0.0.1:{alpha_port}", upstream=f"127.0.0.1:{alpha_backend.server_port}")
        client.create_proxy(name="beta", listen=f"127.0.0.1:{beta_port}", upstream=f"127.0.0.1:{beta_backend.server_port}")
        if regime == "latency":
            client.add_latency(proxy="alpha", latency_ms=300)
        elif regime == "connection_error":
            client.set_enabled(proxy="alpha", enabled=False)

        urls = {"tool_alpha": f"http://127.0.0.1:{alpha_port}/customer/C-042", "tool_beta": f"http://127.0.0.1:{beta_port}/customer/C-042"}
        monitor_results: list[OTelHTTPToolResult] = []
        with OTelRequestsToolClient() as otel_client:
            for tool_id in ("tool_alpha", "tool_beta"):
                for _ in range(_PROBES_PER_TOOL):
                    monitor_results.append(otel_client.get(tool_id=tool_id, url=urls[tool_id]))
            events = [result.event for result in monitor_results]
            snapshot = DeterministicReducer().reduce(
                trajectory_id=f"toolroute-otel-transport-{regime}", seq=0, events=events,
                observed_at_ms=max(event.timestamp_ms for event in events),
            )
            condition_inputs = _condition_inputs(snapshot)
            best_actions = ToolRouteOracle.observable_best_actions(snapshot)
            if len(best_actions) != 1:
                raise RuntimeError("transport calibration requires one observable best action")
            oracle_action = next(iter(best_actions))
            selected_action = oracle_action if decision_callback is None else decision_callback(
                condition, condition_inputs[condition], directory,
            ).strip()
            if selected_action not in _ACTIONS:
                _write_once(directory, "model-decision.json", {
                    "condition": condition, "accepted": False, "classification": "MALFORMED_SUBJECT_RESPONSE",
                    "response_text": selected_action,
                })
                _write_once(directory, "result.json", {"classification": "MALFORMED_SUBJECT_RESPONSE"})
                classification = "MALFORMED_SUBJECT_RESPONSE"
                return directory
            action_result = None if selected_action == "wait" else otel_client.get(tool_id=selected_action, url=urls[selected_action])

        _write_once(directory, "raw-otel-monitor-spans.json", {
            "spans": [{"tool_id": result.tool_id, "span": result.raw_span} for result in monitor_results],
        })
        _write_once(directory, "reducer-events.json", {"events": [event.to_dict() for event in events]})
        _write_once(directory, "snapshot.json", snapshot)
        _write_once(directory, "condition-inputs.json", condition_inputs)
        _write_once(directory, "model-decision.json", {
            "decision_source": "host_observable_oracle_positive_control" if decision_callback is None else "external_subject",
            "selected_action": selected_action,
            "observable_best_actions": sorted(best_actions),
            "observable_margin_ms": ToolRouteOracle.observable_margin(snapshot),
            "policy_regret": ToolRouteOracle.observable_regret(snapshot, selected_action),
        })
        if action_result is not None:
            _write_once(directory, "raw-otel-action-span.json", {"tool_id": action_result.tool_id, "span": action_result.raw_span})
            _write_once(directory, "action-result.json", {
                "status_code": action_result.status_code,
                "event": action_result.event.to_dict(),
            })
        else:
            _write_once(directory, "action-result.json", {"action": "wait", "executed": False, "reason": "subject_selected_wait"})

        tool_state = snapshot.get("tools", {})
        assert isinstance(tool_state, dict)
        b_tool_lines = [line for line in str(condition_inputs["B"]["prompt"]).splitlines() if line.startswith("  tool_")]
        c_tool_lines = [line for line in str(condition_inputs["C"]["prompt"]).splitlines() if line.startswith("  tool_")]
        checks = {
            "each_tool_has_three_standard_otel_spans": all(
                sum(result.tool_id == tool for result in monitor_results) == _PROBES_PER_TOOL for tool in urls
            ),
            "every_reducer_event_is_otel_derived": all(event.source == "otel_requests_http_client_span_v1" for event in events),
            "observable_margin_is_actionable": ToolRouteOracle.observable_margin(snapshot) >= _MIN_MARGIN_MS,
            "oracle_selected_action_has_zero_regret": ToolRouteOracle.observable_regret(snapshot, selected_action) == 0.0 if decision_callback is None else True,
            "live_action_matches_telemetry_selection": action_result is not None and action_result.event.payload["success"] is True if decision_callback is None else True,
            "latency_fault_observed": regime != "latency" or float(tool_state["tool_alpha"]["latency_ewma_ms"]) >= 250.0,
            "connection_fault_observed": regime != "connection_error" or tool_state["tool_alpha"]["last_error"] == "CONNECTION_ERROR",
            "http_fault_observed": regime != "http_error" or tool_state["tool_beta"]["last_error"] == "HTTP_503",
            "neutral_control_has_same_tool_lines": all(
                marker in str(condition_inputs["B"]["prompt"])
                for marker in ("tool_alpha: window=3", "tool_beta: window=3")
            ),
            "neutral_control_preserves_tool_row_shape": (
                len(b_tool_lines) == len(c_tool_lines) == 2
                and [line.split(":", 1)[0] for line in b_tool_lines] == [line.split(":", 1)[0] for line in c_tool_lines]
            ),
            "only_c_carries_truthful_snapshot": (
                condition_inputs["A"]["visible_snapshot"] is None
                and condition_inputs["B"]["visible_snapshot"] is None
                and condition_inputs["C"]["visible_snapshot"] == snapshot
            ),
        }
        if not all(checks.values()):
            raise RuntimeError(f"transport calibration checks failed: {checks}")
        _write_once(directory, "result.json", {"classification": "COMPLETED", "checks": checks})
        classification = "COMPLETED"
    except Exception as exc:
        raised = exc
        _write_once(directory, "result.json", {"classification": "FAILED", "exception_type": type(exc).__name__, "reason": str(exc)})
    finally:
        for proxy in ("alpha", "beta"):
            try:
                client.delete_proxy(proxy=proxy)
            except OSError:
                pass
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
        alpha_backend.shutdown()
        alpha_backend.server_close()
        beta_backend.shutdown()
        beta_backend.server_close()
        _finalize(directory, classification)
    if raised is not None:
        raise raised
    return directory


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--toxiproxy-server", type=Path, required=True)
    parser.add_argument("--experiments-root", type=Path, default=Path("experiments"))
    parser.add_argument("--regime", choices=(*_REGIMES, "all"), default="all")
    args = parser.parse_args()
    if not args.toxiproxy_server.is_file() or not os.access(args.toxiproxy_server, os.X_OK):
        raise ValueError("--toxiproxy-server must name an executable local binary")
    regimes = _REGIMES if args.regime == "all" else (args.regime,)
    directories = [_run_regime(regime=regime, toxiproxy_server=args.toxiproxy_server, experiments_root=args.experiments_root) for regime in regimes]
    print(json.dumps({"classification": "COMPLETED", "directories": [str(directory) for directory in directories]}))


if __name__ == "__main__":
    main()
