#!/usr/bin/env bash
set -euo pipefail

# Interactive mirror of run_novel.sh.
#
# Drives the same pipeline but pauses for human annotation after the
# outline stage, after every chapter draft, after each cycle's chapter
# review stage, and after each cycle's revision stage. At every pause
# the harness asks you to read the produced artifacts and type free-text
# notes; a small LLM call (via the local `claude` CLI) classifies the
# note as continue / revise / rewrite and the harness loops accordingly.
# Notes are also injected into the next render of the relevant prompt as
# a <human_editor_notes> block.
#
# Provider configuration mirrors run_novel.sh. Tweak below as needed.

SMOKE_TEST="${SMOKE_TEST:-0}"
if [[ "${1:-}" == "--smoke" ]]; then
  SMOKE_TEST=1
  shift
fi

SMOKE_ARGS=()
if [[ "${SMOKE_TEST}" == "1" ]]; then
  SMOKE_ARGS=(
    --max-chapters 1
    --run-dir runs/smoke_chapter1_interactive
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
python3 scripts/interactive_runner.py \
  --premise-file "exp/benjamin.txt" \
  --run-dir runs/vel_interactive_latest \
  --min-cycles 4 \
  --max-cycles 4 \
  --outline-review-cycles 2 \
  --max-parallel-drafts 1 \
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
