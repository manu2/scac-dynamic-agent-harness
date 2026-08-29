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

Gate G0 (Specification & Threat Model) is complete on branch
`codex/g0-sst-schema`. ToolRoute v0.4 has passed local engineering checks with
fresh-context subagents: independent monitor probes, an observable-only primary
oracle, condition-input/output capture, and verified terminal hashes. These are
unblinded development diagnostics—not empirical evidence—and do not establish a
telemetry effect. Gate G1 collector and positive-control code is implemented.
Timeout and deterministic tool-fault controls pass locally; cgroup-v2 memory
enforcement must be demonstrated on a delegated Linux cgroup-v2 runner before
G1 can close. Provider trials remain unauthorized. A narrow ToolRoute-only API
pilot may proceed before that Linux proof only after its full-checkpoint,
isolated-runner, tokenizer, observation-calibration, evaluator-defeat,
frozen-manifest, and provenance-binding requirements pass; this exception does
not apply to MemoryGovernor, RetryBudget, or a combined study. The current
ToolRoute risks and next actions are in
`docs/10_toolroute_v0_4_status_and_next_gate.md` and
`docs/13_toolroute_api_and_toxiproxy_preflight.md`.
