# Provenance policy

The artifact separates immutable historical evidence from derived reporting.
`provenance/RESULT_PROVENANCE.csv` maps manuscript figures/tables and case-study
outputs to relative source files, configurations, manifests, plotting scripts,
source identity, checksums, status, and limitations. `provenance/SHA256SUMS.txt`
records checksums for the included artifact files and selected original evidence
references.

The original repository has no commits, so `source_revision` is recorded as
`NO_GIT_COMMIT_WORKTREE_2026-09-28` rather than inventing a revision. Historical
files whose full content is not copied are referenced by their original relative
path and source checksum, and are never replaced with synthetic measurements.

The author-confirmed correction concerning rho metadata for the 240- and
360-minute window points is a provenance correction only. Raw metadata remains
unchanged in the original evidence; no stored result value is rewritten here.

The included publication figures are supplied historical outputs. A figure is
marked `REGENERABLE_FROM_INCLUDED_DATA` only where the corresponding plot data
and script are included and the source mapping supports that claim. Otherwise
it is marked `REPORTING_ONLY` or `UNVERIFIED`.
