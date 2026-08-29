# ToolRoute v0.6 API Run Readiness

**Status:** superseded as the live handoff by
`docs/15_toolroute_api_handover_2026-08-30.md`. One C-only transport smoke per
provider has been attempted and finalized; no paper cohort is authorized.

## What is complete

- The study unit is one isolated, independent full-checkpoint decision.
- Each six-seed block contains four turns and three information conditions:
  72 provider requests per model (6 x 4 x 3).
- The v0.6 synthetic observation model has retained baseline, label-error,
  event-loss, freshness, and stale-exclusion calibration artifacts.
- The primary oracle uses only monitor facts visible to Condition C; latent
  regret remains diagnostic only.
- The runner reserves an artifact directory before a request, captures the
  exact prompt and provider response, rejects malformed labels, and finalizes
  content hashes.
- Toxiproxy is frozen as a non-paper adapter diagnostic. It is neither a
  prerequisite nor part of the ToolRoute API denominator.

## Exact actions remaining before the first API call

1. Choose the model/provider cohort and confirm each API adapter and exact
   tokenizer implementation. A byte or whitespace-token control is not valid
   for paper data.
2. Create a committed pilot manifest from
   `manifests/toolroute_api_pilot.template.json`. It must include the frozen
   model/version, tokenizer/version, output cap, parameters, six seeds,
   condition randomization, baseline, sensitivity analysis, exclusions, and
   analysis plan.
3. Review the manifest, set only the ToolRoute-specific provenance authorization
   to true, and bind the manifest SHA-256. Do not change the generic global
   authorization or authorize another scenario.
4. Run a six-seed canary. Audit provider-reported input/output tokens, raw
   response parsing, and every finalization hash. Keep it outside the main
   denominator.
5. Without changing the frozen contract, run the precommitted main cohort and
   analyze each model independently. Preserve malformed and failed requests.

## Recommended first-paper execution scale

- Canary: one six-seed block on one provider model (72 requests).
- Main: two new six-seed blocks per model (144 requests per model; 48
  independent decisions per condition/model).
- Three models: 432 main requests; 504 requests including the one-model
  canary.

This is a synthetic-monitor ToolRoute paper study. It tests whether truthful,
structured current observations improve route choice under the frozen simulated
measurement process; it does not claim a live-outage or Toxiproxy result.

## Explicitly out of scope

- Linux cgroup-v2 enforcement and MemoryGovernor evidence.
- RetryBudget redesign or collection.
- New local fresh-subagent trajectories.
- Further Toxiproxy work.
