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

## Gate requirements

No provider call is allowed until:

- schema fixtures and trust-boundary tests pass;
- memory, timeout, and tool-fault positive controls pass;
- deterministic scenarios reproduce in clean containers;
- context-isolated reviewers find no algorithm leakage or trivial evaluator
  bypass; and
- the pilot manifest and analysis plan are frozen.
