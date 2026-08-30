"""Host-side cgroup v2 collection with explicit capability checks.

This module never substitutes host values when cgroup v2 is unavailable.  It is
deliberately separate from the reducer: it reads kernel counters, computes
counter deltas, and emits normalized raw events for the reducer to consume.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time
from typing import Callable

from scac_harness.events import RawTelemetryEvent


class CgroupV2Unavailable(RuntimeError):
    """Raised when the requested cgroup v2 controller cannot be verified."""


@dataclass(frozen=True)
class CgroupCapability:
    available: bool
    reason: str | None
    root: Path
    controllers: frozenset[str]


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise CgroupV2Unavailable(f"cannot read {path}: {exc}") from exc


def _key_value_file(path: Path) -> dict[str, int]:
    result: dict[str, int] = {}
    for line in _read_text(path).splitlines():
        pieces = line.split()
        if len(pieces) != 2:
            raise CgroupV2Unavailable(f"malformed cgroup counter line in {path}: {line!r}")
        try:
            result[pieces[0]] = int(pieces[1])
        except ValueError as exc:
            raise CgroupV2Unavailable(f"non-integer cgroup counter in {path}: {line!r}") from exc
    return result


class CgroupV2Collector:
    """Collect a bounded memory/CPU cgroup-v2 sample for one trial cgroup."""

    REQUIRED_FILES = frozenset({"memory.current", "memory.max", "memory.events", "cpu.max", "cpu.stat"})

    def __init__(self, root: Path, clock_ms: Callable[[], int] | None = None) -> None:
        self.root = Path(root)
        self._clock_ms = clock_ms or (lambda: time.monotonic_ns() // 1_000_000)
        self._previous_memory_events: dict[str, int] | None = None
        self._previous_cpu_stat: dict[str, int] | None = None

    def capability(self) -> CgroupCapability:
        controllers_file = self.root / "cgroup.controllers"
        if not controllers_file.is_file():
            return CgroupCapability(False, f"missing {controllers_file}", self.root, frozenset())
        try:
            controllers = frozenset(_read_text(controllers_file).split())
        except CgroupV2Unavailable as exc:
            return CgroupCapability(False, str(exc), self.root, frozenset())
        missing = self.REQUIRED_FILES - {p.name for p in self.root.iterdir() if p.is_file()}
        if missing:
            return CgroupCapability(False, f"missing required files: {', '.join(sorted(missing))}", self.root, controllers)
        if not {"memory", "cpu"}.issubset(controllers):
            return CgroupCapability(False, "memory and cpu controllers are not both available", self.root, controllers)
        return CgroupCapability(True, None, self.root, controllers)

    def _require_capability(self) -> None:
        capability = self.capability()
        if not capability.available:
            raise CgroupV2Unavailable(capability.reason or "cgroup v2 unavailable")

    @staticmethod
    def _delta(current: dict[str, int], previous: dict[str, int] | None, fields: tuple[str, ...]) -> dict[str, int]:
        if previous is None:
            return {field: 0 for field in fields}
        delta: dict[str, int] = {}
        for field in fields:
            now = current.get(field, 0)
            before = previous.get(field, 0)
            if now < before:
                raise CgroupV2Unavailable(f"counter regressed for {field}: {now} < {before}")
            delta[field] = now - before
        return delta

    def collect(self) -> list[RawTelemetryEvent]:
        """Return normalized cgroup events; first sample has an explicit zero interval."""
        self._require_capability()
        timestamp_ms = self._clock_ms()
        memory_events = _key_value_file(self.root / "memory.events")
        cpu_stat = _key_value_file(self.root / "cpu.stat")
        memory_delta = self._delta(memory_events, self._previous_memory_events, ("high", "max", "oom", "oom_kill"))
        cpu_delta = self._delta(cpu_stat, self._previous_cpu_stat, ("nr_throttled", "throttled_usec", "usage_usec"))
        self._previous_memory_events = memory_events
        self._previous_cpu_stat = cpu_stat

        memory_max_raw = _read_text(self.root / "memory.max")
        memory_max = None if memory_max_raw == "max" else int(memory_max_raw)
        cpu_max_parts = _read_text(self.root / "cpu.max").split()
        if len(cpu_max_parts) != 2:
            raise CgroupV2Unavailable("malformed cpu.max")
        quota_raw, period_raw = cpu_max_parts
        period_usec = int(period_raw)
        quota_cores = None if quota_raw == "max" else int(quota_raw) / period_usec

        memory_payload = {
            "current_bytes": int(_read_text(self.root / "memory.current")),
            "max_bytes": memory_max,
            "events_delta": memory_delta,
        }
        cpu_payload = {
            "quota_cores": quota_cores,
            "period_usec": period_usec,
            "nr_throttled_delta": cpu_delta["nr_throttled"],
            "throttled_usec_delta": cpu_delta["throttled_usec"],
            "usage_usec_delta": cpu_delta["usage_usec"],
        }
        return [
            RawTelemetryEvent(timestamp_ms, "cgroup_v2", "memory", memory_payload),
            RawTelemetryEvent(timestamp_ms, "cgroup_v2", "cpu", cpu_payload),
        ]
