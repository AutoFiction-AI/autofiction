#!/usr/bin/env bash
set -euo pipefail

# Smoke-test mode: only generate / review / revise the first chapter.
# Toggle with `SMOKE_TEST=1 ./run_novel.sh` (or pass `--smoke` as the first arg).
# The full outline is still generated and reviewed for the whole book; only the
# per-chapter draft/review/revision pipeline is capped. Whole-novel audits that
# require multiple chapters are skipped automatically.
SMOKE_TEST="${SMOKE_TEST:-0}"
if [[ "${1:-}" == "--smoke" ]]; then
  SMOKE_TEST=1
  shift
fi

SMOKE_ARGS=()
if [[ "${SMOKE_TEST}" == "1" ]]; then
  SMOKE_ARGS=(
    --max-chapters 1
    --run-dir runs/smoke_chapter1
    --skip-cross-chapter-audit
    --skip-local-window-audit
    --skip-plot-architecture-audit
    --skip-character-arc-audit
    --skip-ending-audit
    --skip-prose-distinctiveness-audit
    --skip-theme-coherence-audit
    --skip-cold-reader-pass
  )
fi

CODEX_BIN=/Applications/Codex.app/Contents/Resources/codex \
\
python3 scripts/runner.py \
  --premise-file "exp/longer.txt" \
  --run-dir runs/vel_4cycle_retry_latest \
  --min-cycles 4 \
  --max-cycles 4 \
  --outline-review-cycles 2 \
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
  --aggregation-provider claude \
  ${SMOKE_ARGS[@]+"${SMOKE_ARGS[@]}"}
