# Research Roadmap: Dynamic SCAC

## Objective

Determine whether supplying a small, truthful, fresh, host-verified telemetry
state before consequential decisions improves correct operational completion in
multi-turn agent trajectories.

## 4D state and provenance model

The versioned state contains:

1. **Hardware:** memory usage/headroom/events/PSI, CPU quota/throttling/PSI,
   ephemeral disk, processes, and optional GPU state.
2. **Tools:** true sliding-window history buffer, success/failure counts, consecutive
   failures, EWMA latency estimator, retry-after, and circuit state.
3. **Runtime:** wall-time budget, exit classification, thread/PID state, and
   execution policy.
4. **Economics:** token headroom/usage, rate limits, cost, and remaining budget.

Every snapshot enforces:
- RFC 8785 (JSON Canonicalization Scheme) deterministic SHA-256 identity hashing.
- Explicit field-level derivation provenance linking derived state to raw event hashes.
- True unavailability representation: missing or unobserved metrics are never fabricated as zero or healthy defaults.
- Monotonic sequence numbers and observation timestamps.

## Gates

- **G0 — specification (Complete):** freeze SST v0.1 JSON Schema Draft 2020-12,
  RFC 8785 canonicalization, sliding-window deterministic reducer, compact renderer,
  trust boundaries, and comprehensive invariant test suite.
- **G1 — enforcement (In progress):** cgroup-v2 collector and host-owned positive
  controls are implemented. Timeout and deterministic tool-fault controls pass
  locally; the cgroup-v2 memory OOM-kill positive control is blocked pending a
  delegated Linux cgroup-v2 runner and cannot be substituted with a host limit.
- **G2 — scenarios (In progress):** seeded, model-free ToolRoute,
  MemoryGovernor, and RetryBudget simulators plus external oracles are locally
  calibrated without model calls. The local MemoryGovernor is explicitly virtual
  and makes no cgroup-enforcement claim. Clean-container reproduction and
  context-isolated leakage/evaluator-defeat reviews remain pending.
- **Development smoke path:** offline A/B/C ToolRoute messages may be supplied to
  fresh-context Codex subagents after complete host-side capture. These are
  engineering smoke tests only: shared workspace access prevents them from being
  blinded empirical trials or inclusion in a study denominator.
- **G3 — pilot:** one configured model; A/B/C conditions; natural-language subset.
- **G4 — main study:** powered, randomized, frozen multi-model execution with sample size determined by simulation from pilot base rates and minimum detectable effect.
- **G5 — extensions:** GPU pressure, shared multi-agent resources, real outages,
  and telemetry-poisoning robustness under separate protocols.

## Repository boundary

The static-contract repository remains the evidence and manuscript anchor for
Phase 1. This repository owns Phase 2 code, containers, simulators, manifests,
and raw trajectories. Reciprocal commit/release pins preserve lineage without
mixing denominators.
