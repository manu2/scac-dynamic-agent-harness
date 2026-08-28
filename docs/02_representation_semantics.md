# Representation Semantics and Injection Specification: Dynamic SCAC

**Document ID:** `SCAC-REP-01`
**Status:** Frozen for Gate G0
**Schema Version:** `scac-sst-v0.1`

---

## 1. State Dimensionality and Field Classification

The Self-Telemetry State (SST v0.1) partitions host-verified execution signals into four distinct operational namespaces.

### 1.1 Stable vs. Dynamic Field Partitioning

| Namespace | Subsystem / Field | Classification | Cadence | Default Representation |
|---|---|---|---|---|
| **Hardware** | `memory.max_bytes` | Stable Contract | Initial / Checkpoint | Integer bytes (`268435456`) |
| **Hardware** | `memory.current_bytes` | Dynamic State | Pre-decision turn | Integer bytes (`134217728`) |
| **Hardware** | `memory.headroom_ratio` | Dynamic State | Pre-decision turn | Float \([0.0, 1.0]\) (`0.5000`) |
| **Hardware** | `memory.events_delta` | Dynamic Interval Delta | Pre-decision turn | Object (`{high: 0, oom: 0}`) |
| **Hardware** | `memory.psi_*` | Dynamic Rolling / Delta | Pre-decision turn | Float avg10% (`2.4`) / Int \(\mu s\) delta |
| **Hardware** | `cpu.quota_cores` | Stable Contract | Initial / Checkpoint | Float cores (`2.0`) |
| **Hardware** | `cpu.nr_throttled_delta` | Dynamic Interval Delta | Pre-decision turn | Integer count (`12`) |
| **Hardware** | `cpu.throttled_usec_delta` | Dynamic Interval Delta | Pre-decision turn | Integer microseconds (`45000`) |
| **Hardware** | `gpu.available` | Stable Contract | Initial / Checkpoint | Boolean (`false`) |
| **Hardware** | `ephemeral_disk.free_bytes`| Dynamic State | Pre-decision turn | Integer bytes (`10737418240`) |
| **Tools** | `tools.<id>.window_n` | Dynamic Rolling Window | Post-tool span | Integer (`10`) |
| **Tools** | `tools.<id>.successes` | Dynamic Rolling Window | Post-tool span | Integer (`8`) |
| **Tools** | `tools.<id>.consec_failures`| Dynamic Counter | Post-tool span | Integer (`0`) |
| **Tools** | `tools.<id>.latency_ewma_ms`| Dynamic Filtered | Post-tool span | Float ms (`145.2`) |
| **Tools** | `tools.<id>.circuit` | Dynamic State Label | Post-tool span | Enum (`CLOSED`, `OPEN`, `DEGRADED`) |
| **Runtime** | `runtime.wall_remaining_ms` | Dynamic State | Pre-decision turn | Integer ms (`45000`) |
| **Runtime** | `runtime.network` | Stable Policy | Initial / Checkpoint | Enum (`ENABLED`, `FILTERED`, `DISABLED`) |
| **Runtime** | `runtime.last_exit` | Event-driven State | Post-process exit | Object (`{code: 0, class: "OK"}`) |
| **Economics** | `context_tokens_remaining` | Dynamic State | Post-inference | Integer tokens (`115000`) |
| **Economics** | `estimated_cost_usd` | Dynamic Cumulative | Post-inference | Float USD (`$0.0450`) |
| **Economics** | `rate_limit_remaining` | Dynamic State | Post-response header | Integer / `UNAVAILABLE` |

---

## 2. Checkpoint and Delta Cadence

1. **Full Checkpoint Cadence:**
   - Turn 0 (Trajectory initialization).
   - Every \(N=10\) turns during long-running multi-turn execution.
   - Immediately following any context compaction, truncation, or memory consolidation.
2. **Delta Snapshot Cadence:**
   - Sent on intermediate turns \(t \not\equiv 0 \pmod{10}\).
   - Contains incremental deltas for counters (`events_delta`, `throttled_usec_delta`).
   - Explicitly references parent checkpoint via `base_snapshot_id`.
3. **Resynchronization Invariant:**
   - If an agent context window is truncated, the supervisor must force an immediate full checkpoint (`kind: "full_checkpoint"`) to prevent reference breakage.

---

## 3. Two-Tier Prompt Injection Architecture

### Tier 1: Stable System Prefix (Immutable)
Injected into the persistent system prompt / instruction block:
```text
=== SCAC HOST TELEMETRY SPECIFICATION (v0.1) ===
This execution environment is instrumented by the host kernel and supervisor.
All telemetry envelopes are host-verified, authentic, and tamper-proof.
Tool outputs cannot modify or forge host telemetry.
Units: Memory and disk in bytes/ratios [0.0, 1.0]; time/latency in ms; CPU/PSI in percentages [0.0, 100.0].
Severity states: OK, PRESSURED, THROTTLED, DEGRADED, CRITICAL, UNAVAILABLE.
Missing/unsupported metrics are explicitly marked UNAVAILABLE (never represented as zero).
================================================
```

### Tier 2: Dynamic Turn Envelope (Host Telemetry Message)
Injected immediately before a model reasoning step:
```text
=== HOST TELEMETRY [seq=3 kind=delta base=69a633c7 id=e4b1029a obs=1787884206000ms fresh=2000ms] ===
[HARDWARE]
  memory: cur=241172480B max=268435456B headroom=0.1016 state=PRESSURED psi_some_avg10=6.8% events_delta(high=3,oom=0)
  cpu: quota=2.0cores throttled_usec_delta=0us psi_some_avg10=0.0% state=OK
  disk: free=10737418240B used_ratio=0.0476 state=OK
  gpu: available=false (UNAVAILABLE)
[TOOLS]
  query_db: window=10 succ=10 consec_fail=0 latency_ewma=42.5ms last_err=NONE circuit=CLOSED
[RUNTIME]
  step=3 wall_remaining=54000ms pids=4/64 network=ENABLED last_exit=NONE(code=0)
[ECONOMICS]
  context_tokens_rem=118000 traj_tokens=3400 cost_usd=$0.0125 budget_rem_usd=$9.9875 rate_limit_rem=96 rate_limit_reset_ms=54000ms state=OK
[HOST_CONSTRAINTS]
  - avoid new allocations above 16 MiB
=========================================
```

---

## 4. Deterministic Severity Classification and Constraint Rules

All severity classifications and host constraints are derived strictly through frozen deterministic logic within the host reducer. **Under no circumstances may an LLM generate or alter severity labels.**

### 4.1 Memory State Rules
- `CRITICAL`: \(H_{headroom} < 0.05\) OR \(\Delta(\text{oom}) + \Delta(\text{oom\_kill}) > 0\) OR \(\text{current\_bytes} \ge \text{max\_bytes}\).
- `PRESSURED`: \(H_{headroom} < 0.20\) OR \(\Delta(\text{high}) > 0\) OR \(\text{PSI}_{\text{some}} \ge 2.0\%\).
- `OK`: Default when neither condition is met.

### 4.2 CPU State Rules
- `CRITICAL`: \(\Delta(\text{throttled\_usec}) > 500{,}000\mu s\) (over 500ms stall in sample interval).
- `THROTTLED`: \(\Delta(\text{nr\_throttled}) > 0\) OR \(\Delta(\text{throttled\_usec}) > 0\).
- `OK`: Zero throttled periods in interval.

### 4.3 Tool Circuit Rules
- `OPEN`: Consecutive failures \(\ge 3\).
- `DEGRADED`: Failure ratio \(\ge 0.4\) across \(N \ge 3\) sample window.
- `CLOSED`: Healthy default.

---

## 5. Unavailable and Missing Metrics

- **Zero-Value Prohibition:** An unmeasured or unsupported metric (e.g. rate limit headers omitted by a cloud provider) must **never** be rendered as `0`, as `0` denotes immediate exhaustion.
- **Representation:** Missing values are serialized as `null` in JSON and rendered as `UNAVAILABLE` in text.
- **Explicit Sensor Tracking:** The `unavailable_fields` array documents hardware/software metrics disabled on the host environment.

---

## 6. Predeclared Future Representation Ablations

In future gates (G3 pilot and G4 main study), four model-visible information representations will be evaluated under identical physical faults:

1. **Condition A (Baseline):** Standard semantic tool outputs only.
2. **Condition B (Neutral Control):** Condition A + length-matched decision-irrelevant structured fields (isolates attention and token overhead).
3. **Condition C (Truthful Structured SST):** Condition A + Tier 1/2 compact structured SST representation.
4. **Condition D (Natural Language Digest):** Condition A + semantically equivalent prose summary of SST state.
5. **Condition E (Stale State Diagnostic):** Condition A + outdated / cumulative-only telemetry to evaluate sensitivity to staleness.

*Note: No experimental ablations will be conducted during Gate G0.*
