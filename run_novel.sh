#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 "$SCRIPT_DIR/scripts/runner.py" \
  --max-parallel-drafts 6 \
  --max-parallel-reviews 6 \
  --max-parallel-revisions 6 \
  "$@"
