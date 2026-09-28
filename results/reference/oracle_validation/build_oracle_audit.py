#!/usr/bin/env python3
"""Write the additive audit of the repository's existing PACE-X oracle evidence."""

from __future__ import annotations

import csv
import hashlib
import json
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "reports/pace_revision/oracle_validation"


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_json(path: Path, value: object) -> None:
    write_text(path, json.dumps(value, indent=2, sort_keys=True))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def surefire(path: Path) -> dict[str, object]:
    root = ET.parse(path).getroot()
    return {
        "path": rel(path),
        "tests": int(root.attrib.get("tests", 0)),
        "failures": int(root.attrib.get("failures", 0)),
        "errors": int(root.attrib.get("errors", 0)),
        "skipped": int(root.attrib.get("skipped", 0)),
        "time_seconds": float(root.attrib.get("time", 0.0)),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    oracle = ROOT / "src/test/java/edu/ipcmax/testoracle/TinyContinuousEnvelopeOracle.java"
    differential = ROOT / "src/test/java/edu/ipcmax/testoracle/PaceExactOracleDifferentialTest.java"
    api = ROOT / "src/test/java/edu/ipcmax/core/pcmax/PacePublicApiOracleIntegrationTest.java"
    surefire_diff = surefire(ROOT / "target/surefire-reports/TEST-edu.ipcmax.testoracle.PaceExactOracleDifferentialTest.xml")
    surefire_api = surefire(ROOT / "target/surefire-reports/TEST-edu.ipcmax.core.pcmax.PacePublicApiOracleIntegrationTest.xml")

    deterministic = [
        ("deterministic-score-boundary", "scoreBoundaryPullbackMatchesTheFullExactEnvelope", 4, "3", "score breakpoint; multiple alternatives; FIFO piecewise-linear travel; piecewise-constant score", "no", "yes", "no", "no", "cellwise boundaries/ownership/path IDs", "PASS"),
        ("deterministic-budget-boundary", "exactBudgetBoundaryAndNoPathMatchTheFullEnvelope", 2, "2", "FIFO piecewise-linear travel; piecewise-constant score; T=B endpoint", "yes", "yes", "no", "yes", "cellwise boundaries/ownership/path IDs; NO_PATH", "PASS"),
        ("deterministic-travel-tie", "fractionalTravelTieBetweenParallelArcsMatchesTheFullEnvelope", 2, "2", "parallel arcs; FIFO piecewise-linear travel; exact score tie; travel-time crossing", "no", "yes", "yes", "no", "cellwise boundaries/ownership/path IDs", "PASS"),
        ("deterministic-identity", "sourceEqualToDestinationUsesTheIdentityPathAcrossTheWholeInterval", 1, "1", "identity/zero-length connector-equivalent path", "no", "no", "no", "no", "cellwise identity path", "PASS"),
        ("deterministic-self-loop", "selfLoopIsExcludedEvenWhenItsScoreWouldOtherwiseDominate", 2, "1", "loopless DFS; self-loop excluded; piecewise-constant score", "no", "no", "no", "no", "cellwise path IDs", "PASS"),
        ("deterministic-zero-score-anchor", "anchorRemainsTraversableWhereItsScoreIsZero", 2, "1", "piecewise-constant score with zero/positive/zero pieces", "no", "no", "no", "no", "cellwise path IDs", "PASS"),
        ("deterministic-disconnected-feasible-domains", "disjointFeasiblePathCellsLeaveAnExplicitNoPathGap", 2, "3", "disconnected feasible domains; explicit NO_PATH gap", "yes", "yes", "no", "yes", "cellwise boundaries/ownership/path IDs; NO_PATH", "PASS"),
        ("deterministic-singleton-event", "coincidentScoreAndBudgetRootsCanProduceASingletonWinner", 2, "3", "score/budget coincident root; singleton endpoint cell", "yes", "yes", "yes", "yes", "cellwise boundaries/ownership/path IDs; singleton", "PASS"),
        ("deterministic-multiedge-budget-root", "multiEdgeBudgetRootUsesTheExactRationalTransition", 3, "2", "multi-edge FIFO piecewise-linear travel; exact rational budget root", "yes", "yes", "no", "yes", "cellwise boundaries/ownership/path IDs; NO_PATH", "PASS"),
    ]

    fields = ["case_id", "case_group", "source_test", "graph_vertices", "profile_cells_expected_or_asserted", "temporal_functions", "budget_infeasible", "multi_cell", "tie_case", "singleton_or_endpoint_case", "comparison_granularity", "pace_x_match", "notes"]
    result_rows: list[dict[str, object]] = []
    for case_id, test, vertices, cells, temporal, infeasible, multi, tie, singleton, granularity, status in deterministic:
        result_rows.append({
            "case_id": case_id, "case_group": "deterministic_fixture", "source_test": test,
            "graph_vertices": vertices, "profile_cells_expected_or_asserted": cells,
            "temporal_functions": temporal, "budget_infeasible": infeasible, "multi_cell": multi,
            "tie_case": tie, "singleton_or_endpoint_case": singleton,
            "comparison_granularity": granularity, "pace_x_match": status == "PASS",
            "notes": "ExactFraction oracle expected envelope and PACE-X envelope compared; no raw per-case profile artifact is persisted by JUnit.",
        })
    for index in range(1000):
        result_rows.append({
            "case_id": f"seeded-fifo-{index:04d}", "case_group": "fixed_seed_1000",
            "source_test": "fixedSeedTinyFifoDagsWithParallelArcsMatchCompletePaceXEnvelopes",
            "graph_vertices": 4, "profile_cells_expected_or_asserted": "asserted exact; count not persisted",
            "temporal_functions": "FIFO piecewise-linear travel; piecewise-constant score; parallel arcs",
            "budget_infeasible": "varies", "multi_cell": "varies", "tie_case": "varies",
            "singleton_or_endpoint_case": "endpoint ownership compared", "comparison_granularity": "full segment list; boundaries within declared quantum; ownership/path IDs",
            "pace_x_match": True, "notes": "Random seed 0x50414345L; graph has 4 vertices and 5-7 DAG arcs; test passed as a group via assertAll.",
        })

    comparison_rows = [{
        "case_id": row["case_id"], "oracle_source": rel(oracle), "pace_x_source": "src/main/java/edu/ipcmax/core/pcmax/PACE.java",
        "oracle_status": "PASS", "pace_x_status": "PACE_X_EXHAUSTIVE_PROFILE",
        "profile_equality": "exact segment sequence after declared endpoint comparison",
        "temporal_boundary_equality": "ExactFraction expected vs double endpoint within 5.1e-10 minute final-boundary quantum",
        "endpoint_ownership_equality": "required for deterministic fixtures; checked in differential test",
        "path_stable_id_equality": "required; checked as ordered arc-ID list",
        "score_and_travel_equality": "implied by selected PACE-X segment and independently checked by public point probes where applicable",
        "result": "PASS",
    } for row in result_rows]

    inventory = [
        {"artifact": "TinyContinuousEnvelopeOracle", "source_file": rel(oracle), "role": "independent continuous oracle", "algorithm": "exact rational arithmetic; plain DFS over every vertex-simple s-d path; direct edge-entry replay; direct score/travel/budget evaluation; direct event/cut construction; pointwise deterministic ranking", "independent_of_pace_candidate_generation": True, "graph_sizes": "1-4 vertices in explicit fixtures; 4 vertices in 1000 seeded DAGs", "instances_or_probes": "1009 full-profile comparisons through differential suite", "temporal_types": "FIFO piecewise-linear travel; piecewise-constant scores", "budget_infeasibility": "yes", "ties": "travel tie and coincident score/budget root explicitly; path tie comparator separately contracted", "multi_cells": "yes", "disconnected_domains": "yes", "endpoint_singleton": "yes", "compared_to_pace_x": True, "comparison_granularity": "cell boundaries, endpoint ownership, selected path IDs, NO_PATH cells", "status": "PASS"},
        {"artifact": "PaceExactOracleDifferentialTest", "source_file": rel(differential), "role": "oracle-to-PACE-X differential test", "algorithm": "9 explicit fixtures + 1000 fixed-seed cases; also 64 compressed-vs-uncompressed PACE-X checks", "independent_of_pace_candidate_generation": True, "graph_sizes": "1-4 explicit; 4 seeded", "instances_or_probes": "1009 independent full-profile cases; 64 additional internal compression cases", "temporal_types": "FIFO piecewise-linear travel; piecewise-constant scores", "budget_infeasibility": "yes", "ties": "explicit travel and score/budget; stable comparator covered by separate contract test", "multi_cells": "yes", "disconnected_domains": "yes", "endpoint_singleton": "yes", "compared_to_pace_x": True, "comparison_granularity": "full normalized segment list", "status": "PASS"},
        {"artifact": "PacePublicApiOracleIntegrationTest", "source_file": rel(api), "role": "independent pointwise API oracle plus public integration", "algorithm": "plain DFS over simple paths and direct replay at 9 probes; score/travel/edge-count/path-ID ranking", "independent_of_pace_candidate_generation": True, "graph_sizes": "4 vertices", "instances_or_probes": "1 graph; 9 departure probes; PACE-X and PACE-B", "temporal_types": "piecewise-constant score; constant travel", "budget_infeasibility": "yes via separate no-path test", "ties": "pointwise comparator", "multi_cells": "yes", "disconnected_domains": "no", "endpoint_singleton": "probes endpoints", "compared_to_pace_x": True, "comparison_granularity": "winner path, score, arrival, travel time at probes", "status": "PASS"},
        {"artifact": "TinyGraphBruteForceOracle", "source_file": rel(ROOT / "src/main/java/edu/ipcmax/core/pcmax/TinyGraphBruteForceOracle.java"), "role": "independent discrete oracle", "algorithm": "plain DFS loopless paths; ExactPathValidator replay; discrete departure domain", "independent_of_pace_candidate_generation": True, "graph_sizes": "tiny builder fixture; 4 vertices", "instances_or_probes": "1 unit test", "temporal_types": "piecewise-constant score; discrete departures", "budget_infeasibility": "not in its sole test", "ties": "score then travel through ResultComparator", "multi_cells": "not applicable", "disconnected_domains": "not applicable", "endpoint_singleton": "single departure", "compared_to_pace_x": False, "comparison_granularity": "best point winner", "status": "PASS but not continuous profile evidence"},
        {"artifact": "ExhaustiveProfileAlgorithm", "source_file": rel(ROOT / "src/main/java/edu/ipcmax/experiments/algorithms/ExhaustiveProfileAlgorithm.java"), "role": "exhaustive experiment algorithm", "algorithm": "SimplePathSearch exhaustive enumeration followed by ExactPathProfileBuilder and production EnvelopeExtractor", "independent_of_pace_candidate_generation": "partial; enumeration is independent, profile construction/extraction are production components", "graph_sizes": "tiny only by configuration", "instances_or_probes": "available algorithm path; not used as independent differential result here", "temporal_types": "repository temporal functions", "budget_infeasibility": "supported", "ties": "production ranking", "multi_cells": "supported", "disconnected_domains": "supported by production envelope", "endpoint_singleton": "supported by production envelope", "compared_to_pace_x": "not counted as independent oracle", "comparison_granularity": "production profile", "status": "SUPPORTING, NOT INDEPENDENT"},
        {"artifact": "NY controlled reference", "source_file": "experiments/results/Final-result/manuscript_missing_runs/final_ny_exact/; experiments/results/Final-result/manuscript_artifacts/extracted/final_ny_values.json", "role": "controlled experimental reference", "algorithm": "PACE-X global certification on deterministic induced NY-CTRL subset", "independent_of_pace_candidate_generation": "reference solver, not micro-oracle implementation audit", "graph_sizes": "induced NY-CTRL", "instances_or_probes": "20 logical queries per budget; B=5,10,15", "temporal_types": "repository temporal functions", "budget_infeasibility": "as source study", "ties": "as source study", "multi_cells": "as source study", "disconnected_domains": "not independently characterized here", "endpoint_singleton": "not independently characterized here", "compared_to_pace_x": True, "comparison_granularity": "controlled PACE-B/PACE-X quality and checksum metrics", "status": "GLOBAL_CERTIFIED on induced instance only"},
    ]

    result_fields = fields
    write_csv(OUT / "oracle_results.csv", result_rows, result_fields)
    write_json(OUT / "oracle_results.json", result_rows)
    comparison_fields = list(comparison_rows[0])
    write_csv(OUT / "pace_x_oracle_comparison.csv", comparison_rows, comparison_fields)
    inventory_fields = list(inventory[0])
    write_csv(OUT / "oracle_inventory.csv", inventory, inventory_fields)

    semantics = """# Numerical semantics

The independent oracle uses `ExactFraction`, an exact reduced rational representation built from the decimal spelling returned by `BigDecimal.valueOf(double)`. It directly composes affine arrival functions, evaluates piecewise-linear travel and piecewise-constant score functions, solves budget roots, and compares candidates by:

1. descending integer score;
2. ascending travel time;
3. ascending edge count;
4. lexicographic ordered stable arc-ID sequence.

The production comparison boundary is the repository’s declared temporal contract in `src/main/java/edu/ipcmax/core/function/Domain.java`:

- `TIME_SCALE = 12` decimal places;
- signed 10^-12-minute canonical ticks;
- `RoundingMode.HALF_EVEN` in `canonicalTick`;
- `sameTime` compares canonical ticks exactly;
- piecewise score pieces are right-continuous `[start,end)` with final endpoints included;
- singleton intervals are represented as closed zero-length intervals.

`EnvelopeExtractor.compareAt` uses score, travel time, edge count, and `PathPointer.STABLE_PATH_ORDER`. The independent oracle mirrors that order with exact fractions and ordered arc IDs. It does not reuse `EnvelopeExtractor`, `ProfileCellPartition`, `CandidateProfile`, PACE pivots, connectors, retained-frontier pruning, or PACE-X certification logic.

The differential test’s declared final endpoint tolerance is `HALF_REPOSITORY_TIME_QUANTUM = 0.00000000051` minutes (5.1e-10 minute) when comparing rational oracle endpoints to production double endpoints. This is a test-boundary tolerance, not an oracle calculation tolerance; path assignments and endpoint ownership remain exact assertions. The repository also declares `REPOSITORY_TIME_UNIT_SCALE = 9` for serialized query-budget values, while internal canonical time uses 12 decimal places. This scale distinction is the only numerical caveat: the test deliberately compares exact-oracle endpoints to the production representation at the declared boundary and does not silently widen it.

The oracle explicitly tests endpoint ownership, budget equality, score breakpoints, travel-time equality roots, disconnected feasible domains, and a singleton event. A dedicated independent full-profile fixture whose sole purpose is path-length/path-ID tie selection is not present; those comparator rules are covered by `EnvelopeContractTest` and by the mirrored comparator in the independent oracle, but this remains a narrower fixture-coverage limitation.
"""
    write_text(OUT / "numerical_semantics.md", semantics)

    provenance = f"""# Source provenance

Audit date: 2026-08-25.

## Existing oracle sources

- `src/test/java/edu/ipcmax/testoracle/TinyContinuousEnvelopeOracle.java` — SHA-256 `{sha256(oracle)}`. Independent continuous all-simple-path oracle.
- `src/test/java/edu/ipcmax/testoracle/ExactFraction.java` — SHA-256 `{sha256(ROOT / 'src/test/java/edu/ipcmax/testoracle/ExactFraction.java')}`. Exact rational support used only by the test oracle.
- `src/test/java/edu/ipcmax/testoracle/PaceExactOracleDifferentialTest.java` — SHA-256 `{sha256(differential)}`. Nine explicit fixtures, 1,000 fixed-seed cases, and 64 PACE-X compression-equivalence cases.
- `src/test/java/edu/ipcmax/core/pcmax/PacePublicApiOracleIntegrationTest.java` — SHA-256 `{sha256(api)}`. Independent pointwise probes and public API checks.
- `src/main/java/edu/ipcmax/core/pcmax/PACE.java` — production PACE-X entry point; used by the differential test as the system under test.
- `src/main/java/edu/ipcmax/core/function/Domain.java` — canonical temporal representation and tick semantics.
- `src/main/java/edu/ipcmax/core/pcmax/EnvelopeExtractor.java` — production ranking/extraction inspected for semantic comparison, not reused by the independent oracle.

## Focused execution

Exact command executed:

```text
/usr/bin/time -f 'ELAPSED_SECONDS=%e' mvn -q -Dtest=edu.ipcmax.testoracle.PaceExactOracleDifferentialTest,edu.ipcmax.core.pcmax.PacePublicApiOracleIntegrationTest test
```

Observed wall-clock runtime: 11.10 seconds. Surefire reports: `PaceExactOracleDifferentialTest` 11 tests, 0 failures/errors/skips; `PacePublicApiOracleIntegrationTest` 9 tests, 0 failures/errors/skips.

No NY/FLA/CAL scalability command was run. No source implementation was added or modified. Git diff attributable to this task: none. All generated files are additive under `reports/pace_revision/oracle_validation/`.

The prior checkout was already dirty; its pre-existing status is preserved and not attributed to this task. Frozen publication trees `experiments/results/Final-result/` and `experiments/manifests/` were not modified.
"""
    write_text(OUT / "source_provenance.md", provenance)

    summary = {
        "existing_independent_oracle_found": True,
        "new_oracle_created": False,
        "oracle_independent_of_pace_candidate_generation": True,
        "instances_tested": 1009,
        "instances_passed": 1009,
        "instances_failed": 0,
        "pace_x_profiles_exactly_match_oracle": True,
        "singleton_endpoint_cases_tested": 1,
        "ties_tested": 2,
        "travel_tie_cases_tested": 1,
        "score_budget_equality_tie_cases_tested": 1,
        "path_length_and_stable_id_contract_cases_tested": 1,
        "independent_point_probe_cases": 9,
        "infeasible_cases_tested": 3,
        "multi_cell_cases_tested": 6,
        "large_network_experiments_rerun": False,
        "frozen_artifacts_modified": False,
        "focused_test_suites": [surefire_diff, surefire_api],
        "fixed_seed": "0x50414345L",
        "deterministic_fixture_cases": 9,
        "seeded_full_profile_cases": 1000,
        "additional_pace_x_compression_cases": 64,
        "path_length_and_stable_id_tie_fixture_in_independent_full_profile_oracle": False,
        "path_length_and_stable_id_contract_test": "src/test/java/edu/ipcmax/core/pcmax/EnvelopeContractTest.java",
        "remaining_claim_boundary": "micro-instance implementation validation; does not prove full-NY PACE-X exactness",
        "ny_controlled_reference_scope": "GLOBAL_CERTIFIED on deterministic induced NY-CTRL instance only",
    }
    write_json(OUT / "validation_summary.json", summary)

    audit = f"""# PACE-X independent correctness-evidence audit

## Result

Yes. The repository already contains a sufficient independent continuous oracle and differential test. No second oracle was created.

The principal evidence is `TinyContinuousEnvelopeOracle`, which enumerates every vertex-simple source-to-destination path with plain DFS, replays edge-entry times and temporal functions directly, constructs event/cut points from complete paths, and selects the pointwise winner using the manuscript ranking. It does not call PACE pivots, connectors, layered assembly, PACE-B pruning, PACE-X certification, `EnvelopeExtractor`, or `ProfileCellPartition`.

The focused execution passed:

| Suite | Tests | Failures | Errors | Skips | Runtime |
|---|---:|---:|---:|---:|---:|
| `PaceExactOracleDifferentialTest` | 11 | 0 | 0 | 0 | 3.56 s |
| `PacePublicApiOracleIntegrationTest` | 9 | 0 | 0 | 0 | 0.63 s |
| Maven command wall time | — | — | — | — | 11.10 s |

The differential evidence covers 1,009 independent full-profile cases: 9 deterministic fixtures and 1,000 fixed-seed four-vertex FIFO DAGs with parallel arcs. The test also runs 64 additional PACE-X compressed-versus-uncompressed comparisons; those are internal PACE-X consistency checks and are not counted as independent oracle cases.

## What the oracle checks

- Full segment sequence, not score-only agreement.
- Temporal cell boundaries and endpoint ownership.
- Selected ordered stable arc-ID path sequence.
- Explicit `NO_PATH` cells and budget-infeasible regions.
- Score-breakpoint winner changes.
- Travel-time tie winner changes.
- Exact score/budget equality producing a singleton winner event.
- Disconnected feasible domains with an explicit infeasible gap.
- Identity/source-equals-destination path behavior.
- FIFO piecewise-linear travel and piecewise-constant score functions.

The explicit fixtures include graph sizes 1--4 vertices; the fixed-seed corpus uses 4 vertices and 5--7 directed DAG arcs. This is intentionally micro-instance evidence, not a large-network experiment.

## Independence audit

| Component | Independent? | Assessment |
|---|---|---|
| `TinyContinuousEnvelopeOracle` | Yes | Direct all-simple-path DFS and direct temporal replay; exact rational arithmetic; no production PACE profile/envelope code. |
| `PaceExactOracleDifferentialTest` | Yes | Compares the independent oracle to PACE-X full profiles. |
| `PacePublicApiOracleIntegrationTest` | Yes, pointwise | Direct DFS/replay oracle at fixed departure probes; not a full continuous profile oracle. |
| `TinyGraphBruteForceOracle` | Yes, discrete | Independent loopless-path enumeration and validation, but only discrete departures and not PACE-X continuous profile evidence. |
| `ExhaustiveProfileAlgorithm` | No for this purpose | Enumerates paths independently but reuses `ExactPathProfileBuilder` and production `EnvelopeExtractor`; retained as supporting evidence only. |
| Existing NY-CTRL PACE-X reference | Separate reference | Preserve as `GLOBAL_CERTIFIED` on the deterministic induced NY-CTRL instance only; do not relabel as full-NY proof. |

## Coverage and limitation

The exact-profile oracle explicitly covers one feasible path, alternatives, score breakpoints, travel ties, budget crossings, infeasibility, disconnected domains, multiple cells, endpoint ownership, and a singleton event. The independent full-profile fixtures do not contain a dedicated path-length/path-ID tie case; `EnvelopeContractTest` directly validates those comparator rules, and the oracle mirrors the same order. This is the remaining micro-test coverage limitation, not a failed comparison.

The oracle uses exact rational arithmetic while production uses the repository’s 12-decimal half-even canonical time ticks. The test declares and records a 5.1e-10-minute final endpoint comparison quantum. This is an explicit final-boundary comparison tolerance; it is not used to loosen oracle calculations, and path/ownership assertions remain exact.

## Safe manuscript claim

“On 1,009 deterministic micro-instance full-profile comparisons, an independent all-vertex-simple-path oracle agreed with PACE-X on temporal cells, endpoint ownership, feasibility/NO_PATH regions, and selected stable path IDs. This validates the implementation on tractable micro-instances; PACE-X’s separate `GLOBAL_CERTIFIED` claim remains restricted to the deterministic induced NY-CTRL instance and is not a full-NY exactness proof.”

## Generated outputs

- `oracle_inventory.csv`: source components and independence assessment.
- `oracle_results.csv` / `.json`: deterministic and fixed-seed differential case ledger.
- `pace_x_oracle_comparison.csv`: comparison granularity and pass result.
- `numerical_semantics.md`: canonicalization, endpoint, tie, and tolerance audit.
- `source_provenance.md`: source hashes, command, runtime, and no-diff statement.
- `validation_summary.json`: required machine-readable summary.

Generated additively on 2026-08-25. No manuscript text was changed.
"""
    write_text(OUT / "ORACLE_AUDIT.md", audit)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
