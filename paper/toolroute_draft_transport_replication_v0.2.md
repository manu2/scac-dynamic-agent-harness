# Agent Harness Awareness: Turning Verified Telemetry into Operational Control for Tool-Using Agents

Manu Agrawal and Shrey Nagpal

## Abstract

Autonomous agents increasingly act through tools, yet their harnesses keep the operational facts that determine whether those actions will succeed—latency, failures, route health, deadlines, quotas, and resource pressure—outside the agent’s decision loop. This creates **operational blindness**: semantically equivalent actions can have radically different operational consequences while appearing identical to the model. We introduce **Agent Harness Awareness**, a trust-separated control architecture that converts bounded, fresh, host-verified telemetry into an agent decision input while keeping measurement, enforcement, and evaluation outside the model. We evaluate the tools-and-network instance in two separately analysed frozen studies. In the primary 216-decision direct-provider ToolRoute ablation across GPT-5.6 Sol, Claude Sonnet 5, and Gemini 3.7 Flash, verified tool-health state reduced mean observable policy regret by **96.9%** against a neutral same-shape interface (4,252 ms to 131 ms) and raised completion from **69.4% to 95.8%**. In a separate 27-decision end-to-end replication using live local TCP/HTTP execution, OpenTelemetry client spans, and Toxiproxy-injected faults, verified state selected the observable-best route and completed the live action in **9/9** model-by-fault cases, versus **5/9** completion for the neutral control. These results establish a practical systems principle: telemetry should not end at human dashboards. Selected, provenance-preserving operational state can serve as a high-leverage control input for autonomous agents.

## 1. From operational blindness to closed-loop control

An agent can understand a user request and every tool's semantics yet still make an avoidable operational error. The missing information is often not semantic; it is the current state of the harness: which route is slow, failing, rate-limited, stale, resource-constrained, or no longer economical. When the harness knows this state but the agent does not, equivalent APIs remain indistinguishable at the moment the agent selects one.

This is a general agent-runtime problem, not merely a routing problem. Agent harnesses already observe four high-value operational dimensions: **tools and network** (route health, errors, circuit state); **runtime** (deadlines, queueing, and concurrency); **hardware and sandbox** (memory headroom, CPU pressure, storage); and **economics** (context headroom, token burn, quota, and cost). A harness-aware agent can use these facts for alternate-route selection, deadline-aware decomposition, checkpointing before budget exhaustion, resource-aware concurrency, and backpressure-aware coordination. The challenge is to expose a trustworthy, decision-relevant projection without handing the model authority over measurement or enforcement.

We call this gap **operational blindness**. **Agent Harness Awareness** closes it by reducing bounded, freshness-labelled, host-verified execution state into an agent decision interface. The host retains authority over collection, reduction, safety, and enforcement. The model may adapt its next strategic action, but cannot rewrite the measurements, disable constraints, or modify the evaluator.

This paper contributes a general systems paradigm, a trust-separated state interface, a frozen 216-decision multi-model information ablation, and a separately analysed 27-decision OpenTelemetry/Toxiproxy transport replication. The contribution is not a new tool-call syntax or model ranking. It is evidence that what an agent knows about its harness can be as consequential as what it knows about the user task. This addresses a practical reliability gap: recent agent evaluations find that controlled tool/API failures and dynamic replanning remain difficult even when ordinary task execution succeeds (Gupta, 2026; Zhu et al., 2026). Harness Awareness supplies a distinct missing capability: make verified current operational facts available *before* the consequential route decision.

## 2. Agent Harness Awareness

At decision time $t$, let $x_t$ denote the task and tool interface, $h_t$ the host operational state, and $z_t = \phi(h_t)$ a bounded host-generated projection. Harness Awareness asks whether a policy using $(x_t,z_t)$ takes a lower-loss operational action than one using $x_t$ alone or an otherwise identical neutral interface.

The proposed **Substrate State Telemetry (SST) contract** is intentionally minimal and trust-separated. It can expose four families of facts: **tools** (success history, latency, error/circuit state); **runtime** (deadlines and exit state); **hardware** (memory, CPU, disk, processes); and **economics** (context headroom, quota, rate, cost). ToolRoute evaluates the tools family. The other dimensions are direct future instantiations, not pooled evidence.

Harness Awareness complements rather than replaces deterministic systems controls. The data plane—kernel, proxy, circuit breaker, retry policy, and scheduler—continues to own immediate recovery and safety. The agent control plane acts when current state changes strategy: choose a route, defer work, adopt a degraded-mode plan, or allocate time and budget differently.

## 3. Two complementary ToolRoute studies

ToolRoute evaluates the tools-and-network dimension through two deliberately distinct studies. They answer different questions and are analysed separately throughout this paper.

| Study | Question | Evidence | Role in the paper |
| --- | --- | --- | --- |
| **Study 1: controlled information ablation** | Does truthful state improve route selection when the decision interface is held constant? | 216 frozen direct-provider decisions; seeded host-owned monitor. | Primary behavioral estimate. |
| **Study 2: live transport replication** | Does the same information effect survive a standard-telemetry, actual HTTP tool path? | 27 frozen remote-model decisions; OTel spans, Toxiproxy, and live selected-route execution. | End-to-end systems replication; never pooled with Study 1. |

### 3.1 Study 1: controlled information ablation

The task is to retrieve a read-only customer record via one of two functionally equivalent routes, `tool_alpha` and `tool_beta`, or choose `wait`. The host owns monitoring, schedules, execution, and an external observable-cost oracle. Each decision is an independent full-checkpoint episode; models have no shell, filesystem, network-tool, schedule, oracle, or artifact access.

| Condition | Model-visible information |
| --- | --- |
| A: task only | Task and equivalent tool descriptions; no operational projection. |
| B: neutral envelope | Same telemetry-shaped envelope, fields, row order, and tool rows as C, with equal neutral values for both routes. |
| C: verified state | The same envelope with fresh host-owned facts for current route state. |

**A is the deployment baseline:** task and tool semantics alone, approximating conventional agent behavior without harness state. **B is the structural control:** the same telemetry-shaped interface with all route-relevant values neutralized. **C is the intervention:** verified current state. Thus A-to-C measures the practical deployment gain, while B-to-C isolates the informational contribution of telemetry from interface shape and formatting. B is not an exact provider-token-matching control; input-token counts are descriptive.

We report two complementary outcomes. **Observable policy regret** is the avoidable observable operational cost of the selected action: \(r_{\mathrm{obs}}(a,z)=c_{\mathrm{obs}}(a,z)-\min_{a'}c_{\mathrm{obs}}(a',z)\). The host computes \(c_{\mathrm{obs}}\) using only canonical monitor facts rendered in C, combining monitored latency with predeclared failure, circuit-open, and missed-record penalties. It is reported in milliseconds; **0 ms regret means that the agent selected an observable-best action with no excess operational cost, not that the request itself took zero time.** The evaluator never uses hidden latent anomalies unavailable to the model. **Completion** is a separate binary outcome: whether the selected route successfully retrieves the requested record; in Study 2, whether the post-decision live HTTP action succeeds. A route can complete yet still have positive regret when it was avoidably slower or riskier.

The frozen direct-provider cohort contains 216 independent decisions: three model families × six seeds × four turns × three conditions. Every attempt retained a prompt, sanitized request/response, snapshot, tool event, evaluation result, and finalization hashes; no request was retried.

### 3.2 Study 2: live OpenTelemetry transport replication

The separately labelled v0.2 replication preserves the same A/B/C intervention but changes the observation and execution substrate:

```text
instrumented HTTP client → Toxiproxy → equivalent local HTTP route
          │                                      │
          └── OpenTelemetry client spans ────────┘
                         │
          host-owned reducer → bounded agent state → model decision
                                                        │
                                           live selected-route execution
```

Each episode takes three monitor requests per route through actual local TCP/HTTP proxies. Standard OpenTelemetry HTTP client spans provide duration and outcome facts; the host reducer converts them to the ToolRoute snapshot. Toxiproxy injects a predeclared 300 ms latency, connection failure, or HTTP 503 on one route. The model's chosen route is then executed through the same still-live proxy.

The frozen replication contains 27 independent decisions: three model families × three fault regimes × A/B/C. Provider/model, condition, faulted route, option order, execution order, no-retry policy, manifest SHA-256, and Toxiproxy binary SHA-256 were fixed before execution. Raw standard spans, reducer events, selected condition prompts, sanitized provider records, post-decision action spans, results, and finalization hashes are retained. These data are reported separately and never pooled with the 216-decision cohort.

## 4. Results

### 4.1 Study 1: controlled information ablation

Against the task-only deployment baseline A, verified state C reduces mean observable policy regret from 4,826.45 ms to 131.12 ms: a **97.3% reduction**. Completion rises from 47/72 (65.3%) to 69/72 (95.8%), a **30.6-point increase**. The structural B-to-C comparison reaches the same conclusion while holding interface shape constant: regret falls from 4,251.54 ms to 131.12 ms (**96.9% lower**) and completion rises from 50/72 (69.4%; Wilson 95% CI 58.0–79.0%) to 69/72 (95.8%; Wilson 95% CI 88.3–98.5%), a **26.4-point increase**. Together, these comparisons show both practical deployment value and the informational contribution of verified telemetry.

| Condition | Role | Mean observable regret (ms) | Completion |
| --- | --- | ---: | ---: |
| A | Task-only deployment baseline | 4,826.45 | 47/72 (65.3%) |
| B | Neutral structural control | 4,251.54 | 50/72 (69.4%) |
| C | Verified host state | 131.12 | 69/72 (95.8%) |

![A, B, and C observable policy regret](figures/figure_1_conditions_log.pdf)

*Figure 1. Mean observable policy regret for all three information conditions in the frozen 216-decision cohort. Log scaling keeps verified-state values visible; A, B, and C are independent condition means, not trajectories.*

### 4.2 Study 2: live transport replication

The transport replication reproduces the central result without relying on the synthetic monitor. The task-only deployment baseline A completed 6/9 live actions (66.7%) with 6,734.30 ms mean observable policy regret. The neutral structural control B completed 5/9 actions (55.6%) with 8,956.37 ms regret. Verified state C selected the observable-best route in **9/9 cases**, completed **9/9 live actions**, and incurred **0.00 ms** regret. Thus C improves both the practical task-only baseline and the same-shape structural control, while the B-to-C comparison isolates the information effect.

The result holds in every model family and every predeclared fault regime. C contains one latency, one connection-error, and one HTTP-error episode for Gemini 3.7 Flash, Claude Sonnet 5, and GPT-5.6 Sol; every C decision selected the viable route from OTel-derived state and that route completed over the live proxied HTTP path.

| Model | A: success / 3 | B: success / 3 | C: success / 3 | C mean regret |
| --- | ---: | ---: | ---: | ---: |
| GPT-5.6 Sol | 2 | 1 | 3 | 0.00 ms |
| Claude Sonnet 5 | 2 | 2 | 3 | 0.00 ms |
| Gemini 3.7 Flash | 2 | 2 | 3 | 0.00 ms |
| **Total** | **6/9** | **5/9** | **9/9** | **0.00 ms** |

![OpenTelemetry transport replication outcome matrix](figures/figure_2_transport_replication.pdf)

*Figure 2. Study 2 live transport replication. The upper panel shows that all nine verified-state C cases selected the observable-best route and completed the subsequent live proxied HTTP action. The lower panel reports mean observable policy regret and live completion for all A/B/C conditions, highlighting the B-to-C structural-control comparison. Here, 0 ms regret denotes zero excess observable operational cost, not zero HTTP duration.*

The counterbalanced design also exposes the baseline decision pattern that the state interface corrects. Across A and B, models selected `tool_alpha` in 17 of 18 decisions (94.4%), including 7 of 8 cases in which `tool_beta` was listed first. We describe this as an observed **default route-label preference** in this cohort, not as a claim about universal positional bias. Condition C removed its operational consequence: the model selected the healthy route in every regime regardless of which route was degraded or listed first.

The two studies answer complementary questions. Study 1 isolates a repeated behavioral effect under a precisely controlled monitor. Study 2 shows that the same information intervention survives a real instrumented tool path: telemetry is collected from actual requests, reduced by the host, supplied to the model, and followed by a live route execution. Together, they support a strong systems conclusion: **verified operational telemetry is a high-leverage control input for agentic tool use.**

## 5. Implications, boundaries, and agenda

Modern observability systems collect traces, metrics, and logs for human operators. Harness Awareness supplies the missing control-plane step: select the facts relevant to the immediate decision, preserve provenance and freshness, and expose the bounded result to the agent without giving it authority over truth or enforcement.

The principle applies to alternate-region routing, deadline-aware planning, quota-aware work decomposition, context-budget checkpointing, resource-aware concurrency, and multi-agent backpressure. The correct interface is not a raw telemetry dump; it is narrow, redacted, freshness-labelled, and host-owned.

The evidence is strong for the mechanism tested here: current verified tool-health facts improve selection between functionally equivalent routes. The primary cohort uses a synthetic host-owned monitor; the replication uses a minimal local HTTP service and deterministic proxy faults. Neither study claims uncontrolled production-outage rates, universal service topologies, or completed evidence for hardware, runtime, and economic state. Those are the next high-value tests, not prerequisites for the demonstrated control-loop effect.

## 6. Conclusion

Agent Harness Awareness closes an operational loop that tool-using systems often leave open: the harness observes execution state while the agent chooses as if that state did not exist. In the frozen controlled cohort, verified state substantially outperformed both the task-only deployment baseline and the neutral same-shape structural control; the latter shows that the improvement is attributable to verified operational information rather than interface formatting. In the separately reported OpenTelemetry/Toxiproxy replication, that same information intervention selected the observable-best route and completed every C action across three providers and three fault regimes. The evidence supports a clear systems direction: turn selected, verified telemetry into an active agent control input while keeping truth and enforcement in the harness.

## References

- Yao et al. *ReAct: Synergizing Reasoning and Acting in Language Models*. ICLR 2023. https://arxiv.org/abs/2210.03629
- Schick et al. *Toolformer: Language Models Can Teach Themselves to Use Tools*. NeurIPS 2023. https://arxiv.org/abs/2302.04761
- Liu et al. *AgentBench: Evaluating LLMs as Agents*. ICLR 2024. https://arxiv.org/abs/2308.03688
- Yao et al. *tau-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains*. ICLR 2025. https://arxiv.org/abs/2406.12045
- OpenTelemetry. *Specification*. https://opentelemetry.io/docs/specs/
- Shopify. *Toxiproxy*. https://github.com/Shopify/toxiproxy
- He and Yu. *Agent-Native Telemetry: Verifiable State-Delta Evidence for Autonomous Operations*. 2026. https://arxiv.org/abs/2608.16178
- Gupta. *ReliabilityBench: Evaluating LLM Agent Reliability Under Production-Like Stress Conditions*. 2026. https://arxiv.org/abs/2601.06112
- Zhu et al. *When Tools Fail: Benchmarking Dynamic Replanning and Anomaly Recovery in LLM Agents*. 2026. https://arxiv.org/abs/2606.05806
