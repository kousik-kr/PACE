#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ ! -d "$ROOT/case_studies/nyc_shuttle/v2/processed/NYC-REAL-V2" ]]; then
  echo "Required NYC processed input is absent; download/prepare it first." >&2
  exit 2
fi
cat >&2 <<'EOF'
The NYC workflow is a separate, data-download-dependent case study. The
artifact includes manifests, scripts, provenance, and supplied outputs, but
does not redistribute the third-party road/traffic/transit inputs. Download
them according to case_studies/nyc_shuttle/README.md before running.
EOF
exec python3 "$ROOT/case_studies/nyc_shuttle/scripts/build_reports.py" "$@"
