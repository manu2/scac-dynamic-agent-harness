"""Optional local HTTP-span capture and Toxiproxy control for ToolRoute validation."""

from __future__ import annotations

from dataclasses import dataclass
import json
import time
from urllib import error, request

from scac_harness.events import RawTelemetryEvent


@dataclass(frozen=True)
class HTTPToolResult:
    status_code: int | None
    event: RawTelemetryEvent


def capture_http_tool_span(*, tool_id: str, url: str, timestamp_ms: int, timeout_s: float = 5.0) -> HTTPToolResult:
    """Call a local endpoint and turn the observed outcome into a host event."""
    started = time.monotonic()
    status: int | None = None
    try:
        with request.urlopen(url, timeout=timeout_s) as response:  # nosec B310: caller controls local validation URL
            status = response.status
    except error.HTTPError as exc:
        status = exc.code
    except error.URLError:
        status = None
    latency_ms = max(0, round((time.monotonic() - started) * 1000))
    success = status is not None and 200 <= status < 300
    error_class = "NONE" if success else (f"HTTP_{status}" if status is not None else "CONNECTION_ERROR")
    return HTTPToolResult(status, RawTelemetryEvent(
        timestamp_ms=timestamp_ms, source="host_http_span_v1", topic="tool_span",
        payload={"tool_id": tool_id, "latency_ms": latency_ms, "success": success, "error_class": error_class},
    ))


class ToxiproxyClient:
    """Minimal HTTP client; the optional toxiproxy server remains external to the harness."""

    def __init__(self, base_url: str = "http://127.0.0.1:8474") -> None:
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, body: dict[str, object] | None = None) -> dict[str, object]:
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = request.Request(self.base_url + path, data=data, method=method, headers={"Content-Type": "application/json"})
        with request.urlopen(req, timeout=5) as response:  # nosec B310: explicit local validation endpoint
            raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}

    def create_proxy(self, *, name: str, listen: str, upstream: str) -> dict[str, object]:
        return self._request("POST", "/proxies", {"name": name, "listen": listen, "upstream": upstream, "enabled": True})

    def add_latency(self, *, proxy: str, latency_ms: int, jitter_ms: int = 0) -> dict[str, object]:
        return self._request("POST", f"/proxies/{proxy}/toxics", {"name": "scac_latency", "type": "latency", "stream": "downstream", "toxicity": 1.0, "attributes": {"latency": latency_ms, "jitter": jitter_ms}})

    def set_enabled(self, *, proxy: str, enabled: bool) -> dict[str, object]:
        return self._request("POST", f"/proxies/{proxy}", {"enabled": enabled})

    def delete_proxy(self, *, proxy: str) -> dict[str, object]:
        return self._request("DELETE", f"/proxies/{proxy}")
