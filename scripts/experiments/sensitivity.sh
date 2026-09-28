#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ "${PACE_ARTIFACT_RUN_EXPENSIVE:-0}" != "1" ]]; then
  cat >&2 <<'EOF'
Sensitivity reproduction is intentionally opt-in and was not run during audit.
Supply the required graph variants/manifests, then review the selected config
before setting PACE_ARTIFACT_RUN_EXPENSIVE=1.
EOF
  exit 2
fi
CONFIG="${1:-$ROOT/experiments/configs/paper_q1.yaml}"
exec python3 "$ROOT/experiments/scripts/run_all.py" \
  --config "$CONFIG" \
  --run-id "${PACE_ARTIFACT_RUN_ID:-sensitivity-$(date +%Y%m%d-%H%M%S)}" \
  --stages preflight,build,queries,plan,sensitivity,collect,validate,summarize --study T05
