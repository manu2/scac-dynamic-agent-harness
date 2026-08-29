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


def test_next_turn_resume_restores_delta_linkage(tmp_path: Path) -> None:
    trial = ToolRouteDevelopmentTrial(10, "C", tmp_path)
    trial.next_turn()
    trial.submit("wait")
    resumed = ToolRouteDevelopmentTrial.resume_for_next_turn(trial.directory)
    second = resumed.next_turn()
    assert second.turn == 1
    assert second.snapshot is not None and second.snapshot["kind"] == "delta"
    host = __import__("json").loads((trial.directory / "turn-01-host.json").read_text())
    assert host["cumulative_snapshot"]["hardware"]["memory"]["state"] == "UNKNOWN"


def test_terminal_record_includes_completion_and_finalization(tmp_path: Path) -> None:
    trial = ToolRouteDevelopmentTrial(1, "A", tmp_path)
    for action in ("tool_alpha", "tool_alpha", "tool_alpha"):
        trial.next_turn()
        result = trial.submit(action)
        if result["terminal"]:
            break
    assert result["task_completed"] is True
    assert (trial.directory / "finalization.json").exists()


def test_prose_response_fails_closed(tmp_path: Path) -> None:
    trial = ToolRouteDevelopmentTrial(42, "A", tmp_path)
    trial.next_turn()
    try:
        trial.submit("tool_beta", response_text="I refuse tool_alpha and choose tool_beta")
    except ValueError:
        pass
    else:
        raise AssertionError("conversational prose must be rejected")


def test_option_orders_are_balanced_across_six_seed_block(tmp_path: Path) -> None:
    orders = [ToolRouteDevelopmentTrial(seed, "A", tmp_path)._option_order() for seed in range(6)]
    for action in ("tool_alpha", "tool_beta", "wait"):
        assert [order.index(action) for order in orders].count(0) == 2
        assert [order.index(action) for order in orders].count(1) == 2
        assert [order.index(action) for order in orders].count(2) == 2


def test_v4_monitor_probes_are_independent_of_action_outcome_namespace(tmp_path: Path) -> None:
    trial = ToolRouteDevelopmentTrial(3, "C", tmp_path)
    turn = trial.next_turn()
    host = __import__("json").loads((trial.directory / "turn-00-host.json").read_text())
    assert len(host["raw_events"]) == 6
    assert "HOST_CONSTRAINTS" not in turn.message
    assert "primary_oracle" in __import__("json").loads((trial.directory / "manifest.json").read_text())


def test_v4_calibration_passes_across_three_seed_block(tmp_path: Path) -> None:
    for seed in (24, 25, 26):
        trial = ToolRouteDevelopmentTrial(seed, "C", tmp_path)
        while True:
            turn = trial.next_turn()
            assert turn.snapshot is not None
            from scac_harness.scenarios.toolroute import ToolRouteOracle
            action = next(iter(ToolRouteOracle.observable_best_actions(trial._prior_snapshot)))  # type: ignore[arg-type]
            result = trial.submit(action)
            if result["terminal"]:
                break
