# Execution Tracker: Dynamic SCAC

## Overall status

- **Current stage:** G0 specification & review remediation (Complete; branch `codex/g0-sst-schema`).
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

### 2026-08-28 — G0 completion and peer-review remediation

- **RFC 8785 Conformance:** Implemented strict JSON Canonicalization Scheme (JCS) serialization in `src/scac_harness/identity.py`, normalizing `-0.0` to `0`, formatting integer-valued floats without trailing `.0`, and enforcing UTF-16 code point property key ordering.
- **Sliding-Window Tool Health:** Corrected tool health evaluation in `src/scac_harness/reducer.py` by introducing an explicit outcome history buffer (`history: list[bool]`, max 10) to guarantee proper sample eviction under shifting failure regimes.
- **Elimination of Telemetry Fabrication:** Reducer and renderer updated to eliminate fabricated defaults (e.g. 0-byte memory, 1 GiB free disk, ENABLED network). Unobserved subsystems are strictly marked `state="UNKNOWN"` and listed in `unavailable_fields`.
- **Derivation Provenance:** Added field-level audit provenance (`derivation_provenance`) mapping derived state namespaces to contributing raw event SHA-256 hashes.
- **Raw Event Cryptographic Verification:** `RawTelemetryEvent` now enforces cryptographic content verification on creation and deserialization, failing closed against forged hashes.
- **Delta Linkage Fix:** Trajectory validator updated to reject self-linked deltas and initial deltas without prior trajectory history. Added snapshot rehydration helper (`rehydrate_snapshot`).
- **Fixture Verification:** Updated invalid fixtures and test assertions to test specific contract violations rather than general failures.
- **Test Suite:** 48 passing unit and integration tests with 0 failures.
