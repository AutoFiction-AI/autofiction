from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "scripts" / "runner.py"


def run_pipeline(*args: str) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(RUNNER), *args]
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class SmokeTests(unittest.TestCase):
    def test_user_premise_dry_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_user_", dir="/tmp") as tmp:
            run_dir = Path(tmp) / "run"
            proc = run_pipeline(
                "--premise",
                "A surveyor falls in love with the town she has been sent to erase.",
                "--run-dir",
                str(run_dir),
                "--max-cycles",
                "1",
                "--min-cycles",
                "1",
                "--dry-run",
            )
            self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
            premise_text = (run_dir / "input" / "premise.txt").read_text(encoding="utf-8").strip()
            self.assertEqual(
                premise_text,
                "A surveyor falls in love with the town she has been sent to erase.",
            )
            run_config = json.loads(
                (run_dir / "config" / "run_config.json").read_text(encoding="utf-8")
            )
            self.assertEqual(run_config["provider"], "codex")
            self.assertEqual(run_config["model"], "gpt-5.4")
            self.assertEqual(run_config["reasoning_effort"], "xhigh")
            gate = json.loads((run_dir / "gate" / "cycle_01" / "gate.json").read_text(encoding="utf-8"))
            self.assertIn(gate["decision"], {"PASS", "FAIL"})

    def test_claude_provider_dry_run_uses_provider_defaults(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_claude_", dir="/tmp") as tmp:
            run_dir = Path(tmp) / "run"
            proc = run_pipeline(
                "--provider",
                "claude",
                "--premise",
                "A theater dresser falls in love with the mayor's translator.",
                "--run-dir",
                str(run_dir),
                "--max-cycles",
                "1",
                "--min-cycles",
                "1",
                "--dry-run",
            )
            self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
            run_config = json.loads(
                (run_dir / "config" / "run_config.json").read_text(encoding="utf-8")
            )
            self.assertEqual(run_config["provider"], "claude")
            self.assertEqual(run_config["model"], "claude-opus-4-6")
            self.assertEqual(run_config["reasoning_effort"], "max")

    def test_generated_premise_dry_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_gen_", dir="/tmp") as tmp:
            run_dir = Path(tmp) / "run"
            proc = run_pipeline(
                "--generate-premise",
                "--premise-seed",
                "deadbeef",
                "--run-dir",
                str(run_dir),
                "--max-cycles",
                "1",
                "--min-cycles",
                "1",
                "--dry-run",
            )
            self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
            self.assertTrue((run_dir / "premise" / "premise_search_plan.json").is_file())
            self.assertTrue((run_dir / "premise" / "premise_candidates.jsonl").is_file())
            self.assertTrue((run_dir / "premise" / "uniqueness_clusters.json").is_file())
            self.assertTrue((run_dir / "premise" / "selection.json").is_file())
            self.assertTrue((run_dir / "input" / "premise.txt").is_file())

    def test_generated_premise_dry_run_with_claude_provider(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_gen_claude_", dir="/tmp") as tmp:
            run_dir = Path(tmp) / "run"
            proc = run_pipeline(
                "--provider",
                "claude",
                "--generate-premise",
                "--premise-seed",
                "deadbeef",
                "--run-dir",
                str(run_dir),
                "--max-cycles",
                "1",
                "--min-cycles",
                "1",
                "--dry-run",
            )
            self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
            run_config = json.loads(
                (run_dir / "config" / "run_config.json").read_text(encoding="utf-8")
            )
            self.assertEqual(run_config["provider"], "claude")
            self.assertEqual(run_config["model"], "claude-opus-4-6")
            self.assertEqual(run_config["reasoning_effort"], "max")
            self.assertTrue((run_dir / "premise" / "premise_search_plan.json").is_file())
            self.assertTrue((run_dir / "premise" / "premise_candidates.jsonl").is_file())
            self.assertTrue((run_dir / "premise" / "uniqueness_clusters.json").is_file())
            self.assertTrue((run_dir / "premise" / "selection.json").is_file())
            self.assertTrue((run_dir / "input" / "premise.txt").is_file())

    def test_stage_group_provider_overrides_dry_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_hybrid_", dir="/tmp") as tmp:
            run_dir = Path(tmp) / "run"
            proc = run_pipeline(
                "--provider",
                "codex",
                "--outline-provider",
                "claude",
                "--draft-provider",
                "claude",
                "--review-provider",
                "codex",
                "--revision-provider",
                "codex",
                "--revision-dialogue-provider",
                "claude",
                "--premise",
                "A civil servant falls in love with a municipal illusionist.",
                "--run-dir",
                str(run_dir),
                "--max-cycles",
                "1",
                "--min-cycles",
                "1",
                "--dry-run",
            )
            self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
            run_config = json.loads(
                (run_dir / "config" / "run_config.json").read_text(encoding="utf-8")
            )
            self.assertEqual(run_config["provider"], "codex")
            self.assertEqual(run_config["stage_profiles"]["outline"]["provider"], "claude")
            self.assertEqual(run_config["stage_profiles"]["draft"]["provider"], "claude")
            self.assertEqual(run_config["stage_profiles"]["review"]["provider"], "codex")
            self.assertEqual(
                run_config["revision_pass_profiles"]["p2_dialogue_idiolect_cadence"]["provider"],
                "claude",
            )
            outline_manifest = json.loads(
                (run_dir / "manifests" / "outline.json").read_text(encoding="utf-8")
            )
            draft_manifest = json.loads(
                (run_dir / "manifests" / "draft_chapter_01.json").read_text(encoding="utf-8")
            )
            review_manifest = json.loads(
                (run_dir / "manifests" / "cycle_01_review_chapter_01.json").read_text(encoding="utf-8")
            )
            revision_manifest = json.loads(
                (run_dir / "manifests" / "cycle_01_continuity_reconciliation.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(outline_manifest["provider"], "claude")
            self.assertEqual(outline_manifest["model"], "claude-opus-4-6")
            self.assertEqual(draft_manifest["provider"], "claude")
            self.assertEqual(review_manifest["provider"], "codex")
            self.assertEqual(revision_manifest["provider"], "codex")

    def test_clean_resume_reuses_cycle_status_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_resume_", dir="/tmp") as tmp:
            run_dir = Path(tmp) / "run"
            first = run_pipeline(
                "--premise",
                "A singer inherits a failed border zoo.",
                "--run-dir",
                str(run_dir),
                "--max-cycles",
                "1",
                "--min-cycles",
                "1",
                "--dry-run",
            )
            self.assertEqual(first.returncode, 0, first.stderr or first.stdout)

            second = run_pipeline(
                "--premise",
                "A singer inherits a failed border zoo.",
                "--run-dir",
                str(run_dir),
                "--max-cycles",
                "1",
                "--min-cycles",
                "1",
                "--dry-run",
            )
            self.assertEqual(second.returncode, 0, second.stderr or second.stdout)
            combined_log = second.stdout + second.stderr
            self.assertIn("resume_source=cycle_status", combined_log)
            self.assertIn("status=PASS success_cycle=01", combined_log)

    def test_tampered_generated_selection_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_tamper_", dir="/tmp") as tmp:
            run_dir = Path(tmp) / "run"
            proc = run_pipeline(
                "--generate-premise",
                "--premise-seed",
                "deadbeef",
                "--run-dir",
                str(run_dir),
                "--max-cycles",
                "1",
                "--min-cycles",
                "1",
                "--dry-run",
            )
            self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)

            selection_path = run_dir / "premise" / "selection.json"
            selection = json.loads(selection_path.read_text(encoding="utf-8"))
            shortlist = selection["shortlist_ids"]
            self.assertGreaterEqual(len(shortlist), 2)
            replacement = shortlist[1] if selection["selected_candidate_id"] == shortlist[0] else shortlist[0]
            selection["selected_candidate_id"] = replacement
            selection_path.write_text(json.dumps(selection, indent=2) + "\n", encoding="utf-8")
            (run_dir / "input" / "premise.txt").write_text("tampered premise\n", encoding="utf-8")

            rerun = run_pipeline(
                "--generate-premise",
                "--premise-seed",
                "deadbeef",
                "--run-dir",
                str(run_dir),
                "--max-cycles",
                "1",
                "--min-cycles",
                "1",
                "--dry-run",
            )
            self.assertEqual(rerun.returncode, 0, rerun.stderr or rerun.stdout)
            combined_log = rerun.stdout + rerun.stderr
            self.assertIn("premise_resume_invalid", combined_log)


if __name__ == "__main__":
    unittest.main()
