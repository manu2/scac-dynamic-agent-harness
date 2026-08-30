# ToolRoute v1.0 Fixed-Structure Canary Audit

## Scope

This excluded engineering canary executed seed 6 across four turns and A/B/C
for GPT-5.6 Sol, Claude Sonnet 5, and Gemini 3.7 Flash: 36 independent,
tool-less API decisions. The frozen manifest is
`manifests/toolroute_api_canary.v1.0.json`.

## Integrity audit

- 36/36 expected provider × turn × condition cells completed exactly once.
- 0 provider errors; 0 malformed responses; 0 duplicate cells.
- Every terminal `finalization.json` hash verified.
- B has the same envelope, fields, order, and tool rows as C, with identical
  alpha/beta values. No tokenizer service, online padding, or equality claim
  is used.

## Descriptive behavior

For every model, C chose `tool_beta` with zero observable regret on the two
degraded decision turns (0 and 3). A and B chose `tool_alpha`, receiving 80.0
and 7453.81 regret respectively. All conditions chose zero-regret actions on
turns 1 and 2. This is a single-seed canary and must not be used as a paper
treatment-effect estimate.

## Decision

The execution and capture path is ready for a separately frozen paper cohort.
Provider-reported usage remains descriptive; the paper's primary contrast is
C–A, with C–B and B–A prespecified secondary contrasts.
