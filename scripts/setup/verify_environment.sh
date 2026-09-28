#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
echo "artifact_root=$ROOT"
command -v java >/dev/null || { echo "ERROR: Java is required" >&2; exit 1; }
command -v mvn >/dev/null || { echo "ERROR: Maven is required" >&2; exit 1; }
command -v python3 >/dev/null || { echo "ERROR: Python 3 is required for reporting drivers" >&2; exit 1; }

JAVA_VERSION="$(java -version 2>&1 | sed -n '1p')"
MAVEN_VERSION="$(mvn -version | sed -n '1p')"
PYTHON_VERSION="$(python3 --version 2>&1)"
echo "$JAVA_VERSION"
echo "$MAVEN_VERSION"
echo "$PYTHON_VERSION"

if ! java -version 2>&1 | grep -Eq 'version "21([.]|$)'; then
  echo "ERROR: Java 21 is required by pom.xml" >&2
  exit 1
fi
echo "environment=PASS"
