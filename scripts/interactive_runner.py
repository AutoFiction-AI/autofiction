#!/usr/bin/env python3
"""Interactive mirror of scripts/runner.py.

Wraps NovelPipelineRunner with TTY checkpoints after the outline stage,
after each individual chapter draft, after each cycle's chapter-review
stage, and after each cycle's revision stage. At every checkpoint the
human reads the produced artifacts and types free-text annotations; a
small LLM call (via the Claude CLI) interprets the annotation as one of
continue / revise / rewrite and the harness loops accordingly. The
annotation is also injected into the next render of the relevant prompt
as a <human_editor_notes> block.

Designed as a thin wrapper: re-uses the parent runner's job builders,
prompt rendering, validation, and resume behaviour. Only the
parallelism of the draft stage is suppressed, so each chapter can be
inspected before the next is generated.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
for _path in (str(SCRIPTS_DIR), str(REPO_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from runner import (  # noqa: E402
    JobSpec,
    NovelPipelineRunner,
    PipelineError,
    build_config,
    parse_args,
)


VALID_ACTIONS = ("continue", "revise", "rewrite")


class InteractivePipelineRunner(NovelPipelineRunner):
    """NovelPipelineRunner with human-in-the-loop checkpoints."""

    def __init__(self, *, repo_root: Path, cfg) -> None:
        super().__init__(repo_root=repo_root, cfg=cfg)
        self._annotations_dir = self.run_dir / "annotations"
        self._pending_outline_notes: str | None = None
        self._pending_chapter_notes: dict[str, str] = {}
        self._pending_review_notes: dict[int, str] = {}
        self._pending_revision_notes: dict[int, str] = {}
        self._current_cycle: int | None = None
        self._decision_bin = self._resolve_decision_bin()

    # ------------------------------------------------------------------
    # Stage overrides
    # ------------------------------------------------------------------

    def _run_outline_stage(self) -> None:
        super()._run_outline_stage()
        while True:
            action, note = self._checkpoint(
                stage_label="outline",
                key="outline",
                read_paths=self._outline_read_paths(),
                summary="Outline + scene plan + style bible + spatial layout are written.",
            )
            if action == "continue":
                self._pending_outline_notes = None
                return
            self._pending_outline_notes = self._compose_notes(action, note)
            self._invalidate_outline_outputs()
            self._log(f"interactive outline_rerun action={action}")
            super()._run_outline_stage()

    def _run_draft_stage(self) -> None:
        # In add-cycles resume mode, the parent expects all chapter files to
        # already exist; defer to it without interactive pauses.
        if self._add_cycles_mode():
            super()._run_draft_stage()
            return
        # Force serial drafting so each chapter can be inspected.
        for spec in self.chapter_specs:
            chapter_rel = f"chapters/{spec.chapter_id}.md"
            while True:
                self._draft_single_chapter(spec)
                action, note = self._checkpoint(
                    stage_label=f"chapter_draft:{spec.chapter_id}",
                    key=f"draft_{spec.chapter_id}",
                    read_paths=[chapter_rel],
                    summary=f"Drafted {chapter_rel}.",
                )
                if action == "continue":
                    self._pending_chapter_notes.pop(spec.chapter_id, None)
                    break
                self._pending_chapter_notes[spec.chapter_id] = self._compose_notes(
                    action, note
                )
                self._delete_chapter_draft(spec.chapter_id)
                self._log(
                    f"interactive draft_rerun chapter={spec.chapter_id} action={action}"
                )

    def _run_chapter_review_stage(self, cycle: int) -> dict[str, Any]:
        self._current_cycle = cycle
        try:
            result = super()._run_chapter_review_stage(cycle)
            while True:
                cpad = self._cpad(cycle)
                action, note = self._checkpoint(
                    stage_label=f"chapter_review_cycle_{cpad}",
                    key=f"review_cycle_{cpad}",
                    read_paths=self._review_read_paths(cycle),
                    summary=(
                        f"Per-chapter reviews for cycle {cpad} are written under "
                        f"reviews/cycle_{cpad}/. Read individual chapter_*.review.json files."
                    ),
                )
                if action == "continue":
                    self._pending_review_notes.pop(cycle, None)
                    return result
                self._pending_review_notes[cycle] = self._compose_notes(action, note)
                self._invalidate_review_outputs(cycle)
                self._log(
                    f"interactive review_rerun cycle={cpad} action={action}"
                )
                result = super()._run_chapter_review_stage(cycle)
        finally:
            self._current_cycle = None

    def _run_revision_stage(
        self, cycle: int, chapter_ids: list[str]
    ) -> dict[str, Any]:
        self._current_cycle = cycle
        try:
            result = super()._run_revision_stage(cycle, chapter_ids)
            while True:
                cpad = self._cpad(cycle)
                action, note = self._checkpoint(
                    stage_label=f"revision_cycle_{cpad}",
                    key=f"revision_cycle_{cpad}",
                    read_paths=self._revision_read_paths(cycle),
                    summary=(
                        f"Revisions for cycle {cpad} are written under "
                        f"revisions/cycle_{cpad}/ and the post-revision snapshot is at "
                        f"snapshots/cycle_{cpad}/FINAL_NOVEL.post_revision.md."
                    ),
                )
                if action == "continue":
                    self._pending_revision_notes.pop(cycle, None)
                    return result
                self._pending_revision_notes[cycle] = self._compose_notes(action, note)
                self._invalidate_revision_outputs(cycle, chapter_ids)
                self._log(
                    f"interactive revision_rerun cycle={cpad} action={action}"
                )
                result = super()._run_revision_stage(cycle, chapter_ids)
        finally:
            self._current_cycle = None

    # ------------------------------------------------------------------
    # Prompt injection
    # ------------------------------------------------------------------

    def _render_prompt(
        self, template_name: str, replacements: dict[str, str]
    ) -> str:
        text = super()._render_prompt(template_name, replacements)
        notes = self._notes_for_template(template_name, replacements)
        if notes:
            text = text + "\n\n" + self._format_editor_notes_block(notes)
        return text

    def _notes_for_template(
        self, template_name: str, replacements: dict[str, str]
    ) -> str | None:
        if template_name == "outline_prompt.md":
            return self._pending_outline_notes
        if template_name == "chapter_draft_prompt.md":
            chapter_id = replacements.get("CHAPTER_ID")
            if chapter_id:
                return self._pending_chapter_notes.get(chapter_id)
            return None
        if template_name == "chapter_review_prompt.md":
            if self._current_cycle is not None:
                return self._pending_review_notes.get(self._current_cycle)
            return None
        if template_name == "chapter_revision_prompt.md":
            if self._current_cycle is not None:
                return self._pending_revision_notes.get(self._current_cycle)
            return None
        return None

    @staticmethod
    def _format_editor_notes_block(notes: str) -> str:
        return (
            "<human_editor_notes>\n"
            "A human editor has reviewed the prior output of this stage and "
            "left the following annotations. Treat these as authoritative "
            "guidance for what to change. Address each point concretely; do "
            "not merely acknowledge them.\n\n"
            f"{notes.strip()}\n"
            "</human_editor_notes>"
        )

    # ------------------------------------------------------------------
    # Single-chapter draft (mirrors parent _run_draft_stage logic for one
    # chapter, without parallelism).
    # ------------------------------------------------------------------

    def _draft_single_chapter(self, spec) -> None:
        chapter_file = f"chapters/{spec.chapter_id}.md"
        chapter_path = self.run_dir / chapter_file
        if chapter_path.is_file():
            try:
                self._validate_chapter_heading(chapter_path, spec.chapter_number)
            except PipelineError:
                chapter_path.unlink(missing_ok=True)
        if chapter_path.is_file():
            # Reusable existing draft: skip generation; the user can still
            # annotate at the next checkpoint and force a rewrite.
            self._log(f"interactive draft_reuse chapter={spec.chapter_id}")
            return
        continuity_sheet_file = self._outline_continuity_snapshot_rel()
        spatial_layout_file = self._spatial_layout_rel()
        chapter_spec_file = f"outline/chapter_specs/{spec.chapter_id}.json"
        prompt = self._render_prompt(
            "chapter_draft_prompt.md",
            {
                "CHAPTER_ID": spec.chapter_id,
                "CHAPTER_NUMBER": str(spec.chapter_number),
                "CHAPTER_SPEC_FILE": chapter_spec_file,
                "CHAPTER_OUTPUT_FILE": chapter_file,
                "SPATIAL_LAYOUT_FILE": spatial_layout_file,
                "CONTINUITY_SHEET_FILE": continuity_sheet_file,
            },
        )
        job: JobSpec = self._make_job(
            job_id=f"draft_{spec.chapter_id}",
            stage="chapter_draft",
            stage_group="draft",
            cycle=0,
            chapter_id=spec.chapter_id,
            allowed_inputs=[
                "outline/outline.md",
                "outline/scene_plan.tsv",
                "outline/static_story_context.json",
                "outline/style_bible.json",
                spatial_layout_file,
                continuity_sheet_file,
                chapter_spec_file,
                "config/constitution.md",
                "config/prompts/chapter_draft_prompt.md",
            ],
            required_outputs=[chapter_file],
            prompt_text=prompt,
        )
        self._run_job(job)

    # ------------------------------------------------------------------
    # Output invalidation (forces parent stage methods to regenerate)
    # ------------------------------------------------------------------

    def _invalidate_outline_outputs(self) -> None:
        for rel in (
            "outline/outline.md",
            "outline/scene_plan.tsv",
            "outline/style_bible.json",
            "outline/static_story_context.json",
        ):
            path = self.run_dir / rel
            path.unlink(missing_ok=True)
        # Reset in-memory state so the parent re-reads after regen.
        self.chapter_specs = []
        self.style_bible = {}
        self.novel_title = ""

    def _delete_chapter_draft(self, chapter_id: str) -> None:
        path = self.run_dir / "chapters" / f"{chapter_id}.md"
        path.unlink(missing_ok=True)

    def _invalidate_review_outputs(self, cycle: int) -> None:
        cpad = self._cpad(cycle)
        review_dir = self.run_dir / "reviews" / f"cycle_{cpad}"
        if not review_dir.is_dir():
            return
        for path in review_dir.glob("*.review.json"):
            path.unlink(missing_ok=True)

    def _invalidate_revision_outputs(
        self, cycle: int, chapter_ids: list[str]
    ) -> None:
        cpad = self._cpad(cycle)
        rev_dir = self.run_dir / "revisions" / f"cycle_{cpad}"
        if rev_dir.is_dir():
            for path in rev_dir.glob("*.revision_report.json"):
                path.unlink(missing_ok=True)
        # Drop the post-revision chapter files so they get regenerated.
        for chapter_id in chapter_ids:
            for rel in (
                f"revisions/cycle_{cpad}/{chapter_id}.md",
                f"snapshots/cycle_{cpad}/FINAL_NOVEL.post_revision.md",
            ):
                (self.run_dir / rel).unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # Listing helpers for the checkpoint summaries
    # ------------------------------------------------------------------

    def _outline_read_paths(self) -> list[str]:
        return [
            "outline/outline.md",
            "outline/scene_plan.tsv",
            "outline/style_bible.json",
            "outline/spatial_layout.json",
        ]

    def _review_read_paths(self, cycle: int) -> list[str]:
        cpad = self._cpad(cycle)
        review_dir = self.run_dir / "reviews" / f"cycle_{cpad}"
        if not review_dir.is_dir():
            return [f"reviews/cycle_{cpad}/"]
        return sorted(
            str(p.relative_to(self.run_dir))
            for p in review_dir.glob("*.review.json")
        )

    def _revision_read_paths(self, cycle: int) -> list[str]:
        cpad = self._cpad(cycle)
        out: list[str] = [
            f"snapshots/cycle_{cpad}/FINAL_NOVEL.post_revision.md",
        ]
        rev_dir = self.run_dir / "revisions" / f"cycle_{cpad}"
        if rev_dir.is_dir():
            out.extend(
                sorted(
                    str(p.relative_to(self.run_dir))
                    for p in rev_dir.glob("*.revision_report.json")
                )
            )
        return out

    # ------------------------------------------------------------------
    # Checkpoint: TTY pause + free-text capture + decision LLM
    # ------------------------------------------------------------------

    def _checkpoint(
        self,
        *,
        stage_label: str,
        key: str,
        read_paths: list[str],
        summary: str,
    ) -> tuple[str, str]:
        self._annotations_dir.mkdir(parents=True, exist_ok=True)

        bar = "=" * 72
        print()
        print(bar, flush=True)
        print(f"INTERACTIVE CHECKPOINT: {stage_label}", flush=True)
        print(bar, flush=True)
        print(f"run_dir: {self.run_dir}", flush=True)
        print(summary, flush=True)
        if read_paths:
            print("\nRead these files (paths relative to run_dir):", flush=True)
            for rel in read_paths:
                print(f"  - {rel}", flush=True)
        print(
            "\nType your free-text annotation about what works and what does not. "
            "Be specific. Empty input is interpreted as 'continue'.",
            flush=True,
        )
        print(
            "End your annotation with a line containing only `.` (a single period) "
            "or press Ctrl-D.",
            flush=True,
        )
        print(bar, flush=True)

        note = self._read_multiline_from_tty()
        note = note.strip()

        if not note:
            print("[interactive] empty annotation -> continue", flush=True)
            self._persist_annotation(key, "continue", note)
            return "continue", ""

        action = self._decide_action(stage_label, note)
        print(f"[interactive] decided action: {action}", flush=True)
        self._persist_annotation(key, action, note)
        return action, note

    @staticmethod
    def _read_multiline_from_tty() -> str:
        lines: list[str] = []
        try:
            while True:
                line = input()
                if line.strip() == ".":
                    break
                lines.append(line)
        except EOFError:
            pass
        return "\n".join(lines)

    def _persist_annotation(self, key: str, action: str, note: str) -> None:
        path = self._annotations_dir / f"{key}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        body = (
            f"# Annotation: {key}\n\n"
            f"action: {action}\n\n"
            f"---\n\n{note}\n"
        )
        path.write_text(body, encoding="utf-8")

    @staticmethod
    def _compose_notes(action: str, raw_note: str) -> str:
        prefix = {
            "revise": "Revise the prior output to address these notes:",
            "rewrite": "Rewrite the prior output from scratch. The previous draft is being discarded. Apply these notes:",
            "continue": "",
        }.get(action, "Editor notes:")
        if not prefix:
            return raw_note.strip()
        return f"{prefix}\n\n{raw_note.strip()}"

    # ------------------------------------------------------------------
    # Decision LLM: classify free-text into continue|revise|rewrite.
    # ------------------------------------------------------------------

    def _decide_action(self, stage_label: str, note: str) -> str:
        if self._decision_bin is None:
            return self._ask_user_for_action(note)
        prompt = self._build_decision_prompt(stage_label, note)
        try:
            output = self._invoke_decision_cli(prompt)
        except (FileNotFoundError, subprocess.SubprocessError, OSError) as exc:
            print(
                f"[interactive] decision CLI failed ({exc}); falling back to manual choice.",
                flush=True,
            )
            return self._ask_user_for_action(note)
        action = self._parse_decision_output(output)
        if action is None:
            print(
                f"[interactive] decision CLI returned unparseable output: {output!r}; "
                "falling back to manual choice.",
                flush=True,
            )
            return self._ask_user_for_action(note)
        return action

    def _build_decision_prompt(self, stage_label: str, note: str) -> str:
        return textwrap.dedent(
            f"""
            You are routing a human editor's note about a pipeline stage to one of three actions.

            Stage: {stage_label}

            Actions:
            - continue: the note is positive or neutral and the pipeline should advance to the next stage.
            - revise: the note flags issues that need to be addressed; the same artifact should be regenerated with the note as guidance, keeping the existing draft as a starting point.
            - rewrite: the note indicates the artifact is fundamentally wrong and should be regenerated from scratch.

            Reply with a single JSON object on one line, with key "action" and value one of "continue", "revise", "rewrite". No prose, no markdown fence.

            Editor note:
            <<<
            {note}
            >>>
            """
        ).strip()

    def _invoke_decision_cli(self, prompt: str) -> str:
        cmd = [
            self._decision_bin,
            "-p",
            "--output-format",
            "text",
            "--no-session-persistence",
            "--dangerously-skip-permissions",
        ]
        env = os.environ.copy()
        proc = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        if proc.returncode != 0:
            raise subprocess.SubprocessError(
                f"claude exit {proc.returncode}: {proc.stderr.strip()[:200]}"
            )
        return proc.stdout.strip()

    @staticmethod
    def _parse_decision_output(output: str) -> str | None:
        text = output.strip()
        # Try JSON first.
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                action = str(data.get("action", "")).strip().lower()
                if action in VALID_ACTIONS:
                    return action
        except (json.JSONDecodeError, ValueError):
            pass
        # Fallback: scan for a bare keyword.
        lowered = text.lower()
        for action in VALID_ACTIONS:
            if action in lowered:
                return action
        return None

    @staticmethod
    def _ask_user_for_action(note: str) -> str:
        del note
        prompt = (
            "[interactive] choose action manually: "
            "[c]ontinue / [r]evise / [w] rewrite > "
        )
        while True:
            try:
                choice = input(prompt).strip().lower()
            except EOFError:
                return "continue"
            if choice in ("", "c", "continue"):
                return "continue"
            if choice in ("r", "revise"):
                return "revise"
            if choice in ("w", "rw", "rewrite"):
                return "rewrite"
            print("Please enter one of c / r / w.", flush=True)

    @staticmethod
    def _resolve_decision_bin() -> str | None:
        env_bin = os.environ.get("CLAUDE_BIN")
        if env_bin and Path(env_bin).is_file() and os.access(env_bin, os.X_OK):
            return env_bin
        return shutil.which("claude")


def main() -> int:
    try:
        args = parse_args()
        cfg = build_config(REPO_ROOT, args)
        runner = InteractivePipelineRunner(repo_root=REPO_ROOT, cfg=cfg)
        return runner.run()
    except PipelineError as exc:
        print(f"[interactive-pipeline][error] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
