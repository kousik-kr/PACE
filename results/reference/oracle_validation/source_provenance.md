# Source provenance

Audit date: 2026-08-25.

## Existing oracle sources

- `src/test/java/edu/ipcmax/testoracle/TinyContinuousEnvelopeOracle.java` — SHA-256 `6de0f756ddc8feefee025596569dce5e020b00bf2e1db7601279a6dab36a358a`. Independent continuous all-simple-path oracle.
- `src/test/java/edu/ipcmax/testoracle/ExactFraction.java` — SHA-256 `3317b7e6027c2efc07e1bd9d5b33f7f6657e8a0b4fc9ac0bd31a74e097133a28`. Exact rational support used only by the test oracle.
- `src/test/java/edu/ipcmax/testoracle/PaceExactOracleDifferentialTest.java` — SHA-256 `7730df5b79846ad0e38ef17f742ae293b17fdc2d17f7da2d4cb6a21d54ccf14c`. Nine explicit fixtures, 1,000 fixed-seed cases, and 64 PACE-X compression-equivalence cases.
- `src/test/java/edu/ipcmax/core/pcmax/PacePublicApiOracleIntegrationTest.java` — SHA-256 `9b8d01edd164090f47a4ccb3643a4643869d49a3ea6f502beb4252fc45a81c02`. Independent pointwise probes and public API checks.
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
