# Execution Tracker: Dynamic SCAC

## Overall status

- **Current stage:** G0 specification & review remediation round 2 (Complete; branch `codex/g0-sst-schema`).
- **Provider calls:** not authorized.
- **Empirical trials:** none.
- **Upstream design basis:** `manu2/Context-Aware-Agent-Experiment` commit
  `f35173d29375216af88c708687efbcc51f36398a`.

## Stage ledger

| Stage | Work | Status | Evidence |
|---|---|---|---|
| G0.0 | Create separate repository boundary | Complete | `PROVENANCE.json` |
| G0.1 | Scaffold governance, protocol, package, and tests | Complete | initial repository tree |
| G0.2 | Freeze SST v0.1 JSON Schema Draft 2020-12 | Complete | `src/scac_harness/schemas/scac-sst-v0.1.json` |
| G0.3 | Generate valid and invalid test fixtures | Complete | 9 valid, 12 invalid fixtures in `tests/fixtures/` |
| G0.4 | Implement snapshot & trajectory validation | Complete | `src/scac_harness/validator.py`, `tests/test_validation.py` |
| G0.5 | Implement RFC 8785 canonical identity hashing | Complete | `src/scac_harness/identity.py`, `tests/test_identity.py` |
| G0.6 | Implement deterministic reducer interface | Complete | `src/scac_harness/reducer.py`, `tests/test_reducer.py` |
| G0.7 | Implement compact model-visible renderer | Complete | `src/scac_harness/renderer.py`, `tests/test_renderer.py` |
| G0.8 | Complete threat model & representation semantics | Complete | `docs/01_threat_model_and_trust_boundaries.md`, `docs/02_representation_semantics.md` |
| G1 | Collectors and fail-closed enforcement | Pending | positive-control records (Next stage upon authorization) |
| G2 | Deterministic scenarios and oracles | Pending | calibration artifacts |
| G3 | One-model pilot | Blocked by G0–G2 | frozen pilot manifest |

## Execution log

### 2026-08-28 — G0 completion and peer-review remediation (Round 1 & 2)

- **Vetted RFC 8785 (JCS) Conformance:** Adopted official `jcs>=0.2.1` implementation in `src/scac_harness/identity.py` for canonical serialization, strictly satisfying ECMAScript 7.1.12.1 float representations (`1e30 -> 1e+30`, `1e-7 -> 1e-7`, `-0.0 -> 0`) and UTF-16 code unit property key sorting.
- **Deep Raw Event Immutability:** Introduced `FrozenDict` in `src/scac_harness/events.py` ensuring that `event.payload` is deeply immutable and cannot be mutated after content hashing, while supporting serialization and deepcopy.
- **Elimination of Partial Observation Fabrication:** In `src/scac_harness/reducer.py`, when `current_bytes` is observed without `max_bytes`, `headroom_ratio` remains `None` and memory `state` is classified as `UNKNOWN` (never fabricated as 1.0 or OK).
- **Interval Delta Isolation & Freshness Tracking:** In `src/scac_harness/reducer.py`, interval deltas (`events_delta`, `nr_throttled_delta`, etc.) are reset across reduction windows and never carried across unrelated turns. Added `subsystem_observed_at_ms` to track fine-grained subsystem observation ages.
- **True Sparse Delta Representation:** Updated schema, reducer, and renderer so delta snapshots (`kind == "delta"`) only contain the namespaces and counters actually observed/modified in the current interval, with full rehydration supported.
- **Genuine Unsupported-as-Zero Fixture & Validation:** Updated `unsupported_metric_represented_as_zero.json` to declare an unavailable metric with value 0, and updated `validate_snapshot` to reject any unavailable field represented as zero.
- **Roadmap Scope Correction:** Restored protocol-aligned wording in `RESEARCH_ROADMAP.md` (removing premature sample size and model commitments).
- **Test Suite:** 52 passing unit and integration tests with 0 failures.
