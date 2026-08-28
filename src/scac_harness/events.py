"""Normalized Raw Telemetry Event definitions and serialization."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from scac_harness.identity import compute_content_hash


@dataclass(frozen=True)
class RawTelemetryEvent:
    """An immutable, host-recorded raw telemetry event."""

    timestamp_ms: int
    source: str
    topic: str
    payload: dict[str, Any]
    event_id: str = field(default="")

    def __post_init__(self) -> None:
        if not self.event_id:
            # Deterministic hash of the core event content
            core = {
                "timestamp_ms": self.timestamp_ms,
                "source": self.source,
                "topic": self.topic,
                "payload": self.payload,
            }
            object.__setattr__(self, "event_id", compute_content_hash(core))

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp_ms": self.timestamp_ms,
            "source": self.source,
            "topic": self.topic,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RawTelemetryEvent:
        return cls(
            timestamp_ms=data["timestamp_ms"],
            source=data["source"],
            topic=data["topic"],
            payload=data["payload"],
            event_id=data.get("event_id", ""),
        )
