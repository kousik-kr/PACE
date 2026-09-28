# Phase-A raw-data audit

Date: 2026-09-11

## Status

Phase A is complete. Phase B is **stopped before figure regeneration** because
the requested principal large-network protocol is not supported by the raw
results: at window 120 min and rho=0.30, all 196 fully completed FLA logical
queries have completed-query median runtimes above 5 s, and the other four FLA
logical queries contain timeout trials. The raw evidence must not be forced into
the requested publication claim.

The raw result tree contains 138,368 files. No file under
`experiments/results/Final-result` was modified.

## Principal large-network runtime audit

| Dataset | Logical queries | Fully completed logical queries | Incomplete logical queries | Completed-query median (s) | Minimum (s) | Maximum (s) | Completed logical queries >=5 s | Normal trial rows >=5 s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| NY | 200 | 200 | 0 | 3.285385 | 1.964845 | 4.385594 | 0 | 0 |
| FLA | 200 | 196 | 4 | 8.148790 | 7.253909 | 9.715976 | 196 | 596 |
| CAL | 200 | 200 | 0 | 0.967245 | 0.115449 | 3.006088 | 0 | 0 |

`n_completed` counts a logical query only when all three measured trials have
status `COMPLETED`. Runtime medians are formed from the three measured trial
times per completed logical query and then summarized across logical queries.
The FLA timeout query IDs are recorded in the CSV-producing audit logic and are
not silently discarded from the completion audit.

## Figure 3 — controlled exact reference

Raw source: `manuscript_missing_runs/final_ny_exact/`.
The final exact study does contain 20 logical queries at each requested budget
B=5, 10, and 15 min, with three measured trials per method. The recomputed
PACE-X and PACE-B runtime medians match the current manuscript values to the
reported precision. The runtime error bars are not a named statistic in the raw
study summary; the audit table provides the recomputed Q1/Q3/IQR of logical-query
medians. The raw quality object does not serialize `path_agreement_fraction` or
`relative_score_gap_percent`; this audit uses profile-checksum equality as an
explicit proxy for path agreement and recomputes score gap from paired
`average_selected_score` values.

The recomputed median score gaps are approximately 39.25%, 64.89%, and 75.55%
for B=5, 10, and 15, respectively, when the per-query gap is summarized over
nonzero exact-reference scores. The current manuscript values 36.9%, 62.8%,
and 72.3% therefore do not match the raw final exact study.

## Figure 4 — successive policy

Raw source: `manuscript_missing_runs/final_ny_policy/`, paired to the B=5
PACE-X records in `final_ny_exact/`. The four requested stages are present and
all 20 logical queries complete across three measured trials. Runtime medians
recompute as 0.07320, 0.04255, 0.02804, and 0.02694 s. The checksum-agreement
proxy has medians 100%, 100%, 0%, and 0%. The recomputed median score gaps are
0%, 0%, 39.25%, and 39.25%, so the currently printed 36.9% gap is not supported
by this raw final exact/policy pairing.

## Figure 5 — large-network comparison

Raw source: the six canonical T03 batches for NY, FLA, and CAL. Each requested
setting has 200 logical query IDs and three measured trials. iSCOPE rows carry
status `TIME_CAPPED_NOT_CERTIFIED` under its configured 5 s cutoff. The only
5 s interpretation supported by the raw configuration is the iSCOPE cutoff;
PACE-B was executed with a 10 s internal limit in these T03 batches.

The PACE-B audit fails the requested all-below-5-s publication check for FLA.
Consequently, no Figure 5 replacement was generated. The existing figure must
not be relabeled as a common 5 s protocol or retain a PACE-B 10 s boundary.

## Figure 6 — travel-time budget distribution

Raw source: the T03 `queries.jsonl` manifests. The requested filter yields 200
unique query budgets per network. The recomputed inclusive five-number summaries
are stored in `plot_data/fig6_budget_distribution.csv`; they agree with the
current budget-distribution values.

## Figure 7 — algorithmic sensitivity

The L/Kf rows are supported by the NY-EXACT aggregate summary generated from
the raw E14 records. The theta rows are supported by the fasttrack parameter
records, with failed/no-feasible logical queries excluded from the runtime
median and counted in completion. The source families are not one fully crossed
experiment: L/Kf use the E14 parameter grid, while theta uses the fasttrack
L=1 configuration. All per-setting counts and completed-query runtime medians
are in `SENSITIVITY_RUNTIME_AUDIT.csv`.

## Figure 8 — workload sensitivity

The NY T03 raw records support window 120/240/360 min and rho 0.10/0.30/0.50,
with runtime medians computed over fully completed logical queries only. The
current workload CSV labels all window points as rho=0.30, but its 240- and
360-minute runtime values correspond to rho=0.10 in the raw source. The raw
rho=0.30 values are 3.2854, 3.3475, and 3.4945 s for windows 120, 240, and
360 min. Density records at approximately 5% and 40% are also present, with no
comparable score values.

## Query counts, filtering, and aggregation

- Repeated process trials were grouped by `query.query_id`; they were not
  counted as separate logical queries.
- Warmup records were excluded before all measured-runtime calculations.
- Sensitivity runtime medians exclude logical queries without three normal
  measured completions; failures and incomplete records are counted separately.
- T03 score audit values use `output.average_selected_score` multiplied by
  `output.feasible_coverage_fraction`, treating missing/unresolved score as zero.
- Figure 5(c) normalization is 100 times the iSCOPE zero-unreported workload
  score divided by the corresponding PACE-B score. It is not an approximation
  ratio.

## Required next decision

Before Phase B can be authorized, reconcile the manuscript's principal FLA
protocol with the raw T03 result: either supply a valid below-5-s PACE-B result
set for the stated comparison or revise the protocol/claim and captions. No
figure was regenerated after this discrepancy was found.
