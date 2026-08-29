# ToolRoute v0.4 Seeds 50–54 Development Cohort Audit

**Date:** 2026-08-29
**Stage:** local development smoke and harness hardening
**Status:** not empirical data; not a paper cohort; no provider/API calls

## Scope

This audit covers terminal A/B/C trajectories for seeds 50–54 under
`ToolRoute-v0.4`. The word “cohort” here identifies an artifact set, not a
statistical sample. The runs used fresh Codex subagents for each decision, but
those subagents had shared workspace access. They are therefore development
diagnostics under the repository protocol.

## Verified provenance

| Check | Result |
|---|---|
| Terminal trajectories | 15: one A, B, and C directory for each of five seeds |
| Hash finalization | 15/15 finalization manifests verify every listed artifact |
| Decision subjects | 51/51 recorded subject identifiers are unique |
| Handoff capture | Every submitted decision has a `turn-XX-handoff.json` artifact |
| B/C byte control | No byte-length mismatch for B and C at corresponding seed/turns |
| Provider status | No provider/API request; `provider_trials_authorized: false` |

Each directory retains its condition message, exact subject prompt, host probe
events, snapshots, action response, primary observable-oracle regret,
clairvoyant diagnostic regret, terminal classification, and hashes.

## Descriptive outcomes

| Condition | Terminal completion | Calls | Successful calls | Mean cumulative primary regret | Mean latency |
|---|---:|---:|---:|---:|---:|
| A | 4/5 | 18 | 14 | 13,426.92 | 4,620 ms |
| B | 4/5 | 18 | 14 | 13,426.92 | 4,620 ms |
| C | 5/5 | 15 | 15 | 0.00 | 460 ms |

The C actions agree with the observable-only primary oracle at every recorded
turn. A and B followed the same action pattern in this artifact set. Thus the
harness has repeatedly captured the behavior it was built to diagnose: subjects
given the synthetic monitor chose the route preferred by that monitor, while
subjects without it often selected the poor route.

## What cannot be concluded

Do **not** call these five seed triads matched, isolated, statistically
significant, or empirical. In particular:

- each condition uses independent model generations, so same-seed condition
  labels do not create paired observations;
- the subjects could inspect the shared workspace, eliminating blinding;
- B is UTF-8 byte matched only, not provider-tokenizer matched;
- five consecutive seeds omit one of the six turn-zero action permutations
  required by the documented counterbalancing block; and
- monitor observations are controlled synthetic probes, not a validated live
  telemetry process.

The equality of A and B in this small artifact set does not establish “zero
attention tax.” The C pattern is promising engineering evidence, not an
estimated causal effect.

## Correct next steps

1. Preserve this artifact set and use it only for capture, prompt, parser,
   reducer, and evaluator regression checks.
2. Do not collect more local fresh-subagent trajectories unless investigating a
   new defect; this path has served its hardening purpose.
3. Pass Linux cgroup-v2 G1, then G2 clean-container and context-isolation/
   evaluator-defeat reviews.
4. Freeze an isolated provider pilot with a pinned model/tokenizer, a
   tokenizer-matched B control, randomized assignment, exact request/response
   capture, and a predeclared analysis/power plan.

See `docs/07_toolroute_hardening_issue_ledger.md` (TR-020) and
`docs/10_toolroute_v0_4_status_and_next_gate.md` for the controlling
interpretation and gate status.
