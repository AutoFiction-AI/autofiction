from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import export_run_to_artifacts as export_module


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class ExportRunToArtifactsTests(unittest.TestCase):
    def test_export_copies_status_and_new_pipeline_outputs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="export_run_", dir="/tmp") as tmp:
            tmp_path = Path(tmp)
            run_dir = tmp_path / "run"
            artifacts_root = tmp_path / "artifacts"
            (run_dir / "outline").mkdir(parents=True, exist_ok=True)
            (run_dir / "outline" / "title.txt").write_text(
                "Secondhand Thoughts\n",
                encoding="utf-8",
            )
            (run_dir / "FINAL_NOVEL.md").write_text(
                "# Secondhand Thoughts\n\nBody.\n",
                encoding="utf-8",
            )
            (run_dir / "input" / "premise.txt").parent.mkdir(parents=True, exist_ok=True)
            (run_dir / "input" / "premise.txt").write_text("Premise.\n", encoding="utf-8")
            (run_dir / "premise" / "selected_premise.txt").parent.mkdir(
                parents=True, exist_ok=True
            )
            (run_dir / "premise" / "selected_premise.txt").write_text(
                "Premise.\n",
                encoding="utf-8",
            )
            _write_json(run_dir / "outline" / "spatial_layout.json", {"layout": {}})
            _write_json(
                run_dir / "outline" / "outline_review_cycle_01.json",
                {"cycle": 1, "summary": "ok"},
            )
            (run_dir / "outline" / "pre_revision" / "cycle_01").mkdir(
                parents=True, exist_ok=True
            )
            (run_dir / "outline" / "pre_revision" / "cycle_01" / "outline.md").write_text(
                "Original outline.\n",
                encoding="utf-8",
            )
            _write_json(
                run_dir / "status" / "cycle_01" / "cycle_status.json",
                {"cycle": 1, "stages": {"llm_aggregator": {"status": "complete"}}},
            )
            _write_json(
                run_dir / "status" / "cycle_01" / "quality_summary.json",
                {"cycle": 1, "quality": "ok"},
            )
            _write_json(
                run_dir / "packets" / "cycle_01" / "aggregation_decisions.json",
                {"cycle": 1, "canonical_choices": []},
            )
            _write_json(
                run_dir / "packets" / "cycle_01" / "aggregation_materialization_summary.json",
                {"cycle": 1, "status": "complete"},
            )
            _write_json(
                run_dir / "reports" / "final_status.json",
                {
                    "status": "PASS",
                    "completed_at_utc": "2026-03-29T21:22:36Z",
                    "terminal_reason": "max_cycles_reached",
                    "final_novel_file": "FINAL_NOVEL.md",
                    "chapter_count": 17,
                    "success_cycle": 3,
                    "min_cycles": 2,
                    "max_cycles": 3,
                    "add_cycles": 1,
                    "base_completed_cycles": 2,
                    "validation_mode": "lenient",
                },
            )
            _write_json(run_dir / "reports" / "final_report.json", {"status": "PASS"})
            _write_json(
                run_dir / "config" / "run_config.json",
                {
                    "provider": "codex",
                    "model": "gpt-5.4",
                    "reasoning_effort": "xhigh",
                    "premise_mode": "user",
                    "final_cycle_global_only": True,
                    "local_window_size": 4,
                    "local_window_overlap": 2,
                    "stage_profiles": {
                        "outline": {
                            "provider": "claude",
                            "model": "claude-opus-4-6",
                            "reasoning_effort": "max",
                        },
                        "review": {
                            "provider": "codex",
                            "model": "gpt-5.4",
                            "reasoning_effort": "xhigh",
                        },
                        "full_review": {
                            "provider": "claude",
                            "model": "claude-opus-4-6",
                            "reasoning_effort": "max",
                        },
                        "cross_chapter_audit": {
                            "provider": "claude",
                            "model": "claude-opus-4-6",
                            "reasoning_effort": "max",
                        },
                        "revision": {
                            "provider": "codex",
                            "model": "gpt-5.4",
                            "reasoning_effort": "xhigh",
                        },
                        "llm_aggregator": {
                            "provider": "claude",
                            "model": "claude-opus-4-6",
                            "reasoning_effort": "max",
                        },
                    },
                    "revision_pass_profiles": {
                        "p2_dialogue_idiolect_cadence": {
                            "provider": "claude",
                            "model": "claude-opus-4-6",
                            "reasoning_effort": "max",
                        }
                    },
                },
            )

            dest_dir = export_module.export_run_to_artifacts(run_dir, artifacts_root)

            self.assertEqual(
                dest_dir,
                (artifacts_root / "books" / "secondhand_thoughts").resolve(),
            )
            self.assertTrue((dest_dir / "FINAL_NOVEL.md").is_file())
            self.assertTrue((dest_dir / "status" / "cycle_01" / "cycle_status.json").is_file())
            self.assertTrue((dest_dir / "outline" / "spatial_layout.json").is_file())
            self.assertTrue(
                (dest_dir / "outline" / "pre_revision" / "cycle_01" / "outline.md").is_file()
            )
            self.assertTrue(
                (dest_dir / "packets" / "cycle_01" / "aggregation_decisions.json").is_file()
            )

            metadata = json.loads((dest_dir / "generation_metadata.json").read_text())
            self.assertEqual(metadata["schema_version"], 2)
            self.assertEqual(metadata["title"], "Secondhand Thoughts")
            self.assertEqual(metadata["run_status"], "PASS")
            self.assertTrue(metadata["final_cycle_global_only"])
            self.assertEqual(metadata["local_window_size"], 4)
            self.assertEqual(metadata["local_window_overlap"], 2)
            self.assertIn("status", metadata["exported_dirs"])
            self.assertEqual(metadata["stages"]["outline"]["provider"], "claude")
            self.assertEqual(metadata["stages"]["llm_aggregator"]["provider"], "claude")
            self.assertEqual(
                metadata["revision_passes"]["p2_dialogue_idiolect_cadence"]["provider"],
                "claude",
            )


if __name__ == "__main__":
    unittest.main()
