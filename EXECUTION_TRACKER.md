# Execution Tracker: Dynamic SCAC

## Overall status

- **Current stage:** G1 enforcement implementation and capability-gated controls (In progress; branch `codex/g0-sst-schema`).
- **Provider calls:** not authorized.
- **Empirical trials:** none.
- **Upstream design basis:** `manu2/Context-Aware-Agent-Experiment` commit
  `f35173d29375216af88c708687efbcc51f36398a`.

## Stage ledger

| Stage | Work | Status | Evidence |
|---|---|---|---|
| G0.0 | Create separate repository boundary | Complete | `PROVENANCE.json` |
| G0.1 | Scaffold governance, protocol, package, and tests | Complete | initial repository tree |
| G0.2 | Freeze SST v0.1 JSON Schema Draft 2020-12 | Complete | `src/scac_harness/schemas/scac-sst-v0.1.json` |
| G0.3 | Generate valid and invalid test fixtures | Complete | 9 valid, 12 invalid fixtures in `tests/fixtures/` |
| G0.4 | Implement snapshot & trajectory validation | Complete | `src/scac_harness/validator.py`, `tests/test_validation.py` |
| G0.5 | Implement RFC 8785 canonical identity hashing | Complete | `src/scac_harness/identity.py`, `tests/test_identity.py` |
| G0.6 | Implement deterministic reducer interface | Complete | `src/scac_harness/reducer.py`, `tests/test_reducer.py` |
| G0.7 | Implement compact model-visible renderer | Complete | `src/scac_harness/renderer.py`, `tests/test_renderer.py` |
| G0.8 | Complete threat model & representation semantics | Complete | `docs/01_threat_model_and_trust_boundaries.md`, `docs/02_representation_semantics.md` |
| G1 | Collectors and fail-closed enforcement | In progress | `collectors.py`, `enforcement.py`, and immutable `experiments/g1-controls/` records; Linux cgroup-v2 memory proof pending |
| G2 | Deterministic scenarios and oracles | In progress | all three local simulators/oracles and immutable `experiments/g2-calibrations/` records; clean-container and review gates pending |
| G3 | One-model pilot | Blocked by G0–G2 | frozen pilot manifest |

## Execution log

### 2026-08-28 — G0 completion and peer-review remediation (Round 1 & 2)

- **Vetted RFC 8785 (JCS) Conformance:** Adopted official `jcs>=0.2.1` implementation in `src/scac_harness/identity.py` for canonical serialization, strictly satisfying ECMAScript 7.1.12.1 float representations (`1e30 -> 1e+30`, `1e-7 -> 1e-7`, `-0.0 -> 0`) and UTF-16 code unit property key sorting.
- **Deep Raw Event Immutability:** Introduced `FrozenDict` in `src/scac_harness/events.py` ensuring that `event.payload` is deeply immutable and cannot be mutated after content hashing, while supporting serialization and deepcopy.
- **Elimination of Partial Observation Fabrication:** In `src/scac_harness/reducer.py`, when `current_bytes` is observed without `max_bytes`, `headroom_ratio` remains `None` and memory `state` is classified as `UNKNOWN` (never fabricated as 1.0 or OK).
- **Interval Delta Isolation & Freshness Tracking:** In `src/scac_harness/reducer.py`, interval deltas (`events_delta`, `nr_throttled_delta`, etc.) are reset across reduction windows and never carried across unrelated turns. Added `subsystem_observed_at_ms` to track fine-grained subsystem observation ages.
- **True Sparse Delta Representation:** Updated schema, reducer, and renderer so delta snapshots (`kind == "delta"`) only contain the namespaces and counters actually observed/modified in the current interval, with full rehydration supported.
- **Genuine Unsupported-as-Zero Fixture & Validation:** Updated `unsupported_metric_represented_as_zero.json` to declare an unavailable metric with value 0, and updated `validate_snapshot` to reject any unavailable field represented as zero.
- **Roadmap Scope Correction:** Restored protocol-aligned wording in `RESEARCH_ROADMAP.md` (removing premature sample size and model commitments).
- **Test Suite:** 52 passing unit and integration tests with 0 failures.

### 2026-08-28 — G1 host-controlled enforcement implementation

- Added `CgroupV2Collector`, which parses `memory.current`, `memory.max`,
  `memory.events`, `cpu.max`, and `cpu.stat`; it emits explicit first-window
  deltas and fails closed on unavailable files, malformed data, or counter
  regression.
- Added host-owned timeout and deterministic tool-fault positive controls. Both
  passed locally and their stdout, stderr, classification, and timing records
  were retained immutably in `experiments/g1-controls/`.
- Added a Linux-only cgroup-v2 memory allocation control. It can pass only after
  a dedicated child cgroup reports an `oom_kill` increment. This macOS host has
  no cgroup-v2 filesystem, so the attempted memory control is recorded as
  `BLOCKED/CGROUP_V2_UNAVAILABLE`; it is not counted as a pass.
- Revalidated G0 with the vetted `jcs` implementation, immutable raw event
  payloads, sparse deltas, and 52 pre-G1 tests passing. The combined local suite
  now has 58 passing tests.

### 2026-08-29 — G2 local ToolRoute calibration start

- Implemented a seeded, model-free ToolRoute simulator and external expected-cost
  oracle. Tool health schedules are exogenous; the agent-facing action interface
  is limited to a named equivalent tool or `wait`.
- Added a swapped-tool-name control and immutable calibration archival before the
  first action. A local oracle-following calibration completed four turns with
  zero policy regret.
- This begins G2 and supports local design/calibration work; it neither enables
  provider calls nor substitutes for the Linux cgroup-v2 memory control.

### 2026-08-29 — G2 complete local scenario calibration

- Added deterministic RetryBudget and virtual-only MemoryGovernor simulators
  with host-owned, predeclared action oracles. The MemoryGovernor calibration is
  labelled `virtual_only_no_cgroup_claim` in its manifest.
- Archived four-turn oracle-following calibrations for ToolRoute, MemoryGovernor,
  and RetryBudget. Each has zero policy regret by construction; these artifacts
  validate simulator/oracle mechanics, not adaptation by a model.
- The combined local suite has 67 passing tests. G2 remains open for clean Linux
  container reproduction, context-isolated leakage review, and evaluator-defeat
  testing.

### 2026-08-29 — Offline fresh-context ToolRoute development smoke

- Added a host-owned offline A/B/C trial runner with pre-generated,
  action-independent potential outcomes, host-monitor raw events, reducer and
  renderer use for C, byte-matched B neutral padding, constrained action capture,
  and write-once per-turn artifacts.
- Ran one matched development-only A/C smoke decision using fresh-context Codex
  subagents. Against the same hidden turn-1 tape, A selected `tool_alpha`
  (regret 11,920 ms-equivalent) and C selected `tool_beta` (regret 0). These
  observations are not empirical study data: subagents share workspace access,
  the sample is one per condition, and no blinding or frozen pilot manifest
  exists.
- The combined local suite has 70 passing tests. Next hardening: isolate hidden
  schedules from the action agent's filesystem and add an evaluator-defeat test
  suite before collecting additional development smoke trajectories.

### 2026-08-29 — Fresh-subagent smoke handoff

- Added `python -m scac_harness.smoke_cli` with deterministic `start`, `submit`,
  and `next` operations. It validates one-label action responses, captures the
  unedited response and subject identifier, and restores the prior SST snapshot
  when compiling a delta turn after a cross-process subagent response.
- Added `docs/04_offline_subagent_smoke_runbook.md` for another Codex agent to
  orchestrate A/B/C smoke trajectories using fresh-context subagents. The
  runbook preserves the non-blinded, development-only interpretation boundary.
- Verified the complete command lifecycle and combined suite: 72 tests passing.
