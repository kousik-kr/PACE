# ICDE 2027 baselines: SICSP-Pref and THop

**Status:** Implementation contract; no baseline results claimed.
**Integration branch:** `feature/icde27-sicsp-thop`.
**Source papers:**
1. Ye Yuan et al., *Constrained Shortest Path Query in a Large Time-Dependent Graph*, PVLDB 12(10), 2019. Main sequential method: Sections 3.1–3.2, Algorithm 1 (`ICSP_Arr`), Algorithm 2 (`ArrTime`).
2. Lei Li, Sibo Wang, Xiaofang Zhou, *Time-Dependent Hop Labeling on Road Network*, ICDE 2019. Native FPP model: Section III; pruned THop: Section IV; partitioned THop: Section V; optional approximations: Section VI.

## Scientific contracts — do not silently change

* **THop** remains the ORIGINAL fastest-path-profile problem: for each departure t in I, minimize travel time. It must NOT optimize preference or impose the PACE travel-time budget. Index building, index bytes, and query time are distinct measurements. Route witnesses, if reconstructed, are used only to report the chosen fastest paths; score is not part of route selection.
* **Native SICSP** must first reproduce arrival-time minimization with additive weight bound; keep the source paper's separate O-point/W-point mechanisms and breakpoint-driven reverse/forward Dijkstra candidate generation. Section 3.2 specifies ICSP_Arr explicitly but leaves ICSP_Wgh analogous rather than fully specified. Write down reconstruction assumptions and reference checks.
* **SICSP-Pref** is an OBJECTIVE-ADAPTED SICSP BASELINE, not the original algorithm. Keep LST/EAT and path-grouped breakpoint candidate generation; replace weight attribute by score, flip secondary ranking/dominance only where the original algorithm uses it, enforce T_P(t) <= B and select largest S_P(t) over the retained candidates. Do not add PACE pivots/connectors or replace native Dijkstra with custom score-search. Candidate-level exact replay does NOT certify global optimality.
* All implementations operate on immutable `TDGraph` and `QuerySpec` objects; never modify PACE-B/PACE-X or iSCOPE logic to accommodate them. Preserve historical runs and artifacts.

## Repository integration points confirmed

* Graph: `src/main/java/edu/ipcmax/core/graph/{TDGraph,Edge}.java`.
* Temporal inputs: `core/function/{Domain,PiecewiseLinearFn,PiecewiseConstFn}.java`.
* Candidate scoring and feasible replay: `core/pcmax/ExactPathProfileBuilder.java`.
* Score envelope: `core/pcmax/EnvelopeExtractor.java`.
* Native fastest-path envelope: `core/pcmax/FastestEnvelopeExtractor.java` (explicitly ignores preferences).
* Experiment interface: `experiments/framework/ExperimentAlgorithm.java`, with `prepare` for THop indexing.
* Registry: `experiments/AlgorithmRegistry.java`.
* Outcome envelope `AlgorithmResult` can currently only store `EnvelopeProfile`; native fastest results must be marked `objective=MIN_TRAVEL_TIME`, `budget_applied=false` and must NOT be interpreted as preference-optimal.
* Independent oracle: `src/test/java/edu/ipcmax/testoracle/TinyContinuousEnvelopeOracle.java` (preference oracle); implement a separate independent fastest-profile reference.

**Build blocker confirmed:** current public GitHub tree has no root `pom.xml`, but `README.md`, `scripts/setup/build.sh`, `scripts/validation/smoke.sh` require one. Resolve this before claiming passing Maven tests.

## Proposed packages / stable IDs

* `edu.ipcmax.baselines.thop`: `TemporalFastestProfileSearch`, `HopLabel`, `ThopIndexBuilder`, `ThopIndex`, `ThopProfileQuery`, then `PartitionedThopIndex`, optional `AtDijkstra`, `BottomUpCompression`.
* `edu.ipcmax.baselines.sicsp`: `TimeDependentDijkstra`, `LatestDepartureSearch`, `BreakpointCandidate`, `SicspArrivalCandidates`, `SicspWeightCandidates`, `SicspDominance`, `SicspNativeQuery`, `SicspPreferenceQuery`.
* Thin runners under `experiments/algorithms`: IDs `thop-exact`, `sicsp-native`, `sicsp-pref`; add `thop-at`, `thop-bu` only after the exact version passes validation.

The public API of THop must return the fastest temporal profile; the output may include witnesses and ancillary score for analysis but score must not influence selection. For SICSP-Pref the existing canonical `EnvelopeProfile` from candidate replay and score envelope is appropriate.

## Incremental PR strategy

### PR 0 — Build and contract tests
1. Restore the actual Maven root build file, or explicitly resolve build layout.
2. Add contract tests demonstrating that THop ignores score and budget: modifying only scores or B must not alter the native fastest profile.
3. Add two incompatible-objective example graphs: fastest path differs from feasible most-preferred path; verify PACE and native THop intentionally differ.
4. Freeze query fixtures, seeds, attributes and input checksums.

### PR 1 — Time-dependent reference searches
1. Implement point earliest-arrival Dijkstra on FIFO edges using edge-entry-time evaluation and stable ties.
2. Implement reverse latest-departure search using generalized FIFO arrival inversion; handle plateaus, closed/open interval ends, discontinuities of scores, and finite function support.
3. Implement an independent, small-graph native fastest profile oracle by enumerating simple paths and exact time-dependent lower envelopes (not by calling PACE).
4. Tests: trivial graph, equal paths, crossing arrivals, constant travel, FIFO plateaus, no path and time-domain limits.

### PR 2 — THop exact, small networks
1. Construct unpruned in/out hop labels from *complete* fastest-path functions with witness support.
2. Implement the Section IV pruned ordered labeling exactly after the unpruned form passes.
3. Query by intersecting hops, composing their time-dependent profiles at actual entry time and taking min envelope; no budget filtering.
4. Compare every source-destination pair and all breakpoints against independent oracle on tiny networks.
5. Track `index_construction_ns`, `index_bytes`, `query_ns`, `labels`, `hop_intersections`, `function_pieces`, `index_peak_memory`.
6. Only after parity implement Section V partitioned boundary/inner labels, disk-backed storage, sampling and optionally Section VI approximations. Partial small-network THop must not be called full large-network THop.

### PR 3 — Native SICSP
1. Separate ICSP_Arr O-points and ICSP_Wgh W-points; keep native Dijkstra candidate selection and grouping by complete path.
2. Record ambiguity ledger for underspecified ICSP_Wgh and temporal arguments.
3. Construct arrival/weight profiles according to Sections 3.1–3.2, then apply original weight bound.
4. Check Figure 1 and Figure 2 examples; independently compare native answer to exact small-graph constrained arrival reference; error is reported because original method is heuristic.

### PR 4 — Minimal SICSP-Pref objective adaptation
1. Keep native breakpoints, reverse/forward Dijkstra and candidate grouping unchanged, including their limitations.
2. Replace edge weight attributes with time-dependent preference scores; preserve O and adapted W point handling.
3. Implement point-level dominance with direction minimizing arrival / maximizing score, with a clear statement that it is not a global interval-safe guarantee.
4. Retain path witnesses; exact replay each candidate over entire source-departure interval; enforce T_P <= B; compute highest-score feasible envelope and original PACE tie rules.
5. Expose `candidate_generated`, `candidate_distinct`, `dominance_rejected`, `profile_replay_ns`, `envelope_ns`, `unresolved_fraction`.
6. Tiny oracle establishes candidate gap, not an invalid global-exactness claim.

### PR 5 — Fair experiments
1. Add three separate evaluation axes:
   * native THop fastest profile vs independent fastest-profile oracle and PACE travel-time characteristics (OBJECTIVES DIFFER),
   * SICSP-Pref vs PACE-B preference-constraint profile (OBJECTIVES MATCH),
   * native SICSP vs native exact small-graph arrival/weight oracle (fidelity).
2. Use identical graph/time functions, queries, departure domains; SICSP-Pref/PACE use identical scores and B.
3. THop preprocessing outside per-query time via `prepare`; report indexing time/space and end-to-end amortized analysis, not online timing alone.
4. Report coverage, score, travel time, native accuracy, quality gap, profiles, index resources separately. Do not treat THop's faster native problem as a win on preference maximization.
5. Test tiny -> extracted subgraphs -> NY/FLA/CAL conditional on memory/time; record completed and incomplete runs separately. Never silently change historical config or timeouts.
6. Use cold/warm and 1/24 worker runs only with explicit equivalent resource configuration.

## Gates

* **G0:** root Maven build restored, baseline existing smoke and oracle tests pass unchanged.
* **G1:** point forward/reverse search and time operators pass deterministic unit tests.
* **G2:** THop native exact profiles match independent oracle on every tiny tested pair; changing preference alone does not alter native output.
* **G3:** native SICSP reproduces its documented stages; all reconstruction assumptions audited.
* **G4:** SICSP-Pref's output is correct over its candidate registry and is gap-evaluated against independent global oracle.
* **G5:** only validated implementations enter full-network benchmarks.

**No experiment has been run and no correctness guarantee has been established by this document.**
