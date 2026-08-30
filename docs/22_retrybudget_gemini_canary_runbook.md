# RetryBudget v0.2 Gemini C-Only Canary Runbook

**Status:** prepared and intentionally unauthorized. This is a development
transport/capture canary, not paper evidence.

## Purpose

Run exactly one independent-full-checkpoint RetryBudget trajectory: seed 61,
condition C, Gemini 3.7 Flash, maximum seven provider generations. Verify that
the provider follows exact action-label instructions, fresh checkpoints advance
correctly, and every partial/error/complete trajectory finalizes. Do not infer a
telemetry effect from this C-only canary.

## Frozen inputs

- Manifest: `manifests/retrybudget_api_canary.v0.2.json`
- Provider: `gemini-3.7-flash`, Google GenerateContent API
- Request settings: `temperature: 0.0`, `maxOutputTokens: 16`, no native tools
  or system instruction
- Authorization field: `retrybudget_provider_trials_authorized` in
  `PROVENANCE.json`, currently `false`
- State delivery: independent full checkpoints; every turn is a new provider
  generation with no supplied history

## Required review before enabling

1. Confirm the manifest SHA-256 and its seven-generation maximum.
2. Confirm that the scenario's v0.2 transition/oracle, neutral B envelope,
   action-position balance, fixed-policy check, and write-once runner remain
   green.
3. Explicitly approve a **narrow RetryBudget development-canary exception** to
   the global provider prohibition in `PROTOCOL.md`. The exception must apply
   only to this manifest, seed, condition, provider/model, and development
   classification; it must not authorize a paper cohort.
4. In one atomic reviewed change, set the provenance authorization field to
   `true`, set `retrybudget_pilot_manifest_sha256` to the actual manifest digest,
   and update `authorization_scope`. Commit that authorization before execution.
5. Set `GEMINI_API_KEY` only in the process environment. Never add it to the
   repository or a manifest.

## Command after authorization

```zsh
.venv/bin/python scripts/run_retrybudget_api_canary.py
```

The launcher fails before transport if provenance, manifest scope, provider
adapter, model endpoint, static generation configuration, or key environment is
wrong. It rechecks authorization immediately before every provider generation.

## Required post-run audit

1. Verify one newly reserved directory under
   `experiments/api-preflight/retrybudget-v0-2/`.
2. Confirm it contains `manifest.json`, per-turn input/host/provider-request/
   provider-response/result files, and `finalization.json`.
3. Verify every finalization SHA-256 and terminal classification. A provider
   error, malformed output, or revoked authorization is a retained failed
   development attempt, not a reason to retry under the same authorization.
4. Confirm the provider request contains no `tools` or `systemInstruction`, and
   retains `temperature: 0.0` and `maxOutputTokens: 16` on every turn.
5. Revoke authorization in a separate committed record immediately after the
   one declared trajectory. Do not convert this canary into paper data.
