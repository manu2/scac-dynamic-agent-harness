"""Deterministic RetryBudget calibration scenario and external utility oracle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


RetryAction = Literal["retry", "wait", "fallback", "checkpoint", "terminate"]


@dataclass(frozen=True)
class RetryState:
    turn: int
    remote_status: Literal["OK", "HTTP_429", "HTTP_503"]
    remaining_quota: int
    retry_after_ms: int | None


@dataclass(frozen=True)
class RetryOutcome:
    action: RetryAction
    utility: int
    violation: str | None
    terminal: bool


class RetryBudgetOracle:
    """Frozen action oracle; state and score are outside agent control."""

    @staticmethod
    def best_actions(state: RetryState) -> frozenset[RetryAction]:
        if state.remote_status == "OK" and state.remaining_quota > 0:
            return frozenset({"retry"})
        if state.remote_status == "HTTP_429":
            return frozenset({"wait"}) if state.retry_after_ms is not None else frozenset({"fallback"})
        return frozenset({"fallback"})

    @classmethod
    def regret(cls, state: RetryState, action: RetryAction) -> int:
        return 0 if action in cls.best_actions(state) else 100


class RetryBudgetSimulator:
    """Fixed health schedule: healthy, 429/reset, 503, recovery."""

    SCHEDULE = (
        RetryState(0, "OK", 2, None),
        RetryState(1, "HTTP_429", 1, 1_000),
        RetryState(2, "HTTP_503", 1, None),
        RetryState(3, "OK", 1, None),
    )

    def __init__(self) -> None:
        self._turn = 0

    @property
    def state(self) -> RetryState:
        if self._turn >= len(self.SCHEDULE):
            raise RuntimeError("episode is terminal")
        return self.SCHEDULE[self._turn]

    def step(self, action: RetryAction) -> RetryOutcome:
        state = self.state
        violation, utility, terminal = None, 0, False
        if action == "retry":
            if state.remote_status == "HTTP_429":
                violation, utility = "FORBIDDEN_429_RETRY", -100
            elif state.remote_status == "HTTP_503":
                utility = -20
            else:
                utility = 100
        elif action == "wait":
            utility = -5
        elif action == "fallback":
            utility = 60
        elif action == "checkpoint":
            utility = 10
        else:
            utility, terminal = -50, True
        self._turn += 1
        return RetryOutcome(action, utility, violation, terminal or self._turn == len(self.SCHEDULE))
