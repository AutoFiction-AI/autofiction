from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import lint_chapter_text as lint_module


class LintChapterTextTests(unittest.TestCase):
    def test_interrogative_dialogue_without_question_mark_is_reported(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lint_qmark_", dir="/tmp") as tmp:
            chapter = Path(tmp) / "chapter_01.md"
            chapter.write_text(
                '# Chapter 1\n\n"What do you mean," she said.\n',
                encoding="utf-8",
            )

            report = lint_module.lint_chapter_file(chapter)

            self.assertEqual(report["chapter_id"], "chapter_01")
            self.assertEqual(report["findings"][0]["type"], "interrogative_missing_qmark")
            self.assertFalse(report["findings"][0]["auto_fixed"])

    def test_stray_list_marker_is_auto_fixed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lint_list_", dir="/tmp") as tmp:
            chapter = Path(tmp) / "chapter_01.md"
            chapter.write_text(
                "# Chapter 1\n\n- This should be a prose sentence.\n",
                encoding="utf-8",
            )

            report = lint_module.lint_chapter_file(chapter)

            self.assertEqual(report["findings"][0]["type"], "stray_list_marker")
            self.assertTrue(report["findings"][0]["auto_fixed"])
            self.assertNotIn("- This should be a prose sentence.", chapter.read_text(encoding="utf-8"))
            self.assertIn("This should be a prose sentence.", chapter.read_text(encoding="utf-8"))

    def test_clean_text_produces_no_findings(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lint_clean_", dir="/tmp") as tmp:
            chapter = Path(tmp) / "chapter_01.md"
            chapter.write_text(
                '# Chapter 1\n\n"Can you stay?" she asked.\nHe nodded.\n',
                encoding="utf-8",
            )

            report = lint_module.lint_chapter_file(chapter)

            self.assertEqual(report["findings"], [])

    def test_exclamative_what_phrase_does_not_false_fire(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lint_exclamative_", dir="/tmp") as tmp:
            chapter = Path(tmp) / "chapter_01.md"
            chapter.write_text(
                '# Chapter 1\n\n"What a mess," she said.\n',
                encoding="utf-8",
            )

            report = lint_module.lint_chapter_file(chapter)

            self.assertEqual(report["findings"], [])


if __name__ == "__main__":
    unittest.main()
