# Scenario Boundaries and Parallel Work Protocol

**Status:** authoritative collaboration contract, pre-pilot  
**Applies to:** every contributor and every scenario

## One shared harness; separate experiments

SCAC shares a measurement substrate, not a shared empirical denominator.
ToolRoute, RetryBudget, and MemoryGovernor are separate experiments with
independent causal dynamics and oracles. A passing calibration, smoke run, or
review in one scenario must never be reported as a pass for another.

| Layer | Shared and change-controlled | Scenario-owned and independent |
|---|---|---|
| Contract | SST schema, identity hashing, validator, missing-data semantics, descriptive-only renderer, host trust boundary | Action schema, transition rules, task completion, oracle, observation model, scenario prompt, calibration policy |
| Enforcement | G1 cgroup/timeout/tool-fault controls and provider-call prohibition | Which enforced signal matters and scenario-specific positive/negative controls |
| Artifacts | Immutable, reserved before action/request, retention and audit conventions | `experiments/<stage>/<scenario>/...`, manifests, raw events, trajectories, issue ledger, analysis cohort |
| Statistics | Predeclare inclusion, preserve attempts, independent-vs-paired rule, power simulation | Primary outcome, minimum effect, exclusions justified by that scenario only |

## Current scenario state

| Scenario | Current state | Explicit boundary | Next permitted work |
|---|---|---|---|
| ToolRoute v1.0 | Frozen 216-decision direct-provider cohort complete; authorization revoked | Synthetic host-owned monitor; tools dimension only; no pooling with other scenarios | Frozen-cohort analysis, manuscript, and artifact release; no new provider calls without a reviewed protocol |
| RetryBudget v0.2 | Deterministic transition/oracle hardening and archived developer calibration only | No fresh-subagent or provider run is authorized | Freeze/calibrate observation and A/B/C contracts; add manifest, prompt/capture, inclusion, and readiness packet |
| MemoryGovernor | Virtual deterministic calibration only | Makes no cgroup-enforcement claim | Run only after Linux G1; then create a separately frozen observation/oracle contract |

## RetryBudget mandatory design review

RetryBudget v0.1 is historical calibration only. Its `wait` action advanced the
schedule rather than preserving the pending request; `fallback` risked an
unconditional-policy shortcut; and its oracle returned binary regret. v0.2
replaces those semantics with a pending-work state machine and numeric,
observable dynamic-programming oracle. Its developer calibration establishes
all five actions as uniquely optimal somewhere and separates fixed policies from
the oracle; those checks must be repeated on the separately frozen seed block.

The implementation is still not a ready agent experiment. A RetryBudget owner
must freeze a scenario-owned observation model, A/B/C prompt contract, artifact
manifest, exact prompt capture, inclusion rules, and analysis plan before any
agent behavior is collected. The current issue ledger and readiness contract are
`docs/21_retrybudget_issue_ledger.md` and
`docs/20_retrybudget_v0_2_design_and_readiness.md`.

## Rules for contributors

1. Read `README.md`, `RESEARCH_ROADMAP.md`, `EXECUTION_TRACKER.md`,
   `PROTOCOL.md`, `PROVENANCE.json`, and this document before changing a
   scenario.
2. Work only in the named scenario's code, tests, docs, and artifact namespace
   unless the change is genuinely shared. Do not alter another scenario's
   simulator, oracle, prompt, manifest, or artifacts.
3. A shared-layer change needs a written rationale in `EXECUTION_TRACKER.md`,
   regression tests for every affected scenario, and review for leakage or
   changed scoring semantics.
4. Reserve the artifact directory before any action or external request. Never
   overwrite, migrate, rename, or pool historical records. Historical paths
   remain valid; all new G2 records use `g2-calibrations/<scenario>/`.
5. Each scenario keeps its own issue ledger and readiness note. Its provider
   manifest may be frozen only after its stated protocol gates and that
   scenario's own observation, oracle, and evaluator-defeat gates pass.
   ToolRoute's narrow synthetic API exception is defined only in `PROTOCOL.md`;
   it does not close global G1/G2 or authorize either other scenario.
6. No provider call is authorized by this document. `PROVENANCE.json` and the
   global protocol remain controlling.

## Required scenario readiness packet

Before a scenario can request a local fresh-subagent smoke or provider pilot,
its owner must commit a packet containing:

- a versioned action/state-transition specification and deterministic seed
  policy;
- an observable-only primary oracle plus any hidden-state diagnostic clearly
  labelled as such;
- measurement-model calibration, including noise, missingness, and freshness;
- fixed-policy/evaluator-defeat baselines and expected failures;
- a scenario-specific artifact manifest and exact prompt/handoff capture;
- an issue ledger, inclusion rules, and analysis plan.

## Conflict resolution

If a shared change helps one scenario but changes another's rendered facts or
score, do not merge it as a silent improvement. Split it behind a versioned
scenario adapter or pause the change until a common protocol amendment is
reviewed. Fail closed: uncertainty about ownership means no new agent trials.
