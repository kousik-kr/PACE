# PACE revised figures v3

Six vector PDFs and matching 600-dpi PNGs, derived from frozen data inside the
parent `q1_figures_v2` directory.

- [Visual gallery](review/index.html)
- [Revision report and captions](review/FIGURE_REVISION_REPORT.md)
- [New successive-policy trade-off](figures/fig04_successive_policy_tradeoff_v3.pdf)
- [Source provenance](provenance/figure_sources.csv)
- [Current file hashes](provenance/figure_hashes.csv)
- [Validation results](review/validation_results.json)

From this directory:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build_package.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_package.py --render-previews
```

The runtime ECDF, NYC revision, and runtime-versus-budget-bucket revision require
inputs absent from this permitted package. Coverage/completion and score
definitions that cannot be resolved locally are identified in the report.

No experiments were rerun. Figure derived exclusively from frozen data under q1_figures_v2.
