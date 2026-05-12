# Interactive Harness

`scripts/interactive_runner.py` is a thin wrapper around
`scripts/runner.py`'s `NovelPipelineRunner` that inserts human checkpoints
into the otherwise unattended pipeline. It is intended for hands-on
authoring sessions where you want to read each stage's output before the
next stage runs.

## What changes vs. the standard runner

Everything else (premise resolution, outline review cycles, audits,
revision aggregation, continuity reconciliation, gate writing) is
unchanged. The wrapper:

- Forces serial chapter drafting (one chapter at a time) so each can be
  inspected before the next is produced. The `--max-parallel-drafts`
  flag is honoured by the parent but the subclass only ever submits one
  draft job at a time.
- Pauses at four checkpoint boundaries:
  1. After the outline stage (outline + scene plan + style bible +
     spatial layout).
  2. After **each** chapter draft.
  3. After each cycle's chapter-review stage (all per-chapter
     `chapter_*.review.json` files for the cycle).
  4. After each cycle's revision stage (per-chapter revision reports +
     the post-revision novel snapshot).
- At each checkpoint, asks you to type a free-text annotation in the
  terminal (terminate with a single `.` on its own line or Ctrl-D).
- Sends the annotation to a small Claude CLI call which classifies it
  into one of `continue` / `revise` / `rewrite`.
- On `continue`: proceeds.
- On `revise` or `rewrite`: invalidates the just-produced artifact,
  stores the annotation as a `<human_editor_notes>` block, and re-runs
  that stage. The block is appended to the relevant stage prompt the
  next time it is rendered, so the agent sees your guidance verbatim.
- Persists every annotation to `<run_dir>/annotations/<key>.md` for
  later inspection.

The decision LLM uses `$CLAUDE_BIN` or whichever `claude` binary is on
`PATH`. If neither is available or the call fails, the harness falls
back to a manual `c / r / w` prompt.

## Usage

```bash
# Same provider config as run_novel.sh; pauses at each checkpoint.
./run_novel_interactive.sh

# Smoke variant: outline + first chapter only.
SMOKE_TEST=1 ./run_novel_interactive.sh
# (or pass --smoke as the first argument)
```

You can also invoke the Python entrypoint directly with any of the
flags accepted by `scripts/runner.py`:

```bash
python3 scripts/interactive_runner.py --help
```

## Checkpoint UX

```
========================================================================
INTERACTIVE CHECKPOINT: chapter_draft:ch01
========================================================================
run_dir: /abs/path/to/runs/your_run
Drafted chapters/ch01.md.

Read these files (paths relative to run_dir):
  - chapters/ch01.md

Type your free-text annotation about what works and what does not. Be
specific. Empty input is interpreted as 'continue'.
End your annotation with a line containing only `.` (a single period)
or press Ctrl-D.
========================================================================
The scene establishes Mara well but the dialogue with Ben feels stagey.
The bar setting works. Please tighten the second half.
.
[interactive] decided action: revise
```

The harness will then delete `chapters/ch01.md`, append your note to the
draft prompt as `<human_editor_notes>`, and rerun the draft job. The
loop continues until you accept (empty annotation or a note the
decision LLM reads as `continue`).

## Scope limitations

- The wrapper does not pause inside the outline-review cycles, audits,
  or aggregation steps. Those run as in the standard pipeline.
- Per-chapter review pauses are not implemented (the harness pauses
  once per cycle after all chapter reviews complete). If you want
  per-chapter review pauses, force `--max-parallel-reviews 1` and read
  the JSONL job logs as they are written.
- `--add-cycles` resume mode bypasses interactive checkpoints; it is
  treated as a passthrough to the parent runner.
