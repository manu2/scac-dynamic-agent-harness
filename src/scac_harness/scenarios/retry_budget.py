"""Deterministic RetryBudget v0.2 pending-work scenario and observable oracle.

This module intentionally models a pending work item rather than a row in a
fixed schedule. In particular, ``wait`` advances a host-owned logical clock
while retaining the work item; it never discards it merely to reach a favourable
later row. The primary oracle is a finite dynamic program over the same state
fields that a future condition-C renderer must expose.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from pathlib import Path
import random
from typing import Literal

from scac_harness.scenarios.archive import archive_calibration


RetryAction = Literal["retry", "wait", "fallback", "checkpoint", "terminate"]
PrimaryStatus = Literal["OK", "HTTP_429", "HTTP_503"]


@dataclass(frozen=True)
class RetryState:
    """Complete observable state for one pending work item.

    ``decision_steps_remaining`` prevents an invalid action from creating a
    cycle in the host-owned transition system. It is part of the decision budget
    and must be rendered if an agent experiment uses this oracle.
    """

    work_item: int
    decision_steps_remaining: int
    deadline_remaining_ms: int
    primary_status: PrimaryStatus
    remaining_quota: int
    retry_after_ms: int | None
    fallback_available: bool
    fallback_utility: int
    checkpoint_available: bool
    checkpointed: bool
    checkpoint_recovery_utility: int

    def __post_init__(self) -> None:
        if self.work_item < 0:
            raise ValueError("work_item must be non-negative")
        if self.decision_steps_remaining < 0:
            raise ValueError("decision_steps_remaining must be non-negative")
        if self.deadline_remaining_ms < 0:
            raise ValueError("deadline_remaining_ms must be non-negative")
        if self.remaining_quota < 0:
            raise ValueError("remaining_quota must be non-negative")
        if self.retry_after_ms is not None and self.retry_after_ms <= 0:
            raise ValueError("retry_after_ms must be positive when present")
        if self.primary_status == "HTTP_429" and self.retry_after_ms is None:
            raise ValueError("HTTP_429 requires an explicit retry_after_ms")
        if self.primary_status != "HTTP_429" and self.retry_after_ms is not None:
            raise ValueError("retry_after_ms is only valid for HTTP_429")
        if self.fallback_utility < 0 or self.checkpoint_recovery_utility < 0:
            raise ValueError("declared utilities must be non-negative")


@dataclass(frozen=True)
class RetryTransition:
    """Host-owned result of applying one action to one observable state."""

    action: RetryAction
    immediate_utility: int
    violation: str | None
    completed_work: bool
    next_state: RetryState | None


@dataclass(frozen=True)
class RetryOutcome:
    """Archived outcome without exposing mutable simulator internals."""

    action: RetryAction
    utility: int
    violation: str | None
    completed_work: bool
    terminal: bool


class RetryBudgetOracle:
    """Finite observable action-value oracle outside agent control.

    Values are total utility after the selected action followed by an optimal
    continuation. The transition uses no latent schedule: recovery is encoded by
    the visible 429 retry-after field and all other action effects are declared
    in ``RetryState``.
    """

    ACTIONS: tuple[RetryAction, ...] = ("retry", "wait", "fallback", "checkpoint", "terminate")
    PRIMARY_SUCCESS_UTILITY = 100
    FORBIDDEN_RETRY_UTILITY = -30
    UNAVAILABLE_FALLBACK_UTILITY = -30
    PRIMARY_503_UTILITY = -20
    CHECKPOINT_COST = 5
    WAIT_COST = 5

    @classmethod
    def transition(cls, state: RetryState, action: RetryAction) -> RetryTransition:
        """Apply one declared action without reading hidden environment state."""
        if action not in cls.ACTIONS:
            raise ValueError(f"unknown RetryBudget action: {action}")
        if state.decision_steps_remaining == 0:
            raise ValueError("cannot act after the decision budget is exhausted")

        next_steps = state.decision_steps_remaining - 1

        def advance(**changes: object) -> RetryState:
            return replace(state, decision_steps_remaining=next_steps, **changes)

        if action == "retry":
            if state.remaining_quota == 0:
                return RetryTransition(
                    action, cls.FORBIDDEN_RETRY_UTILITY, "QUOTA_EXHAUSTED", False, advance()
                )
            if state.primary_status == "OK":
                return RetryTransition(action, cls.PRIMARY_SUCCESS_UTILITY, None, True, None)
            if state.primary_status == "HTTP_429":
                return RetryTransition(
                    action,
                    cls.FORBIDDEN_RETRY_UTILITY,
                    "FORBIDDEN_RETRY_BEFORE_RETRY_AFTER",
                    False,
                    advance(),
                )
            return RetryTransition(
                action,
                cls.PRIMARY_503_UTILITY,
                "PRIMARY_HTTP_503",
                False,
                advance(remaining_quota=state.remaining_quota - 1),
            )

        if action == "wait":
            # Waiting is meaningful only when a visible recovery time arrives
            # before expiry. It preserves the pending work and quota.
            if state.primary_status == "HTTP_429" and state.retry_after_ms is not None:
                if state.retry_after_ms >= state.deadline_remaining_ms:
                    return RetryTransition(action, 0, "DEADLINE_EXPIRED_WHILE_WAITING", False, None)
                return RetryTransition(
                    action,
                    -cls.WAIT_COST,
                    None,
                    False,
                    advance(
                        deadline_remaining_ms=state.deadline_remaining_ms - state.retry_after_ms,
                        primary_status="OK",
                        retry_after_ms=None,
                    ),
                )
            return RetryTransition(action, 0, "NO_DECLARED_RECOVERY_TO_WAIT_FOR", False, None)

        if action == "fallback":
            if not state.fallback_available:
                return RetryTransition(
                    action, cls.UNAVAILABLE_FALLBACK_UTILITY, "FALLBACK_UNAVAILABLE", False, advance()
                )
            return RetryTransition(action, state.fallback_utility, None, True, None)

        if action == "checkpoint":
            if not state.checkpoint_available or state.checkpointed:
                return RetryTransition(
                    action, -cls.CHECKPOINT_COST, "CHECKPOINT_UNAVAILABLE", False, advance()
                )
            return RetryTransition(
                action,
                -cls.CHECKPOINT_COST,
                None,
                False,
                advance(checkpoint_available=False, checkpointed=True),
            )

        # ``terminate`` is deliberately useful only after host-visible progress
        # was preserved by a checkpoint. It never invents a successful result.
        return RetryTransition(
            action,
            state.checkpoint_recovery_utility if state.checkpointed else 0,
            None,
            False,
            None,
        )

    @classmethod
    def value(cls, state: RetryState) -> int:
        """Optimal observable continuation value for a pending work item."""
        if state.decision_steps_remaining == 0:
            return state.checkpoint_recovery_utility if state.checkpointed else 0
        return max(cls.action_values(state).values())

    @classmethod
    def action_values(cls, state: RetryState) -> dict[RetryAction, int]:
        """Return numeric values for every legal label in the declared action set."""
        values: dict[RetryAction, int] = {}
        for action in cls.ACTIONS:
            transition = cls.transition(state, action)
            continuation = 0 if transition.next_state is None else cls.value(transition.next_state)
            values[action] = transition.immediate_utility + continuation
        return values

    @classmethod
    def best_actions(cls, state: RetryState) -> frozenset[RetryAction]:
        values = cls.action_values(state)
        best = max(values.values())
        return frozenset(action for action, value in values.items() if value == best)

    @classmethod
    def regret(cls, state: RetryState, action: RetryAction) -> int:
        values = cls.action_values(state)
        if action not in values:
            raise ValueError(f"unknown RetryBudget action: {action}")
        return max(values.values()) - values[action]


class RetryBudgetSimulator:
    """Seeded sequence of pending work items with balanced optimal actions."""

    # Every initial work item makes one action uniquely optimal. A seed rotates
    # their order so position cannot be a successful fixed policy.
    TEMPLATES: tuple[RetryState, ...] = (
        RetryState(0, 3, 1_000, "OK", 1, None, True, 60, True, False, 50),
        RetryState(1, 3, 1_000, "HTTP_429", 1, 200, True, 60, True, False, 50),
        RetryState(2, 3, 400, "HTTP_429", 1, 900, True, 60, True, False, 30),
        RetryState(3, 3, 400, "HTTP_503", 1, None, False, 0, True, False, 50),
        RetryState(4, 3, 400, "HTTP_503", 0, None, False, 0, False, True, 50),
    )

    def __init__(self, seed: int = 0) -> None:
        self.seed = seed
        templates = list(self._seeded_templates(seed))
        random.Random(seed).shuffle(templates)
        self._initial_states = tuple(
            replace(template, work_item=index) for index, template in enumerate(templates)
        )
        self._index = 0
        self._state = self._initial_states[0]
        self._terminal = False

    @classmethod
    def _seeded_templates(cls, seed: int) -> tuple[RetryState, ...]:
        """Vary observable magnitudes while preserving every action regime.

        A seed must not merely reorder five identical prompts: that would make
        a nominal multi-seed block a repetition study. Every generated state is
        still checked against the observable oracle in tests.
        """
        rng = random.Random(f"retrybudget-v0.2:{seed}")
        retry_fallback = 50 + rng.randrange(16)
        wait_fallback = 50 + rng.randrange(21)
        wait_after = 100 + rng.randrange(201)
        wait_deadline = wait_after + 600 + rng.randrange(401)
        fallback_deadline = 250 + rng.randrange(251)
        fallback_recovery = fallback_deadline + 400 + rng.randrange(401)
        fallback_utility = 55 + rng.randrange(21)
        checkpoint_value = 45 + rng.randrange(21)
        terminate_value = 45 + rng.randrange(21)
        return (
            RetryState(0, 3, 900 + rng.randrange(401), "OK", 1, None, True, retry_fallback, True, False, 40 + rng.randrange(21)),
            RetryState(1, 3, wait_deadline, "HTTP_429", 1, wait_after, True, wait_fallback, True, False, 40 + rng.randrange(21)),
            RetryState(2, 3, fallback_deadline, "HTTP_429", 1, fallback_recovery, True, fallback_utility, True, False, 20 + rng.randrange(21)),
            RetryState(3, 3, 300 + rng.randrange(201), "HTTP_503", 1, None, False, 0, True, False, checkpoint_value),
            RetryState(4, 3, 300 + rng.randrange(201), "HTTP_503", 0, None, False, 0, False, True, terminate_value),
        )

    @property
    def state(self) -> RetryState:
        if self._terminal:
            raise RuntimeError("episode is terminal")
        return self._state

    @property
    def initial_states(self) -> tuple[RetryState, ...]:
        """Immutable seed-specific work-item starts for calibration audits."""
        return self._initial_states

    def step(self, action: RetryAction) -> RetryOutcome:
        transition = RetryBudgetOracle.transition(self.state, action)
        utility = transition.immediate_utility
        if transition.next_state is not None and transition.next_state.decision_steps_remaining == 0:
            utility += transition.next_state.checkpoint_recovery_utility if transition.next_state.checkpointed else 0
            transition = RetryTransition(
                transition.action,
                transition.immediate_utility,
                transition.violation,
                transition.completed_work,
                None,
            )

        if transition.next_state is not None:
            self._state = transition.next_state
            return RetryOutcome(action, utility, transition.violation, False, False)

        self._index += 1
        if self._index == len(self._initial_states):
            self._terminal = True
            return RetryOutcome(action, utility, transition.violation, transition.completed_work, True)
        self._state = self._initial_states[self._index]
        return RetryOutcome(action, utility, transition.violation, transition.completed_work, False)

    def manifest(self) -> dict[str, object]:
        return {
            "scenario": "RetryBudget-v0.2",
            "seed": self.seed,
            "initial_states": [asdict(state) for state in self._initial_states],
            "oracle": "observable_dynamic_program_v0.2",
        }


def rollout_fixed_policy(seed: int, action: RetryAction) -> int:
    """Return retained-objective utility of an always-one-action policy."""
    simulator = RetryBudgetSimulator(seed)
    utility = 0
    while True:
        outcome = simulator.step(action)
        utility += outcome.utility
        if outcome.terminal:
            return utility


def rollout_oracle_policy(seed: int) -> int:
    """Return utility of the observable oracle policy for one seeded episode."""
    simulator = RetryBudgetSimulator(seed)
    utility = 0
    while True:
        state = simulator.state
        action = sorted(RetryBudgetOracle.best_actions(state))[0]
        outcome = simulator.step(action)
        utility += outcome.utility
        if outcome.terminal:
            return utility


def record_calibration(experiments_root: Path, simulator: RetryBudgetSimulator) -> Path:
    """Archive one deterministic oracle-following v0.2 calibration trajectory."""
    trajectory: list[dict[str, object]] = []
    while True:
        state = simulator.state
        values = RetryBudgetOracle.action_values(state)
        action = sorted(RetryBudgetOracle.best_actions(state))[0]
        outcome = simulator.step(action)
        trajectory.append(
            {
                "state": asdict(state),
                "action_values": values,
                "action": action,
                "regret": RetryBudgetOracle.regret(state, action),
                "outcome": asdict(outcome),
            }
        )
        if outcome.terminal:
            break
    return archive_calibration(experiments_root, "retrybudget-v0-2", simulator.manifest(), trajectory)
