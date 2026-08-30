# Execution Tracker: Dynamic SCAC

## Overall status

- **Current stage:** G1 enforcement implementation and capability-gated controls (In progress; branch `codex/g0-sst-schema`).
- **Provider calls:** not authorized for any further call. One seed-8 ToolRoute
  paper-block attempt (36 completed decisions) is retained; resumption requires
  an execution-config clarification and fresh authorization.
- **Empirical trials:** 36 submitted ToolRoute paper-cohort attempts retained
  under `experiments/api-paper-v1.0-seed8/`; eligible to remain in the cohort.
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

### 2026-08-30 — Toxiproxy fresh-subagent strategy smoke prepared

- Added `ToolRouteTransportStrategy` and a Toxiproxy loopback implementation,
  plus a separate start/submit/abort runner for one-decision fresh-subagent
  smoke. It preserves the synthetic benchmark as the primary causal path and
  namespaces socket-backed subagent records under `dev-smoke-toxiproxy/`.
- A setup-only C start observed real alpha latency of about 303 ms versus beta
  1.6 ms and rendered that projection correctly. It was finalized as
  `ABORTED_DEVELOPMENT` before any subject was created; no fabricated choice was
  submitted. The complete local test suite passed (94 tests).

### 2026-08-30 — One-decision Toxiproxy fresh-subagent smoke

- Ran exactly one development-only condition-C Toxiproxy attempt with one
  context-free subject and no provider/API call. The initial sandboxed launch
  was denied loopback binding before trial reservation; the same command then
  started with local loopback permission.
- The retained monitor spans observed alpha latencies of 304, 304, and 303 ms
  and beta latencies of 1, 1, and 1 ms. The subject selected `tool_beta`.
- The subsequent real proxied beta action did not succeed: it produced a 22 ms
  `CONNECTION_ERROR`. The finalized result classified the attempt `COMPLETED`
  with `success: false` and observable `policy_regret: 0.0`.
- `host.json`, `input.json`, `manifest.json`, and `result.json` all match their
  hashes in `finalization.json`. This socket-backed smoke remains development
  evidence only and is not a paper or provider-cohort result.

### 2026-08-30 — Toxiproxy scope frozen

- Reviewed the cross-session C smoke: backend logs contain the six monitor
  requests but no beta action request, establishing that the connection error
  was caused by child-process lifecycle reaping, not an exogenous route fault.
- Recorded TR-025 and froze Toxiproxy as an optional adapter prototype. Its
  code and retained attempts remain for provenance, but no repair or further
  collection is in scope for the first ToolRoute paper.

### 2026-08-30 — ToolRoute v0.6 synthetic observation calibration

- Added retained model-free six-seed × four-turn calibration under
  `experiments/g2-calibrations/toolroute-observation/`, covering baseline,
  10% monitor-label error, 10% event loss, 500 ms delivery age, and 2.5 s
  stale delivery. Fixed alpha, fixed beta, and fixed wait policies all retain
  positive mean observable regret in every eligible configuration.
- Corrected a discovered v0.5 freshness semantic error: delivery delay had
  shifted both event and checkpoint timestamps, concealing age. v0.6 preserves
  the probe timestamp, advances checkpoint delivery time, renders tool age,
  and excludes observations older than `fresh_for_ms`. The initial v0.5
  calibration remains preserved but is superseded; v0.6 is the candidate
  frozen observation model.

### 2026-08-30 — ToolRoute v0.6 API-run readiness cleanup

- Reconciled current source and operating documentation to the calibrated
  ToolRoute v0.6 contract. The reservation-first API episode now records v0.6
  scenario/oracle identifiers rather than stale v0.4 labels.
- Added `docs/14_toolroute_v0_6_api_run_readiness.md` as the single operational
  handoff: a separate six-seed canary, then two new six-seed blocks per chosen
  model, with independent full-checkpoint decisions and no pooling with the
  development or Toxiproxy artifacts.
- Full local verification passed: 95 tests. The two socket-adapter tests were
  run with local loopback permission only; no external network or provider/API
  call was made.
- Provider authorization remains false. Before the first request, select the
  provider/model and exact tokenizer, commit the completed manifest/analysis
  plan, and explicitly bind its SHA-256 in `PROVENANCE.json`.

### 2026-08-30 — ToolRoute API provenance and provider-adapter hardening

- Closed TR-027: an API transport exception now writes a terminal
  `PROVIDER_ERROR` result and finalization hashes rather than leaving a reserved
  directory incomplete. The runner records the sanitized provider request and
  raw provider JSON response; exception text is deliberately excluded to avoid
  credential-bearing URL leakage.
- Added local, tool-less protocol adapters for OpenAI Chat Completions,
  Anthropic Messages, and Gemini GenerateContent. Each exposes its full
  request metadata without credentials and captures provider-reported input
  and output usage. No adapter was invoked against a remote endpoint.
- Full verification passed: 96 tests, including the two loopback-only adapter
  tests. No provider/API calls were made and authorization remains false.

### 2026-08-30 — Scoped ToolRoute transport-smoke authorization

- Added a frozen, non-paper transport manifest that enumerates exactly three
  independent condition-C episodes: Gemini 3.7 Flash, GPT-5.6 Terra, and
  Claude Opus 5. Its purpose is request/response, parser, usage, and
  finalization validation before any balanced cohort.
- The authorization verifier now checks the exact seed, turn, condition, model,
  and provider against the manifest; a manifest hash alone cannot authorize an
  undeclared paid request.
- `PROVENANCE.json` binds the manifest SHA-256 and authorizes only those three
  diagnostic calls. Gemini must run first; inspect its terminal artifacts before
  the OpenAI or Anthropic diagnostic. None enters a paper denominator.

### 2026-08-30 — Completed three-call ToolRoute transport smoke

- Gemini 3.7 Flash completed the authorized seed-0/turn-1/C episode: it returned
  `tool_alpha`, with zero observable and diagnostic regret, 343 input tokens,
  179 output tokens, normal `STOP`, and six valid finalization hashes. This is
  an API-path diagnostic, not paper evidence or an A/B/C comparison.
- GPT-5.6 Terra and Claude Opus 5 each reached their provider endpoint but
  returned HTTP 400 before a model response. Each attempt retained a sanitized
  request, terminal `PROVIDER_ERROR`, and six valid hashes; neither is a model
  behavior result. No retry was issued.
- Revoked the consumed scoped authorization. Added structured, credential-redacted
  HTTP error-body capture for a future revised manifest so provider request
  incompatibilities can be diagnosed without exposing a key. The first smoke's
  error bodies cannot be reconstructed and are retained unchanged.

### 2026-08-30 — Handover freeze

- Added `docs/15_toolroute_api_handover_2026-08-30.md` as the controlling
  self-contained handoff. It names each attempted API artifact, records the
  valid Gemini diagnostic and two pre-inference failures, authorizations,
  immutable-artifact rules, exact next sequence, and a ready-to-paste handover
  prompt for a fresh agent.

### 2026-08-30 — Sampling-control transport repair authorization

- Compared failed ToolRoute requests against the successful static-study API
  code. Claude Opus 5's prior manifest explicitly records that it rejects
  supplied sampling controls; the failed ToolRoute request had sent
  `temperature: 0.0`. GPT-5.6 Terra likewise received an explicit 0.0 control,
  unlike the successful OpenAI patterns which used provider defaults or 1.0.
- Updated both provider adapters to omit `temperature` when unset, added
  regression coverage, and froze a new two-episode C-only diagnostic manifest:
  seed 1 / turn 1 for GPT-5.6 Terra first, then Claude Opus 5. The manifest
  hash is bound in provenance; neither attempt is paper evidence.

### 2026-08-30 — Pre-request manifest-scope rejection repair

- The first invocation of the sampling-fix runner passed its stale hard-coded
  seed 0 while the new manifest declared seed 1. Authorization rejected it
  before the provider adapter was invoked; the reserved directory is finalized
  `REJECTED_MANIFEST_SCOPE` and is not a provider request.
- Repaired the CLI to accept/pass `--seed` and `--turn`, and repaired the API
  episode to terminally finalize all revoked or undeclared-scope rejections.
  Regression tests cover both cases. The pending authorized Terra diagnostic
  remains seed 1 / turn 1 and has not yet been submitted.

### 2026-08-30 — Completed sampling-control transport smoke

- GPT-5.6 Terra completed its fresh seed-1/turn-1/C diagnostic after sampling
  controls were omitted: `tool_alpha`, zero observable regret, 304 input and
  27 output tokens, and all terminal hashes valid. This confirms the former
  OpenAI HTTP 400 was request-configuration related, not a ToolRoute failure.
- Claude Opus 5 reached the model after the same repair but returned an explicit
  provider `refusal`, with empty content and zero output tokens (613 input
  tokens). It was correctly finalized as `MALFORMED_PROVIDER_RESPONSE`; do not
  coerce a choice from it or classify it as a route decision.
- Revoked the two-call authorization. A future Opus inclusion requires a
  separately frozen, non-paper prompt-acceptance diagnostic; no model or prompt
  substitution is authorized by this record.

### 2026-08-30 — Scoped Claude Sonnet 5 prompt-acceptance diagnostic

- Claude Opus 5's repaired request was API-successful but model-refused: the
  raw response has `stop_reason: refusal`, an empty `content` array, and zero
  output tokens. There is no hidden natural-language refusal message. This is
  distinct from the earlier HTTP 400 transport failure.
- Authorized one new seed-2/turn-1/C Claude Sonnet 5 diagnostic with the same
  tool-less Anthropic Messages path and omitted sampling controls. It exists
  solely to determine whether the refusal is Opus-specific or a Claude/prompt
  compatibility issue; it is not paper data.

### 2026-08-30 — Completed Claude Sonnet 5 prompt-acceptance diagnostic

- Sonnet 5 completed the authorized seed-2/turn-1/C call normally with
  `stop_reason: end_turn`: it selected `tool_beta`, incurred zero observable
  regret, and used 610 input / 7 output tokens. All terminal hashes verify.
- The same direct Anthropic Messages path therefore works for the ToolRoute
  prompt. The earlier empty Opus response is model-specific prompt refusal,
  not an API-level or harness-level incompatibility. Revoked the consumed
  authorization. Sonnet 5 is now the eligible Anthropic candidate pending a
  separately frozen balanced cohort protocol.

### 2026-08-30 — First-paper model cohort selection

- Selected the intended ToolRoute paper cohort: OpenAI GPT-5.6 Sol, Anthropic
  Claude Sonnet 5, and Google Gemini 3.7 Flash. Terra and Opus remain retained
  transport diagnostics only and are not candidates for the cohort.
- Gemini Flash and Sonnet 5 have completed clean ToolRoute C-only transport
  diagnostics. Sol has successful direct-API precedent in the separate static
  study but needs one separately authorized ToolRoute C-only diagnostic before
  the tokenizer-pinned A/B/C canary. Provider authorization remains false.

### 2026-08-30 — Structural-B correction and GPT-5.6 Sol transport diagnostic

- Corrected a material setup defect (TR-030): the former API Condition B was
  only opaque padding, not a table-structured neutral control. B now retains
  C's telemetry envelope and fields while assigning equal benign health values
  to both tools.
- Added provider-native token-counter adapters: OpenAI input-token, Anthropic
  Messages count-tokens, and Gemini countTokens. A frozen paper manifest must
  retain the exact B/C count record before cohort generation; reported usage is
  checked again where a provider supplies it. No paper cohort is authorized.
- Authorized exactly one fresh C-only GPT-5.6 Sol diagnostic (seed 3, turn 1),
  then revoked authorization after completion. It returned `tool_beta`, zero
  observable regret, and 303 input / 5 output tokens. Terminal hashes verify:
  `experiments/api-transport-smoke/api-preflight/toolroute/20260830T083610.523454Z-C-0c92df46ea004b49a621d0a20f1ddf6a`.
- Sonnet 5 and Gemini Flash retain earlier clean C-only transport diagnostics;
  those do not substitute for per-provider B/C native-count calibration.

### 2026-08-30 — Compact ToolRoute API cohort frozen for execution

- Frozen `manifests/toolroute_api_pilot.v0.7.json`: 216 independent decisions
  (three selected models × six seeds × four turns × A/B/C), with native
  provider token counts, independent full checkpoints, no tools, provider
  defaults, no request retries, and deterministic execution randomization.
- Added the manifest-bound cohort runner. It refuses undeclared episodes and
  constructs B with the selected provider's native count endpoint before a
  generation request; any unmatched B prompt fails closed.
- Before authorization, checked every 24 seed/turn B/C prompt pair under the
  deterministic test tokenizer after repairing a turn-0 one-token overshoot.
  The complete local test suite passes (101 tests). The next action is an
  authorized provider block; no cohort request has yet been submitted.

### 2026-08-30 — v0.7 Gemini canary invalidated; authorization-control repair

- A Gemini v0.7 canary began under the frozen manifest. Twelve model decisions
  completed before the operator revoked authorization after observing an
  in-progress native-token setup concern. Twenty-eight later reservations were
  rejected before model generation; one interrupted B setup reservation was
  recovered and terminally finalized. All 41 directories now have finalization
  hashes. This mixed, interrupted block is retained as engineering evidence and
  excluded from every paper denominator.
- Identified TR-031: the runner rechecked authorization before generation but
  not before each provider-native token-count request. It has been corrected to
  recheck before every count and episode, and setup failures now finalize
  automatically. The exact old runner was terminated; authorization remains
  revoked. A revised manifest and fresh cohort are required before any restart.

### 2026-08-30 — Final ToolRoute protocol simplification (v1.0)

- Audited and removed the active online token-equalization path: provider token
  counter adapters, iterative opaque padding, tokenizer-bound constructor
  inputs, and the associated count-request authorization surface. Historical
  v0.7–v0.9 manifests and attempts remain retained as excluded engineering
  records.
- The final A/B/C contract is now fixed structure: B has C's envelope, field
  names, ordering, and rows, but identical neutral tool values; C has truthful
  values. No padding or exact token equality is claimed. Provider-reported
  input-token usage and prompt characters are retained as descriptive checks.
- Added `manifests/toolroute_api_canary.v1.0.json`, a fresh 36-decision,
  per-episode end-to-end canary (one seed × four turns × A/B/C × three models),
  outside the paper denominator. It is not yet authorized. The full 24-state
  route-symmetry test for B passes locally.

### 2026-08-30 — Fixed-structure v1.0 end-to-end canary completed

- Authorized, executed, and then revoked exactly the 36 decisions in
  `manifests/toolroute_api_canary.v1.0.json`: one seed × four turns × A/B/C ×
  GPT-5.6 Sol, Claude Sonnet 5, and Gemini 3.7 Flash. All 36 completed with
  exact-label parsing; every expected provider/turn/condition cell occurred
  once, with no duplicates, no provider errors, and valid finalization hashes.
- This one-seed engineering canary exhibited the intended contrast consistently
  across all three models: on turns 0 and 3, A and B selected `tool_alpha`
  (80.0 and 7453.81 observable regret), while C selected `tool_beta` (0).
  On turns 1 and 2, all conditions selected zero-regret actions. This is
  validation evidence only, not a treatment-effect estimate or paper data.
- B/C prompt-character and provider-reported input-token values were retained
  as descriptive checks. They are deliberately not forced equal. Authorization
  is revoked; a new frozen paper manifest is required for further calls.

### 2026-08-30 — Fixed-structure Gemini v1.1 seed-7 test completed

- Authorized, executed, audited, and revoked the 12 Gemini 3.7 Flash seed-7
  decisions in `manifests/toolroute_api_gemini_test_seed.v1.1.json`. All four
  turns have one A/B/C record, all 12 parsed and completed, and every terminal
  hash verifies. It is excluded engineering evidence, not paper data.
- On turn 0, A/B selected `tool_alpha` (80.0 observable regret) and C selected
  `tool_beta` (0). On turns 1–3 all three conditions selected zero-regret
  actions; seed 7's turn-3 healthy route is alpha. Authorization is revoked.

### 2026-08-30 — ToolRoute paper cohort v1.0 Seed-8 execution completed

- Frozen paper manifest `manifests/toolroute_api_paper.v1.0.json` committed and
  bound in `PROVENANCE.json` (SHA-256 `9fb8003e4742b3e94afd872a88522cbe5d238d13ae631c1f0f30c78705789218`).
- Executed the first scheduled paper block (Seed 8, turns 0–3, A/B/C across
  `gpt-5.6-sol`, `claude-sonnet-5`, and `gemini-3.7-flash` = 36 total decisions)
  via isolated per-process invocations stored in `experiments/api-paper-v1.0-seed8/`.
- **Integrity Audit:** Exactly 36/36 expected provider × turn × condition cells
  completed exactly once; 0 provider errors; 0 malformed responses; all 36
  `finalization.json` artifact digests verified; outer `pilot_manifest_sha256`
  consistently bound; Condition B tool symmetry verified across all B prompts.
- **Results Summary (Seed 8):**
  - On Turn 0 (differential tool latency: `tool_beta` 100ms vs `tool_alpha` 180ms):
    All three models chose `tool_alpha` under Condition A (80.0 ms regret) and
    Condition B (80.0 ms regret), while choosing `tool_beta` under Condition C
    (**0.00 ms regret**).
  - On Turns 1, 2, and 3: All three models chose `tool_alpha` (0.00 ms regret)
    across all conditions.
  - Overall Mean Regret across Seed 8: Condition C = **0.00 ms**, Condition B = **20.00 ms**,
    Condition A = **20.00 ms** across all three model families.
  - Attention Tax ($B - A$) = **0.00 ms**; Epistemic Treatment Effect ($C - B$) = **-20.00 ms** (100% regret elimination).
- Authorization immediately revoked in `PROVENANCE.json`.

### 2026-08-30 — Independent Seed-8 artifact audit and cohort pause

- Independently rechecked all 36 artifact directories: exact expected grid,
  no duplicates, no missing cells, all completed with an exact action, all
  finalization hashes valid, exact frozen-manifest hash binding, no API-native
  tool/function fields, symmetric B tool rows, and provider-local execution
  order matching the manifest-salted deterministic ordering.
- The source test suite passed 102/102 tests. The loopback HTTP tests require
  local socket permission and were rerun outside the filesystem sandbox; no
  provider call was made by this audit.
- Found TR-033: the frozen v1.0 manifest states that sampling controls are
  omitted/provider-default, but every recorded Gemini request contains
  `generationConfig.temperature: 0.0`. This is a documentation deviation, not
  a within-Gemini A/B/C confound: all three conditions share the same setting
  and raw requests preserve it. Seed 8 remains in the paper cohort. Before
  resumption, freeze an execution-config clarification and retain the same
  `temperature: 0.0` setting for all later Gemini calls.

### 2026-08-30 — ToolRoute v1.0 execution-config enforcement

- Added frozen companion
  `manifests/toolroute_api_paper.v1.0.execution-config.json` (SHA-256
  `d1cba39f9aec08082d52207aef79a8c0845ff2fccecf528dcf7ebb8bfec45f78`),
  which binds the parent paper manifest and declares the effective request
  fields for all three providers.
- The cohort runner now requires this companion. Authorization checks its hash
  before every request, records its hash in every future episode, and rejects a
  locally constructed request whose adapter/body disagrees with the declaration.
  `PROVENANCE.json` remains false/null; no provider call was made.
- Full local suite: 107 passed. The existing seed-8 artifacts are immutable and
  remain included; the next authorization may run only seeds 9–10 (72
  decisions) under this same effective configuration. Seeds 11–13 require a
  subsequent reviewed continuation configuration.

### 2026-08-30 — ToolRoute paper cohort v1.0 continuation seeds 9–10 completed

- Authorized, executed, audited, and revoked the 72 decisions in the first paper
  continuation block: Seeds 9 and 10 across four turns, A/B/C conditions, and
  three models (`gpt-5.6-sol`, `claude-sonnet-5`, `gemini-3.7-flash`).
- Artifacts stored under `experiments/api-paper-v1.0-seeds9-10/`.
- **Integrity Audit:** Exactly 72/72 unique expected cells completed once (24 per
  model); 0 provider errors; 0 malformed responses; all 72 `finalization.json`
  artifact hashes valid; outer `pilot_manifest_sha256` (`9fb8003e...`) and
  `execution_config_sha256` (`d1cba39f...`) hashes verified; 0 tool/function
  declarations; symmetric B tool rows; 0 retries.
- **Results Summary (Seeds 9 & 10):**
  - **`gpt-5.6-sol`:** Condition C achieved **0.00 mean regret**, 100% success rate,
    160.0 ms mean latency; Condition B: 3,288.51 mean regret (62.5% success);
    Condition A: 3,298.51 mean regret (62.5% success). Treatment effect $C - B = -3,288.51$ ms.
  - **`claude-sonnet-5`:** Condition C achieved **0.00 mean regret**, 100% success rate,
    160.0 ms mean latency; Condition B: 3,298.51 mean regret (62.5% success);
    Condition A: 4,222.22 mean regret (50.0% success). Treatment effect $C - B = -3,298.51$ ms.
  - **`gemini-3.7-flash`:** Condition C achieved **727.06 mean regret**, 87.5% success rate,
    200.0 ms mean latency (chose `wait` on Seed 9 Turn 3); Condition B: 3,298.51 mean regret
    (62.5% success); Condition A: 3,298.51 mean regret (62.5% success). Treatment effect $C - B = -2,571.45$ ms.
- Authorization revoked immediately in `PROVENANCE.json` (`toolroute_provider_trials_authorized: false`).
- Seeds 11–13 remain held pending separate authorization.

### 2026-08-30 — Independent audit of seeds 9–10 continuation

- Independently verified all 72 directories against the expected 3-model ×
  2-seed × 4-turn × A/B/C grid: no missing, duplicate, or out-of-scope cell;
  every terminal classification was `COMPLETED`; every finalization hash,
  parent-manifest hash, and execution-config hash verified.
- Verified no provider-native tool/function field at any request depth, exact B
  row symmetry, and exact cross-provider prompt and host-record equality for
  each seed × turn × condition. Provider-local artifact order matches the
  frozen salted ordering. The 107-test local suite passed after collection; no
  audit provider calls were made.
- No new protocol or capture issue was identified. The sole nonzero Condition-C
  regret in seeds 9–10 is Gemini seed-9/turn-3 choosing `wait` (5816.47 ms);
  it is a valid completed observation, not an artifact anomaly or a retry case.

### 2026-08-30 — Final ToolRoute continuation scope frozen

- Added a separate immutable execution-config companion for the final seeds
  11–13 only (SHA-256
  `0a12df01886f7e33f362cb7b23dba691efdbfea1bc11c98d44a409193f1bd35c`). It preserves the completed blocks and the effective provider
  settings (including Gemini `temperature: 0.0`) while limiting the remaining
  authorization to exactly 108 decisions.
- `PROVENANCE.json` remains false/null. No provider call is authorized by this
  commit; the final execution agent must verify, bind, and later revoke this
  companion's hash.

### 2026-08-30 — ToolRoute paper cohort v1.0 final continuation seeds 11–13 completed

- Authorized, executed, audited, and revoked the 108 decisions in the final paper
  continuation block: Seeds 11, 12, and 13 across four turns, A/B/C conditions,
  and three models (`gpt-5.6-sol`, `claude-sonnet-5`, `gemini-3.7-flash`).
- Artifacts stored under `experiments/api-paper-v1.0-seeds11-13/`.
- **Integrity Audit:** Exactly 108/108 unique expected cells completed once (36 per
  model); 0 provider errors; 0 malformed responses; all 108 `finalization.json`
  artifact hashes valid; outer `pilot_manifest_sha256` (`9fb8003e...`) and
  `execution_config_sha256` (`0a12df01...`) hashes verified; 0 tool/function
  declarations; symmetric B tool rows; 0 retries.
- **Factual Results Summary (Seeds 11–13):**
  - **`gpt-5.6-sol`:** Condition C: mean regret 151.00 ms (91.7% call success, 186.7 ms latency);
    Condition B: mean regret 4,414.99 ms (75.0% success, 1,506.7 ms latency);
    Condition A: mean regret 7,241.95 ms (58.3% success, 2,176.7 ms latency).
  - **`claude-sonnet-5`:** Condition C: mean regret 151.00 ms (91.7% call success, 186.7 ms latency);
    Condition B: mean regret 7,241.95 ms (58.3% success, 2,176.7 ms latency);
    Condition A: mean regret 7,241.95 ms (58.3% success, 2,176.7 ms latency).
  - **`gemini-3.7-flash`:** Condition C: mean regret 0.00 ms (100.0% call success, 160.0 ms latency);
    Condition B: mean regret 7,241.95 ms (58.3% success, 2,176.7 ms latency);
    Condition A: mean regret 7,241.95 ms (58.3% success, 2,176.7 ms latency).
- Authorization revoked immediately in `PROVENANCE.json` (`toolroute_provider_trials_authorized: false`).
- All 216 planned paper cohort decisions across Seeds 8–13 are now executed and finalized.

### 2026-08-30 — Independent final paper-cohort audit

- Verified the full planned cohort end to end: 36 seed-8 + 72 seeds-9–10 +
  108 seeds-11–13 artifacts = exactly 216 unique provider × seed × turn ×
  condition cells, with no missing, duplicate, or out-of-scope record.
- Every result is `COMPLETED`; every finalization digest verifies; every block
  carries the parent manifest hash and the appropriate continuation-config hash.
  Cross-provider prompt and host records match for each seed × turn ×
  condition; B rows are symmetric; no request contains an API-native
  tool/function field; and no retry occurred.
- Final regression check: 107 tests passed. Authorization remains false/null.
  Collection is complete; this audit makes no inferential claim. The next work
  is frozen-cohort analysis and manuscript framing, not further provider calls.
