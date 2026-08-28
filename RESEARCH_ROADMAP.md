# Research Roadmap: Dynamic SCAC

## Objective

Determine whether supplying a small, truthful, fresh, host-verified telemetry
state before consequential decisions improves correct operational completion in
multi-turn agent trajectories.

## 4D state

The versioned state contains:

1. **Hardware:** memory usage/headroom/events/PSI, CPU quota/throttling/PSI,
   ephemeral disk, processes, and optional GPU state.
2. **Tools:** recent outcomes, consecutive failures, latency estimator,
   retry-after, and circuit state.
3. **Runtime:** wall-time budget, exit classification, thread/PID state, and
   execution policy.
4. **Economics:** token headroom/usage, rate limits, cost, and remaining budget.

Every value records provenance, observation time, window, availability, and
freshness. Missing is never encoded as zero.

## Gates

- **G0 — specification:** freeze SST v0.1, trust boundaries, renderer, hypotheses,
  metrics, and analysis skeleton.
- **G1 — enforcement:** implement collectors and fail-closed memory, timeout, and
  tool-fault positive controls.
- **G2 — scenarios:** implement deterministic ToolRoute, MemoryGovernor, and
  RetryBudget simulators, external oracles, and context-isolated reviews.
- **G3 — pilot:** one configured model; A/B/C conditions; natural-language subset.
- **G4 — main study:** powered, randomized, frozen multi-model execution.
- **G5 — extensions:** GPU pressure, shared multi-agent resources, real outages,
  and telemetry-poisoning robustness under separate protocols.

## Repository boundary

The static-contract repository remains the evidence and manuscript anchor for
Phase 1. This repository owns Phase 2 code, containers, simulators, manifests,
and raw trajectories. Reciprocal commit/release pins preserve lineage without
mixing denominators.
