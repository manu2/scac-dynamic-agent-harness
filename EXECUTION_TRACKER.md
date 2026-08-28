# Execution Tracker: Dynamic SCAC

## Overall status

- **Current stage:** G0 repository initialization.
- **Provider calls:** not authorized.
- **Empirical trials:** none.
- **Upstream design basis:** `manu2/Context-Aware-Agent-Experiment` commit
  `f35173d29375216af88c708687efbcc51f36398a`.

## Stage ledger

| Stage | Work | Status | Evidence |
|---|---|---|---|
| G0.0 | Create separate repository boundary | Complete | `PROVENANCE.json` |
| G0.1 | Scaffold governance, protocol, schema, package, and tests | Complete | initial repository tree |
| G0.2 | Freeze SST v0.1 semantics and fixtures | Pending | schema and unit tests |
| G0.3 | Complete threat model and injection renderer | Pending | design review |
| G1 | Collectors and fail-closed enforcement | Pending | positive-control records |
| G2 | Deterministic scenarios and oracles | Pending | calibration artifacts |
| G3 | One-model pilot | Blocked by G0–G2 | frozen pilot manifest |

## Execution log

### 2026-08-28 — repository initialization

- Established a separate Phase 2 repository to prevent accidental pooling with
  the static-contract cohort.
- Added the governance documents, protocol, SST schema skeleton, source layout,
  tests, and immutable-artifact placeholders.
- Recorded the exact upstream commit. No external model calls or experiments ran.
