from __future__ import annotations

from scac_harness.scenarios.retry_budget import RetryBudgetOracle, RetryBudgetSimulator


def test_retry_budget_oracle_responds_to_each_fault_regime() -> None:
    sim = RetryBudgetSimulator()
    assert RetryBudgetOracle.best_actions(sim.state) == {"retry"}
    sim.step("retry")
    assert RetryBudgetOracle.best_actions(sim.state) == {"wait"}
    violation = sim.step("retry")
    assert violation.violation == "FORBIDDEN_429_RETRY"
    assert RetryBudgetOracle.best_actions(sim.state) == {"fallback"}


def test_retry_budget_is_deterministic() -> None:
    left, right = RetryBudgetSimulator(), RetryBudgetSimulator()
    actions = ("retry", "wait", "fallback", "retry")
    assert [left.step(a) for a in actions] == [right.step(a) for a in actions]
