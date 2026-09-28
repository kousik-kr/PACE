# Paper-to-code claim audit

The authoritative manuscript requested for this audit is missing. The
repository contains no `PACE.tex` or manuscript PDF. This document therefore
uses `PACE_CODEBASE_AUDIT_REPORT.md` and the stored final-publication audits as
secondary evidence, while marking all manuscript-location-dependent findings
accordingly. The machine-readable matrix in `PAPER_CLAIM_MATRIX.csv` is the
claim-level register.

## Status policy

- **VERIFIED** means the active source and appropriate tests or historical
  evidence directly support the property.
- **PARTIALLY_VERIFIED** means some implementation/evidence exists, but a
  manuscript, historical binding, or theorem-level condition is missing.
- **UNVERIFIED** means the available material cannot establish the property.
- **CONTRADICTED** means the inspected implementation/evidence conflicts with
  the stated intended behavior.

Passing Java tests is not treated as mathematical exactness or experimental
reproduction.

## A. Temporal network model

The source supports directed stable-ID arcs, continuous evaluation of
piecewise-linear travel functions, piecewise-constant preference functions,
endpoint-aware domains, nonnegative travel validation, and vertex-simple path
validation. The independent oracle directly replays edge functions at the
actual entry time and includes a FIFO fixture with a decreasing travel-time
segment. This supports the general distinction required by the task: a FIFO
arrival function may arise even when travel time decreases on a segment, while
the principal synthetic construction is more restricted and uses
nondecreasing piecewise-linear travel-time functions.

The package does not merge those assumptions. The former is a model/property
tested on small instances; the latter is a construction/configuration claim
whose historical use is only partially recoverable from current generator
files and manifests.

Support and horizon checks are present in `QuerySpec` and the layered
generator. The implementation includes nonwaiting replay, explicit singleton
cells, and endpoint ownership. These facts do not prove that every bounded
execution covers the entire departure interval.

## B. Query semantics

`Domain`, `TimeRange`, `ProfileCellPartition`, and `EnvelopeExtractor` can
represent disjoint cells, closed singleton event cells, feasible cells, and
`NO_PATH` cells. The active comparator is:

1. descending preference score;
2. ascending travel time;
3. ascending edge count;
4. lexicographically ascending stable edge-ID sequence.

The comparator is directly covered by envelope contract tests and mirrored by
the independent oracle. The important limitation is output semantics: the
bounded generator can leave cells unrepresented because a cap or interruption
prevents candidate generation, but envelope serialization uses `NO_PATH` for
uncovered cells and the active output does not expose a manuscript-level `U`
symbol. NYC reports explicitly identify bounded-empty results as unresolved,
not infeasible. A paper statement equating all `NO_PATH` cells with proven
infeasibility is contradicted.

## C. Query-region construction and lower bounds

The active scalable path is not the EA/LD temporal-labeling construction
described in the prior manuscript audit. `QueryCorridor.build` constructs an
over-approximating static corridor using forward and reverse Dijkstra distances
with all-support minimum edge travel times, then retains original outgoing
arcs passing the static source/suffix inequalities. `PointForwardLabeling` is
used for point-departure connector work, not as the query-region builder.

This may be safe under an appropriate static lower-bound argument, and the
stored NYC fastest-witness audits report safe-corridor containment on their
tested inputs. It is nevertheless a different construction from EA/LD and
requires a different proof. `QueryLowerBounds` uses the complete corridor
graph rather than a graph with selected pivot edges removed; this part is
consistent with the requested lower-bound audit. Flat arrival portions are
handled by domain restriction and profile composition in the active path, with
continuous tests, but no authoritative manuscript is available to verify the
intended theorem statement.

## D. Pivot selection and connectors

Positive score support is intersected with feasible edge-entry support to
identify score-relevant arcs. A selected pivot is subsequently allowed over
its complete admissible entry domain, so traversal at a zero instantaneous
score is possible. Selected pivots and already visited vertices are excluded
from pivot-free connectors, while non-selected score arcs can remain ordinary
connector arcs.

The major discrepancy is pivot ranking. The active selector ranks by maximum
instantaneous score, positive-domain measure, normalized detour, cell ID, and
stable arc ID. The prior manuscript audit identifies an integrated-score
ranking in the paper description. The package does not silently change either
one; it records the mismatch.

PACE-X's general connector branch performs deterministic DFS enumeration of
vertex-simple, lower-bound-feasible connectors. It is exhaustive only when
the relevant graph/domain is complete and the full search completes without
any work, wall-time, memory, connector, breakpoint, or query-work cap. PACE-B
has portfolio and fast-only modes. The final fast-only branch uses a temporal
FIFO fastest structure at a request-cell midpoint and replays it over the
cell. The NYC diagnostic also records a static lower-bound witness mode in a
separate historical workflow. These are not one interchangeable connector
definition.

No active fallback rule was found that silently substitutes another connector
when the selected connector is temporally invalid or structurally conflicts.
Such cases can be rejected or yield an empty request. Cache keys are domain-
and context-sensitive and cache-disabling tests exist, but cache reuse is not
itself an optimality theorem.

## E. Layered candidate assembly

The generator includes an identity source state, zero-pivot destination
completion, pivot-depth accounting, explicit selected-pivot traversal,
temporal connector joins, residual budget restriction, path conflict checks,
canonical descriptors, and duplicate/dominance handling. It distinguishes
the root departure domain from induced component-entry domains: a prefix is
restricted by residual lower bounds, then its arrival image supplies a
connector request domain.

The domain-sensitive cache and candidate/fragment descriptors retain temporal
information in the active code. Tests cover continuous domains, repeated
entry-time behavior, path conflicts, parallel arcs, identity connectors, and
zero-pivot cases. The broader claim that all feasible complete paths are
preserved remains conditional on the corridor, connector enumeration, depth,
and resource completion guarantees.

## F. Bounded state retention

PACE-B's frontier compressor applies a retention bound per endpoint/depth/cell
and includes deterministic representative selection. It also has safe
dominance and configured metrics such as champion score/arrival/length/path
identity, coverage and fill behavior. The prior audit found that the active
representative policy is not the manuscript's single tuple. It must not be
called an exact dominance rule. Retention is a heuristic policy bounded by
`K_f`; it can discard candidates needed for globally optimal profiles.

Event cells and isolated times are represented by endpoint-aware domains and
are covered by envelope/oracle tests. That is implementation regression
evidence, not proof that all retained states satisfy a manuscript-level
optimality theorem.

## G. Replay and envelope construction

Materialized candidates are replayed against original temporal functions,
validated for budget and structural simplicity, deduplicated, and processed by
the deterministic envelope extractor. The extractor identifies comparison
events, evaluates singleton cells, respects the stable path ranking, and
produces maximal cells over the supplied registry/domain. The 1,009-case
independent oracle confirms cell boundaries, endpoint ownership, singleton
events, feasibility, and selected paths on tractable micro-instances.

The material replay domain is the key limitation: the active layered generator
passes an admitted final/expansion root domain to replay, rather than
automatically replaying every candidate across the complete original query
interval. The envelope may span the root query domain, but that does not prove
that every candidate was evaluated over all of it. Claims of exactness are
therefore valid only relative to the generated registry and its admitted
domains.

## H. PACE-X exactness

PACE-X can use exhaustive pivot selection and connector enumeration, and the
source has an effective depth based on selected-pivot count. Completion and
exactness are separate status fields. `PaceGenerationResult` rejects global
certification when generation is incomplete/capped, and result validation
rejects resource-limited PACE-X records marked globally certified.

The independent oracle evidence is strong but bounded: 1,009 deterministic
micro-instance full-profile comparisons agree. The controlled NY-Exact/NY-CTRL
records are a separate workload-level certificate scope. Neither establishes
global exactness on an entire large NY/FLA/CAL network. A numerical match on a
fixture cannot be promoted to a mathematical exactness claim.

## I. Experimental and case-study claims

The matrix records platform, dataset, temporal input, query-generation,
controlled-reference, successive-restriction, large-network, sensitivity, and
NYC findings. The central evidence limitations are:

- hardware cannot be established from Java source alone;
- current defaults do not prove historical settings;
- raw large-network records show a PACE-B 10-second internal limit and FLA
  completed-query medians above five seconds in the revised audit;
- raw policy-study score gaps do not support every manuscript-printed target
  value;
- L/K_f sensitivity evidence includes 8 in stored frozen data while some
  manuscript prose reportedly lists only 1, 2, 4;
- window sensitivity raw metadata records rho=0.10 at 240/360 minutes while
  the author has identified those labels as reporting errors; raw metadata is
  preserved and the correction is not silently applied;
- the NYC displayed example is reproducibly identified, but its real-data
  PACE-X subset certified zero queries, so interval-best is registry-scoped,
  not a global exactness result.

## Safe scientific summary

The code supports a deterministic continuous temporal profile implementation,
strong small-instance differential tests, and a bounded candidate-envelope
workflow. PACE-X can be globally certified only for a completed qualifying
execution scope. PACE-B selects the best path among generated/retained
candidates and has no global-optimality guarantee. The manuscript must be
provided and reconciled with the implementation before these findings can be
converted into submission claims.
