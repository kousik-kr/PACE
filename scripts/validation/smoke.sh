#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
mvn -f "$ROOT/pom.xml" -q -Dtest='*Test' test
java -cp "$ROOT/target/classes" edu.ipcmax.experiments.PaceCli --demo --algorithm pace-x
echo "smoke=PASS"
