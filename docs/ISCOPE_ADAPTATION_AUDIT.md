# iSCOPE-Profile adaptation audit

## Scope

The iSCOPE baseline is audited independently of PACE. The authoritative
manuscript is missing, so the intended protocol below is taken from the task
specification and checked against `src/main/java/edu/ipcmax/experiments/algorithms/IScopeAlgorithm.java`,
`AlgorithmConfig`, `PaceBench`, stored T03 records, and the prior repository
audit.

## Executed implementation

`AlgorithmRegistry` creates `IScopeAlgorithm`. Its run path:

1. obtains the configured query deadline, defaulting to five seconds;
2. reserves up to one second for finalization;
3. prepares a static lower-bound graph and computes a source-to-destination
   witness;
4. streams complete vertex-simple paths through `SimplePathSearch`;
5. replays each complete path over the query departure domain using
   `ExactPathProfileBuilder.budgetContext`;
6. commits accepted profiles to a `CommittedScoreEnvelope` while the search is
   still running; and
7. returns `TIME_CAPPED_NOT_CERTIFIED` when the deadline/path cap prevents
   exhaustive completion.

Partial paths are not profiled as destination labels. Cancelled or partial
profiles are discarded. Duplicate stable path-ID sequences are removed.

## Continuation and replacement semantics

The code does not maintain an explicit “previous selected label” variable or a
separate continuation state. `CommittedScoreEnvelope.commit` retains the
currently selected path candidates from the existing envelope, adds the new
candidate, and re-runs `EnvelopeExtractor` over that set. At each cell the
extractor applies the active comparator: higher score, shorter travel time,
fewer edges, then lexicographically smaller stable edge-ID sequence.

This means the observed implementation is an incremental best-envelope over
the paths discovered so far. A prior winner remains selected where it remains
the best in the current registry; it can be replaced when a newly discovered
candidate wins. That is behaviorally related to the manuscript's continuation
description, but it is not implemented as an explicit “continue until
infeasible, then choose a replacement” state machine. Replacement can also be
affected by the order and set of fully profiled paths discovered before the
deadline.

Status: **PARTIALLY_VERIFIED**. The manuscript's exact continuation rule,
tie-resolution description, and uncovered-domain notation cannot be checked
without the manuscript and a source-identity-bound baseline revision.

## Domain coverage and interruption

`CommittedScoreEnvelope` is initialized on the complete query departure
domain, and each accepted path is replayed on the query domain. The final
profile can still contain unresolved/uncovered cells because the path search is
cut off. The code labels the run as time-capped/not certified; it does not
convert a partial envelope into a global optimum.

For a time-capped run, the profile contains only paths accepted before the
deadline. Search interruption can therefore affect both coverage and the
selected path. The result status and exactness scope are the authoritative
interpretation; a nonempty profile is not a completed response.

## Runtime boundaries

The intended historical protocol says both methods use 24 workers, iSCOPE gets
the departure interval, search stops at five seconds, final profile
construction occurs afterward, and iSCOPE's reported time excludes final
profile construction while PACE-B's includes its full pipeline.

The source does not match that wording exactly:

- `IScopeAlgorithm` uses a deadline, but it profiles paths and updates the
  envelope during the deadline-controlled search.
- Its `algorithm_total` timing is set after the run and includes lower-bound
  preprocessing, streamed search, path profiling, and envelope commits.
- Finalization reserve is part of the deadline policy; it is not an independent
  post-search profile phase.
- Stored T03 configuration/provenance records identify 24-worker general
  protocol metadata, but the active baseline source itself does not establish
  that every historical process used 24 workers.
- The stored final-publication audit reports iSCOPE as a five-second-capped
  method while the canonical PACE-B T03 batches used a ten-second PACE-B
  internal limit. This is not a common five-second end-to-end runtime
  protocol.

Status: **CONTRADICTED** for the claim that the source implements a separate
post-cutoff profile-construction phase and search-only timing boundary;
**PARTIALLY_VERIFIED** for the existence of a five-second iSCOPE deadline and
time-capped status.

## Full-window score and unresolved portions

`IScopeAlgorithm.coverage` computes found-duration over the query domain. The
final metric fields are then processed by the shared experiment framework.
The repository's Java `ProfileSupport.averageSelectedScore` uses resolved
feasible measure as its denominator. Frozen T03 audit code separately
zero-fills unresolved portions for a full-window score. These are different
quantities and must not be compared without naming the calculation.

## Reproducible baseline diagnostic

A common-selection-rule diagnostic can be run separately on stored complete
path profiles:

1. use the same query manifest and graph temporal inputs for both methods;
2. retain only fully generated destination paths available before the iSCOPE
   cutoff;
3. materialize their profiles over the same departure interval;
4. apply the shared score/travel-time/edge-count/stable-ID comparator; and
5. report search time, profile construction time, complete-response time,
   coverage, and full-window score as separate fields.

This is a diagnostic, not a replacement for historical iSCOPE results. It is
not injected into the published baseline or used to edit historical tables.
The artifact provides the existing result schemas and reporting scripts but
does not run the diagnostic automatically because the necessary large inputs
and raw result batches are excluded.

## Required author decisions

1. Provide the authoritative corrected manuscript and identify its version.
2. Provide the source revision and exact baseline commit used for the reported
   iSCOPE/PACE-B experiments.
3. Confirm whether reported iSCOPE runtime is search-only, complete-response,
   or a separately measured phase, and supply raw timing fields.
4. Confirm the worker/process protocol and whether final profile construction
   was included in either method's reported runtime.
5. Reconcile the common five-second claim with the stored PACE-B ten-second
   T03 configuration and FLA time audit.
