#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUN_ID="${1:-}"
if [[ -z "$RUN_ID" ]]; then
  echo "Usage: $0 RUN_ID" >&2
  echo "This reporting-only workflow consumes an existing artifact run; it does not run routing." >&2
  exit 2
fi
exec python3 "$ROOT/experiments/scripts/summarize_results.py" \
  --config "$ROOT/experiments/configs/paper_q1.yaml" --run-id "$RUN_ID"
