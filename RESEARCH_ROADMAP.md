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
- **ToolRoute API cohort (collection complete; analysis pending):** independent full-checkpoint
  episodes, isolated remote-model access, capture/finalization, observation-model
  calibration, and evaluator-defeat checks are complete. Six 36-decision
  blocks (seeds 8–13; 216 decisions) were executed from a committed,
  hash-bound manifest and are preserved.
  Independent audit found a documentation discrepancy: the manifest says
  sampling controls are omitted while its Gemini requests explicitly set
  `temperature: 0.0`. Because that setting is identical across the seed-8
  Gemini A/B/C cells and is retained in each raw request, it is not a treatment
  confound and seed 8 remains in the cohort. The two subsequent continuation
  blocks hash-bound execution configurations and retained Gemini
  `temperature: 0.0`; authorization is now revoked after collection. The Linux
  cgroup-v2 proof remains a MemoryGovernor requirement, not a blocker for this
  narrow synthetic ToolRoute study.
- **Selected first-paper model cohort:** OpenAI `gpt-5.6-sol`, Anthropic
  `claude-sonnet-5`, and Google `gemini-3.7-flash`. The model selection is
  retained. Provider authorization is false. The complete cohort used the
  recorded settings, including Gemini `temperature: 0.0`; analysis and
  manuscript framing remain before any follow-on protocol is considered.
- **ToolRoute positioning:** `docs/18_harness_awareness_positioning_and_evidence_memo.md`
  and `docs/19_manuscript_narrative_contract.md` record the paper's broad
  Harness Awareness thesis, its relationship to the prior Substrate Awareness
  work, completed evidence, and drafting claim boundaries. The core position is
  that verified operational state is an active control input, not merely a
  debugging artifact. ToolRoute establishes the route-selection instance of a
  split-plane architecture; it does not claim live production telemetry,
  replacement of deterministic middleware, or completed evidence for the other
  state dimensions. The next artifact is a reproducible frozen-cohort analysis
  report. The manuscript is organized as architecture, a controlled
  information-ablation method, results, and bounded systems agenda; it uses
  “trust-separated harness interface,” not an unsupported L0/L2 zero-trust
  claim.
- **G2 — scenarios (In progress):** seeded, model-free ToolRoute,
  MemoryGovernor, and RetryBudget simulators plus external oracles are locally
  calibrated without model calls. The local MemoryGovernor is explicitly virtual
  and makes no cgroup-enforcement claim. Clean-container reproduction and
  context-isolated leakage/evaluator-defeat reviews remain pending.
- **RetryBudget v0.2 (pre-provider hardening complete):** the v0.1 fixed-row
  calibration is superseded for future work. v0.2 preserves pending work across
  waits, uses a numeric observable dynamic-programming oracle, and gives all
  five actions explicit lifecycle semantics. Its seed-varying calibration,
  baseline A/B/C full-checkpoint renderer, position control, write-once
  provider runner, C-only Gemini development manifest, and self-audit are
  committed. Provider authorization is deliberately false. The next permitted
  step is an independently reviewed, narrow development canary; a paper A/B/C
  cohort needs separate inclusion, episode-level analysis, and seed/power
  freeze. See `docs/20_retrybudget_v0_2_design_and_readiness.md`,
  `docs/21_retrybudget_issue_ledger.md`, and
  `docs/23_retrybudget_preprovider_audit.md`.
- **Scenario isolation:** each scenario has an independent action/oracle,
  calibration, development, and provider-readiness contract. ToolRoute v0.4
  hardening does not close RetryBudget or MemoryGovernor readiness. New
  artifacts are namespaced under `experiments/<stage>/<scenario>/`; historical
  records remain immutable in their original paths. The collaboration contract
  is `docs/11_scenario_boundaries_and_parallel_work_protocol.md`.
- **Development smoke path:** offline A/B/C ToolRoute messages may be supplied
  to fresh-context Codex subagents after complete host-side capture. These are
  engineering smoke tests only: shared workspace access prevents them from
  being blinded empirical trials or inclusion in a study denominator. The
  hardened ToolRoute v0.4 path uses independent host-monitor probes, an
  observable-only primary oracle, descriptive-only C envelopes, cumulative
  private resume state, UTF-8 byte-matched (not token-matched) B controls,
  deterministic action-order rotation, completion records, and finalization
  hashes. The v0.4 CLI also records the exact coordinator-to-subject prompt
  with a frozen delimiter. Open limitations and the next gate are retained in
  `docs/07_toolroute_hardening_issue_ledger.md` and
  `docs/10_toolroute_v0_4_status_and_next_gate.md`.
- **Toxiproxy development diagnostic (Frozen optional):** one condition-C fresh-subagent action
  selected the route whose three pre-decision monitor spans were healthy and
  low-latency, but the later real proxied action returned a connection error
  while the observable snapshot oracle assigned zero regret. This retained
  local result tests socket-backed end-to-end capture only; it does not alter
  ToolRoute API readiness or provide paper evidence. Its cross-session
  lifecycle defect is TR-025; do not spend further first-paper effort there.
- **G3 — pilot:** one configured model; A/B/C conditions; natural-language subset.
- **G4 — main study:** powered, randomized, frozen multi-model execution with sample size determined by simulation from pilot base rates and minimum detectable effect.
- **G5 — extensions:** GPU pressure, shared multi-agent resources, real outages,
  and telemetry-poisoning robustness under separate protocols.

## Repository boundary

The static-contract repository remains the evidence and manuscript anchor for
Phase 1. This repository owns Phase 2 code, containers, simulators, manifests,
and raw trajectories. Reciprocal commit/release pins preserve lineage without
mixing denominators.
