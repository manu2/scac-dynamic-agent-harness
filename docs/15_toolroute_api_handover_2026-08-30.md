# ToolRoute API Handover — 2026-08-30 (historical; superseded)

> This handover predates the final fixed-structure B-control decision. Do not
> follow its tokenizer-matching instructions; use `PROTOCOL.md`,
> `docs/07_toolroute_hardening_issue_ledger.md`, and the current final manifest.

## Current truth

- Branch and remote head: `codex/g0-sst-schema`, commit `3b8a564`.
- `PROVENANCE.json` has `toolroute_provider_trials_authorized: false`.
- The selected first-paper cohort is GPT-5.6 Sol, Claude Sonnet 5, and Gemini
  3.7 Flash. Terra and Opus are retained diagnostic history only. Sonnet and
  Gemini have clean ToolRoute transport diagnostics; Sol has successful prior
  project API precedent but still needs its own ToolRoute C-only smoke before a
  balanced cohort.
- `.env` is copied locally, mode 600, and ignored by Git. Never print, stage,
  hash, or copy it into an artifact.
- Toxiproxy is frozen and out of scope. RetryBudget and MemoryGovernor are out
  of scope. Do not run fresh-subagent smoke trajectories.
- The future paper cohort remains synthetic ToolRoute: independent full
  checkpoints; six seeds x four turns x A/B/C = 72 decisions per model; B is a
  same-shape equal-tool neutral table and provider token usage is descriptive.

## Completed non-paper API transport smoke

All attempts used seed 0, turn 1, Condition C only, no tools, temperature 0,
and a 1024 output cap. This is a transport diagnostic, not an A/B/C comparison
and not paper evidence.

| Provider/model | Classification | Finding | Artifact |
|---|---|---|---|
| Gemini 3.7 Flash | `COMPLETED` | `tool_alpha`; observable and latent regret 0; 343 input / 179 output tokens; normal STOP | `experiments/api-transport-smoke/api-preflight/toolroute/20260829T212006.505625Z-C-c023a7f749db487fae9ac5c16e374169/` |
| GPT-5.6 Terra | `PROVIDER_ERROR` | HTTP 400 before inference; no retry | `experiments/api-transport-smoke/api-preflight/toolroute/20260829T212032.613836Z-C-dacd723d0e2a4da88f65b47a13899dbb/` |
| Claude Opus 5 | `PROVIDER_ERROR` | HTTP 400 before inference; no retry | `experiments/api-transport-smoke/api-preflight/toolroute/20260829T212105.365870Z-C-932695ebde0a440894dc64f4513f2587/` |

All 18 listed transport-smoke artifact hashes verify. The Gemini result is
consistent with the current observable oracle, but is one diagnostic choice
only—not evidence of telemetry improvement. The initial OpenAI/Anthropic error
bodies were intentionally not retained; do not reinterpret those 400s as model
behavior or silently replace them.

## What changed after the failures

TR-028 is fixed for future attempts: provider HTTP error bodies are now retained
as structured JSON after recursive API-key redaction. Existing artifacts are
immutable and cannot gain this missing detail retroactively.

The authorization check now validates the exact seed, turn, condition, model,
and provider listed in the frozen manifest. A hash match alone cannot authorize
an extra paid call.

## Required next sequence

1. Read `AGENTS.md`, `PROTOCOL.md`, `PROVENANCE.json`, this handover, and
   `docs/07_toolroute_hardening_issue_ledger.md` before editing or calling a
   provider.
2. Diagnose the OpenAI and Anthropic 400s against each provider's current
   official API reference. Update the adapters and add mocked regression tests;
   do not reuse or alter the finalized failed directories.
3. Run ` .venv/bin/python -m pytest -q` and inspect the changed request payloads.
   Use Gemini only for any new cheap transport diagnostic unless a revised
   manifest explicitly authorizes a different provider.
4. Create a **new** committed, C-only transport manifest that enumerates each
   new attempt exactly. Bind its SHA-256 in `PROVENANCE.json`, set only
   `toolroute_provider_trials_authorized` true, commit and push, then run it.
   After each submitted call, audit `provider-request.json`, raw provider
   response/error, `result.json`, and `finalization.json`; revoke authorization
   again before any code repair.
5. Only after all three providers complete a clean C-only diagnostic, design
   and freeze the separate balanced A/B/C canary manifest. It must use the
   exact provider tokenizer for B. Do not enable the paper cohort merely
   because a transport smoke passes.

## Execution commands (only after steps 2–4)

```sh
.venv/bin/python -m pytest -q
.venv/bin/python scripts/run_toolroute_transport_smoke.py \
  --provider google --model gemini-3.7-flash
```

The runner reads `.env` into process memory only and prints only trial path and
classification. It may make a paid request; never run it while provenance is
false or against an undeclared episode.

## Handover prompt

> Continue ToolRoute only from `docs/15_toolroute_api_handover_2026-08-30.md`.
> Do not make provider calls until you have repaired and mock-tested the
> OpenAI/Anthropic 400 path, committed a newly enumerated C-only smoke manifest,
> and bound its SHA-256 in `PROVENANCE.json`. Preserve every existing artifact;
> do not retry or pool the three completed transport-smoke attempts. Use Gemini
> 3.7 Flash for initial debugging. Keep Toxiproxy, RetryBudget, and
> MemoryGovernor out of scope. After each authorized call, verify all terminal
> hashes and update EXECUTION_TRACKER.md and the issue ledger.
