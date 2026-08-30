from __future__ import annotations

import json
from pathlib import Path

from scac_harness.scenarios.toolroute import ToolRouteOracle, ToolRouteSimulator, record_calibration


def test_toolroute_is_deterministic_for_seed_and_actions() -> None:
    left = ToolRouteSimulator(seed=17)
    right = ToolRouteSimulator(seed=17)
    assert left.manifest() == right.manifest()
    action = next(iter(ToolRouteOracle.best_actions(left.state)))
    assert left.step(action) == right.step(action)


def test_toolroute_oracle_penalizes_degraded_route() -> None:
    sim = ToolRouteSimulator(seed=3)
    # Turn zero is equal health; turn one has a deliberately degraded route.
    sim.step("wait")
    state = sim.state
    best = ToolRouteOracle.best_actions(state)
    worse = next(name for name in state.health if name not in best)
    assert ToolRouteOracle.regret(state, worse) > 0
    assert ToolRouteOracle.regret(state, next(iter(best))) == 0


def test_toolroute_wait_has_missed_record_cost() -> None:
    sim = ToolRouteSimulator(seed=3)
    assert ToolRouteOracle.regret(sim.state, "wait") > 0


def test_observable_oracle_uses_only_monitor_fields() -> None:
    snapshot = {"tools": {
        "tool_alpha": {"window_n": 6, "successes": 1, "latency_ewma_ms": 4_200.0, "circuit": "OPEN"},
        "tool_beta": {"window_n": 6, "successes": 6, "latency_ewma_ms": 180.0, "circuit": "CLOSED"},
    }}
    assert ToolRouteOracle.observable_best_actions(snapshot) == {"tool_beta"}
    assert ToolRouteOracle.observable_regret(snapshot, "tool_beta") == 0
    assert ToolRouteOracle.observable_regret(snapshot, "tool_alpha") > 0
    assert ToolRouteOracle.observable_margin(snapshot) > 50


def test_toolroute_tool_name_swap_does_not_change_regime_costs() -> None:
    first = ToolRouteSimulator(seed=11, tool_names=("remote_a", "local_b"))
    swapped = ToolRouteSimulator(seed=11, tool_names=("local_b", "remote_a"))
    first_costs = sorted(ToolRouteOracle.expected_cost(v) for v in first.state.health.values())
    swapped_costs = sorted(ToolRouteOracle.expected_cost(v) for v in swapped.state.health.values())
    assert first_costs == swapped_costs


def test_toolroute_calibration_is_archived_before_actions(tmp_path: Path) -> None:
    sim = ToolRouteSimulator(seed=5)
    record = record_calibration(tmp_path, sim)
    assert json.loads((record / "manifest.json").read_text())["seed"] == 5
    assert len(json.loads((record / "trajectory.json").read_text())) == 4
