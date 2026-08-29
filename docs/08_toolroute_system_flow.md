# ToolRoute System Flow

The downloadable JPEG is retained at
`/Users/manuagrawal/.codex/visualizations/2026/08/28/01a049b0-d80a-74d2-838e-3bdedd1fce16/toolroute-experiment-flow.jpg`.
This versioned Mermaid source is the repository artifact.

```mermaid
flowchart LR
  S[Hidden tool state] --> M[Independent host probes]
  M --> T[Reducer and descriptive SST]
  A[Condition A: task] --> D[Fresh decision subject]
  B[Condition B: neutral structure] --> D
  T --> C[Condition C: telemetry]
  C --> D
  D --> E[Host executes fixed potential outcome]
  E --> P[Primary: completion, realized cost, violations]
  T -. observable facts only .-> O[Primary observable oracle]
  S -. secondary ceiling only .-> Q[Clairvoyant diagnostic oracle]
```
