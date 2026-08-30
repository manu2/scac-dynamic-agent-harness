# ToolRoute v0.4 Fresh-Subagent Execution Playbook

## Purpose and boundary

Run **two complete development-only A/B/C triads** for ToolRoute v0.4 using
seeds `34` and `35`. This is a harness-validation exercise, not provider
evidence or paper data. No API/provider calls are authorized.

## Preflight: all checks must pass

From the repository root, read `README.md`, `RESEARCH_ROADMAP.md`,
`EXECUTION_TRACKER.md`, `PROTOCOL.md`, and `PROVENANCE.json`, then run:

```sh
.venv/bin/pytest -q
git diff --check
```

Require 82 or more passing tests (or a documented higher count), zero test
failures, and no whitespace errors. Confirm `PROVENANCE.json` still says
`provider_trials_authorized: false`.

## Non-negotiable execution rules

1. Use `ToolRoute-v0.4` only. Never resume a v0.3 directory.
2. For **every single decision turn**, create a brand-new subagent with
   `fork_turns="none"`.
3. Give that subject only the exact `subject_prompt` returned by `smoke_cli
   start` or `smoke_cli next`. Do not concatenate, trim, abbreviate, reformat,
   summarize, or add context. The CLI freezes the condition message, a constant
   double-newline delimiter, and the subject-only instruction in a per-turn
   `turn-XX-handoff.json` artifact.
4. Submit the subject’s exact raw response and identifier. If it is malformed,
   submit it anyway so the host archives a rejection, then create another fresh
   subject for the same still-pending turn.
5. Do not edit source, prompts, scenarios, artifacts, or documentation during
   the cohort. Do not reuse a decision subject.
6. If fresh-subagent creation is unavailable, stop. Finalize any starts with
   `smoke_cli abort --reason fresh_subject_capacity_unavailable`; do not use a
   scripted substitute or an old subject.

## Per-condition lifecycle

```sh
.venv/bin/python -m scac_harness.smoke_cli start --seed 34 --condition C
.venv/bin/python -m scac_harness.smoke_cli submit \
  --trial-dir '<trial-dir>' --subject-id '<fresh-agent-id>' \
  --response '<exact-raw-response>'
.venv/bin/python -m scac_harness.smoke_cli next --trial-dir '<trial-dir>'
```

Repeat until the `submit` output reports `terminal: true`. Run A, B, and C for
seed 34, then A, B, and C for seed 35. Conditions may be started sequentially
to conserve subagent slots; use fresh subjects for every decision regardless.

## Required end-of-cohort audit

For every terminal directory:

1. Verify `finalization.json` hashes every listed artifact correctly.
2. Record action sequence, completion, primary `policy_regret`, secondary
   `clairvoyant_regret_diagnostic`, latency, rejected-response count, terminal
   classification, and hash result.
3. Check that every C host artifact identifies
   `synthetic_host_probe_v0.4`, that its prompt contains no `HOST_CONSTRAINTS`,
   and that every result includes both oracle metrics.
4. Update `EXECUTION_TRACKER.md` and `docs/07_toolroute_hardening_issue_ledger.md`
   with facts only. Do not claim a treatment effect.

## Interpretation rule

The two triads demonstrate end-to-end local behavior only. They may reveal
capture, monitor, prompt, parser, scoring, or evaluator defects. They cannot
be pooled with provider trials or described as blinded empirical evidence.
