# Reproducibility guide

## What this package can establish

The package independently builds the Java implementation, runs its existing
regression suite, runs an independent continuous oracle on tractable
micro-instances, and processes supplied small historical summaries. It does
not establish that the missing manuscript's proof text matches the code, that
the unavailable historical commit was used, or that the large-network results
can be regenerated from the excluded road-network inputs.

PACE-X and PACE-B share profile/replay/envelope code but differ in candidate
generation and retention. PACE-X may receive a global certification status
only after a complete qualifying exhaustive execution. PACE-B chooses the best
path among its generated/retained candidates; it does not guarantee global
optimality. iSCOPE's historical reported runtime must be treated according to
the stored measurement boundary; the active source interleaves profiling and
envelope updates with search.

## Clean-workspace use

The package is self-contained for Level 1/2 Java work. From its root:

```bash
./scripts/setup/verify_environment.sh
./scripts/setup/build.sh
./scripts/validation/artifact_integrity.py
./scripts/validation/oracle.sh
```

No command above reads the original repository. The package does not depend on
personal absolute paths, and its data directories contain metadata/manifests,
not road-network binaries or private downloads.

## Evidence classes

1. **Implementation evidence**: Java source and tests in this package.
2. **Independent correctness evidence**: `results/reference/oracle_validation/`
   and its source provenance/validation summary.
3. **Historical measurement evidence**: relative source mappings and checksums
   in `provenance/RESULT_PROVENANCE.csv` and `SHA256SUMS.txt`; bulk raw files
   remain in the original tree and are not silently reconstructed.
4. **Derived reporting evidence**: plot data, tables, and supplied figures in
   `results/` and `figures/`, explicitly marked as historical/supplied.

These classes are not interchangeable. A test pass is not a measured runtime;
a stored table is not an independently regenerated experiment; and an oracle
fixture is not a large-network optimality proof.

## Known reproduction gaps

- Authoritative manuscript and bibliographic metadata are missing.
- No Git commit/history exists in the audited source tree.
- Large third-party/derived road-network and NYC input data are not included.
- Several historical raw result trees are excluded for size and contain
  machine-specific metadata that must be normalized before release.
- The active code/paper mismatches listed in the claim matrix remain unresolved.
- The stored large-network raw audit does not support an unqualified common
  five-second PACE-B/iSCOPE comparison.
