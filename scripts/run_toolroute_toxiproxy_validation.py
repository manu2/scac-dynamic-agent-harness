"""Run one retained local socket-level ToolRoute adapter validation.

This validates telemetry collection through real local HTTP proxies. It does
not call a model and must never be included in a synthetic API outcome cohort.
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
from urllib import request
from uuid import uuid4

from scac_harness.http_tools import ToxiproxyClient, capture_http_tool_span
from scac_harness.reducer import DeterministicReducer
from scac_harness.renderer import render_tier2_envelope


class _SuccessHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        self.send_response(200)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *_: object) -> None:
        return


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _write_once(directory: Path, filename: str, value: object) -> None:
    destination = directory / filename
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


def _wait_ready(base_url: str, process: subprocess.Popen[str]) -> None:
    for _ in range(50):
        if process.poll() is not None:
            raise RuntimeError("toxiproxy-server exited before becoming ready")
        try:
            with request.urlopen(base_url + "/version", timeout=0.2):
                return
        except OSError:
            time.sleep(0.1)
    raise TimeoutError("toxiproxy-server did not become ready")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--toxiproxy-server", type=Path, required=True)
    parser.add_argument("--experiments-root", type=Path, default=Path("experiments"))
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    directory = args.experiments_root / "adapter-validation" / "toolroute" / f"{stamp}-toxiproxy-v2.12.0-{uuid4().hex}"
    directory.mkdir(parents=True, mode=0o700)
    backend = ThreadingHTTPServer(("127.0.0.1", 0), _SuccessHandler)
    backend_thread = Thread(target=backend.serve_forever, daemon=True)
    backend_thread.start()
    admin_port, alpha_port, beta_port = _free_port(), _free_port(), _free_port()
    base_url = f"http://127.0.0.1:{admin_port}"
    server = subprocess.Popen([str(args.toxiproxy_server), "-host", "127.0.0.1", "-port", str(admin_port)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    client = ToxiproxyClient(base_url)
    error: Exception | None = None
    try:
        _wait_ready(base_url, server)
        schedule = {
            "kind": "toolroute_toxiproxy_socket_adapter_validation_v1",
            "not_model_evidence": True,
            "toxiproxy_version": "2.12.0",
            "backend": f"127.0.0.1:{backend.server_port}",
            "schedule": [
                {"step": "baseline", "alpha": "enabled", "beta": "enabled"},
                {"step": "latency", "alpha": {"latency_ms": 150, "jitter_ms": 0}},
                {"step": "disable", "beta": "disabled"},
            ],
        }
        _write_once(directory, "manifest.json", schedule)
        upstream = f"127.0.0.1:{backend.server_port}"
        client.create_proxy(name="alpha", listen=f"127.0.0.1:{alpha_port}", upstream=upstream)
        client.create_proxy(name="beta", listen=f"127.0.0.1:{beta_port}", upstream=upstream)
        events = [
            capture_http_tool_span(tool_id="tool_alpha", url=f"http://127.0.0.1:{alpha_port}/", timestamp_ms=1000).event,
            capture_http_tool_span(tool_id="tool_beta", url=f"http://127.0.0.1:{beta_port}/", timestamp_ms=1010).event,
        ]
        client.add_latency(proxy="alpha", latency_ms=150)
        events.append(capture_http_tool_span(tool_id="tool_alpha", url=f"http://127.0.0.1:{alpha_port}/", timestamp_ms=2000).event)
        client.set_enabled(proxy="beta", enabled=False)
        events.append(capture_http_tool_span(tool_id="tool_beta", url=f"http://127.0.0.1:{beta_port}/", timestamp_ms=3000, timeout_s=1.0).event)
        _write_once(directory, "raw-events.json", {"events": [event.to_dict() for event in events]})
        snapshot = DeterministicReducer().reduce("toolroute-toxiproxy-validation", 0, events, observed_at_ms=3020)
        _write_once(directory, "checkpoint.json", snapshot)
        _write_once(directory, "rendered-telemetry.json", {"text": render_tier2_envelope(snapshot)})
        checks = {
            "baseline_success": bool(events[0].payload["success"]) and bool(events[1].payload["success"]),
            "latency_injected": int(events[2].payload["latency_ms"]) >= 120,
            "disabled_proxy_is_failure": events[3].payload["error_class"] == "CONNECTION_ERROR",
        }
        if not all(checks.values()):
            raise RuntimeError(f"Toxiproxy validation checks failed: {checks}")
        _write_once(directory, "result.json", {"classification": "COMPLETED", "checks": checks})
    except Exception as exc:
        _write_once(directory, "result.json", {"classification": "FAILED", "error": repr(exc)})
        error = exc
    finally:
        for proxy in ("alpha", "beta"):
            try:
                client.delete_proxy(proxy=proxy)
            except OSError:
                pass
        server.terminate()
        try:
            server.wait(timeout=3)
        except subprocess.TimeoutExpired:
            server.kill()
        backend.shutdown()
        backend.server_close()
    classification = "FAILED" if error is not None else "COMPLETED"
    hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(directory.glob("*.json"))}
    _write_once(directory, "finalization.json", {"classification": classification, "artifact_sha256": hashes})
    if error is not None:
        raise error
    print(directory)


if __name__ == "__main__":
    main()
