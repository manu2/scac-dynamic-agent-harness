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
| ToolRoute v0.4 | Local fresh-subagent engineering smoke only; no empirical data | Synthetic probes; shared-workspace subjects; B is byte- not tokenizer-matched | One handoff-artifact smoke if useful; then G1/G2 and isolated API-pilot preparation |
| RetryBudget v0.1 | Deterministic model-free calibration only | No fresh-subagent or provider run is authorized | Repair/freeze causal transition and utility/oracle design; add evaluator-defeat tests and a scenario issue ledger |
| MemoryGovernor | Virtual deterministic calibration only | Makes no cgroup-enforcement claim | Run only after Linux G1; then create a separately frozen observation/oracle contract |

## RetryBudget mandatory design review

The current implementation is not a ready experiment. Its `wait` action
advances the schedule rather than preserving the pending request; `fallback`
has sufficiently high utility to risk an unconditional-policy shortcut; and
the oracle returns binary regret. A RetryBudget owner must resolve or justify
each property in a new scenario contract before collecting any agent behavior.
They must also test fixed-action baselines (`always retry`, `always wait`,
`always fallback`, `always checkpoint`, `always terminate`) and demonstrate
that no telemetry-blind baseline nearly matches the oracle by construction.

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
   manifest may be frozen only after global G1/G2 gates and that scenario's
   own observation, oracle, and evaluator-defeat gates pass.
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
