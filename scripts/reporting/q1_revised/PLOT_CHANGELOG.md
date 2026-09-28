# Phase-A plot changelog

No publication figure was regenerated in this run. The mandatory FLA runtime
check failed before Phase B, so the current v3 PDFs/PNGs remain untouched.

| Requested figure | Phase-A result | Required publication action |
|---|---|---|
| Figure 3 | Raw final exact study supports B=5/10/15 and runtime medians; score gaps differ from current manuscript values | Recompute from `plot_data/fig3_controlled.csv` only after the manuscript discrepancy is accepted |
| Figure 4 | Four cumulative policy stages are present; runtime and checksum-agreement proxy reproduce the stage pattern; score gap differs | Recompute from `plot_data/fig4_restrictions.csv` only after the discrepancy is accepted |
| Figure 5 | BLOCKED: FLA PACE-B violates the requested all-below-5-s condition; PACE-B raw T03 configuration uses a 10 s internal limit | Do not generate a replacement until protocol/claim is reconciled |
| Figure 6 | Budget manifests support 200 unique queries per network and the current five-number summaries | Safe to regenerate after Figure 5 decision |
| Figure 7 | Sensitivity raw records exist, but L/Kf and theta come from different evaluated configuration families | Use completed-query runtime labels and disclose source-family distinction |
| Figure 8 | Raw T03 supports requested window/rho settings; two current window runtimes are labeled with the wrong rho | Regenerate with raw filters, completed-query medians, and absolute scores |

Explicit cleanup requirements recorded for Phase B:

1. Remove all obsolete 10 s PACE-B boundary wording from publication-facing
   plots/captions/README files.
2. Label the 5 s line as the iSCOPE-Profile cutoff only.
3. Use completed-query-only runtime medians for every sensitivity setting.
4. Preserve unresolved=0 in full-window score aggregation.
5. Report all raw-data discrepancies against the current manuscript instead of
   forcing agreement.
