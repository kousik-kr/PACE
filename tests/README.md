# Artifact tests

The Java regression and independent-oracle tests remain in `src/test/java` so
they are compiled by Maven. The package-level integrity check is
`python3 scripts/validation/artifact_integrity.py` and checks required files,
excluded private/binary inputs, and machine-specific absolute paths.

The test suite is evidence about the implementation and its tested fixtures;
passing tests do not establish the manuscript's mathematical or experimental
claims globally.
