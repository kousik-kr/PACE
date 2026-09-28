# Code layout

The artifact is a standard Maven project at its root. Production Java source is
under `../src/main/java`, tests under `../src/test/java`, and the Maven build
file is `../pom.xml`. The `code/` directory is retained as a named inventory
location for the publication package; it contains no second copy of the source.

This layout is intentional: the copied experiment drivers use the standard
Maven paths, so the artifact can be built from a clean checkout without path
rewriting or links to the original repository.
