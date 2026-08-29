"""Swappable local transport strategies for ToolRoute development smoke tests.

They collect and execute tool spans; they never decide an action or score it.
The synthetic benchmark remains the paper path.  Toxiproxy is an adapter smoke
strategy and its artifacts must remain separately namespaced.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from scac_harness.events import RawTelemetryEvent
from scac_harness.http_tools import capture_http_tool_span


class ToolRouteTransportStrategy(Protocol):
    """Host-owned transport boundary used before and after a subject decision."""

    name: str

    def monitor(self, *, timestamp_ms: int) -> list[RawTelemetryEvent]: ...

    def execute(self, *, action: str, timestamp_ms: int) -> RawTelemetryEvent: ...


@dataclass(frozen=True)
class ToxiproxyTransportStrategy:
    """Collect genuine loopback HTTP spans through preconfigured proxies."""

    urls: dict[str, str]
    probes_per_tool: int = 3
    name: str = "toxiproxy_loopback_http_v1"

    def monitor(self, *, timestamp_ms: int) -> list[RawTelemetryEvent]:
        events: list[RawTelemetryEvent] = []
        for index, tool in enumerate(sorted(self.urls)):
            for probe in range(self.probes_per_tool):
                events.append(capture_http_tool_span(
                    tool_id=tool, url=self.urls[tool], timestamp_ms=timestamp_ms + index * 100 + probe,
                    timeout_s=2.0,
                ).event)
        return events

    def execute(self, *, action: str, timestamp_ms: int) -> RawTelemetryEvent:
        if action == "wait":
            return RawTelemetryEvent(
                timestamp_ms=timestamp_ms, source=self.name, topic="tool_span",
                payload={"tool_id": "wait", "latency_ms": 500, "success": False, "error_class": "NONE"},
            )
        if action not in self.urls:
            raise ValueError(f"unknown ToolRoute action: {action}")
        return capture_http_tool_span(tool_id=action, url=self.urls[action], timestamp_ms=timestamp_ms, timeout_s=2.0).event
