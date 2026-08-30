from __future__ import annotations

import pytest

from scac_harness.retry_budget_observation import (
    RetryBudgetObservationModel,
    build_prompt,
    observable_projection,
    prompt_record,
)
from scac_harness.scenarios.retry_budget import RetryBudgetOracle, RetryBudgetSimulator


def _state() -> object:
    return RetryBudgetSimulator.TEMPLATES[1]


def test_b_and_c_have_identical_field_envelope_and_option_order() -> None:
    state = _state()
    b = prompt_record(condition="B", seed=9, state=state)  # type: ignore[arg-type]
    c = prompt_record(condition="C", seed=9, state=state)  # type: ignore[arg-type]
    assert b["option_order"] == c["option_order"]
    b_lines = [line.split("=", 1)[0] for line in str(b["prompt"]).splitlines() if "=" in line]
    c_lines = [line.split("=", 1)[0] for line in str(c["prompt"]).splitlines() if "=" in line]
    assert b_lines == c_lines
    assert "primary_status=NEUTRAL" in str(b["prompt"])
    assert "primary_status=HTTP_429" in str(c["prompt"])


def test_a_has_no_host_state_and_c_exposes_oracle_inputs() -> None:
    state = _state()
    a = build_prompt(condition="A", seed=1, state=state)  # type: ignore[arg-type]
    c = prompt_record(condition="C", seed=1, state=state)  # type: ignore[arg-type]
    assert "HOST-OWNED RETRYBUDGET STATE" not in a
    projection = c["visible_projection"]
    assert isinstance(projection, dict)
    assert set(RetryBudgetOracle.action_values(state)) == set(RetryBudgetOracle.ACTIONS)
    assert projection["primary_status"] == state.primary_status
    assert projection["retry_after_ms"] == state.retry_after_ms
    assert projection["checkpoint_recovery_utility"] == state.checkpoint_recovery_utility
    assert "work_item" not in projection


def test_option_positions_are_balanced_across_five_adjacent_seeds() -> None:
    state = _state()
    positions = {action: set() for action in RetryBudgetOracle.ACTIONS}
    for seed in range(5):
        options = prompt_record(condition="A", seed=seed, state=state)["option_order"]
        assert isinstance(options, list)
        for index, action in enumerate(options):
            positions[action].add(index)
    assert all(seen == set(range(len(RetryBudgetOracle.ACTIONS))) for seen in positions.values())


def test_uncalibrated_observation_noise_fails_closed() -> None:
    with pytest.raises(NotImplementedError, match="not calibrated"):
        observable_projection(
            _state(), RetryBudgetObservationModel(missing_field_probability=0.1)
        )
    with pytest.raises(ValueError, match="delivery delay"):
        RetryBudgetObservationModel(delivery_delay_ms=1)
