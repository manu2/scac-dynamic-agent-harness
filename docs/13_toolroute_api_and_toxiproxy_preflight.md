# ToolRoute API and optional Toxiproxy preflight

**Status:** implementation and local tests complete; provider use prohibited.

## Purpose and scope

The ToolRoute API cohort is an independent one-decision-per-episode study. For
each episode, the local harness derives a complete current monitor checkpoint,
renders the assigned condition, writes immutable input artifacts, and only then
sends one prompt to a tool-less remote model. The provider receives no tool,
schedule, oracle, filesystem capability, or artifact path. The local process
retains schedule, evaluator, raw host events, response, and terminal hashes.

This is separate from `experiments/dev-smoke/`; the two record sets cannot be
pooled.

## Controls now implemented

- `ToolRouteAPIEpisode` reserves `experiments/api-preflight/toolroute/<id>/`
  before any request, captures prompt/host/response/result, then finalizes JSON
  artifact hashes.
- Each decision sends a full checkpoint with `base_snapshot_id: null`; no prior
  conversation state is required.
- A, B and C share task/options. B is matched to the supplied tokenizer; a
  paper run must inject a pinned provider tokenizer, never `WhitespaceTokenizer`.
- `ToolRouteAuthorization.load` binds provenance to the SHA-256 of a committed
  frozen manifest. A caller boolean cannot enable a request. Repository
  provenance remains false with a null hash.
- The versioned synthetic observation model records probe count, label error,
  event loss and delivery delay. Non-zero settings are sensitivity calibration,
  not silently mixed into a primary cohort.
- Unit tests defeat fixed alpha, fixed beta, and fixed wait policies over the
  six-seed/four-turn rotation.

## Remaining ToolRoute pilot freeze work

1. Select provider/model and obtain its exact tokenizer/version.
2. Copy and complete `manifests/toolroute_api_pilot.template.json`, then freeze
   model/version, tokenizer/version, parameters, parser, no-retry policy,
   seeds/randomization, observation baseline/sensitivity grid,
   inclusion/exclusion rules, and analysis/power plan in a pilot manifest.
3. Retain model-free calibration for the frozen baseline and each declared
   sensitivity point; verify the observable-oracle margin for eligible states.
4. Commit the manifest. Only explicit review may bind its SHA-256 in provenance
   and set `toolroute_provider_trials_authorized` true. That has not happened.

## Optional local Toxiproxy validation

Toxiproxy is a realism/adapter validation, not a prerequisite or substitute for
the causal synthetic cohort. It places real local HTTP services behind local
fault proxies. `capture_http_tool_span` converts observed status and latency to
the same host event the reducer consumes. It tests collection over sockets, not
whether the model sees different information than from a correctly rendered
synthetic monitor.

Once available locally: start two loopback services and `toxiproxy-server`,
precommit a proxy schedule, capture no-fault and injected-fault spans, retain
the proxy schedule/spans/checkpoint/final hashes, and verify reducer-renderer
agreement. Do not combine these adapter records with synthetic API outcomes.

The first completed local validation used Shopify Toxiproxy v2.12.0 for macOS
ARM, downloaded to a temporary directory and SHA-256-verified against the
official release checksum. It retained two successful baseline spans, a 152 ms
injected-latency alpha span, and a disabled-proxy beta `CONNECTION_ERROR` span
under `experiments/adapter-validation/toolroute/`. Three attempts exist: the
first failed closed on an invalid error label, the second exposed a validator
script finalization bug after completing its telemetry work, and the third is
the clean completed run. All three are finalized and hash-valid. Homebrew was
not used and no system ownership or permission was changed.
