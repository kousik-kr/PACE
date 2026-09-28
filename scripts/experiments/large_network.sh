#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ "${PACE_ARTIFACT_RUN_EXPENSIVE:-0}" != "1" ]]; then
  cat >&2 <<'EOF'
Large-network reproduction is intentionally opt-in and was not run during
audit. It requires licensed/reconstructed NY, FLA, and CAL inputs, a reviewed
24-worker configuration, and substantial memory/time.
EOF
  exit 2
fi
CONFIG="${1:-$ROOT/experiments/configs/paper_q1_server_24c_250g_5s.yaml}"
exec python3 "$ROOT/experiments/scripts/run_all.py" \
  --config "$CONFIG" \
  --run-id "${PACE_ARTIFACT_RUN_ID:-large-network-$(date +%Y%m%d-%H%M%S)}" \
  --stages preflight,build,queries,plan,main,collect,validate,summarize
