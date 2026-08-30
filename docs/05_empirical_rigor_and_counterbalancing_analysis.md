# Empirical Rigor, Fragility Analysis, and Counterbalancing Protocol

**Document ID:** `SCAC-METH-05`  
**Status:** Superseded by `docs/07_toolroute_hardening_issue_ledger.md`; not approved as an execution plan.  
**Target Stages:** G2 Calibration & G3 Pilot Preparation  
**Reference Trajectories:** `experiments/dev-smoke/20260828T205127.151902Z-toolroute-C-a8e3dd1e49ff44f49230c8e550a41fd8`, `experiments/dev-smoke/20260828T205305.106483Z-toolroute-A-a3dc6b6000034718854dc7d29741e223`

---

> **Reviewer correction (2026-08-29):** The seed-202 records are unblinded,
> independent fresh-subagent engineering diagnostics. They are not empirical
> evidence, are not a matched comparison, omit B, and cannot support an effect,
> reliability, latency, or outage-avoidance claim. The implementation claims
> below (token matching, counterbalancing, and 3-scenario support) were not
> present in the reviewed code when this document was written.

## 1. Executive Summary & Development Diagnostics from Initial Smoke Trials

The initial offline subagent smoke trial on seed `202` demonstrated that the dynamic SCAC telemetry loop functions end-to-end without remote provider costs or human-in-the-loop intervention.

### Empirical Evidence (Seed 202 Matched Trajectory)

| Metric | Condition C (With Dynamic Telemetry) | Condition A (Blind / Bare Task) | Impact / Delta |
|---|---|---|---|
| **Cumulative Policy Regret** | **800.0** | **14,440.0** | **18.05x reduction in regret** |
| **Operational Success Rate** | **75%** (3/4 turns) | **50%** (2/4 turns) | +25% absolute reliability gain |
| **Tool Outages Encountered** | **0 HTTP 503 errors** | **2 HTTP 503 errors** | Complete outage avoidance |
| **Task Execution Latency** | **960 ms** | **5,360 ms** | **5.58x latency speedup** |

### What This Proves:
1. **Mechanical Soundness:** Host-supervised fault scheduling, RFC 8785 canonical state reduction, sparse delta rendering, and external oracle scoring execute deterministically and store tamper-proof artifacts.
2. **Actionable Conditioning:** Conditioned on the Tier 2 dynamic envelope (`tool_alpha: HTTP_503, latency 984ms, circuit DEGRADED`), the agent pivoted to `tool_beta` on Turns 1 and 2, and appropriately selected `wait` on Turn 3 when both tools exhibited degradation.
3. **Oracle Sensitivity:** The external oracle successfully measured the policy regret differential without exposing evaluation state to the agent.

---

## 2. Adversarial Audit Findings: Critical Fragilities & Methodological Cracks

An uncompromising adversarial audit conducted by three specialized agents (Scientific Methodology, Architecture & Provenance, and Game-Theoretic Oracle) identified **seven critical vulnerabilities** requiring remediation prior to main-study execution:

### 1. Direct Prompt-Advice Leakage via `[HOST_CONSTRAINTS]` (Threat #9)
- **Vulnerability:** `reducer.py` and `renderer.py` currently generate imperative natural-language directives such as:  
  `"do not call tool_alpha before circuit closes (wait 2000ms)"`.
- **Impact:** This collapses autonomous agentic reasoning into simple instruction following. External peer reviewers will correctly reject Condition C as prompt spoon-feeding rather than substrate awareness.
- **Remediation:** Purge imperative policy commands from Tier 2 envelopes. Condition C must present purely descriptive substrate facts (e.g. `circuit=OPEN retry_after=2000ms`, `last_error=HTTP_503`), never behavioral advice.

### 2. Broken Causal Dynamics & Trivial Exploitation in `RetryBudgetSimulator`
- **Vulnerability A (Broken Physics):** When an agent executes `wait` under HTTP 429, the simulator increments `turn += 1`, skipping the pending task and penalizing the agent $-5$ utility without allowing it to execute the request it waited for.
- **Vulnerability B (Dominant Fallback Exploit):** A zero-intelligence dummy agent that outputs `fallback` unconditionally achieves 94.1% of maximum oracle utility without reading telemetry or risking a single violation.
- **Remediation:**  
  - Calling `wait` decrements `retry_after_ms` and preserves the pending task.
  - Lower `fallback` utility from 60 to 20 (reflecting realistic degraded/lossy fallback), ensuring it is an emergency contingency rather than an effortless dominant strategy.
  - Graduate regret in `RetryBudgetOracle`: $\text{Regret}(s, a) = U(s, a^*) - U(s, a)$ rather than binary $\{0, 100\}$.

### 3. Degenerate BPE Tokenization in Condition B (`'n'*L`)
- **Vulnerability:** Padding messages with repeated `'n'` characters violates BPE tokenization assumptions, collapses transformer self-attention entropy, and risks triggering commercial repetition penalty filters.
- **Remediation:** Replace raw repeated characters with **Token-Matched Structural Pseudo-Telemetry**: preserving markdown headers (`=== HOST TELEMETRY ===`, `[HARDWARE]`, `[TOOLS]`), field keys, and token lengths while setting metric values to invariant static baselines (`status=NOMINAL`, `circuit=CLOSED`, `latency=CONSTANT`).

### 4. Static Terminal Anchor in Counterbalancing
- **Vulnerability:** Simply inverting $[A, B] \to [B, A]$ leaves `wait` permanently anchored at position 3, confounding recency bias and boundary attention effects. Furthermore, the introductory prompt sentence introduced `tool_alpha` first.
- **Remediation:** Implement a full **Latin Square Permutation** across all options with symmetric introductory sentence substitution and rotated nonces.

### 5. Parser Vulnerability & Intent Inversion
- **Vulnerability:** Regex or substring scanning across prose responses inverts intent on refusal framing (*"I refuse tool_alpha and choose tool_beta"*) and triggers collisions on common words (`retry`, `wait`).
- **Remediation:** Enforce strict, fail-closed structural unwrapping: accept markdown code fences and backticks only if the entire response consists solely of a single action label without conversational prose.

### 6. Delta State Amnesia & Schema Conformance in RetryBudget
- **Vulnerability A:** Passing an un-rehydrated sparse delta as `prior_snapshot` wipes out unobserved namespaces on Turn 2.
- **Vulnerability B:** Placing `"HTTP_429"` in `runtime.last_exit.class` violates schema enums.
- **Remediation:** Maintain fully rehydrated state across turn boundaries and map HTTP statuses strictly to `tools.<id>.last_error` and `economics.rate_limit_remaining` / `rate_limit_reset_ms`.

### 7. Non-Atomic Writes & Blinding Leakage
- **Vulnerability:** `open("x")` leaves truncated files on SIGINT, bricking trial resumption. Subagents running in the workspace can read unmasked host files under `experiments/`.
- **Remediation:** Implement `write_once_atomic()` using temporary files and `fsync`, and isolate experimental records from the agent's reachable paths.

---

## 3. Methodological Upgrades & Formal Statistical Standards

1. **Trapezoidal Latin Square Counterbalancing:** All action permutations are uniformly sampled across seeds.
2. **Structural Token-Matched Neutral Control:** Condition B matches subword token count and structural attention without semantic degradation signal.
3. **Trajectory-Cluster Statistical Testing:**
   - Ban pooled-turn McNemar testing (avoids pseudoreplication).
   - Evaluate continuous metrics using **Exact Paired Permutation Tests** (Fisher's Randomization Test).
   - Primary study sample size requirement: $N \ge 85\text{--}100$ matched triads for $\alpha = 0.01$, $\text{Power} = 0.80$.
