# ToolRoute OTel/Toxiproxy v0.2 provider runbook

**Status:** code and model-free controls validated; provider authorization is
currently **false**. This runbook is the only approved execution path after a
separate reviewer explicitly freezes and hash-binds the v0.2 manifest.

## Purpose and boundary

v0.2 is a fresh, separately labelled transport-integration replication. It
does not repair, replace, or pool the completed v0.1 Gemini pilot or the frozen
216-decision synthetic ToolRoute v1.0 cohort. Every episode runs a real local
HTTP request through Toxiproxy, derives the model-visible snapshot from standard
OpenTelemetry HTTP client spans, and sends only the resulting decision prompt
to the provider.

The manifest is the source of truth for all 27 episodes. It fixes the model,
provider, regime, condition, faulted route, option order, and per-model run
sequence. The command accepts only `--episode-id`: do not add condition,
fault, option-order, retry, or sampling overrides.

## Pre-call gate

Run these read-only checks before changing authorization:

```bash
git status --branch --short
.venv/bin/pytest -q
.venv/bin/python -c 'import json; from pathlib import Path; from scac_harness.otel_transport_manifest import validate_cross_model_pilot_manifest; validate_cross_model_pilot_manifest(json.loads(Path("manifests/toolroute_otel_transport_pilot.v0.2.json").read_text())); print("manifest valid")'
```

Use an executable local Toxiproxy binary. It is intentionally not committed:
platform binaries do not belong in the source repository. Record its SHA-256 in
each episode artifact; the runner does this automatically. The current local
Mac binary is Toxiproxy 2.11.0 with SHA-256
`fb9085e232ffe7bfdae3a0be8da5f041cc66fb75740ec173173b5b3cc1b35750`.
If another binary is used, retain its different artifact hash and do not claim
binary identity.

Only after these checks and independent review:

1. Change the v0.2 manifest status from `DRAFT_NOT_AUTHORIZED` to
   `FROZEN_AUTHORIZED`.
2. Compute its SHA-256.
3. Set `toolroute_otel_transport_provider_trials_authorized` to `true` and
   `toolroute_otel_transport_pilot_manifest_sha256` to that exact digest in
   `PROVENANCE.json`.
4. Commit those two exact files before the first provider request. Do not edit
   the manifest or provenance while a block is running.

## Execution order

Run **only Gemini v0.2 first**, in `sequence` order 0 through 8. After those
nine calls, revoke authorization, audit the complete block, and stop. Do not
start Sonnet or GPT during the same handoff. The exact Gemini episode ids are:

```text
gemini-00-connection-c
gemini-01-latency-a
gemini-02-http-b
gemini-03-latency-c
gemini-04-connection-a
gemini-05-http-c
gemini-06-latency-b
gemini-07-connection-b
gemini-08-http-a
```

For each id, invoke exactly:

```bash
.venv/bin/python scripts/run_toolroute_otel_transport_cohort.py \
  --episode-id <EXACT_ID> \
  --toxiproxy-server tools/toxiproxy-server
```

The command reserves its directory before the provider request, validates the
authorization immediately before transport, keeps HTTP backends/proxy/monitor
alive through action execution, and finalizes hashes whether the result is a
success, malformed model response, or provider error. Never retry an episode:
the attempted artifact is its denominator record.

## Mandatory post-block audit

Confirm all nine expected directories exist under
`experiments/api-otel-transport-v0.2/g2-calibrations/toolroute-otel-transport/`.
For each, require:

- `finalization.json` hashes validate every listed artifact;
- manifest contains `evidence_class=provider_transport_pilot`, model/provider,
  episode id, sequence, authorization-manifest SHA, frozen option order, and
  Toxiproxy binary SHA;
- exactly six monitor spans: three per tool, all from
  `otel_requests_http_client_span_v1`;
- condition input has no visible snapshot for A/B and carries the exact
  truthful snapshot only for C;
- `model-decision.json` records the raw parsed action, observable best action,
  actual regret, and `selected_action_is_observable_best` without a forced
  pass value;
- `result.json` separates infrastructure checks from the observed model
  outcome, and the post-decision action matches the selected action.

Revoke the provenance authorization after the ninth artifact. A second reviewer
must inspect the block before any Sonnet or GPT episode is authorized.

## Prompt for a worker agent

> Work only in `scac-dynamic-agent-harness`. Read `README.md`, `PROTOCOL.md`,
> `PROVENANCE.json`, `manifests/toolroute_otel_transport_pilot.v0.2.json`, and
> `docs/25_toolroute_otel_transport_v0_2_runbook.md`. Do not modify source,
> prompts, manifest, provenance, or prior artifacts. First run the prescribed
> pre-call checks. If authorization is not exactly hash-bound and true, stop
> without making any API request. If it is true, execute only the nine Gemini
> episode ids in ascending sequence, one command per id, with no retry. After
> each command, verify its terminal classification and finalization hashes.
> After the ninth, revoke the authorization, write a factual report listing all
> artifact directories and any non-completed classifications, then stop. Do not
> run Sonnet or GPT and do not make claims from aggregate numbers.
