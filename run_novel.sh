#!/usr/bin/env bash
set -euo pipefail

CODEX_BIN=/Applications/Codex.app/Contents/Resources/codex \

python3 scripts/runner.py \
  --premise-file "exp/the_unwritten_room/benjamin.txt" \
  --run-dir runs/vel_4cycle_retry_latest \
  --min-cycles 4 \
  --max-cycles 4 \
  --outline-review-cycles 1 \
  --max-parallel-drafts 6 \
  --max-parallel-reviews 6 \
  --max-parallel-revisions 6 \
  --validation-mode lenient \
  --local-window-size 4 \
  --local-window-overlap 2 \
  --provider codex \
  --outline-provider claude \
  --outline-revision-provider claude \
  --draft-provider claude \
  --review-provider codex \
  --full-review-provider claude \
  --cross-chapter-audit-provider claude \
  --local-window-audit-provider codex \
  --revision-provider codex \
  --revision-dialogue-provider claude \
  --aggregation-provider claude