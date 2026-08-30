# RetryBudget v0.2 Design and Readiness Contract

**Status:** development-canary-ready and intentionally provider-disabled. It
is not authorized for a paper cohort.

## Question

Does current, host-owned service, quota, deadline, fallback, and checkpoint
state improve the next operational decision for a pending piece of work?

RetryBudget is a distinct scenario from ToolRoute. It evaluates a pending-work
lifecycle and cannot reuse ToolRoute's prompt, oracle, cohort, or evidence.

## v0.1 defects being replaced

The v0.1 calibration advanced through a fixed schedule after every action,
including `wait`; it therefore discarded the pending request rather than waiting
on it. It also assigned binary regret despite action utilities and made
unconditional fallback nearly competitive. Its action names were broader than
its transition semantics. It is preserved as historical calibration only.

## v0.2 state and action contract

Each episode has one pending work item and a host-owned logical clock. A full
decision checkpoint includes, at minimum:

- elapsed and remaining deadline;
- primary-service status and an explicit retry-after/recovery time when known;
- remaining primary quota;
- fallback availability and its declared cost/latency;
- checkpoint availability, whether a recoverable checkpoint exists, and its
  declared recoverable value.

The action set remains `retry`, `wait`, `fallback`, `checkpoint`, and
`terminate`.

- `retry` attempts the primary service. It may complete pending work, consume
  quota, or produce a host-classified failure/forbidden-retry outcome.
- `wait` advances only the logical clock to the relevant recovery boundary or
  deadline and **preserves pending work**.
- `fallback` completes through a declared alternative when available, with its
  predeclared lower utility/cost.
- `checkpoint` preserves recoverable progress at a declared cost; it does not
  silently complete the work.
- `terminate` ends the episode and returns only the declared recoverable value
  of a prior checkpoint, if any.

Service recovery is an exogenous host schedule. The model cannot modify it,
quota, deadline, fallback availability, checkpoint value, action-value oracle,
or the artifact record.

## Observable primary oracle

The primary oracle is a deterministic dynamic-programming action-value oracle.
For every scored state it evaluates each legal action, then follows the optimal
observable continuation. Its inputs are limited to the same canonical facts
that condition C receives. Action regret is the difference between the best
observable action value and the selected action value; it is numeric, not
binary. A hidden-state diagnostic, if any, must remain secondary and visibly
labelled.

This makes an initial `wait` action meaningful: it can lead to a later recovery
state without erasing the work item. It also makes checkpoint and terminate
meaningful only where their declared recovery value changes the optimal action.

## Required calibration and evaluator-defeat checks

Before any agent behavior is collected, v0.2 must demonstrate:

1. deterministic, seed-stable transitions and write-once archived calibration;
2. each action is uniquely optimal in at least one observable, non-ambiguous
   calibration state, or the unused action is removed from the protocol;
3. `wait` preserves pending work and reaches the declared recovery boundary;
4. no fixed policy (`always retry`, `always wait`, `always fallback`, `always
   checkpoint`, `always terminate`) nearly matches the observable oracle across
   the frozen seed block;
5. the observable oracle never reads a field absent from condition C;
6. action labels, invalid-action handling, deadline expiry, quota exhaustion,
   and terminal records have explicit tests;
7. a separate observation model, A/B/C prompt contract, artifact manifest,
   inclusion rules, and analysis plan are frozen before any local subject or
   provider call.

## Initial implementation evidence

The transition/oracle implementation is `RetryBudget-v0.2`. Its focused test
suite verifies deterministic transitions; uniquely optimal calibration states
for all five actions; pending-work preservation across `wait`; numeric regret;
checkpoint/termination recovery semantics; explicit invalid/deadline outcomes;
and fixed-action baseline separation. Across seed-varying developer calibration
seeds 0--11, the observable-oracle policy totals 4,371 utility and the best
fixed policy (`always checkpoint`) totals 2,007, a 54.1% gap. This is a development
calibration, not an agent-result denominator or a frozen main-study seed block.

The first pre-finalization oracle-following artifact is retained at
`experiments/g2-calibrations/retrybudget-v0-2/20260830T202837.478701Z-retrybudget-v0-2-990b98475ab3441989de0f481ba2e796/`.
It is historical only. The current seed-61 calibration is retained at
`experiments/g2-calibrations/retrybudget-v0-2/20260830T205316.217706Z-retrybudget-v0-2-b63c79c940a3479fa06481451fb92dab/`.
It contains seven transitions, all five action types, zero action regret, a
terminal outcome, and verified finalization hashes.

## Observation and prompt work in progress

The v0.2 pure observation renderer now defines independent full-checkpoint A/B/C
messages. A exposes only task/action semantics; B exposes the identical
host-state field envelope and option order using `NEUTRAL` values; C exposes the
complete state projection consumed by the primary oracle. Five adjacent seeds
rotate every action through every option position for the same state. The
baseline has zero delivery delay and zero loss/corruption. Non-zero observation
loss/corruption fails closed until a separately calibrated sensitivity model is
implemented. The control is structurally matched rather than token-identical;
actual provider input-token usage will be retained as a descriptive
manipulation check. This is a development contract, not a frozen paper-cohort
prompt.

## Local-only execution mechanism

`RetryBudgetDevelopmentTrial` and `retry_budget_smoke_cli` implement a
write-once, fresh-context handoff path. The subject receives only its current
condition prompt and an exact-label instruction; the host retains state,
action-values, oracle, transitions, rejections, and finalization hashes. The
first host-oracle end-to-end diagnostic is retained at
`experiments/dev-smoke/retrybudget-v0-2/20260830T203620.187555Z-C-a15f02f345a24aa8a0f06093757bc8b8/`.
It has seven full-checkpoint decisions, zero oracle regret, valid finalization
hashes, and `provider_calls: prohibited`. It validates execution capture only;
it is not a subagent trajectory or paper evidence.

## Provider-canary boundary and next gate

The committed `manifests/retrybudget_api_canary.v0.2.json` permits, once
separately authorized, exactly one **development-only** Gemini 3.7 Flash,
condition-C, seed-61 trajectory with at most seven generations. Its runner
reserves a write-once directory before execution; records every current prompt,
host-only state/oracle, sanitized request, response/error, exact-label result,
and terminal hash manifest; and rechecks live authorization before every paid
generation. Its primary episode outcome is realized cumulative utility versus
the oracle episode utility, not a sum of local dynamic-program gaps. See the
runbook and pre-provider audit for the remaining authorization and review
requirements.

New records belong under `experiments/g2-calibrations/retrybudget-v0-2/` and
`experiments/api-preflight/retrybudget-v0-2/`; historical records remain
immutable. Passing this packet permits only a separate readiness review. It
does not authorize a provider call or pooling with ToolRoute.
