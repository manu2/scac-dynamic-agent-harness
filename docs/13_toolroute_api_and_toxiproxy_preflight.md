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
   The v0.6 calibration has now done this across six seeds and four turns:
   baseline, 10% label error, 10% event loss, and 500 ms delivery age each
   retain all 24 states with an 80 ms minimum margin; 2.5 s delivery age
   excludes all 24 states rather than scoring stale telemetry. The earlier
   v0.5 calibration is retained but superseded because it hid delivery age by
   shifting probe timestamps.
4. Commit the manifest. Only explicit review may bind its SHA-256 in provenance
   and set `toolroute_provider_trials_authorized` true. That has not happened.

## Frozen optional Toxiproxy work

Toxiproxy is a realism/adapter validation, not a prerequisite or substitute for
the causal synthetic cohort. It places real local HTTP services behind local
fault proxies. `capture_http_tool_span` converts observed status and latency to
the same host event the reducer consumes. It tests collection over sockets, not
whether the model sees different information than from a correctly rendered
synthetic monitor.

No further Toxiproxy work is planned for the first paper. Do not combine these
adapter records with synthetic API outcomes.

The first completed local validation used Shopify Toxiproxy v2.12.0 for macOS
ARM, downloaded to a temporary directory and SHA-256-verified against the
official release checksum. It retained two successful baseline spans, a 152 ms
injected-latency alpha span, and a disabled-proxy beta `CONNECTION_ERROR` span
under `experiments/adapter-validation/toolroute/`. Three attempts exist: the
first failed closed on an invalid error label, the second exposed a validator
script finalization bug after completing its telemetry work, and the third is
the clean completed run. All three are finalized and hash-valid. Homebrew was
not used and no system ownership or permission was changed.

## Frozen fresh-subagent end-to-end smoke

`scripts/toxiproxy_subagent_smoke.py` is a separate development-only,
one-decision transport-strategy smoke. `start` launches two loopback proxy
routes, precommits a 300 ms alpha latency versus a healthy beta route, captures
three real monitor spans per route, and freezes the exact A/B/C subject prompt.
`submit` accepts a fresh subject's exact action label, executes that action
through the same still-running proxy, retains its action span, closes the local
processes, and finalizes the artifact. A cross-session run exposed backend
lifecycle reaping between start and submit (TR-025), so this path is frozen
rather than repaired for the first paper. Artifacts are under
`experiments/dev-smoke-toxiproxy/` and are never paper or API-cohort evidence.
