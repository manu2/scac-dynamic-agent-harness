"""Portable, deterministic MemoryGovernor calibration simulator.

This module is intentionally not evidence of kernel cgroup enforcement. It
calibrates the agent action interface and external oracle on hosts such as macOS.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MemoryState:
    turn: int
    limit_bytes: int
    occupied_bytes: int
    remaining_work_bytes: int

    @property
    def headroom_bytes(self) -> int:
        return self.limit_bytes - self.occupied_bytes


@dataclass(frozen=True)
class MemoryAction:
    chunk_bytes: int
    workers: int
    checkpoint: bool = False

    def __post_init__(self) -> None:
        if self.chunk_bytes <= 0 or self.workers <= 0:
            raise ValueError("chunk_bytes and workers must be positive")


@dataclass(frozen=True)
class MemoryOutcome:
    success: bool
    violation: str | None
    processed_bytes: int
    terminal: bool


class MemoryGovernorOracle:
    """Frozen safety-first external oracle over a predeclared action set."""

    ACTIONS = (
        MemoryAction(64, 1), MemoryAction(64, 2), MemoryAction(128, 1),
        MemoryAction(128, 2), MemoryAction(256, 1), MemoryAction(256, 2),
    )

    @classmethod
    def safe_actions(cls, state: MemoryState) -> frozenset[MemoryAction]:
        return frozenset(a for a in cls.ACTIONS if a.chunk_bytes * a.workers <= state.headroom_bytes)

    @classmethod
    def best_actions(cls, state: MemoryState) -> frozenset[MemoryAction]:
        safe = cls.safe_actions(state)
        if not safe:
            return frozenset({MemoryAction(64, 1, checkpoint=True)})
        throughput = max(a.chunk_bytes * a.workers for a in safe)
        return frozenset(a for a in safe if a.chunk_bytes * a.workers == throughput)

    @classmethod
    def regret(cls, state: MemoryState, action: MemoryAction) -> float:
        if action not in cls.safe_actions(state):
            return 10_000.0
        best = max(a.chunk_bytes * a.workers for a in cls.best_actions(state))
        return float(best - action.chunk_bytes * action.workers)


class MemoryGovernorSimulator:
    """Frozen pressure schedule for portable, model-free calibration."""

    def __init__(self) -> None:
        self._occupancy = (256, 768, 512, 256)
        self._turn = 0
        # Four decision points exercise both pressure onset and recovery.
        self._remaining = 1536

    @property
    def state(self) -> MemoryState:
        if self._turn >= len(self._occupancy):
            raise RuntimeError("episode is terminal")
        return MemoryState(self._turn, 1024, self._occupancy[self._turn], self._remaining)

    def step(self, action: MemoryAction) -> MemoryOutcome:
        state = self.state
        footprint = action.chunk_bytes * action.workers
        if footprint > state.headroom_bytes:
            self._turn = len(self._occupancy)
            return MemoryOutcome(False, "VIRTUAL_MEMORY_LIMIT", 0, True)
        processed = min(footprint, self._remaining)
        self._remaining -= processed
        self._turn += 1
        return MemoryOutcome(True, None, processed, self._remaining == 0 or self._turn == len(self._occupancy))
