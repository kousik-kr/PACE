# Repository audit

Audit date: 2026-09-28

## Scope and source identity

The audited repository is the current `I-PC-Max` working tree. `git status`
reports every project file as untracked and `git log` reports that the `master`
branch has no commits. Consequently there is no recoverable Git commit, tag, or
branch that can be named as the historical source revision for the published
experiments. The best available source identity is the SHA-256 inventory in
`../provenance/SHA256SUMS.txt`, together with the relative paths recorded in
`../provenance/RESULT_PROVENANCE.csv`.

The task specified the latest corrected 25-page manuscript as authoritative. No
`PACE.tex`, manuscript PDF, or other manuscript source is present in the
audited tree. `PACE_CODEBASE_AUDIT_REPORT.md` is a prior secondary audit that
refers to `PACE.tex`; it is evidence about a previously inspected state, not a
substitute for the missing authoritative manuscript. Claims in this package
therefore use the prior audit's cited sections only as provisional locations.

The original working tree was not modified except for ignored build output
created by bounded validation. No source, historical result, manifest, or
publication report was overwritten.

## Build and source map

The project is one Maven module using Java 21. The production entry point in
the shaded JAR is `edu.ipcmax.experiments.PaceBench`; the small interactive
entry point is `edu.ipcmax.experiments.PaceCli`. The active experiment path is:

`PaceBench -> PaceExperimentAlgorithm -> PACE -> ForwardLayeredFrontierGenerator -> EnvelopeExtractor -> ProfileSupport/PaceBench serialization`.

The PACE-X and PACE-B implementation is retained in full under
`src/main/java/edu/ipcmax/core/pcmax/`. The package-level areas are:

| Area | Relevant paths | Role |
| --- | --- | --- |
| Temporal functions/domains | `core/function/` | Continuous piecewise-linear travel functions, piecewise-constant scores, endpoint-aware domains. |
| Graph model | `core/graph/`, `core/loader/` | Directed stable-ID graph and generated-dataset loader. |
| Labeling/indexes | `core/labeling/`, `core/index/` | Point temporal labeling and static lower-bound/index support. |
| PACE | `core/pcmax/` | Corridor, pivots, connectors, layered frontier, replay, envelope, completion, and exactness metadata. |
| Profile/validation | `core/profile/`, `core/validate/` | Candidate profiles, envelope support, path simplicity and output validation. |
| Experiment framework | `experiments/` | Algorithm registry, CLI, query manifests, metrics, process/resource guards. |
| Query generation | `experiments/querygen/` | Base-weight candidate sampling, temporal regimes, budgets, and manifest generation. |
| NYC workflow | `casestudy/nyc/` and `case_studies/nyc_shuttle/` | Separate data-calibrated case-study runner and Python provenance/analysis scripts. |

## Entry points

- Compile/package: `mvn -q package`.
- Synthetic CLI: `java -cp target/classes edu.ipcmax.experiments.PaceCli --demo --algorithm pace-x`.
- Unified experiment driver: `experiments/scripts/run_all.py`.
- Dataset query generation: `edu.ipcmax.experiments.querygen.QuerySetGenerator` and `experiments/scripts/generate_queries.py`.
- Independent continuous oracle: `PaceExactOracleDifferentialTest` and
  `TinyContinuousEnvelopeOracle`.
- Controlled historical studies: `experiments/scripts/run_final_ny_exact_study.py`
  and `run_final_ny_policy_study.py`.
- Reporting/validation: `experiments/scripts/summarize_results.py`,
  `validate_results.py`, and the frozen final-publication scripts.
- NYC data construction: `case_studies/nyc_shuttle/scripts/`, with downloads
  intentionally outside this artifact.

## Configuration and dependencies

`pom.xml` pins Maven plugin versions, Java release 21, Jackson 2.17.2, and
JUnit Jupiter 5.10.2. Experiment configuration is JSON-compatible YAML under
`experiments/configs/`; study-specific files are under `experiments/configs/studies/`.
Historical query manifests are under `experiments/manifests/queries/` in the
original repository. The artifact includes only the tiny manifest and references
large historical manifests by provenance path and checksum.

The Python experiment/reporting layer declares its dependencies in
`experiments/pyproject.toml`. The NYC adapter has a separate requirements file
in the original tree; it is not installed or executed by the smoke workflow.

## Historical evidence inspected

- `reports/pace_revision/final_publication/` for supplied tables, figures,
  plot data, final-value decisions, and provenance records.
- `reports/pace_revision/oracle_validation/` for the independent oracle audit,
  1,009 differential-case ledger, numerical semantics, and source provenance.
- `reports/pace_revision/final_publication/q1_figures_v2/revised_figures_v3/`
  for the current audited figure package and its raw-data audit.
- `experiments/results/Final-result/` for frozen result records, metadata, and
  the NYC diagnostic outputs. Large raw result trees and embedded environments
  are not copied into the public artifact.
- `experiments/manifests/` and `data/input/*/manifest.json` for query and
  dataset identity. The network files themselves are not redistributed here.
- `case_studies/nyc_shuttle/` for the 14 May 2026 EDT workflow, source
  manifests, mapping/provenance reports, and the supplied displayed profile.

## Retained in this artifact

- Complete production Java source and existing Java tests.
- Maven build metadata and dependency declarations.
- Experiment scripts, plotting/reporting support, schemas, and configurations
  needed to understand or rerun the supported workflows.
- Independent-oracle evidence, small plot data, supplied publication figures,
  tables, query metadata, and checksums.
- NYC scripts, query manifests, source references, and validation reports, but
  not third-party raw inputs or generated road-network binaries.
- Audit documents that distinguish implementation facts, historical evidence,
  and unsupported manuscript claims.

## Excluded from the public package

The following remain in the original repository and were excluded from the
separate package by scope, size, or redistribution risk:

- `data/input/*` graph and temporal-function binaries, except their metadata is
  described in the audit; these are third-party/derived datasets requiring
  provenance and rights review.
- `experiments/results/Final-result/` raw JSONL batches, virtual environments,
  scratch/reconciliation trees, and other bulk frozen outputs.
- NYC `raw/`, `processed/`, and `intermediate/` downloads/binaries, including
  GTFS archives and generated Parquet/CSV/GZIP road data.
- `target/`, Python caches, local virtual environments, compiled JARs/classes,
  and temporary logs.
- Older/unrelated research configurations and data not needed for the PACE
  paper's controlled, large-network, sensitivity, or NYC workflows. They are
  not declared obsolete; they are outside this artifact's publication scope.

## Findings and scientific consequences

| ID | Severity | Finding | Consequence |
| --- | --- | --- | --- |
| R1 | BLOCKER | No authoritative manuscript source/PDF is present. | Paper locations, intended claims, and bibliographic metadata cannot be independently checked. |
| R2 | BLOCKER | No Git commit/history is present. | The historical source revision used for final experiments cannot be established. |
| R3 | CRITICAL | Active corridor uses static all-support minimum travel bounds; prior audit says the manuscript describes EA/LD temporal labeling. | The preservation proof and query-region claim do not describe the executed algorithm. |
| R4 | CRITICAL | Active pivot ranking uses maximum instantaneous score and positive-domain measure, not the prior audit's integrated-score ranking. | Reported pivot semantics and any ranking-based theoretical claim are mismatched. |
| R5 | CRITICAL | Final PACE-B fast-only mode uses a midpoint time-dependent connector; other production branches use a static lower-bound witness/portfolio. | “Single fastest connector” must be qualified; connector policy is not one uniform manuscript rule. |
| R6 | CRITICAL | Bounded cap overflow is fail-closed; uncovered profile cells serialize as `NO_PATH`, with no active `U` symbol. | Unresolved cells can be confused with infeasibility and exactness claims are too strong. |
| R7 | MAJOR | Replay uses the candidate's admitted/root domain rather than automatically replaying every candidate over the complete query interval. | Full-window replay claims require narrowing or new evidence. |
| R8 | MAJOR | `ProfileSupport`'s `average_selected_score` divides by resolved feasible measure. | It is not the manuscript's full-window zero-filled score unless separately recomputed. |
| R9 | MAJOR | Stored T03 evidence has PACE-B 10-second internal limits and FLA completed-query medians above 5 seconds. | The common five-second comparison and Figure 5 claim require author reconciliation. |
| R10 | MAJOR | Historical figure/provenance records include source-specific metadata and some stale/absolute paths. | Independent regeneration and release portability are impaired. |
| R11 | MODERATE | The current tree includes both newer and legacy configurations with different defaults/counts. | Current defaults cannot establish historical settings; configuration provenance must be selected per result. |

## Audit conclusion

The package is technically buildable and contains unusually strong micro-instance
oracle evidence, but it is not submission-ready. The artifact status is
`BLOCKED_BY_SCIENTIFIC_MISMATCH`, with the missing manuscript and historical
source identity recorded as separate blockers. No scientific behavior was
changed to make the implementation agree with the paper.
