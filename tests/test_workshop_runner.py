"""
Smoke tests for the workshop harness orchestrator.

Run with:
    python3 -m unittest tests.test_workshop_runner -v
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "scripts" / "workshop_runner.py"
PREMISE = REPO_ROOT / "exp" / "longer.txt"
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def run_workshop(*args: str) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(RUNNER), *args]
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class WorkshopSmokeTests(unittest.TestCase):
    def test_dry_run_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workshop_", dir="/tmp") as tmp:
            run_dir = Path(tmp) / "run"
            proc = run_workshop(
                "--dry-run",
                "--run-dir", str(run_dir),
                "--premise-file", str(PREMISE),
                "--chapter-count", "3",
            )
            self.assertEqual(
                proc.returncode,
                0,
                msg=f"workshop runner exited non-zero\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}",
            )

            # Top-level artifacts.
            for rel in [
                "config/00_shared_aesthetic.md",
                "config/premise.txt",
                "config/harness_manifest.json",
                "research/dossier.md",
                "blueprint/bible.md",
                "outline/outline.md",
                "voice/trial_a.md",
                "voice/trial_b.md",
                "voice/choice.md",
                "voice/style_guide.md",
                "reads/v1_structural_notes.md",
                "reads/v2_character_theme_notes.md",
                "reads/v4_final_notes.md",
                "manuscript/full.md",
                "manuscript/colophon.md",
            ]:
                self.assertTrue(
                    (run_dir / rel).is_file(),
                    msg=f"missing artifact: {rel}",
                )

            # Per-chapter artifacts at every revision stage.
            for n in (1, 2, 3):
                pad = f"{n:02d}"
                for rel in [
                    f"drafts/v1/chapter_{pad}.md",
                    f"drafts/v2/chapter_{pad}.md",
                    f"drafts/v3/chapter_{pad}.md",
                    f"drafts/v4/chapter_{pad}.md",
                    f"reads/v3_line_notes/chapter_{pad}.md",
                    f"manuscript/chapter_{pad}.md",
                ]:
                    self.assertTrue(
                        (run_dir / rel).is_file(),
                        msg=f"missing per-chapter artifact: {rel}",
                    )

            # Premise was inlined into shared aesthetic.
            shared = (run_dir / "config" / "00_shared_aesthetic.md").read_text()
            self.assertIn(
                "cult leader",
                shared,
                msg="premise text not inlined into shared aesthetic",
            )
            self.assertNotIn(
                "{{PREMISE}}",
                shared,
                msg="premise template placeholder not replaced",
            )

            # Manifest sanity.
            manifest = json.loads((run_dir / "config" / "harness_manifest.json").read_text())
            self.assertEqual(manifest["harness"], "workshop_runner")
            self.assertTrue(manifest["dry_run"])
            self.assertIn("research", manifest["stages"])
            self.assertIn("final_polish", manifest["stages"])

            # Chapter heading contract holds in stubs.
            ch3 = (run_dir / "drafts" / "v1" / "chapter_03.md").read_text()
            self.assertIn(
                "# Chapter 3",
                ch3,
                msg="stub chapter missing required heading",
            )

            # Full manuscript stub concatenates the polished chapters.
            full = (run_dir / "manuscript" / "full.md").read_text()
            self.assertIn("# Chapter 1", full)
            self.assertIn("# Chapter 3", full)

    def test_start_stop_stage_partial(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workshop_part_", dir="/tmp") as tmp:
            run_dir = Path(tmp) / "run"
            proc = run_workshop(
                "--dry-run",
                "--run-dir", str(run_dir),
                "--premise-file", str(PREMISE),
                "--chapter-count", "2",
                "--start-stage", "research",
                "--stop-stage", "outline",
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            self.assertTrue((run_dir / "research" / "dossier.md").is_file())
            self.assertTrue((run_dir / "outline" / "outline.md").is_file())
            self.assertFalse((run_dir / "voice" / "trial_a.md").exists())
            self.assertFalse((run_dir / "manuscript" / "full.md").exists())

    def test_checkpoint_resume_skips_completed_jobs(self) -> None:
        """Default behavior: rerun without --force leaves completed outputs untouched."""
        with tempfile.TemporaryDirectory(prefix="workshop_ckpt_", dir="/tmp") as tmp:
            run_dir = Path(tmp) / "run"
            common = [
                "--dry-run",
                "--run-dir", str(run_dir),
                "--premise-file", str(PREMISE),
                "--chapter-count", "2",
            ]
            proc = run_workshop(*common)
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)

            # Snapshot mtimes of all artifacts.
            artifacts = sorted(run_dir.rglob("*"))
            mtimes_before = {p: p.stat().st_mtime_ns for p in artifacts if p.is_file()}
            self.assertGreater(len(mtimes_before), 20)

            # Sleep enough to ensure the filesystem mtime resolution would
            # detect a rewrite if one happened.
            import time as _t

            _t.sleep(1.05)

            proc2 = run_workshop(*common)
            self.assertEqual(proc2.returncode, 0, msg=proc2.stderr)

            # Stage-output artifacts must be untouched; only the logs/runner.log
            # and the regenerated config files (which the harness always
            # materializes at start) may have changed.
            tolerated = {
                run_dir / "config" / "00_shared_aesthetic.md",
                run_dir / "config" / "premise.txt",
                run_dir / "config" / "harness_manifest.json",
                run_dir / "logs" / "runner.log",
            }
            for path, mt in mtimes_before.items():
                if path in tolerated:
                    continue
                # Prompt logs are rewritten each invocation; that's fine.
                if "/logs/prompts/" in str(path):
                    continue
                self.assertEqual(
                    path.stat().st_mtime_ns,
                    mt,
                    msg=f"checkpoint should have skipped: {path.relative_to(run_dir)} was rewritten",
                )

            # The runner.log should have recorded the skips.
            log_text = (run_dir / "logs" / "runner.log").read_text()
            self.assertIn("job_skip_already_done", log_text)

    def test_force_flag_disables_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workshop_force_", dir="/tmp") as tmp:
            run_dir = Path(tmp) / "run"
            common = [
                "--dry-run",
                "--run-dir", str(run_dir),
                "--premise-file", str(PREMISE),
                "--chapter-count", "2",
            ]
            proc = run_workshop(*common)
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)

            chapter = run_dir / "drafts" / "v1" / "chapter_01.md"
            mt_before = chapter.stat().st_mtime_ns

            import time as _t

            _t.sleep(1.05)

            proc2 = run_workshop(*common, "--force")
            self.assertEqual(proc2.returncode, 0, msg=proc2.stderr)

            self.assertNotEqual(
                chapter.stat().st_mtime_ns,
                mt_before,
                msg="--force should have regenerated the chapter stub",
            )

    def test_partial_failure_resume_regenerates_only_missing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workshop_partial_", dir="/tmp") as tmp:
            run_dir = Path(tmp) / "run"
            common = [
                "--dry-run",
                "--run-dir", str(run_dir),
                "--premise-file", str(PREMISE),
                "--chapter-count", "3",
            ]
            proc = run_workshop(*common)
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)

            # Simulate a partial failure: delete one chapter from a per-chapter
            # stage's outputs. Capture mtimes of the survivors.
            target = run_dir / "drafts" / "v2" / "chapter_02.md"
            self.assertTrue(target.is_file())
            target.unlink()

            survivor = run_dir / "drafts" / "v2" / "chapter_01.md"
            other_stage = run_dir / "drafts" / "v3" / "chapter_03.md"
            mt_survivor = survivor.stat().st_mtime_ns
            mt_other = other_stage.stat().st_mtime_ns

            import time as _t

            _t.sleep(1.05)

            proc2 = run_workshop(*common)
            self.assertEqual(proc2.returncode, 0, msg=proc2.stderr)

            # The deleted chapter was regenerated.
            self.assertTrue(target.is_file())
            # Its peers were left alone.
            self.assertEqual(survivor.stat().st_mtime_ns, mt_survivor)
            self.assertEqual(other_stage.stat().st_mtime_ns, mt_other)

    def test_invalid_stage_name_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workshop_bad_", dir="/tmp") as tmp:
            run_dir = Path(tmp) / "run"
            proc = run_workshop(
                "--dry-run",
                "--run-dir", str(run_dir),
                "--premise-file", str(PREMISE),
                "--start-stage", "not_a_stage",
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("not_a_stage", proc.stderr + proc.stdout)


class RateLimitParserTests(unittest.TestCase):
    """
    Direct tests of the rate-limit detection logic. The full retry loop hits
    subprocess; here we test the parser the loop calls.
    """

    def _make_runner(self, run_dir: Path, *, fallback_wait: int = 600):
        # Late import — sys.path is mutated at module load above.
        import workshop_runner as wr

        args = wr.parse_args([
            "--dry-run",
            "--run-dir", str(run_dir),
            "--premise-file", str(PREMISE),
            "--chapter-count", "1",
            "--rate-limit-wait", str(fallback_wait),
        ])
        runner = wr.WorkshopRunner(args)
        runner.run_dir.mkdir(parents=True, exist_ok=True)
        runner.logs_dir.mkdir(parents=True, exist_ok=True)
        return runner, wr

    def test_structured_rate_limit_event_parsed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rl_struct_", dir="/tmp") as tmp:
            run_dir = Path(tmp) / "run"
            runner, wr = self._make_runner(run_dir)
            jobs_dir = run_dir / "logs" / "jobs"
            jobs_dir.mkdir(parents=True, exist_ok=True)
            log = jobs_dir / "blueprint.jsonl"
            err = jobs_dir / "blueprint.stderr.txt"
            err.write_text("")

            reset_at = int(time.time()) + 1800  # 30 min in the future
            events = [
                {"type": "system", "subtype": "init", "session_id": "abc"},
                {
                    "type": "rate_limit_event",
                    "rate_limit_info": {
                        "status": "rejected",
                        "resetsAt": reset_at,
                        "rateLimitType": "five_hour_window",
                    },
                },
            ]
            log.write_text("\n".join(json.dumps(e) for e in events) + "\n")

            pause = runner._diagnose_rate_limit_pause(log, err)
            self.assertIsNotNone(pause, msg="parser missed structured rate_limit_event")
            assert pause is not None  # type narrowing
            self.assertEqual(pause["reset_at"], reset_at)
            self.assertEqual(pause["rate_limit_type"], "five_hour_window")
            # wait = (reset_at - now) + buffer(120) + jitter[0..30]
            self.assertGreaterEqual(pause["wait_seconds"], 1800 + 120)
            self.assertLessEqual(pause["wait_seconds"], 1800 + 120 + 30 + 5)

    def test_text_marker_fallback_uses_configured_wait(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rl_text_", dir="/tmp") as tmp:
            run_dir = Path(tmp) / "run"
            runner, wr = self._make_runner(run_dir, fallback_wait=900)
            jobs_dir = run_dir / "logs" / "jobs"
            jobs_dir.mkdir(parents=True, exist_ok=True)
            log = jobs_dir / "draft_01.jsonl"
            err = jobs_dir / "draft_01.stderr.txt"

            log.write_text(
                json.dumps({"type": "system", "subtype": "init", "session_id": "x"}) + "\n"
            )
            err.write_text("Error: 429 Too Many Requests — please retry later.\n")

            pause = runner._diagnose_rate_limit_pause(log, err)
            self.assertIsNotNone(pause)
            assert pause is not None
            self.assertEqual(pause["wait_seconds"], 900)
            self.assertEqual(pause["rate_limit_type"], "text-pattern")
            self.assertIsNone(pause["reset_at"])

    def test_clean_failure_returns_none(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rl_clean_", dir="/tmp") as tmp:
            run_dir = Path(tmp) / "run"
            runner, wr = self._make_runner(run_dir)
            jobs_dir = run_dir / "logs" / "jobs"
            jobs_dir.mkdir(parents=True, exist_ok=True)
            log = jobs_dir / "blueprint.jsonl"
            err = jobs_dir / "blueprint.stderr.txt"

            log.write_text(
                json.dumps({"type": "system", "subtype": "init", "session_id": "x"}) + "\n"
                + json.dumps({"type": "result", "subtype": "error_max_turns", "is_error": True}) + "\n"
            )
            err.write_text("hit max turns; exiting\n")

            pause = runner._diagnose_rate_limit_pause(log, err)
            self.assertIsNone(pause, msg="parser false-positived on non-quota error")

    def test_rotate_attempt_logs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rl_rot_", dir="/tmp") as tmp:
            run_dir = Path(tmp) / "run"
            runner, wr = self._make_runner(run_dir)
            jobs_dir = run_dir / "logs" / "jobs"
            jobs_dir.mkdir(parents=True, exist_ok=True)
            log = jobs_dir / "blueprint.jsonl"
            err = jobs_dir / "blueprint.stderr.txt"
            log.write_text('{"hello":"world"}\n')
            err.write_text("a stderr line\n")

            runner._rotate_attempt_logs(log, err, attempt=1)

            self.assertFalse(log.is_file())
            self.assertFalse(err.is_file())
            self.assertTrue((jobs_dir / "blueprint.attempt-1.jsonl").is_file())
            self.assertTrue((jobs_dir / "blueprint.attempt-1.stderr.txt").is_file())


if __name__ == "__main__":
    unittest.main()
