"""Deterministic ToolRoute calibration environment and external action oracle.

The simulator deliberately owns the health schedule and score.  Agents can only
choose a tool name or wait; neither a model nor a tool result can alter the
schedule, expected costs, or oracle.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import random
from typing import Literal


Action = Literal["wait"] | str


@dataclass(frozen=True)
class ToolHealth:
    success_probability: float
    latency_ms: int
    retry_after_ms: int | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.success_probability <= 1.0:
            raise ValueError("success_probability must be in [0, 1]")
        if self.latency_ms < 0:
            raise ValueError("latency_ms must be non-negative")


@dataclass(frozen=True)
class ToolRouteState:
    turn: int
    health: dict[str, ToolHealth]


@dataclass(frozen=True)
class ToolRouteOutcome:
    action: Action
    turn: int
    success: bool
    latency_ms: int
    error_class: str | None
    policy_regret: float
    terminal: bool


class ToolRouteOracle:
    """External expected-cost oracle for functionally equivalent tools."""

    FAILURE_PENALTY_MS = 10_000
    MISSED_RECORD_PENALTY_MS = 10_000
    WAIT_LATENCY_MS = 500

    @classmethod
    def expected_cost(cls, health: ToolHealth) -> float:
        # Lower is better; failed calls cost their latency plus a fixed recovery
        # penalty, defined before any trajectory runs.
        return health.latency_ms + (1.0 - health.success_probability) * cls.FAILURE_PENALTY_MS

    @classmethod
    def best_actions(cls, state: ToolRouteState) -> frozenset[str]:
        costs = {name: cls.expected_cost(health) for name, health in state.health.items()}
        minimum = min(costs.values())
        return frozenset(name for name, cost in costs.items() if cost == minimum)

    @classmethod
    def regret(cls, state: ToolRouteState, action: Action) -> float:
        best = min(cls.expected_cost(health) for health in state.health.values())
        if action == "wait":
            # ToolRoute has one required record per decision interval. Waiting
            # intentionally does not retrieve it, so it incurs the predeclared
            # missed-record penalty rather than being treated as a free escape.
            return float(cls.WAIT_LATENCY_MS + cls.MISSED_RECORD_PENALTY_MS - best)
        if action not in state.health:
            raise ValueError(f"unknown ToolRoute action: {action}")
        return cls.expected_cost(state.health[action]) - best

    @classmethod
    def observable_expected_cost(cls, tool: dict[str, object]) -> float:
        """Cost estimate from canonical monitor facts, never latent health.

        These are precisely the fields rendered in Tier 2: window size,
        successes, latency EWMA, and circuit state.  It is the primary oracle
        for ToolRoute v0.4; ``expected_cost`` remains a clairvoyant diagnostic.
        """
        window = int(tool.get("window_n", 0))
        successes = int(tool.get("successes", 0))
        failure_rate = 0.5 if window == 0 else (window - successes) / window
        latency = float(tool.get("latency_ewma_ms", 0.0))
        cost = latency + failure_rate * cls.FAILURE_PENALTY_MS
        if tool.get("circuit") == "OPEN":
            cost += cls.MISSED_RECORD_PENALTY_MS
        return cost

    @classmethod
    def observable_best_actions(cls, snapshot: dict[str, object]) -> frozenset[str]:
        tools = snapshot.get("tools")
        if not isinstance(tools, dict) or not tools:
            raise ValueError("observable ToolRoute oracle requires monitor tool state")
        costs = {str(name): cls.observable_expected_cost(value) for name, value in tools.items() if isinstance(value, dict)}
        minimum = min(costs.values())
        return frozenset(name for name, cost in costs.items() if cost == minimum)

    @classmethod
    def observable_regret(cls, snapshot: dict[str, object], action: Action) -> float:
        tools = snapshot["tools"]
        assert isinstance(tools, dict)
        costs = {str(name): cls.observable_expected_cost(value) for name, value in tools.items() if isinstance(value, dict)}
        best = min(costs.values())
        if action == "wait":
            return float(cls.WAIT_LATENCY_MS + cls.MISSED_RECORD_PENALTY_MS - best)
        if action not in costs:
            raise ValueError(f"unknown ToolRoute action: {action}")
        return costs[action] - best

    @classmethod
    def observable_margin(cls, snapshot: dict[str, object]) -> float:
        tools = snapshot["tools"]
        assert isinstance(tools, dict)
        costs = sorted(cls.observable_expected_cost(value) for value in tools.values() if isinstance(value, dict))
        if len(costs) < 2:
            raise ValueError("observable ToolRoute oracle requires two tools")
        return costs[1] - costs[0]


class ToolRouteSimulator:
    """Seeded finite schedule for local, reproducible ToolRoute calibration."""

    def __init__(self, seed: int, tool_names: tuple[str, str] = ("remote_a", "local_b")) -> None:
        if len(tool_names) != 2 or len(set(tool_names)) != 2:
            raise ValueError("ToolRoute requires exactly two distinct tool names")
        self.seed = seed
        self.tool_names = tool_names
        self._rng = random.Random(seed)
        self._schedule = self._build_schedule()
        self._turn = 0
        self._terminal = False

    def _build_schedule(self) -> tuple[dict[str, ToolHealth], ...]:
        # The regimes are intentionally fixed and name-independent. A seeded
        # rotation decides which equivalent endpoint receives each regime.
        regimes = (
            (ToolHealth(0.98, 100), ToolHealth(0.98, 100)),
            (ToolHealth(0.20, 4_200, 2_000), ToolHealth(0.99, 180)),
            (ToolHealth(0.80, 800), ToolHealth(0.99, 180)),
            (ToolHealth(0.99, 180), ToolHealth(0.20, 4_200, 2_000)),
        )
        schedule: list[dict[str, ToolHealth]] = []
        for left, right in regimes:
            if self._rng.randrange(2):
                left, right = right, left
            schedule.append({self.tool_names[0]: left, self.tool_names[1]: right})
        return tuple(schedule)

    @property
    def state(self) -> ToolRouteState:
        if self._terminal:
            raise RuntimeError("episode is terminal")
        return ToolRouteState(self._turn, dict(self._schedule[self._turn]))

    def step(self, action: Action) -> ToolRouteOutcome:
        state = self.state
        regret = ToolRouteOracle.regret(state, action)
        if action == "wait":
            outcome = ToolRouteOutcome(action, state.turn, False, 500, None, regret, False)
        else:
            health = state.health[action]
            # Separate per-turn draw makes outcomes deterministic for a fixed
            # seed and action sequence, while health itself remains exogenous.
            success = self._rng.random() < health.success_probability
            outcome = ToolRouteOutcome(
                action,
                state.turn,
                success,
                health.latency_ms,
                None if success else "HTTP_503",
                regret,
                False,
            )
        # One call retrieves one of several required records. A successful call
        # must not erase later health transitions from the calibration episode.
        self._terminal = self._turn == len(self._schedule) - 1
        if self._terminal:
            outcome = ToolRouteOutcome(
                outcome.action,
                outcome.turn,
                outcome.success,
                outcome.latency_ms,
                outcome.error_class,
                outcome.policy_regret,
                True,
            )
        if not self._terminal:
            self._turn += 1
        return outcome

    def manifest(self) -> dict[str, object]:
        """Return a serializable, name-explicit schedule for immutable artifacts."""
        return {
            "scenario": "ToolRoute-v0.1",
            "seed": self.seed,
            "tool_names": list(self.tool_names),
            "schedule": [{name: asdict(health) for name, health in turn.items()} for turn in self._schedule],
        }


def record_calibration(
    experiments_root: Path,
    simulator: ToolRouteSimulator,
    actions: list[Action] | None = None,
) -> Path:
    """Run and immutably archive one model-free ToolRoute calibration.

    The directory is reserved before the first action. The caller receives the
    artifact path only after its manifest and complete action log are written.
    """
    parent = Path(experiments_root) / "g2-calibrations"
    parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    from uuid import uuid4

    directory = parent / f"{stamp}-toolroute-{uuid4().hex}"
    directory.mkdir(mode=0o700)
    with (directory / "manifest.json").open("x", encoding="utf-8") as handle:
        json.dump(simulator.manifest(), handle, indent=2, sort_keys=True)
        handle.write("\n")

    records: list[dict[str, object]] = []
    action_index = 0
    while True:
        state = simulator.state
        if actions is None:
            action = sorted(ToolRouteOracle.best_actions(state))[0]
        else:
            if action_index >= len(actions):
                raise ValueError("action sequence ended before terminal ToolRoute state")
            action = actions[action_index]
            action_index += 1
        outcome = simulator.step(action)
        records.append({"state": {"turn": state.turn, "health": {k: asdict(v) for k, v in state.health.items()}}, "action": action, "outcome": asdict(outcome)})
        if outcome.terminal:
            break
    with (directory / "trajectory.json").open("x", encoding="utf-8") as handle:
        json.dump(records, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return directory
