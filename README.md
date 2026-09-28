# PACE research artifact
## What is included

- The complete Java Maven implementation and existing regression tests.
- PACE-X, PACE-B, the iSCOPE adaptation, query generation, experiment drivers,
  reporting support, configurations, schemas, and NYC case-study scripts.
- An independent continuous oracle and stored audit evidence for 1,009
  tractable micro-instance comparisons.
- Supplied historical plot data, tables, figures, and provenance mappings.
- Dataset metadata and query manifests without redistributing large or
  third-party road-network inputs.

PACE-B selects the best path among generated/retained candidates; it does not
guarantee global optimality. PACE-X can be globally certified only for a
completed qualifying exhaustive execution scope. A passing regression test is
not a mathematical exactness proof.

## Requirements and quick start

Java 21, Maven, and Python 3 are required for the documented interface.

```bash
./scripts/setup/verify_environment.sh
./scripts/setup/build.sh
./scripts/validation/artifact_integrity.py
./scripts/validation/smoke.sh
```

For the independent oracle:

```bash
./scripts/validation/oracle.sh
```

Smoke and oracle commands use only the included Java source/tests and tiny demo
inputs. They do not execute the historical campaign.

## Reproduction levels

Level 1 is the smoke workflow above. Level 2 is the independent oracle and
reporting-only validation over supplied data. Level 3 wrappers are explicit
and opt-in:

```bash
PACE_ARTIFACT_RUN_EXPENSIVE=1 ./scripts/experiments/controlled.sh
PACE_ARTIFACT_RUN_EXPENSIVE=1 ./scripts/experiments/large_network.sh
PACE_ARTIFACT_RUN_EXPENSIVE=1 ./scripts/experiments/sensitivity.sh CONFIG
./scripts/experiments/nyc_case_study.sh
```

These require the excluded network/temporal inputs, matching query manifests,
reviewed resource limits, and legal permission. The large-network wrapper does
not prove that its current stored T03 configuration matches the manuscript;
the raw audit records a PACE-B ten-second internal limit and FLA runs above
five seconds. Do not call that a common five-second comparison without author
reconciliation.

## Data and NYC case study

`data/manifests/` contains metadata for NY, FLA, CAL, and controlled exact
datasets; the graph files are intentionally absent. Download or reconstruct
them only from authorized sources and verify the recorded checksums.

The NYC workflow is a separate 14 May 2026 EDT data-calibrated case study.
The displayed example is `NYC-Q012-MORNING-R20`: source 146634, destination
151351, interval 07:00–09:00 EDT, and `B=8.382654224124` minutes. Its five
reported path signatures are retained in the supplied plot data; singleton
assignments at 07:41, 07:58, and 07:59 are preserved without inventing causes.
Road, traffic, and GTFS inputs must be downloaded separately according to
`case_studies/nyc_shuttle/README.md` and checked for redistribution rights.
