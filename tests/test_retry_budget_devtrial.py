from __future__ import annotations

import json
from pathlib import Path

from scac_harness.retry_budget_devtrial import RetryBudgetDevelopmentTrial
from scac_harness.scenarios.retry_budget import RetryBudgetOracle


def test_conditions_hold_initial_host_state_constant_and_b_matches_c_envelope(tmp_path: Path) -> None:
    trials = {condition: RetryBudgetDevelopmentTrial(12, condition, tmp_path) for condition in ("A", "B", "C")}
    turns = {condition: trial.next_turn() for condition, trial in trials.items()}
    c_host = json.loads((trials["C"].directory / "turn-00-host.json").read_text())
    assert "HOST-OWNED RETRYBUDGET STATE" not in turns["A"].message
    assert "primary_status=NEUTRAL" in turns["B"].message
    assert "primary_status=" + str(c_host["state"]["primary_status"]) in turns["C"].message
    b_fields = [line.split("=", 1)[0] for line in turns["B"].message.splitlines() if "=" in line]
    c_fields = [line.split("=", 1)[0] for line in turns["C"].message.splitlines() if "=" in line]
    assert b_fields == c_fields


def test_recorded_trial_resumes_at_pending_action(tmp_path: Path) -> None:
    trial = RetryBudgetDevelopmentTrial(7, "C", tmp_path)
    trial.next_turn()
    resumed = RetryBudgetDevelopmentTrial.resume_for_submission(trial.directory)
    action = sorted(RetryBudgetOracle.best_actions(resumed._simulator.state))[0]
    assert resumed.submit(action, subject_id="fresh-1", response_text=action)["action"] == action


def test_oracle_following_trial_finalizes_with_valid_hash_set(tmp_path: Path) -> None:
    trial = RetryBudgetDevelopmentTrial(3, "C", tmp_path)
    while True:
        turn = trial.next_turn()
        action = sorted(RetryBudgetOracle.best_actions(trial._simulator.state))[0]
        result = trial.submit(action, subject_id="oracle-development", response_text=action)
        assert result["policy_regret"] == 0
        if result["terminal"]:
            break
        trial = RetryBudgetDevelopmentTrial.resume_for_next_turn(trial.directory)
    finalization = json.loads((trial.directory / "finalization.json").read_text())
    assert finalization["classification"] == "COMPLETED"
    assert set(finalization["artifact_sha256"]) == {
        path.name for path in trial.directory.glob("*.json") if path.name != "finalization.json"
    }


def test_prose_response_fails_closed(tmp_path: Path) -> None:
    trial = RetryBudgetDevelopmentTrial(2, "A", tmp_path)
    trial.next_turn()
    try:
        trial.submit("retry", subject_id="fresh-1", response_text="I choose retry")
    except ValueError:
        pass
    else:
        raise AssertionError("conversational prose must be rejected")
