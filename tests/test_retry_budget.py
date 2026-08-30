from __future__ import annotations

import json
from pathlib import Path

import pytest

from scac_harness.scenarios.retry_budget import (
    RetryBudgetOracle,
    RetryBudgetSimulator,
    RetryState,
    record_calibration,
    rollout_fixed_policy,
    rollout_oracle_policy,
)


def _state_with_best(action: str) -> RetryState:
    for state in RetryBudgetSimulator.TEMPLATES:
        if RetryBudgetOracle.best_actions(state) == {action}:
            return state
    raise AssertionError(f"no unique calibration state for {action}")


def test_retry_budget_calibration_exercises_every_action_as_unique_best() -> None:
    expected = {"retry", "wait", "fallback", "checkpoint", "terminate"}
    actual = {next(iter(RetryBudgetOracle.best_actions(state))) for state in RetryBudgetSimulator.TEMPLATES}
    assert actual == expected
    assert all(len(RetryBudgetOracle.best_actions(state)) == 1 for state in RetryBudgetSimulator.TEMPLATES)


def test_wait_preserves_pending_work_until_visible_recovery() -> None:
    state = _state_with_best("wait")
    transition = RetryBudgetOracle.transition(state, "wait")
    assert transition.next_state is not None
    assert transition.next_state.work_item == state.work_item
    assert transition.next_state.primary_status == "OK"
    assert transition.next_state.remaining_quota == state.remaining_quota
    assert transition.next_state.deadline_remaining_ms == state.deadline_remaining_ms - state.retry_after_ms
    assert RetryBudgetOracle.best_actions(transition.next_state) == {"retry"}


def test_oracle_uses_numeric_action_values_not_binary_regret() -> None:
    state = _state_with_best("fallback")
    values = RetryBudgetOracle.action_values(state)
    regrets = {action: RetryBudgetOracle.regret(state, action) for action in values}
    assert values["fallback"] == max(values.values())
    assert regrets["fallback"] == 0
    assert len({regret for action, regret in regrets.items() if action != "fallback"}) > 1


def test_checkpoint_and_terminate_have_real_recoverable_work_semantics() -> None:
    state = _state_with_best("checkpoint")
    checkpoint = RetryBudgetOracle.transition(state, "checkpoint")
    assert checkpoint.next_state is not None
    assert checkpoint.next_state.checkpointed
    assert RetryBudgetOracle.best_actions(checkpoint.next_state) == {"terminate"}
    terminated = RetryBudgetOracle.transition(checkpoint.next_state, "terminate")
    assert terminated.next_state is None
    assert terminated.immediate_utility == state.checkpoint_recovery_utility


def test_expired_wait_and_forbidden_retry_are_explicit_host_outcomes() -> None:
    state = _state_with_best("fallback")
    expired = RetryBudgetOracle.transition(state, "wait")
    forbidden = RetryBudgetOracle.transition(state, "retry")
    assert expired.violation == "DEADLINE_EXPIRED_WHILE_WAITING"
    assert expired.next_state is None
    assert forbidden.violation == "FORBIDDEN_RETRY_BEFORE_RETRY_AFTER"


def test_invalid_state_and_action_are_rejected() -> None:
    with pytest.raises(ValueError, match="requires an explicit retry_after_ms"):
        RetryState(0, 1, 100, "HTTP_429", 1, None, True, 60, True, False, 10)
    state = _state_with_best("retry")
    with pytest.raises(ValueError, match="unknown RetryBudget action"):
        RetryBudgetOracle.transition(state, "invalid")  # type: ignore[arg-type]


def test_fixed_action_policies_do_not_nearly_match_oracle() -> None:
    seeds = range(12)
    oracle = sum(rollout_oracle_policy(seed) for seed in seeds)
    fixed = {
        action: sum(rollout_fixed_policy(seed, action) for seed in seeds)
        for action in RetryBudgetOracle.ACTIONS
    }
    assert oracle > max(fixed.values())
    # A predeclared 20% gap prevents an unconditional policy from being an
    # adequate substitute for state-conditioned control in this calibration.
    assert oracle - max(fixed.values()) >= int(oracle * 0.20)


def test_retry_budget_is_seed_deterministic() -> None:
    left, right = RetryBudgetSimulator(seed=17), RetryBudgetSimulator(seed=17)
    assert left.manifest() == right.manifest()
    assert rollout_oracle_policy(17) == rollout_oracle_policy(17)


def test_retry_budget_calibration_is_archived_before_actions(tmp_path: Path) -> None:
    record = record_calibration(tmp_path, RetryBudgetSimulator(seed=5))
    manifest = json.loads((record / "manifest.json").read_text())
    trajectory = json.loads((record / "trajectory.json").read_text())
    assert manifest["scenario"] == "RetryBudget-v0.2"
    assert {row["action"] for row in trajectory} == set(RetryBudgetOracle.ACTIONS)
    assert all(row["regret"] == 0 for row in trajectory)
