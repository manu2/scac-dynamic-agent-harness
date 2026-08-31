# Agent Harness Awareness: Turning Verified Telemetry into Operational Control for Tool-Using Agents

Manu Agrawal and Shrey Nagpal

## Abstract

Tool-using agents commonly choose among APIs from task semantics and tool descriptions while the execution harness separately observes latency, failures, and route health. This separation creates **operational blindness**: a healthy route and a degraded route can look identical at the decision where the choice matters. We introduce **Agent Harness Awareness**, a trust-separated design in which compact, fresh, host-verified operational state becomes a first-class control input while measurement, enforcement, and evaluation remain outside the model. In a frozen 216-decision direct-provider ToolRoute cohort spanning GPT-5.6 Sol, Claude Sonnet 5, and Gemini 3.7 Flash, truthful tool-health state reduced mean observable policy regret by 96.9% versus a neutral same-shape telemetry control (4,252 ms to 131 ms) and increased completion from 69.4% to 95.8%. We separately reproduce the decision effect in a standards-based live transport integration: 27 remote-model decisions over actual local TCP/HTTP routes, OpenTelemetry HTTP client spans, and Toxiproxy-injected latency, connection, and HTTP failures. There, verified state produced 9/9 successful, zero-regret selections across all model families and fault regimes, versus 5/9 completion and 8,956 ms mean regret for the neutral control. Telemetry need not terminate at human dashboards: selected, verified operational facts can become direct control inputs for autonomous agents.

## 1. From operational blindness to closed-loop control

An agent can understand a user request and every tool's semantics yet still make an avoidable operational error. The missing information is often not semantic; it is the current state of the harness: which route is slow, failing, rate-limited, stale, resource-constrained, or no longer economical. When the harness knows this state but the agent does not, equivalent APIs remain indistinguishable at the moment the agent selects one.

We call this gap **operational blindness**. **Agent Harness Awareness** closes it by reducing bounded, freshness-labelled, host-verified execution state into an agent decision interface. The host retains authority over collection, reduction, safety, and enforcement. The model may adapt its next strategic action, but cannot rewrite the measurements, disable constraints, or modify the evaluator.

This paper contributes a general systems paradigm, a trust-separated state interface, a frozen 216-decision multi-model information ablation, and a separately analysed 27-decision OpenTelemetry/Toxiproxy transport replication. The contribution is not a new tool-call syntax or model ranking. It is evidence that what an agent knows about its harness can be as consequential as what it knows about the user task. This addresses a practical reliability gap: recent agent evaluations find that controlled tool/API failures and dynamic replanning remain difficult even when ordinary task execution succeeds (Gupta, 2026; Zhu et al., 2026). Harness Awareness supplies a distinct missing capability: make verified current operational facts available *before* the consequential route decision.

## 2. Agent Harness Awareness

At decision time $t$, let $x_t$ denote the task and tool interface, $h_t$ the host operational state, and $z_t = \phi(h_t)$ a bounded host-generated projection. Harness Awareness asks whether a policy using $(x_t,z_t)$ takes a lower-loss operational action than one using $x_t$ alone or an otherwise identical neutral interface.

The proposed **Substrate State Telemetry (SST) contract** is intentionally minimal and trust-separated. It can expose four families of facts: **tools** (success history, latency, error/circuit state); **runtime** (deadlines and exit state); **hardware** (memory, CPU, disk, processes); and **economics** (context headroom, quota, rate, cost). ToolRoute evaluates the tools family. The other dimensions are direct future instantiations, not pooled evidence.

Harness Awareness complements rather than replaces deterministic systems controls. The data plane—kernel, proxy, circuit breaker, retry policy, and scheduler—continues to own immediate recovery and safety. The agent control plane acts when current state changes strategy: choose a route, defer work, adopt a degraded-mode plan, or allocate time and budget differently.

## 3. ToolRoute method

The task is to retrieve a read-only customer record via one of two functionally equivalent routes, `tool_alpha` and `tool_beta`, or choose `wait`. The host owns monitoring, schedules, execution, and an external observable-cost oracle. Each decision is an independent full-checkpoint episode; models have no shell, filesystem, network-tool, schedule, oracle, or artifact access.

| Condition | Model-visible information |
| --- | --- |
| A: task only | Task and equivalent tool descriptions; no operational projection. |
| B: neutral envelope | Same telemetry-shaped envelope, fields, row order, and tool rows as C, with equal neutral values for both routes. |
| C: verified state | The same envelope with fresh host-owned facts for current route state. |

B is the structural control. It holds interface shape and technical content constant while neutralizing route-relevant values, isolating operational information from the presence of a table or extra prompt text. It is not an exact provider-token-matching control; input-token counts are descriptive.

The primary outcome is **observable policy regret**: excess selected-action cost under an oracle restricted to canonical facts rendered in C. This avoids scoring a model against latent reliability it could not observe. The frozen direct-provider cohort contains 216 independent decisions: three model families × six seeds × four turns × three conditions. Every attempt retained a prompt, sanitized request/response, snapshot, tool event, evaluation result, and finalization hashes; no request was retried.

### 3.1 Live OpenTelemetry transport replication

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

### 4.1 Frozen ToolRoute cohort

Across 72 decisions per condition, C reduces mean observable policy regret from 4,251.54 ms in B to 131.12 ms: a 96.9% reduction. Completion rises from 50/72 (69.4%; Wilson 95% CI 58.0–79.0%) to 69/72 (95.8%; Wilson 95% CI 88.3–98.5%), a 26.4-point increase. A is also materially worse than C (4,826.45 ms regret; 47/72 completion), demonstrating that a telemetry-shaped envelope alone does not explain the result.

| Model | A regret (ms) | B regret (ms) | C regret (ms) | C completion |
| --- | ---: | ---: | ---: | ---: |
| GPT-5.6 Sol | 4,723.81 | 3,307.00 | 75.50 | 23/24 (95.8%) |
| Claude Sonnet 5 | 5,031.72 | 4,723.81 | 75.50 | 23/24 (95.8%) |
| Gemini 3.7 Flash | 4,723.81 | 4,723.81 | 242.35 | 23/24 (95.8%) |

![A, B, and C observable policy regret](figures/figure_1_conditions_log.pdf)

*Figure 1. Mean observable policy regret for all three information conditions in the frozen 216-decision cohort. Log scaling keeps verified-state values visible; A, B, and C are independent condition means, not trajectories.*

### 4.2 Live transport replication

The transport replication reproduces the central result without relying on the synthetic monitor. Across nine B decisions, models completed 5/9 actions (55.6%) and incurred 8,956.37 ms mean observable policy regret. Across nine C decisions, models selected the observable-best route in **9/9 cases**, completed **9/9 live actions**, and incurred **0.00 ms** mean observable policy regret: a 100% B-to-C regret reduction in this frozen replication.

The result holds in every model family and every predeclared fault regime. C contains one latency, one connection-error, and one HTTP-error episode for Gemini 3.7 Flash, Claude Sonnet 5, and GPT-5.6 Sol; every C decision selected the viable route from OTel-derived state and that route completed over the live proxied HTTP path.

| Model | A: success / 3 | B: success / 3 | C: success / 3 | C mean regret |
| --- | ---: | ---: | ---: | ---: |
| GPT-5.6 Sol | 2 | 1 | 3 | 0.00 ms |
| Claude Sonnet 5 | 2 | 2 | 3 | 0.00 ms |
| Gemini 3.7 Flash | 2 | 2 | 3 | 0.00 ms |
| **Total** | **6/9** | **5/9** | **9/9** | **0.00 ms** |

![OpenTelemetry transport replication outcome matrix](figures/figure_2_transport_replication.pdf)

*Figure 2. The nine verified-state cells in the 27-decision OpenTelemetry/Toxiproxy replication. Each selected the observable-best route and completed the subsequent live proxied HTTP action; the adjacent chart reports all A/B/C completion outcomes.*

The counterbalanced design also exposes the baseline decision pattern that the state interface corrects. Across A and B, models selected `tool_alpha` in 17 of 18 decisions (94.4%), including 7 of 8 cases in which `tool_beta` was listed first. We describe this as an observed **default route-label preference** in this cohort, not as a claim about universal positional bias. Condition C removed its operational consequence: the model selected the healthy route in every regime regardless of which route was degraded or listed first.

The two cohorts answer complementary questions. The 216-decision cohort isolates a repeated behavioral effect under a precisely controlled monitor. The 27-decision cohort shows that the same information intervention survives a real instrumented tool path: telemetry is collected from actual requests, reduced by the host, supplied to the model, and followed by a live route execution. Together, they support a strong systems conclusion: **verified operational telemetry is a high-leverage control input for agentic tool use.**

## 5. Implications, boundaries, and agenda

Modern observability systems collect traces, metrics, and logs for human operators. Harness Awareness supplies the missing control-plane step: select the facts relevant to the immediate decision, preserve provenance and freshness, and expose the bounded result to the agent without giving it authority over truth or enforcement.

The principle applies to alternate-region routing, deadline-aware planning, quota-aware work decomposition, context-budget checkpointing, resource-aware concurrency, and multi-agent backpressure. The correct interface is not a raw telemetry dump; it is narrow, redacted, freshness-labelled, and host-owned.

The evidence is strong for the mechanism tested here: current verified tool-health facts improve selection between functionally equivalent routes. The primary cohort uses a synthetic host-owned monitor; the replication uses a minimal local HTTP service and deterministic proxy faults. Neither study claims uncontrolled production-outage rates, universal service topologies, or completed evidence for hardware, runtime, and economic state. Those are the next high-value tests, not prerequisites for the demonstrated control-loop effect.

## 6. Conclusion

Agent Harness Awareness closes an operational loop that tool-using systems often leave open: the harness observes execution state while the agent chooses as if that state did not exist. In a frozen 216-decision cohort, verified state reduced mean observable policy regret by 96.9% and raised completion by 26.4 points against a neutral same-shape control. In a separately reported 27-decision OpenTelemetry/Toxiproxy replication, verified state selected the best route and completed the live action in all nine C episodes across three providers and three fault regimes. The evidence supports a clear systems direction: turn selected, verified telemetry into an active agent control input while keeping truth and enforcement in the harness.

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
