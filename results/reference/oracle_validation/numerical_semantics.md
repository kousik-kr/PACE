# Numerical semantics

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
