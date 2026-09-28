# Score metric audit

## Raw fields and observed aggregation

The T03 result records expose `output.average_selected_score` and
`output.feasible_coverage_fraction`. The local extraction logic in
`Final-result/pace_existing_data_extract.py` constructs the publication-level
zero-unreported score as:

`score_zero_unreported = average_selected_score * clamp(feasible_coverage_fraction, 0, 1)`

Missing selected scores and unresolved coverage therefore contribute zero. The
raw summaries distinguish this field from `avg_score_reported_resolved_only`.
The recomputed Figure 5 absolute score medians are:

| Dataset | PACE-B zero-unreported score | iSCOPE zero-unreported score | iSCOPE / PACE-B |
|---|---:|---:|---:|
| NY | 376.8917 | 295.4968 | 78.4036% |
| FLA | 222.2292 | 173.8963 | 78.2509% |
| CAL | 306.6167 | 82.6259 | 26.9476% |

These ratios are workload-level normalized scores, not approximation ratios.

## Independent cell-duration check

The T03 JSONL records contain aggregate output values and envelope-cell counts,
but no serialized per-cell score durations or profile interval table. Therefore
an independent exact-duration recomputation from temporal cells cannot be
performed from the raw Final-result snapshot. No temporal sampling or new score
definition was introduced.

## Exact and policy score comparisons

The final NY exact/policy records expose paired `average_selected_score` values
and profile checksums but do not serialize `relative_score_gap_percent` or
`path_agreement_fraction`. The audit recomputes the relative score gap per
paired logical query and marks checksum equality as a clearly identified path
agreement proxy. This is why the recomputed exact/policy gap differs from the
current manuscript values.
