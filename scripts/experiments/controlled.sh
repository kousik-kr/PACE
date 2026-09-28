#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ "${PACE_ARTIFACT_RUN_EXPENSIVE:-0}" != "1" ]]; then
  cat >&2 <<'EOF'
Controlled reproduction is intentionally opt-in and was not run during audit.
Set PACE_ARTIFACT_RUN_EXPENSIVE=1 after supplying the NY-Exact inputs and
reviewing configs/studies/t01_exactness_oracle.yaml.
EOF
  exit 2
fi
exec python3 "$ROOT/experiments/scripts/run_all.py" \
  --config "$ROOT/experiments/configs/paper_q1.yaml" \
  --run-id "${PACE_ARTIFACT_RUN_ID:-controlled-$(date +%Y%m%d-%H%M%S)}" \
  --stages preflight,build,exactness,collect,validate,summarize --study T01
