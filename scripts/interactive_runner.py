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

import dataclasses
import difflib
import json
import os
import re
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
        # Interactive mode: the human checkpoint after the outline stage IS
        # the review. Suppress the parent's automatic LLM outline_review /
        # outline_revision cycles so the human sees the freshly generated
        # outline before any LLM critique fires.
        if not getattr(cfg, "skip_outline_review", False):
            cfg = dataclasses.replace(cfg, skip_outline_review=True)
        super().__init__(repo_root=repo_root, cfg=cfg)
        self._annotations_dir = self.run_dir / "annotations"
        self._pending_outline_notes: str | None = None
        self._pending_chapter_notes: dict[str, str] = {}
        self._pending_review_notes: dict[int, str] = {}
        self._pending_revision_notes: dict[int, str] = {}
        self._current_cycle: int | None = None
        self._decision_bin = self._resolve_decision_bin()
        # Snapshot of artifact text at the moment the human asked for a
        # revise/rewrite, keyed by run-relative path. Used to render a
        # within-checkpoint diff once the regenerated artifact appears.
        self._prior_artifacts: dict[str, str] = {}

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
            self._snapshot_paths(self._outline_read_paths())
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
                self._snapshot_paths([chapter_rel])
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
                self._snapshot_paths(self._review_read_paths(cycle))
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
                self._snapshot_paths(self._revision_read_paths(cycle))
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

        digest = self._build_digest(stage_label)
        if digest:
            print(f"\n--- DIGEST ---\n{digest}", flush=True)

        diff = self._build_diff(stage_label, read_paths)
        if diff:
            print(f"\n--- DIFF vs. prior version ---\n{diff}", flush=True)

        if read_paths:
            print("\nRaw files (paths relative to run_dir):", flush=True)
            for idx, rel in enumerate(read_paths, start=1):
                print(f"  [{idx}] {rel}", flush=True)

        print(
            "\nCommands while typing your annotation:\n"
            "  /r N        — dump raw file [N] inline (then keep typing)\n"
            "  /r <path>   — dump a specific file inline\n"
            "  /list       — re-show the file index\n"
            "  /help       — show this command list\n"
            "Type your free-text annotation about what works and what does "
            "not. Be specific. Empty input is interpreted as 'continue'.",
            flush=True,
        )
        print(
            "End your annotation with a line containing only `.` (a single period) "
            "or press Ctrl-D.",
            flush=True,
        )
        print(bar, flush=True)

        note = self._read_annotation_with_commands(read_paths)
        note = note.strip()

        if not note:
            print("[interactive] empty annotation -> continue", flush=True)
            self._persist_annotation(key, "continue", note)
            return "continue", ""

        action = self._decide_action(stage_label, note)
        print(f"[interactive] decided action: {action}", flush=True)
        self._persist_annotation(key, action, note)
        return action, note

    def _read_annotation_with_commands(self, read_paths: list[str]) -> str:
        """Read a multiline annotation with inline /r-style commands.

        Lines that start with `/` are treated as commands and never appear
        in the returned annotation. A line containing only `.` or EOF
        terminates the annotation.
        """
        lines: list[str] = []
        try:
            while True:
                line = input()
                stripped = line.strip()
                if stripped == ".":
                    break
                if stripped.startswith("/"):
                    self._handle_checkpoint_command(stripped, read_paths)
                    continue
                lines.append(line)
        except EOFError:
            pass
        return "\n".join(lines)

    def _handle_checkpoint_command(
        self, command: str, read_paths: list[str]
    ) -> None:
        parts = command.split(None, 1)
        head = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""
        if head in ("/help", "/?"):
            print(
                "  /r N        — dump raw file [N] inline\n"
                "  /r <path>   — dump a specific run-relative file\n"
                "  /list       — re-show the file index\n"
                "  /help       — this list\n"
                "  .           — finish annotation",
                flush=True,
            )
            return
        if head in ("/list", "/l"):
            if not read_paths:
                print("  (no files listed at this checkpoint)", flush=True)
                return
            for idx, rel in enumerate(read_paths, start=1):
                print(f"  [{idx}] {rel}", flush=True)
            return
        if head in ("/r", "/read"):
            if not arg:
                print("  usage: /r <index>  or  /r <path>", flush=True)
                return
            target: Path | None = None
            label: str = arg
            if arg.isdigit():
                i = int(arg)
                if 1 <= i <= len(read_paths):
                    label = read_paths[i - 1]
                    target = self.run_dir / label
                else:
                    print(
                        f"  no file at index {i} (range 1..{len(read_paths)})",
                        flush=True,
                    )
                    return
            else:
                target = self.run_dir / arg
            if target is None or not target.is_file():
                print(f"  file not found: {label}", flush=True)
                return
            self._dump_file_to_tty(target, label)
            return
        print(f"  unknown command: {head}. Try /help.", flush=True)

    def _dump_file_to_tty(self, path: Path, label: str) -> None:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            print(f"  could not read {label}: {exc}", flush=True)
            return
        bar = "-" * 72
        print(f"\n{bar}\n>>> {label}\n{bar}", flush=True)
        # Pretty-print JSON if it parses; otherwise dump as-is.
        if path.suffix == ".json":
            try:
                data = json.loads(text)
                text = json.dumps(data, indent=2, ensure_ascii=False)
            except (json.JSONDecodeError, ValueError):
                pass
        print(text, flush=True)
        print(f"{bar}\n<<< end {label}\n", flush=True)

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
    # Digest + diff: pre-read summaries so the human doesn't have to open
    # every artifact to form an opinion.
    # ------------------------------------------------------------------

    def _snapshot_paths(self, rels: list[str]) -> None:
        for rel in rels:
            path = self.run_dir / rel
            if not path.is_file():
                continue
            try:
                self._prior_artifacts[rel] = path.read_text(
                    encoding="utf-8", errors="replace"
                )
            except OSError:
                continue

    def _build_digest(self, stage_label: str) -> str:
        try:
            if stage_label == "outline":
                return self._digest_outline()
            if stage_label.startswith("chapter_draft:"):
                return self._digest_chapter_draft(
                    stage_label.split(":", 1)[1]
                )
            if stage_label.startswith("chapter_review_cycle_"):
                cycle = int(stage_label.rsplit("_", 1)[1])
                return self._digest_review_cycle(cycle)
            if stage_label.startswith("revision_cycle_"):
                cycle = int(stage_label.rsplit("_", 1)[1])
                return self._digest_revision_cycle(cycle)
        except Exception as exc:  # noqa: BLE001 — digest must never crash the harness
            return f"(digest unavailable: {exc})"
        return ""

    def _build_diff(self, stage_label: str, read_paths: list[str]) -> str:
        try:
            if stage_label == "outline":
                return self._diff_text_artifact("outline/outline.md")
            if stage_label.startswith("chapter_draft:"):
                rel = f"chapters/{stage_label.split(':', 1)[1]}.md"
                return self._diff_text_artifact(rel)
            if stage_label.startswith("chapter_review_cycle_"):
                cycle = int(stage_label.rsplit("_", 1)[1])
                return self._diff_review_cycle(cycle)
            if stage_label.startswith("revision_cycle_"):
                cycle = int(stage_label.rsplit("_", 1)[1])
                return self._diff_revision_cycle(cycle)
        except Exception as exc:  # noqa: BLE001
            return f"(diff unavailable: {exc})"
        return ""

    # ---- per-stage digests -------------------------------------------

    def _digest_outline(self) -> str:
        lines: list[str] = []
        outline_md = self._read_run_text("outline/outline.md")
        if outline_md:
            words = len(outline_md.split())
            chapter_titles = self._extract_outline_chapter_titles(outline_md)
            lines.append(f"outline.md: {words:,} words")
            if chapter_titles:
                lines.append(f"chapters in outline.md: {len(chapter_titles)}")
                for title in chapter_titles[:30]:
                    lines.append(f"  - {title}")
                if len(chapter_titles) > 30:
                    lines.append(f"  ...and {len(chapter_titles) - 30} more")

        specs_jsonl = self._read_run_text("outline/chapter_specs.jsonl")
        if specs_jsonl:
            count = 0
            target_words = 0
            for raw in specs_jsonl.splitlines():
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    spec = json.loads(raw)
                except (json.JSONDecodeError, ValueError):
                    continue
                count += 1
                target_words += int(spec.get("projected_min_words") or 0)
            if count:
                lines.append(
                    f"chapter_specs.jsonl: {count} specs"
                    + (
                        f", min target ~{target_words:,} words"
                        if target_words
                        else ""
                    )
                )

        scene_tsv = self._read_run_text("outline/scene_plan.tsv")
        if scene_tsv:
            rows = [r for r in scene_tsv.splitlines() if r.strip()]
            data_rows = rows[1:] if len(rows) > 1 else []
            lines.append(f"scene_plan.tsv: {len(data_rows)} scenes")

        sb = self._read_run_json("outline/style_bible.json")
        if isinstance(sb, dict):
            profiles = sb.get("character_voice_profiles") or []
            if isinstance(profiles, list):
                names = [
                    str(p.get("character_id") or "?")
                    for p in profiles
                    if isinstance(p, dict)
                ]
                if names:
                    lines.append(
                        "style_bible characters: "
                        + ", ".join(names[:20])
                        + (f" (+{len(names) - 20})" if len(names) > 20 else "")
                    )

        spatial = self._read_run_json("outline/spatial_layout.json")
        if isinstance(spatial, dict):
            locs = spatial.get("locations") or spatial.get("places") or []
            if isinstance(locs, list) and locs:
                lines.append(f"spatial_layout locations: {len(locs)}")

        return "\n".join(lines)

    @staticmethod
    def _extract_outline_chapter_titles(text: str) -> list[str]:
        # Match the outline convention "**Chapter N — Title**" anchored at
        # the start of a line, so register-marker bullets like
        # "- **Chapter 7 — phoneme-displacement register**" inside body
        # paragraphs are not picked up. The title runs from the en/em dash
        # to the first closing `**` on the same line (chapter 9's italic
        # parenthetical after the closing `**` is correctly excluded).
        pattern = re.compile(
            r"^\*\*Chapter\s+(\d+)\s*[—\-–]\s*([^*\n]+?)\*\*",
            re.IGNORECASE | re.MULTILINE,
        )
        seen: set[str] = set()
        titles: list[str] = []
        for match in pattern.finditer(text):
            num = match.group(1)
            if num in seen:
                continue
            seen.add(num)
            title = match.group(2).strip()
            titles.append(f"Chapter {num} — {title}")
        return titles

    def _digest_chapter_draft(self, chapter_id: str) -> str:
        rel = f"chapters/{chapter_id}.md"
        text = self._read_run_text(rel)
        if not text:
            return f"(no content at {rel})"
        word_count = len(text.split())
        line_count = text.count("\n") + 1
        # Count scene breaks (loose heuristic: blank-line-separated `#` or
        # `## Scene` headers, or `***` separators).
        scene_breaks = (
            len(re.findall(r"(?m)^\s*\*\s*\*\s*\*\s*$", text))
            + len(re.findall(r"(?m)^##\s", text))
        )
        head_lines = self._first_nonempty_lines(text, 6)
        tail_lines = self._last_nonempty_lines(text, 4)
        prior = self._prior_artifacts.get(rel)
        delta = ""
        if prior is not None:
            prior_words = len(prior.split())
            delta = f"  (Δ {word_count - prior_words:+,} words vs. prior)"

        out = [
            f"{rel}: {word_count:,} words, {line_count} lines, ~{scene_breaks} scene breaks{delta}",
            "",
            "head:",
        ]
        out.extend(f"  > {ln}" for ln in head_lines)
        out.append("")
        out.append("tail:")
        out.extend(f"  > {ln}" for ln in tail_lines)
        return "\n".join(out)

    @staticmethod
    def _first_nonempty_lines(text: str, n: int) -> list[str]:
        out: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            out.append(stripped[:160])
            if len(out) >= n:
                break
        return out

    @staticmethod
    def _last_nonempty_lines(text: str, n: int) -> list[str]:
        out: list[str] = []
        for line in reversed(text.splitlines()):
            stripped = line.strip()
            if not stripped:
                continue
            out.append(stripped[:160])
            if len(out) >= n:
                break
        return list(reversed(out))

    def _digest_review_cycle(self, cycle: int) -> str:
        cpad = self._cpad(cycle)
        review_dir = self.run_dir / "reviews" / f"cycle_{cpad}"
        if not review_dir.is_dir():
            return f"(no reviews/cycle_{cpad}/ directory)"
        files = sorted(review_dir.glob("*.review.json"))
        if not files:
            return f"(no chapter_*.review.json files in reviews/cycle_{cpad}/)"

        lines: list[str] = [f"cycle {cpad}: {len(files)} chapter review(s)"]
        for path in files:
            data = self._load_json(path)
            if not isinstance(data, dict):
                lines.append(f"  {path.name}: (unparseable)")
                continue
            chap = data.get("chapter_id", path.stem.split(".")[0])
            verdicts = data.get("verdicts") or {}
            verdict_summary = " ".join(
                f"{k}={v}" for k, v in sorted(verdicts.items())
            ) if isinstance(verdicts, dict) else ""
            findings = data.get("findings") or []
            counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0}
            for f in findings if isinstance(findings, list) else []:
                if not isinstance(f, dict):
                    continue
                sev = str(f.get("severity", "")).strip().upper()
                if sev in counts:
                    counts[sev] += 1
            counts_str = (
                f"CRIT={counts['CRITICAL']} HIGH={counts['HIGH']} "
                f"MED={counts['MEDIUM']} (total {len(findings)})"
            )
            lines.append(f"  {chap}: {verdict_summary} | {counts_str}")

            # Top findings: critical > high > medium, capped.
            top: list[dict[str, Any]] = []
            for sev_order in ("CRITICAL", "HIGH", "MEDIUM"):
                for f in findings if isinstance(findings, list) else []:
                    if not isinstance(f, dict):
                        continue
                    if str(f.get("severity", "")).strip().upper() == sev_order:
                        top.append(f)
                    if len(top) >= 3:
                        break
                if len(top) >= 3:
                    break
            for f in top:
                src = f.get("source", "?")
                sev = f.get("severity", "?")
                problem = str(f.get("problem", "")).split(".")[0]
                if len(problem) > 140:
                    problem = problem[:137] + "..."
                lines.append(f"    [{sev}/{src}] {problem}")
            summary = data.get("summary")
            if isinstance(summary, str) and summary.strip():
                short = summary.strip().replace("\n", " ")
                if len(short) > 220:
                    short = short[:217] + "..."
                lines.append(f"    summary: {short}")
        return "\n".join(lines)

    def _digest_revision_cycle(self, cycle: int) -> str:
        cpad = self._cpad(cycle)
        rev_dir = self.run_dir / "revisions" / f"cycle_{cpad}"
        if not rev_dir.is_dir():
            return f"(no revisions/cycle_{cpad}/ directory)"
        # The canonical per-chapter report is named `<chapter_id>.revision_report.json`.
        # Pass-level files (`<chapter_id>.<pass>.revision_report.json`) are not
        # surfaced here.
        files = sorted(
            p
            for p in rev_dir.glob("*.revision_report.json")
            if p.stem.count(".") == 1  # chapter_NN.revision_report
        )
        if not files:
            files = sorted(rev_dir.glob("*.revision_report.json"))
        if not files:
            return f"(no revision_report.json files in revisions/cycle_{cpad}/)"

        snapshot_rel = f"snapshots/cycle_{cpad}/FINAL_NOVEL.post_revision.md"
        snap_text = self._read_run_text(snapshot_rel)
        lines: list[str] = [f"cycle {cpad}: {len(files)} chapter revision report(s)"]
        if snap_text:
            lines.append(
                f"{snapshot_rel}: {len(snap_text.split()):,} words"
            )
        for path in files:
            data = self._load_json(path)
            if not isinstance(data, dict):
                lines.append(f"  {path.name}: (unparseable)")
                continue
            chap = data.get("chapter_id", path.stem.split(".")[0])
            results = data.get("finding_results") or []
            counts = {"FIXED": 0, "PARTIAL": 0, "UNRESOLVED": 0}
            for r in results if isinstance(results, list) else []:
                if not isinstance(r, dict):
                    continue
                st = str(r.get("status_after_revision", "")).strip().upper()
                if st in counts:
                    counts[st] += 1
            total = sum(counts.values())
            chap_rel = f"revisions/cycle_{cpad}/{chap}.md"
            new_text = self._read_run_text(chap_rel)
            wd = ""
            if new_text is not None:
                wd = f", {len(new_text.split()):,} words"
            lines.append(
                f"  {chap}: FIXED={counts['FIXED']} PARTIAL={counts['PARTIAL']} "
                f"UNRESOLVED={counts['UNRESOLVED']} (of {total}){wd}"
            )
            unresolved_notes = [
                str(r.get("revision_note", "")).strip()
                for r in (results if isinstance(results, list) else [])
                if isinstance(r, dict)
                and str(r.get("status_after_revision", "")).strip().upper()
                in {"PARTIAL", "UNRESOLVED"}
                and str(r.get("revision_note", "")).strip()
            ]
            for note_text in unresolved_notes[:2]:
                short = note_text.replace("\n", " ")
                if len(short) > 180:
                    short = short[:177] + "..."
                lines.append(f"    note: {short}")
            summary = data.get("summary")
            if isinstance(summary, str) and summary.strip():
                short = summary.strip().replace("\n", " ")
                if len(short) > 220:
                    short = short[:217] + "..."
                lines.append(f"    summary: {short}")
        return "\n".join(lines)

    # ---- per-stage diffs ---------------------------------------------

    def _diff_text_artifact(self, rel: str) -> str:
        prior = self._prior_artifacts.get(rel)
        if prior is None:
            return ""
        current = self._read_run_text(rel)
        if current is None:
            return ""
        if prior == current:
            return "(no textual change from prior version)"
        return self._format_unified_diff(prior, current, rel, max_lines=80)

    @staticmethod
    def _format_unified_diff(
        prior: str, current: str, label: str, *, max_lines: int = 80
    ) -> str:
        diff_iter = difflib.unified_diff(
            prior.splitlines(),
            current.splitlines(),
            fromfile=f"{label} (prior)",
            tofile=f"{label} (current)",
            n=2,
            lineterm="",
        )
        out: list[str] = []
        for i, dline in enumerate(diff_iter):
            if i >= max_lines:
                out.append(f"... (diff truncated at {max_lines} lines)")
                break
            out.append(dline)
        return "\n".join(out)

    def _diff_review_cycle(self, cycle: int) -> str:
        """Compare this cycle's reviews to the just-rejected snapshot (if any)
        or to the previous cycle's reviews on disk."""
        cpad = self._cpad(cycle)
        review_dir = self.run_dir / "reviews" / f"cycle_{cpad}"
        if not review_dir.is_dir():
            return ""
        per_chapter: list[str] = []
        for path in sorted(review_dir.glob("*.review.json")):
            rel = str(path.relative_to(self.run_dir))
            cur = self._load_json(path)
            if not isinstance(cur, dict):
                continue
            chap = cur.get("chapter_id", path.stem.split(".")[0])
            prior_text = self._prior_artifacts.get(rel)
            prior_data: dict[str, Any] | None = None
            prior_origin = "(no prior version)"
            if prior_text is not None:
                try:
                    parsed = json.loads(prior_text)
                    if isinstance(parsed, dict):
                        prior_data = parsed
                        prior_origin = "vs. rejected previous attempt"
                except (json.JSONDecodeError, ValueError):
                    pass
            if prior_data is None and cycle > 1:
                prev_path = (
                    self.run_dir
                    / "reviews"
                    / f"cycle_{self._cpad(cycle - 1)}"
                    / path.name
                )
                prev = self._load_json(prev_path)
                if isinstance(prev, dict):
                    prior_data = prev
                    prior_origin = f"vs. cycle_{self._cpad(cycle - 1)}"
            if prior_data is None:
                continue
            per_chapter.append(
                self._format_review_chapter_diff(chap, prior_data, cur, prior_origin)
            )
        return "\n".join(per_chapter)

    @staticmethod
    def _format_review_chapter_diff(
        chap: str,
        prior: dict[str, Any],
        current: dict[str, Any],
        origin: str,
    ) -> str:
        def _verdicts(d: dict[str, Any]) -> dict[str, str]:
            v = d.get("verdicts")
            return v if isinstance(v, dict) else {}

        def _finding_ids(d: dict[str, Any]) -> dict[str, dict[str, Any]]:
            out: dict[str, dict[str, Any]] = {}
            for f in d.get("findings") or []:
                if isinstance(f, dict):
                    fid = str(f.get("finding_id", "")).strip()
                    if fid:
                        out[fid] = f
            return out

        flips: list[str] = []
        prior_v = _verdicts(prior)
        cur_v = _verdicts(current)
        for k in sorted(set(prior_v) | set(cur_v)):
            if prior_v.get(k) != cur_v.get(k):
                flips.append(f"{k}: {prior_v.get(k, '?')}→{cur_v.get(k, '?')}")

        prior_ids = _finding_ids(prior)
        cur_ids = _finding_ids(current)
        added = sorted(set(cur_ids) - set(prior_ids))
        removed = sorted(set(prior_ids) - set(cur_ids))

        head = f"  {chap} {origin}: "
        bits: list[str] = []
        if flips:
            bits.append("verdicts " + ", ".join(flips))
        else:
            bits.append("verdicts unchanged")
        bits.append(f"+{len(added)}/-{len(removed)} findings")
        out = [head + " | ".join(bits)]
        for fid in added[:4]:
            f = cur_ids[fid]
            sev = f.get("severity", "?")
            src = f.get("source", "?")
            problem = str(f.get("problem", "")).split(".")[0]
            if len(problem) > 140:
                problem = problem[:137] + "..."
            out.append(f"    + [{sev}/{src}] {fid}: {problem}")
        if len(added) > 4:
            out.append(f"    + ...and {len(added) - 4} more")
        for fid in removed[:4]:
            out.append(f"    - {fid}")
        if len(removed) > 4:
            out.append(f"    - ...and {len(removed) - 4} more")
        return "\n".join(out)

    def _diff_revision_cycle(self, cycle: int) -> str:
        cpad = self._cpad(cycle)
        rev_dir = self.run_dir / "revisions" / f"cycle_{cpad}"
        if not rev_dir.is_dir():
            return ""
        per_chapter: list[str] = []
        for path in sorted(rev_dir.glob("*.revision_report.json")):
            if path.stem.count(".") != 1:
                continue  # skip pass-level files
            rel = str(path.relative_to(self.run_dir))
            cur = self._load_json(path)
            if not isinstance(cur, dict):
                continue
            chap = cur.get("chapter_id", path.stem.split(".")[0])
            prior_text = self._prior_artifacts.get(rel)
            prior_data: dict[str, Any] | None = None
            prior_origin = "(no prior version)"
            if prior_text is not None:
                try:
                    parsed = json.loads(prior_text)
                    if isinstance(parsed, dict):
                        prior_data = parsed
                        prior_origin = "vs. rejected previous attempt"
                except (json.JSONDecodeError, ValueError):
                    pass
            if prior_data is None and cycle > 1:
                prev_path = (
                    self.run_dir
                    / "revisions"
                    / f"cycle_{self._cpad(cycle - 1)}"
                    / path.name
                )
                prev = self._load_json(prev_path)
                if isinstance(prev, dict):
                    prior_data = prev
                    prior_origin = f"vs. cycle_{self._cpad(cycle - 1)}"
            if prior_data is None:
                continue
            per_chapter.append(
                self._format_revision_chapter_diff(
                    chap, prior_data, cur, prior_origin
                )
            )
        return "\n".join(per_chapter)

    @staticmethod
    def _format_revision_chapter_diff(
        chap: str,
        prior: dict[str, Any],
        current: dict[str, Any],
        origin: str,
    ) -> str:
        def _status_counts(d: dict[str, Any]) -> dict[str, int]:
            counts = {"FIXED": 0, "PARTIAL": 0, "UNRESOLVED": 0}
            for r in d.get("finding_results") or []:
                if not isinstance(r, dict):
                    continue
                s = str(r.get("status_after_revision", "")).strip().upper()
                if s in counts:
                    counts[s] += 1
            return counts

        pc = _status_counts(prior)
        cc = _status_counts(current)
        deltas = ", ".join(
            f"{k}: {pc[k]}→{cc[k]}" for k in ("FIXED", "PARTIAL", "UNRESOLVED")
        )
        return f"  {chap} {origin}: {deltas}"

    # ---- small IO helpers --------------------------------------------

    def _read_run_text(self, rel: str) -> str | None:
        path = self.run_dir / rel
        if not path.is_file():
            return None
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None

    def _read_run_json(self, rel: str) -> Any:
        text = self._read_run_text(rel)
        if text is None:
            return None
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return None

    @staticmethod
    def _load_json(path: Path) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, json.JSONDecodeError, ValueError):
            return None

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
