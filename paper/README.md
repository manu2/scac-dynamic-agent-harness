# ToolRoute manuscript artifacts

This directory holds a review draft for the ToolRoute-only arXiv preprint and
the reproducible analysis built from the frozen v1.0 API cohort. It is not a
submission package yet.

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

The main manuscript figure shows the within-model B-to-C percentage reduction
in regret, making the information treatment visible without encouraging a
provider ranking. Raw A/B/C milliseconds remain in the results table, appendix
figure, and derived CSVs.

## Final-review PDF

The polished final-review proof is written to
`output/pdf/toolroute_arxiv_review_draft.pdf` by:

```bash
/Users/manuagrawal/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  scripts/build_toolroute_final_draft.py
```

The builder embeds the audited figures and uses macOS `sips` only to rasterize
them for ReportLab. The output identifies Manu Agrawal as first author and
Shrey Nagpal as second author. It is a final-review PDF, not yet an arXiv
source package: this workspace has no LaTeX engine, and affiliations, verified
BibTeX, release DOI, and the final submission commit remain to be added.
