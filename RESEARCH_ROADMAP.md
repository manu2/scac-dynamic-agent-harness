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
- **G1 — enforcement:** implement collectors and fail-closed memory, timeout, and
  tool-fault positive controls.
- **G2 — scenarios:** implement deterministic ToolRoute, MemoryGovernor, and
  RetryBudget simulators, external oracles, and context-isolated reviews.
- **G3 — pilot:** one configured model (Gemini 3.7 Flash); A/B/C conditions; natural-language subset.
- **G4 — main study:** powered, randomized, frozen multi-model execution (Gemini 3.7 Flash, DeepSeek-R1 / Kimi K3, GPT-5.6 Terra; \(N=30\) per cell).
- **G5 — extensions:** GPU pressure, shared multi-agent resources, real outages,
  and telemetry-poisoning robustness under separate protocols.

## Repository boundary

The static-contract repository remains the evidence and manuscript anchor for
Phase 1. This repository owns Phase 2 code, containers, simulators, manifests,
and raw trajectories. Reciprocal commit/release pins preserve lineage without
mixing denominators.
