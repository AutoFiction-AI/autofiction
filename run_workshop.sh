#!/usr/bin/env bash
# workshop harness: premise-tailored, professional-writer pipeline.
#
# A standalone novel harness for the premise in exp/longer.txt. Mirrors a
# real writer's process: research, blueprint, outline, voice trial, drafting,
# three editing passes (structural, character/theme, line), final read,
# final polish. See docs/workshop_harness.md.
#
# Dry-run (no provider calls, produces stub artifacts end-to-end):
#   ./run_workshop.sh --dry-run
#
# Live (requires `claude` CLI on PATH or $CLAUDE_BIN):
#   ./run_workshop.sh
#
# Custom run directory:
#   ./run_workshop.sh --run-dir runs/my_book
#
# Resume from a stage:
#   ./run_workshop.sh --start-stage revise_line

set -euo pipefail

cd "$(dirname "$0")"

DRY_RUN=0
EXTRA_ARGS=()
RUN_DIR_DEFAULT="runs/workshop_demo"

for arg in "$@"; do
  case "$arg" in
    --dry-run)
      DRY_RUN=1
      EXTRA_ARGS+=("--dry-run")
      ;;
    *)
      EXTRA_ARGS+=("$arg")
      ;;
  esac
done

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[workshop] dry-run: provider calls disabled; producing stub artifacts."
fi

python3 scripts/workshop_runner.py \
  --premise-file exp/longer.txt \
  --run-dir "$RUN_DIR_DEFAULT" \
  --model claude-opus-4-7 \
  --reasoning max \
  ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}
