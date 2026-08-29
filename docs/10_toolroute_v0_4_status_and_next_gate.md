# ToolRoute v0.4 Status and Next Gate

**Recorded:** 2026-08-29  
**Scope:** local development smoke only; no provider/API calls

## Verified local state

ToolRoute v0.4 is a working engineering harness. It separates latent tool
health, independently seeded synthetic monitor probes, the reduced
model-visible projection, and action potential outcomes. Its primary oracle is
limited to canonical monitor facts rendered to Condition C; latent expected
cost remains a diagnostic only. A/B/C messages, raw responses, monitor events,
results, rejections, terminal classifications, and finalization hashes are
preserved under `experiments/dev-smoke/`.

The seed 34–35 block used a distinct fresh-context subagent for every captured
decision. All six terminal artifact hash sets verified; no response was
malformed or rejected; C prompts had no `HOST_CONSTRAINTS`; and C monitor
events were labelled `synthetic_host_probe_v0.4`. Seed 34/C and 35/C completed
with zero primary observable-oracle regret. Seed 35/A completed with primary
regret 80; other A/B trajectories exhausted the decision budget before three
records. These facts show capture and scoring behavior, not a treatment effect.

## What the development results do and do not support

They support the narrow conclusion that the harness can present telemetry,
capture a fresh subject's action, and score it against an observable-only
oracle without the previously detected direct prompt advice or latent-oracle
mismatch.

They do **not** support an empirical claim that telemetry improves model
decisions. The subjects can access the shared workspace, A/B/C generations are
independent rather than paired, the cohort is tiny, and the monitor is a
controlled synthetic observation model. Do not pool these records with a later
provider cohort or present them in a paper denominator.

## Open threats and required resolution

| Threat | Required resolution before paper data |
|---|---|
| Synthetic observation model | Predeclare probe accuracy, latency/freshness, missingness, and noise/staleness sensitivity; frame it as synthetic unless live telemetry is separately validated. |
| Shared filesystem | Execute provider subjects in an isolated runner that cannot read schedules, oracle, evaluator, or artifacts. |
| Neutral control | Construct B against the pinned provider tokenizer and record the tokenizer/version. |
| Independent generations | Analyze as independent samples; do not use paired tests merely because fault tapes share a seed. |
| Resource enforcement | Linux cgroup-v2 memory proof remains required for MemoryGovernor/global G1, but not for the narrow isolated synthetic ToolRoute API pilot. |
| API provenance | Implement reservation-before-request, immutable raw request/response capture, parser/retry/cost capture, and terminal finalization. |

## Exact next sequence

1. The post-fix seed 50–54 development block has verified
   `turn-XX-handoff.json` capture. Do not treat its five seed triads as a
   counterbalanced cohort and do not collect additional local fresh-subagent
   data unless debugging a newly identified harness defect.
2. Complete the ToolRoute-specific API preflight in
   `docs/13_toolroute_api_and_toxiproxy_preflight.md`: model-free observation
   sensitivity calibration, provider tokenizer pinning, and isolated-runner
   review.
3. Freeze the provider pilot manifest and analysis plan: model/version,
   tokenizer, prompts, action parsing, retry policy, seeds/assignment,
   observation calibration, outcomes, exclusions, power simulation, and one
   explicit state-delivery mode (persistent-history deltas or independent
   full-checkpoint episodes).
4. Only then, and only after the manifest hash is bound in provenance, execute
   a small isolated API pilot. Inspect artifacts and behavior;
   use its base rates to set the predeclared main-study sample size.

## Decision

**No provider calls yet.** Local execution code plus remote model inference is
an acceptable eventual architecture for a reproducible paper study, but it
becomes evidence only after the above ToolRoute gates and a powered, frozen API
cohort. The optional Toxiproxy adapter validation may run locally once its
binary is installed; it is not paper evidence and does not authorize a model.
