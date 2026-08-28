# AGENTS.md: Dynamic SCAC Harness

This repository implements the dynamic, multi-turn phase of Project Aether-Bus /
SCAC. It is a separate experimental system from the static-contract evidence in
`manu2/Context-Aware-Agent-Experiment`.

## Required documents

Every agent must read and maintain:

- `README.md`: repository overview and quickstart.
- `RESEARCH_ROADMAP.md`: research questions, architecture, and gates.
- `EXECUTION_TRACKER.md`: live execution and provenance ledger.
- `PROTOCOL.md`: frozen experimental contract and analysis rules.
- `PROVENANCE.json`: pinned upstream basis and repository lineage.

## Operating rules

1. Update `EXECUTION_TRACKER.md` and `RESEARCH_ROADMAP.md` whenever an execution
   step, design decision, edge case, or architecture change occurs.
2. Fail closed. Memory, timeout, and tool-fault positive controls must pass before
   model trials. Never weaken an evaluator or preflight to obtain a passing run.
3. Preserve every attempted trajectory, prompt, tool event, telemetry snapshot,
   generated artifact, stdout/stderr stream, and terminal classification under
   `experiments/`. Never overwrite or delete historical trials.
4. Reserve trial directories atomically before external model calls. All attempts
   count under the predeclared inclusion rules.
5. Keep enforcement outside the model. The model cannot edit telemetry, disable
   cgroups, rewrite tool-health state, or modify the evaluator.
6. Do not pool results with the static-contract repository. Cross-study synthesis
   requires an explicit protocol and separately labelled cohorts.
7. No provider calls are authorized until gates G0–G2 in `PROTOCOL.md` pass and a
   pilot manifest is frozen.
