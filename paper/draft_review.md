# ToolRoute Draft Review Gate

**Status:** sample manuscript ready for research review, not yet an arXiv
submission package. The 2026-08-31 tone review was incorporated: the paper now
states the architectural thesis and exact empirical result more directly while
avoiding unverified priority, mechanism-of-reasoning, token-overhead, and
production-resilience claims. A subsequent line-level review replaced
minimizing language with intentional architectural wording while retaining the
non-token-matching control statement and the tools-only empirical boundary.
The formatted proof identifies Manu Agrawal as first author and Shrey Nagpal as
second author.

## What was adopted from the earlier Substrate Awareness paper

- Start from a named systems failure: **operational blindness**, not generic
  agent unreliability.
- Lead the abstract and results with one concrete, traceable measured effect.
- Show the principal result as a within-model treatment contrast, not a model
  leaderboard. Figure 1 reports B-to-C regret reduction independently for each
  model family.
- Preserve the corresponding raw values. Figure A1 and the derived CSVs make
  the normalization fully inspectable.
- Move the wider research program after the empirical instance: ToolRoute
  supports the dynamic tools dimension; it motivates the broader architecture.

## What was intentionally not copied

- The current evidence is not a resource-limit execution study, so the draft
  does not borrow RAM/timeout framing or raw cross-model scaling claims.
- The manuscript does not call B and C exact token matched. They are a
  same-shape structural control with equal versus route-relevant values.
- It does not claim a provider ranking, production deployment result, or that
  LLM control replaces proxies, circuit breakers, or schedulers.
- It does not turn independent provider generations into shared-seed paired
  observations. The analysis labels the 18 model-by-seed bootstrap correctly.

## Scientific self-review

| Review question | Finding |
| --- | --- |
| Is the central claim directly supported? | Yes. C has 131.12 ms mean observable regret versus B's 4,251.54 ms and 95.8% versus 69.4% completion. The effect reproduces in all three model families. |
| Can a table-format effect explain B-to-C? | The design directly addresses this: B and C retain the same telemetry envelope, fields, tool rows, and order; only route-relevant values differ. It is strong evidence for useful state, though not an exact token-count claim. |
| Is the primary score fair to C? | Yes. The primary oracle uses observable canonical monitor facts exposed to C, rather than latent reliability. |
| Are results auditable? | Yes. The analysis reads only the three frozen cohort roots, validates all 216 expected cells, and re-hashes every finalized JSON artifact before deriving values. |
| Is the writing too defensive? | No. The draft has one direct scope section, then uses the result to argue positively for Harness Awareness as a control-plane design direction. |
| Is the writing too broad? | No empirical claim extends beyond route selection in the synthetic monitor. The broad architecture is explicitly a design thesis and research program. |

## Before arXiv upload

1. Convert this review draft to the chosen LaTeX template and replace Markdown
   references with verified BibTeX records.
2. Add author names, affiliations, acknowledgements, code-release URL, and the
   immutable commit SHA/artifact archive DOI.
3. Add the Substrate Awareness citation once its preprint is public; until then,
   describe the relationship in prose without a non-public bibliography entry.
4. Perform one independent text-and-figure review against
   `paper/analysis/toolroute_v1_analysis.json`, then freeze the submission
   commit and archive the exact cohort and generated outputs.
