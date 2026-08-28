# Threat Model and Trust Boundaries: Dynamic SCAC

**Document ID:** `SCAC-SEC-01`
**Status:** Frozen for Gate G0
**Schema Target:** `scac-sst-v0.1`

---

## 1. Architectural Trust Hierarchy

The Dynamic SCAC harness enforces a strict separation between privileged host components and unprivileged execution context:

```text
+-------------------------------------------------------------------------+
| [LEVEL 0: Host OS Kernel & Supervisor] (Privileged, Immutable)           |
| - Linux cgroup v2 controller subsystem (/sys/fs/cgroup)                 |
| - Monotonic hardware clock & POSIX signal dispatcher                    |
| - Raw event collector & append-only JSONL storage (out-of-tree)         |
| - Deterministic Reducer (Pure Python, zero network/model dependencies)  |
| - External Decision Oracles & Invariant Verifiers                      |
+-------------------------------------------------------------------------+
                                    |
                                    v (Host-controlled Injection)
+-------------------------------------------------------------------------+
| [LEVEL 1: Privileged Model Context Envelope] (Host Authored)            |
| - Tier 1: Stable System Prefix (Specification, units, trust invariant)   |
| - Tier 2: Dynamic Turn Envelope (Versioned SST snapshot or delta)       |
+-------------------------------------------------------------------------+
                                    |
                                    v (Visible to Model)
+-------------------------------------------------------------------------+
| [LEVEL 2: Multi-Turn Agent Loop & LLM Reasoning] (Untrusted)             |
| - Multi-turn reasoning / Chain-of-thought                               |
| - Structured Action Dispatch (chunk_size, worker_count, tool_route)     |
+-------------------------------------------------------------------------+
                                    |
                                    v (Sandboxed Action Execution)
+-------------------------------------------------------------------------+
| [LEVEL 3: External Tools, Subprocesses & Network Services] (Adversarial) |
| - External HTTP APIs (status codes, headers, bodies)                     |
| - Sandboxed worker processes & filesystem access                         |
| - Prompt injection vectors & malformed outputs                          |
+-------------------------------------------------------------------------+
```

---

## 2. Comprehensive Threat Inventory and Mitigations

| # | Threat Name | Trust Boundary | Attacker / Failure Source | Affected Asset | Failure Mode | Mitigation Strategy | Residual Risk | Test & Audit Evidence |
|---|---|---|---|---|---|---|---|---|
| 1 | **Telemetry Poisoning** | L3 -> L0 / L1 | Malicious tool or compromised subprocess | Host telemetry state | Injected false resource metrics (e.g. fabricated 0% memory usage) | Telemetry collectors read exclusively from kernel cgroup v2 interfaces and monotonic host clocks; tool results are never parsed for host telemetry. | Kernel interface vulnerabilities (mitigated via rootless containers). | Unit tests in `test_schema.py` rejecting tool payload injection. |
| 2 | **Tool-Result Prompt Injection** | L3 -> L2 | Remote API or scraped untrusted payload | Agent decision-making | Untrusted prose in tool output instructs agent to disregard host constraints. | Strict separation: tool outputs render in standard observation blocks; host telemetry renders in distinct privileged envelope with fixed delimiters. | Model compliance susceptibility to indirect prompt injection. | Adversarial fixture `raw_tool_content_in_privileged_block.json`. |
| 3 | **Tool Metadata Masquerading** | L3 -> L1 | Adversarial tool returning pseudo-telemetry headers | Snapshot integrity | Tool returns fake headers mimicking host telemetry envelope tags. | Host reducer ignores arbitrary tool headers; only host wrapper measures span latency and exit codes. | None within the harness boundary. | Adversarial fixture `tool_supplied_overwrite_attempt.json`. |
| 4 | **Stale-State Harm** | L0 -> L1 -> L2 | Scheduling delay or asynchronous lag | Decision validity | Agent makes allocation decisions based on expired telemetry (e.g. headroom depleted 5000ms ago). | Explicit `fresh_for_ms` validity duration in snapshot; `validate_trajectory` fails closed if current time exceeds expiration. | Clock skew between container and host (avoided via monotonic host epoch). | `test_trajectory_rejects_stale_snapshot_at_injection_time`. |
| 5 | **Replayed Snapshots** | L1 -> L2 | Rogue or buggy execution loop | Trajectory sequence | Stale snapshot injected repeatedly across consecutive turns. | Monotonically increasing `seq` and `observed_at_ms` enforced by `validate_trajectory`. | None. | `test_trajectory_rejects_regressing_sequence_numbers`. |
| 6 | **Reordered Events** | L0 -> L0 Reducer | Asynchronous span collection buffer | Snapshot accuracy | Out-of-order event reduction produces incorrect EWMA latency or circuit state. | Reducer explicitly sorts events by `(timestamp_ms, event_id)` before folding. | Microsecond-level timestamp ties broken deterministically by hash. | `test_deterministic_reduction_identical_output`. |
| 7 | **Metric Gaming** | L2 -> Oracle | Strategic agent policy | Scientific validity | Agent terminates early or avoids tool calls entirely to report zero violations/retries. | Evaluation oracles score task utility and regret alongside resource metrics; premature exit penalizes utility. | Metric definition loopholes (closed via predeclared loss functions in G2). | Scenario oracle definitions in `PROTOCOL.md`. |
| 8 | **Enforcement Disable Attempts** | L2 -> L0 | Adversarial agent code execution | Kernel sandbox / cgroups | Agent executes `chmod`, `kill -9`, or cgroup unshare to bypass limits. | Enforcement is unprivileged; cgroup controllers and watchdog timers run outside the sandbox container. | Container breakout zero-days (isolated via standard Docker/OCI seccomp profiles). | G1 fail-closed positive control suite. |
| 9 | **Prompt-Advice Leakage** | L1 -> L2 | Overly prescriptive host constraints | Experimental validity | Recommended constraints give away the exact algorithm/action rather than physical limits. | Frozen deterministic rules based strictly on physical thresholds (e.g. "avoid allocations >16MB"), tested in ablation (A/B/C/D). | Model interprets physical bounds as action hints. | Context-isolated design reviews prior to G3. |
| 10 | **Excessive Telemetry Salience** | L1 -> L2 | Oversized prompt envelope | Agent attention | Telemetry drowns out task instructions or causes instruction distraction. | Compact token footprint (<300 tokens, <1800 chars); Condition B (neutral control) isolates attention tax. | Model-specific attention biases. | `test_renderer_bounded_output_size`. |
| 11 | **Attention and Token Overhead** | L1 -> L2 | Dynamic envelope size | Economic efficiency | High per-turn token consumption increases latency and API costs. | Delta snapshotting reduces repeated state; minimal string formatting. | Tokenizer variations across models. | Token-budget validation in `test_renderer.py`. |
| 12 | **Observer Overhead** | L0 Host | High-frequency kernel metric polling | Substrate performance | Heavy collector CPU utilization causes throttling or artificial latency. | Event-driven span collection; cgroup sampling restricted to pre-decision checkpoints (<=5Hz). | Minimal CPU time for /sys/fs/cgroup reads (<0.1ms per read). | G1 collector overhead benchmarking. |
| 13 | **Host/Model Clock Disagreement** | L0 <-> L1 | Timezone / epoch mismatch | Freshness verification | Relative timestamp mismatch causes false staleness rejections. | Single monotonic host timestamp (`observed_at_ms`) relative to host epoch used across all components. | None. | `test_trajectory_monotonic_sequence_and_timestamps`. |
| 14 | **Corrupted Raw-Event Logs** | L0 Storage | Partial disk write or crash | Trajectory auditability | Trajectory cannot be cryptographically verified against raw telemetry. | Atomic JSONL writes; each snapshot records immutable SHA-256 hashes of all contributing raw events. | Filesystem unbuffered crash (mitigated by fsync on checkpoint). | `test_reducer_audit_linkage_to_raw_event_hashes`. |
| 15 | **Unsupported Metric Ambiguity** | L0 -> L1 | Missing hardware sensors (e.g. no GPU, missing PSI) | Decision reliability | Unsupported metric reported as `0` instead of missing, misleading model. | Strict rule: missing values represented as `null`, `available: false`, or omitted, rendered as `UNAVAILABLE` (never `0`). | Model misinterpreting `UNAVAILABLE`. | `test_renderer_explicit_unavailable_rendering`. |
| 16 | **Privacy & Secret Leakage** | L0 / L3 -> L1 | Environment variables, API keys, raw headers | Data security | Authorization headers or credentials rendered into model context. | Reducer strips all HTTP headers, credentials, tokens, and payloads; only normalized error classes (`HTTP_429`, `HTTP_503`) recorded. | None. | `test_no_secrets_or_raw_headers_in_rendered_output`. |
| 17 | **Multi-Tenant Data Leakage** | L0 Host | Shared host executing multiple concurrent trials | Experimental isolation | Metrics from concurrent trial contaminate target trial cgroup. | Dedicated isolated cgroup hierarchy per trial; cgroup paths pinned by trajectory ID. | Kernel cgroup nesting bugs. | Trajectory ID validation in `validate_trajectory`. |

---

## 3. Trust Boundary Verification Checklist

- [x] All privileged schemas enforce `additionalProperties: false`.
- [x] Snapshot cryptographic identities (`snapshot_id`) verify canonical body SHA-256.
- [x] Trajectory validator enforces monotonic sequence numbers and timestamps.
- [x] Reducer executes deterministically without network or model invocation.
- [x] Renderer output is bounded, sanitizes credentials, and explicitly flags `UNAVAILABLE` values.
