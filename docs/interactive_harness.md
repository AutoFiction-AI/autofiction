# Interactive Harness

`scripts/interactive_runner.py` is a thin wrapper around
`scripts/runner.py`'s `NovelPipelineRunner` that inserts human checkpoints
into the otherwise unattended pipeline. It is intended for hands-on
authoring sessions where you want to read each stage's output before the
next stage runs.

## What changes vs. the standard runner

The LLM outline review/revision cycles are suppressed (the human
checkpoint after the outline stage *is* the review). Everything else
(premise resolution, audits, revision aggregation, continuity
reconciliation, gate writing) is unchanged. The wrapper:

- Forces serial chapter drafting (one chapter at a time) so each can be
  inspected before the next is produced. The `--max-parallel-drafts`
  flag is honoured by the parent but the subclass only ever submits one
  draft job at a time.
- Pauses at four checkpoint boundaries:
  1. After the outline stage (outline + scene plan + style bible +
     spatial layout). The automatic LLM `outline_review` /
     `outline_revision` cycles are skipped in interactive mode; your
     free-text annotation drives any rerun of the outline itself.
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

Every checkpoint prints, in order:

1. **DIGEST** — a pre-read summary of the artifact(s) you would
   otherwise have to open by hand. Stage-specific:
   - *outline*: word count of `outline.md`, the extracted chapter list,
     scene count from `scene_plan.tsv`, character list from
     `style_bible.json`, location count from `spatial_layout.json`.
   - *chapter draft*: word count, line count, rough scene-break count,
     and head/tail excerpts.
   - *chapter review cycle*: per-chapter verdict line, severity counts
     (CRITICAL / HIGH / MEDIUM), the top findings by severity (with
     source and a one-sentence problem clip), and the review summary.
   - *revision cycle*: per-chapter `FIXED / PARTIAL / UNRESOLVED`
     counts, post-revision word count, the first couple of unresolved
     revision notes, and the merged-pass summary.
2. **DIFF vs. prior version** — only rendered if a prior version is
   available. The prior comes from either (a) the just-rejected
   artifact (captured before invalidation, so a second pass shows what
   actually changed) or (b) cycle N-1's artifact on disk for
   review/revision stages. For chapter drafts and the outline this is a
   short unified text diff (capped at 80 lines); for reviews it shows
   verdict flips and finding-id deltas; for revisions it shows the
   `FIXED/PARTIAL/UNRESOLVED` transitions.
3. **Raw files** — the same file list as before, but indexed `[1]`,
   `[2]`, … so you can dump any one of them inline without leaving the
   prompt.

While typing your annotation you can use slash commands instead of
opening a separate editor:

| Command | Effect |
| --- | --- |
| `/r N` or `/read N` | Dump raw file `[N]` inline (JSON is pretty-printed). |
| `/r <path>` | Dump a specific run-relative file. |
| `/list` | Re-show the indexed file list. |
| `/help` | Show this command list. |
| `.` (alone on a line) or Ctrl-D | Finish the annotation. |

A line starting with `/` is treated as a command and is not added to
your annotation. Lines that do not start with `/` are accumulated and
sent to the decision LLM verbatim.

```
========================================================================
INTERACTIVE CHECKPOINT: chapter_draft:chapter_01
========================================================================
run_dir: /abs/path/to/runs/your_run
Drafted chapters/chapter_01.md.

--- DIGEST ---
chapters/chapter_01.md: 3,227 words, 152 lines, ~0 scene breaks  (Δ +180 words vs. prior)

head:
  > # Chapter 1
  > Coffee still clung to the apartment.
  > It wasn't fresh coffee. Nahla had been dead nine days...
  > ...

tail:
  > Again he reached for the first breath of Al-Fatiha...

--- DIFF vs. prior version ---
--- chapters/chapter_01.md (prior)
+++ chapters/chapter_01.md (current)
@@ -21,5 +21,5 @@
 ...

Raw files (paths relative to run_dir):
  [1] chapters/chapter_01.md

Commands while typing your annotation: ...
========================================================================
/r 1
... (full chapter dumped) ...
The first breath beat is now clearer; the second half still rushes
the failed-recitation close. Tighten lines 120–140.
.
[interactive] decided action: revise
```

The harness will then delete `chapters/chapter_01.md`, append your note
to the draft prompt as `<human_editor_notes>`, and rerun the draft job.
On the second pass the DIFF section shows exactly what the model
changed in response to your notes.

## Scope limitations

- The LLM outline-review and outline-revision cycles do not run in
  interactive mode; the wrapper forces `skip_outline_review=True`.
  Audits, aggregation steps, and per-cycle chapter-review/revision
  stages still run as in the standard pipeline.
- Per-chapter review pauses are not implemented (the harness pauses
  once per cycle after all chapter reviews complete). If you want
  per-chapter review pauses, force `--max-parallel-reviews 1` and read
  the JSONL job logs as they are written.
- `--add-cycles` resume mode bypasses interactive checkpoints; it is
  treated as a passthrough to the parent runner.
