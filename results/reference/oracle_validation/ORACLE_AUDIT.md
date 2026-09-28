# PACE-X independent correctness-evidence audit

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
