# Experimental protocol and execution levels

This protocol is a reproducibility interface, not an authorization to launch
the historical campaign. No Level 3 experiment was run during this audit.

## Level 1: smoke tests

Requirements: Java 21, Maven, and an ordinary development machine. No road
network or external download is needed.

```bash
./scripts/setup/verify_environment.sh
./scripts/validation/artifact_integrity.py
./scripts/validation/smoke.sh
```

The smoke command builds/tests the Java project, runs the small `PaceCli`
demonstration with PACE-X, and writes only Maven `target/` output. It uses the
repository demo graph and fixed in-code inputs; it does not claim to reproduce
historical random workloads.

## Level 2: focused reproduction

The independent continuous oracle is the safest focused check:

```bash
./scripts/validation/oracle.sh
```

It runs `PaceExactOracleDifferentialTest` and
`PacePublicApiOracleIntegrationTest`. The stored audit reports 1,009
independent full-profile micro-instance comparisons, plus separate internal
PACE-X consistency checks. A successful run validates only the tested fixtures
under the repository's canonical time-tick semantics.

The controlled result-processing workflow can operate on supplied raw result
trees without routing if the author later adds those raw files. Use the
reporting script only with a reviewed run directory:

```bash
./scripts/reporting/regenerate_supported.sh RUN_ID
```

The current package includes derived plot data and supplied figures, but not
the bulk raw runs needed to regenerate every summary.

## Level 3: full experimental reproduction

All full workflows are opt-in and refuse to start unless
`PACE_ARTIFACT_RUN_EXPENSIVE=1` is set. The wrappers do not run automatically:

```bash
PACE_ARTIFACT_RUN_EXPENSIVE=1 ./scripts/experiments/controlled.sh
PACE_ARTIFACT_RUN_EXPENSIVE=1 ./scripts/experiments/large_network.sh
PACE_ARTIFACT_RUN_EXPENSIVE=1 ./scripts/experiments/sensitivity.sh \
  experiments/configs/studies/e05_window.yaml
./scripts/experiments/nyc_case_study.sh
```

Before any such run, supply the input graphs/functions/manifests, verify
redistribution rights, choose a run ID, and review the relevant configuration.
The default large-network configuration is the stored T03 design, not a claim
that it matches the final manuscript protocol. The raw-data audit found a
PACE-B ten-second T03 limit and FLA queries above five seconds, so the author
must resolve that mismatch before calling the workflow a reproduction of a
common five-second comparison.

## Inputs and outputs

| Workflow | Required inputs | Output location | Expected evidence |
| --- | --- | --- | --- |
| Environment/build | Java 21, Maven | `target/` | Maven classes/JAR; no scientific results. |
| Smoke | None beyond build tools | stdout and `target/` | Demo statuses and passing tests. |
| Oracle | None beyond build tools | Maven reports/stdout | Differential test result; no historical tables. |
| Controlled | NY-Exact/NY-CTRL graph, temporal data, query manifests, exact-study config | `experiments/results/<run-id>/` | PACE-X/PACE-B profile/status records and validation summaries. |
| Large network | NY, FLA, CAL inputs, evaluation manifests, reviewed resource limits | run directory | Query-level records, trial aggregation, coverage, RSS, and status counts. |
| Sensitivity | Required graph variants and per-series manifests | run directory | Series-specific raw records and aggregation. |
| NYC | Licensed/downloaded road, traffic, transit/GTFS inputs and manifests | case-study results/reports | Data provenance, exact replay diagnostics, and displayed profile. |
| Reporting-only | Existing raw run directory and matching config | run `summaries/`, `tables/`, `figures/` | Derived outputs only; no routing execution. |

## Seeds and determinism

Some generator/config files record seeds, including dataset seed 42 and query
generation seeds. The no-commit working tree and missing source binding mean
those do not establish the seed used for every historical published result.
Where historical seeds or manifests are absent, the artifact makes no claim of
bitwise reproduction. Java profile checksums are deterministic for matching
inputs/configuration under the repository's canonicalization, but runtime and
resource observations are environment-dependent.

## Failure behavior and resources

Resource limits must be treated as scientifically meaningful statuses, not
silently converted to missing data. The Java runner serializes timeout,
memory, cap, unresolved, and completion information. A failed or interrupted
PACE-X run cannot receive global certification. A bounded PACE-B empty result
must not be reported as infeasible without an independent certificate.

Level 3 large-network work requires substantial RAM, fast local storage, and
many hours or longer depending on network/series. The requested 24-worker
protocol and 300 GB historical hardware are not established from this source
tree. The NYC workflow requires external downloads and legal review.

## Historical result regeneration

The supplied publication figures/tables and plot data are retained under
`results/` and `figures/` as historical evidence. They are not relabelled as
freshly reproduced measurements. Each record is mapped in
`../provenance/RESULT_PROVENANCE.csv`; missing raw sources are explicitly
marked `REPORTING_ONLY` or `UNVERIFIED`.
