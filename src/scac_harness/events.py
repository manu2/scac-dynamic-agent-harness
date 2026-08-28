"""Normalized Raw Telemetry Event definitions with cryptographic provenance and deep immutability."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Mapping

from scac_harness.identity import compute_content_hash


class FrozenDict(dict):
    """An immutable dictionary that rejects mutation and supports deepcopy/serialization."""

    def __setitem__(self, key: Any, value: Any) -> None:
        raise TypeError(f"'{self.__class__.__name__}' object is immutable")

    def __delitem__(self, key: Any) -> None:
        raise TypeError(f"'{self.__class__.__name__}' object is immutable")

    def clear(self) -> None:
        raise TypeError(f"'{self.__class__.__name__}' object is immutable")

    def update(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError(f"'{self.__class__.__name__}' object is immutable")

    def setdefault(self, key: Any, default: Any = None) -> Any:
        raise TypeError(f"'{self.__class__.__name__}' object is immutable")

    def pop(self, *args: Any, **kwargs: Any) -> Any:
        raise TypeError(f"'{self.__class__.__name__}' object is immutable")

    def popitem(self) -> Any:
        raise TypeError(f"'{self.__class__.__name__}' object is immutable")

    def __copy__(self) -> FrozenDict:
        return self

    def __deepcopy__(self, memo: Any) -> FrozenDict:
        return FrozenDict({k: copy.deepcopy(v, memo) for k, v in self.items()})


def _deep_freeze(val: Any) -> Any:
    """Recursively freeze dictionaries and lists into immutable mappings and tuples."""
    if isinstance(val, (dict, Mapping)):
        return FrozenDict({k: _deep_freeze(v) for k, v in val.items()})
    elif isinstance(val, (list, tuple)):
        return tuple(_deep_freeze(v) for v in val)
    elif isinstance(val, set):
        return frozenset(_deep_freeze(v) for v in val)
    return val


def _unfreeze(val: Any) -> Any:
    """Recursively convert frozen mappings and tuples back into standard mutable dicts and lists."""
    if isinstance(val, (dict, Mapping)):
        return {k: _unfreeze(v) for k, v in val.items()}
    elif isinstance(val, tuple):
        return [_unfreeze(v) for v in val]
    return val


@dataclass(frozen=True)
class RawTelemetryEvent:
    """An immutable, host-recorded raw telemetry event with cryptographic provenance verification."""

    timestamp_ms: int
    source: str
    topic: str
    payload: Mapping[str, Any]
    event_id: str = field(default="")

    def __init__(
        self,
        timestamp_ms: int,
        source: str,
        topic: str,
        payload: dict[str, Any] | Mapping[str, Any],
        event_id: str = "",
    ) -> None:
        object.__setattr__(self, "timestamp_ms", timestamp_ms)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "topic", topic)

        # Deep freeze payload to prevent post-creation mutation
        frozen_payload = _deep_freeze(payload)
        object.__setattr__(self, "payload", frozen_payload)

        # Compute content hash on standard representation
        core = {
            "timestamp_ms": timestamp_ms,
            "source": source,
            "topic": topic,
            "payload": _unfreeze(frozen_payload),
        }
        calculated_id = compute_content_hash(core)

        if event_id:
            if event_id != calculated_id:
                raise ValueError(
                    f"Forged or corrupted event_id: declared '{event_id}' != calculated '{calculated_id}'"
                )
            object.__setattr__(self, "event_id", event_id)
        else:
            object.__setattr__(self, "event_id", calculated_id)

    def to_dict(self) -> dict[str, Any]:
        """Return a deep-copied, cryptographically verified dictionary representation."""
        core = {
            "timestamp_ms": self.timestamp_ms,
            "source": self.source,
            "topic": self.topic,
            "payload": _unfreeze(self.payload),
        }
        computed = compute_content_hash(core)
        if computed != self.event_id:
            raise ValueError(f"Event payload tampering detected: hash '{self.event_id}' != computed '{computed}'")
        return {
            "event_id": self.event_id,
            "timestamp_ms": self.timestamp_ms,
            "source": self.source,
            "topic": self.topic,
            "payload": _unfreeze(self.payload),
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
