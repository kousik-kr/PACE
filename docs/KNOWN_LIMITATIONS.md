# Known limitations and author blockers

## Scientific blockers

- Provide the latest corrected 25-page PACE manuscript or LaTeX source and its
  version. The repository currently contains neither.
- Provide the historical source commit/repository snapshot used for final
  reported experiments. The current Git repository has no commits.
- Reconcile EA/LD manuscript query-region prose with the active static-minimum
  corridor implementation.
- Reconcile integrated-score pivot ranking prose with the active maximum-score
  comparator.
- Define whether the paper means midpoint temporal fastest connectors, static
  lower-bound witnesses, or a connector portfolio for each PACE-B study.
- Correct unresolved/NO_PATH semantics, replay-domain claims, bounded-retention
  language, and PACE-X exactness scope.

## Experimental-evidence blockers

- Supply the complete historical raw result/manifests needed to regenerate
  reported tables, or approve a reporting-only release that clearly labels
  supplied figures/tables as non-reproduced.
- Reconcile the T03 PACE-B ten-second limit and FLA >5-second completed-query
  medians with the manuscript's common five-second comparison.
- Reconcile controlled and successive-policy raw score-gap recomputations with
  printed manuscript values.
- Confirm hardware, process isolation, workers, warmups, trials, limits, and
  seed handling from execution records rather than current defaults.
- Preserve raw rho=0.10 metadata at the 240/360 window points and add the
  author-confirmed reporting correction as a separately versioned note.

## Release/usability blockers

- Review redistribution rights for DIMACS-derived road networks, generated
  temporal data, NYC road/traffic data, and MTA/GTFS material.
- Approve a public license; this package includes only `LICENSE.PROPOSED.md` and
  grants no license.
- Supply verified authors/bibliographic information for `CITATION.cff`.
- Normalize historical absolute paths and stale figure/hash provenance before
  archive submission.

## Safe current claim

The current package is suitable for author review of implementation and
evidence limitations. It is not ready for an artifact claim that the paper's
scientific statements or all reported experimental values have been reproduced.
