# SCAC Dynamic Agent Harness

An experimental harness for testing whether fresh, host-verified execution
telemetry improves the decisions of multi-turn, tool-using LLM agents under
resource pressure, tool degradation, and quota exhaustion.

## Research boundary

This repository is the dynamic follow-on to the static execution-contract study
in [Context-Aware-Agent-Experiment](https://github.com/manu2/Context-Aware-Agent-Experiment).
The studies have different experimental units and must remain separately labelled.
No Phase 1 raw artifact is copied or pooled here.

The pinned design basis is recorded in `PROVENANCE.json`.

## Core loop

```text
enforced environment -> raw event log -> deterministic reducer
       ^                                      |
       |                                      v
 action executor <- model decision <- versioned SST snapshot
       |
       v
 external oracle and trajectory audit
```

## Initial scenarios

- **ToolRoute:** select among equivalent tools under seeded latency and failure
  regimes.
- **MemoryGovernor:** adjust chunk and worker controls under changing cgroup v2
  pressure.
- **RetryBudget:** choose retry, wait, fallback, checkpoint, or termination under
  service and quota degradation.

## Repository layout

```text
src/scac_harness/        collector, reducer, renderer, runner, schemas
scenarios/               deterministic scenario definitions and oracles
tests/                   unit, schema, enforcement, and reproducibility tests
experiments/             immutable calibration and trial artifacts
docs/                    design reviews and empirical reports
```

## Current status

Design scaffold only. No provider trials are authorized. Begin with G0 schema and
threat-model fixtures, followed by local G1 positive controls and G2 deterministic
scenario calibration.
