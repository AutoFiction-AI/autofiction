#!/usr/bin/env python3
"""
workshop_runner.py — a premise-tailored novel harness.

Built for the premise in `exp/longer.txt`: a single literary novel about an
Indigenous Latin American cult-leader-turned-dictator across the arc of his life.

The harness mirrors a professional writer's process:

    research -> blueprint -> outline -> voice trial ->
    draft (per chapter) ->
    structural read -> structural revise (per chapter) ->
    character & theme read -> character & theme revise (per chapter) ->
    line read (per chapter) -> line revise (per chapter) ->
    final read -> final polish

Each stage is one Claude Code job (or, in dry-run mode, a deterministic stub
that exercises the orchestration without provider calls).

Dry-run produces a complete run directory with stub artifacts so the harness
can be smoke-tested end-to-end without a provider. Live runs invoke the
`claude` CLI per stage with the same single-file, isolated-prompt contract
the existing `runner.py` uses.

This file is deliberately standalone (stdlib only) and lean. It does not
share state with `scripts/runner.py`.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = REPO_ROOT / "prompts" / "workshop"

DEFAULT_CHAPTER_COUNT = 16  # used in dry-run; live runs read the actual outline.

# When claude reports a rejected rate-limit, sleep until resetsAt + buffer +
# jitter. The buffer absorbs clock drift; the jitter avoids thundering-herd if
# multiple runs are paused at the same time.
RATE_LIMIT_RESET_BUFFER_SECONDS = 120
RATE_LIMIT_RESET_JITTER_SECONDS = 30

RATE_LIMIT_TEXT_MARKERS = (
    "rate limit",
    "rate_limit",
    "rate-limit",
    "429",
    "too many requests",
    "usage limit",
    "quota",
    "you've hit your limit",
    "you have hit your limit",
)

STAGE_ORDER = [
    "research",
    "blueprint",
    "outline",
    "voice_trial",
    "draft",
    "read_structural",
    "revise_structural",
    "read_character_theme",
    "revise_character_theme",
    "read_line",
    "revise_line",
    "final_read",
    "final_polish",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def slugify_title(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or "chapter"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def render_template(template: str, replacements: dict[str, str]) -> str:
    out = template
    for key, value in replacements.items():
        out = out.replace("{{" + key + "}}", value)
    return out


def parse_outline_chapters(outline_path: Path) -> list[dict[str, str]]:
    """
    Pull chapter headings out of `outline/outline.md`.

    Expects `## Chapter N — Title` headings. Falls back to numbered chapters
    only (no titles) if no em-dash form is present.
    """
    if not outline_path.exists():
        return []

    text = read_text(outline_path)
    chapters: list[dict[str, str]] = []
    pattern = re.compile(
        r"^##\s*Chapter\s+(\d+)\s*[—\-–:]\s*(.+?)\s*$",
        re.MULTILINE,
    )
    for m in pattern.finditer(text):
        chapters.append({"number": m.group(1), "title": m.group(2).strip()})
    if chapters:
        return chapters

    fallback = re.compile(r"^##\s*Chapter\s+(\d+)\b.*$", re.MULTILINE)
    for m in fallback.finditer(text):
        chapters.append({"number": m.group(1), "title": ""})
    return chapters


# ---------------------------------------------------------------------------
# Job execution
# ---------------------------------------------------------------------------


@dataclass
class Job:
    stage: str
    name: str  # used for log file naming; e.g. "draft_03"
    prompt_path: Path
    prompt_replacements: dict[str, str] = field(default_factory=dict)
    inputs: list[Path] = field(default_factory=list)  # files the job is expected to read
    outputs: list[Path] = field(default_factory=list)  # files the job must produce


class WorkshopRunner:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.run_dir = Path(args.run_dir).resolve()
        self.logs_dir = self.run_dir / "logs"
        self.prompts_dir = PROMPTS_DIR
        self.dry_run = bool(args.dry_run)
        self.claude_bin = args.claude_bin
        self.model = args.model
        self.reasoning = args.reasoning
        self.idle_timeout_seconds = args.idle_timeout
        self.wall_timeout_seconds = args.wall_timeout
        self.force = bool(args.force)
        self.quiet = bool(args.quiet)
        self.max_retries = max(0, int(args.max_retries))
        self.rate_limit_wait = max(60, int(args.rate_limit_wait))

        self.premise_text = ""
        self.shared_aesthetic = ""
        self.chapter_count = args.chapter_count or DEFAULT_CHAPTER_COUNT

        self._log_lock_path = self.run_dir / "logs" / "runner.log"

    # ------------------------------------------------------------------
    # Entrypoint
    # ------------------------------------------------------------------

    def run(self) -> int:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        premise_path = Path(self.args.premise_file).resolve()
        if not premise_path.is_file():
            raise FileNotFoundError(f"premise file not found: {premise_path}")
        self.premise_text = read_text(premise_path).strip()
        self.log(f"start premise={premise_path} run_dir={self.run_dir} dry_run={self.dry_run}")

        self._materialize_shared_aesthetic()
        self.shared_aesthetic = read_text(self.run_dir / "config" / "00_shared_aesthetic.md")

        # Allow the user to ask for a partial run.
        active_stages = self._select_stages()
        self.log(f"stages_planned={active_stages}")

        for stage in active_stages:
            self._dispatch_stage(stage)

        self.log("done")
        return 0

    # ------------------------------------------------------------------
    # Stage dispatch
    # ------------------------------------------------------------------

    def _select_stages(self) -> list[str]:
        start = self.args.start_stage or STAGE_ORDER[0]
        stop = self.args.stop_stage or STAGE_ORDER[-1]
        if start not in STAGE_ORDER:
            raise ValueError(f"unknown --start-stage: {start}")
        if stop not in STAGE_ORDER:
            raise ValueError(f"unknown --stop-stage: {stop}")
        i, j = STAGE_ORDER.index(start), STAGE_ORDER.index(stop)
        if j < i:
            raise ValueError("--stop-stage precedes --start-stage")
        return STAGE_ORDER[i : j + 1]

    def _dispatch_stage(self, stage: str) -> None:
        handler: Callable[[], None] = getattr(self, f"_stage_{stage}")
        self.log(f"stage_start={stage}")
        t0 = time.time()
        handler()
        self.log(f"stage_done={stage} elapsed={time.time() - t0:.1f}s")

    # ------------------------------------------------------------------
    # Stage implementations
    # ------------------------------------------------------------------

    def _stage_research(self) -> None:
        job = Job(
            stage="research",
            name="research",
            prompt_path=self.prompts_dir / "01_research.md",
            inputs=[self.run_dir / "config" / "00_shared_aesthetic.md"],
            outputs=[self.run_dir / "research" / "dossier.md"],
        )
        self._execute(job)

    def _stage_blueprint(self) -> None:
        job = Job(
            stage="blueprint",
            name="blueprint",
            prompt_path=self.prompts_dir / "02_blueprint.md",
            inputs=[
                self.run_dir / "config" / "00_shared_aesthetic.md",
                self.run_dir / "research" / "dossier.md",
            ],
            outputs=[self.run_dir / "blueprint" / "bible.md"],
        )
        self._execute(job)

    def _stage_outline(self) -> None:
        job = Job(
            stage="outline",
            name="outline",
            prompt_path=self.prompts_dir / "03_outline.md",
            inputs=[
                self.run_dir / "config" / "00_shared_aesthetic.md",
                self.run_dir / "blueprint" / "bible.md",
            ],
            outputs=[self.run_dir / "outline" / "outline.md"],
        )
        self._execute(job)

        # Update chapter count from the outline that just landed (live mode).
        if not self.dry_run:
            chapters = parse_outline_chapters(self.run_dir / "outline" / "outline.md")
            if chapters:
                self.chapter_count = len(chapters)
                self.log(f"chapter_count_from_outline={self.chapter_count}")

    def _stage_voice_trial(self) -> None:
        job = Job(
            stage="voice_trial",
            name="voice_trial",
            prompt_path=self.prompts_dir / "04_voice_trial.md",
            inputs=[
                self.run_dir / "config" / "00_shared_aesthetic.md",
                self.run_dir / "blueprint" / "bible.md",
                self.run_dir / "outline" / "outline.md",
            ],
            outputs=[
                self.run_dir / "voice" / "trial_a.md",
                self.run_dir / "voice" / "trial_b.md",
                self.run_dir / "voice" / "choice.md",
                self.run_dir / "voice" / "style_guide.md",
            ],
        )
        self._execute(job)

    def _stage_draft(self) -> None:
        for spec in self._chapter_specs():
            n_padded = f"{int(spec['number']):02d}"
            out = self.run_dir / "drafts" / "v1" / f"chapter_{n_padded}.md"
            inputs = [
                self.run_dir / "config" / "00_shared_aesthetic.md",
                self.run_dir / "voice" / "style_guide.md",
                self.run_dir / "blueprint" / "bible.md",
                self.run_dir / "outline" / "outline.md",
            ]
            # Prior chapters in v1 (already drafted).
            for prior in self._prior_chapters("drafts/v1", int(spec["number"])):
                inputs.append(prior)
            job = Job(
                stage="draft",
                name=f"draft_{n_padded}",
                prompt_path=self.prompts_dir / "05_chapter_draft.md",
                prompt_replacements={
                    "CHAPTER_NUMBER": spec["number"],
                    "CHAPTER_NUMBER_PADDED": n_padded,
                    "CHAPTER_TITLE": spec["title"] or f"Chapter {spec['number']}",
                },
                inputs=inputs,
                outputs=[out],
            )
            self._execute(job)

    def _stage_read_structural(self) -> None:
        inputs = [
            self.run_dir / "config" / "00_shared_aesthetic.md",
            self.run_dir / "blueprint" / "bible.md",
            self.run_dir / "outline" / "outline.md",
        ]
        for ch in self._existing_chapters("drafts/v1"):
            inputs.append(ch)
        job = Job(
            stage="read_structural",
            name="read_structural",
            prompt_path=self.prompts_dir / "06_read_structural.md",
            inputs=inputs,
            outputs=[self.run_dir / "reads" / "v1_structural_notes.md"],
        )
        self._execute(job)

    def _stage_revise_structural(self) -> None:
        notes = self.run_dir / "reads" / "v1_structural_notes.md"
        for spec in self._chapter_specs():
            n_padded = f"{int(spec['number']):02d}"
            src = self.run_dir / "drafts" / "v1" / f"chapter_{n_padded}.md"
            out = self.run_dir / "drafts" / "v2" / f"chapter_{n_padded}.md"
            job = Job(
                stage="revise_structural",
                name=f"revise_structural_{n_padded}",
                prompt_path=self.prompts_dir / "07_revise_structural.md",
                prompt_replacements={
                    "CHAPTER_NUMBER": spec["number"],
                    "CHAPTER_NUMBER_PADDED": n_padded,
                    "CHAPTER_TITLE": spec["title"] or f"Chapter {spec['number']}",
                },
                inputs=[
                    self.run_dir / "config" / "00_shared_aesthetic.md",
                    self.run_dir / "voice" / "style_guide.md",
                    self.run_dir / "blueprint" / "bible.md",
                    self.run_dir / "outline" / "outline.md",
                    notes,
                    src,
                ],
                outputs=[out],
            )
            self._execute(job)

    def _stage_read_character_theme(self) -> None:
        inputs = [
            self.run_dir / "config" / "00_shared_aesthetic.md",
            self.run_dir / "blueprint" / "bible.md",
            self.run_dir / "outline" / "outline.md",
            self.run_dir / "voice" / "style_guide.md",
        ]
        for ch in self._existing_chapters("drafts/v2"):
            inputs.append(ch)
        job = Job(
            stage="read_character_theme",
            name="read_character_theme",
            prompt_path=self.prompts_dir / "08_read_character_theme.md",
            inputs=inputs,
            outputs=[self.run_dir / "reads" / "v2_character_theme_notes.md"],
        )
        self._execute(job)

    def _stage_revise_character_theme(self) -> None:
        notes = self.run_dir / "reads" / "v2_character_theme_notes.md"
        for spec in self._chapter_specs():
            n_padded = f"{int(spec['number']):02d}"
            src = self.run_dir / "drafts" / "v2" / f"chapter_{n_padded}.md"
            out = self.run_dir / "drafts" / "v3" / f"chapter_{n_padded}.md"
            job = Job(
                stage="revise_character_theme",
                name=f"revise_character_theme_{n_padded}",
                prompt_path=self.prompts_dir / "09_revise_character_theme.md",
                prompt_replacements={
                    "CHAPTER_NUMBER": spec["number"],
                    "CHAPTER_NUMBER_PADDED": n_padded,
                    "CHAPTER_TITLE": spec["title"] or f"Chapter {spec['number']}",
                },
                inputs=[
                    self.run_dir / "config" / "00_shared_aesthetic.md",
                    self.run_dir / "voice" / "style_guide.md",
                    self.run_dir / "blueprint" / "bible.md",
                    self.run_dir / "outline" / "outline.md",
                    notes,
                    src,
                ],
                outputs=[out],
            )
            self._execute(job)

    def _stage_read_line(self) -> None:
        for spec in self._chapter_specs():
            n_padded = f"{int(spec['number']):02d}"
            src = self.run_dir / "drafts" / "v3" / f"chapter_{n_padded}.md"
            out = self.run_dir / "reads" / "v3_line_notes" / f"chapter_{n_padded}.md"
            job = Job(
                stage="read_line",
                name=f"read_line_{n_padded}",
                prompt_path=self.prompts_dir / "10_read_line.md",
                prompt_replacements={
                    "CHAPTER_NUMBER": spec["number"],
                    "CHAPTER_NUMBER_PADDED": n_padded,
                    "CHAPTER_TITLE": spec["title"] or f"Chapter {spec['number']}",
                },
                inputs=[
                    self.run_dir / "config" / "00_shared_aesthetic.md",
                    self.run_dir / "voice" / "style_guide.md",
                    self.run_dir / "blueprint" / "bible.md",
                    src,
                ],
                outputs=[out],
            )
            self._execute(job)

    def _stage_revise_line(self) -> None:
        for spec in self._chapter_specs():
            n_padded = f"{int(spec['number']):02d}"
            src = self.run_dir / "drafts" / "v3" / f"chapter_{n_padded}.md"
            notes = self.run_dir / "reads" / "v3_line_notes" / f"chapter_{n_padded}.md"
            out = self.run_dir / "drafts" / "v4" / f"chapter_{n_padded}.md"
            job = Job(
                stage="revise_line",
                name=f"revise_line_{n_padded}",
                prompt_path=self.prompts_dir / "11_revise_line.md",
                prompt_replacements={
                    "CHAPTER_NUMBER": spec["number"],
                    "CHAPTER_NUMBER_PADDED": n_padded,
                    "CHAPTER_TITLE": spec["title"] or f"Chapter {spec['number']}",
                },
                inputs=[
                    self.run_dir / "config" / "00_shared_aesthetic.md",
                    self.run_dir / "voice" / "style_guide.md",
                    notes,
                    src,
                ],
                outputs=[out],
            )
            self._execute(job)

    def _stage_final_read(self) -> None:
        inputs = [
            self.run_dir / "config" / "00_shared_aesthetic.md",
            self.run_dir / "blueprint" / "bible.md",
            self.run_dir / "outline" / "outline.md",
            self.run_dir / "voice" / "style_guide.md",
        ]
        for ch in self._existing_chapters("drafts/v4"):
            inputs.append(ch)
        job = Job(
            stage="final_read",
            name="final_read",
            prompt_path=self.prompts_dir / "12_final_read.md",
            inputs=inputs,
            outputs=[self.run_dir / "reads" / "v4_final_notes.md"],
        )
        self._execute(job)

    def _stage_final_polish(self) -> None:
        # Per-chapter polish, then assemble. In dry-run we synthesize a
        # plausible full.md from the v4 chapters; live runs let the agent do it
        # in one job since the assembly is part of the polish prompt.
        # Order matters in dry-run: per-chapter stubs must land before the
        # `full.md` stub so the concatenation has chapter content to splice.
        outputs: list[Path] = []
        for spec in self._chapter_specs():
            n_padded = f"{int(spec['number']):02d}"
            outputs.append(self.run_dir / "manuscript" / f"chapter_{n_padded}.md")
        outputs.append(self.run_dir / "manuscript" / "colophon.md")
        outputs.append(self.run_dir / "manuscript" / "full.md")

        inputs = [
            self.run_dir / "config" / "00_shared_aesthetic.md",
            self.run_dir / "voice" / "style_guide.md",
            self.run_dir / "blueprint" / "bible.md",
            self.run_dir / "reads" / "v4_final_notes.md",
        ]
        for ch in self._existing_chapters("drafts/v4"):
            inputs.append(ch)

        job = Job(
            stage="final_polish",
            name="final_polish",
            prompt_path=self.prompts_dir / "13_final_polish.md",
            inputs=inputs,
            outputs=outputs,
        )
        self._execute(job)

    # ------------------------------------------------------------------
    # Chapter spec resolution
    # ------------------------------------------------------------------

    def _chapter_specs(self) -> list[dict[str, str]]:
        """
        In dry-run, synthesize specs (we have no real outline). In live mode,
        read the outline for the canonical chapter list.
        """
        outline_path = self.run_dir / "outline" / "outline.md"
        if outline_path.is_file():
            parsed = parse_outline_chapters(outline_path)
            if parsed:
                return parsed
        # Fallback (dry-run or outline not yet written).
        return [
            {"number": str(i + 1), "title": f"Chapter {i + 1} working title"}
            for i in range(self.chapter_count)
        ]

    def _existing_chapters(self, subdir: str) -> list[Path]:
        d = self.run_dir / subdir
        if not d.is_dir():
            return []
        return sorted(d.glob("chapter_*.md"))

    def _prior_chapters(self, subdir: str, current_n: int) -> list[Path]:
        result = []
        for p in self._existing_chapters(subdir):
            m = re.match(r"chapter_(\d{2})\.md", p.name)
            if not m:
                continue
            if int(m.group(1)) < current_n:
                result.append(p)
        return result

    # ------------------------------------------------------------------
    # Job execution: dry vs. live
    # ------------------------------------------------------------------

    def _execute(self, job: Job) -> None:
        # Checkpoint resume: if every declared output already exists and is
        # non-empty, treat the job as done unless --force was passed. This is
        # what makes per-chapter resume work after a partial-stage failure.
        if not self.force and self._already_done(job):
            self.log(f"job_skip_already_done job={job.name}")
            return

        # Verify inputs exist (skip if dry-run and we haven't built them yet —
        # the dry stub will produce plausible files for downstream stages).
        for inp in job.inputs:
            if not inp.is_file():
                if self.dry_run:
                    # Tolerated: the orchestration is the test.
                    self.log(f"WARN missing_input_dry job={job.name} path={inp}")
                else:
                    raise FileNotFoundError(f"job {job.name}: missing input {inp}")

        prompt = self._build_prompt(job)

        prompt_log = self.logs_dir / "prompts" / f"{job.name}.md"
        write_text(prompt_log, prompt)

        if self.dry_run:
            self._execute_dry(job)
            return

        self._execute_live(job, prompt)

    def _build_prompt(self, job: Job) -> str:
        template = read_text(job.prompt_path)
        rendered = render_template(template, job.prompt_replacements)
        # The agent will be running with cwd=run_dir so paths are relative
        # to the run dir. Build a small frame around the prompt.
        manifest_lines = []
        manifest_lines.append(f"# Job: {job.name}  ({job.stage})")
        manifest_lines.append("")
        manifest_lines.append("Working directory: this run directory (paths below are relative).")
        manifest_lines.append("")
        manifest_lines.append("## Inputs (read these)")
        for p in job.inputs:
            manifest_lines.append(f"- `{self._rel_to_run(p)}`")
        manifest_lines.append("")
        manifest_lines.append("## Required outputs (write exactly these files)")
        for p in job.outputs:
            manifest_lines.append(f"- `{self._rel_to_run(p)}`")
        manifest_lines.append("")
        manifest_lines.append("---")
        manifest_lines.append("")
        return "\n".join(manifest_lines) + rendered

    def _rel_to_run(self, p: Path) -> str:
        try:
            return str(p.relative_to(self.run_dir))
        except ValueError:
            return str(p)

    # ---- dry ----

    def _execute_dry(self, job: Job) -> None:
        for out in job.outputs:
            self._dry_artifact(job, out)
        self.log(f"job_dry_done job={job.name} outputs={len(job.outputs)}")

    def _dry_artifact(self, job: Job, out: Path) -> None:
        """
        Write a stub artifact whose content is deterministic and useful.
        Chapter files get a heading + lorem-style placeholder paragraph so
        downstream stages have something to read.
        """
        rel = self._rel_to_run(out)
        header = (
            f"<!-- workshop-runner dry-run stub\n"
            f"     stage: {job.stage}\n"
            f"     job: {job.name}\n"
            f"     output: {rel}\n"
            f"     ts: {ts()}\n"
            f"-->\n"
        )

        m = re.match(r"(drafts/v[1-4]|manuscript)/chapter_(\d{2})\.md$", rel)
        if m:
            n = int(m.group(2))
            title = next(
                (s["title"] for s in self._chapter_specs() if int(s["number"]) == n),
                f"Working title {n}",
            ) or f"Working title {n}"
            body = (
                f"# Chapter {n} — {title}\n\n"
                f"_Stub content for chapter {n}. In a live run this paragraph would\n"
                f"be a full chapter draft of the novel about the cult-leader-turned-dictator.\n"
                f"The stub keeps the orchestrator runnable end-to-end without provider calls.\n\n"
                f"The dossier, bible, outline, and style guide are all upstream of this file.\n"
                f"The structural, character/theme, and line passes will read this file in turn.\n_\n"
            )
            write_text(out, header + body)
            return

        if rel == "outline/outline.md":
            ch_lines = []
            for i in range(self.chapter_count):
                n = i + 1
                ch_lines.append(f"## Chapter {n} — Working title {n}\n")
                ch_lines.append(
                    "_Stub chapter spec: function, beats, heritage thread, doubt thread,\n"
                    "image work, avoid. Replaced in a live run by the outliner agent._\n"
                )
            write_text(out, header + "# Outline (stub)\n\n" + "\n".join(ch_lines))
            return

        if rel == "manuscript/full.md":
            parts = [header, "# The Novel (stub)\n", "*A novel.*\n\n"]
            for i in range(self.chapter_count):
                n_padded = f"{i + 1:02d}"
                ch = self.run_dir / "manuscript" / f"chapter_{n_padded}.md"
                if ch.is_file():
                    parts.append(read_text(ch))
                    parts.append("\n\n\n")
            write_text(out, "".join(parts))
            return

        if rel == "manuscript/colophon.md":
            write_text(
                out,
                header
                + "# Colophon\n\n"
                f"Title: (stub)\n\nChapters: {self.chapter_count}\n\nSign-off: dry-run.\n",
            )
            return

        # Generic stub.
        title_guess = out.stem.replace("_", " ").title()
        write_text(
            out,
            header
            + f"# {title_guess} (stub)\n\n"
            f"This is a dry-run stub for `{rel}`.\nReplaced by an agent in a live run.\n",
        )

    # ---- live ----

    def _execute_live(self, job: Job, prompt: str) -> None:
        """
        Run a live claude job, with automatic wait-and-retry on rate-limit
        failures. The retry loop only fires for rate-limit-shaped errors;
        other failures (missing inputs, hard crashes, non-quota timeouts)
        propagate immediately.
        """
        if not self.claude_bin:
            raise RuntimeError(
                "no --claude-bin given and CLAUDE_BIN not set; cannot run live"
            )

        log_jsonl = self.logs_dir / "jobs" / f"{job.name}.jsonl"
        stderr_path = self.logs_dir / "jobs" / f"{job.name}.stderr.txt"
        log_jsonl.parent.mkdir(parents=True, exist_ok=True)

        max_attempts = 1 + self.max_retries
        attempt = 0
        while True:
            attempt += 1
            try:
                self._run_one_live_attempt(job, prompt, log_jsonl, stderr_path, attempt)
                return
            except RuntimeError as failure:
                pause = self._diagnose_rate_limit_pause(log_jsonl, stderr_path)
                if pause is None or attempt >= max_attempts:
                    raise

                wait = pause["wait_seconds"]
                reset_at = pause.get("reset_at")
                kind = pause.get("rate_limit_type") or "unknown"
                self.log(
                    f"job_rate_limit_pause job={job.name} attempt={attempt}/{max_attempts} "
                    f"wait_s={wait} reset_at={reset_at or 'n/a'} kind={kind}"
                )
                reset_str = (
                    datetime.fromtimestamp(reset_at, tz=timezone.utc).strftime("%H:%M:%SZ")
                    if reset_at
                    else "unknown"
                )
                self._stdout(
                    f"\n[{job.name}] rate-limit detected ({kind}); resting until {reset_str} "
                    f"(~{wait}s) then retrying ({attempt}/{max_attempts})."
                )

                # Preserve the failed attempt's logs.
                self._rotate_attempt_logs(log_jsonl, stderr_path, attempt)
                self._sleep_with_heartbeat(wait, job.name)

    def _run_one_live_attempt(
        self,
        job: Job,
        prompt: str,
        log_jsonl: Path,
        stderr_path: Path,
        attempt: int,
    ) -> None:
        cmd = [
            self.claude_bin,
            "-p",
            "--output-format",
            "stream-json",
            "--verbose",
            "--no-session-persistence",
            "--dangerously-skip-permissions",
        ]
        if self.model:
            cmd.extend(["--model", self.model])
        if self.reasoning:
            cmd.extend(["--effort", self.reasoning])

        self.log(f"job_live_start job={job.name} attempt={attempt} cmd={' '.join(cmd)}")
        if attempt == 1:
            self._stdout(f"\n────── {job.name} ({job.stage}) ──────")
        else:
            self._stdout(f"\n────── {job.name} ({job.stage}) — retry attempt {attempt} ──────")

        # Streamer thread tails the jsonl log as the agent writes it.
        stop_event = threading.Event()
        streamer = threading.Thread(
            target=self._stream_log,
            args=(log_jsonl, stop_event, job.name),
            daemon=True,
        )

        t0 = time.time()
        with log_jsonl.open("w", encoding="utf-8") as out_f, stderr_path.open(
            "w", encoding="utf-8"
        ) as err_f:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=out_f,
                stderr=err_f,
                text=True,
                cwd=str(self.run_dir),
            )
            try:
                assert proc.stdin is not None
                proc.stdin.write(prompt)
                proc.stdin.close()
            except BrokenPipeError:
                pass

            streamer.start()

            # Lightweight watchdog: wall-clock cap + idle (no-JSONL) cap.
            poll_interval = 10
            wall = 0.0
            idle = 0.0
            last_size = 0
            try:
                while proc.poll() is None:
                    time.sleep(poll_interval)
                    wall += poll_interval
                    try:
                        size = log_jsonl.stat().st_size
                    except OSError:
                        size = 0
                    if size > last_size:
                        last_size = size
                        idle = 0.0
                    else:
                        idle += poll_interval

                    if wall >= self.wall_timeout_seconds:
                        self._kill_proc(proc)
                        raise RuntimeError(
                            f"job {job.name} wall-clock timeout after {wall:.0f}s"
                        )
                    if idle >= self.idle_timeout_seconds:
                        self._kill_proc(proc)
                        raise RuntimeError(
                            f"job {job.name} idle timeout after {idle:.0f}s (no JSONL output)"
                        )
            finally:
                stop_event.set()
                streamer.join(timeout=5)

        rc = proc.returncode
        elapsed = time.time() - t0
        self.log(
            f"job_live_done job={job.name} attempt={attempt} rc={rc} elapsed={elapsed:.1f}s"
        )
        if rc != 0:
            raise RuntimeError(f"job {job.name} failed rc={rc}; see {stderr_path}")

        missing = [p for p in job.outputs if not p.is_file()]
        if missing:
            raise RuntimeError(
                f"job {job.name} succeeded but did not produce: "
                + ", ".join(self._rel_to_run(p) for p in missing)
            )

    @staticmethod
    def _kill_proc(proc: subprocess.Popen) -> None:
        try:
            proc.terminate()
        except OSError:
            return
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
                proc.wait()
            except OSError:
                pass

    def _rotate_attempt_logs(
        self, log_jsonl: Path, stderr_path: Path, attempt: int
    ) -> None:
        """Move {job}.jsonl + {job}.stderr.txt aside so the next attempt
        starts with empty logs. Rotated names: {job}.attempt-N.jsonl,
        {job}.attempt-N.stderr.txt."""
        rotations = [
            (log_jsonl, ".jsonl", f".attempt-{attempt}.jsonl"),
            (stderr_path, ".stderr.txt", f".attempt-{attempt}.stderr.txt"),
        ]
        for src, suffix, replacement in rotations:
            if not src.is_file():
                continue
            if src.name.endswith(suffix):
                new_name = src.name[: -len(suffix)] + replacement
            else:
                new_name = src.name + replacement
            keep = src.with_name(new_name)
            try:
                src.replace(keep)
            except OSError:
                pass

    def _sleep_with_heartbeat(self, total: int, job_name: str) -> None:
        """Sleep in chunks, emitting a stderr heartbeat every 60s so the user
        knows the harness is waiting and not hung."""
        remaining = int(total)
        chunk = 60
        while remaining > 0:
            step = min(chunk, remaining)
            time.sleep(step)
            remaining -= step
            if remaining > 0:
                self.log(f"rate_limit_wait_heartbeat job={job_name} remaining_s={remaining}")

    # ---- rate-limit parsing ----

    def _diagnose_rate_limit_pause(
        self, log_jsonl: Path, stderr_path: Path
    ) -> dict | None:
        """
        Returns {wait_seconds, reset_at, rate_limit_type} if the most recent
        attempt looks like a rate-limit rejection, else None.

        Detects:
        1. A claude `rate_limit_event` with `rate_limit_info.status="rejected"`
           and a numeric `resetsAt` epoch — preferred; gives a precise wait.
        2. Any free-text marker (rate limit / 429 / quota / etc.) in events
           or stderr — fallback; uses `--rate-limit-wait` seconds.
        """
        events = self._load_jsonl_events(log_jsonl)

        for evt in reversed(events):
            if not isinstance(evt, dict):
                continue
            if evt.get("type") != "rate_limit_event":
                continue
            info = evt.get("rate_limit_info")
            if not isinstance(info, dict):
                continue
            if str(info.get("status", "")).strip().lower() != "rejected":
                continue
            raw_reset = info.get("resetsAt")
            try:
                reset_epoch = int(raw_reset)
            except (TypeError, ValueError):
                continue
            now = int(time.time())
            base = max(0, reset_epoch - now)
            jitter = (
                random.randint(0, RATE_LIMIT_RESET_JITTER_SECONDS)
                if RATE_LIMIT_RESET_JITTER_SECONDS > 0
                else 0
            )
            wait = base + RATE_LIMIT_RESET_BUFFER_SECONDS + jitter
            return {
                "wait_seconds": wait,
                "reset_at": reset_epoch,
                "rate_limit_type": (str(info.get("rateLimitType", "")).strip() or None),
            }

        body_blobs: list[str] = []
        for evt in events:
            if isinstance(evt, dict):
                try:
                    body_blobs.append(json.dumps(evt))
                except (TypeError, ValueError):
                    pass
        try:
            stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            stderr_text = ""

        combined = ("\n".join(body_blobs) + "\n" + stderr_text).lower()
        if any(marker in combined for marker in RATE_LIMIT_TEXT_MARKERS):
            return {
                "wait_seconds": self.rate_limit_wait,
                "reset_at": None,
                "rate_limit_type": "text-pattern",
            }
        return None

    @staticmethod
    def _load_jsonl_events(path: Path) -> list[dict]:
        events: list[dict] = []
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return events
        for raw in text.splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                events.append(obj)
        return events

    # ------------------------------------------------------------------
    # Shared aesthetic materialization
    # ------------------------------------------------------------------

    def _materialize_shared_aesthetic(self) -> None:
        """
        Copy `prompts/workshop/00_shared_aesthetic.md` into the run dir with
        the premise inlined. Every stage's prompt frame references this file
        by run-dir-relative path.
        """
        src = self.prompts_dir / "00_shared_aesthetic.md"
        template = read_text(src)
        rendered = render_template(template, {"PREMISE": self.premise_text})
        out = self.run_dir / "config" / "00_shared_aesthetic.md"
        write_text(out, rendered)

        # Also drop the premise itself for traceability.
        write_text(self.run_dir / "config" / "premise.txt", self.premise_text + "\n")

        # And a manifest of the harness for the artifacts repo.
        manifest = {
            "harness": "workshop_runner",
            "version": 1,
            "stages": STAGE_ORDER,
            "premise_first_chars": self.premise_text[:200],
            "ts": ts(),
            "dry_run": self.dry_run,
        }
        write_text(
            self.run_dir / "config" / "harness_manifest.json",
            json.dumps(manifest, indent=2) + "\n",
        )

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def log(self, msg: str) -> None:
        line = f"[{ts()}] {msg}\n"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        with self._log_lock_path.open("a", encoding="utf-8") as f:
            f.write(line)
        # Stderr so the user sees progress without polluting redirected stdout.
        sys.stderr.write(line)
        sys.stderr.flush()

    def _stdout(self, msg: str) -> None:
        if self.quiet:
            return
        sys.stdout.write(msg + "\n")
        sys.stdout.flush()

    # ------------------------------------------------------------------
    # Checkpoint resume
    # ------------------------------------------------------------------

    def _already_done(self, job: Job) -> bool:
        """A job is 'done' if every declared output exists and is non-empty."""
        if not job.outputs:
            return False
        for p in job.outputs:
            if not p.is_file():
                return False
            try:
                if p.stat().st_size == 0:
                    return False
            except OSError:
                return False
        return True

    # ------------------------------------------------------------------
    # Live stream printer
    # ------------------------------------------------------------------

    def _stream_log(
        self,
        log_path: Path,
        stop_event: threading.Event,
        job_name: str,
    ) -> None:
        """
        Tail a stream-json log as the agent writes it and print human-readable
        progress (assistant text, tool calls, final result). Best-effort: any
        parse error is silently dropped — the raw jsonl on disk is the truth.
        """
        pos = 0
        buf = ""
        printed_any = False
        while True:
            try:
                with log_path.open("r", encoding="utf-8", errors="replace") as f:
                    f.seek(pos)
                    chunk = f.read()
                    pos = f.tell()
            except FileNotFoundError:
                chunk = ""

            if chunk:
                buf += chunk
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    if self._print_stream_event(line, job_name):
                        printed_any = True

            if stop_event.is_set():
                # Drain any final bytes.
                try:
                    with log_path.open("r", encoding="utf-8", errors="replace") as f:
                        f.seek(pos)
                        rest = f.read()
                except FileNotFoundError:
                    rest = ""
                if rest:
                    buf += rest
                if buf.strip():
                    for line in buf.splitlines():
                        if self._print_stream_event(line, job_name):
                            printed_any = True
                if not printed_any:
                    self._stdout(f"[{job_name}] (no events streamed)")
                return

            time.sleep(0.4)

    def _print_stream_event(self, raw_line: str, job_name: str) -> bool:
        raw_line = raw_line.strip()
        if not raw_line:
            return False
        try:
            evt = json.loads(raw_line)
        except json.JSONDecodeError:
            return False
        if not isinstance(evt, dict):
            return False
        kind = evt.get("type")

        if kind == "system" and evt.get("subtype") == "init":
            sess = evt.get("session_id", "")
            self._stdout(f"[{job_name}] session={sess[:8] or '?'} started")
            return True

        if kind == "assistant":
            msg = evt.get("message") or {}
            content = msg.get("content") or []
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")
                if btype == "text":
                    text = (block.get("text") or "").strip()
                    if text:
                        for line in text.splitlines():
                            self._stdout(f"[{job_name}] {line}")
                elif btype == "tool_use":
                    name = block.get("name", "?")
                    summary = self._summarize_tool_input(name, block.get("input") or {})
                    self._stdout(f"[{job_name}] · {name}({summary})")
            return True

        if kind == "result":
            sub = evt.get("subtype", "")
            dur_ms = evt.get("duration_ms")
            usage = evt.get("usage") or {}
            in_tok = usage.get("input_tokens")
            out_tok = usage.get("output_tokens")
            cache_read = usage.get("cache_read_input_tokens")
            bits: list[str] = []
            if sub:
                bits.append(sub)
            if isinstance(dur_ms, (int, float)):
                bits.append(f"{dur_ms / 1000:.1f}s")
            if in_tok is not None:
                bits.append(f"in={in_tok}")
            if out_tok is not None:
                bits.append(f"out={out_tok}")
            if cache_read is not None:
                bits.append(f"cache={cache_read}")
            self._stdout(f"[{job_name}] ◀ result {' '.join(bits)}")
            return True

        return False

    @staticmethod
    def _summarize_tool_input(name: str, inp: dict) -> str:
        if not isinstance(inp, dict):
            return ""
        # Keys that are useful to show inline, in priority order.
        for key in ("file_path", "path", "command", "pattern", "url", "prompt"):
            if key in inp and isinstance(inp[key], str):
                v = inp[key].replace("\n", " ").strip()
                if len(v) > 100:
                    v = v[:97] + "..."
                return f"{key}={v}"
        # Fall back to a compact key list.
        keys = ",".join(sorted(inp.keys()))
        return keys[:100]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _resolve_claude_bin(arg: str | None) -> str | None:
    if arg:
        return arg
    env = os.environ.get("CLAUDE_BIN", "").strip()
    if env:
        return env
    found = shutil.which("claude")
    return found


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="workshop_runner",
        description="Premise-tailored novel harness (research → draft → revise → polish).",
    )
    p.add_argument("--premise-file", default=str(REPO_ROOT / "exp" / "longer.txt"))
    p.add_argument("--run-dir", default=str(REPO_ROOT / "runs" / "workshop_demo"))
    p.add_argument("--dry-run", action="store_true", help="produce stub artifacts, no provider calls")
    p.add_argument(
        "--start-stage",
        default=None,
        help=f"first stage to run (one of: {', '.join(STAGE_ORDER)})",
    )
    p.add_argument(
        "--stop-stage",
        default=None,
        help="last stage to run (inclusive)",
    )
    p.add_argument(
        "--chapter-count",
        type=int,
        default=0,
        help="dry-run chapter count fallback (live runs read the outline)",
    )
    p.add_argument("--claude-bin", default=None, help="path to claude CLI (falls back to $CLAUDE_BIN, then PATH)")
    p.add_argument("--model", default="claude-opus-4-7", help="claude model id")
    p.add_argument("--reasoning", default="max", help="claude --effort value")
    p.add_argument(
        "--idle-timeout",
        type=int,
        default=1800,
        help="seconds of jsonl silence before killing a job (default 1800; heavy stages like blueprint can stall while the model thinks)",
    )
    p.add_argument(
        "--wall-timeout",
        type=int,
        default=7200,
        help="seconds of wall-clock before killing a job (default 7200)",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="re-run every job even if its outputs already exist (disables checkpoint resume)",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="suppress streamed agent output to stdout (the jsonl logs are still written)",
    )
    p.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="max automatic retries per job after a detected rate-limit pause (default 3)",
    )
    p.add_argument(
        "--rate-limit-wait",
        type=int,
        default=600,
        help="fallback seconds to sleep when a rate-limit is suspected but no resetsAt is available (default 600)",
    )
    args = p.parse_args(argv)
    args.claude_bin = _resolve_claude_bin(args.claude_bin)
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    runner = WorkshopRunner(args)
    return runner.run()


if __name__ == "__main__":
    sys.exit(main())
