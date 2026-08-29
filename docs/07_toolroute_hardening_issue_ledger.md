# ToolRoute Hardening Issue Ledger

This is a development-quality ledger, not a results report.  Entries remain
part of the provenance record even after remediation; no existing experiment
artifact is modified or removed.

| ID | Status | Finding | Effect on interpretation | Disposition |
| TR-022 | Fixed | API preflight could have been enabled by a caller-supplied boolean, which was not an auditable authorization boundary. | A local caller could bypass the intended approval record. | Replaced with provenance- and frozen-manifest-hash-bound `ToolRouteAuthorization`; default provenance remains false/null. |
| TR-023 | Open operational | Homebrew cannot install optional Toxiproxy because `/opt/homebrew` is not writable by the user. | Socket-level adapter validation cannot run in the current environment. | Adapter and loopback contract tests pass; no sudo or ownership mutation attempted. Does not block synthetic ToolRoute preflight. |
|---|---|---|---|---|
| TR-001 | Fixed | Tier-2 rendering projected imperative host constraints. | Confounds telemetry with direct policy advice. | Tier-2 now excludes `recommended_constraints`; retain host-side only. |
| TR-002 | Fixed | Cross-process continuation supplied a sparse delta as the reducer prior. | Could erase unobserved state namespaces. | Persist a private cumulative rehydrated snapshot and resume from it. |
| TR-003 | Fixed | `wait` regret had no task semantics. | Could label a missed required record as a wise route choice. | A wait now carries a frozen missed-record penalty in ToolRoute. |
| TR-004 | Fixed | Development artifacts were exclusive-create but not durable/finalized. | Interrupted records and later tampering were not detectable. | Publish via fsync/link and write terminal artifact hashes. |
| TR-005 | Mitigated | B used repeated-character padding. | It is byte-matched but not a valid token/attention control. | Use varied opaque text, call it UTF-8 byte-matched only; provider study must pin a tokenizer. |
| TR-006 | Open | Synthetic probe exposes a perfect state-derived health signal. | Measures response to a perfect simulated observation, not a real noisy monitor. | Keep development-only; predeclare/calibrate an observation model before a pilot. |
| TR-007 | Open | Fresh Codex subagents can read the shared workspace. | No blinding; records cannot enter a paper denominator. | Require an isolated runner before empirical collection. |
| TR-008 | Open | A/B/C generations are independent. | Same fault tape does not make the model outputs paired. | Treat smoke comparisons descriptively only. |
| TR-009 | Rejected | HTTP statuses allegedly populated `runtime.last_exit.class`. | No current code path does this. | No change without a reproducing test. |
| TR-010 | Rejected | A prose substring parser allegedly inverted action intent. | Current exact-label validation already fails closed. | Retain/add regression coverage; no parser rewrite. |
| TR-011 | Fixed | Hashed action ordering left `tool_beta` first on every turn of the first v0.2 triad. | The apparent C route preference was position-confounded. | Use a six-seed balanced permutation block plus within-trajectory cyclic rotation; retain v0.2 as a diagnostic only. |
| TR-012 | Fixed | CLI rejected malformed output before archiving it. | Violates retain-every-attempt and leaves a pending trial without provenance. | Archive a per-turn rejection record, fail closed, and permit a fresh replacement response. |
| TR-013 | Fixed operationally | A coordinator abbreviated emitted B/C messages before handoff. | The decision subject would not receive its assigned condition verbatim. | Submitted no actions, finalized the starts as `ABORTED_DEVELOPMENT`, and delegated exact-message handoff to a dedicated host coordinator. |
| TR-014 | Open operational | The platform retained completed child threads against the fresh-subagent concurrency cap. | Prevented completion of the predeclared six-seed block without reusing a subject. | Finalize only completed trajectories; leave unsubmitted starts untouched and resume in a fresh task/session with new subjects. |
| TR-015 | Fixed in v0.4 | Primary oracle used latent reliability unavailable in rendered telemetry. | Penalized reasonable observable decisions and invalidated oracle agreement. | Primary oracle now uses only monitor fields rendered to C; latent oracle is diagnostic only. |
| TR-016 | Fixed in v0.4 | Monitor signal was a thresholded projection of hidden probability. | Not a credible measurement process. | Use separately seeded probe outcomes, independent from action potential outcomes. |
| TR-017 | Open operational | Fresh-subagent capacity was exhausted after v0.4 review despite a successful capacity probe. | Prevented two planned v0.4 A/B/C triads before their first action. | Six empty starts were finalized as `ABORTED_DEVELOPMENT`; resume only in a fresh task/session. |
| TR-018 | Fixed for future runs | In the seed-34/B turn-0 v0.4 handoff, the required subject-only suffix immediately followed a no-terminal-newline emitted message without a separating newline. Both strings were preserved byte-for-byte, and later no-newline handoffs used a separator. | Creates a one-turn handoff-format inconsistency in a development-only trajectory. | Preserve the affected trajectory as a diagnostic. `smoke_cli` now emits and archives a frozen `subject_prompt` with a constant double-newline delimiter; future cohort inputs are auditable in `turn-XX-handoff.json`. |
| TR-019 | Open | No provider-call adapter, provider request/response capture path, or tokenizer-pinned B-control constructor is frozen. | The offline smoke runner cannot itself produce an API-study denominator. | After G1/G2 close, implement and test a reservation-first, isolated API runner; freeze model/version, tokenizer, retry policy, raw request/response capture, and cost accounting before any provider request. |
| TR-020 | Open interpretation | The post-fix seeds 50–54 block was reported as five “matched empirical triads” with a statistically significant effect. It contains independent shared-workspace subagent generations, is not tokenizer-matched, and stops one seed short of the documented six-seed counterbalancing block. | The observed C-versus-A/B pattern is a reproducible development signal, not an estimable treatment effect or an attention-tax result. | Preserve and audit all artifacts. Relabel the cohort development-only; do not run inferential statistics or include it in paper data. A future provider study must use the frozen isolated, tokenizer-matched, randomized protocol. |
| TR-021 | Open design choice | Fresh-subagent smoke decisions receive a delta-labelled current prompt without the prior base snapshot, while a normal persistent agent would retain the prior state. Current ToolRoute tool entries happen to contain all facts used by its oracle. | The smoke path validates current-state action capture, not sparse-delta comprehension or a persistent-agent history effect. | Freeze one API-pilot mode before collection: either persistent trajectories with complete prior message history and deltas, or independent decision episodes with full checkpoints only. Do not mix modes in one denominator. |

## Handoff rule

Before any ToolRoute run is discussed outside development, verify that every
terminal directory includes `manifest.json`, per-turn input/host/result files,
and `finalization.json`; then assess all open ledger items.  Passing local
smoke runs do not close an open issue.
