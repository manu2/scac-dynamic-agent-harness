"""Start/submit a retained one-decision ToolRoute Toxiproxy subagent smoke.

Development-only.  It verifies the complete path from real local transport
telemetry to a fresh subject prompt and back to a real proxied tool execution.
It is never a provider/API cohort or paper denominator.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
from urllib import request
from uuid import uuid4

from scac_harness.http_tools import ToxiproxyClient
from scac_harness.reducer import DeterministicReducer
from scac_harness.renderer import render_tier2_envelope
from scac_harness.scenarios.toolroute import ToolRouteOracle
from scac_harness.toolroute_transport import ToxiproxyTransportStrategy


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _write_once(directory: Path, filename: str, value: object) -> None:
    target = directory / filename
    if target.exists():
        raise FileExistsError(target)
    temporary = directory / f".{filename}.{uuid4().hex}.tmp"
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush(); os.fsync(handle.fileno())
    try:
        os.link(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def _finalize(directory: Path, classification: str) -> None:
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(directory.glob("*.json"))}
    _write_once(directory, "finalization.json", {"classification": classification, "artifact_sha256": hashes})


def _wait(base_url: str, process: subprocess.Popen[object]) -> None:
    for _ in range(50):
        if process.poll() is not None:
            raise RuntimeError("toxiproxy server failed to start")
        try:
            with request.urlopen(base_url + "/version", timeout=0.2):
                return
        except OSError:
            time.sleep(0.1)
    raise TimeoutError("toxiproxy server did not become ready")


def _prompt(condition: str, telemetry: str) -> str:
    task = "Task: retrieve the next required record. tool_alpha and tool_beta are functionally equivalent. Return exactly one listed action label and no other text.\nOptions: tool_alpha, tool_beta, wait\n"
    if condition == "A":
        return task
    if condition == "B":
        prefix = "[NEUTRAL STRUCTURAL CONTROL]\n"
        return task + prefix + ("cedar lantern meadow " * 100)[:max(0, len(telemetry) - len(prefix))]
    return task + telemetry


def _close(manifest: dict[str, object]) -> None:
    runtime = manifest["runtime"]
    assert isinstance(runtime, dict)
    client = ToxiproxyClient(str(runtime["admin_url"]))
    for name in ("tool_alpha", "tool_beta"):
        try:
            client.delete_proxy(proxy=name)
        except OSError:
            pass
    for key in ("toxiproxy_pid", "backend_pid"):
        try:
            os.kill(int(runtime[key]), signal.SIGTERM)
        except ProcessLookupError:
            pass


def start(args: argparse.Namespace) -> None:
    directory = Path(args.experiments_root) / "dev-smoke-toxiproxy" / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')}-{args.condition}-{uuid4().hex}"
    directory.mkdir(parents=True, mode=0o700)
    backend_port, admin_port, alpha_port, beta_port = _free_port(), _free_port(), _free_port(), _free_port()
    backend_log = (directory / "backend.log").open("x")
    toxi_log = (directory / "toxiproxy.log").open("x")
    backend = subprocess.Popen([sys.executable, "-m", "http.server", str(backend_port), "--bind", "127.0.0.1"], stdout=backend_log, stderr=subprocess.STDOUT)
    toxi = subprocess.Popen([str(args.toxiproxy_server), "-host", "127.0.0.1", "-port", str(admin_port)], stdout=toxi_log, stderr=subprocess.STDOUT)
    backend_log.close(); toxi_log.close()
    base_url = f"http://127.0.0.1:{admin_port}"
    manifest = {"kind": "development_only_toxiproxy_subagent_smoke_v1", "not_paper_evidence": True, "condition": args.condition, "strategy": "toxiproxy_loopback_http_v1", "runtime": {"admin_url": base_url, "toxiproxy_pid": toxi.pid, "backend_pid": backend.pid, "alpha_url": f"http://127.0.0.1:{alpha_port}/", "beta_url": f"http://127.0.0.1:{beta_port}/"}, "precommitted_schedule": {"tool_alpha": {"latency_ms": 300}, "tool_beta": {"latency_ms": 0}}}
    try:
        _wait(base_url, toxi)
        client = ToxiproxyClient(base_url)
        upstream = f"127.0.0.1:{backend_port}"
        client.create_proxy(name="tool_alpha", listen=f"127.0.0.1:{alpha_port}", upstream=upstream)
        client.create_proxy(name="tool_beta", listen=f"127.0.0.1:{beta_port}", upstream=upstream)
        client.add_latency(proxy="tool_alpha", latency_ms=300)
        _write_once(directory, "manifest.json", manifest)
        strategy = ToxiproxyTransportStrategy({"tool_alpha": manifest["runtime"]["alpha_url"], "tool_beta": manifest["runtime"]["beta_url"]})  # type: ignore[index]
        events = strategy.monitor(timestamp_ms=1000)
        snapshot = DeterministicReducer().reduce("toxiproxy-subagent-smoke", 0, events, observed_at_ms=1300)
        if ToolRouteOracle.observable_margin(snapshot) < 50:
            raise RuntimeError("observable oracle margin is ambiguous")
        telemetry = render_tier2_envelope(snapshot)
        message = _prompt(args.condition, telemetry)
        subject_prompt = message + "\n\nDo not inspect the workspace or use tools. Reply with exactly one action label and nothing else."
        _write_once(directory, "host.json", {"raw_events": [e.to_dict() for e in events], "snapshot": snapshot, "rendered_telemetry": telemetry})
        _write_once(directory, "input.json", {"condition": args.condition, "message": message, "subject_prompt": subject_prompt})
        print(json.dumps({"trial_dir": str(directory), "subject_prompt": subject_prompt}, indent=2))
    except Exception as exc:
        _write_once(directory, "result.json", {"classification": "FAILED_START", "error": repr(exc)})
        _finalize(directory, "FAILED_START")
        _close(manifest)
        raise


def submit(args: argparse.Namespace) -> None:
    directory = Path(args.trial_dir)
    manifest = json.loads((directory / "manifest.json").read_text())
    response = args.response.strip()
    if response not in {"tool_alpha", "tool_beta", "wait"}:
        _write_once(directory, "rejection.json", {"response_text": args.response, "reason": "response_is_not_exact_action_label"})
        print(json.dumps({"accepted": False}))
        return
    host = json.loads((directory / "host.json").read_text())
    runtime = manifest["runtime"]
    strategy = ToxiproxyTransportStrategy({"tool_alpha": runtime["alpha_url"], "tool_beta": runtime["beta_url"]})
    event = strategy.execute(action=response, timestamp_ms=2000)
    result = {"classification": "COMPLETED", "subject_id": args.subject_id, "response_text": args.response, "action": response, "action_event": event.to_dict(), "policy_regret": ToolRouteOracle.observable_regret(host["snapshot"], response), "success": bool(event.payload["success"])}
    _write_once(directory, "result.json", result)
    _close(manifest)
    _finalize(directory, "COMPLETED")
    print(json.dumps(result, indent=2))


def abort(args: argparse.Namespace) -> None:
    directory = Path(args.trial_dir)
    manifest = json.loads((directory / "manifest.json").read_text())
    _write_once(directory, "result.json", {"classification": "ABORTED_DEVELOPMENT", "reason": args.reason})
    _close(manifest)
    _finalize(directory, "ABORTED_DEVELOPMENT")
    print(json.dumps({"trial_dir": str(directory), "classification": "ABORTED_DEVELOPMENT"}))


def main() -> None:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    p_start = commands.add_parser("start")
    p_start.add_argument("--condition", choices=("A", "B", "C"), default="C")
    p_start.add_argument("--toxiproxy-server", required=True, type=Path)
    p_start.add_argument("--experiments-root", default="experiments")
    p_submit = commands.add_parser("submit")
    p_submit.add_argument("--trial-dir", required=True)
    p_submit.add_argument("--subject-id", required=True)
    p_submit.add_argument("--response", required=True)
    p_abort = commands.add_parser("abort")
    p_abort.add_argument("--trial-dir", required=True)
    p_abort.add_argument("--reason", required=True)
    args = parser.parse_args()
    if args.command == "start":
        start(args)
    elif args.command == "submit":
        submit(args)
    else:
        abort(args)


if __name__ == "__main__":
    main()
