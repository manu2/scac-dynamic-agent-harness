"""Normalized Raw Telemetry Event definitions and provenance verification."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from scac_harness.identity import compute_content_hash


@dataclass(frozen=True)
class RawTelemetryEvent:
    """An immutable, host-recorded raw telemetry event with cryptographic provenance verification."""

    timestamp_ms: int
    source: str
    topic: str
    payload: dict[str, Any]
    event_id: str = field(default="")

    def __post_init__(self) -> None:
        core = {
            "timestamp_ms": self.timestamp_ms,
            "source": self.source,
            "topic": self.topic,
            "payload": self.payload,
        }
        calculated_id = compute_content_hash(core)
        if self.event_id:
            if self.event_id != calculated_id:
                raise ValueError(
                    f"Forged or corrupted event_id: declared '{self.event_id}' != calculated '{calculated_id}'"
                )
        else:
            object.__setattr__(self, "event_id", calculated_id)

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
        if "timestamp_ms" not in data or "source" not in data or "topic" not in data or "payload" not in data:
            raise ValueError(f"Malformed raw telemetry event dict: {data}")
        return cls(
            timestamp_ms=data["timestamp_ms"],
            source=data["source"],
            topic=data["topic"],
            payload=data["payload"],
            event_id=data.get("event_id", ""),
        )
