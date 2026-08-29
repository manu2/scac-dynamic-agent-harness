# Dynamic SCAC Experimental Protocol

**Version:** design-v0.1
**Status:** pre-pilot; provider calls prohibited

## Primary question

Does a fresh, truthful telemetry snapshot supplied immediately before a
consequential model decision improve correct operational completion relative to
the same environment without that projection?

## Conditions

- **A — Observation only:** semantic tool results; no operational projection.
- **B — Neutral control:** A plus length-matched decision-irrelevant fields.
- **C — Structured SST:** A plus truthful compact telemetry.
- **D — Natural-language digest:** semantically equivalent rendering on a subset.
- **E — Stale state diagnostic:** delayed or cumulative-only state on a subset.

The environment and fault schedule are identical across information conditions.
Only model-visible state changes.

## Primary scenarios

1. ToolRoute: seeded health schedule and equivalent tools; score first post-change
   action and cumulative policy regret.
2. MemoryGovernor: explicit chunk/worker action interface under cgroup pressure;
   score correct completion, violations, and adaptation latency.
3. RetryBudget: seeded outage/quota state with retry/wait/fallback/checkpoint
   actions; score utility, dominated retries, violations, and premature exit.

Scenario-specific action semantics, oracle assumptions, artifact namespaces,
and readiness must be maintained separately under the scenario-boundary
protocol in `docs/11_scenario_boundaries_and_parallel_work_protocol.md`. A
scenario's calibration or development artifacts never establish readiness for
another scenario and are never pooled without an explicitly frozen
cross-scenario synthesis protocol.

## ToolRoute observation and scoring contract (v0.4 development)

ToolRoute separates latent environment state, independent host-monitor probes,
and the model-visible SST projection. The primary ToolRoute oracle may use only
canonical monitor facts that are rendered to Condition C: probe window size,
success count, latency EWMA, and circuit state. A latent-health expected-cost
oracle is retained only as a diagnostic ceiling. Every primary scored state must
pass a predeclared observable-margin calibration before a subject receives it;
ambiguous states are retained but are not eligible for exact action-agreement
claims.
The v0.4 probes are a controlled synthetic observation model, not live host
telemetry; results must be framed accordingly unless a separately frozen,
calibrated live-monitor protocol is used. Before an API pilot, the observation
model must specify and test measurement accuracy, latency/freshness, missingness,
and noise/staleness sensitivity. The exact coordinator-to-subject handoff must
be recorded with the frozen `subject_prompt_v1_double_newline_delimiter`
contract; the condition message itself remains unmodified.

## Primary outcomes

- correct completion without a hard operational violation;
- action-level oracle agreement and policy regret;
- adaptation latency after a state transition;
- OOM, limit, timeout, quota, and forbidden-call violations;
- turns, tool calls, retries, tokens, wall time, and separately reported
  MB-seconds/GB-seconds, API cost, and token cost.

## Integrity rules

- Freeze model IDs, prompts, reducer, thresholds, renderer, simulators, seeds,
  metrics, exclusions, and analysis before the main study.
- Treat organizational trial numbers as unpaired unless a provider supplies an
  effective shared seed and the design truly matches trajectories.
- Retain every attempt. Reserve its directory before any provider request.
- Use Wilson intervals for binary outcomes. Use independent-sample tests for
  independent generations; McNemar only for genuine matched pairs. Use bootstrap
  intervals and predeclared rank/permutation tests for skewed cost and duration.
- Determine main-study sample size by simulation from pilot base rates and the
  minimum effect of interest; 10 trials are a pilot, not paper-grade evidence.
- Keep enforcement and the external oracle outside model control.

## ToolRoute API-pilot gate

ToolRoute is a narrow synthetic tool-health experiment. Its API pilot may be
authorized without MemoryGovernor's Linux cgroup-v2 memory proof, but only when
all of the following are frozen and passing:

- the independent full-checkpoint episode mode is used (no sparse deltas and no
  persistent model history in this cohort);
- the model has no filesystem, shell, network-tool, schedule, oracle, or
  artifact access beyond its one assigned prompt;
- the reservation-first API runner passes mock-provider, malformed-response,
  redaction, finalization, and evaluator-defeat tests;
- B is matched by the pinned provider tokenizer, not merely UTF-8 byte length;
- the synthetic observation model's accuracy, freshness, missingness, and
  noise/staleness sensitivity are calibrated and retained; and
- a ToolRoute pilot manifest and analysis plan are committed, with the
  scenario-specific authorization field in `PROVENANCE.json` set to `true`.

The generic `provider_trials_authorized` field remains false until all scenarios
meet the global gates. This narrower authorization applies only to ToolRoute
and cannot be reused by MemoryGovernor or RetryBudget.

## Global gate requirements

No MemoryGovernor or cross-scenario provider call is allowed until:

- schema fixtures and trust-boundary tests pass;
- memory, timeout, and tool-fault positive controls pass;
- deterministic scenarios reproduce in clean containers;
- context-isolated reviewers find no algorithm leakage or trivial evaluator
  bypass; and
- the pilot manifest and analysis plan are frozen.
