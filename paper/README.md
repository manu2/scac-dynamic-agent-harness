# ToolRoute manuscript artifacts

This directory holds the ToolRoute manuscript source, the reproducible frozen
v1.0 analysis, and the separately labelled OTel/Toxiproxy transport-replication
figures. It is not an arXiv source package yet.

Install the sole figure dependency, then regenerate all derived tables and PDFs
from the repository root:

```bash
python -m pip install -r paper/requirements.txt
```

```bash
/Users/manuagrawal/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  scripts/analyze_toolroute_v1_paper.py
```

The script reads only the three retained paper-cohort roots declared in its
source, validates the exact 216-cell grid, and writes derived output under
`paper/analysis/` and `paper/figures/`. It makes no provider calls and never
rewrites `experiments/`.

The versioned manuscript source is
`paper/toolroute_draft_transport_replication_v0.2.md`. Its primary figure shows
all A/B/C condition means on a logarithmic regret scale, while the second figure
shows the complete 27-decision live transport replication. Generate these
figures with:

```bash
/Users/manuagrawal/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  scripts/generate_toolroute_transport_draft_figures.py
```

Regenerate the hash-validated transport summary used by the replication figure
with:

```bash
/Users/manuagrawal/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  scripts/analyze_toolroute_otel_transport_v0_2.py
```

## Submission-ready PDF

The polished submission-ready proof is written to
`output/pdf/agent_harness_awareness_toolroute.pdf` by:

```bash
/Users/manuagrawal/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  scripts/build_toolroute_submission_pdf.py
```

The builder embeds the audited figures. It uses macOS `sips` only to rasterize
Figure 1; the approved 2400-pixel Figure 2 PNG is embedded directly, without a
second rasterization step. The output identifies Manu Agrawal as first author and
Shrey Nagpal as second author. It remains a formatted submission proof rather
than an arXiv source package: affiliations, verified BibTeX, and final release
metadata remain to be added.
