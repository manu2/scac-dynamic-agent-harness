# RetryBudget Issue Ledger

**Status:** active scenario-specific ledger. Historical v0.1 artifacts remain
preserved and are not paper evidence.

| ID | Status | Finding | Risk | Required disposition |
| --- | --- | --- | --- | --- |
| RB-001 | Fixed in v0.2 | `wait` advanced the fixed schedule and discarded pending work. | A wait result could look favorable while not representing the action's operational meaning. | A host-owned logical clock now preserves pending work, quota, and work-item identity across visible recovery. |
| RB-002 | Fixed in v0.2 | Oracle regret was binary although outcomes had distinct utilities. | The score could hide meaningful action differences and fail to reflect the declared objective. | A finite observable dynamic program now returns numeric action values and numeric regret. |
| RB-003 | Provisional developer-calibration pass | `fallback` returned high utility in v0.1. | A telemetry-blind fixed fallback policy may nearly match the oracle. | In seeds 0--11 the best fixed policy totals 1,860 utility versus 4,200 for the observable oracle (55.7% gap). Repeat on the separately frozen seed block before agent trials. |
| RB-004 | Fixed in v0.2 | `checkpoint` and `terminate` lacked a lifecycle that could make them rational actions. | Decorative actions create prompt noise and weaken the experiment. | Checkpoint now preserves declared partial-work value at a cost; terminate can recover only that host-visible value. Each is uniquely optimal in a calibration state. |
| RB-005 | Open observation gate | v0.1 had no A/B/C observation model or freshness/noise/missingness calibration. | A later apparent telemetry effect could be an unmeasured prompt or observation artifact. | Freeze and calibrate a scenario-owned observation contract after transition/oracle validation. |
| RB-006 | Open readiness gate | No RetryBudget prompt, runner, manifest, issue-free calibration packet, or evaluator-defeat suite exists. | Any local or provider run would be premature. | Complete the v0.2 readiness packet under `docs/11_scenario_boundaries_and_parallel_work_protocol.md`. |
