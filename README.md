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
paper/                   ToolRoute manuscript, derived analysis, and figures
output/pdf/              formatted ToolRoute final-review proof
```

## Current status

Gate G0 (Specification & Threat Model) is complete. ToolRoute v1.0 collection
is complete as a narrow synthetic API study: independent full-checkpoint
episodes, an observable-only primary oracle, reservation-first artifact capture,
and finalization hashes. Fresh-context subagent artifacts and the optional
Toxiproxy adapter are retained development diagnostics—not empirical evidence.

The selected first-paper cohort is GPT-5.6 Sol, Claude Sonnet 5, and Gemini
3.7 Flash. The frozen six-seed cohort is complete: 216 independent decisions
are retained under `experiments/api-paper-v1.0-seed8/`,
`experiments/api-paper-v1.0-seeds9-10/`, and
`experiments/api-paper-v1.0-seeds11-13/`. Authorization is deliberately
revoked. An audit found that the
manifest's "sampling controls omitted" wording does not match the recorded
Gemini requests, which explicitly use `temperature: 0.0`. This is a
documentation deviation, not a condition confound: all Gemini A/B/C decisions
use the same captured parameter. The completed cohort used
`temperature: 0.0` for Gemini throughout. This narrow ToolRoute work does not close G1
globally or apply to MemoryGovernor, RetryBudget, or a combined study. See
`docs/17_toolroute_v1_execution_config_clarification.md`.

## OTel/Toxiproxy transport replication (separate pre-provider path)

`scripts/run_toolroute_otel_transport_calibration.py` is a model-free,
socket-backed integration calibration. It instruments two local HTTP routes
with standard OpenTelemetry Requests client spans, injects a predeclared
latency, connection-error, or HTTP-error regime through Toxiproxy, reduces only
the span facts into the existing host snapshot, and executes the selected route
through the same still-live proxy. It archives raw spans, reducer events,
condition inputs, action result, and finalization hashes under
`experiments/g2-calibrations/toolroute-otel-transport/`.

This is a distinct integration replication, not an alteration of or addition
to the 216-decision ToolRoute v1.0 cohort. The provider command is deliberately
blocked by the separate false provenance flag except during a reviewed,
hash-bound execution window. The frozen v0.2 transport-replication manifest is
being collected in audited stages: nine of its 27 independent episodes (three
per provider) are retained under
`experiments/api-otel-transport-v0.2/g2-calibrations/toolroute-otel-transport/`.
Authorization is currently revoked; those partial results are not a completed
cross-model effect estimate. See
`docs/24_otel_transport_replication_research_note.md`.

## ToolRoute manuscript review package

The reproducible ToolRoute manuscript, frozen-cohort analysis, and source
figures are documented in `paper/README.md`. The shareable review proof is
`output/pdf/toolroute_arxiv_review_draft.pdf`: a four-page formatted artifact
for manual review, not yet an arXiv source bundle.
