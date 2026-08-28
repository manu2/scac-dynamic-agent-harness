from __future__ import annotations

from pathlib import Path

from scac_harness.devtrial import ToolRouteDevelopmentTrial


def test_conditions_hold_fault_tape_constant_and_b_matches_c_bytes(tmp_path: Path) -> None:
    trials = {c: ToolRouteDevelopmentTrial(42, c, tmp_path) for c in ("A", "B", "C")}
    turns = {c: trial.next_turn() for c, trial in trials.items()}
    assert turns["A"].state.health == turns["B"].state.health == turns["C"].state.health
    assert len(turns["B"].message.encode()) == len(turns["C"].message.encode())
    assert "4200" not in turns["A"].message and "4200" not in turns["B"].message
    assert "HOST TELEMETRY" in turns["C"].message


def test_potential_outcomes_do_not_depend_on_action_history(tmp_path: Path) -> None:
    alpha = ToolRouteDevelopmentTrial(7, "A", tmp_path)
    beta = ToolRouteDevelopmentTrial(7, "B", tmp_path)
    alpha.next_turn(); beta.next_turn()
    alpha.submit("tool_alpha"); beta.submit("wait")
    next_alpha, next_beta = alpha.next_turn(), beta.next_turn()
    assert next_alpha.state.health == next_beta.state.health


def test_recorded_trial_can_resume_only_at_pending_action(tmp_path: Path) -> None:
    trial = ToolRouteDevelopmentTrial(9, "A", tmp_path)
    trial.next_turn()
    resumed = ToolRouteDevelopmentTrial.resume_for_submission(trial.directory)
    assert resumed.submit("tool_alpha")["action"] == "tool_alpha"
