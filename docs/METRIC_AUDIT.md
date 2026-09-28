# Metric and aggregation audit

## Source of metric rules

The primary implementation is `ProfileSupport.java`, with process/resource
measurement and record serialization in `PaceBench.java`. Python aggregation
is in `experiments/scripts/collect_results.py`, `summarize_results.py`, and the
final-publication audit scripts. Raw final result trees are referenced by
provenance but are not copied into this package.

## Profile-level quantities

For an envelope domain of total positive-duration measure `|I|`, the Java
output code accumulates positive-duration found cells as `F` and integrates
the selected score and travel time over those found cells. It emits:

- `feasible_coverage_fraction = F / |I|` (with a zero-domain special case);
- `infeasible_interval_measure = max(0, |I|-F)`;
- `average_selected_score = integral(score over found cells) / F`;
- `average_selected_travel_time = integral(travel time over found cells) / F`;
- `distinct_selected_paths`, path changes, cell count, and a deterministic
  profile checksum.

The average score and travel-time fields are therefore resolved-window
averages. They are not full-window averages when unresolved/NO_PATH duration
exists. A full-window zero-filled score can be computed as
`integral(score over found cells) / |I|`; the frozen T03 audit records that
post-processing convention separately. The two values must not share one
label.

Singleton cells have zero positive duration and do not contribute to these
integrals, although they remain in the profile and affect endpoint/path
assignment and checksum comparisons.

## Reference quality and relative gap

`ProfileSupport.quality` unions candidate/reference breakpoints and evaluates
open interval interiors. It computes path agreement by duration, feasibility
disagreement by duration, score regret relative to the reference score, score
agreement, breakpoint precision/recall, and travel-time gaps on score ties.
The relative score gap is an integrated reference-weighted score regret divided
by the integrated reference score, with a `max(referenceScore, 1)` factor per
positive-duration sample. When the denominator is zero, the implementation
returns zero for `integrated_score_regret` and `relative_score_gap_percent`.
This is not the same as averaging pointwise relative errors.

The exact full-window gap used by a reporting script may instead zero-fill
unresolved candidate portions and compare against a full-window reference.
Each result table must cite which formula it used. Stored raw audits do not
provide complete raw fields for every historical study, so some printed score
gaps remain only partially verified.

## Timing and resource metrics

`PaceBench` separately records preprocessing, query total, algorithm phase
timings, reference time, serialization, CPU, heap, and process RSS fields.
Peak RSS is process-level and includes graph/runtime overhead; it is not
algorithm-only memory consumption. The metric audit must not subtract graph
load or infer algorithm-specific memory from process RSS unless the report
explicitly says so.

The iSCOPE source records its deadline-controlled algorithm total while it
profiles/envelopes paths during search. Historical reports describing iSCOPE
as search-only therefore need a raw timing boundary or author confirmation.
PACE-B's reported query time includes the PACE pipeline represented by its
`query_total`/algorithm timing record, subject to the exact runner/config.

## Trials, logical queries, and filtering

The final T03 provenance identifies three measured process-level trials for
each logical query, with warm-up rows excluded from measured slices. The
correct aggregation order is:

1. exclude warm-up rows and classify terminal statuses;
2. group repeated rows by logical `query_id` and trial;
3. require the declared number of valid measured trials for a complete logical
   query, while retaining incomplete/failure counts;
4. aggregate the three trial runtime observations to one logical-query value
   (the stored final audits use the median); and
5. summarize logical-query values across the workload (again using median for
   the central runtime value, with coverage/completion reported separately).

The sensitivity audit says incomplete logical queries are excluded from
runtime medians but remain in completion statistics. A different source file
may use a different filter; the result provenance must bind every summary to
its aggregation script and raw rows.

## Figure 3 error bars

The revised Figure 3 audit specifies median plus/minus half-IQR. The IQR is
calculated across logical-query runtime observations after three-trial
aggregation. This is not a standard error and should not be labelled as one.
The stored revised audit recomputes Q1/Q3 from logical-query medians. The
original plotting path and manuscript are unavailable in this package, so the
claim is **PARTIALLY_VERIFIED** until the author supplies the exact manuscript
and plotting source binding.

## Historical inconsistencies found

- The final controlled raw-study audit reports median score gaps approximately
  39.25%, 64.89%, and 75.55% for B=5, 10, 15 under its paired recomputation,
  while current manuscript values are reported as 36.9%, 62.8%, and 72.3% in
  the supplied audit. These are verification findings, not replacement values.
- The successive-policy raw audit recomputes 39.25% for the two fast-connector
  stages, while the supplied stage target is 36.9%.
- The stored large-network final publication CSV reports a PACE-B FLA runtime
  that differs from the revised raw-data audit's completed-query behavior; the
  revised audit identifies incomplete FLA queries and medians above five
  seconds. The artifact does not rewrite the CSV.
- Window sensitivity source metadata records rho=0.10 for 240/360 minutes;
  the author has identified that as a reporting-metadata error. Raw metadata
  remains authoritative evidence of what is stored; the correction belongs in
  a separate provenance note.

## Metric status

The implementation formulas are verified at source level. Historical
reproduction of all paper values is only partial because the manuscript,
historical commit, and complete raw result bindings are missing. No metric was
changed to force agreement with manuscript targets.
