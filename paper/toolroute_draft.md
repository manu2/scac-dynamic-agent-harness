# Agent Harness Awareness: Verified Operational State as a First-Class Input to Tool-Using Agents

Manu Agrawal and Shrey Nagpal

## Abstract

Tool-using agents are commonly given a task and API descriptions while
remaining unaware of the operational state of the harness in which they act.
This operational blindness makes a feasible route and a degraded route look
identical at the moment the agent chooses. We introduce **Agent Harness
Awareness**, a closed-loop design in which compact, fresh, host-verified
execution state becomes a first-class input to agent decision making while
measurement, scoring, and enforcement remain outside the model. We instantiate
the idea in ToolRoute, a controlled routing benchmark with two functionally
equivalent tools and seeded changes in observed latency and reliability. Across
216 frozen, hash-finalized direct-provider decisions from GPT-5.6 Sol, Claude
Sonnet 5, and Gemini 3.7 Flash, truthful tool-health state reduced mean
observable policy regret by 96.9% relative to a neutral same-shape telemetry
control (4,252 ms to 131 ms) and increased operational completion from 69.4%
to 95.8%. The effect appears in all three model families. These findings
establish a foundational systems principle: operational observability can be
an active control input, not merely an artifact for human dashboards and
post-hoc debugging. A trust-separated harness can transform selected
operational facts into decision-ready state, enabling an agent to condition its
next strategic action on current execution state.

## 1. From operational blindness to active control

An agent can reason carefully about user intent and tool semantics yet still
make a poor operational choice. The reason is often not a failure to understand
the task. It is that the agent sees a menu of tools but not the current state
of the execution harness: which route is slow, failing, stale, rate-limited,
resource-constrained, or no longer economical. To the agent, equivalent APIs
remain equivalent even when the host already knows that one is degraded.

We call this gap **operational blindness**. Our proposal is **Agent Harness
Awareness**: an agent-facing interface that turns verified execution telemetry
from a passive observability artifact into an active control input. The
interface is intentionally minimal and trust-separated: the host measures raw
state, reduces it to a bounded and freshness-labelled snapshot, and retains
enforcement authority outside the model. The model may use that state to choose
a different high-level action; it cannot edit the measurement, the scheduler,
the oracle, or the underlying constraints.

This paper makes two linked contributions. First, it articulates Harness
Awareness as a general systems design principle: agents should reason not only
over task semantics but also over verified operational state. Second, it
provides a rigorous multi-model empirical validation in the tools dimension:
in ToolRoute, verified tool-health state reduces observable policy regret by
96.9% and raises operational completion from 69.4% to 95.8% across three
provider/model families. The result does not depend on a model ranking or a new
tool-call mechanism; it arises from supplying the correct operational facts
before the decision.

## 2. Agent Harness Awareness

### 2.1 Trust-separated state interface

At a decision time $t$, let $x_t$ be the task and tool interface, $h_t$ the
host's operational state, and $z_t = \phi(h_t)$ a compact snapshot emitted by
the harness. Agent Harness Awareness asks whether a policy using $(x_t,z_t)$
chooses a lower-loss operational action than a policy using $x_t$ alone or an
otherwise identical neutral interface. ToolRoute shows why this projection
matters: when $z_t$ carries truthful route-relevant monitor facts, agents
select actions with substantially lower observable cost than under task-only or
neutral same-shape information. A selected, verifiable projection can therefore
be a high-leverage operational input without moving measurement or enforcement
authority into the model.

The intended contract spans four state families:

1. **Tools:** recent success, latency, error state, retry-after, and circuit state.
2. **Runtime:** deadlines, wall-clock headroom, exit state, and execution policy.
3. **Hardware:** memory, CPU, disk, process, and accelerator state.
4. **Economics:** context headroom, token burn, quota, rate limits, and cost.

ToolRoute empirically evaluates the first family, **Tools**. The remaining
families are next empirical instantiations of the four-dimensional state
contract, not pooled evidence in this paper.

### 2.2 Split planes: deterministic recovery and agent adaptation

Harness Awareness complements deterministic systems controls. The data plane
(kernel, proxy, circuit breaker, retry policy, scheduler) should continue to
own fast local enforcement and recovery. The agent control plane becomes useful
when current state changes the *strategy*: choose a different tool, defer an
operation, select a degraded-mode plan, or allocate remaining time and budget
differently. ToolRoute isolates this fundamental strategic boundary--routing
between functionally equivalent endpoints under dynamic degradation--while
preserving deterministic enforcement in the data plane.

## 3. ToolRoute: a controlled information ablation

### 3.1 Task and conditions

ToolRoute presents a single task, two functionally equivalent tools
(`tool_alpha`, `tool_beta`), and a `wait` option. A seeded synthetic
host-owned monitor probes each tool three times and records a monitor-window
success count, latency EWMA, circuit/error state, and snapshot age. The tool
schedule creates changes in those observed facts. The model receives one
independent, full-checkpoint prompt per decision; it has no filesystem, shell,
network tool, schedule, oracle, or artifact access.

We isolate the agent-facing state channel with three conditions:

| Condition | Model-visible information |
| --- | --- |
| A: task only | Task and equivalent tool descriptions; no operational projection. |
| B: neutral envelope | The same telemetry-shaped envelope, fields, row order, and tool rows as C, but equal neutral values for the two tools. |
| C: verified state | The same envelope with fresh host-owned monitor facts for the current tool state. |

Condition B is the critical structural control: holding the envelope, fields,
ordering, and tool rows fixed while neutralizing route-relevant values isolates
the contribution of operational state from the presence and shape of the
interface. It is not an exact provider-token-matching control; the paper
retains provider input-token counts descriptively but makes no token-equality
claim.

### 3.2 External evaluation and auditability

The primary outcome is **observable policy regret**: the excess cost of the
selected action under an oracle restricted to the canonical monitor facts
rendered in C. This avoids scoring C against latent reliability that the model
could not have observed. Successful operational outcome is a secondary,
binary evaluation of the selected action. The latent-state oracle is retained
only as a diagnostic, never as the primary score.

Every provider attempt reserved an artifact directory before invocation and
preserved its prompt, sanitized request and response record, monitor snapshot,
tool event, evaluator result, stdout/stderr, and finalization hashes. The
cohort contains 3 model families x 6 seeds x 4 turns x 3 conditions = 216
independent direct-provider decisions. All 216 records completed and finalized
with valid artifact hashes; no request was retried. Execution order was
deterministically randomized from the frozen manifest.

The provider cohort uses a calibrated synthetic monitor with zero delivery
delay. This makes the state channel controllable and exactly scoreable. It is
not presented as a live production telemetry deployment.

### 3.3 Analysis

The predeclared empirical centerpiece is B-to-C: neutral versus truthful
operational state in the same interface. We report all decisions in the
denominator, Wilson intervals for completion, and raw as well as normalized
regret. To make model-scale differences visually secondary, the main regret
figure normalizes each model family's B mean to 100%; the appendix reports raw
milliseconds. This is a within-model treatment display, not a cross-provider
ranking. Independent provider generations remain independent; a descriptive
bootstrap over the 18 model-by-seed environment blocks summarizes variation
without pretending that providers share a sampling seed.

## 4. Results

Truthful operational state changes the next action substantially. Across all
72 decisions per condition, C reduces mean observable policy regret from
4,251.54 ms in B to 131.12 ms--a 4,120.42 ms reduction (96.9%). Completion
rises from 50/72 (69.4%; Wilson 95% CI 58.0-79.0%) to 69/72 (95.8%; 95% CI
88.3-98.5%), a 26.4-point increase. Condition A is also materially worse than
C (4,826.45 ms regret; 47/72, 65.3% completion), showing that the benefit is
not merely a neutral telemetry envelope.

![Within-model normalized policy regret](figures/figure_1_relative_regret.pdf)

*Figure 1. Mean observable policy regret normalized within each model family
to B = 100%. C remains sharply lower for GPT-5.6 Sol, Claude Sonnet 5, and
Gemini 3.7 Flash. Raw milliseconds are shown in Appendix Figure A1.*

| Model | A regret (ms) | B regret (ms) | C regret (ms) | C completion |
| --- | ---: | ---: | ---: | ---: |
| GPT-5.6 Sol | 4,723.81 | 3,307.00 | 75.50 | 23/24 (95.8%) |
| Claude Sonnet 5 | 5,031.72 | 4,723.81 | 75.50 | 23/24 (95.8%) |
| Gemini 3.7 Flash | 4,723.81 | 4,723.81 | 242.35 | 23/24 (95.8%) |

The cross-family repetition matters. The result is not carried by a single
provider: C produces a low-regret route in every family, while A and B retain
substantial avoidable cost. The three C choices of `wait` are retained in the
denominator; they are not filtered away to improve the apparent result.

![Operational completion](figures/figure_2_completion.pdf)

*Figure 2. Operational completion by condition and model family, with Wilson
intervals reported in the panels. The verified-state condition completes 23 of
24 decisions for each model family.*

### 4.1 What the result establishes

ToolRoute provides strong empirical evidence that verified, current tool-health
state is a consequential control input for an agent's operational route
selection. The B-to-C controlled information ablation holds the
telemetry-shaped interface fixed while changing route-relevant values. The
result therefore shows that model choices are strongly sensitive to structured
operational facts, rather than only to the presence of a table-shaped prompt.

At the architectural level, this shows how passive observability can become a
control input. The host owns truth, reduction, and enforcement; the agent uses
a bounded representation to adapt its plan. That division gives systems
builders a concrete route to integrate agent reasoning with operational state
without granting the model authority over the measurement or safety layer.

## 5. Scope and research agenda

The experiment deliberately isolates one decision type: two-route selection
under a synthetic, immediately delivered tool-health monitor. Larger tool
catalogs, noisy or delayed monitors, stateful multi-turn histories, changing
task semantics, and live service integration are important next tests. Those
tests strengthen the deployment case; they are not required to interpret the
controlled information result reported here.

The same interface suggests several direct extensions. Runtime state can guide
deadline-aware planning; hardware signals can enable memory or concurrency
adaptation; economic state can inform context, quota, and cost-aware
orchestration; and multi-agent systems can expose backpressure and shared
capacity. These are instances of the same question: whether a verified
projection of the harness makes an agent's next strategic action more
operationally appropriate.

The closest adjacent direction, Agent-Native Telemetry, develops compact and
verifiable telemetry evidence and agent access paths for autonomous operations.
Its evaluation emphasizes representation, transport, query/context efficiency,
and integrity. ToolRoute is complementary: it evaluates the downstream
behavioral question using a neutral same-shape control. The work should be read
alongside, not against, emerging telemetry and observability systems.

## 6. Related work

ReAct established the importance of interleaving reasoning with environment
actions, while Toolformer studied learned tool use. AgentBench and tau-bench
show that agents can fail in evolving, stateful environments. ToolRoute focuses
on a different missing observation: the verified operational state of the
execution harness at the instant of route choice. OpenTelemetry provides an
established foundation for traces, metrics, and logs; Harness Awareness extends
selected, provenance-preserving telemetry toward an agent decision interface,
closing the loop between verified operational state and strategic action.

## 7. Conclusion

Agent Harness Awareness closes a loop that current tool-using agents often
leave open: the harness observes operational state, but the agent chooses as if
that state did not exist. In a frozen 216-decision ToolRoute cohort, supplying
truthful tool-health state reduced observable policy regret by 96.9% against a
neutral same-shape control and increased completion by 26.4 points. Taken
together, these results advance a transition from passive observability to
closed-loop agent control: agents can reason over verified execution telemetry,
while the harness retains authority to measure and enforce it.

## Appendix A. Raw policy regret

![Raw observable policy regret](figures/appendix_figure_a1_raw_regret.pdf)

*Figure A1. Raw mean observable policy regret in milliseconds. These are the
unnormalized values behind Figure 1.*

## References

- Yao et al. *ReAct: Synergizing Reasoning and Acting in Language Models*.
  ICLR 2023. https://arxiv.org/abs/2210.03629
- Schick et al. *Toolformer: Language Models Can Teach Themselves to Use
  Tools*. NeurIPS 2023. https://arxiv.org/abs/2302.04761
- Liu et al. *AgentBench: Evaluating LLMs as Agents*. ICLR 2024.
  https://arxiv.org/abs/2308.03688
- Yao et al. *tau-bench: A Benchmark for Tool-Agent-User Interaction in
  Real-World Domains*. ICLR 2025. https://arxiv.org/abs/2406.12045
- OpenTelemetry. *Specification*. https://opentelemetry.io/docs/specs/
- He and Yu. *Agent-Native Telemetry: Verifiable State-Delta Evidence for
  Autonomous Operations*. 2026. https://arxiv.org/abs/2608.16178
