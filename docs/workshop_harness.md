# Workshop Harness

A premise-tailored novel pipeline. Standalone from `scripts/runner.py`.

Built for the premise in `exp/longer.txt`: a single literary novel about an
Indigenous Latin American cult-leader-turned-dictator across the arc of his
life, ending on the question of whether a lie inhabited long enough can
become true.

The harness is designed around how a professional writer actually works on
a difficult novel: gather the subject, decide the world, plan the book,
trial a voice, draft each chapter, then read the whole thing through three
discrete editorial lenses, revising once after each read, before a final
read-through and a polish pass.

## Stage graph

```
research            ─▶ research/dossier.md
blueprint           ─▶ blueprint/bible.md
outline             ─▶ outline/outline.md
voice_trial         ─▶ voice/{trial_a,trial_b,choice,style_guide}.md
draft               ─▶ drafts/v1/chapter_NN.md            (per chapter)
read_structural     ─▶ reads/v1_structural_notes.md
revise_structural   ─▶ drafts/v2/chapter_NN.md            (per chapter)
read_character_theme─▶ reads/v2_character_theme_notes.md
revise_character_theme─▶ drafts/v3/chapter_NN.md          (per chapter)
read_line           ─▶ reads/v3_line_notes/chapter_NN.md  (per chapter)
revise_line         ─▶ drafts/v4/chapter_NN.md            (per chapter)
final_read          ─▶ reads/v4_final_notes.md
final_polish        ─▶ manuscript/{chapter_NN,colophon,full}.md
```

Each editorial read-and-revise cycle has a distinct lens, so the revision
work does not collapse into "make it better" but instead asks one
question at a time:

1. **Structural.** Does the story actually happen? Are scenes in the right
   chapters, in the right order, with real causal links? Does the ending
   carry the load? Continuity across the manuscript.
2. **Character & theme.** Is the protagonist a person, not a symbol? Do
   the heritage and doubt threads track behaviorally across the book?
   Are supporting characters alive? Does the closing image carry the
   premise's question without speaking it?
3. **Line.** Sentence by sentence: tics, dialogue authenticity, image
   work, sanitization slips, scene endings. Per chapter, with an
   acceptance test the reviser self-checks against.

The final read is one last cold pass that catches seams, regressions, and
the placement of the last paragraph. Final polish applies that read's
notes and assembles the manuscript.

## Why fewer stages than `runner.py`

The existing pipeline has many specialized audits (scene consistency,
dialogue diagnostic, cold reader, plot architecture, character arc,
ending, prose distinctiveness, theme coherence, cross-chapter,
local-window). That breadth is appropriate for the research pipeline,
which is studying which audits catch which failure modes.

This harness is not a research instrument. It is a writer's process. The
three editorial lenses cover what a senior editor on a single book would
do, and they keep each revision pass narrow enough that the reviser does
not slide into the workshop-polish failure mode the constitution warns
against. The audits in `runner.py` are not redundant — they have caught
real failure modes — but they are a different kind of tool.

## Running

Dry-run (no provider calls; produces stub artifacts so the orchestration
itself can be exercised):

```bash
./run_workshop.sh --dry-run
```

Live (requires `claude` CLI on PATH or `$CLAUDE_BIN`):

```bash
./run_workshop.sh
```

Custom run directory:

```bash
./run_workshop.sh --run-dir runs/my_book
```

Resume from a stage (after a failure or a deliberate break):

```bash
./run_workshop.sh --start-stage revise_line
```

Stop at a stage (e.g. for inspecting outputs before committing to a
revision pass):

```bash
./run_workshop.sh --start-stage research --stop-stage voice_trial
```

Default model is `claude-opus-4-7` at `--effort max`, matching the
documented recommended configuration in the project README. Override
with `--model` and `--reasoning` if needed.

## Dry-run behavior

`--dry-run` writes deterministic stub artifacts in place of provider
calls. Chapter files include the required `# Chapter N — Title`
heading so downstream stages have a parseable file to read. The
shared aesthetic is materialized into the run directory either way
(with the premise inlined), as is a `config/harness_manifest.json`
recording the stages, model, and run metadata. This lets the
orchestration be smoke-tested end-to-end and lets a future stage be
written and exercised without paying provider costs.

## Run directory layout

```
<run-dir>/
├── config/
│   ├── 00_shared_aesthetic.md   # premise inlined; binding aesthetic
│   ├── premise.txt
│   └── harness_manifest.json
├── research/
│   └── dossier.md
├── blueprint/
│   └── bible.md
├── outline/
│   └── outline.md
├── voice/
│   ├── trial_a.md
│   ├── trial_b.md
│   ├── choice.md
│   └── style_guide.md
├── drafts/
│   ├── v1/chapter_NN.md   # initial draft
│   ├── v2/chapter_NN.md   # after structural revision
│   ├── v3/chapter_NN.md   # after character & theme revision
│   └── v4/chapter_NN.md   # after line revision
├── reads/
│   ├── v1_structural_notes.md
│   ├── v2_character_theme_notes.md
│   ├── v3_line_notes/chapter_NN.md
│   └── v4_final_notes.md
├── manuscript/
│   ├── chapter_NN.md
│   ├── colophon.md
│   └── full.md            # the assembled book
└── logs/
    ├── runner.log
    ├── prompts/<job>.md   # the exact prompt sent to each agent
    └── jobs/<job>.{jsonl,stderr.txt}
```

## Worker isolation

Each stage is one `claude` CLI invocation with `cwd` set to the run
directory. The prompt frame lists declared inputs (read these) and
declared outputs (write exactly these). Outputs are verified to exist
after each live job; missing outputs fail the run.

The harness does not enforce the same worktree-style isolation
`runner.py` uses (per-job ephemeral workspace, copy in / copy out). The
working assumption here is that a single book project is being built in
one run directory and stages write only within their declared output
prefixes. If you need stronger guarantees, wrap each job in a worktree
or restrict via filesystem permissions.

## Resumability and checkpoints

The orchestrator checkpoints at **job granularity**, not stage
granularity. Before each job runs, the harness checks whether every
declared output for that job already exists and is non-empty. If yes,
the job is skipped (`job_skip_already_done` in the runner log).

This makes partial-stage failures cheap to recover from. If chapter 7
of 15 fails during line revision, just rerun the same command:

```bash
./run_workshop.sh
```

Chapters 1–6 and 8–15 are skipped (their `drafts/v4/chapter_NN.md`
already exists); only chapter 7 is regenerated. The same logic
applies to the global stages — a successful research dossier will
not be redone on a rerun. Combine with `--start-stage` for
deliberate restart points.

To redo work even when outputs exist, pass `--force`:

```bash
./run_workshop.sh --force                 # redo everything
./run_workshop.sh --start-stage revise_line --force   # redo line revision and on
```

The simplest "I want to start over" recovery is to delete the run
directory and rerun. To selectively redo specific chapters, delete
their output files and rerun without `--force`.

## Rate-limit handling

If a live job fails and the failure looks like a rate-limit rejection
(either claude's structured `rate_limit_event` with status `rejected`,
or any free-text marker — `429`, `rate limit`, `quota`, `usage limit`
— in the JSONL log or stderr), the harness:

1. Parses the `resetsAt` epoch from the rate-limit event (when present).
2. Computes a sleep duration: `(resetsAt - now) + 120s buffer + 0–30s
   jitter`. If no `resetsAt` is available, falls back to
   `--rate-limit-wait` seconds (default 600).
3. Rotates the failed attempt's logs out of the way:
   `{job}.jsonl` → `{job}.attempt-N.jsonl` (same for stderr).
4. Sleeps with a 60-second heartbeat written to `runner.log` so you
   can see the harness is waiting and not hung.
5. Re-runs the same job from scratch.

Up to `--max-retries` retries per job (default 3) before propagating
the failure. Non-rate-limit failures (missing inputs, hard crashes,
genuine model errors) propagate immediately — only rate-limit-shaped
failures trigger the wait-and-retry path.

Default timeouts have been raised to accommodate heavy literary
stages: idle 30 minutes, wall 2 hours. Override with `--idle-timeout`
and `--wall-timeout` if needed. The blueprint and outline stages
(producing 5,000–8,000-word structured documents at max reasoning)
routinely stall between JSONL events for many minutes while the model
thinks; 10-minute idle timeouts are not enough.

## Live output streaming

During live runs, the harness tails each job's `stream-json` log as
it grows and prints human-readable progress to stdout: assistant
text, tool calls (`Read`, `Write`, `Edit`, `Bash` with their key
parameters), and the final result event (subtype, duration, token
counts). This gives you a live view of what the agent is doing in
each stage without having to tail the raw JSONL file yourself.

To suppress streaming (the JSONL logs are still written):

```bash
./run_workshop.sh --quiet
```

Streaming is best-effort: parse errors on individual events are
silently dropped, since the raw JSONL on disk
(`<run-dir>/logs/jobs/<job>.jsonl`) is the source of truth.

The `runner.log` lifecycle events (`stage_start`, `job_live_start`,
`job_skip_already_done`, etc.) continue to go to stderr regardless
of `--quiet`, so progress is always visible.

## What this harness does *not* do

- Multiple revision cycles. Each editorial lens runs once. If the
  final read flags survival of a structural or character problem, the
  expected response is a *new* run starting from the failed stage, not
  another cycle inside this harness.
- Provider mixing. Claude only. The premise rewards a writer that can
  hold a single voice across 50,000+ words; routing chapters through
  multiple models in one book risks voice drift.
- Audits in the `runner.py` sense. The line-read prompt absorbs the
  highest-leverage line-level audits (sanitization slip, scene-ending
  workshop tics, dialogue voice differentiation, prose tic counts)
  into a single per-chapter pass.

## File index

- `scripts/workshop_runner.py` — orchestrator.
- `prompts/workshop/00_shared_aesthetic.md` — premise-aware aesthetic
  binding for every stage.
- `prompts/workshop/01_research.md` through `13_final_polish.md` —
  per-stage prompts.
- `run_workshop.sh` — entrypoint.
- `tests/test_workshop_runner.py` — dry-run smoke coverage.
