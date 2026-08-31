"""OpenTelemetry-backed HTTP tool observations for the transport replication.

This module is intentionally separate from the frozen synthetic ToolRoute
runner.  A local HTTP client is instrumented with the standard Requests
instrumentor; the adapter consumes the finished OpenTelemetry span and only
then emits a SCAC ``RawTelemetryEvent``.  It rejects incomplete or ambiguous
span batches rather than silently filling in health facts.
"""

from __future__ import annotations

from dataclasses import dataclass
import threading
from typing import Any, Mapping

from opentelemetry import trace
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
import requests

from scac_harness.events import RawTelemetryEvent


OTEL_HTTP_SOURCE = "otel_requests_http_client_span_v1"
_INSTRUMENTATION_LOCK = threading.RLock()


@dataclass(frozen=True)
class OTelHTTPToolResult:
    """One real HTTP request and its sole completed client span."""

    tool_id: str
    status_code: int | None
    event: RawTelemetryEvent
    raw_span: Mapping[str, object]


def _json_scalar(value: Any) -> object:
    """Return a JSON-safe scalar/list value without retaining opaque objects."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_json_scalar(item) for item in value]
    return str(value)


def serialize_finished_span(span: object) -> dict[str, object]:
    """Preserve auditable, transport-relevant OpenTelemetry span facts."""
    attributes = getattr(span, "attributes", {})
    status = getattr(span, "status", None)
    context = getattr(span, "context", None)
    resource = getattr(span, "resource", None)
    resource_attributes = getattr(resource, "attributes", {}) if resource is not None else {}
    span_events = []
    for event in getattr(span, "events", ()):
        event_attributes = getattr(event, "attributes", {})
        # Retain the standard exception type, but never persist exception text
        # or a traceback: either may echo endpoint/query material.
        exception_type = _attribute(dict(event_attributes), "exception.type", "error.type")
        span_events.append({
            "name": str(getattr(event, "name", "")),
            "exception_type": _json_scalar(exception_type) if exception_type is not None else None,
        })
    return {
        "name": str(getattr(span, "name", "")),
        "kind": str(getattr(span, "kind", "")),
        "start_time_unix_nano": int(getattr(span, "start_time", 0)),
        "end_time_unix_nano": int(getattr(span, "end_time", 0)),
        "status_code": str(getattr(status, "status_code", "")),
        "trace_id": f"{getattr(context, 'trace_id', 0):032x}",
        "span_id": f"{getattr(context, 'span_id', 0):016x}",
        "attributes": {str(key): _json_scalar(value) for key, value in dict(attributes).items()},
        "events": span_events,
        "resource": {str(key): _json_scalar(value) for key, value in dict(resource_attributes).items()},
    }


def _attribute(attributes: Mapping[str, object], *names: str) -> object | None:
    for name in names:
        value = attributes.get(name)
        if value is not None:
            return value
    return None


def event_from_http_client_span(*, tool_id: str, raw_span: Mapping[str, object]) -> RawTelemetryEvent:
    """Map one standard OTel HTTP-client span to one validated SCAC tool event.

    No observed fact is fabricated.  In particular, a missing end timestamp,
    method, or endpoint identity is a protocol failure.  HTTP status and
    transport error are derived from standard semantic-convention attributes.
    """
    attributes = raw_span.get("attributes")
    if not isinstance(attributes, Mapping):
        raise ValueError("OTel span lacks an attribute mapping")
    start_ns = raw_span.get("start_time_unix_nano")
    end_ns = raw_span.get("end_time_unix_nano")
    if not isinstance(start_ns, int) or not isinstance(end_ns, int) or end_ns < start_ns:
        raise ValueError("OTel span lacks a valid start/end duration")
    method = _attribute(attributes, "http.request.method", "http.method")
    endpoint = _attribute(attributes, "server.address", "net.peer.name", "url.full", "http.url")
    if str(method).upper() != "GET" or not isinstance(endpoint, str) or not endpoint:
        raise ValueError("OTel span is not an identifiable GET HTTP client span")

    raw_status = _attribute(attributes, "http.response.status_code", "http.status_code")
    status_code: int | None
    try:
        status_code = int(raw_status) if raw_status is not None else None
    except (TypeError, ValueError) as exc:
        raise ValueError("OTel span carries a non-numeric HTTP status") from exc
    error_type = _attribute(attributes, "error.type", "exception.type")
    success = status_code is not None and 200 <= status_code < 300
    if success:
        error_class = "NONE"
    elif status_code is not None:
        error_class = f"HTTP_{status_code}"
    elif error_type is not None or str(raw_span.get("status_code", "")).endswith("ERROR"):
        error_class = "CONNECTION_ERROR"
    else:
        raise ValueError("failed OTel HTTP span has neither response status nor error type")

    latency_ms = round((end_ns - start_ns) / 1_000_000, 3)
    timestamp_ms = end_ns // 1_000_000
    return RawTelemetryEvent(
        timestamp_ms=timestamp_ms,
        source=OTEL_HTTP_SOURCE,
        topic="tool_span",
        payload={
            "tool_id": tool_id,
            "latency_ms": latency_ms,
            "success": success,
            "error_class": error_class,
            "otel_span_id": raw_span.get("span_id"),
            "otel_trace_id": raw_span.get("trace_id"),
            "http_status_code": status_code,
        },
    )


class OTelRequestsToolClient:
    """Scoped standard Requests instrumentation with an in-memory span exporter.

    Requests instrumentation is process-global by design.  The coordinator
    serializes this scope and always uninstalls it; attempting nested clients
    fails rather than mixing spans between episodes.
    """

    def __init__(self, *, service_name: str = "scac-toolroute-transport") -> None:
        self._provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
        self._exporter = InMemorySpanExporter()
        self._provider.add_span_processor(SimpleSpanProcessor(self._exporter))
        self._instrumentor = RequestsInstrumentor()
        self._active = False
        self.service_name = service_name

    def __enter__(self) -> "OTelRequestsToolClient":
        _INSTRUMENTATION_LOCK.acquire()
        try:
            if self._instrumentor.is_instrumented_by_opentelemetry:
                raise RuntimeError("Requests instrumentation is already active; refusing to mix OTel spans")
            self._instrumentor.instrument(tracer_provider=self._provider)
            self._active = True
            return self
        except Exception:
            _INSTRUMENTATION_LOCK.release()
            raise

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        try:
            try:
                if self._active:
                    self._instrumentor.uninstrument()
            finally:
                self._active = False
                self._provider.shutdown()
        finally:
            _INSTRUMENTATION_LOCK.release()

    def get(self, *, tool_id: str, url: str, timeout_s: float = 2.0) -> OTelHTTPToolResult:
        if not self._active:
            raise RuntimeError("OTelRequestsToolClient must be used as a context manager")
        self._exporter.clear()
        status_code: int | None = None
        try:
            response = requests.get(url, timeout=timeout_s)
            status_code = response.status_code
        except requests.RequestException:
            # The failed request still must have produced its client span.  The
            # adapter below verifies that before representing it as a fault.
            pass
        spans = list(self._exporter.get_finished_spans())
        if len(spans) != 1:
            raise RuntimeError(f"expected exactly one OTel HTTP client span for {tool_id}, found {len(spans)}")
        raw_span = serialize_finished_span(spans[0])
        event = event_from_http_client_span(tool_id=tool_id, raw_span=raw_span)
        if status_code != event.payload["http_status_code"]:
            raise RuntimeError("requests result disagrees with the OTel span HTTP status")
        return OTelHTTPToolResult(tool_id, status_code, event, raw_span)
