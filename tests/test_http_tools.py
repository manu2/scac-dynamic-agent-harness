from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from scac_harness.http_tools import ToxiproxyClient, capture_http_tool_span


class _Handler(BaseHTTPRequestHandler):
    calls: list[tuple[str, str]] = []

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/failure":
            self.send_response(503)
        else:
            self.send_response(200)
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        self.__class__.calls.append((self.command, self.path))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"{}")

    def do_DELETE(self) -> None:  # noqa: N802
        self.__class__.calls.append((self.command, self.path))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, *_: object) -> None:
        return


def _server() -> tuple[ThreadingHTTPServer, Thread]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def test_capture_http_tool_span_records_real_status() -> None:
    server, _ = _server()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        ok = capture_http_tool_span(tool_id="alpha", url=base + "/ok", timestamp_ms=1)
        failed = capture_http_tool_span(tool_id="beta", url=base + "/failure", timestamp_ms=2)
    finally:
        server.shutdown()
    assert ok.status_code == 200 and ok.event.payload["success"] is True
    assert failed.status_code == 503 and failed.event.payload["error_class"] == "HTTP_503"


def test_capture_http_tool_span_uses_schema_error_taxonomy_for_connection_failure() -> None:
    result = capture_http_tool_span(tool_id="alpha", url="http://127.0.0.1:1/", timestamp_ms=3, timeout_s=0.1)
    assert result.status_code is None
    assert result.event.payload["error_class"] == "CONNECTION_ERROR"


def test_toxiproxy_client_uses_expected_local_api_paths() -> None:
    _Handler.calls.clear()
    server, _ = _server()
    try:
        client = ToxiproxyClient(f"http://127.0.0.1:{server.server_port}")
        client.create_proxy(name="alpha", listen="127.0.0.1:19000", upstream="127.0.0.1:19001")
        client.add_latency(proxy="alpha", latency_ms=50)
        client.set_enabled(proxy="alpha", enabled=False)
        client.delete_proxy(proxy="alpha")
    finally:
        server.shutdown()
    assert _Handler.calls == [("POST", "/proxies"), ("POST", "/proxies/alpha/toxics"), ("POST", "/proxies/alpha"), ("DELETE", "/proxies/alpha")]
