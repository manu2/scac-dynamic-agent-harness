# RetryBudget v0.2 Design and Readiness Contract

**Status:** transition/oracle implementation and first archived calibration
complete; not authorized for fresh-subagent or provider trials.

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
and fixed-action baseline separation. Across developer calibration seeds 0--11,
the observable-oracle policy totals 4,200 utility and the best fixed policy
(`always checkpoint`) totals 1,860, a 55.7% gap. This is a development
calibration, not an agent-result denominator or a frozen main-study seed block.

The first write-once oracle-following artifact is retained at
`experiments/g2-calibrations/retrybudget-v0-2/20260830T202837.478701Z-retrybudget-v0-2-990b98475ab3441989de0f481ba2e796/`.
It contains seven transitions, all five action types, zero action regret, and a
terminal outcome.

## Boundary and next gate

New records belong under `experiments/g2-calibrations/retrybudget-v0-2/` and
must preserve historical v0.1 artifacts unchanged. Passing this packet only
permits a separate readiness review; it does not authorize provider calls or
pooling with ToolRoute.
