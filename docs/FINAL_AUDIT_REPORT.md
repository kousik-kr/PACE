# Final audit report

## A. Repository audit

Inspected Git state/history, Maven build metadata, all Java production/test
packages, PACE-X/PACE-B/iSCOPE entry points, temporal functions, graph/loader
and query-generation code, experiment configs/manifests, plotting/reporting
scripts, frozen final-publication evidence, oracle evidence, metrics, and the
NYC case-study workflow. The artifact retains complete Java source/tests,
selected experiment support/configuration, small evidence/plot data, supplied
figures/tables, and provenance. It excludes large/third-party input data,
virtual environments, compiled output, and bulk raw result trees. No
historical source revision is recoverable: the repository has no Git commits.

## B. Scientific consistency

Verified: temporal representation, stable IDs, endpoint-aware continuous
profiles, active path ranking comparator, structural validation, explicit
completion/cap guards, deterministic envelope processing, and the independent
micro-instance oracle evidence.

Partially verified: FIFO/general model distinction, query-region safety,
historical configurations, dataset identity/counts, controlled completion,
metrics/aggregation, and NYC provenance.

Contradicted: active EA/LD versus static corridor description, integrated-score
versus maximum-score pivot ranking, uniform PACE-B connector semantics,
full-I replay wording, unresolved `U` versus `NO_PATH` semantics, heuristic
retention as exact dominance, resolved-window versus full-window score, and
the unqualified common five-second large-network protocol. See the matrix for
claim-level detail.

## C. Reproducibility

Reproducible in a clean workspace: Maven compilation, Java regression tests,
the synthetic CLI, and independent oracle tests. Re-generable from supplied
data only: selected publication plot/table workflows and figure audit outputs.
Requires unavailable/excluded inputs: controlled and large-network routing,
complete raw-result regeneration, and NYC processing. Significant resources:
all Level 3 network studies, especially 24-worker large-network runs and NYC
data preparation.

## D. Validation

The original repository Maven suite completed successfully with `mvn -q test`. The isolated artifact ran all 243 Java tests with 0 failures and 0 errors, `scripts/validation/artifact_integrity.py` passed, `scripts/validation/smoke.sh` passed, and `scripts/validation/oracle.sh` passed. The independent oracle evidence reports 1,009 passing full-profile micro-instance comparisons. No full historical campaign was run. Submission-critical scientific mismatches and
missing evidence remain failures, not suppressed warnings.

## E. Publication artifact

The deliverable is the `paper_artifact/` directory. Reviewers can run:

```bash
cd paper_artifact
./scripts/validation/smoke.sh
```

The complete inventory is in `ARTIFACT_MANIFEST.json`; provenance and checksums
are under `provenance/`.

## F. Submission blockers

1. Provide the authoritative corrected manuscript and version.
2. Provide the historical source commit and raw run/config bindings.
3. Reconcile code/paper semantics listed in `KNOWN_LIMITATIONS.md`.
4. Reconcile the five-second baseline protocol and FLA raw results.
5. Reconcile controlled/policy score-gap target values.
6. Confirm data redistribution rights, authorship metadata, and a public
   license.

## G. Release readiness

`BLOCKED_BY_SCIENTIFIC_MISMATCH`
