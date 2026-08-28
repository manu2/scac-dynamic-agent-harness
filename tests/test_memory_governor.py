from __future__ import annotations

from scac_harness.scenarios.memory_governor import MemoryGovernorOracle, MemoryGovernorSimulator


def test_memory_oracle_reduces_parallelism_under_pressure() -> None:
    sim = MemoryGovernorSimulator()
    assert max(a.chunk_bytes * a.workers for a in MemoryGovernorOracle.best_actions(sim.state)) == 512
    sim.step(next(iter(MemoryGovernorOracle.best_actions(sim.state))))
    assert max(a.chunk_bytes * a.workers for a in MemoryGovernorOracle.best_actions(sim.state)) == 256


def test_memory_violation_is_external_and_terminal() -> None:
    sim = MemoryGovernorSimulator()
    unsafe = max(MemoryGovernorOracle.ACTIONS, key=lambda a: a.chunk_bytes * a.workers)
    sim.step(next(iter(MemoryGovernorOracle.best_actions(sim.state))))
    outcome = sim.step(unsafe)
    assert outcome.violation == "VIRTUAL_MEMORY_LIMIT"
    assert outcome.terminal is True
