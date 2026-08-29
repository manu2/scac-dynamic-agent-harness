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

### 2026-08-29 — ToolRoute development hardening

- Audited the unblinded seed-202 smoke records and retained them as development
  artifacts only; they are not matched empirical evidence and must not be used
  to claim a treatment effect.
- Fixed Tier-2 prompt-advice leakage, sparse-delta resume state loss, ambiguous
  wait scoring, and missing terminal/finalization records in ToolRoute v0.2.
- Added an explicit issue ledger at `docs/07_toolroute_hardening_issue_ledger.md`.
  Open issues include perfect synthetic probes, shared-filesystem leakage, and
  byte rather than tokenizer matching; these block empirical interpretation.
- Ran a complete v0.2 seed-17 A/B/C development triad using fresh-context
  subagents. All terminal finalization hashes verified. It is retained solely
  as a capture and evaluator diagnostic: the then-hashed option ordering put
  `tool_beta` first on every turn, so its descriptive A/B/C differences are
  position-confounded and not evidence of a telemetry effect.
- Replaced that ordering with a six-seed balanced block in ToolRoute v0.3.
  The first v0.3 decision pass exposed a malformed `- tool_alpha` response;
  the runner was amended to archive rejected responses rather than discarding
  them. The three partial v0.3 directories were terminally finalized as
  `ABORTED_DEVELOPMENT` after that protocol revision. v0.3 collection is
  intentionally paused pending a fresh full block; all retained records remain
  development-only.

### 2026-08-29 — ToolRoute v0.3 fresh-subagent block (partial)

- Completed and hash-verified seed 18 and seed 19 A/B/C trajectories using a
  distinct no-context Codex subagent for each decision. These records are
  strictly development diagnostics.
- A seed-19 C decision selected the lower-latency route shown by telemetry but
  incurred 20 oracle-regret because the oracle also prices latent reliability.
  This is a required telemetry/oracle-alignment calibration issue, not a result
  supporting the treatment.
- Platform concurrency retained completed subagent threads and prevented fresh
  subject creation for seeds 20–23. Seed 20/A has one captured decision; all
  other reserved starts are untouched. They must be resumed in a fresh session
  with fresh subjects; no existing subject may be reused.

### 2026-08-29 — ToolRoute v0.4 observation/oracle alignment

- Replaced direct thresholded latent-health projection with separately seeded
  monitor probes. These probes are independent from the fixed action outcome
  tape.
- Made observable-monitor cost the primary ToolRoute oracle and retained the
  latent expected-cost oracle only as a diagnostic ceiling. Added a fail-closed
  minimum observable-margin calibration guard and v0.4 multi-seed calibration
  tests. No v0.4 subject trajectory has been started at this entry.
- Terminally finalized the 12 unsubmitted/partial v0.3 directories as
  `ABORTED_DEVELOPMENT` with reason `superseded_by_toolroute_v0_4_observation_oracle_contract`.
  A hash audit of every finalized development artifact passed.
- Full v0.4 review passed: 82 tests, compilation, lifecycle/finalization audit,
  no prompt-advice rendering, and observable-margin calibration. Attempted
  seeds 32–33 A/B/C fresh-subagent triads, but platform child-thread capacity
  failed before any response. The six empty starts were finalized as
  `ABORTED_DEVELOPMENT`; new v0.4 subject trajectories require a fresh task.

### 2026-08-29 — ToolRoute v0.4 fresh-subagent development block (seeds 34–35)

- Preflight passed with 82 tests, zero failures, no `git diff --check` errors,
  and `provider_trials_authorized: false`; no provider/API calls were made.
- Completed terminal A/B/C trajectories for seeds 34 and 35 using a distinct
  `fork_turns="none"` subagent for every decision. No response was malformed or
  rejected. Seed 34/A and 34/B ended `DECISION_BUDGET_EXHAUSTED` at 2/3 records;
  seed 35/B ended the same way at 1/3 records. Seed 34/C, 35/A, and 35/C ended
  `COMPLETED` at 3/3 records.
- All six finalization hash sets verified. Every result contained primary and
  diagnostic oracle metrics; every prompt excluded `HOST_CONSTRAINTS`; and all
  C host events identified `synthetic_host_probe_v0.4`.
- On seed 34/B turn 0, the required subject-only suffix was concatenated
  directly after the final byte of the emitted message because that B message
  had no terminal newline. The emitted message and suffix were each preserved
  byte-for-byte, but there was no separating newline; subsequent no-newline
  messages used an explicit separator. This is retained as an operational
  anomaly and the trajectory remains development-only.
- These trajectories are local harness diagnostics only, are not blinded
  empirical evidence, and support no treatment-effect claim.

### 2026-08-29 — ToolRoute v0.4 preservation and next-gate freeze

- Consolidated the local ToolRoute conclusion: the v0.4 harness can capture the
  intended decision process, but the two fresh-subagent seed triads are neither
  blinded nor powered and provide no empirical treatment-effect evidence.
- Fixed the future-handoff defect observed in seed 34/B turn 0. `smoke_cli` now
  emits a `subject_prompt` that is the unmodified condition message plus a
  constant double-newline delimiter and universal subject instruction, and it
  persists that exact prompt in `turn-XX-handoff.json`. Existing trajectories
  are immutable and were not altered.
- The next ToolRoute work is explicitly gated: one clean local post-fix smoke
  triad may verify the handoff artifact only; no additional local smoke run is
  evidence. Before any API call, complete Linux cgroup-v2 G1, clean-container
  and context-isolated G2 reviews, freeze the observation model and provider
  pilot manifest, then validate a reservation-first isolated API runner.
- `PROVENANCE.json` remains `provider_trials_authorized: false`. The issue
  ledger and the complete decision record are in
  `docs/07_toolroute_hardening_issue_ledger.md` and
  `docs/10_toolroute_v0_4_status_and_next_gate.md`.

### 2026-08-29 — Scenario-isolation protocol for parallel work

- Established `docs/11_scenario_boundaries_and_parallel_work_protocol.md` as
  the authoritative separation between common harness invariants and
  scenario-owned design. ToolRoute evidence and open items do not transfer to
  RetryBudget or MemoryGovernor.
- New G2 calibration artifacts are now written below
  `experiments/g2-calibrations/<scenario>/`; existing artifacts were preserved
  in place and are not migrated or rewritten.
- RetryBudget remains **calibration-only**. Its current v0.1 simulator advances
  after `wait`, permits a high-utility unconditional fallback, and uses a
  coarse binary regret oracle. Those semantics require a separate design review
  and evaluator-defeat tests before any fresh-subagent or provider trajectory.

### 2026-08-29 — ToolRoute v0.4 post-fix development audit (seeds 50–54)

- Retained 15 terminal development trajectories (A/B/C for each seed 50–54).
  All finalization hashes verify; 51/51 decision records have distinct subject
  identifiers; each submitted turn has a `turn-XX-handoff.json`; and every B/C
  turn is UTF-8 byte matched. These are capture/provenance facts only.
- The raw outcomes are strongly patterned: C completed 5/5 trajectories in
  three turns with zero primary observable regret; A and B each completed 4/5,
  with identical aggregate outcomes (mean regret 13,426.92; mean latency
  4,620 ms). This is a useful end-to-end diagnostic: fresh subjects can react
  to the rendered synthetic monitor and the evaluator records the expected
  difference.
- This is **not** a matched or isolated empirical cohort. The 51 generations
  are independent; fresh Codex subagents share the repository workspace; B is
  byte- but not tokenizer-matched; and seeds 50–54 omit the sixth permutation
  required by the six-seed development block. Consequently, do not calculate
  significance, claim zero attention tax, or describe these trajectories as a
  treatment effect or paper evidence.
- The misframing and corrective disposition are recorded as TR-020. No provider
  calls were made; `PROVENANCE.json` remains `provider_trials_authorized: false`.

### 2026-08-30 — ToolRoute delta-delivery boundary

- Recorded TR-021: fresh-subagent smoke decisions receive only the current
  delta-labelled prompt, not the prior base snapshot. This does not affect the
  current ToolRoute action oracle because each emitted tool entry contains the
  complete rolling facts it uses. It does mean the smoke path is not a test of
  persistent-agent delta rehydration. The provider pilot must freeze either a
  persistent-history delta mode or independent full-checkpoint episodes.

### 2026-08-30 — ToolRoute isolated API preflight and optional HTTP adapter

- Added a reservation-first, tool-less `ToolRouteAPIEpisode` path under
  `experiments/api-preflight/toolroute/`. Each prospective provider decision
  receives an independent full checkpoint (`base_snapshot_id: null`), while the
  local harness retains schedule, raw monitor events, evaluator, exact prompt,
  raw response, result, and terminal hashes.
- Provider invocation is fail-closed: `ToolRouteAuthorization` verifies the
  scenario-specific provenance flag and a frozen manifest SHA-256. Current
  provenance is deliberately false with a null hash. No provider call issued.
- Added versioned observation-model fields plus tests for noise/freshness
  recording, malformed response capture, finalization, tokenizer-matched B
  control, fixed-policy evaluator defeat, and local HTTP span capture. The full
  suite passed 90 tests after an approved host-only run enabled loopback test
  server binding.
- Implemented but did not execute the optional `ToxiproxyClient` adapter.
  Homebrew installation failed because `/opt/homebrew` is not user-writable;
  no system ownership/permission change occurred. Recorded as TR-023; it does
  not change synthetic ToolRoute readiness.

### 2026-08-30 — completed local Toxiproxy socket-adapter validation

- Downloaded the official Shopify Toxiproxy v2.12.0 macOS ARM server to a
  temporary directory and verified it against the release checksum; no
  Homebrew repair, sudo, system install, provider call, or subagent was used.
- Ran a retained real-loopback schedule under
  `experiments/adapter-validation/toolroute/`: alpha/beta baseline HTTP 200,
  alpha 150 ms injected latency (observed 152 ms), then disabled beta proxy
  (observed `CONNECTION_ERROR`). The reducer accepted the real host spans and
  emitted a checkpoint/rendered telemetry record.
- The first run failed closed because `NETWORK_ERROR` was not a schema-valid
  SST error class (TR-024); it was finalized as failed. A second successful
  telemetry run exposed an uninitialized failure-finalization variable and was
  subsequently finalized without changing its contents. The corrected third
  run completed. All three attempt hash sets verify. This validates the socket
  collection adapter only; it is not model behavior or paper outcome evidence.
