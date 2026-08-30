# ToolRoute Manuscript Narrative Contract

**Purpose:** prevent a correction cycle during drafting. This document fixes
the paper's strongest fact-grounded position before prose, figures, or an
abstract are written.

## One-sentence thesis

**Agent Harness Awareness turns verified execution telemetry from a passive
observability artifact into an active control input for tool-using agents.**

## Claim ladder

| Level | Claim | Evidence status |
| --- | --- | --- |
| Paradigm | Agents should reason over verified operational state, not task semantics alone. | Design thesis, motivated by the architecture and empirical instance. |
| Architecture | A trust-separated harness can reduce raw observations into fresh, bounded SST for agent decisions while retaining enforcement outside the model. | Implemented in this repository; ToolRoute exercises the tool-state dimension. |
| Empirical | Truthful tool-health state substantially improves ToolRoute action quality over task-only and neutral same-shape controls. | Directly measured in the frozen 216-decision cohort. |
| Systems implication | Harness state belongs on the agent control plane, complementing deterministic middleware on the data plane. | Architectural implication; ToolRoute demonstrates route selection, not all macro-adaptations. |
| Research program | Resource, deadline, economic, and multi-agent state can be evaluated through the same interface. | Planned extensions, not pooled evidence. |

## Required narrative moves

1. Lead with **operational blindness**, not a generic “LLM agents are
   unreliable” introduction.
2. State the positive idea early: observability becomes control input.
3. Explain the split plane before a reviewer asks why middleware cannot route
   the two ToolRoute endpoints itself.
4. Make the B→C contrast the main result. It is the cleanest evidence that
   route-relevant state, rather than telemetry-shaped formatting, changes the
   decision.
5. Show all model-family results and all three retained C `wait` outcomes.
6. Present future use cases as direct consequences of the interface, not as
   measured deployment savings or production incident reductions.

## Recommended manuscript structure

1. **Introduction — operational blindness to active control.** Define the
   problem, introduce Harness Awareness as the dynamic extension of Substrate
   Awareness, and state the contributions.
2. **Harness Awareness architecture.** Describe the freshness-labelled SST,
   trust-separated ownership, intended four-dimensional contract, and split
   plane between deterministic enforcement and agent control.
3. **ToolRoute — controlled information ablation.** Describe the seeded,
   host-owned monitor; functionally equivalent routes; A/B/C conditions;
   independent direct-provider decisions; externally owned observable-cost
   oracle; randomization; and hash-finalized preservation.
4. **Results.** Lead with the B-to-C result, then show all model-family rows,
   completion outcomes, and retained `wait` selections.
5. **Interpretation, boundaries, and research agenda.** State the synthetic,
   two-route, zero-delivery-delay boundary directly, then develop scaling,
   hardware/runtime/economic state, and multi-agent coordination as the next
   instances of the same interface.
6. **Related work.** Position the work against tool-use agents, interactive
   agent benchmarks, and observability systems without claiming that no prior
   agent has consumed state. Discuss Agent-Native Telemetry as the closest
   compact, verified telemetry architecture and distinguish ToolRoute's
   controlled behavioral information-ablation question from its systems
   transport, integrity, and context-efficiency evaluation. Do not call the two
   papers orthogonal, claim exclusivity over agent-consumable telemetry, or
   describe the present benchmark result as universal causal proof.

The evaluation must have its own method section before results. The architecture
is general; the frozen evidence is the ToolRoute tools-dimension instance.

## Evidence language

Use:

- “In the frozen ToolRoute cohort, verified tool-health state reduced mean
  observable policy regret by 96.9% relative to the neutral same-shape control.”
- “The effect reproduced across three provider/model families.”
- “The result supports Harness Awareness as an operational decision interface.”
- “ToolRoute is a controlled information ablation of the agent-facing
  operational-state channel.”
- “The implementation uses a trust-separated harness interface: the host owns
  measurement, reduction, and enforcement; the model may consume but cannot
  rewrite state.”
- “ToolRoute demonstrates operative routing; the same contract is designed to
  extend to resource, runtime, and economic state.”

Do not use:

- “proves frontier models possess latent systems reasoning”;
- “formally proves the causal signal is 7.17× larger than formatting”;
- “solves the POMDP,” “near-minimal sufficient statistic,” or
  “information-bottleneck optimal”; 
- “replaces middleware,” “prevents outages,” “saves $X,” or “production-ready
  standard”; 
- “exact token matched” or “same token geometry.”
- “causal ablation” without qualifying the precise randomized information
  intervention and its benchmark boundary; use “controlled information
  ablation” instead.
- “zero-trust L0/L2” unless a distinct, implemented security model with those
  levels is formally specified and evaluated; use “trust-separated harness
  interface.”

## Non-negotiable factual qualifiers

- ToolRoute is a **synthetic host-owned monitor** with zero delivery delay in
  the provider cohort, not a live production telemetry deployment.
- B matches C's telemetry-shaped envelope, fields, ordering, and tool rows; it
  is not exact provider-token matched. Input-token usage is descriptive.
- Model decisions are independent provider generations. Treat condition results
  with the frozen independent-sample analysis plan.
- The provider cohort evaluates the tools dimension. Hardware, runtime, and
  economics are architectural dimensions and future empirical scenarios.
- Gemini used explicit `temperature: 0.0`; this setting is documented and
  stable across all its cohort decisions.

## Draft review gate

Before accepting any section, ask:

1. Does the paragraph advance the operational-blindness → control-input story?
2. Is every quantitative statement traceable to a retained cohort artifact?
3. Does it distinguish evidence, architectural implication, and research
   program without weakening the thesis?
4. Would a middleware, token-control, staleness, or synthetic-benchmark
   reviewer find their strongest question answered directly?
5. Does it make the reader more confident that Harness Awareness is a useful
   general design direction?
