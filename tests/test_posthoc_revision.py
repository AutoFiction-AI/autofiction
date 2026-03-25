from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import posthoc_revision as posthoc_revision_module
import runner as runner_module


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class PosthocRevisionTests(unittest.TestCase):
    def test_resolve_source_run_prefers_source_run_txt(self) -> None:
        with tempfile.TemporaryDirectory(prefix="posthoc_source_", dir="/tmp") as tmp:
            novel_dir = Path(tmp)
            source_run_dir = novel_dir / "actual_run"
            source_run_dir.mkdir()
            (novel_dir / "source_run.txt").write_text(
                str(source_run_dir) + "\n",
                encoding="utf-8",
            )
            _write_json(
                novel_dir / "generation_metadata.json",
                {"source_run": "/tmp/other_run"},
            )

            resolved = posthoc_revision_module._resolve_source_run_dir(novel_dir, "")

            self.assertEqual(resolved, source_run_dir.resolve())

    def test_resolve_baseline_prefers_final_novel_md(self) -> None:
        with tempfile.TemporaryDirectory(prefix="posthoc_baseline_", dir="/tmp") as tmp:
            novel_dir = Path(tmp)
            primary = novel_dir / "FINAL_NOVEL.md"
            secondary = novel_dir / "FINAL_NOVEL.manual_rescue.md"
            primary.write_text("primary\n", encoding="utf-8")
            secondary.write_text("secondary\n", encoding="utf-8")

            resolved = posthoc_revision_module._resolve_baseline_file(novel_dir, "")

            self.assertEqual(resolved, primary)

    def test_verify_baseline_matches_compiled_chapters(self) -> None:
        with tempfile.TemporaryDirectory(prefix="posthoc_match_", dir="/tmp") as tmp:
            tmp_path = Path(tmp)
            chapters_dir = tmp_path / "chapters"
            chapters_dir.mkdir()
            (chapters_dir / "chapter_01.md").write_text("# Chapter 1\n\nA.\n", encoding="utf-8")
            (chapters_dir / "chapter_02.md").write_text("# Chapter 2\n\nB.\n", encoding="utf-8")
            baseline_file = tmp_path / "FINAL_NOVEL.md"
            baseline_file.write_text(
                "# Test Title\n\n# Chapter 1\n\nA.\n\n\n# Chapter 2\n\nB.\n",
                encoding="utf-8",
            )

            specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1,
                    chapter_engine="engine",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="mode",
                    scene_count_target=1,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                ),
                runner_module.ChapterSpec(
                    chapter_id="chapter_02",
                    chapter_number=2,
                    projected_min_words=1,
                    chapter_engine="engine",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="mode",
                    scene_count_target=1,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                ),
            ]

            matched = posthoc_revision_module._verify_baseline_matches_chapters(
                baseline_file=baseline_file,
                title="Test Title",
                chapter_specs=specs,
                chapters_dir=chapters_dir,
                allow_mismatch=False,
            )

            self.assertTrue(matched)

    def test_verify_baseline_mismatch_raises_without_override(self) -> None:
        with tempfile.TemporaryDirectory(prefix="posthoc_mismatch_", dir="/tmp") as tmp:
            tmp_path = Path(tmp)
            chapters_dir = tmp_path / "chapters"
            chapters_dir.mkdir()
            (chapters_dir / "chapter_01.md").write_text("# Chapter 1\n\nA.\n", encoding="utf-8")
            baseline_file = tmp_path / "FINAL_NOVEL.md"
            baseline_file.write_text("# Wrong Title\n\n# Chapter 1\n\nB.\n", encoding="utf-8")
            specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1,
                    chapter_engine="engine",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="mode",
                    scene_count_target=1,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
            ]

            with self.assertRaises(runner_module.PipelineError):
                posthoc_revision_module._verify_baseline_matches_chapters(
                    baseline_file=baseline_file,
                    title="Test Title",
                    chapter_specs=specs,
                    chapters_dir=chapters_dir,
                    allow_mismatch=False,
                )
