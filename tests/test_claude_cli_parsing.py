from __future__ import annotations

import dataclasses
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import runner as runner_module


CLAUDE_STREAM_JSON = """\
{"type":"system","subtype":"init","cwd":"/tmp/project","session_id":"af1ca5c0-beb9-4ba6-b616-6f1f9e05a187","tools":["Task","TaskOutput","Bash","Glob","Grep","ExitPlanMode","Read","Edit","Write","NotebookEdit","WebFetch","TodoWrite","WebSearch","TaskStop","AskUserQuestion","Skill","EnterPlanMode","EnterWorktree","ExitWorktree","CronCreate","CronDelete","CronList","ToolSearch"],"mcp_servers":[],"model":"claude-opus-4-6","permissionMode":"bypassPermissions","slash_commands":["keybindings-help","debug","simplify","batch","loop","claude-api","compact","context","cost","heapdump","init","pr-comments","release-notes","review","security-review","extra-usage","insights"],"apiKeySource":"none","claude_code_version":"2.1.73","output_style":"default","agents":["general-purpose","statusline-setup","Explore","Plan"],"skills":["keybindings-help","debug","simplify","batch","loop","claude-api"],"plugins":[],"uuid":"94f3c246-d33b-47b9-a9e7-59d5fc1b3527","fast_mode_state":"off"}
{"type":"assistant","message":{"model":"claude-opus-4-6","id":"msg_0172n5gp4M2814JV91mWvcJR","type":"message","role":"assistant","content":[{"type":"text","text":"OK"}],"stop_reason":null,"stop_sequence":null,"usage":{"input_tokens":2,"cache_creation_input_tokens":8304,"cache_read_input_tokens":6371,"cache_creation":{"ephemeral_5m_input_tokens":0,"ephemeral_1h_input_tokens":8304},"output_tokens":1,"service_tier":"standard","inference_geo":"not_available"},"context_management":null},"parent_tool_use_id":null,"session_id":"af1ca5c0-beb9-4ba6-b616-6f1f9e05a187","uuid":"0f2fe5ca-03f3-42bc-a081-8c33d924dbf8"}
{"type":"rate_limit_event","rate_limit_info":{"status":"allowed","resetsAt":1773288000,"rateLimitType":"five_hour","overageStatus":"rejected","overageDisabledReason":"org_level_disabled","isUsingOverage":false},"uuid":"795f7ca1-d600-4d9f-b718-477f0491e058","session_id":"af1ca5c0-beb9-4ba6-b616-6f1f9e05a187"}
{"type":"result","subtype":"success","is_error":false,"duration_ms":1266,"duration_api_ms":1249,"num_turns":1,"result":"OK","stop_reason":"end_turn","session_id":"af1ca5c0-beb9-4ba6-b616-6f1f9e05a187","total_cost_usd":0.0551955,"usage":{"input_tokens":2,"cache_creation_input_tokens":8304,"cache_read_input_tokens":6371,"output_tokens":4,"server_tool_use":{"web_search_requests":0,"web_fetch_requests":0},"service_tier":"standard","cache_creation":{"ephemeral_1h_input_tokens":8304,"ephemeral_5m_input_tokens":0},"inference_geo":"","iterations":[],"speed":"standard"},"modelUsage":{"claude-opus-4-6":{"inputTokens":2,"outputTokens":4,"cacheReadInputTokens":6371,"cacheCreationInputTokens":8304,"webSearchRequests":0,"costUSD":0.0551955,"contextWindow":200000,"maxOutputTokens":32000}},"permission_denials":[],"fast_mode_state":"off","uuid":"40c57907-8a80-46ec-98b2-20058a8adfde"}
"""

CLAUDE_RATE_LIMIT_STREAM_JSON = """\
{"type":"system","subtype":"init","cwd":"/tmp","session_id":"quota-session","model":"claude-opus-4-6"}
{"type":"rate_limit_event","rate_limit_info":{"status":"rejected","resetsAt":2000000000,"rateLimitType":"five_hour","overageStatus":"rejected","overageDisabledReason":"org_level_disabled","isUsingOverage":false},"uuid":"rate-limit-1","session_id":"quota-session"}
{"type":"assistant","message":{"id":"quota-msg","container":null,"model":"<synthetic>","role":"assistant","stop_reason":"stop_sequence","stop_sequence":"","type":"message","usage":{"input_tokens":0,"output_tokens":0,"cache_creation_input_tokens":0,"cache_read_input_tokens":0,"server_tool_use":{"web_search_requests":0,"web_fetch_requests":0},"service_tier":null,"cache_creation":{"ephemeral_1h_input_tokens":0,"ephemeral_5m_input_tokens":0},"inference_geo":null,"iterations":null,"speed":null},"content":[{"type":"text","text":"You've hit your limit · resets 12am (America/New_York)"}],"context_management":null},"parent_tool_use_id":null,"session_id":"quota-session","uuid":"quota-assistant","error":"rate_limit"}
{"type":"result","subtype":"success","is_error":true,"duration_ms":166,"duration_api_ms":0,"num_turns":1,"result":"You've hit your limit · resets 12am (America/New_York)","stop_reason":"stop_sequence","session_id":"quota-session","total_cost_usd":0,"usage":{"input_tokens":0,"cache_creation_input_tokens":0,"cache_read_input_tokens":0,"output_tokens":0,"server_tool_use":{"web_search_requests":0,"web_fetch_requests":0},"service_tier":"standard","cache_creation":{"ephemeral_1h_input_tokens":0,"ephemeral_5m_input_tokens":0},"inference_geo":"","iterations":[],"speed":"standard"},"modelUsage":{},"permission_denials":[],"fast_mode_state":"off","uuid":"quota-result"}
"""


def make_runner(tmp_dir: Path) -> runner_module.NovelPipelineRunner:
    default_profile = runner_module.ExecutionProfile(
        provider="claude",
        agent_bin="claude",
        model="claude-opus-4-6",
        reasoning_effort="max",
    )
    cfg = runner_module.RunnerConfig(
        premise="A surveyor falls in love with the town she has been sent to erase.",
        premise_mode="user",
        premise_brief=None,
        award_profile="major-award",
        premise_seed=None,
        premise_reroll_max=4,
        premise_candidate_count=30,
        premise_generation_batch_size=6,
        premise_min_unique_clusters=8,
        premise_shortlist_size=6,
        run_dir=tmp_dir,
        max_cycles=1,
        min_cycles=1,
        max_parallel_drafts=1,
        max_parallel_reviews=1,
        max_parallel_revisions=1,
        provider="claude",
        agent_bin="claude",
        model="claude-opus-4-6",
        reasoning_effort="max",
        stage_profiles={
            stage_group: default_profile
            for stage_group in runner_module.STAGE_GROUP_VALUES
        },
        revision_pass_profiles={},
        dry_run=True,
        dry_run_chapter_count=18,
        job_timeout_seconds=3600,
        job_idle_timeout_seconds=1800,
        validation_mode="lenient",
    )
    return runner_module.NovelPipelineRunner(REPO_ROOT, cfg)


class ClaudeCliParsingTests(unittest.TestCase):
    def test_aggregate_findings_expands_full_award_pattern_hits(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_pattern_expand_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1,
                    chapter_engine="discovery",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                ),
                runner_module.ChapterSpec(
                    chapter_id="chapter_02",
                    chapter_number=2,
                    projected_min_words=1,
                    chapter_engine="discovery",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                ),
            ]

            run_dir = runner.cfg.run_dir
            (run_dir / "reviews" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (run_dir / "snapshots" / "cycle_01" / "chapters").mkdir(parents=True, exist_ok=True)
            (run_dir / "snapshots" / "cycle_01" / "chapters" / "chapter_01.md").write_text(
                "# Chapter 1\n\nEnough words here.\n",
                encoding="utf-8",
            )
            (run_dir / "snapshots" / "cycle_01" / "chapters" / "chapter_02.md").write_text(
                "# Chapter 2\n\nEnough words here too.\n",
                encoding="utf-8",
            )
            chapter_review = {
                "chapter_id": "chapter_01",
                "verdicts": {
                    runner_module.PRIMARY_REVIEW_LENS: "PASS",
                    "craft": "PASS",
                    "dialogue": "PASS",
                    "prose": "PASS",
                },
                "findings": [],
                "summary": "No chapter-local blockers.",
            }
            (run_dir / "reviews" / "cycle_01" / "chapter_01.review.json").write_text(
                json.dumps(chapter_review) + "\n",
                encoding="utf-8",
            )
            chapter_review["chapter_id"] = "chapter_02"
            (run_dir / "reviews" / "cycle_01" / "chapter_02.review.json").write_text(
                json.dumps(chapter_review) + "\n",
                encoding="utf-8",
            )

            full_review = {
                "cycle": 1,
                "verdict": "FAIL",
                "summary": "A repeated prose auto-commentary pattern weakens both chapters.",
                "findings": [],
                "pattern_findings": [
                    {
                        "pattern_id": "PROSE_AUTOCOMM",
                        "severity": "MEDIUM",
                        "global_problem": "Recurring prose auto-commentary flattens POV texture.",
                        "affected_chapters": ["chapter_01", "chapter_02"],
                        "global_rewrite_principles": (
                            "Replace explanatory self-commentary with more direct sensory or "
                            "behavioral rendering."
                        ),
                        "chapter_hits": [
                            {
                                "chapter_id": "chapter_01",
                                "evidence": "snapshots/cycle_01/FINAL_NOVEL.md:15",
                                "problem": "Chapter 1 keeps naming the emotional result after it already lands.",
                                "rewrite_direction": (
                                    "Revise snapshots/cycle_01/FINAL_NOVEL.md:12-18 to stop "
                                    "paraphrasing the beat after the action lands."
                                ),
                                "acceptance_test": (
                                    "Pass if snapshots/cycle_01/FINAL_NOVEL.md:12-18 lets the "
                                    "scene register through action instead of after-the-fact gloss."
                                ),
                            },
                            {
                                "chapter_id": "chapter_02",
                                "evidence": "snapshots/cycle_01/FINAL_NOVEL.md:41",
                                "problem": "Chapter 2 explains the room's emotional geometry too cleanly.",
                                "rewrite_direction": (
                                    "Revise snapshots/cycle_01/FINAL_NOVEL.md:37-45 so the pressure "
                                    "comes through behavior and interruption instead of summary."
                                ),
                                "acceptance_test": (
                                    "Pass if snapshots/cycle_01/FINAL_NOVEL.md:37-45 no longer "
                                    "depends on explanatory gloss to tell the reader how the moment lands."
                                ),
                            },
                        ],
                    }
                ],
            }
            (run_dir / "reviews" / "cycle_01" / "full_award.review.json").write_text(
                json.dumps(full_review) + "\n",
                encoding="utf-8",
            )

            aggregate = runner._aggregate_findings(1)

            self.assertEqual(aggregate["full_award_verdict"], "FAIL")
            self.assertEqual(
                sorted(aggregate["by_chapter"].keys()),
                ["chapter_01", "chapter_02"],
            )
            self.assertEqual(len(aggregate["all_findings"]), 2)
            self.assertTrue(
                all(finding["source"] == "award_global" for finding in aggregate["all_findings"])
            )
            self.assertEqual(
                {finding["chapter_id"] for finding in aggregate["all_findings"]},
                {"chapter_01", "chapter_02"},
            )

    def test_aggregate_findings_warns_on_underfan_pattern_claim_without_failing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_pattern_underfan_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1,
                    chapter_engine="discovery",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                ),
                runner_module.ChapterSpec(
                    chapter_id="chapter_02",
                    chapter_number=2,
                    projected_min_words=1,
                    chapter_engine="discovery",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                ),
            ]

            run_dir = runner.cfg.run_dir
            (run_dir / "reviews" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (run_dir / "snapshots" / "cycle_01" / "chapters").mkdir(parents=True, exist_ok=True)
            (run_dir / "snapshots" / "cycle_01" / "chapters" / "chapter_01.md").write_text(
                "# Chapter 1\n\nEnough words here.\n",
                encoding="utf-8",
            )
            (run_dir / "snapshots" / "cycle_01" / "chapters" / "chapter_02.md").write_text(
                "# Chapter 2\n\nEnough words here too.\n",
                encoding="utf-8",
            )
            for chapter_id in ("chapter_01", "chapter_02"):
                (run_dir / "reviews" / "cycle_01" / f"{chapter_id}.review.json").write_text(
                    json.dumps(
                        {
                            "chapter_id": chapter_id,
                            "verdicts": {
                                runner_module.PRIMARY_REVIEW_LENS: "PASS",
                                "craft": "PASS",
                                "dialogue": "PASS",
                                "prose": "PASS",
                            },
                            "findings": [],
                            "summary": "No chapter-local blockers.",
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )

            (run_dir / "reviews" / "cycle_01" / "full_award.review.json").write_text(
                json.dumps(
                    {
                        "cycle": 1,
                        "verdict": "FAIL",
                        "summary": "A recurring prose pattern affects both chapters.",
                        "findings": [],
                        "pattern_findings": [
                            {
                                "pattern_id": "PROSE_AUTOCOMM",
                                "severity": "MEDIUM",
                                "global_problem": "Recurring prose auto-commentary flattens POV texture.",
                                "affected_chapters": ["chapter_01", "chapter_02"],
                                "chapter_hits": [
                                    {
                                        "chapter_id": "chapter_01",
                                        "evidence": "snapshots/cycle_01/FINAL_NOVEL.md:15",
                                        "problem": "Chapter 1 over-explains the beat.",
                                        "rewrite_direction": (
                                            "Revise snapshots/cycle_01/FINAL_NOVEL.md:12-18 to let the "
                                            "action carry the turn."
                                        ),
                                        "acceptance_test": (
                                            "Pass if snapshots/cycle_01/FINAL_NOVEL.md:12-18 no longer "
                                            "depends on explanatory gloss."
                                        ),
                                    }
                                ],
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            aggregate = runner._aggregate_findings(1)

            self.assertEqual(len(aggregate["all_findings"]), 1)
            self.assertEqual(aggregate["all_findings"][0]["chapter_id"], "chapter_01")
            self.assertTrue(
                any(
                    warning["action"] == "underfan_full_award_pattern_claim"
                    for warning in runner.validation_warnings
                )
            )

    def test_load_repaired_full_award_review_normalizes_legacy_shape_and_preserves_original(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_full_award_repair_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1,
                    chapter_engine="discovery",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                ),
                runner_module.ChapterSpec(
                    chapter_id="chapter_02",
                    chapter_number=2,
                    projected_min_words=1,
                    chapter_engine="discovery",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                ),
            ]

            run_dir = runner.cfg.run_dir
            (run_dir / "reviews" / "cycle_01").mkdir(parents=True, exist_ok=True)
            legacy_review = {
                "cycle": "01",
                "verdict": "fail",
                "summary": "Legacy-shaped review output.",
                "findings": [
                    {
                        "finding_id": "LEGACY_F1",
                        "severity": "MEDIUM",
                        "chapter_id": "ch1",
                        "description": "The chapter lands its turn and then keeps explaining it.",
                        "evidence": [
                            {
                                "location": "snapshots/cycle_01/FINAL_NOVEL.md:12",
                                "description": "Turn lands here.",
                            },
                            {
                                "location": "snapshots/cycle_01/FINAL_NOVEL.md:19",
                                "description": "Later lines restate the same turn.",
                            },
                        ],
                        "rewrite_direction": "Cut the explanatory afterglow and end sooner.",
                    }
                ],
                "pattern_findings": [
                    {
                        "pattern_id": "MIDSECTION_PLATEAU",
                        "severity": "HIGH",
                        "description": "The middle chapters keep resolving to the same emotional state.",
                        "chapter_hits": [
                            {
                                "chapter_id": "ch2",
                                "evidence": [
                                    {
                                        "location": "snapshots/cycle_01/FINAL_NOVEL.md:33",
                                        "description": "Opens in the same posture as the prior chapter.",
                                    }
                                ],
                                "rewrite_direction": "Force a different exit state by the end of the chapter.",
                            }
                        ],
                    }
                ],
            }
            rel = "reviews/cycle_01/full_award.review.json"
            (run_dir / rel).write_text(json.dumps(legacy_review) + "\n", encoding="utf-8")

            repaired = runner._load_repaired_full_award_review(
                rel,
                1,
                {"chapter_01", "chapter_02"},
                "snapshots/cycle_01/FINAL_NOVEL.md",
            )

            self.assertEqual(repaired["cycle"], 1)
            self.assertEqual(repaired["verdict"], "FAIL")
            self.assertEqual(repaired["findings"][0]["chapter_id"], "chapter_01")
            self.assertEqual(
                repaired["findings"][0]["problem"],
                "The chapter lands its turn and then keeps explaining it.",
            )
            self.assertIn(
                "snapshots/cycle_01/FINAL_NOVEL.md:12 - Turn lands here.",
                repaired["findings"][0]["evidence"],
            )
            self.assertTrue(repaired["findings"][0]["acceptance_test"])
            self.assertEqual(
                repaired["pattern_findings"][0]["global_problem"],
                "The middle chapters keep resolving to the same emotional state.",
            )
            self.assertEqual(
                repaired["pattern_findings"][0]["affected_chapters"],
                ["chapter_02"],
            )
            self.assertEqual(
                repaired["pattern_findings"][0]["chapter_hits"][0]["chapter_id"],
                "chapter_02",
            )
            self.assertTrue(
                repaired["pattern_findings"][0]["chapter_hits"][0]["acceptance_test"]
            )

            preserved = (
                run_dir / "reviews" / "cycle_01" / "full_award.review.invalid.original.json"
            )
            self.assertTrue(preserved.is_file())
            self.assertEqual(json.loads(preserved.read_text(encoding="utf-8")), legacy_review)

    def test_load_repaired_full_award_review_maps_legacy_verdict_and_grouped_pattern_shape(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_full_award_legacy_grouped_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1,
                    chapter_engine="discovery",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                ),
                runner_module.ChapterSpec(
                    chapter_id="chapter_02",
                    chapter_number=2,
                    projected_min_words=1,
                    chapter_engine="discovery",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                ),
            ]

            run_dir = runner.cfg.run_dir
            (run_dir / "reviews" / "cycle_01").mkdir(parents=True, exist_ok=True)
            legacy_review = {
                "cycle": 1,
                "verdict": "CONDITIONAL_PASS",
                "summary": "Legacy grouped review output.",
                "findings": [
                    {
                        "id": "LEGACY_F1",
                        "severity": "medium",
                        "chapter_id": "ch1",
                        "problem": "The chapter overexplains its turn.",
                        "evidence": [
                            {
                                "location": "snapshots/cycle_01/FINAL_NOVEL.md:12",
                                "description": "The turn lands here.",
                            }
                        ],
                        "fix": "Cut the explanatory tail and land on the action.",
                    }
                ],
                "pattern_findings": [
                    {
                        "id": "LEGACY_PATTERN",
                        "severity": "medium",
                        "global_problem": "A repeated pattern keeps flattening pressure.",
                        "chapter_ids": ["ch1", "chapter_02"],
                        "fix": "Keep the strongest instance and vary the weaker repetitions.",
                        "chapter_hits": [
                            {
                                "chapter_id": "ch1",
                                "evidence": ["snapshots/cycle_01/FINAL_NOVEL.md:12"],
                                "local_problem": "Chapter 1 explains the pattern too bluntly.",
                            },
                            {
                                "chapter_id": "chapter_02",
                                "evidence": ["snapshots/cycle_01/FINAL_NOVEL.md:33"],
                                "local_note": "Chapter 2 restates the same pattern beat.",
                            },
                        ],
                    }
                ],
            }
            rel = "reviews/cycle_01/full_award.review.json"
            (run_dir / rel).write_text(json.dumps(legacy_review) + "\n", encoding="utf-8")

            repaired = runner._load_repaired_full_award_review(
                rel,
                1,
                {"chapter_01", "chapter_02"},
                "snapshots/cycle_01/FINAL_NOVEL.md",
            )
            runner._validate_full_award_review_json(
                repaired,
                1,
                {"chapter_01", "chapter_02"},
                rel,
                "snapshots/cycle_01/FINAL_NOVEL.md",
            )

            self.assertEqual(repaired["verdict"], "FAIL")
            self.assertEqual(repaired["findings"][0]["finding_id"], "LEGACY_F1")
            self.assertEqual(repaired["findings"][0]["chapter_id"], "chapter_01")
            self.assertIn(
                "Revise snapshots/cycle_01/FINAL_NOVEL.md:12",
                repaired["findings"][0]["rewrite_direction"],
            )
            pattern = repaired["pattern_findings"][0]
            self.assertEqual(pattern["pattern_id"], "LEGACY_PATTERN")
            self.assertEqual(pattern["affected_chapters"], ["chapter_01", "chapter_02"])
            self.assertEqual(
                pattern["chapter_hits"][0]["problem"],
                "Chapter 1 explains the pattern too bluntly.",
            )
            self.assertEqual(
                pattern["chapter_hits"][1]["problem"],
                "Chapter 2 restates the same pattern beat.",
            )
            self.assertIn(
                "Keep the strongest instance and vary the weaker repetitions.",
                pattern["chapter_hits"][0]["rewrite_direction"],
            )
            self.assertIn(
                "Revise snapshots/cycle_01/FINAL_NOVEL.md:33",
                pattern["chapter_hits"][1]["rewrite_direction"],
            )

    def test_run_full_award_review_stage_repairs_legacy_output_instead_of_fallback(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_full_award_stage_repair_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1,
                    chapter_engine="discovery",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
            ]

            run_dir = runner.cfg.run_dir
            (run_dir / "snapshots" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (run_dir / "context" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (run_dir / "outline").mkdir(parents=True, exist_ok=True)
            (run_dir / "config" / "prompts").mkdir(parents=True, exist_ok=True)
            (run_dir / "config").mkdir(parents=True, exist_ok=True)
            (run_dir / "snapshots" / "cycle_01" / "FINAL_NOVEL.md").write_text(
                "# Title\n\n# Chapter 1\n\nBody.\n",
                encoding="utf-8",
            )
            (run_dir / "context" / "cycle_01" / "global_cycle_context.json").write_text(
                json.dumps({"chapter_spine": []}) + "\n",
                encoding="utf-8",
            )
            (run_dir / "outline" / "style_bible.json").write_text(
                json.dumps(
                    {
                        "character_voice_profiles": [
                            {
                                "character_id": "nick",
                                "public_register": "guarded",
                                "private_register": "angry",
                                "syntax_signature": "plain",
                                "lexical_signature": "visual",
                                "forbidden_generic_lines": "none",
                                "stress_tells": "tightens",
                                "profanity_profile": "moderate",
                                "contraction_level": "high",
                                "interruption_habit": "rare",
                                "self_correction_tendency": "light",
                                "indirectness": "mixed",
                                "repetition_tolerance": "some",
                                "evasion_style": "narrows",
                                "sentence_completion_style": "finishes",
                            }
                        ],
                        "dialogue_rules": {
                            "anti_transcript_cadence": True,
                            "required_leverage_shifts_per_scene": 1,
                            "max_consecutive_low_info_replies": 2,
                            "idiolect_separation_required": True,
                            "default_contraction_use": "high",
                        },
                        "prose_style_profile": {
                            "narrative_tense": "past tense",
                            "narrative_distance": "close",
                            "rhythm_target": "mixed",
                            "sensory_bias": ["visual"],
                            "diction": "concrete",
                            "forbidden_drift_patterns": ["generic phrasing"],
                            "chapter_texture_variance": "vary rhythm",
                        },
                        "aesthetic_risk_policy": {
                            "sanitization_disallowed": True,
                            "dark_content_allowed_when_character_true": True,
                            "profanity_allowed_when_scene_pressure_warrants": True,
                            "euphemism_penalty": "high",
                            "creative_risk_policy": "push toward specificity",
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (run_dir / "outline" / "continuity_sheet.json").write_text(
                json.dumps(
                    {
                        "characters": [],
                        "timeline": {
                            "story_start": "spring",
                            "estimated_span": "one month",
                            "seasonal_track": [],
                            "key_events": [],
                        },
                        "geography": {
                            "primary_setting": "city",
                            "key_locations": [],
                            "distances": [],
                        },
                        "world_rules": [],
                        "power_structure": [],
                        "objects": [],
                        "financial_state": {"debts": [], "income_sources": []},
                        "knowledge_state": [],
                        "environmental_constants": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (run_dir / "config" / "constitution.md").write_text(
                "constitution placeholder\n",
                encoding="utf-8",
            )
            (run_dir / "config" / "prompts" / "full_award_review_prompt.md").write_text(
                (REPO_ROOT / "prompts" / "full_award_review_prompt.md").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )

            legacy_review = {
                "cycle": "01",
                "verdict": "FAIL",
                "summary": "Legacy review from the model.",
                "findings": [
                    {
                        "finding_id": "LEGACY_F1",
                        "severity": "MEDIUM",
                        "chapter_id": "ch1",
                        "description": "The chapter repeats its central point.",
                        "evidence": [
                            {
                                "location": "snapshots/cycle_01/FINAL_NOVEL.md:4",
                                "description": "Opening repetition.",
                            }
                        ],
                        "rewrite_direction": "Trim the repeated explanation.",
                    }
                ],
                "pattern_findings": [],
            }

            def fake_run_job(_job: runner_module.JobSpec) -> None:
                output = run_dir / "reviews" / "cycle_01" / "full_award.review.json"
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(json.dumps(legacy_review) + "\n", encoding="utf-8")

            runner._run_job = fake_run_job

            runner._run_full_award_review_stage(1)

            repaired = json.loads(
                (
                    run_dir / "reviews" / "cycle_01" / "full_award.review.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(repaired["cycle"], 1)
            self.assertEqual(repaired["findings"][0]["chapter_id"], "chapter_01")
            self.assertNotEqual(
                repaired["findings"][0]["finding_id"],
                "fallback_full_award_contract",
            )
            self.assertTrue(
                (
                    run_dir / "reviews" / "cycle_01" / "full_award.review.invalid.original.json"
                ).is_file()
            )

    def test_run_full_award_review_stage_maps_near_pass_legacy_shape_without_retry(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_full_award_no_retry_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1,
                    chapter_engine="discovery",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                ),
                runner_module.ChapterSpec(
                    chapter_id="chapter_02",
                    chapter_number=2,
                    projected_min_words=1,
                    chapter_engine="discovery",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                ),
            ]

            run_dir = runner.cfg.run_dir
            (run_dir / "snapshots" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (run_dir / "context" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (run_dir / "outline").mkdir(parents=True, exist_ok=True)
            (run_dir / "config" / "prompts").mkdir(parents=True, exist_ok=True)
            (run_dir / "config").mkdir(parents=True, exist_ok=True)
            (run_dir / "snapshots" / "cycle_01" / "FINAL_NOVEL.md").write_text(
                "# Title\n\n# Chapter 1\n\nBody.\n\n# Chapter 2\n\nBody.\n",
                encoding="utf-8",
            )
            (run_dir / "context" / "cycle_01" / "global_cycle_context.json").write_text(
                json.dumps({"chapter_spine": []}) + "\n",
                encoding="utf-8",
            )
            (run_dir / "outline" / "style_bible.json").write_text(
                json.dumps(
                    {
                        "character_voice_profiles": [
                            {
                                "character_id": "nick",
                                "public_register": "guarded",
                                "private_register": "angry",
                                "syntax_signature": "plain",
                                "lexical_signature": "visual",
                                "forbidden_generic_lines": "none",
                                "stress_tells": "tightens",
                                "profanity_profile": "moderate",
                                "contraction_level": "high",
                                "interruption_habit": "rare",
                                "self_correction_tendency": "light",
                                "indirectness": "mixed",
                                "repetition_tolerance": "some",
                                "evasion_style": "narrows",
                                "sentence_completion_style": "finishes",
                            }
                        ],
                        "dialogue_rules": {
                            "anti_transcript_cadence": True,
                            "required_leverage_shifts_per_scene": 1,
                            "max_consecutive_low_info_replies": 2,
                            "idiolect_separation_required": True,
                            "default_contraction_use": "high",
                        },
                        "prose_style_profile": {
                            "narrative_tense": "past tense",
                            "narrative_distance": "close",
                            "rhythm_target": "mixed",
                            "sensory_bias": ["visual"],
                            "diction": "concrete",
                            "forbidden_drift_patterns": ["generic phrasing"],
                            "chapter_texture_variance": "vary rhythm",
                        },
                        "aesthetic_risk_policy": {
                            "sanitization_disallowed": True,
                            "dark_content_allowed_when_character_true": True,
                            "profanity_allowed_when_scene_pressure_warrants": True,
                            "euphemism_penalty": "high",
                            "creative_risk_policy": "push toward specificity",
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (run_dir / "outline" / "continuity_sheet.json").write_text(
                json.dumps(
                    {
                        "characters": [],
                        "timeline": {
                            "story_start": "spring",
                            "estimated_span": "one month",
                            "seasonal_track": [],
                            "key_events": [],
                        },
                        "geography": {
                            "primary_setting": "city",
                            "key_locations": [],
                            "distances": [],
                        },
                        "world_rules": [],
                        "power_structure": [],
                        "objects": [],
                        "financial_state": {"debts": [], "income_sources": []},
                        "knowledge_state": [],
                        "environmental_constants": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (run_dir / "config" / "constitution.md").write_text(
                "constitution placeholder\n",
                encoding="utf-8",
            )
            (run_dir / "config" / "prompts" / "full_award_review_prompt.md").write_text(
                (REPO_ROOT / "prompts" / "full_award_review_prompt.md").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )

            legacy_review = {
                "cycle": 1,
                "verdict": "PASS WITH CONDITIONS",
                "summary": "Near-pass legacy review from the model.",
                "findings": [
                    {
                        "id": "LEGACY_F1",
                        "severity": "HIGH",
                        "chapter_id": "ch1",
                        "problem": "The chapter re-explains its turn.",
                        "evidence": ["snapshots/cycle_01/FINAL_NOVEL.md:4"],
                        "fix": "Cut the repeated explanation and leave the turn on the page.",
                    }
                ],
                "pattern_findings": [
                    {
                        "id": "LEGACY_PATTERN",
                        "severity": "MEDIUM",
                        "global_problem": "A repeated pattern is flattening the chapter exits.",
                        "chapter_ids": ["chapter_01", "ch2"],
                        "fix": "Keep the strongest exit beat and vary the other recurrence.",
                        "chapter_hits": [
                            {
                                "chapter_id": "chapter_01",
                                "evidence": ["snapshots/cycle_01/FINAL_NOVEL.md:4"],
                                "local_note": "Chapter 1 spells out the same exit beat twice.",
                            },
                            {
                                "chapter_id": "ch2",
                                "evidence": ["snapshots/cycle_01/FINAL_NOVEL.md:8"],
                                "local_problem": "Chapter 2 lands in the same explanatory register.",
                            },
                        ],
                    }
                ],
            }

            calls: list[str] = []

            def fake_run_job(job: runner_module.JobSpec) -> None:
                calls.append(job.job_id)
                output = run_dir / "reviews" / "cycle_01" / "full_award.review.json"
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(json.dumps(legacy_review) + "\n", encoding="utf-8")

            runner._run_job = fake_run_job

            runner._run_full_award_review_stage(1)

            self.assertEqual(calls, ["cycle_01_full_award_review"])
            saved = json.loads(
                (
                    run_dir / "reviews" / "cycle_01" / "full_award.review.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(saved["verdict"], "FAIL")
            self.assertEqual(saved["findings"][0]["finding_id"], "LEGACY_F1")
            self.assertEqual(saved["pattern_findings"][0]["pattern_id"], "LEGACY_PATTERN")
            self.assertIn(
                "Keep the strongest exit beat and vary the other recurrence.",
                saved["pattern_findings"][0]["chapter_hits"][0]["rewrite_direction"],
            )
            self.assertNotEqual(
                saved["findings"][0]["finding_id"],
                "fallback_full_award_contract",
            )

    def test_run_full_award_review_stage_accepts_low_severity_without_retry(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_full_award_low_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1,
                    chapter_engine="discovery",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
            ]

            run_dir = runner.cfg.run_dir
            (run_dir / "snapshots" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (run_dir / "context" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (run_dir / "outline").mkdir(parents=True, exist_ok=True)
            (run_dir / "config" / "prompts").mkdir(parents=True, exist_ok=True)
            (run_dir / "config").mkdir(parents=True, exist_ok=True)
            (run_dir / "snapshots" / "cycle_01" / "FINAL_NOVEL.md").write_text(
                "# Title\n\n# Chapter 1\n\nBody.\n",
                encoding="utf-8",
            )
            (run_dir / "context" / "cycle_01" / "global_cycle_context.json").write_text(
                json.dumps({"chapter_spine": []}) + "\n",
                encoding="utf-8",
            )
            (run_dir / "outline" / "style_bible.json").write_text(
                json.dumps(
                    {
                        "character_voice_profiles": [],
                        "dialogue_rules": {},
                        "prose_style_profile": {"narrative_tense": "past tense"},
                        "aesthetic_risk_policy": {},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (run_dir / "outline" / "continuity_sheet.json").write_text(
                json.dumps(
                    {
                        "characters": [],
                        "timeline": {
                            "story_start": "spring",
                            "estimated_span": "one month",
                            "seasonal_track": [],
                            "key_events": [],
                        },
                        "geography": {
                            "primary_setting": "city",
                            "key_locations": [],
                            "distances": [],
                        },
                        "world_rules": [],
                        "power_structure": [],
                        "objects": [],
                        "financial_state": {"debts": [], "income_sources": []},
                        "knowledge_state": [],
                        "environmental_constants": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (run_dir / "config" / "constitution.md").write_text(
                "constitution placeholder\n",
                encoding="utf-8",
            )
            (run_dir / "config" / "prompts" / "full_award_review_prompt.md").write_text(
                (REPO_ROOT / "prompts" / "full_award_review_prompt.md").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )

            review = {
                "cycle": 1,
                "verdict": "FAIL",
                "summary": "Mostly strong, with one soft polish note.",
                "findings": [
                    {
                        "finding_id": "LOW_NOTE_CH01",
                        "severity": "LOW",
                        "chapter_id": "chapter_01",
                        "evidence": "snapshots/cycle_01/FINAL_NOVEL.md:4",
                        "problem": "A light polish issue remains.",
                        "rewrite_direction": (
                            "Revise snapshots/cycle_01/FINAL_NOVEL.md:4-6 to tighten the sentence."
                        ),
                        "acceptance_test": (
                            "Pass if snapshots/cycle_01/FINAL_NOVEL.md:4-6 reads more cleanly."
                        ),
                    }
                ],
                "pattern_findings": [],
            }

            calls: list[str] = []

            def fake_run_job(job: runner_module.JobSpec) -> None:
                calls.append(job.job_id)
                output = run_dir / "reviews" / "cycle_01" / "full_award.review.json"
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(json.dumps(review) + "\n", encoding="utf-8")

            runner._run_job = fake_run_job

            runner._run_full_award_review_stage(1)

            self.assertEqual(calls, ["cycle_01_full_award_review"])
            saved = json.loads(
                (
                    run_dir / "reviews" / "cycle_01" / "full_award.review.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(saved["findings"][0]["severity"], "LOW")

    def test_build_full_award_review_job_mentions_unquoted_integer_cycle_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_full_award_prompt_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            run_dir = runner.cfg.run_dir
            (run_dir / "outline").mkdir(parents=True, exist_ok=True)
            (run_dir / "config" / "prompts").mkdir(parents=True, exist_ok=True)
            (run_dir / "outline" / "continuity_sheet.json").write_text(
                json.dumps(
                    {
                        "characters": [],
                        "timeline": {
                            "story_start": "spring",
                            "estimated_span": "one month",
                            "seasonal_track": [],
                            "key_events": [],
                        },
                        "geography": {
                            "primary_setting": "city",
                            "key_locations": [],
                            "distances": [],
                        },
                        "world_rules": [],
                        "power_structure": [],
                        "objects": [],
                        "financial_state": {"debts": [], "income_sources": []},
                        "knowledge_state": [],
                        "environmental_constants": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (run_dir / "config" / "prompts" / "full_award_review_prompt.md").write_text(
                (REPO_ROOT / "prompts" / "full_award_review_prompt.md").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )

            job = runner._build_full_award_review_job(1)
            self.assertIn("unquoted integer `1`", job.prompt_text)
            self.assertIn('not a zero-padded or quoted string like `"01"`', job.prompt_text)

    def test_load_repaired_full_award_review_coerces_legacy_single_hit_pattern(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_full_award_pattern_repair_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1,
                    chapter_engine="engine",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
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
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                ),
            ]
            run_dir = runner.cfg.run_dir
            (run_dir / "reviews" / "cycle_01").mkdir(parents=True, exist_ok=True)
            review_rel = "reviews/cycle_01/full_award.review.json"
            (run_dir / review_rel).write_text(
                json.dumps(
                    {
                        "cycle": 1,
                        "verdict": "FAIL",
                        "summary": "Pattern review.",
                        "findings": [],
                        "pattern_findings": [
                            {
                                "finding_id": "P1",
                                "severity": "MEDIUM",
                                "chapter_id": "ch1",
                                "description": "A recurring pattern weakens the prose.",
                                "evidence": ["snapshots/cycle_01/FINAL_NOVEL.md:12"],
                                "rewrite_direction": "Roughen the repeated explanatory phrasing.",
                                "acceptance_test": "The cited lines stop repeating the same explanatory move.",
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            repaired = runner._load_repaired_full_award_review(
                review_rel,
                1,
                {"chapter_01", "chapter_02"},
                "snapshots/cycle_01/FINAL_NOVEL.md",
            )
            runner._validate_full_award_review_json(
                repaired,
                1,
                {"chapter_01", "chapter_02"},
                review_rel,
                "snapshots/cycle_01/FINAL_NOVEL.md",
            )

            pattern = repaired["pattern_findings"][0]
            self.assertEqual(pattern["pattern_id"], "P1")
            self.assertEqual(pattern["affected_chapters"], ["chapter_01"])
            self.assertEqual(pattern["chapter_hits"][0]["chapter_id"], "chapter_01")
            self.assertTrue(
                (
                    run_dir / "reviews" / "cycle_01" / "full_award.review.invalid.original.json"
                ).is_file()
            )

    def test_load_repaired_cross_chapter_audit_normalizes_shape_and_preserves_original(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_cross_audit_repair_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1,
                    chapter_engine="engine",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
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
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                ),
            ]
            run_dir = runner.cfg.run_dir
            (run_dir / "reviews" / "cycle_01").mkdir(parents=True, exist_ok=True)
            rel = "reviews/cycle_01/cross_chapter_audit.json"
            legacy = {
                "cycle": "01",
                "summary": "",
                "redundancy_findings": [
                    {
                        "finding_id": "DUPLICATE_ID",
                        "category": "REDUNDANCY",
                        "subcategory": "",
                        "severity": "medium",
                        "chapter_id": "ch1",
                        "evidence": ["snapshots/cycle_01/FINAL_NOVEL.md:12"],
                        "description": "Priya gets a fresh portrait even though she was already introduced.",
                        "revision_directive": "Cut the repeated physical sketch and keep only one identifying detail.",
                        "acceptance_test": "The later chapter no longer reintroduces Priya with a fresh portrait.",
                    }
                ],
                "consistency_findings": [
                    {
                        "finding_id": "DUPLICATE_ID",
                        "category": "CONSISTENCY",
                        "subcategory": "object_tracking",
                        "severity": "high",
                        "chapter_id": "ch2",
                        "evidence": ["snapshots/cycle_01/FINAL_NOVEL.md:41"],
                        "problem": "The notebook appears here after being left elsewhere.",
                        "revision_directive": "Restore the notebook's prior location or add the missing transfer.",
                        "acceptance_test": "The notebook's location is causally consistent with the earlier chapter.",
                    }
                ],
            }
            (run_dir / rel).write_text(json.dumps(legacy) + "\n", encoding="utf-8")

            repaired = runner._load_repaired_cross_chapter_audit(
                rel,
                1,
                {"chapter_01", "chapter_02"},
                "snapshots/cycle_01/FINAL_NOVEL.md",
            )

            self.assertEqual(repaired["cycle"], 1)
            self.assertTrue(repaired["summary"])
            self.assertEqual(repaired["redundancy_findings"][0]["category"], "redundancy")
            self.assertEqual(repaired["redundancy_findings"][0]["chapter_id"], "chapter_01")
            self.assertEqual(
                repaired["redundancy_findings"][0]["problem"],
                "Priya gets a fresh portrait even though she was already introduced.",
            )
            self.assertEqual(
                repaired["redundancy_findings"][0]["rewrite_direction"],
                "Cut the repeated physical sketch and keep only one identifying detail.",
            )
            self.assertEqual(
                repaired["consistency_findings"][0]["finding_id"],
                "DUPLICATE_ID_2",
            )
            self.assertEqual(
                repaired["consistency_findings"][0]["category"],
                "consistency",
            )
            preserved = (
                run_dir
                / "reviews"
                / "cycle_01"
                / "cross_chapter_audit.invalid.original.json"
            )
            self.assertTrue(preserved.is_file())
            self.assertEqual(json.loads(preserved.read_text(encoding="utf-8")), legacy)

    def test_compute_windows_uses_overlap_and_keeps_tail_window(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_local_window_layout_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            chapter_ids = [f"chapter_{idx:02d}" for idx in range(1, 19)]

            windows = runner._compute_windows(chapter_ids, 4, 2)

            self.assertEqual(len(windows), 8)
            self.assertEqual(
                windows[0],
                ["chapter_01", "chapter_02", "chapter_03", "chapter_04"],
            )
            self.assertEqual(
                windows[1],
                ["chapter_03", "chapter_04", "chapter_05", "chapter_06"],
            )
            self.assertEqual(
                windows[-1],
                ["chapter_15", "chapter_16", "chapter_17", "chapter_18"],
            )
            self.assertEqual(
                runner._compute_windows(chapter_ids[:5], 4, 2),
                [
                    ["chapter_01", "chapter_02", "chapter_03", "chapter_04"],
                    ["chapter_03", "chapter_04", "chapter_05"],
                ],
            )

    def test_build_chapter_line_index_tracks_final_novel_line_ranges(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_chapter_line_index_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1,
                    chapter_engine="engine",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
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
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                ),
                runner_module.ChapterSpec(
                    chapter_id="chapter_03",
                    chapter_number=3,
                    projected_min_words=1,
                    chapter_engine="engine",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                ),
            ]

            compiled_novel = runner.cfg.run_dir / "snapshots" / "cycle_01" / "FINAL_NOVEL.md"
            compiled_novel.parent.mkdir(parents=True, exist_ok=True)
            compiled_novel.write_text(
                "# Title\n\n# Chapter 1\n\nOne.\n\n# Chapter 2\n\nTwo.\nThree.\n\n# Chapter 3\n\nFour.\n",
                encoding="utf-8",
            )

            index = runner._build_chapter_line_index(compiled_novel)

            self.assertEqual(
                index,
                {
                    "chapter_01": {"start_line": 3, "end_line": 6},
                    "chapter_02": {"start_line": 7, "end_line": 11},
                    "chapter_03": {"start_line": 12, "end_line": 14},
                },
            )

    def test_load_repaired_local_window_audit_normalizes_shape_and_preserves_original(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_local_window_repair_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1,
                    chapter_engine="engine",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
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
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                ),
            ]

            run_dir = runner.cfg.run_dir
            (run_dir / "reviews" / "cycle_01").mkdir(parents=True, exist_ok=True)
            rel = "reviews/cycle_01/local_window_02.json"
            legacy = {
                "cycle": "01",
                "window": "2",
                "chapters": ["ch1", "ch2"],
                "findings": [
                    {
                        "category": "coherence",
                        "subcategory": "",
                        "severity": "high",
                        "chapter_id": "ch2",
                        "evidence": ["snapshots/cycle_01/FINAL_NOVEL.md:12"],
                        "counterpart_evidence": ["snapshots/cycle_01/FINAL_NOVEL.md:6"],
                        "description": "Facts shift across the handoff.",
                        "revision_directive": (
                            "Revise snapshots/cycle_01/FINAL_NOVEL.md:10-14 to match the earlier account."
                        ),
                        "acceptance_test": (
                            "Pass if snapshots/cycle_01/FINAL_NOVEL.md:10-14 matches snapshots/cycle_01/FINAL_NOVEL.md:6."
                        ),
                        "boundary_span": "chapter_01/chapter_02",
                    }
                ],
            }
            (run_dir / rel).write_text(json.dumps(legacy) + "\n", encoding="utf-8")

            repaired = runner._load_repaired_local_window_audit(
                rel,
                1,
                {"chapter_01", "chapter_02"},
                "snapshots/cycle_01/FINAL_NOVEL.md",
            )

            finding = repaired["findings"][0]
            self.assertEqual(repaired["cycle"], 1)
            self.assertEqual(repaired["window_id"], "window_02")
            self.assertEqual(repaired["chapters_reviewed"], ["chapter_01", "chapter_02"])
            self.assertEqual(finding["finding_id"], "window_02_001")
            self.assertEqual(finding["category"], "factual_coherence")
            self.assertEqual(finding["subcategory"], "unspecified")
            self.assertEqual(finding["severity"], "HIGH")
            self.assertEqual(finding["chapter_id"], "chapter_02")
            self.assertEqual(finding["problem"], "Facts shift across the handoff.")
            self.assertEqual(finding["pass_hint"], "p1_structural_craft")
            self.assertEqual(
                finding["related_chapter_ids"],
                ["chapter_01", "chapter_02"],
            )
            self.assertTrue(finding["fix_owner_reason"].strip())
            self.assertTrue(repaired["summary"].strip())
            preserved = (
                run_dir
                / "reviews"
                / "cycle_01"
                / "local_window_02.invalid.original.json"
            )
            self.assertTrue(preserved.is_file())
            self.assertEqual(json.loads(preserved.read_text(encoding="utf-8")), legacy)

    def test_validate_local_window_audit_enforces_category_specific_fields(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_local_window_validate_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            chapter_ids = {"chapter_01", "chapter_02"}
            base_payload = {
                "cycle": 1,
                "window_id": "window_01",
                "chapters_reviewed": ["chapter_01", "chapter_02"],
                "summary": "A boundary problem weakens the handoff.",
                "findings": [
                    {
                        "finding_id": "LW01-001",
                        "category": "factual_coherence",
                        "subcategory": "action_attribution",
                        "severity": "HIGH",
                        "chapter_id": "chapter_02",
                        "related_chapter_ids": ["chapter_01"],
                        "boundary_span": "chapter_01/chapter_02",
                        "counterpart_evidence": "snapshots/cycle_01/FINAL_NOVEL.md:6",
                        "pass_hint": "p1_structural_craft",
                        "evidence": "snapshots/cycle_01/FINAL_NOVEL.md:12",
                        "problem": "Facts shift across the handoff.",
                        "rewrite_direction": "Make the later chapter match the earlier fact.",
                        "acceptance_test": "The same physical fact appears in both chapters.",
                        "fix_owner_reason": "The later chapter should conform.",
                    }
                ],
            }

            missing_counterpart = json.loads(json.dumps(base_payload))
            del missing_counterpart["findings"][0]["counterpart_evidence"]
            with self.assertRaisesRegex(
                runner_module.PipelineError,
                "requires counterpart_evidence",
            ):
                runner._validate_local_window_audit_json(
                    missing_counterpart,
                    1,
                    chapter_ids,
                    "reviews/cycle_01/local_window_01.json",
                    "snapshots/cycle_01/FINAL_NOVEL.md",
                )

            missing_related = json.loads(json.dumps(base_payload))
            missing_related["findings"][0]["category"] = "redundant_scene_functions"
            del missing_related["findings"][0]["related_chapter_ids"]
            del missing_related["findings"][0]["boundary_span"]
            with self.assertRaisesRegex(
                runner_module.PipelineError,
                "related_chapter_ids",
            ):
                runner._validate_local_window_audit_json(
                    missing_related,
                    1,
                    chapter_ids,
                    "reviews/cycle_01/local_window_01.json",
                    "snapshots/cycle_01/FINAL_NOVEL.md",
                )

            missing_related_general = json.loads(json.dumps(base_payload))
            missing_related_general["findings"][0]["category"] = "pacing_rhythm"
            del missing_related_general["findings"][0]["related_chapter_ids"]
            with self.assertRaisesRegex(
                runner_module.PipelineError,
                "related_chapter_ids must be a non-empty array",
            ):
                runner._validate_local_window_audit_json(
                    missing_related_general,
                    1,
                    chapter_ids,
                    "reviews/cycle_01/local_window_01.json",
                    "snapshots/cycle_01/FINAL_NOVEL.md",
                )

    def test_load_repaired_local_window_audit_does_not_synthesize_boundary_span_for_nonrequired_categories(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_local_window_no_boundary_repair_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1,
                    chapter_engine="engine",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
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
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                ),
            ]

            run_dir = runner.cfg.run_dir
            (run_dir / "reviews" / "cycle_01").mkdir(parents=True, exist_ok=True)
            rel = "reviews/cycle_01/local_window_01.json"
            payload = {
                "cycle": 1,
                "window_id": "window_01",
                "chapters_reviewed": ["chapter_01", "chapter_02"],
                "summary": "Boundary-local clarity issue.",
                "findings": [
                    {
                        "finding_id": "LW01-001",
                        "category": "pre_scan",
                        "subcategory": "chronology_gap",
                        "severity": "MEDIUM",
                        "chapter_id": "chapter_02",
                        "related_chapter_ids": ["chapter_01"],
                        "pass_hint": "p1_structural_craft",
                        "evidence": "snapshots/cycle_01/FINAL_NOVEL.md:12",
                        "problem": "The timeline is unclear at the chapter boundary.",
                        "rewrite_direction": "Clarify the elapsed time at the start of chapter 2.",
                        "acceptance_test": "A reader can tell how much time passed by the second paragraph.",
                        "fix_owner_reason": "Later chapter owns the missing handoff cue.",
                    }
                ],
            }
            (run_dir / rel).write_text(json.dumps(payload) + "\n", encoding="utf-8")

            repaired = runner._load_repaired_local_window_audit(
                rel,
                1,
                {"chapter_01", "chapter_02"},
                "snapshots/cycle_01/FINAL_NOVEL.md",
            )

            finding = repaired["findings"][0]
            self.assertNotIn("boundary_span", finding)
            preserved = (
                run_dir
                / "reviews"
                / "cycle_01"
                / "local_window_01.invalid.original.json"
            )
            self.assertFalse(preserved.exists())

    def test_default_local_window_pass_hint_covers_all_prompt_categories(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_local_window_pass_hints_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))

            self.assertEqual(
                runner._default_local_window_pass_hint("pre_scan"),
                "p1_structural_craft",
            )
            self.assertEqual(
                runner._default_local_window_pass_hint("pre-scan"),
                "p1_structural_craft",
            )
            self.assertEqual(
                runner._default_local_window_pass_hint("prescan"),
                "p1_structural_craft",
            )
            self.assertEqual(
                runner._default_local_window_pass_hint("repetitive_scene_dynamics"),
                "p1_structural_craft",
            )
            self.assertEqual(
                runner._default_local_window_pass_hint("character_decision_coherence"),
                "p1_structural_craft",
            )
            self.assertEqual(
                runner._default_local_window_pass_hint("scene_dynamics"),
                "p1_structural_craft",
            )
            self.assertEqual(
                runner._default_local_window_pass_hint("decision_coherence"),
                "p1_structural_craft",
            )

    def test_materialize_output_alias_supports_local_window_review_outputs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_local_window_alias_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            run_dir = runner.cfg.run_dir
            (run_dir / "out").mkdir(parents=True, exist_ok=True)
            (run_dir / "out" / "review.json").write_text(
                '{"cycle": 1, "window_id": "window_02"}\n',
                encoding="utf-8",
            )

            copied = runner._materialize_output_alias(
                base_dir=run_dir,
                required_rel="reviews/cycle_01/local_window_02.json",
                stage="local_window_audit",
                cycle=1,
                chapter_id=None,
            )

            self.assertTrue(copied)
            self.assertEqual(
                (run_dir / "reviews" / "cycle_01" / "local_window_02.json").read_text(
                    encoding="utf-8"
                ),
                '{"cycle": 1, "window_id": "window_02"}\n',
            )
            self.assertEqual(len(runner.validation_warnings), 1)
            self.assertEqual(runner.validation_warnings[0]["action"], "copied_output_alias")

    def test_local_window_unit_state_marks_artifact_stale_when_inputs_change(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_local_window_freshness_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1,
                    chapter_engine="engine",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
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
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                ),
            ]

            run_dir = runner.cfg.run_dir
            runner._prepare_run_dir()
            (run_dir / "outline" / "style_bible.json").write_text("{}\n", encoding="utf-8")
            (run_dir / "context" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (run_dir / "context" / "cycle_01" / "continuity_sheet.json").write_text(
                "{}\n",
                encoding="utf-8",
            )
            (run_dir / "context" / "cycle_01" / "chapter_line_index.json").write_text(
                json.dumps(
                    {
                        "chapter_01": {"start_line": 3, "end_line": 6},
                        "chapter_02": {"start_line": 7, "end_line": 10},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (run_dir / "outline" / "chapter_specs").mkdir(parents=True, exist_ok=True)
            chapter_spec_rel = run_dir / "outline" / "chapter_specs" / "chapter_01.json"
            chapter_spec_rel.write_text("{}\n", encoding="utf-8")
            (run_dir / "outline" / "chapter_specs" / "chapter_02.json").write_text(
                "{}\n",
                encoding="utf-8",
            )
            (run_dir / "snapshots" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (run_dir / "snapshots" / "cycle_01" / "FINAL_NOVEL.md").write_text(
                "# Title\n\n# Chapter 1\n\nOne.\n\n# Chapter 2\n\nTwo.\n",
                encoding="utf-8",
            )

            artifact_rel = "reviews/cycle_01/local_window_01.json"
            artifact_path = run_dir / artifact_rel
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text(
                json.dumps(
                    {
                        "cycle": 1,
                        "window_id": "window_01",
                        "chapters_reviewed": ["chapter_01", "chapter_02"],
                        "summary": "The window reads cleanly.",
                        "findings": [
                            {
                                "finding_id": "LW01-001",
                                "category": "reading_momentum",
                                "subcategory": "pressure_gain",
                                "severity": "MEDIUM",
                                "chapter_id": "chapter_02",
                                "related_chapter_ids": ["chapter_01"],
                                "pass_hint": "p1_structural_craft",
                                "evidence": "snapshots/cycle_01/FINAL_NOVEL.md:8",
                                "problem": "The handoff needs sharper pressure.",
                                "rewrite_direction": "Sharpen the new pressure at the chapter turn.",
                                "acceptance_test": "The next chapter opens with materially higher pressure.",
                                "fix_owner_reason": "The later chapter owns the handoff.",
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            state = runner._local_window_audit_unit_state(
                1,
                "window_01",
                ["chapter_01", "chapter_02"],
            )
            self.assertEqual(state["status"], "reused")
            self.assertTrue(state["fresh"])

            future_mtime = artifact_path.stat().st_mtime + 5
            os.utime(chapter_spec_rel, (future_mtime, future_mtime))

            stale_state = runner._local_window_audit_unit_state(
                1,
                "window_01",
                ["chapter_01", "chapter_02"],
            )
            self.assertEqual(stale_state["status"], "stale")
            self.assertEqual(stale_state["reason"], "inputs_newer_than_output")

    def test_build_local_window_audit_job_includes_expected_inputs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_local_window_job_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id=f"chapter_{idx:02d}",
                    chapter_number=idx,
                    projected_min_words=1,
                    chapter_engine="engine",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
                for idx in range(1, 5)
            ]

            runner._prepare_run_dir()
            run_dir = runner.cfg.run_dir
            (run_dir / "outline" / "continuity_sheet.json").write_text("{}\n", encoding="utf-8")

            job = runner._build_local_window_audit_job(
                1,
                ["chapter_01", "chapter_02", "chapter_03", "chapter_04"],
                {},
            )

            self.assertIn("outline/style_bible.json", job.allowed_inputs)
            self.assertIn("context/cycle_01/chapter_line_index.json", job.allowed_inputs)
            self.assertIn("outline/chapter_specs/chapter_01.json", job.allowed_inputs)
            self.assertIn("config/prompts/local_window_audit_prompt.md", job.allowed_inputs)
            self.assertEqual(job.stage_group, "cross_chapter_audit")
            self.assertIn("window_01", job.prompt_text)
            self.assertIn("context/cycle_01/chapter_line_index.json", job.prompt_text)

    def test_run_local_window_audit_stage_reuses_fresh_windows_and_builds_missing_ones(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_local_window_stage_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id=f"chapter_{idx:02d}",
                    chapter_number=idx,
                    projected_min_words=1,
                    chapter_engine="engine",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
                for idx in range(1, 7)
            ]

            runner._prepare_run_dir()
            run_dir = runner.cfg.run_dir
            (run_dir / "outline" / "style_bible.json").write_text("{}\n", encoding="utf-8")
            (run_dir / "outline" / "continuity_sheet.json").write_text("{}\n", encoding="utf-8")
            runner._ensure_cycle_continuity_snapshot(1)
            (run_dir / "outline" / "chapter_specs").mkdir(parents=True, exist_ok=True)
            for idx in range(1, 7):
                (run_dir / "outline" / "chapter_specs" / f"chapter_{idx:02d}.json").write_text(
                    "{}\n",
                    encoding="utf-8",
                )

            final_novel = run_dir / "snapshots" / "cycle_01" / "FINAL_NOVEL.md"
            final_novel.parent.mkdir(parents=True, exist_ok=True)
            final_novel.write_text(
                "# Title\n\n"
                "# Chapter 1\n\nOne.\n\n"
                "# Chapter 2\n\nTwo.\n\n"
                "# Chapter 3\n\nThree.\n\n"
                "# Chapter 4\n\nFour.\n\n"
                "# Chapter 5\n\nFive.\n\n"
                "# Chapter 6\n\nSix.\n",
                encoding="utf-8",
            )
            runner._write_json(
                runner._chapter_line_index_rel(1),
                runner._build_chapter_line_index(final_novel),
            )

            existing_rel = runner._local_window_audit_rel(1, "window_01")
            (run_dir / existing_rel).parent.mkdir(parents=True, exist_ok=True)
            (run_dir / existing_rel).write_text(
                json.dumps(
                    {
                        "cycle": 1,
                        "window_id": "window_01",
                        "chapters_reviewed": [
                            "chapter_01",
                            "chapter_02",
                            "chapter_03",
                            "chapter_04",
                        ],
                        "summary": "Existing window artifact.",
                        "findings": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            summary = runner._run_local_window_audit_stage(1)

            self.assertEqual(summary["status"], "complete")
            self.assertEqual(summary["units"]["window_01"]["status"], "reused")
            self.assertEqual(summary["units"]["window_02"]["status"], "complete")
            self.assertTrue(
                (run_dir / runner._local_window_audit_rel(1, "window_02")).is_file()
            )

    def test_run_local_window_audit_stage_is_nonblocking_when_setup_prereq_is_missing(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_local_window_setup_fail_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id=f"chapter_{idx:02d}",
                    chapter_number=idx,
                    projected_min_words=1,
                    chapter_engine="engine",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
                for idx in range(1, 5)
            ]

            runner._prepare_run_dir()
            run_dir = runner.cfg.run_dir
            (run_dir / "outline" / "style_bible.json").write_text("{}\n", encoding="utf-8")
            (run_dir / "outline" / "continuity_sheet.json").write_text("{}\n", encoding="utf-8")
            runner._ensure_cycle_continuity_snapshot(1)
            (run_dir / "outline" / "chapter_specs").mkdir(parents=True, exist_ok=True)
            for idx in range(1, 5):
                (run_dir / "outline" / "chapter_specs" / f"chapter_{idx:02d}.json").write_text(
                    "{}\n",
                    encoding="utf-8",
                )

            final_novel = run_dir / "snapshots" / "cycle_01" / "FINAL_NOVEL.md"
            final_novel.parent.mkdir(parents=True, exist_ok=True)
            final_novel.write_text(
                "# Title\n\n"
                "# Chapter 1\n\nOne.\n\n"
                "# Chapter 2\n\nTwo.\n\n"
                "# Chapter 3\n\nThree.\n\n"
                "# Chapter 4\n\nFour.\n",
                encoding="utf-8",
            )

            summary = runner._run_local_window_audit_stage(1)

            self.assertEqual(summary["status"], "failed")
            self.assertEqual(summary["reason"], "setup_failed_nonblocking")
            self.assertTrue(
                any(
                    row.get("stage") == "local_window_audit"
                    and row.get("action") == "continued_after_local_window_setup_failure"
                    for row in runner.validation_warnings
                )
            )

    def test_aggregate_findings_collects_local_window_findings(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_local_window_aggregate_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id=f"chapter_{idx:02d}",
                    chapter_number=idx,
                    projected_min_words=1,
                    chapter_engine="engine",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
                for idx in range(1, 5)
            ]

            run_dir = runner.cfg.run_dir
            (run_dir / "reviews" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (run_dir / "snapshots" / "cycle_01" / "chapters").mkdir(parents=True, exist_ok=True)
            for idx in range(1, 5):
                chapter_id = f"chapter_{idx:02d}"
                (run_dir / "snapshots" / "cycle_01" / "chapters" / f"{chapter_id}.md").write_text(
                    f"# Chapter {idx}\n\nEnough words here for {chapter_id}.\n",
                    encoding="utf-8",
                )
                (run_dir / "reviews" / "cycle_01" / f"{chapter_id}.review.json").write_text(
                    json.dumps(
                        {
                            "chapter_id": chapter_id,
                            "verdicts": {
                                runner_module.PRIMARY_REVIEW_LENS: "PASS",
                                "craft": "PASS",
                                "dialogue": "PASS",
                                "prose": "PASS",
                            },
                            "findings": [],
                            "summary": "No chapter-local blockers.",
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )

            (run_dir / "snapshots" / "cycle_01" / "FINAL_NOVEL.md").write_text(
                "# Title\n\n"
                "# Chapter 1\n\nOne.\n\n"
                "# Chapter 2\n\nTwo.\n\n"
                "# Chapter 3\n\nThree.\n\n"
                "# Chapter 4\n\nFour.\n",
                encoding="utf-8",
            )
            (run_dir / "reviews" / "cycle_01" / "full_award.review.json").write_text(
                json.dumps(
                    {
                        "cycle": 1,
                        "verdict": "PASS",
                        "summary": "No global blockers.",
                        "findings": [],
                        "pattern_findings": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (run_dir / "reviews" / "cycle_01" / "cross_chapter_audit.json").write_text(
                json.dumps(
                    {
                        "cycle": 1,
                        "summary": "No cross-chapter blockers.",
                        "redundancy_findings": [],
                        "consistency_findings": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (run_dir / "reviews" / "cycle_01" / "local_window_01.json").write_text(
                json.dumps(
                    {
                        "cycle": 1,
                        "window_id": "window_01",
                        "chapters_reviewed": [
                            "chapter_01",
                            "chapter_02",
                            "chapter_03",
                            "chapter_04",
                        ],
                        "summary": "One boundary-local voice issue.",
                        "findings": [
                            {
                                "finding_id": "LW01-001",
                                "category": "boundary_local_voice_drift",
                                "subcategory": "dialogue_register",
                                "severity": "HIGH",
                                "chapter_id": "chapter_03",
                                "related_chapter_ids": ["chapter_02"],
                                "boundary_span": "chapter_02/chapter_03",
                                "pass_hint": "p2_dialogue_idiolect_cadence",
                                "evidence": "snapshots/cycle_01/FINAL_NOVEL.md:12",
                                "problem": "The dialogue register flips abruptly at the handoff.",
                                "rewrite_direction": "Revise snapshots/cycle_01/FINAL_NOVEL.md:12-16 so Chapter 3 preserves the prior register while staying scene-pressured.",
                                "acceptance_test": "The cited handoff now sounds like the same speakerly world rather than a reset into cleaner dialogue.",
                                "fix_owner_reason": "The drift first appears in the later chapter.",
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            aggregate = runner._aggregate_findings(1)

            self.assertEqual(aggregate["summary"]["local_window_windows_expected"], 1)
            self.assertEqual(aggregate["summary"]["local_window_windows_available"], 1)
            self.assertEqual(aggregate["summary"]["by_source"]["local_window"], 1)
            finding = aggregate["all_findings"][0]
            self.assertEqual(finding["source"], "local_window")
            self.assertEqual(
                runner._assign_revision_pass_key(finding),
                "p2_dialogue_idiolect_cadence",
            )

    def test_aggregate_findings_uses_configured_local_window_layout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_local_window_aggregate_cfg_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.cfg = dataclasses.replace(
                runner.cfg,
                local_window_size=3,
                local_window_overlap=1,
            )
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id=f"chapter_{idx:02d}",
                    chapter_number=idx,
                    projected_min_words=1,
                    chapter_engine="engine",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
                for idx in range(1, 7)
            ]

            run_dir = runner.cfg.run_dir
            (run_dir / "reviews" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (run_dir / "snapshots" / "cycle_01" / "chapters").mkdir(parents=True, exist_ok=True)
            for idx in range(1, 7):
                chapter_id = f"chapter_{idx:02d}"
                (run_dir / "snapshots" / "cycle_01" / "chapters" / f"{chapter_id}.md").write_text(
                    f"# Chapter {idx}\n\nEnough words here for {chapter_id}.\n",
                    encoding="utf-8",
                )
                (run_dir / "reviews" / "cycle_01" / f"{chapter_id}.review.json").write_text(
                    json.dumps(
                        {
                            "chapter_id": chapter_id,
                            "verdicts": {
                                runner_module.PRIMARY_REVIEW_LENS: "PASS",
                                "craft": "PASS",
                                "dialogue": "PASS",
                                "prose": "PASS",
                            },
                            "findings": [],
                            "summary": "No chapter-local blockers.",
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )

            (run_dir / "snapshots" / "cycle_01" / "FINAL_NOVEL.md").write_text(
                "# Title\n\n"
                "# Chapter 1\n\nOne.\n\n"
                "# Chapter 2\n\nTwo.\n\n"
                "# Chapter 3\n\nThree.\n\n"
                "# Chapter 4\n\nFour.\n\n"
                "# Chapter 5\n\nFive.\n\n"
                "# Chapter 6\n\nSix.\n",
                encoding="utf-8",
            )
            (run_dir / "reviews" / "cycle_01" / "full_award.review.json").write_text(
                json.dumps(
                    {
                        "cycle": 1,
                        "verdict": "PASS",
                        "summary": "No global blockers.",
                        "findings": [],
                        "pattern_findings": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (run_dir / "reviews" / "cycle_01" / "cross_chapter_audit.json").write_text(
                json.dumps(
                    {
                        "cycle": 1,
                        "summary": "No cross-chapter blockers.",
                        "redundancy_findings": [],
                        "consistency_findings": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (run_dir / "reviews" / "cycle_01" / "local_window_01.json").write_text(
                json.dumps(
                    {
                        "cycle": 1,
                        "window_id": "window_01",
                        "chapters_reviewed": [
                            "chapter_01",
                            "chapter_02",
                            "chapter_03",
                        ],
                        "summary": "One local-window issue.",
                        "findings": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            aggregate = runner._aggregate_findings(1)

            self.assertEqual(aggregate["summary"]["local_window_windows_expected"], 3)
            self.assertEqual(aggregate["summary"]["local_window_windows_available"], 1)

    def test_aggregate_findings_dedupes_cross_chapter_and_full_award_overlap(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_cross_audit_dedupe_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1,
                    chapter_engine="engine",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
            ]

            run_dir = runner.cfg.run_dir
            (run_dir / "reviews" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (run_dir / "snapshots" / "cycle_01" / "chapters").mkdir(parents=True, exist_ok=True)
            (run_dir / "snapshots" / "cycle_01" / "chapters" / "chapter_01.md").write_text(
                "# Chapter 1\n\nEnough words here.\n",
                encoding="utf-8",
            )
            chapter_review = {
                "chapter_id": "chapter_01",
                "verdicts": {
                    runner_module.PRIMARY_REVIEW_LENS: "PASS",
                    "craft": "PASS",
                    "dialogue": "PASS",
                    "prose": "PASS",
                },
                "findings": [],
                "summary": "No chapter-local blockers.",
            }
            (run_dir / "reviews" / "cycle_01" / "chapter_01.review.json").write_text(
                json.dumps(chapter_review) + "\n",
                encoding="utf-8",
            )
            full_review = {
                "cycle": 1,
                "verdict": "FAIL",
                "summary": "A repeated introduction weakens Chapter 1.",
                "findings": [
                    {
                        "finding_id": "PRIYA_INTRO_AWARD",
                        "severity": "MEDIUM",
                        "chapter_id": "chapter_01",
                        "evidence": "snapshots/cycle_01/FINAL_NOVEL.md:12",
                        "problem": "Priya is reintroduced with a fresh physical sketch after the manuscript already established her.",
                        "rewrite_direction": "Cut the repeated physical sketch in snapshots/cycle_01/FINAL_NOVEL.md:12-15 and keep only one identifying detail.",
                        "acceptance_test": "The cited lines no longer give Priya a fresh portrait after her first introduction.",
                    }
                ],
                "pattern_findings": [],
            }
            (run_dir / "reviews" / "cycle_01" / "full_award.review.json").write_text(
                json.dumps(full_review) + "\n",
                encoding="utf-8",
            )
            cross_audit = {
                "cycle": 1,
                "summary": "Repeated introduction issue.",
                "redundancy_findings": [
                    {
                        "finding_id": "PRIYA_INTRO_AUDIT",
                        "category": "redundancy",
                        "subcategory": "character_reintroduction",
                        "severity": "MEDIUM",
                        "chapter_id": "chapter_01",
                        "evidence": "snapshots/cycle_01/FINAL_NOVEL.md:15",
                        "problem": "Priya is reintroduced with a fresh physical sketch after the manuscript already established her.",
                        "rewrite_direction": "Cut the repeated physical sketch in snapshots/cycle_01/FINAL_NOVEL.md:12-15 and keep only one identifying detail.",
                        "acceptance_test": "The cited lines no longer give Priya a fresh portrait after her first introduction.",
                    }
                ],
                "consistency_findings": [],
            }
            (run_dir / "reviews" / "cycle_01" / "cross_chapter_audit.json").write_text(
                json.dumps(cross_audit) + "\n",
                encoding="utf-8",
            )

            aggregate = runner._aggregate_findings(1)

            self.assertEqual(len(aggregate["all_findings"]), 1)
            finding = aggregate["all_findings"][0]
            self.assertEqual(finding["chapter_id"], "chapter_01")
            self.assertEqual(finding["source"], "award_global")
            self.assertIn("snapshots/cycle_01/FINAL_NOVEL.md:12", finding["evidence"])
            self.assertIn("snapshots/cycle_01/FINAL_NOVEL.md:15", finding["evidence"])

    def test_aggregate_findings_promotes_cross_chapter_source_for_stronger_routing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_cross_audit_route_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1,
                    chapter_engine="engine",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
            ]

            run_dir = runner.cfg.run_dir
            (run_dir / "reviews" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (run_dir / "snapshots" / "cycle_01" / "chapters").mkdir(parents=True, exist_ok=True)
            (run_dir / "snapshots" / "cycle_01" / "chapters" / "chapter_01.md").write_text(
                "# Chapter 1\n\nEnough words here.\n",
                encoding="utf-8",
            )
            chapter_review = {
                "chapter_id": "chapter_01",
                "verdicts": {
                    runner_module.PRIMARY_REVIEW_LENS: "PASS",
                    "craft": "PASS",
                    "dialogue": "PASS",
                    "prose": "FAIL",
                },
                "findings": [
                    {
                        "finding_id": "PRIYA_INTRO_PROSE",
                        "source": "prose",
                        "severity": "MEDIUM",
                        "chapter_id": "chapter_01",
                        "evidence": "snapshots/cycle_01/FINAL_NOVEL.md:12",
                        "problem": "Priya is reintroduced with a fresh physical sketch after the manuscript already established her.",
                        "rewrite_direction": "Cut the repeated physical sketch in snapshots/cycle_01/FINAL_NOVEL.md:12-15 and keep only one identifying detail.",
                        "acceptance_test": "The cited lines no longer give Priya a fresh portrait after her first introduction.",
                    }
                ],
                "summary": "One prose-level issue.",
            }
            (run_dir / "reviews" / "cycle_01" / "chapter_01.review.json").write_text(
                json.dumps(chapter_review) + "\n",
                encoding="utf-8",
            )
            full_review = {
                "cycle": 1,
                "verdict": "PASS",
                "summary": "No global blockers.",
                "findings": [],
                "pattern_findings": [],
            }
            (run_dir / "reviews" / "cycle_01" / "full_award.review.json").write_text(
                json.dumps(full_review) + "\n",
                encoding="utf-8",
            )
            cross_audit = {
                "cycle": 1,
                "summary": "Repeated introduction issue.",
                "redundancy_findings": [
                    {
                        "finding_id": "PRIYA_INTRO_AUDIT",
                        "category": "redundancy",
                        "subcategory": "character_reintroduction",
                        "severity": "MEDIUM",
                        "chapter_id": "chapter_01",
                        "evidence": "snapshots/cycle_01/FINAL_NOVEL.md:15",
                        "problem": "Priya is reintroduced with a fresh physical sketch after the manuscript already established her.",
                        "rewrite_direction": "Cut the repeated physical sketch in snapshots/cycle_01/FINAL_NOVEL.md:12-15 and keep only one identifying detail.",
                        "acceptance_test": "The cited lines no longer give Priya a fresh portrait after her first introduction.",
                    }
                ],
                "consistency_findings": [],
            }
            (run_dir / "reviews" / "cycle_01" / "cross_chapter_audit.json").write_text(
                json.dumps(cross_audit) + "\n",
                encoding="utf-8",
            )

            aggregate = runner._aggregate_findings(1)

            self.assertEqual(len(aggregate["all_findings"]), 1)
            finding = aggregate["all_findings"][0]
            self.assertEqual(finding["source"], "cross_chapter")
            self.assertIn("snapshots/cycle_01/FINAL_NOVEL.md:12", finding["evidence"])
            self.assertIn("snapshots/cycle_01/FINAL_NOVEL.md:15", finding["evidence"])

    def test_cross_chapter_audit_fallback_forces_gate_fail(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_cross_audit_gate_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1,
                    chapter_engine="engine",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
            ]

            run_dir = runner.cfg.run_dir
            (run_dir / "reviews" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (run_dir / "snapshots" / "cycle_01" / "chapters").mkdir(parents=True, exist_ok=True)
            (run_dir / "snapshots" / "cycle_01" / "chapters" / "chapter_01.md").write_text(
                "# Chapter 1\n\nEnough words here.\n",
                encoding="utf-8",
            )
            chapter_review = {
                "chapter_id": "chapter_01",
                "verdicts": {
                    runner_module.PRIMARY_REVIEW_LENS: "PASS",
                    "craft": "PASS",
                    "dialogue": "PASS",
                    "prose": "PASS",
                },
                "findings": [],
                "summary": "No chapter-local blockers.",
            }
            (run_dir / "reviews" / "cycle_01" / "chapter_01.review.json").write_text(
                json.dumps(chapter_review) + "\n",
                encoding="utf-8",
            )
            full_review = {
                "cycle": 1,
                "verdict": "PASS",
                "summary": "No global blockers.",
                "findings": [],
                "pattern_findings": [],
            }
            (run_dir / "reviews" / "cycle_01" / "full_award.review.json").write_text(
                json.dumps(full_review) + "\n",
                encoding="utf-8",
            )
            (run_dir / "reviews" / "cycle_01" / "cross_chapter_audit.json").write_text(
                json.dumps(runner._fallback_cross_chapter_audit_payload(1)) + "\n",
                encoding="utf-8",
            )

            aggregate = runner._aggregate_findings(1)
            gate = runner._write_gate(1, aggregate)

            self.assertTrue(aggregate["cross_chapter_audit_failed"])
            self.assertTrue(gate["cross_chapter_audit_failed"])
            self.assertEqual(gate["decision"], "FAIL")
            self.assertEqual(gate["reason"], "cross_chapter_audit_failed")

    def test_load_existing_cycle_status_returns_none_for_invalid_shape(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_cycle_status_invalid_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            (runner.cfg.run_dir / "status" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (runner.cfg.run_dir / "status" / "cycle_01" / "cycle_status.json").write_text(
                json.dumps({"cycle": 1}) + "\n",
                encoding="utf-8",
            )

            self.assertIsNone(runner._load_existing_cycle_status(1))

    def test_write_gate_counts_only_medium_plus_when_low_findings_present(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_gate_low_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            gate = runner._write_gate(
                1,
                {
                    "all_findings": [
                        {
                            "finding_id": "LOW_NOTE",
                            "source": "award_global",
                            "severity": "LOW",
                            "chapter_id": "chapter_01",
                            "evidence": "snapshots/cycle_01/FINAL_NOVEL.md:4",
                            "problem": "A soft note.",
                            "rewrite_direction": "Revise snapshots/cycle_01/FINAL_NOVEL.md:4-6.",
                            "acceptance_test": "Pass if snapshots/cycle_01/FINAL_NOVEL.md:4-6 reads more cleanly.",
                            "status": "UNRESOLVED",
                            "cycle": 1,
                        }
                    ],
                    "full_award_verdict": "FAIL",
                    "chapter_review_failures": 0,
                    "cross_chapter_audit_failed": False,
                },
            )

            self.assertEqual(gate["unresolved_medium_plus_count"], 0)
            self.assertEqual(gate["decision"], "FAIL")
            self.assertEqual(gate["full_award_verdict"], "FAIL")

    def test_resume_cycle_status_preserves_existing_units(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_cycle_status_resume_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))

            resumed = runner._resume_cycle_status(
                1,
                {
                    "cycle": 1,
                    "stages": {
                        "chapter_review": {
                            "status": "complete",
                            "required": True,
                            "units": {
                                "chapter_01": {
                                    "status": "reused",
                                    "validated": True,
                                    "fresh": True,
                                }
                            },
                        }
                    },
                    "advisory_gate": {"decision": "FAIL"},
                },
            )

            self.assertEqual(resumed["run_mode"], "resume")
            self.assertEqual(resumed["resume"]["source"], "cycle_status")
            self.assertEqual(
                resumed["stages"]["chapter_review"]["units"]["chapter_01"]["status"],
                "reused",
            )
            self.assertEqual(resumed["advisory_gate"]["decision"], "FAIL")

    def test_cross_chapter_audit_convergence_logging_does_not_rewrite_previous_audit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_cross_audit_convergence_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1,
                    chapter_engine="engine",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
            ]
            run_dir = runner.cfg.run_dir
            (run_dir / "reviews" / "cycle_01").mkdir(parents=True, exist_ok=True)
            prev_rel = run_dir / "reviews" / "cycle_01" / "cross_chapter_audit.json"
            legacy = {
                "cycle": "01",
                "summary": "",
                "redundancy_findings": [
                    {
                        "finding_id": "OLD_1",
                        "category": "REDUNDANCY",
                        "subcategory": "",
                        "severity": "medium",
                        "chapter_id": "ch1",
                        "evidence": ["snapshots/cycle_01/FINAL_NOVEL.md:12"],
                        "description": "Repeated intro.",
                        "revision_directive": "Cut it.",
                        "acceptance_test": "Gone.",
                    }
                ],
                "consistency_findings": [],
            }
            prev_rel.write_text(json.dumps(legacy) + "\n", encoding="utf-8")

            before = prev_rel.read_text(encoding="utf-8")
            runner._log_cross_chapter_audit_convergence(
                2,
                {
                    "cycle": 2,
                    "summary": "Cycle 2 audit.",
                    "redundancy_findings": [],
                    "consistency_findings": [],
                },
            )

            self.assertEqual(prev_rel.read_text(encoding="utf-8"), before)
            self.assertFalse(
                (
                    run_dir
                    / "reviews"
                    / "cycle_01"
                    / "cross_chapter_audit.invalid.original.json"
                ).exists()
            )

    def test_run_uses_existing_cycle_status_for_resume_mode(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_cycle_status_resume_run_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            aggregate = {
                "summary": {
                    "cycle": 1,
                    "total_unresolved_medium_plus": 0,
                    "by_severity": {},
                    "by_source": {},
                    "chapters_touched": [],
                    "chapter_review_failures": 0,
                    "full_award_verdict": "PASS",
                    "cross_chapter_audit_failed": False,
                },
                "all_findings": [],
                "by_chapter": {},
                "full_award_verdict": "PASS",
                "chapter_review_failures": 0,
                "cross_chapter_audit_failed": False,
            }
            gate = {
                "cycle": 1,
                "full_award_verdict": "PASS",
                "unresolved_medium_plus_count": 0,
                "chapter_review_failures": 0,
                "cross_chapter_audit_failed": False,
                "decision": "PASS",
                "reason": "all_unresolved_medium_plus_closed_and_full_award_pass",
            }
            (runner.cfg.run_dir / "status" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (runner.cfg.run_dir / "status" / "cycle_01" / "cycle_status.json").write_text(
                json.dumps(
                    {
                        "cycle": 1,
                        "stages": {
                            "chapter_review": {
                                "status": "complete",
                                "required": True,
                                "units": {
                                    "chapter_01": {
                                        "status": "reused",
                                        "validated": True,
                                        "fresh": True,
                                    }
                                },
                            }
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with mock.patch.object(runner, "_prepare_run_dir"), mock.patch.object(
                runner, "_resolve_premise"
            ), mock.patch.object(runner, "_run_outline_stage"), mock.patch.object(
                runner, "_run_draft_stage"
            ), mock.patch.object(
                runner, "_assemble_snapshot", return_value=True
            ), mock.patch.object(
                runner, "_build_cycle_context_packs", return_value=True
            ), mock.patch.object(
                runner,
                "_run_chapter_review_stage",
                return_value={
                    "status": "reused",
                    "chapter_count": 1,
                    "units": {
                        "chapter_01": {
                            "status": "reused",
                            "validated": True,
                            "fresh": True,
                        }
                    },
                },
            ), mock.patch.object(
                runner,
                "_run_parallel_full_book_review_stages",
                return_value={
                    "full_award_review": True,
                    "cross_chapter_audit": True,
                    "local_window_audit": {
                        "status": "reused",
                        "units": {
                            "window_01": {
                                "status": "reused",
                                "validated": True,
                                "fresh": True,
                            }
                        },
                    },
                },
            ), mock.patch.object(
                runner, "_aggregate_findings", return_value=aggregate
            ), mock.patch.object(
                runner, "_write_gate", return_value=gate
            ), mock.patch.object(
                runner, "_assemble_post_revision_snapshot", return_value=True
            ), mock.patch.object(
                runner, "_run_continuity_reconciliation", return_value=True
            ), mock.patch.object(
                runner, "_write_final_report"
            ), mock.patch.object(
                runner, "_print_cost_summary"
            ):
                self.assertEqual(runner.run(), 0)

            payload = json.loads(
                (runner.cfg.run_dir / "status" / "cycle_01" / "cycle_status.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(payload["run_mode"], "resume")
            self.assertEqual(payload["resume"]["source"], "cycle_status")
            self.assertEqual(payload["stages"]["assemble_snapshot"]["status"], "reused")
            self.assertEqual(payload["stages"]["chapter_review"]["status"], "reused")


    def test_chapter_specs_preserve_secondary_character_beats_through_runner_outputs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_secondary_beats_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            run_dir = runner.cfg.run_dir
            (run_dir / "outline").mkdir(parents=True, exist_ok=True)

            rows = []
            for chapter_number in range(1, 17):
                row = {
                    "chapter_id": f"chapter_{chapter_number:02d}",
                    "chapter_number": chapter_number,
                    "projected_min_words": 1000,
                    "chapter_engine": "discovery",
                    "pressure_source": "pressure",
                    "state_shift": "shift",
                    "texture_mode": "hot",
                    "scene_count_target": 2,
                    "must_land_beats": [f"beat {chapter_number}"],
                }
                if chapter_number == 1:
                    row["secondary_character_beats"] = [
                        "Let the desk clerk's private panic leak through her efficiency."
                    ]
                    row["setups_to_plant"] = [
                        {
                            "setup_id": "desk_clerk_panic",
                            "description": "Plant the clerk's concealed panic behind her efficiency.",
                            "payoff_window": "chapter_08-chapter_10",
                            "visibility": "light",
                        }
                    ]
                    row["payoffs_to_land"] = [
                        {
                            "setup_id": "old_map_tear",
                            "description": "Reveal why the torn survey map matters now.",
                            "seeded_by": ["chapter_03"],
                            "payoff_type": "reveal",
                        }
                    ]
                rows.append(json.dumps(row))

            (run_dir / "outline" / "chapter_specs.jsonl").write_text(
                "\n".join(rows) + "\n",
                encoding="utf-8",
            )

            runner.chapter_specs = runner._load_and_validate_chapter_specs()
            runner.style_bible = {
                "character_voice_profiles": [],
                "dialogue_rules": {},
                "prose_style_profile": {},
                "aesthetic_risk_policy": {},
            }
            runner._write_chapter_spec_files()
            runner._build_static_story_context()
            (run_dir / "outline" / "continuity_sheet.json").write_text(
                json.dumps(
                    {
                        "characters": [],
                        "timeline": {
                            "story_start": "spring",
                            "estimated_span": "one month",
                            "seasonal_track": [],
                            "key_events": [],
                        },
                        "geography": {
                            "primary_setting": "town",
                            "key_locations": [],
                            "distances": [],
                        },
                        "world_rules": [],
                        "power_structure": [],
                        "objects": [],
                        "financial_state": {"debts": [], "income_sources": []},
                        "knowledge_state": [],
                        "environmental_constants": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (run_dir / "chapters").mkdir(parents=True, exist_ok=True)
            for spec in runner.chapter_specs:
                (run_dir / "chapters" / f"{spec.chapter_id}.md").write_text(
                    f"# Chapter {spec.chapter_number}\n\nBody for {spec.chapter_id}.\n",
                    encoding="utf-8",
                )
            runner._assemble_snapshot(1)
            runner._build_cycle_context_packs(1)

            self.assertEqual(
                runner.chapter_specs[0].secondary_character_beats,
                ["Let the desk clerk's private panic leak through her efficiency."],
            )

            chapter_spec_json = json.loads(
                (run_dir / "outline" / "chapter_specs" / "chapter_01.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                chapter_spec_json["secondary_character_beats"],
                ["Let the desk clerk's private panic leak through her efficiency."],
            )

            static_story_context = json.loads(
                (run_dir / "outline" / "static_story_context.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                static_story_context["chapter_spine"][0]["secondary_character_beats"],
                ["Let the desk clerk's private panic leak through her efficiency."],
            )
            self.assertEqual(
                static_story_context["chapter_spine"][0]["setups_to_plant"][0]["setup_id"],
                "desk_clerk_panic",
            )
            self.assertEqual(
                static_story_context["chapter_spine"][0]["payoffs_to_land"][0]["setup_id"],
                "old_map_tear",
            )

            global_cycle_context = json.loads(
                (run_dir / "context" / "cycle_01" / "global_cycle_context.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                global_cycle_context["chapter_spine"][0]["setups_to_plant"][0]["setup_id"],
                "desk_clerk_panic",
            )

            boundary_context = json.loads(
                (
                    run_dir
                    / "context"
                    / "cycle_01"
                    / "boundary"
                    / "chapter_01.boundary.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(
                boundary_context["setups_to_plant"][0]["setup_id"],
                "desk_clerk_panic",
            )
            self.assertEqual(
                boundary_context["payoffs_to_land"][0]["setup_id"],
                "old_map_tear",
            )
            self.assertEqual(
                boundary_context["secondary_character_beats"],
                ["Let the desk clerk's private panic leak through her efficiency."],
            )
            self.assertEqual(boundary_context["open_hooks_to_carry"], ["beat 1"])

    def test_chapter_review_stage_reports_reused_units(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_review_units_reused_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner._prepare_run_dir()
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1,
                    chapter_engine="engine",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
            ]

            run_dir = runner.cfg.run_dir
            (run_dir / "outline" / "style_bible.json").write_text("{}\n", encoding="utf-8")
            (run_dir / "outline" / "continuity_sheet.json").write_text("{}\n", encoding="utf-8")
            runner._ensure_cycle_continuity_snapshot(1)
            (run_dir / "snapshots" / "cycle_01" / "chapters").mkdir(parents=True, exist_ok=True)
            (run_dir / "context" / "cycle_01" / "boundary").mkdir(parents=True, exist_ok=True)
            (run_dir / "reviews" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (run_dir / "snapshots" / "cycle_01" / "chapters" / "chapter_01.md").write_text(
                "# Chapter 1\n\nFresh snapshot text.\n",
                encoding="utf-8",
            )
            (run_dir / "context" / "cycle_01" / "global_cycle_context.json").write_text(
                "{}\n",
                encoding="utf-8",
            )
            (run_dir / "context" / "cycle_01" / "boundary" / "chapter_01.boundary.json").write_text(
                "{}\n",
                encoding="utf-8",
            )
            (run_dir / "reviews" / "cycle_01" / "chapter_01.review.json").write_text(
                json.dumps(
                    {
                        "chapter_id": "chapter_01",
                        "verdicts": {
                            runner_module.PRIMARY_REVIEW_LENS: "PASS",
                            "craft": "PASS",
                            "dialogue": "PASS",
                            "prose": "PASS",
                        },
                        "findings": [],
                        "summary": "No chapter-local blockers.",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with mock.patch.object(runner, "_run_jobs_parallel") as jobs_mock:
                summary = runner._run_chapter_review_stage(1)

            jobs_mock.assert_not_called()
            self.assertEqual(summary["status"], "reused")
            self.assertEqual(summary["units"]["chapter_01"]["status"], "reused")

    def test_chapter_expand_job_receives_outline_and_scene_plan_inputs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_expand_inputs_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1000,
                    chapter_engine="discovery",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                    secondary_character_beats=["Give the bartender private stakes."],
                )
            ]

            run_dir = runner.cfg.run_dir
            (run_dir / "chapters").mkdir(parents=True, exist_ok=True)
            (run_dir / "outline" / "chapter_specs").mkdir(parents=True, exist_ok=True)
            (run_dir / "config" / "prompts").mkdir(parents=True, exist_ok=True)
            (run_dir / "outline" / "outline.md").write_text(
                "## Middle-Book Progression Map\n\nplaceholder\n",
                encoding="utf-8",
            )
            (run_dir / "outline" / "scene_plan.tsv").write_text(
                "scene_id\tchapter_id\tscene_order\tobjective\topposition\tturn\tconsequence_cost\ttension_peak\n"
                "s1\tchapter_01\t1\tobj\topp\tturn\tcost\tYES\n",
                encoding="utf-8",
            )
            (run_dir / "outline" / "spatial_layout.json").write_text(
                json.dumps({"summary": "layout", "micro": None, "macro": None}) + "\n",
                encoding="utf-8",
            )
            (run_dir / "chapters" / "chapter_01.md").write_text(
                "# Chapter 1\n\nToo short.\n",
                encoding="utf-8",
            )
            (run_dir / "config" / "prompts" / "chapter_expand_prompt.md").write_text(
                (REPO_ROOT / "prompts" / "chapter_expand_prompt.md").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
            (run_dir / "config" / "prompts" / "chapter_draft_prompt.md").write_text(
                (REPO_ROOT / "prompts" / "chapter_draft_prompt.md").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )

            captured_job_groups: list[tuple[str, list[runner_module.JobSpec]]] = []

            chapter_path = run_dir / "chapters" / "chapter_01.md"

            def fake_fresh(output_path: Path, *_args, **_kwargs) -> bool:
                return output_path != chapter_path

            runner._artifact_fresh_against_inputs = fake_fresh

            def capture_run_jobs_parallel(
                jobs: list[runner_module.JobSpec], _max_parallel: int, label: str
            ) -> None:
                captured_job_groups.append((label, list(jobs)))

            runner._run_jobs_parallel = capture_run_jobs_parallel

            runner._run_draft_stage()

            self.assertEqual(len(captured_job_groups), 2)
            self.assertEqual(captured_job_groups[0][0], "draft")
            self.assertEqual(captured_job_groups[1][0], "draft_expand")
            draft_job = captured_job_groups[0][1][0]
            self.assertEqual(len(captured_job_groups[1][1]), 1)
            expand_job = captured_job_groups[1][1][0]
            self.assertIn("outline/spatial_layout.json", draft_job.allowed_inputs)
            self.assertEqual(expand_job.stage, "chapter_expand")
            self.assertIn("outline/outline.md", expand_job.allowed_inputs)
            self.assertIn("outline/scene_plan.tsv", expand_job.allowed_inputs)
            self.assertIn("outline/spatial_layout.json", expand_job.allowed_inputs)

    def test_run_outline_stage_dry_run_produces_outline_review_revision_and_spatial_layout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_outline_preflight_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))

            runner._prepare_run_dir()
            runner._resolve_premise()
            runner._run_outline_stage()

            run_dir = runner.cfg.run_dir
            review_path = run_dir / "outline" / "outline_review_cycle_01.json"
            revision_path = run_dir / "outline" / "outline_revision_cycle_01.json"
            spatial_layout_path = run_dir / "outline" / "spatial_layout.json"
            preserved_outline_path = (
                run_dir / "outline" / "pre_revision" / "cycle_01" / "outline.md"
            )

            self.assertTrue(review_path.is_file())
            self.assertTrue(revision_path.is_file())
            self.assertTrue(spatial_layout_path.is_file())
            self.assertTrue((run_dir / "outline" / "static_story_context.json").is_file())
            self.assertTrue(preserved_outline_path.is_file())

            revision_payload = json.loads(revision_path.read_text(encoding="utf-8"))
            self.assertEqual(
                revision_payload["review_file"], "outline/outline_review_cycle_01.json"
            )
            self.assertEqual(
                revision_payload["pre_revision_outline_outputs"][0],
                "outline/pre_revision/cycle_01/outline.md",
            )
            self.assertNotIn(
                "[Dry-run outline revision applied]",
                preserved_outline_path.read_text(encoding="utf-8"),
            )
            self.assertIn(
                "[Dry-run outline revision applied]",
                (run_dir / "outline" / "outline.md").read_text(encoding="utf-8"),
            )

            continuity_payload = json.loads(
                (run_dir / "outline" / "continuity_sheet.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                continuity_payload["geography"]["spatial_layout_ref"],
                "outline/spatial_layout.json",
            )

            cycle_status = runner._new_cycle_status(1)
            self.assertEqual(cycle_status["stages"]["outline_review"]["status"], "complete")
            self.assertEqual(cycle_status["stages"]["outline_revision"]["status"], "complete")
            self.assertEqual(cycle_status["stages"]["spatial_layout"]["status"], "complete")

    def test_add_cycles_reuses_outline_spatial_and_draft_even_when_prompts_are_newer(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_add_cycles_precycle_reuse_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))

            runner._prepare_run_dir()
            runner._resolve_premise()
            runner._run_outline_stage()
            runner._run_draft_stage()

            runner.cfg = dataclasses.replace(
                runner.cfg,
                add_cycles=1,
                base_completed_cycles=1,
                skip_outline_review=True,
            )

            time_targets = [
                runner.cfg.run_dir / "config" / "prompts" / "spatial_layout_prompt.md",
                runner.cfg.run_dir / "config" / "prompts" / "chapter_draft_prompt.md",
            ]
            for path in time_targets:
                path.touch()

            with mock.patch.object(runner, "_run_job") as run_job, mock.patch.object(
                runner, "_run_jobs_parallel"
            ) as run_jobs:
                runner._run_outline_stage()
                runner._run_draft_stage()

            run_job.assert_not_called()
            run_jobs.assert_not_called()
            self.assertEqual(runner._precycle_stage_entries["spatial_layout"]["status"], "reused")

    def test_run_continuity_reconciliation_returns_complete_and_validates_outputs(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_continuity_complete_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner._prepare_run_dir()

            run_dir = runner.cfg.run_dir
            (run_dir / "snapshots" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (run_dir / "context" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (run_dir / "outline").mkdir(parents=True, exist_ok=True)
            (run_dir / "reviews" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (run_dir / "snapshots" / "cycle_01" / "FINAL_NOVEL.post_revision.md").write_text(
                "# Title\n\n# Chapter 1\n\nBody.\n",
                encoding="utf-8",
            )
            (run_dir / "context" / "cycle_01" / "global_cycle_context.json").write_text(
                json.dumps({"chapter_spine": []}) + "\n",
                encoding="utf-8",
            )
            (run_dir / "outline" / "spatial_layout.json").write_text(
                json.dumps({"summary": "layout", "micro": None, "macro": None}) + "\n",
                encoding="utf-8",
            )
            (run_dir / "outline" / "continuity_sheet.json").write_text(
                "{}\n",
                encoding="utf-8",
            )

            valid_sheet = {
                "characters": [],
                "timeline": {
                    "story_start": "spring",
                    "estimated_span": "one week",
                    "seasonal_track": [],
                    "key_events": [],
                },
                "geography": {
                    "spatial_layout_ref": "outline/spatial_layout.json",
                    "primary_setting": "city",
                    "key_locations": [],
                    "distances": [],
                },
                "world_rules": [],
                "power_structure": [],
                "objects": [],
                "financial_state": {"debts": [], "income_sources": []},
                "knowledge_state": [],
                "environmental_constants": [],
            }

            def fake_run_job(_job: runner_module.JobSpec) -> None:
                (run_dir / "outline" / "continuity_sheet.json").write_text(
                    json.dumps(valid_sheet) + "\n",
                    encoding="utf-8",
                )
                (run_dir / "reviews" / "cycle_01" / "continuity_conflicts.json").write_text(
                    json.dumps(
                        {
                            "cycle": 1,
                            "conflicts": [],
                            "new_facts_added": 0,
                            "facts_updated": 0,
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )

            runner._run_job = fake_run_job

            with mock.patch.object(
                runner,
                "_validate_continuity_sheet",
                wraps=runner._validate_continuity_sheet,
            ) as validate_mock:
                summary = runner._run_continuity_reconciliation(1)

            self.assertEqual(summary["status"], "complete")
            validate_mock.assert_called_once()

    def test_run_continuity_reconciliation_returns_failed_on_soft_job_error(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_continuity_soft_fail_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner._prepare_run_dir()

            run_dir = runner.cfg.run_dir
            (run_dir / "snapshots" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (run_dir / "context" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (run_dir / "outline").mkdir(parents=True, exist_ok=True)
            (run_dir / "snapshots" / "cycle_01" / "FINAL_NOVEL.post_revision.md").write_text(
                "# Title\n\n# Chapter 1\n\nBody.\n",
                encoding="utf-8",
            )
            (run_dir / "context" / "cycle_01" / "global_cycle_context.json").write_text(
                json.dumps({"chapter_spine": []}) + "\n",
                encoding="utf-8",
            )
            (run_dir / "outline" / "spatial_layout.json").write_text(
                json.dumps({"summary": "layout", "micro": None, "macro": None}) + "\n",
                encoding="utf-8",
            )
            (run_dir / "outline" / "continuity_sheet.json").write_text(
                "{}\n",
                encoding="utf-8",
            )

            with mock.patch.object(
                runner,
                "_run_job",
                side_effect=runner_module.PipelineError("boom"),
            ):
                summary = runner._run_continuity_reconciliation(1)

            self.assertEqual(summary["status"], "failed")
            self.assertEqual(summary["reason"], "job_failed_soft")
            self.assertTrue(
                any(
                    row.get("stage") == "continuity_reconciliation"
                    and row.get("action") == "continuity_reconciliation_failed_soft"
                    for row in runner.validation_warnings
                )
            )

    def test_render_prompt_raises_on_unreplaced_placeholder(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_prompt_guard_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            prompt_dir = runner.cfg.run_dir / "config" / "prompts"
            prompt_dir.mkdir(parents=True, exist_ok=True)
            (prompt_dir / "bad_prompt.md").write_text(
                "Hello {{MISSING_TOKEN}}\n",
                encoding="utf-8",
            )

            with self.assertRaises(runner_module.PipelineError):
                runner._render_prompt("bad_prompt.md", {})

    def test_revision_job_optional_guidance_uses_labels_not_colliding_numbers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_revision_prompt_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            run_dir = runner.cfg.run_dir
            (run_dir / "config" / "prompts").mkdir(parents=True, exist_ok=True)
            (run_dir / "config" / "prompts" / "chapter_revision_prompt.md").write_text(
                (REPO_ROOT / "prompts" / "chapter_revision_prompt.md").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )

            packet_data = {
                "has_locator_excerpts": True,
                "original_snapshot_file": "snapshots/cycle_01/chapters/chapter_01.md",
            }

            structural_job = runner._build_chapter_revision_job(
                cycle=1,
                chapter_id="chapter_01",
                chapter_number=1,
                pass_def=runner_module.REVISION_PASS_DEFS[0],
                global_context_file="context/cycle_01/global_cycle_context.json",
                continuity_sheet_file="context/cycle_01/continuity_sheet.json",
                packet_data=packet_data,
            )
            self.assertIn("Locator guidance:", structural_job.prompt_text)
            self.assertNotIn("\n15. If the revision packet includes", structural_job.prompt_text)
            self.assertIn(
                "snapshots/cycle_01/chapters/chapter_01.md",
                structural_job.allowed_inputs,
            )

            dialogue_job = runner._build_chapter_revision_job(
                cycle=1,
                chapter_id="chapter_01",
                chapter_number=1,
                pass_def=runner_module.REVISION_PASS_DEFS[1],
                global_context_file="context/cycle_01/global_cycle_context.json",
                continuity_sheet_file="context/cycle_01/continuity_sheet.json",
                packet_data=packet_data,
            )
            self.assertIn("Dialogue anchor guidance:", dialogue_job.prompt_text)
            self.assertNotIn("{{CHAPTER_INPUT_FILE}}", dialogue_job.prompt_text)
            self.assertNotIn("\n13. Use the original pre-revision snapshot", dialogue_job.prompt_text)
            self.assertIn(
                "snapshots/cycle_01/chapters/chapter_01.md",
                dialogue_job.allowed_inputs,
            )

    def test_style_bible_repair_clamps_low_info_reply_limit_to_two(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_style_bible_clamp_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            style_bible = {
                "character_voice_profiles": [
                    {
                        "character_id": "carmen",
                        "public_register": "direct",
                        "private_register": "guarded",
                        "syntax_signature": "plainspoken",
                        "lexical_signature": "plain",
                        "forbidden_generic_lines": "none",
                        "stress_tells": "tightens up",
                        "profanity_profile": "moderate",
                        "contraction_level": "moderate",
                        "interruption_habit": "rare",
                        "self_correction_tendency": "light",
                        "indirectness": "mixed",
                        "repetition_tolerance": "some",
                        "evasion_style": "narrows",
                        "sentence_completion_style": "finishes",
                    }
                ],
                "dialogue_rules": {
                    "anti_transcript_cadence": True,
                    "required_leverage_shifts_per_scene": 1,
                    "max_consecutive_low_info_replies": 0,
                    "idiolect_separation_required": True,
                    "default_contraction_use": "high",
                },
                "prose_style_profile": {
                    "narrative_tense": "past tense",
                    "narrative_distance": "close",
                    "rhythm_target": "mixed",
                    "sensory_bias": ["touch"],
                    "diction": "concrete",
                    "forbidden_drift_patterns": ["generic cinematic phrasing"],
                    "chapter_texture_variance": "vary chapter rhythm",
                },
                "aesthetic_risk_policy": {
                    "sanitization_disallowed": True,
                    "dark_content_allowed_when_character_true": True,
                    "profanity_allowed_when_scene_pressure_warrants": True,
                    "euphemism_penalty": "high",
                    "creative_risk_policy": "push toward specificity",
                },
            }

            repaired, _repairs = runner._repair_style_bible_data(style_bible)
            self.assertEqual(
                repaired["dialogue_rules"]["max_consecutive_low_info_replies"], 2
            )
            runner._validate_style_bible_data(repaired, "outline/style_bible.json")

    def test_revision_stage_retries_invalid_or_missing_pass_report_once(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_revision_retry_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1000,
                    chapter_engine="discovery",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
            ]

            run_dir = runner.cfg.run_dir
            (run_dir / "chapters").mkdir(parents=True, exist_ok=True)
            (run_dir / "outline").mkdir(parents=True, exist_ok=True)
            (run_dir / "packets" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (run_dir / "config" / "prompts").mkdir(parents=True, exist_ok=True)
            (run_dir / "chapters" / "chapter_01.md").write_text(
                "# Chapter 1\n\nBody.\n",
                encoding="utf-8",
            )
            (run_dir / "outline" / "continuity_sheet.json").write_text(
                json.dumps(
                    {
                        "characters": [],
                        "timeline": {
                            "story_start": "spring",
                            "estimated_span": "one month",
                            "seasonal_track": [],
                            "key_events": [],
                        },
                        "geography": {
                            "primary_setting": "facility",
                            "key_locations": [],
                            "distances": [],
                        },
                        "world_rules": [],
                        "power_structure": [],
                        "objects": [],
                        "financial_state": {"debts": [], "income_sources": []},
                        "knowledge_state": [],
                        "environmental_constants": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (run_dir / "config" / "prompts" / "chapter_revision_prompt.md").write_text(
                (REPO_ROOT / "prompts" / "chapter_revision_prompt.md").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )

            finding = {
                "finding_id": "f1",
                "source": "craft",
                "severity": "HIGH",
                "chapter_id": "chapter_01",
                "evidence": "chapters/chapter_01.md:1",
                "problem": "Test problem",
                "rewrite_direction": "Revise chapters/chapter_01.md:1-3.",
                "acceptance_test": "chapters/chapter_01.md:1-3 reads differently.",
            }
            main_packet = {
                "chapter_id": "chapter_01",
                "findings": [finding],
            }
            (run_dir / runner._revision_packet_rel(1, "chapter_01")).write_text(
                json.dumps(main_packet) + "\n",
                encoding="utf-8",
            )
            for pass_def in runner_module.REVISION_PASS_DEFS:
                pass_packet = {
                    "chapter_id": "chapter_01",
                    "findings": [finding]
                    if pass_def["key"] == runner_module.REVISION_PASS_DEFS[0]["key"]
                    else [],
                    "revision_pass": {
                        "key": pass_def["key"],
                        "label": pass_def["label"],
                        "focus": pass_def["focus"],
                    },
                }
                (run_dir / runner._revision_pass_packet_rel(1, "chapter_01", pass_def["key"])).write_text(
                    json.dumps(pass_packet) + "\n",
                    encoding="utf-8",
                )

            runner._run_jobs_parallel = lambda *_args, **_kwargs: None
            retry_job_ids: list[str] = []

            def fake_run_job(job: runner_module.JobSpec) -> None:
                retry_job_ids.append(job.job_id)
                report_path = run_dir / job.required_outputs[1]
                report_path.parent.mkdir(parents=True, exist_ok=True)
                report_path.write_text(
                    json.dumps(
                        {
                            "chapter_id": job.chapter_id,
                            "finding_results": [
                                {
                                    "finding_id": "f1",
                                    "status_after_revision": "FIXED",
                                    "evidence": "chapters/chapter_01.md:1",
                                    "notes": "Retried successfully.",
                                }
                            ],
                            "summary": "Retry produced a valid report.",
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )

            runner._run_job = fake_run_job

            runner._run_revision_stage(1, ["chapter_01"])

            self.assertEqual(len(retry_job_ids), 1)
            self.assertIn("_retry_1", retry_job_ids[0])
            merged_report = json.loads(
                (
                    run_dir
                    / runner._revision_report_rel(1, "chapter_01")
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(
                merged_report["finding_results"][0]["status_after_revision"], "FIXED"
            )

    def test_load_repaired_revision_report_promotes_nested_summary_and_preserves_original(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_revision_report_repair_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            run_dir = runner.cfg.run_dir
            (run_dir / "revisions" / "cycle_01").mkdir(parents=True, exist_ok=True)

            report_rel = "revisions/cycle_01/chapter_01.p1_structural_craft.revision_report.json"
            report_path = run_dir / report_rel
            report_path.write_text(
                json.dumps(
                    {
                        "chapter_id": "chapter_01",
                        "finding_results": [
                            {
                                "finding_id": "f1",
                                "status_after_revision": "FIXED",
                                "evidence": "chapters/chapter_01.md:1",
                                "notes": "done",
                                "summary": "Nested summary that should be promoted.",
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            repaired = runner._load_repaired_revision_report(
                report_rel,
                "chapter_01",
                {"f1"},
                chapter_file="chapters/chapter_01.md",
            )

            self.assertEqual(
                repaired["summary"], "Nested summary that should be promoted."
            )
            preserved = (
                run_dir
                / "revisions"
                / "cycle_01"
                / "chapter_01.p1_structural_craft.revision_report.invalid.original.json"
            )
            self.assertTrue(preserved.is_file())
            preserved_payload = json.loads(preserved.read_text(encoding="utf-8"))
            self.assertNotIn("summary", preserved_payload)

    def test_validate_revision_report_requires_revision_note_for_nonfixed_results(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_revision_report_note_validate_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            with self.assertRaisesRegex(
                runner_module.PipelineError,
                "missing revision_note for UNRESOLVED",
            ):
                runner._validate_revision_report_json(
                    {
                        "chapter_id": "chapter_01",
                        "finding_results": [
                            {
                                "finding_id": "f1",
                                "status_after_revision": "UNRESOLVED",
                                "evidence": "chapters/chapter_01.md:12-16",
                                "notes": "Still blocked by downstream continuity.",
                            }
                        ],
                        "summary": "Still blocked.",
                    },
                    "chapter_01",
                    "revisions/cycle_01/chapter_01.p1_structural_craft.revision_report.json",
                    {"f1"},
                    chapter_file="chapters/chapter_01.md",
                )

    def test_load_repaired_revision_report_synthesizes_revision_note_from_notes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_revision_report_note_repair_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            run_dir = runner.cfg.run_dir
            (run_dir / "revisions" / "cycle_01").mkdir(parents=True, exist_ok=True)

            report_rel = "revisions/cycle_01/chapter_01.p1_structural_craft.revision_report.json"
            report_path = run_dir / report_rel
            report_path.write_text(
                json.dumps(
                    {
                        "chapter_id": "chapter_01",
                        "finding_results": [
                            {
                                "finding_id": "f1",
                                "status_after_revision": "UNRESOLVED",
                                "evidence": "chapters/chapter_01.md:12-16",
                                "notes": "Trimmed the passage, but the dossier name still has to stay visible.",
                            }
                        ],
                        "summary": "Still partially blocked.",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            repaired = runner._load_repaired_revision_report(
                report_rel,
                "chapter_01",
                {"f1"},
                chapter_file="chapters/chapter_01.md",
            )

            self.assertEqual(
                repaired["finding_results"][0]["revision_note"],
                "Trimmed the passage, but the dossier name still has to stay visible.",
            )
            preserved = (
                run_dir
                / "revisions"
                / "cycle_01"
                / "chapter_01.p1_structural_craft.revision_report.invalid.original.json"
            )
            self.assertTrue(preserved.is_file())

    def test_run_revision_stage_skips_existing_report_after_nested_summary_repair(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(
            prefix="snp_revision_resume_repair_", dir="/tmp"
        ) as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1000,
                    chapter_engine="discovery",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
            ]

            run_dir = runner.cfg.run_dir
            (run_dir / "chapters").mkdir(parents=True, exist_ok=True)
            (run_dir / "outline").mkdir(parents=True, exist_ok=True)
            (run_dir / "config" / "prompts").mkdir(parents=True, exist_ok=True)
            (run_dir / "packets" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (run_dir / "revisions" / "cycle_01").mkdir(parents=True, exist_ok=True)

            (run_dir / "chapters" / "chapter_01.md").write_text(
                "# Chapter 1\n\nBody text.\n", encoding="utf-8"
            )
            (run_dir / "outline" / "continuity_sheet.json").write_text(
                json.dumps(
                    {
                        "chapters": {},
                        "characters": {},
                        "objects": {},
                        "timeline": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (run_dir / "config" / "prompts" / "chapter_revision_prompt.md").write_text(
                (REPO_ROOT / "prompts" / "chapter_revision_prompt.md").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )

            finding = {
                "finding_id": "f1",
                "source": "craft",
                "severity": "HIGH",
                "chapter_id": "chapter_01",
                "evidence": "chapters/chapter_01.md:1",
                "problem": "Test problem",
                "rewrite_direction": "Revise chapters/chapter_01.md:1-3.",
                "acceptance_test": "chapters/chapter_01.md:1-3 reads differently.",
            }

            (run_dir / runner._revision_packet_rel(1, "chapter_01")).write_text(
                json.dumps({"chapter_id": "chapter_01", "findings": [finding]}) + "\n",
                encoding="utf-8",
            )

            for pass_def in runner_module.REVISION_PASS_DEFS:
                pass_packet = {
                    "chapter_id": "chapter_01",
                    "findings": [finding]
                    if pass_def["key"] == runner_module.REVISION_PASS_DEFS[0]["key"]
                    else [],
                    "revision_pass": {
                        "key": pass_def["key"],
                        "label": pass_def["label"],
                        "focus": pass_def["focus"],
                    },
                }
                (
                    run_dir
                    / runner._revision_pass_packet_rel(
                        1, "chapter_01", pass_def["key"]
                    )
                ).write_text(json.dumps(pass_packet) + "\n", encoding="utf-8")

            p1_report_rel = runner._revision_pass_report_rel(
                1, "chapter_01", runner_module.REVISION_PASS_DEFS[0]["key"]
            )
            (run_dir / p1_report_rel).write_text(
                json.dumps(
                    {
                        "chapter_id": "chapter_01",
                        "finding_results": [
                            {
                                "finding_id": "f1",
                                "status_after_revision": "FIXED",
                                "evidence": "chapters/chapter_01.md:1",
                                "notes": "Already done.",
                                "summary": "Nested summary that should allow resume skip.",
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            run_jobs_calls: list[tuple] = []

            def fail_if_called(*args, **kwargs):
                run_jobs_calls.append((args, kwargs))
                raise AssertionError("revision jobs should not be rerun for repaired p1 report")

            runner._run_jobs_parallel = fail_if_called

            runner._run_revision_stage(1, ["chapter_01"])

            self.assertEqual(run_jobs_calls, [])
            repaired_p1 = json.loads((run_dir / p1_report_rel).read_text(encoding="utf-8"))
            self.assertEqual(
                repaired_p1["summary"], "Nested summary that should allow resume skip."
            )
            preserved = run_dir / runner._preserved_invalid_artifact_rel(p1_report_rel)
            self.assertTrue(preserved.is_file())

    def test_run_revision_stage_reports_reused_units(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_revision_units_reused_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner._prepare_run_dir()
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1,
                    chapter_engine="engine",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
            ]

            run_dir = runner.cfg.run_dir
            (run_dir / "outline" / "continuity_sheet.json").write_text(
                json.dumps({"timeline": []}) + "\n",
                encoding="utf-8",
            )
            runner._ensure_cycle_continuity_snapshot(1)
            (run_dir / "chapters" / "chapter_01.md").write_text(
                "# Chapter 1\n\nStable chapter text.\n",
                encoding="utf-8",
            )

            for pass_def in runner_module.REVISION_PASS_DEFS:
                packet_path = run_dir / runner._revision_pass_packet_rel(
                    1, "chapter_01", pass_def["key"]
                )
                packet_path.parent.mkdir(parents=True, exist_ok=True)
                packet_path.write_text(
                    json.dumps(
                        {
                            "chapter_id": "chapter_01",
                            "findings": [],
                            "revision_pass": {
                                "key": pass_def["key"],
                                "label": pass_def["label"],
                                "focus": pass_def["focus"],
                            },
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
                report_path = run_dir / runner._revision_pass_report_rel(
                    1, "chapter_01", pass_def["key"]
                )
                report_path.parent.mkdir(parents=True, exist_ok=True)
                report_path.write_text(
                    json.dumps(
                        {
                            "chapter_id": "chapter_01",
                            "finding_results": [],
                            "summary": f"{pass_def['label']} already complete.",
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )

            (run_dir / runner._revision_packet_rel(1, "chapter_01")).write_text(
                json.dumps({"chapter_id": "chapter_01", "findings": []}) + "\n",
                encoding="utf-8",
            )

            with mock.patch.object(runner, "_run_jobs_parallel") as jobs_mock:
                summary = runner._run_revision_stage(1, ["chapter_01"])

            jobs_mock.assert_not_called()
            self.assertEqual(summary["status"], "reused")
            self.assertEqual(len(summary["units"]), len(runner_module.REVISION_PASS_DEFS))
            self.assertTrue(
                all(unit["status"] == "reused" for unit in summary["units"].values())
            )

    def test_run_revision_stage_reruns_early_pass_when_live_chapter_was_reset(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="snp_revision_resume_reset_", dir="/tmp"
        ) as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1000,
                    chapter_engine="discovery",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
            ]

            run_dir = runner.cfg.run_dir
            (run_dir / "chapters").mkdir(parents=True, exist_ok=True)
            (run_dir / "outline").mkdir(parents=True, exist_ok=True)
            (run_dir / "config" / "prompts").mkdir(parents=True, exist_ok=True)
            (run_dir / "packets" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (run_dir / "revisions" / "cycle_01").mkdir(parents=True, exist_ok=True)

            chapter_path = run_dir / "chapters" / "chapter_01.md"
            chapter_path.write_text("# Chapter 1\n\nBaseline text.\n", encoding="utf-8")
            (run_dir / "outline" / "continuity_sheet.json").write_text(
                json.dumps(
                    {
                        "chapters": {},
                        "characters": {},
                        "objects": {},
                        "timeline": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (run_dir / "config" / "prompts" / "chapter_revision_prompt.md").write_text(
                (REPO_ROOT / "prompts" / "chapter_revision_prompt.md").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )

            finding = {
                "finding_id": "f1",
                "source": "craft",
                "severity": "HIGH",
                "chapter_id": "chapter_01",
                "evidence": "chapters/chapter_01.md:1",
                "problem": "Test problem",
                "rewrite_direction": "Revise chapters/chapter_01.md:1-3.",
                "acceptance_test": "chapters/chapter_01.md:1-3 reads differently.",
            }
            (run_dir / runner._revision_packet_rel(1, "chapter_01")).write_text(
                json.dumps({"chapter_id": "chapter_01", "findings": [finding]}) + "\n",
                encoding="utf-8",
            )

            for pass_def in runner_module.REVISION_PASS_DEFS:
                pass_packet = {
                    "chapter_id": "chapter_01",
                    "findings": [finding]
                    if pass_def["key"] == runner_module.REVISION_PASS_DEFS[0]["key"]
                    else [],
                    "revision_pass": {
                        "key": pass_def["key"],
                        "label": pass_def["label"],
                        "focus": pass_def["focus"],
                    },
                }
                (
                    run_dir
                    / runner._revision_pass_packet_rel(
                        1, "chapter_01", pass_def["key"]
                    )
                ).write_text(json.dumps(pass_packet) + "\n", encoding="utf-8")

            p1_report_rel = runner._revision_pass_report_rel(
                1, "chapter_01", runner_module.REVISION_PASS_DEFS[0]["key"]
            )
            (run_dir / p1_report_rel).write_text(
                json.dumps(
                    {
                        "chapter_id": "chapter_01",
                        "finding_results": [
                            {
                                "finding_id": "f1",
                                "status_after_revision": "FIXED",
                                "evidence": "chapters/chapter_01.md:1",
                                "notes": "Already done.",
                            }
                        ],
                        "summary": "Finished earlier pass.",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            # Simulate a reset/copy-back after the report was written.
            chapter_path.write_text("# Chapter 1\n\nReset text.\n", encoding="utf-8")
            os.utime(chapter_path, None)

            captured_job_groups: list[tuple[str, list[runner_module.JobSpec]]] = []

            def capture_run_jobs_parallel(
                jobs: list[runner_module.JobSpec], _max_parallel: int, label: str
            ) -> None:
                captured_job_groups.append((label, list(jobs)))
                for job in jobs:
                    for output_rel in job.required_outputs:
                        if output_rel.endswith(".revision_report.json"):
                            output_path = run_dir / output_rel
                            output_path.parent.mkdir(parents=True, exist_ok=True)
                            output_path.write_text(
                                json.dumps(
                                    {
                                        "chapter_id": job.chapter_id,
                                        "finding_results": [
                                            {
                                                "finding_id": "f1",
                                                "status_after_revision": "FIXED",
                                                "evidence": "chapters/chapter_01.md:1",
                                                "notes": "Reran after reset.",
                                            }
                                        ],
                                        "summary": "Reran after reset.",
                                    }
                                )
                                + "\n",
                                encoding="utf-8",
                            )

            runner._run_jobs_parallel = capture_run_jobs_parallel
            runner._run_revision_stage(1, ["chapter_01"])

            self.assertTrue(captured_job_groups)
            self.assertEqual(
                captured_job_groups[0][1][0].job_id,
                "cycle_01_revise_p1_structural_craft_chapter_01",
            )

    def test_run_revision_stage_reruns_early_pass_when_later_reports_predate_reset(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(
            prefix="snp_revision_resume_reset_later_reports_", dir="/tmp"
        ) as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1000,
                    chapter_engine="discovery",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
            ]

            run_dir = runner.cfg.run_dir
            (run_dir / "chapters").mkdir(parents=True, exist_ok=True)
            (run_dir / "outline").mkdir(parents=True, exist_ok=True)
            (run_dir / "config" / "prompts").mkdir(parents=True, exist_ok=True)
            (run_dir / "packets" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (run_dir / "revisions" / "cycle_01").mkdir(parents=True, exist_ok=True)

            chapter_path = run_dir / "chapters" / "chapter_01.md"
            chapter_path.write_text("# Chapter 1\n\nBaseline text.\n", encoding="utf-8")
            (run_dir / "outline" / "continuity_sheet.json").write_text(
                json.dumps(
                    {
                        "chapters": {},
                        "characters": {},
                        "objects": {},
                        "timeline": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (run_dir / "config" / "prompts" / "chapter_revision_prompt.md").write_text(
                (REPO_ROOT / "prompts" / "chapter_revision_prompt.md").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )

            finding = {
                "finding_id": "f1",
                "source": "craft",
                "severity": "HIGH",
                "chapter_id": "chapter_01",
                "evidence": "chapters/chapter_01.md:1",
                "problem": "Test problem",
                "rewrite_direction": "Revise chapters/chapter_01.md:1-3.",
                "acceptance_test": "chapters/chapter_01.md:1-3 reads differently.",
            }
            (run_dir / runner._revision_packet_rel(1, "chapter_01")).write_text(
                json.dumps({"chapter_id": "chapter_01", "findings": [finding]}) + "\n",
                encoding="utf-8",
            )

            pass_packet_map = {
                runner_module.REVISION_PASS_DEFS[0]["key"]: [finding],
                runner_module.REVISION_PASS_DEFS[1]["key"]: [],
                runner_module.REVISION_PASS_DEFS[2]["key"]: [],
            }
            report_mtime = 1_700_000_000
            chapter_mtime = report_mtime + 10

            for pass_def in runner_module.REVISION_PASS_DEFS:
                pass_key = pass_def["key"]
                pass_packet = {
                    "chapter_id": "chapter_01",
                    "findings": pass_packet_map[pass_key],
                    "revision_pass": {
                        "key": pass_key,
                        "label": pass_def["label"],
                        "focus": pass_def["focus"],
                    },
                }
                packet_path = run_dir / runner._revision_pass_packet_rel(
                    1, "chapter_01", pass_key
                )
                packet_path.write_text(json.dumps(pass_packet) + "\n", encoding="utf-8")
                os.utime(packet_path, (report_mtime, report_mtime))

                finding_results = (
                    [
                        {
                            "finding_id": "f1",
                            "status_after_revision": "FIXED",
                            "evidence": "chapters/chapter_01.md:1",
                            "notes": "Already done.",
                        }
                    ]
                    if pass_key == runner_module.REVISION_PASS_DEFS[0]["key"]
                    else []
                )
                report_path = run_dir / runner._revision_pass_report_rel(
                    1, "chapter_01", pass_key
                )
                report_path.write_text(
                    json.dumps(
                        {
                            "chapter_id": "chapter_01",
                            "finding_results": finding_results,
                            "summary": "Existing pass report.",
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
                os.utime(report_path, (report_mtime, report_mtime))

            chapter_path.write_text("# Chapter 1\n\nReset text.\n", encoding="utf-8")
            os.utime(chapter_path, (chapter_mtime, chapter_mtime))

            captured_job_groups: list[tuple[str, list[runner_module.JobSpec]]] = []

            def capture_run_jobs_parallel(
                jobs: list[runner_module.JobSpec], _max_parallel: int, label: str
            ) -> None:
                captured_job_groups.append((label, list(jobs)))
                for job in jobs:
                    for output_rel in job.required_outputs:
                        if output_rel.endswith(".revision_report.json"):
                            output_path = run_dir / output_rel
                            output_path.parent.mkdir(parents=True, exist_ok=True)
                            output_path.write_text(
                                json.dumps(
                                    {
                                        "chapter_id": job.chapter_id,
                                        "finding_results": [
                                            {
                                                "finding_id": "f1",
                                                "status_after_revision": "FIXED",
                                                "evidence": "chapters/chapter_01.md:1",
                                                "notes": "Reran after reset.",
                                            }
                                        ],
                                        "summary": "Reran after reset.",
                                    }
                                )
                                + "\n",
                                encoding="utf-8",
                            )

            runner._run_jobs_parallel = capture_run_jobs_parallel
            runner._run_revision_stage(1, ["chapter_01"])

            self.assertTrue(captured_job_groups)
            self.assertEqual(
                captured_job_groups[0][1][0].job_id,
                "cycle_01_revise_p1_structural_craft_chapter_01",
            )

    def test_load_repaired_chapter_review_normalizes_shape_and_synthesizes_summary(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_review_repair_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            run_dir = runner.cfg.run_dir
            (run_dir / "reviews" / "cycle_01").mkdir(parents=True, exist_ok=True)
            review_rel = "reviews/cycle_01/chapter_01.review.json"
            (run_dir / review_rel).write_text(
                json.dumps(
                    {
                        "chapter_id": "ch1",
                        "verdicts": {
                            "award": "fail",
                            "craft": "pass",
                            "dialogue": "PASS",
                            "prose": "pass",
                        },
                        "findings": [
                            {
                                "finding_id": "f1",
                                "source": "CRAFT",
                                "severity": "medium",
                                "chapter_id": "ch1",
                                "evidence": ["snapshots/cycle_01/chapters/chapter_01.md:12"],
                                "description": "The scene repeats itself.",
                                "rewrite_direction": "Trim the repeated beat.",
                                "acceptance_test": "The repeated beat no longer appears twice.",
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            repaired = runner._load_repaired_chapter_review(
                review_rel,
                "chapter_01",
                "snapshots/cycle_01/chapters/chapter_01.md",
            )

            self.assertEqual(repaired["chapter_id"], "chapter_01")
            self.assertEqual(repaired["verdicts"]["award"], "FAIL")
            self.assertEqual(repaired["findings"][0]["source"], "craft")
            self.assertEqual(repaired["findings"][0]["severity"], "MEDIUM")
            self.assertEqual(repaired["findings"][0]["chapter_id"], "chapter_01")
            self.assertEqual(
                repaired["findings"][0]["problem"],
                "The scene repeats itself.",
            )
            self.assertTrue(repaired["summary"].strip())
            self.assertTrue(
                (
                    run_dir / "reviews" / "cycle_01" / "chapter_01.review.invalid.original.json"
                ).is_file()
            )

    def test_normalize_finding_accepts_low_for_award_global_only(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_low_finding_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1,
                    chapter_engine="engine",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
            ]

            raw = {
                "finding_id": "LOW_NOTE",
                "severity": "LOW",
                "chapter_id": "chapter_01",
                "evidence": "snapshots/cycle_01/FINAL_NOVEL.md:4",
                "problem": "A soft award-level note.",
                "rewrite_direction": "Revise snapshots/cycle_01/FINAL_NOVEL.md:4-6 for polish.",
                "acceptance_test": "Pass if snapshots/cycle_01/FINAL_NOVEL.md:4-6 reads more cleanly.",
            }

            finding = runner._normalize_finding(
                raw,
                1,
                force_source="award_global",
            )
            self.assertEqual(finding["severity"], "LOW")
            self.assertEqual(finding["source"], "award_global")

            with self.assertRaises(runner_module.PipelineError):
                runner._normalize_finding(raw, 1, force_source="prose")

    def test_load_repaired_full_award_review_normalizes_elevation_findings(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_elevation_repair_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1,
                    chapter_engine="engine",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
            ]

            run_dir = runner.cfg.run_dir
            (run_dir / "reviews" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (run_dir / "snapshots" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (run_dir / "snapshots" / "cycle_01" / "FINAL_NOVEL.md").write_text(
                "# Title\n\n# Chapter 1\n\nalpha\nbeta\ngamma\n",
                encoding="utf-8",
            )
            rel = "reviews/cycle_01/full_award.review.json"
            (run_dir / rel).write_text(
                json.dumps(
                    {
                        "cycle": 1,
                        "verdict": "FAIL",
                        "summary": "One elevation opportunity.",
                        "findings": [
                            {
                                "finding_id": "E5_STATUS_FLIP",
                                "source": "Elevation",
                                "severity": "ELEVATION_HIGH",
                                "chapter_id": "chapter_01",
                                "pass_hint": "p2_dialogue_idiolect_cadence",
                                "evidence": "snapshots/cycle_01/FINAL_NOVEL.md:5",
                                "problem": "The scene never cashes in on a possible status reversal.",
                                "rewrite_direction": "Revise snapshots/cycle_01/FINAL_NOVEL.md:5-6 so the power dynamic visibly flips mid-exchange.",
                                "acceptance_test": "The cited exchange now contains a clear status reversal rather than a flat continuation.",
                            }
                        ],
                        "pattern_findings": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            repaired = runner._load_repaired_full_award_review(
                rel,
                1,
                {"chapter_01"},
                "snapshots/cycle_01/FINAL_NOVEL.md",
            )

            self.assertEqual(repaired["findings"][0]["source"], "elevation")
            self.assertEqual(repaired["findings"][0]["severity"], "HIGH")

    def test_normalize_finding_routes_elevation_by_pass_hint(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_elevation_route_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1,
                    chapter_engine="engine",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
            ]

            finding = runner._normalize_finding(
                {
                    "finding_id": "E3_DIALOGUE_PRESSURE",
                    "source": "elevation",
                    "severity": "ELEVATION_MEDIUM",
                    "chapter_id": "chapter_01",
                    "pass_hint": "p2_dialogue_idiolect_cadence",
                    "evidence": "snapshots/cycle_01/FINAL_NOVEL.md:4",
                    "problem": "The exchange lacks competing desires in speech.",
                    "rewrite_direction": "Revise snapshots/cycle_01/FINAL_NOVEL.md:4-6 so both speakers pursue different aims in the same conversation.",
                    "acceptance_test": "The cited exchange now contains conflicting immediate agendas rather than cooperative exposition.",
                },
                1,
            )

            self.assertEqual(finding["source"], "elevation")
            self.assertEqual(finding["severity"], "MEDIUM")
            self.assertEqual(finding["pass_hint"], "p2_dialogue_idiolect_cadence")
            self.assertEqual(
                runner._assign_revision_pass_key(finding),
                "p2_dialogue_idiolect_cadence",
            )

    def test_revision_packet_enriches_full_book_citations_with_locator_excerpts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_locator_excerpt_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            run_dir = runner.cfg.run_dir
            (run_dir / "snapshots" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (run_dir / "snapshots" / "cycle_01" / "FINAL_NOVEL.md").write_text(
                "# Title\n\n# Chapter 1\n\nalpha\nbeta\ngamma\ndelta\nepsilon\n",
                encoding="utf-8",
            )

            finding = {
                "finding_id": "award_001",
                "source": "award_global",
                "severity": "MEDIUM",
                "chapter_id": "chapter_01",
                "evidence": "snapshots/cycle_01/FINAL_NOVEL.md:5",
                "problem": "The confrontation is too polished.",
                "rewrite_direction": (
                    "Roughen `snapshots/cycle_01/FINAL_NOVEL.md:5`-"
                    "`snapshots/cycle_01/FINAL_NOVEL.md:7`."
                ),
                "acceptance_test": (
                    "Pass if the revised scene no longer hinges on "
                    "`snapshots/cycle_01/FINAL_NOVEL.md:6`."
                ),
            }

            packet = runner._make_revision_packet_payload(
                cycle=1,
                chapter_id="chapter_01",
                input_snapshot_hash="a" * 64,
                findings=[finding],
                non_negotiables=[],
                dialogue_rules={},
                prose_style_profile={},
                aesthetic_risk_policy={},
            )

            self.assertTrue(packet["has_locator_excerpts"])
            self.assertEqual(
                packet["original_snapshot_file"],
                "snapshots/cycle_01/chapters/chapter_01.md",
            )
            packet_finding = packet["findings"][0]
            locator_excerpts = packet_finding["locator_excerpts"]
            self.assertIn("evidence", locator_excerpts)
            self.assertIn("rewrite_direction", locator_excerpts)
            self.assertIn("acceptance_test", locator_excerpts)
            self.assertEqual(
                locator_excerpts["rewrite_direction"][0]["citation"],
                "snapshots/cycle_01/FINAL_NOVEL.md:5-7",
            )
            self.assertIn(
                "5: alpha",
                locator_excerpts["evidence"][0]["excerpt"],
            )

    def test_revision_packet_skips_locator_helpers_for_chapter_local_citations(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_locator_skip_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            finding = {
                "finding_id": "craft_001",
                "source": "craft",
                "severity": "MEDIUM",
                "chapter_id": "chapter_01",
                "evidence": "snapshots/cycle_01/chapters/chapter_01.md:12",
                "problem": "The scene repeats itself.",
                "rewrite_direction": "Trim the middle exchange.",
                "acceptance_test": "Pass if the argument does not restate itself.",
            }

            packet = runner._make_revision_packet_payload(
                cycle=1,
                chapter_id="chapter_01",
                input_snapshot_hash="b" * 64,
                findings=[finding],
                non_negotiables=[],
                dialogue_rules={},
                prose_style_profile={},
                aesthetic_risk_policy={},
            )

            self.assertNotIn("has_locator_excerpts", packet)
            self.assertNotIn("original_snapshot_file", packet)
            self.assertNotIn("locator_excerpts", packet["findings"][0])

    def test_build_compact_aggregator_input_uses_pass_packets_and_locator_excerpts(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_compact_aggregator_input_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1000,
                    chapter_engine="discovery",
                    pressure_source="inspection pressure",
                    state_shift="A choice is made.",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
            ]
            runner.style_bible = {
                "character_voice_profiles": [{"character_id": "joel"}],
                "prose_style_profile": {"temperature": "high"},
                "aesthetic_risk_policy": {"sanitize": "never"},
            }

            run_dir = runner.cfg.run_dir
            (run_dir / "outline").mkdir(parents=True, exist_ok=True)
            (run_dir / "outline" / "continuity_sheet.json").write_text(
                json.dumps({"characters": [], "geography": {}}) + "\n",
                encoding="utf-8",
            )
            (run_dir / "snapshots" / "cycle_01" / "chapters").mkdir(parents=True, exist_ok=True)
            (run_dir / "snapshots" / "cycle_01" / "chapters" / "chapter_01.md").write_text(
                "# Chapter 1\n\nCurrent chapter text.\n",
                encoding="utf-8",
            )
            (run_dir / "snapshots" / "cycle_01" / "FINAL_NOVEL.md").write_text(
                "# Title\n\n# Chapter 1\n\nalpha\nbeta\ngamma\ndelta\nepsilon\n",
                encoding="utf-8",
            )

            finding = runner._normalize_finding(
                {
                    "finding_id": "award_001",
                    "source": "award_global",
                    "severity": "HIGH",
                    "chapter_id": "chapter_01",
                    "evidence": "snapshots/cycle_01/FINAL_NOVEL.md:5",
                    "problem": "The beat is too polished.",
                    "rewrite_direction": (
                        "Revise `snapshots/cycle_01/FINAL_NOVEL.md:5`-"
                        "`snapshots/cycle_01/FINAL_NOVEL.md:7`."
                    ),
                    "acceptance_test": (
                        "Pass if `snapshots/cycle_01/FINAL_NOVEL.md:6` now feels jagged."
                    ),
                },
                1,
            )

            runner._build_revision_packets(1, {"chapter_01": [finding]})
            compact_input = runner._build_compact_aggregator_input(1, ["chapter_01"])

            self.assertEqual(compact_input["shared_context"]["chapter_count"], 1)
            chapter_rows = compact_input["chapters"]["chapter_01"]["p1_structural_craft"]
            self.assertEqual(chapter_rows[0]["finding_id"], "award_001")
            self.assertIn("locator_excerpt", chapter_rows[0])
            self.assertIn("5: alpha", chapter_rows[0]["locator_excerpt"])

    def test_build_compact_aggregator_input_maps_stage_source_and_elevation_severity(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_compact_aggregator_stage_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1000,
                    chapter_engine="discovery",
                    pressure_source="inspection pressure",
                    state_shift="A choice is made.",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
            ]
            runner.style_bible = {
                "character_voice_profiles": [{"character_id": "joel"}],
                "prose_style_profile": {"temperature": "high"},
                "aesthetic_risk_policy": {"sanitize": "never"},
            }

            run_dir = runner.cfg.run_dir
            (run_dir / "outline").mkdir(parents=True, exist_ok=True)
            (run_dir / "outline" / "continuity_sheet.json").write_text(
                json.dumps({"characters": [], "geography": {}}) + "\n",
                encoding="utf-8",
            )
            (run_dir / "snapshots" / "cycle_01" / "chapters").mkdir(parents=True, exist_ok=True)
            (run_dir / "snapshots" / "cycle_01" / "chapters" / "chapter_01.md").write_text(
                "# Chapter 1\n\nCurrent chapter text.\n",
                encoding="utf-8",
            )
            (run_dir / "snapshots" / "cycle_01" / "FINAL_NOVEL.md").write_text(
                "# Title\n\n# Chapter 1\n\nalpha\nbeta\ngamma\ndelta\nepsilon\n",
                encoding="utf-8",
            )

            craft_finding = runner._normalize_finding(
                {
                    "finding_id": "craft_001",
                    "source": "craft",
                    "severity": "HIGH",
                    "chapter_id": "chapter_01",
                    "evidence": "snapshots/cycle_01/FINAL_NOVEL.md:5",
                    "problem": "The beat is too polished.",
                    "rewrite_direction": "Roughen the turn.",
                    "acceptance_test": "The turn lands with more jagged pressure.",
                },
                1,
            )
            elevation_finding = runner._normalize_finding(
                {
                    "finding_id": "elev_001",
                    "source": "elevation",
                    "severity": "ELEVATION_MEDIUM",
                    "chapter_id": "chapter_01",
                    "evidence": "snapshots/cycle_01/FINAL_NOVEL.md:6",
                    "problem": "The scene could take a bigger imaginative swing.",
                    "rewrite_direction": "Sharpen the image.",
                    "acceptance_test": "The image becomes more singular and memorable.",
                },
                1,
            )

            runner._build_revision_packets(
                1,
                {"chapter_01": [craft_finding, elevation_finding]},
            )
            compact_input = runner._build_compact_aggregator_input(1, ["chapter_01"])

            chapter_rows = compact_input["chapters"]["chapter_01"]["p1_structural_craft"]
            rows_by_id = {row["finding_id"]: row for row in chapter_rows}
            self.assertEqual(rows_by_id["craft_001"]["source"], "chapter_review")
            self.assertEqual(rows_by_id["craft_001"]["review_lens"], "craft")
            self.assertEqual(rows_by_id["elev_001"]["source"], "elevation")
            self.assertEqual(rows_by_id["elev_001"]["severity"], "ELEVATION_MEDIUM")

    def test_build_compact_aggregator_input_includes_prior_attempt_context(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_compact_aggregator_prior_attempt_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1000,
                    chapter_engine="discovery",
                    pressure_source="inspection pressure",
                    state_shift="A choice is made.",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
            ]
            runner.style_bible = {
                "character_voice_profiles": [{"character_id": "joel"}],
                "prose_style_profile": {"temperature": "high"},
                "aesthetic_risk_policy": {"sanitize": "never"},
            }

            run_dir = runner.cfg.run_dir
            (run_dir / "outline").mkdir(parents=True, exist_ok=True)
            (run_dir / "outline" / "continuity_sheet.json").write_text(
                json.dumps({"characters": [], "geography": {}}) + "\n",
                encoding="utf-8",
            )
            for cycle in (1, 2):
                (run_dir / "snapshots" / f"cycle_{cycle:02d}" / "chapters").mkdir(
                    parents=True, exist_ok=True
                )
                (run_dir / "snapshots" / f"cycle_{cycle:02d}" / "chapters" / "chapter_01.md").write_text(
                    "# Chapter 1\n\none\ntwo\nthree\nfour\nfive\nsix\nseven\neight\nnine\nten\n"
                    "eleven\ntwelve\nthirteen\nfourteen\nfifteen\nsixteen\nseventeen\neighteen\n"
                    "nineteen\ntwenty\n",
                    encoding="utf-8",
                )
            (run_dir / "snapshots" / "cycle_02" / "FINAL_NOVEL.md").write_text(
                "# Title\n\n# Chapter 1\n\n"
                + "\n".join(f"line {idx}" for idx in range(1, 35))
                + "\n",
                encoding="utf-8",
            )
            (run_dir / "context" / "cycle_02").mkdir(parents=True, exist_ok=True)
            (run_dir / "context" / "cycle_02" / "chapter_line_index.json").write_text(
                json.dumps({"chapter_01": {"start_line": 3, "end_line": 37}}) + "\n",
                encoding="utf-8",
            )

            previous_finding = runner._normalize_finding(
                {
                    "finding_id": "craft_prev",
                    "source": "craft",
                    "severity": "HIGH",
                    "chapter_id": "chapter_01",
                    "evidence": "snapshots/cycle_01/chapters/chapter_01.md:12-16",
                    "problem": "The reveal still lands too cleanly.",
                    "rewrite_direction": "Fragment the explanation and keep the pressure jagged.",
                    "acceptance_test": "The reveal lands with less briefing energy.",
                },
                1,
            )
            runner._build_revision_packets(1, {"chapter_01": [previous_finding]})
            (run_dir / "revisions" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (run_dir / runner._revision_report_rel(1, "chapter_01")).write_text(
                json.dumps(
                    {
                        "chapter_id": "chapter_01",
                        "finding_results": [
                            {
                                "finding_id": "craft_prev",
                                "status_after_revision": "PARTIAL",
                                "evidence": "chapters/chapter_01.md:13-18",
                                "notes": "Trimmed the explanation, but the dossier name still has to stay visible here.",
                                "revision_note": "Trimmed the explanation, but the dossier name still has to stay visible here.",
                            }
                        ],
                        "summary": "One finding remained partially blocked.",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            current_finding = runner._normalize_finding(
                {
                    "finding_id": "award_002",
                    "source": "award_global",
                    "severity": "HIGH",
                    "chapter_id": "chapter_01",
                    "evidence": "snapshots/cycle_02/FINAL_NOVEL.md:19-22",
                    "problem": "The reveal still reads too much like a clean briefing.",
                    "rewrite_direction": "Keep the information legible without reverting to organized exposition.",
                    "acceptance_test": "The reveal feels pressured and incomplete rather than packaged.",
                },
                2,
            )
            runner._build_revision_packets(2, {"chapter_01": [current_finding]})

            compact_input = runner._build_compact_aggregator_input(2, ["chapter_01"])

            chapter_rows = compact_input["chapters"]["chapter_01"]["p1_structural_craft"]
            self.assertEqual(
                chapter_rows[0]["prior_attempt_context"],
                "Cycle 1 PARTIAL revision note: Trimmed the explanation, but the dossier name still has to stay visible here.",
            )

    def test_apply_aggregation_decisions_materializes_packets_and_tags_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_aggregation_materialize_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1000,
                    chapter_engine="discovery",
                    pressure_source="inspection pressure",
                    state_shift="A choice is made.",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
            ]
            runner.style_bible = {
                "character_voice_profiles": [{"character_id": "joel"}],
                "prose_style_profile": {"temperature": "high"},
                "aesthetic_risk_policy": {"sanitize": "never"},
            }

            run_dir = runner.cfg.run_dir
            (run_dir / "snapshots" / "cycle_01" / "chapters").mkdir(parents=True, exist_ok=True)
            (run_dir / "snapshots" / "cycle_01" / "chapters" / "chapter_01.md").write_text(
                "# Chapter 1\n\nCurrent chapter text.\n",
                encoding="utf-8",
            )
            (run_dir / "snapshots" / "cycle_01" / "FINAL_NOVEL.md").write_text(
                "# Title\n\n# Chapter 1\n\nalpha\nbeta\ngamma\ndelta\nepsilon\n",
                encoding="utf-8",
            )

            structural = runner._normalize_finding(
                {
                    "finding_id": "craft_001",
                    "source": "craft",
                    "severity": "HIGH",
                    "chapter_id": "chapter_01",
                    "evidence": "snapshots/cycle_01/FINAL_NOVEL.md:5",
                    "problem": "The attribution is wrong.",
                    "rewrite_direction": "Change the correction to Joel.",
                    "acceptance_test": "The correction is attributed to Joel.",
                },
                1,
            )
            prose = runner._normalize_finding(
                {
                    "finding_id": "prose_001",
                    "source": "prose",
                    "severity": "MEDIUM",
                    "chapter_id": "chapter_01",
                    "evidence": "snapshots/cycle_01/FINAL_NOVEL.md:6",
                    "problem": "The line overexplains itself.",
                    "rewrite_direction": "Cut the duplicate explanation.",
                    "acceptance_test": "The beat lands without the second explanation.",
                },
                1,
            )
            unfixable_candidate = runner._normalize_finding(
                {
                    "finding_id": "award_002",
                    "source": "award_global",
                    "severity": "HIGH",
                    "chapter_id": "chapter_01",
                    "evidence": "snapshots/cycle_01/FINAL_NOVEL.md:7",
                    "problem": "The chapter is missing groundwork for a later reveal.",
                    "rewrite_direction": "Seed a concrete hint without changing the plot outcome.",
                    "acceptance_test": "The chapter now contains a hint that prepares the later reveal.",
                },
                1,
            )

            runner._build_revision_packets(
                1,
                {"chapter_01": [structural, prose, unfixable_candidate]},
            )
            decisions = {
                "unchanged": [],
                "merges": [],
                "canonical_choices": [
                    {
                        "choice_id": "name_corrector",
                        "value": "Joel",
                        "grounding": "Continuity sheet first establishes Joel as the speaker.",
                        "affected_findings": ["craft_001"],
                        "affected_chapters": ["chapter_01"],
                    }
                ],
                "consistency_directives": [
                    {
                        "directive_id": "telepathy_fragments",
                        "rule": "Render telepathy as fragmentary surface impressions, never as a composed briefing.",
                        "source_findings": ["craft_001"],
                        "reason": "This drafting habit can recur anywhere telepathy appears.",
                    }
                ],
                "context_injections": [
                    {
                        "target_finding": "craft_001",
                        "cross_chapter_context": "Ch 3 line 445: Joel makes the correction first.",
                    }
                ],
                "suppressions": [
                    {
                        "finding_id": "prose_001",
                        "reason": "Lower priority than the structural attribution fix.",
                    }
                ],
                "unfixable": [
                    {
                        "finding_id": "award_002",
                        "attempted_partial_fix": "Add one uneasy reaction beat that anticipates the reveal.",
                        "reason": "The real issue is architectural and cannot be fully solved inside one chapter.",
                    }
                ],
                "pass_reassignments": [
                    {
                        "finding_id": "craft_001",
                        "from_pass": "p1_structural_craft",
                        "to_pass": "p2_dialogue_idiolect_cadence",
                        "reason": "The actual fix is dialogue ownership, not structure.",
                    }
                ],
            }

            runner._apply_aggregation_decisions(1, ["chapter_01"], decisions)

            p1_packet = json.loads(
                (run_dir / runner._revision_pass_packet_rel(1, "chapter_01", "p1_structural_craft")).read_text(
                    encoding="utf-8"
                )
            )
            p2_packet = json.loads(
                (run_dir / runner._revision_pass_packet_rel(1, "chapter_01", "p2_dialogue_idiolect_cadence")).read_text(
                    encoding="utf-8"
                )
            )
            main_packet = json.loads(
                (run_dir / runner._revision_packet_rel(1, "chapter_01")).read_text(
                    encoding="utf-8"
                )
            )
            suppressions = json.loads(
                (run_dir / runner._aggregation_suppressions_rel(1)).read_text(
                    encoding="utf-8"
                )
            )
            unfixable = json.loads(
                (run_dir / runner._aggregation_unfixable_rel(1)).read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(p1_packet["findings"], [])
            self.assertEqual(len(p2_packet["findings"]), 1)
            self.assertEqual(p2_packet["findings"][0]["finding_id"], "craft_001")
            self.assertEqual(
                p2_packet["findings"][0]["aggregated_pass_key"],
                "p2_dialogue_idiolect_cadence",
            )
            self.assertIn(
                "Canonical choice [name_corrector]: Joel.",
                p2_packet["findings"][0]["rewrite_direction"],
            )
            self.assertEqual(
                p2_packet["findings"][0]["cross_chapter_context"],
                "Ch 3 line 445: Joel makes the correction first.",
            )
            self.assertEqual(main_packet["must_fix_count"], 1)
            self.assertIn(
                "Render telepathy as fragmentary surface impressions, never as a composed briefing.",
                main_packet["non_negotiables"],
            )
            self.assertIn(
                "Render telepathy as fragmentary surface impressions, never as a composed briefing.",
                p2_packet["non_negotiables"],
            )
            self.assertEqual(
                main_packet["aggregation_applied"]["decisions_sha1"],
                runner._aggregation_decisions_sha1(decisions),
            )
            self.assertEqual(suppressions["suppressions"][0]["finding_id"], "prose_001")
            self.assertEqual(unfixable["unfixable"][0]["finding_id"], "award_002")
            self.assertEqual(
                unfixable["unfixable"][0]["attempted_partial_fix"],
                "Add one uneasy reaction beat that anticipates the reveal.",
            )

    def test_load_repaired_aggregation_decisions_accepts_consistency_directives(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_aggregation_directives_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1000,
                    chapter_engine="discovery",
                    pressure_source="inspection pressure",
                    state_shift="A choice is made.",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
            ]

            run_dir = runner.cfg.run_dir
            (run_dir / "packets" / "cycle_01").mkdir(parents=True, exist_ok=True)
            decisions_rel = runner._aggregation_decisions_rel(1)
            (run_dir / decisions_rel).write_text(
                json.dumps(
                    {
                        "unchanged": ["craft_001"],
                        "merges": [],
                        "canonical_choices": [],
                        "consistency_directives": [
                            {
                                "directive_id": "thesis_speech",
                                "rule": "Do not let pressured dialogue resolve into composed thesis-speech.",
                                "source_findings": ["craft_001"],
                                "reason": "This is a recurring drafting habit, not a one-off defect.",
                            }
                        ],
                        "context_injections": [],
                        "suppressions": [],
                        "unfixable": [],
                        "pass_reassignments": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            loaded = runner._load_repaired_aggregation_decisions(
                decisions_rel,
                {"craft_001"},
            )

            self.assertEqual(
                loaded["consistency_directives"][0]["directive_id"],
                "thesis_speech",
            )
            self.assertEqual(
                loaded["consistency_directives"][0]["source_findings"],
                ["craft_001"],
            )

    def test_apply_aggregation_decisions_propagates_directives_to_all_chapters(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_aggregation_directive_propagation_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1000,
                    chapter_engine="discovery",
                    pressure_source="inspection pressure",
                    state_shift="A choice is made.",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                ),
                runner_module.ChapterSpec(
                    chapter_id="chapter_02",
                    chapter_number=2,
                    projected_min_words=1000,
                    chapter_engine="complication",
                    pressure_source="social pressure",
                    state_shift="A risk is taken.",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                ),
            ]
            runner.style_bible = {
                "character_voice_profiles": [{"character_id": "joel"}],
                "prose_style_profile": {"temperature": "high"},
                "aesthetic_risk_policy": {"sanitize": "never"},
            }

            run_dir = runner.cfg.run_dir
            (run_dir / "snapshots" / "cycle_01" / "chapters").mkdir(parents=True, exist_ok=True)
            (run_dir / "snapshots" / "cycle_01" / "chapters" / "chapter_01.md").write_text(
                "# Chapter 1\n\nCurrent chapter text.\n",
                encoding="utf-8",
            )
            (run_dir / "snapshots" / "cycle_01" / "chapters" / "chapter_02.md").write_text(
                "# Chapter 2\n\nCurrent chapter text.\n",
                encoding="utf-8",
            )
            (run_dir / "snapshots" / "cycle_01" / "FINAL_NOVEL.md").write_text(
                "# Title\n\n# Chapter 1\n\nalpha\n\n# Chapter 2\n\nbeta\n",
                encoding="utf-8",
            )

            finding_1 = runner._normalize_finding(
                {
                    "finding_id": "craft_001",
                    "source": "craft",
                    "severity": "HIGH",
                    "chapter_id": "chapter_01",
                    "evidence": "snapshots/cycle_01/FINAL_NOVEL.md:3",
                    "problem": "The beat resolves into thesis-speech.",
                    "rewrite_direction": "Roughen the line.",
                    "acceptance_test": "The line no longer resolves into thesis-speech.",
                },
                1,
            )
            finding_2 = runner._normalize_finding(
                {
                    "finding_id": "craft_002",
                    "source": "craft",
                    "severity": "HIGH",
                    "chapter_id": "chapter_02",
                    "evidence": "snapshots/cycle_01/FINAL_NOVEL.md:6",
                    "problem": "The beat resolves into thesis-speech.",
                    "rewrite_direction": "Roughen the line.",
                    "acceptance_test": "The line no longer resolves into thesis-speech.",
                },
                1,
            )

            runner._build_revision_packets(
                1,
                {
                    "chapter_01": [finding_1],
                    "chapter_02": [finding_2],
                },
            )
            rule = "Do not let pressured dialogue resolve into composed thesis-speech."
            decisions = {
                "unchanged": ["craft_001", "craft_002"],
                "merges": [],
                "canonical_choices": [],
                "consistency_directives": [
                    {
                        "directive_id": "thesis_speech",
                        "rule": rule,
                        "source_findings": ["craft_001"],
                        "reason": "This drafting habit should be constrained everywhere.",
                    }
                ],
                "context_injections": [],
                "suppressions": [],
                "unfixable": [],
                "pass_reassignments": [],
            }

            runner._apply_aggregation_decisions(1, ["chapter_01", "chapter_02"], decisions)

            for chapter_id in ("chapter_01", "chapter_02"):
                packet = json.loads(
                    (run_dir / runner._revision_packet_rel(1, chapter_id)).read_text(
                        encoding="utf-8"
                    )
                )
                self.assertIn(rule, packet["non_negotiables"])

    def test_apply_aggregation_decisions_deduplicates_directive_rules_in_non_negotiables(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_aggregation_directive_dedupe_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1000,
                    chapter_engine="discovery",
                    pressure_source="inspection pressure",
                    state_shift="A choice is made.",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
            ]
            runner.style_bible = {
                "character_voice_profiles": [{"character_id": "joel"}],
                "prose_style_profile": {"temperature": "high"},
                "aesthetic_risk_policy": {"sanitize": "never"},
            }

            run_dir = runner.cfg.run_dir
            (run_dir / "snapshots" / "cycle_01" / "chapters").mkdir(parents=True, exist_ok=True)
            (run_dir / "snapshots" / "cycle_01" / "chapters" / "chapter_01.md").write_text(
                "# Chapter 1\n\nCurrent chapter text.\n",
                encoding="utf-8",
            )
            (run_dir / "snapshots" / "cycle_01" / "FINAL_NOVEL.md").write_text(
                "# Title\n\n# Chapter 1\n\nalpha\n",
                encoding="utf-8",
            )

            finding = runner._normalize_finding(
                {
                    "finding_id": "craft_001",
                    "source": "craft",
                    "severity": "HIGH",
                    "chapter_id": "chapter_01",
                    "evidence": "snapshots/cycle_01/FINAL_NOVEL.md:3",
                    "problem": "The beat resolves into thesis-speech.",
                    "rewrite_direction": "Roughen the line.",
                    "acceptance_test": "The line no longer resolves into thesis-speech.",
                },
                1,
            )
            runner._build_revision_packets(1, {"chapter_01": [finding]})
            rule = "Do not let pressured dialogue resolve into composed thesis-speech."
            decisions = {
                "unchanged": ["craft_001"],
                "merges": [],
                "canonical_choices": [],
                "consistency_directives": [
                    {
                        "directive_id": "thesis_speech_a",
                        "rule": rule,
                        "source_findings": ["craft_001"],
                        "reason": "Recurring drafting habit.",
                    },
                    {
                        "directive_id": "thesis_speech_b",
                        "rule": rule,
                        "source_findings": ["craft_001"],
                        "reason": "Same recurring drafting habit.",
                    },
                ],
                "context_injections": [],
                "suppressions": [],
                "unfixable": [],
                "pass_reassignments": [],
            }

            runner._apply_aggregation_decisions(1, ["chapter_01"], decisions)

            packet = json.loads(
                (run_dir / runner._revision_packet_rel(1, "chapter_01")).read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(packet["non_negotiables"].count(rule), 1)

    def test_validate_aggregation_decisions_rejects_malformed_consistency_directives(self) -> None:
        runner = make_runner(Path("/tmp/snp_validate_agg_directives"))
        runner.chapter_specs = [
            runner_module.ChapterSpec(
                chapter_id="chapter_01",
                chapter_number=1,
                projected_min_words=1000,
                chapter_engine="discovery",
                pressure_source="inspection pressure",
                state_shift="A choice is made.",
                texture_mode="hot",
                scene_count_target=2,
                scene_count_target_explicit=True,
                must_land_beats=["beat"],
            )
        ]

        with self.assertRaisesRegex(
            runner_module.PipelineError,
            "consistency_directives\\[1\\].source_findings must be non-empty array",
        ):
            runner._validate_aggregation_decisions(
                {
                    "unchanged": ["craft_001"],
                    "merges": [],
                    "canonical_choices": [],
                    "consistency_directives": [
                        {
                            "directive_id": "thesis_speech",
                            "rule": "Do not let pressured dialogue resolve into composed thesis-speech.",
                            "source_findings": [],
                            "reason": "Recurring drafting habit.",
                        }
                    ],
                    "context_injections": [],
                    "suppressions": [],
                    "unfixable": [],
                    "pass_reassignments": [],
                },
                {"craft_001"},
                "packets/cycle_01/aggregation_decisions.json",
            )

    def test_validate_aggregation_decisions_rejects_malformed_context_injections(self) -> None:
        runner = make_runner(Path("/tmp/snp_validate_agg_context"))
        runner.chapter_specs = [
            runner_module.ChapterSpec(
                chapter_id="chapter_01",
                chapter_number=1,
                projected_min_words=1000,
                chapter_engine="discovery",
                pressure_source="inspection pressure",
                state_shift="A choice is made.",
                texture_mode="hot",
                scene_count_target=2,
                scene_count_target_explicit=True,
                must_land_beats=["beat"],
            )
        ]

        with self.assertRaisesRegex(
            runner_module.PipelineError,
            "context_injections\\[1\\] missing target_finding or cross_chapter_context",
        ):
            runner._validate_aggregation_decisions(
                {
                    "unchanged": ["craft_001"],
                    "merges": [],
                    "canonical_choices": [],
                    "consistency_directives": [],
                    "context_injections": [
                        {
                            "target_finding": "craft_001",
                            "cross_chapter_context": "",
                        }
                    ],
                    "suppressions": [],
                    "unfixable": [],
                    "pass_reassignments": [],
                },
                {"craft_001"},
                "packets/cycle_01/aggregation_decisions.json",
            )

    def test_load_repaired_aggregation_decisions_drops_incomplete_directives(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_aggregation_directive_repair_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1000,
                    chapter_engine="discovery",
                    pressure_source="inspection pressure",
                    state_shift="A choice is made.",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
            ]

            run_dir = runner.cfg.run_dir
            (run_dir / "packets" / "cycle_01").mkdir(parents=True, exist_ok=True)
            decisions_rel = runner._aggregation_decisions_rel(1)
            (run_dir / decisions_rel).write_text(
                json.dumps(
                    {
                        "unchanged": ["craft_001"],
                        "merges": [],
                        "canonical_choices": [],
                        "consistency_directives": [
                            {
                                "directive_id": "good_directive",
                                "rule": "Do not let pressured dialogue resolve into composed thesis-speech.",
                                "source_findings": ["craft_001"],
                                "reason": "Recurring drafting habit.",
                            },
                            {
                                "directive_id": "bad_directive",
                                "rule": "",
                                "source_findings": ["craft_001"],
                                "reason": "Missing rule should drop this directive.",
                            },
                        ],
                        "context_injections": [],
                        "suppressions": [],
                        "unfixable": [],
                        "pass_reassignments": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            loaded = runner._load_repaired_aggregation_decisions(
                decisions_rel,
                {"craft_001"},
            )

            self.assertEqual(len(loaded["consistency_directives"]), 1)
            self.assertEqual(
                loaded["consistency_directives"][0]["directive_id"],
                "good_directive",
            )
            self.assertTrue(
                (run_dir / "packets" / "cycle_01" / "aggregation_decisions.invalid.original.json").is_file()
            )

    def test_load_repaired_aggregation_decisions_drops_invalid_context_injections(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_aggregation_context_repair_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1000,
                    chapter_engine="discovery",
                    pressure_source="inspection pressure",
                    state_shift="A choice is made.",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
            ]

            run_dir = runner.cfg.run_dir
            (run_dir / "packets" / "cycle_01").mkdir(parents=True, exist_ok=True)
            decisions_rel = runner._aggregation_decisions_rel(1)
            (run_dir / decisions_rel).write_text(
                json.dumps(
                    {
                        "unchanged": ["craft_001"],
                        "merges": [],
                        "canonical_choices": [],
                        "consistency_directives": [],
                        "context_injections": [
                            {
                                "target_finding": "missing_finding",
                                "cross_chapter_context": "Ch 3 line 445: Joel makes the correction first.",
                            }
                        ],
                        "suppressions": [],
                        "unfixable": [],
                        "pass_reassignments": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            loaded = runner._load_repaired_aggregation_decisions(
                decisions_rel,
                {"craft_001"},
            )

            self.assertEqual(loaded["context_injections"], [])
            self.assertTrue(
                (run_dir / "packets" / "cycle_01" / "aggregation_decisions.invalid.original.json").is_file()
            )

    def test_run_llm_aggregator_stage_falls_back_when_decisions_are_invalid(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_aggregation_fallback_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1000,
                    chapter_engine="discovery",
                    pressure_source="inspection pressure",
                    state_shift="A choice is made.",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
            ]
            runner.style_bible = {
                "character_voice_profiles": [{"character_id": "joel"}],
                "prose_style_profile": {"temperature": "high"},
                "aesthetic_risk_policy": {"sanitize": "never"},
            }

            run_dir = runner.cfg.run_dir
            runner._prepare_run_dir()
            (run_dir / "outline").mkdir(parents=True, exist_ok=True)
            (run_dir / "outline" / "continuity_sheet.json").write_text(
                json.dumps({"characters": [], "geography": {}}) + "\n",
                encoding="utf-8",
            )
            (run_dir / "snapshots" / "cycle_01" / "chapters").mkdir(parents=True, exist_ok=True)
            (run_dir / "snapshots" / "cycle_01" / "chapters" / "chapter_01.md").write_text(
                "# Chapter 1\n\nCurrent chapter text.\n",
                encoding="utf-8",
            )
            (run_dir / "snapshots" / "cycle_01" / "FINAL_NOVEL.md").write_text(
                "# Title\n\n# Chapter 1\n\nalpha\nbeta\ngamma\ndelta\nepsilon\n",
                encoding="utf-8",
            )

            finding = runner._normalize_finding(
                {
                    "finding_id": "award_001",
                    "source": "award_global",
                    "severity": "HIGH",
                    "chapter_id": "chapter_01",
                    "evidence": "snapshots/cycle_01/FINAL_NOVEL.md:5",
                    "problem": "The beat is too polished.",
                    "rewrite_direction": "Roughen the exchange.",
                    "acceptance_test": "The exchange now sounds harder-edged.",
                },
                1,
            )
            runner._build_revision_packets(1, {"chapter_01": [finding]})

            def fake_run_job(job: runner_module.JobSpec) -> None:
                runner._write_json(
                    job.required_outputs[0],
                    {
                        "unchanged": ["invented_finding"],
                        "merges": [],
                        "canonical_choices": [],
                        "context_injections": [],
                        "suppressions": [],
                        "unfixable": [],
                        "pass_reassignments": [],
                    },
                )

            with mock.patch.object(runner, "_run_job", side_effect=fake_run_job):
                summary = runner._run_llm_aggregator_stage(1, ["chapter_01"])

            self.assertEqual(summary["status"], "failed")
            self.assertEqual(
                summary["reason"],
                "invalid_decisions_fallback_to_mechanical_packets",
            )

    def test_post_revision_snapshot_publishes_root_final_novel_and_reports_it(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_final_novel_publish_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1000,
                    chapter_engine="discovery",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
            ]

            run_dir = runner.cfg.run_dir
            (run_dir / "chapters").mkdir(parents=True, exist_ok=True)
            (run_dir / "chapters" / "chapter_01.md").write_text(
                "# Chapter 1\n\nBody text.\n", encoding="utf-8"
            )

            runner._assemble_post_revision_snapshot(1)

            root_final = run_dir / "FINAL_NOVEL.md"
            snapshot_final = (
                run_dir / "snapshots" / "cycle_01" / "FINAL_NOVEL.post_revision.md"
            )
            (run_dir / "status" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (run_dir / "status" / "cycle_01" / "cycle_status.json").write_text(
                json.dumps({"cycle": 1}) + "\n",
                encoding="utf-8",
            )
            (run_dir / "status" / "cycle_01" / "quality_summary.json").write_text(
                json.dumps({"cycle": 1}) + "\n",
                encoding="utf-8",
            )
            self.assertTrue(root_final.is_file())
            self.assertTrue(snapshot_final.is_file())
            self.assertEqual(
                root_final.read_text(encoding="utf-8"),
                snapshot_final.read_text(encoding="utf-8"),
            )

            runner._write_final_report(success_cycle=1, gate_records=[{"cycle": 1}])
            final_report = json.loads(
                (run_dir / "reports" / "final_report.json").read_text(encoding="utf-8")
            )
            final_status = json.loads(
                (run_dir / "reports" / "final_status.json").read_text(encoding="utf-8")
            )
            self.assertEqual(final_report["final_novel_file"], "FINAL_NOVEL.md")
            self.assertEqual(
                final_report["final_novel_snapshot_file"],
                "snapshots/cycle_01/FINAL_NOVEL.post_revision.md",
            )
            self.assertEqual(
                final_report["cycle_status_files"],
                ["status/cycle_01/cycle_status.json"],
            )
            self.assertEqual(
                final_report["quality_summary_files"],
                ["status/cycle_01/quality_summary.json"],
            )
            self.assertEqual(final_status["final_novel_file"], "FINAL_NOVEL.md")
            self.assertEqual(
                final_status["final_novel_snapshot_file"],
                "snapshots/cycle_01/FINAL_NOVEL.post_revision.md",
            )
            self.assertEqual(
                final_status["last_cycle_status_file"],
                "status/cycle_01/cycle_status.json",
            )
            self.assertEqual(
                final_status["last_quality_summary_file"],
                "status/cycle_01/quality_summary.json",
            )

    def test_write_final_report_merges_existing_gate_history(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_final_report_gate_history_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            run_dir = runner.cfg.run_dir
            runner._prepare_run_dir()
            (run_dir / "gate" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (run_dir / "gate" / "cycle_01" / "gate.json").write_text(
                json.dumps({"cycle": 1, "decision": "FAIL"}) + "\n",
                encoding="utf-8",
            )

            runner._write_final_report(success_cycle=2, gate_records=[{"cycle": 2, "decision": "FAIL"}])
            final_report = json.loads(
                (run_dir / "reports" / "final_report.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                [row["cycle"] for row in final_report["gate_history"]],
                [1, 2],
            )

    def test_write_quality_summary_persists_advisory_cycle_summary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_quality_summary_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            aggregate = {
                "summary": {
                    "cycle": 1,
                    "total_unresolved_medium_plus": 3,
                    "by_severity": {"HIGH": 2, "MEDIUM": 1},
                    "by_source": {"award_global": 1, "cross_chapter": 2},
                    "chapters_touched": ["chapter_01", "chapter_02"],
                    "chapter_review_failures": 1,
                    "full_award_verdict": "FAIL",
                    "cross_chapter_audit_failed": False,
                }
            }
            gate = {
                "decision": "FAIL",
                "reason": "unresolved_medium_plus_or_review_failures_or_full_award_fail",
                "full_award_verdict": "FAIL",
                "unresolved_medium_plus_count": 3,
            }

            runner._write_quality_summary(1, aggregate, gate)

            payload = json.loads(
                (runner.cfg.run_dir / "status" / "cycle_01" / "quality_summary.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(payload["cycle"], 1)
            self.assertTrue(payload["advisory_only"])
            self.assertEqual(payload["total_unresolved_medium_plus"], 3)
            self.assertEqual(payload["advisory_gate"]["decision"], "FAIL")
            self.assertEqual(
                payload["advisory_gate"]["unresolved_medium_plus_count"],
                3,
            )

    def test_run_writes_cycle_status_for_fresh_cycle(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_cycle_status_run_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            aggregate = {
                "summary": {
                    "cycle": 1,
                    "total_unresolved_medium_plus": 0,
                    "by_severity": {},
                    "by_source": {},
                    "chapters_touched": [],
                    "chapter_review_failures": 0,
                    "full_award_verdict": "PASS",
                    "cross_chapter_audit_failed": False,
                },
                "all_findings": [],
                "by_chapter": {},
                "full_award_verdict": "PASS",
                "chapter_review_failures": 0,
                "cross_chapter_audit_failed": False,
            }
            gate = {
                "cycle": 1,
                "full_award_verdict": "PASS",
                "unresolved_medium_plus_count": 0,
                "chapter_review_failures": 0,
                "cross_chapter_audit_failed": False,
                "decision": "PASS",
                "reason": "all_unresolved_medium_plus_closed_and_full_award_pass",
            }

            with mock.patch.object(runner, "_prepare_run_dir"), mock.patch.object(
                runner, "_resolve_premise"
            ), mock.patch.object(runner, "_run_outline_stage"), mock.patch.object(
                runner, "_run_draft_stage"
            ), mock.patch.object(
                runner, "_assemble_snapshot", return_value=False
            ), mock.patch.object(
                runner, "_build_cycle_context_packs", return_value=False
            ), mock.patch.object(
                runner,
                "_run_chapter_review_stage",
                return_value={
                    "status": "complete",
                    "chapter_count": 18,
                    "units": {},
                },
            ) as run_chapter_review, mock.patch.object(
                runner,
                "_run_parallel_full_book_review_stages",
                return_value={
                    "full_award_review": False,
                    "cross_chapter_audit": False,
                    "local_window_audit": {
                        "status": "complete",
                        "units": {
                            "window_01": {
                                "status": "complete",
                                "validated": True,
                                "fresh": True,
                            }
                        },
                    },
                },
            ), mock.patch.object(
                runner, "_aggregate_findings", return_value=aggregate
            ), mock.patch.object(
                runner, "_write_gate", return_value=gate
            ), mock.patch.object(
                runner, "_assemble_post_revision_snapshot", return_value=False
            ), mock.patch.object(
                runner, "_run_continuity_reconciliation", return_value=False
            ), mock.patch.object(
                runner, "_write_final_report"
            ), mock.patch.object(
                runner, "_print_cost_summary"
            ):
                self.assertEqual(runner.run(), 0)

            payload = json.loads(
                (runner.cfg.run_dir / "status" / "cycle_01" / "cycle_status.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(payload["cycle"], 1)
            self.assertEqual(payload["run_mode"], "fresh")
            self.assertFalse(payload["completion_policy"]["terminate_on_quality_pass"])
            self.assertEqual(payload["stages"]["assemble_snapshot"]["status"], "complete")
            self.assertEqual(payload["stages"]["chapter_review"]["status"], "complete")
            self.assertEqual(payload["stages"]["local_window_audit"]["status"], "complete")
            self.assertEqual(
                payload["stages"]["local_window_audit"]["units"]["window_01"]["status"],
                "complete",
            )
            self.assertEqual(payload["stages"]["aggregate_findings"]["status"], "complete")
            self.assertEqual(payload["stages"]["revision"]["status"], "skipped")
            self.assertEqual(
                payload["stages"]["revision"]["reason"],
                "no_actionable_findings",
            )
            self.assertEqual(payload["advisory_gate"]["decision"], "PASS")

    def test_run_records_failed_continuity_reconciliation_status_from_summary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_cycle_status_continuity_fail_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            aggregate = {
                "summary": {
                    "cycle": 1,
                    "total_unresolved_medium_plus": 0,
                    "by_severity": {},
                    "by_source": {},
                    "chapters_touched": [],
                    "chapter_review_failures": 0,
                    "full_award_verdict": "PASS",
                    "cross_chapter_audit_failed": False,
                },
                "all_findings": [],
                "by_chapter": {},
                "full_award_verdict": "PASS",
                "chapter_review_failures": 0,
                "cross_chapter_audit_failed": False,
            }
            gate = {
                "cycle": 1,
                "full_award_verdict": "PASS",
                "unresolved_medium_plus_count": 0,
                "chapter_review_failures": 0,
                "cross_chapter_audit_failed": False,
                "decision": "PASS",
                "reason": "all_unresolved_medium_plus_closed_and_full_award_pass",
            }

            with mock.patch.object(runner, "_prepare_run_dir"), mock.patch.object(
                runner, "_resolve_premise"
            ), mock.patch.object(runner, "_run_outline_stage"), mock.patch.object(
                runner, "_run_draft_stage"
            ), mock.patch.object(
                runner, "_assemble_snapshot", return_value=False
            ), mock.patch.object(
                runner, "_build_cycle_context_packs", return_value=False
            ), mock.patch.object(
                runner,
                "_run_chapter_review_stage",
                return_value={
                    "status": "complete",
                    "chapter_count": 18,
                    "units": {},
                },
            ) as run_chapter_review, mock.patch.object(
                runner,
                "_run_parallel_full_book_review_stages",
                return_value={
                    "full_award_review": False,
                    "cross_chapter_audit": False,
                    "local_window_audit": {
                        "status": "complete",
                        "units": {
                            "window_01": {
                                "status": "complete",
                                "validated": True,
                                "fresh": True,
                            }
                        },
                    },
                },
            ), mock.patch.object(
                runner, "_aggregate_findings", return_value=aggregate
            ), mock.patch.object(
                runner, "_write_gate", return_value=gate
            ), mock.patch.object(
                runner, "_assemble_post_revision_snapshot", return_value=False
            ), mock.patch.object(
                runner,
                "_run_continuity_reconciliation",
                return_value={"status": "failed", "reason": "job_failed_soft"},
            ), mock.patch.object(
                runner, "_write_final_report"
            ), mock.patch.object(
                runner, "_print_cost_summary"
            ):
                self.assertEqual(runner.run(), 0)

            payload = json.loads(
                (runner.cfg.run_dir / "status" / "cycle_01" / "cycle_status.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                payload["stages"]["continuity_reconciliation"]["status"],
                "failed",
            )
            self.assertEqual(
                payload["stages"]["continuity_reconciliation"]["reason"],
                "job_failed_soft",
            )

    def test_run_continues_after_advisory_gate_pass_until_max_cycles(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_advisory_gate_pass_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.cfg = dataclasses.replace(runner.cfg, max_cycles=2)
            aggregate = {
                "summary": {
                    "cycle": 1,
                    "total_unresolved_medium_plus": 0,
                    "by_severity": {},
                    "by_source": {},
                    "chapters_touched": [],
                    "chapter_review_failures": 0,
                    "full_award_verdict": "PASS",
                    "cross_chapter_audit_failed": False,
                },
                "all_findings": [],
                "by_chapter": {},
                "full_award_verdict": "PASS",
                "chapter_review_failures": 0,
                "cross_chapter_audit_failed": False,
            }

            def gate_for_cycle(cycle: int, _aggregate: dict[str, object]) -> dict[str, object]:
                return {
                    "cycle": cycle,
                    "full_award_verdict": "PASS",
                    "unresolved_medium_plus_count": 0,
                    "chapter_review_failures": 0,
                    "cross_chapter_audit_failed": False,
                    "decision": "PASS",
                    "reason": "all_unresolved_medium_plus_closed_and_full_award_pass",
                }

            with mock.patch.object(runner, "_prepare_run_dir"), mock.patch.object(
                runner, "_resolve_premise"
            ), mock.patch.object(runner, "_run_outline_stage"), mock.patch.object(
                runner, "_run_draft_stage"
            ), mock.patch.object(
                runner, "_assemble_snapshot", return_value=False
            ) as assemble_snapshot, mock.patch.object(
                runner, "_build_cycle_context_packs", return_value=False
            ), mock.patch.object(
                runner,
                "_run_chapter_review_stage",
                return_value={
                    "status": "complete",
                    "chapter_count": 18,
                    "units": {},
                },
            ) as run_chapter_review, mock.patch.object(
                runner,
                "_run_parallel_full_book_review_stages",
                return_value={
                    "full_award_review": False,
                    "cross_chapter_audit": False,
                    "local_window_audit": {
                        "status": "complete",
                        "units": {
                            "window_01": {
                                "status": "complete",
                                "validated": True,
                                "fresh": True,
                            }
                        },
                    },
                },
            ), mock.patch.object(
                runner, "_aggregate_findings", return_value=aggregate
            ), mock.patch.object(
                runner, "_write_gate", side_effect=gate_for_cycle
            ) as write_gate, mock.patch.object(
                runner, "_build_revision_packets"
            ) as build_packets, mock.patch.object(
                runner, "_run_revision_stage"
            ) as run_revision, mock.patch.object(
                runner, "_assemble_post_revision_snapshot", return_value=False
            ), mock.patch.object(
                runner, "_run_continuity_reconciliation", return_value=False
            ), mock.patch.object(
                runner, "_write_final_report"
            ) as write_final_report, mock.patch.object(
                runner, "_print_cost_summary"
            ):
                self.assertEqual(runner.run(), 0)

            self.assertEqual(assemble_snapshot.call_count, 2)
            self.assertEqual(write_gate.call_count, 2)
            build_packets.assert_not_called()
            run_revision.assert_not_called()
            self.assertEqual(write_final_report.call_args.args[0], 2)
            self.assertEqual(len(write_final_report.call_args.args[1]), 2)

            cycle_one_status = json.loads(
                (runner.cfg.run_dir / "status" / "cycle_01" / "cycle_status.json").read_text(
                    encoding="utf-8"
                )
            )
            cycle_two_status = json.loads(
                (runner.cfg.run_dir / "status" / "cycle_02" / "cycle_status.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertFalse(
                cycle_one_status["completion_policy"]["terminate_on_quality_pass"]
            )
            self.assertEqual(
                cycle_one_status["stages"]["revision"]["reason"],
                "no_actionable_findings",
            )
            self.assertEqual(cycle_two_status["cycle"], 2)

    def test_run_add_cycles_starts_at_next_cycle(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_add_cycles_run_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.cfg = dataclasses.replace(
                runner.cfg,
                max_cycles=2,
                add_cycles=1,
                base_completed_cycles=1,
            )
            aggregate = {
                "summary": {
                    "cycle": 2,
                    "total_unresolved_medium_plus": 0,
                    "by_severity": {},
                    "by_source": {},
                    "chapters_touched": [],
                    "chapter_review_failures": 0,
                    "full_award_verdict": "PASS",
                    "cross_chapter_audit_failed": False,
                },
                "all_findings": [],
                "by_chapter": {},
                "full_award_verdict": "PASS",
                "chapter_review_failures": 0,
                "cross_chapter_audit_failed": False,
            }

            def gate_for_cycle(cycle: int, _aggregate: dict[str, object]) -> dict[str, object]:
                return {
                    "cycle": cycle,
                    "full_award_verdict": "PASS",
                    "unresolved_medium_plus_count": 0,
                    "chapter_review_failures": 0,
                    "cross_chapter_audit_failed": False,
                    "decision": "PASS",
                    "reason": "all_unresolved_medium_plus_closed_and_full_award_pass",
                }

            with mock.patch.object(runner, "_prepare_run_dir"), mock.patch.object(
                runner, "_resolve_premise"
            ), mock.patch.object(runner, "_run_outline_stage"), mock.patch.object(
                runner, "_run_draft_stage"
            ), mock.patch.object(
                runner, "_assemble_snapshot", return_value=False
            ) as assemble_snapshot, mock.patch.object(
                runner, "_build_cycle_context_packs", return_value=False
            ), mock.patch.object(
                runner,
                "_run_chapter_review_stage",
                return_value={
                    "status": "complete",
                    "chapter_count": 18,
                    "units": {},
                },
            ) as run_chapter_review, mock.patch.object(
                runner,
                "_run_parallel_full_book_review_stages",
                return_value={
                    "full_award_review": False,
                    "cross_chapter_audit": False,
                    "local_window_audit": {
                        "status": "complete",
                        "units": {},
                    },
                },
            ), mock.patch.object(
                runner, "_aggregate_findings", return_value=aggregate
            ), mock.patch.object(
                runner, "_write_gate", side_effect=gate_for_cycle
            ) as write_gate, mock.patch.object(
                runner, "_assemble_post_revision_snapshot", return_value=False
            ), mock.patch.object(
                runner, "_run_continuity_reconciliation", return_value=False
            ), mock.patch.object(
                runner, "_write_final_report"
            ) as write_final_report, mock.patch.object(
                runner, "_print_cost_summary"
            ):
                self.assertEqual(runner.run(), 0)

            assemble_snapshot.assert_called_once_with(2)
            run_chapter_review.assert_not_called()
            write_gate.assert_called_once()
            self.assertEqual(write_gate.call_args.args[0], 2)
            self.assertEqual(write_final_report.call_args.args[0], 2)
            cycle_two_status = json.loads(
                (runner.cfg.run_dir / "status" / "cycle_02" / "cycle_status.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                cycle_two_status["stages"]["chapter_review"]["status"],
                "skipped",
            )
            self.assertEqual(
                cycle_two_status["stages"]["chapter_review"]["reason"],
                "final_cycle_global_only",
            )

    def test_run_skips_chapter_review_on_final_cycle_when_global_only_enabled(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_final_cycle_global_only_run_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.cfg = dataclasses.replace(
                runner.cfg,
                max_cycles=2,
                min_cycles=2,
            )
            aggregates = [
                {
                    "summary": {
                        "cycle": 1,
                        "total_unresolved_medium_plus": 0,
                        "by_severity": {},
                        "by_source": {},
                        "chapters_touched": [],
                        "chapter_review_failures": 0,
                        "chapter_review_skipped": False,
                        "full_award_verdict": "PASS",
                        "cross_chapter_audit_failed": False,
                    },
                    "all_findings": [],
                    "by_chapter": {},
                    "full_award_verdict": "PASS",
                    "chapter_review_failures": 0,
                    "chapter_review_skipped": False,
                    "cross_chapter_audit_failed": False,
                },
                {
                    "summary": {
                        "cycle": 2,
                        "total_unresolved_medium_plus": 0,
                        "by_severity": {},
                        "by_source": {},
                        "chapters_touched": [],
                        "chapter_review_failures": 0,
                        "chapter_review_skipped": True,
                        "full_award_verdict": "PASS",
                        "cross_chapter_audit_failed": False,
                    },
                    "all_findings": [],
                    "by_chapter": {},
                    "full_award_verdict": "PASS",
                    "chapter_review_failures": 0,
                    "chapter_review_skipped": True,
                    "cross_chapter_audit_failed": False,
                },
            ]

            def gate_for_cycle(cycle: int, _aggregate: dict[str, object]) -> dict[str, object]:
                return {
                    "cycle": cycle,
                    "full_award_verdict": "PASS",
                    "unresolved_medium_plus_count": 0,
                    "chapter_review_failures": 0,
                    "cross_chapter_audit_failed": False,
                    "decision": "PASS",
                    "reason": "all_unresolved_medium_plus_closed_and_full_award_pass",
                }

            with mock.patch.object(runner, "_prepare_run_dir"), mock.patch.object(
                runner, "_resolve_premise"
            ), mock.patch.object(runner, "_run_outline_stage"), mock.patch.object(
                runner, "_run_draft_stage"
            ), mock.patch.object(
                runner, "_assemble_snapshot", return_value=False
            ), mock.patch.object(
                runner, "_build_cycle_context_packs", return_value=False
            ), mock.patch.object(
                runner,
                "_run_chapter_review_stage",
                return_value={
                    "status": "complete",
                    "chapter_count": 18,
                    "units": {},
                },
            ) as run_chapter_review, mock.patch.object(
                runner,
                "_run_parallel_full_book_review_stages",
                return_value={
                    "full_award_review": False,
                    "cross_chapter_audit": False,
                    "local_window_audit": {
                        "status": "complete",
                        "units": {},
                    },
                },
            ), mock.patch.object(
                runner, "_aggregate_findings", side_effect=aggregates
            ), mock.patch.object(
                runner, "_write_gate", side_effect=gate_for_cycle
            ), mock.patch.object(
                runner, "_assemble_post_revision_snapshot", return_value=False
            ), mock.patch.object(
                runner, "_run_continuity_reconciliation", return_value=False
            ), mock.patch.object(
                runner, "_write_final_report"
            ), mock.patch.object(
                runner, "_print_cost_summary"
            ):
                self.assertEqual(runner.run(), 0)

            self.assertEqual(run_chapter_review.call_count, 1)
            cycle_two_status = json.loads(
                (runner.cfg.run_dir / "status" / "cycle_02" / "cycle_status.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                cycle_two_status["stages"]["chapter_review"]["status"],
                "skipped",
            )
            self.assertEqual(
                cycle_two_status["stages"]["chapter_review"]["reason"],
                "final_cycle_global_only",
            )

    def test_run_revision_still_executes_when_advisory_gate_pass_has_actionable_findings(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_advisory_gate_actionable_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            aggregate = {
                "summary": {
                    "cycle": 1,
                    "total_unresolved_medium_plus": 0,
                    "by_severity": {"LOW": 1},
                    "by_source": {"chapter_review": 1},
                    "chapters_touched": ["chapter_01"],
                    "chapter_review_failures": 0,
                    "full_award_verdict": "PASS",
                    "cross_chapter_audit_failed": False,
                },
                "all_findings": [
                    {
                        "finding_id": "chapter_01_low_001",
                        "source": "chapter_review",
                        "severity": "LOW",
                        "chapter_id": "chapter_01",
                        "evidence": "chapters/chapter_01.md:4",
                        "problem": "The paragraph repeats a beat that can be tightened.",
                        "rewrite_direction": "Cut the duplicate beat.",
                        "acceptance_test": "The paragraph moves once through the beat.",
                        "status": "UNRESOLVED",
                        "cycle": 1,
                    }
                ],
                "by_chapter": {
                    "chapter_01": [
                        {
                            "finding_id": "chapter_01_low_001",
                        }
                    ]
                },
                "full_award_verdict": "PASS",
                "chapter_review_failures": 0,
                "cross_chapter_audit_failed": False,
            }
            gate = {
                "cycle": 1,
                "full_award_verdict": "PASS",
                "unresolved_medium_plus_count": 0,
                "chapter_review_failures": 0,
                "cross_chapter_audit_failed": False,
                "decision": "PASS",
                "reason": "all_unresolved_medium_plus_closed_and_full_award_pass",
            }

            with mock.patch.object(runner, "_prepare_run_dir"), mock.patch.object(
                runner, "_resolve_premise"
            ), mock.patch.object(runner, "_run_outline_stage"), mock.patch.object(
                runner, "_run_draft_stage"
            ), mock.patch.object(
                runner, "_assemble_snapshot", return_value=False
            ), mock.patch.object(
                runner, "_build_cycle_context_packs", return_value=False
            ), mock.patch.object(
                runner,
                "_run_chapter_review_stage",
                return_value={
                    "status": "complete",
                    "chapter_count": 18,
                    "units": {},
                },
            ), mock.patch.object(
                runner,
                "_run_parallel_full_book_review_stages",
                return_value={
                    "full_award_review": False,
                    "cross_chapter_audit": False,
                    "local_window_audit": {
                        "status": "complete",
                        "units": {
                            "window_01": {
                                "status": "complete",
                                "validated": True,
                                "fresh": True,
                            }
                        },
                    },
                },
            ), mock.patch.object(
                runner, "_aggregate_findings", return_value=aggregate
            ), mock.patch.object(
                runner, "_write_gate", return_value=gate
            ), mock.patch.object(
                runner, "_build_revision_packets"
            ) as build_packets, mock.patch.object(
                runner,
                "_run_llm_aggregator_stage",
                return_value={
                    "status": "complete",
                    "outputs": [
                        "packets/cycle_01/compact_aggregator_input.json",
                        "packets/cycle_01/aggregation_decisions.json",
                    ],
                    "decisions": {
                        "unchanged": ["chapter_01_low_001"],
                        "merges": [],
                        "canonical_choices": [],
                        "context_injections": [],
                        "suppressions": [],
                        "unfixable": [],
                        "pass_reassignments": [],
                    },
                },
            ), mock.patch.object(
                runner,
                "_materialize_aggregation_decisions_stage",
                return_value={
                    "status": "complete",
                    "outputs": [
                        "packets/cycle_01/aggregation_materialization_summary.json",
                        "packets/cycle_01/aggregation_suppressions.json",
                        "packets/cycle_01/aggregation_unfixable.json",
                    ],
                },
            ), mock.patch.object(
                runner,
                "_run_revision_stage",
                return_value={
                    "status": "complete",
                    "chapter_count": 1,
                    "units": {},
                },
            ) as run_revision, mock.patch.object(
                runner, "_assemble_post_revision_snapshot", return_value=False
            ), mock.patch.object(
                runner, "_run_continuity_reconciliation", return_value=False
            ), mock.patch.object(
                runner, "_write_final_report"
            ), mock.patch.object(
                runner, "_print_cost_summary"
            ):
                self.assertEqual(runner.run(), 0)

            build_packets.assert_called_once_with(1, aggregate["by_chapter"])
            run_revision.assert_called_once_with(1, ["chapter_01"])

            payload = json.loads(
                (runner.cfg.run_dir / "status" / "cycle_01" / "cycle_status.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(payload["advisory_gate"]["decision"], "PASS")
            self.assertEqual(
                payload["stages"]["build_revision_packets"]["status"],
                "complete",
            )
            self.assertEqual(payload["stages"]["revision"]["status"], "complete")

    def test_run_returns_success_when_max_cycles_reached_without_quality_pass(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_operational_success_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            aggregate = {
                "summary": {
                    "cycle": 1,
                    "total_unresolved_medium_plus": 1,
                    "by_severity": {"HIGH": 1},
                    "by_source": {"award_global": 1},
                    "chapters_touched": ["chapter_01"],
                    "chapter_review_failures": 0,
                    "full_award_verdict": "FAIL",
                    "cross_chapter_audit_failed": False,
                },
                "all_findings": [
                    {
                        "finding_id": "award_001",
                        "source": "award_global",
                        "severity": "HIGH",
                        "chapter_id": "chapter_01",
                        "evidence": "snapshots/cycle_01/FINAL_NOVEL.md:4",
                        "problem": "The chapter still has a blocker.",
                        "rewrite_direction": "Revise the blocker.",
                        "acceptance_test": "The blocker is resolved.",
                        "status": "UNRESOLVED",
                        "cycle": 1,
                    }
                ],
                "by_chapter": {
                    "chapter_01": [
                        {
                            "finding_id": "award_001",
                        }
                    ]
                },
                "full_award_verdict": "FAIL",
                "chapter_review_failures": 0,
                "cross_chapter_audit_failed": False,
            }
            gate = {
                "cycle": 1,
                "full_award_verdict": "FAIL",
                "unresolved_medium_plus_count": 1,
                "chapter_review_failures": 0,
                "cross_chapter_audit_failed": False,
                "decision": "FAIL",
                "reason": "unresolved_medium_plus_or_review_failures_or_full_award_fail",
            }

            with mock.patch.object(runner, "_prepare_run_dir"), mock.patch.object(
                runner, "_resolve_premise"
            ), mock.patch.object(runner, "_run_outline_stage"), mock.patch.object(
                runner, "_run_draft_stage"
            ), mock.patch.object(
                runner, "_assemble_snapshot", return_value=False
            ), mock.patch.object(
                runner, "_build_cycle_context_packs", return_value=False
            ), mock.patch.object(
                runner,
                "_run_chapter_review_stage",
                return_value={
                    "status": "complete",
                    "chapter_count": 18,
                    "units": {},
                },
            ), mock.patch.object(
                runner,
                "_run_parallel_full_book_review_stages",
                return_value={
                    "full_award_review": False,
                    "cross_chapter_audit": False,
                    "local_window_audit": {
                        "status": "complete",
                        "units": {
                            "window_01": {
                                "status": "complete",
                                "validated": True,
                                "fresh": True,
                            }
                        },
                    },
                },
            ), mock.patch.object(
                runner, "_aggregate_findings", return_value=aggregate
            ), mock.patch.object(
                runner, "_write_gate", return_value=gate
            ), mock.patch.object(
                runner, "_build_revision_packets"
            ) as build_packets, mock.patch.object(
                runner,
                "_run_llm_aggregator_stage",
                return_value={
                    "status": "complete",
                    "outputs": [
                        "packets/cycle_01/compact_aggregator_input.json",
                        "packets/cycle_01/aggregation_decisions.json",
                    ],
                    "decisions": {
                        "unchanged": ["award_001"],
                        "merges": [],
                        "canonical_choices": [],
                        "context_injections": [],
                        "suppressions": [],
                        "unfixable": [],
                        "pass_reassignments": [],
                    },
                },
            ), mock.patch.object(
                runner,
                "_materialize_aggregation_decisions_stage",
                return_value={
                    "status": "complete",
                    "outputs": [
                        "packets/cycle_01/aggregation_materialization_summary.json",
                        "packets/cycle_01/aggregation_suppressions.json",
                        "packets/cycle_01/aggregation_unfixable.json",
                    ],
                },
            ), mock.patch.object(
                runner,
                "_run_revision_stage",
                return_value={
                    "status": "complete",
                    "chapter_count": 1,
                    "units": {},
                },
            ) as run_revision, mock.patch.object(
                runner, "_assemble_post_revision_snapshot", return_value=False
            ), mock.patch.object(
                runner, "_run_continuity_reconciliation", return_value=False
            ), mock.patch.object(
                runner, "_write_final_report"
            ) as write_final_report, mock.patch.object(
                runner, "_print_cost_summary"
            ):
                self.assertEqual(runner.run(), 0)

            build_packets.assert_called_once()
            run_revision.assert_called_once()
            self.assertEqual(write_final_report.call_args.args[0], 1)

    def test_run_draft_stage_skips_expand_when_all_chapters_are_fresh_on_resume(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_draft_resume_skip_expand_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1000,
                    chapter_engine="discovery",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
            ]

            run_dir = runner.cfg.run_dir
            runner._prepare_run_dir()

            (run_dir / "outline" / "outline.md").write_text("# Outline\n", encoding="utf-8")
            (run_dir / "outline" / "scene_plan.tsv").write_text(
                "scene_id\tchapter_id\n", encoding="utf-8"
            )
            (run_dir / "outline" / "static_story_context.json").write_text(
                "{}\n", encoding="utf-8"
            )
            (run_dir / "outline" / "spatial_layout.json").write_text(
                json.dumps({"summary": "layout", "micro": None, "macro": None}) + "\n",
                encoding="utf-8",
            )
            (run_dir / "outline" / "style_bible.json").write_text("{}\n", encoding="utf-8")
            (run_dir / "outline" / "continuity_sheet.json").write_text(
                "{}\n", encoding="utf-8"
            )
            (run_dir / "outline" / "continuity_sheet.outline.json").write_text(
                "{}\n", encoding="utf-8"
            )
            (run_dir / "outline" / "chapter_specs" / "chapter_01.json").write_text(
                "{}\n",
                encoding="utf-8",
            )

            chapter_path = run_dir / "chapters" / "chapter_01.md"
            chapter_path.write_text("# Chapter 1\n\nShort body.\n", encoding="utf-8")

            with mock.patch.object(runner, "_run_jobs_parallel") as run_jobs, mock.patch.object(
                runner, "_log"
            ) as log_mock:
                runner._run_draft_stage()

            run_jobs.assert_not_called()
            logged = [" ".join(str(arg) for arg in call.args) for call in log_mock.call_args_list]
            self.assertIn("draft_resume_all_chapters_present", logged)
            self.assertIn("draft_expand_resume_skipped reason=all_chapters_fresh", logged)
            self.assertIn("draft_complete", logged)
            self.assertEqual(chapter_path.read_text(encoding="utf-8"), "# Chapter 1\n\nShort body.\n")

    def test_build_config_supports_full_review_provider_override(self) -> None:
        argv = [
            "runner.py",
            "--premise",
            "A grifter inherits a bankrupt weather station.",
            "--run-dir",
            "/tmp/full_review_override",
            "--provider",
            "codex",
            "--review-provider",
            "codex",
            "--full-review-provider",
            "claude",
        ]
        with mock.patch.object(sys, "argv", argv):
            args = runner_module.parse_args()
        cfg = runner_module.build_config(REPO_ROOT, args)
        self.assertEqual(cfg.stage_profiles["review"].provider, "codex")
        self.assertEqual(cfg.stage_profiles["full_review"].provider, "claude")
        self.assertEqual(cfg.stage_profiles["full_review"].model, "claude-opus-4-6")
        self.assertEqual(cfg.stage_profiles["full_review"].reasoning_effort, "max")

    def test_build_config_supports_stage_specific_provider_overrides(self) -> None:
        argv = [
            "runner.py",
            "--premise",
            "A grifter inherits a bankrupt weather station.",
            "--run-dir",
            "/tmp/stage_specific_provider_overrides",
            "--provider",
            "codex",
            "--outline-provider",
            "codex",
            "--outline-revision-provider",
            "claude",
            "--cross-chapter-audit-provider",
            "claude",
            "--local-window-audit-provider",
            "codex",
            "--revision-provider",
            "codex",
            "--aggregation-provider",
            "claude",
        ]
        with mock.patch.object(sys, "argv", argv):
            args = runner_module.parse_args()
        cfg = runner_module.build_config(REPO_ROOT, args)
        self.assertEqual(cfg.stage_profiles["outline"].provider, "codex")
        self.assertEqual(cfg.stage_profiles["outline_revision"].provider, "claude")
        self.assertEqual(cfg.stage_profiles["cross_chapter_audit"].provider, "claude")
        self.assertEqual(cfg.stage_profiles["local_window_audit"].provider, "codex")
        self.assertEqual(cfg.stage_profiles["revision"].provider, "codex")
        self.assertEqual(cfg.stage_profiles["llm_aggregator"].provider, "claude")

    def test_build_config_supports_skip_cross_chapter_audit_flag(self) -> None:
        argv = [
            "runner.py",
            "--premise",
            "A grifter inherits a bankrupt weather station.",
            "--run-dir",
            "/tmp/skip_cross_audit",
            "--provider",
            "codex",
            "--skip-cross-chapter-audit",
        ]
        with mock.patch.object(sys, "argv", argv):
            args = runner_module.parse_args()
        cfg = runner_module.build_config(REPO_ROOT, args)
        self.assertTrue(cfg.skip_cross_chapter_audit)
        self.assertEqual(cfg.stage_profiles["cross_chapter_audit"].provider, "codex")

    def test_build_config_supports_local_window_flags(self) -> None:
        argv = [
            "runner.py",
            "--premise",
            "A grifter inherits a bankrupt weather station.",
            "--run-dir",
            "/tmp/local_window_flags",
            "--provider",
            "codex",
            "--skip-local-window-audit",
            "--require-local-window-for-revision",
            "--local-window-size",
            "5",
            "--local-window-overlap",
            "1",
        ]
        with mock.patch.object(sys, "argv", argv):
            args = runner_module.parse_args()
        cfg = runner_module.build_config(REPO_ROOT, args)
        self.assertTrue(cfg.skip_local_window_audit)
        self.assertTrue(cfg.require_local_window_for_revision)
        self.assertEqual(cfg.local_window_size, 5)
        self.assertEqual(cfg.local_window_overlap, 1)

    def test_build_config_supports_final_cycle_global_only_flags(self) -> None:
        argv = [
            "runner.py",
            "--premise",
            "A grifter inherits a bankrupt weather station.",
            "--run-dir",
            "/tmp/final_cycle_global_only_flags",
        ]
        with mock.patch.object(sys, "argv", argv):
            args = runner_module.parse_args()
        cfg = runner_module.build_config(REPO_ROOT, args)
        self.assertTrue(cfg.final_cycle_global_only)

        argv = [
            "runner.py",
            "--premise",
            "A grifter inherits a bankrupt weather station.",
            "--run-dir",
            "/tmp/final_cycle_global_only_flags_off",
            "--no-final-cycle-global-only",
        ]
        with mock.patch.object(sys, "argv", argv):
            args = runner_module.parse_args()
        cfg = runner_module.build_config(REPO_ROOT, args)
        self.assertFalse(cfg.final_cycle_global_only)

    def test_build_config_supports_add_cycles_against_completed_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_add_cycles_cfg_", dir="/tmp") as tmp:
            run_dir = Path(tmp)
            (run_dir / "reports").mkdir(parents=True, exist_ok=True)
            (run_dir / "reports" / "final_status.json").write_text(
                json.dumps({"status": "PASS", "success_cycle": 2}) + "\n",
                encoding="utf-8",
            )
            argv = [
                "runner.py",
                "--premise",
                "A grifter inherits a bankrupt weather station.",
                "--run-dir",
                str(run_dir),
                "--add-cycles",
                "1",
            ]
            with mock.patch.object(sys, "argv", argv):
                args = runner_module.parse_args()
            cfg = runner_module.build_config(REPO_ROOT, args)
            self.assertEqual(cfg.add_cycles, 1)
            self.assertEqual(cfg.base_completed_cycles, 2)
            self.assertEqual(cfg.max_cycles, 3)

    def test_build_config_rejects_add_cycles_without_completed_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_add_cycles_missing_", dir="/tmp") as tmp:
            argv = [
                "runner.py",
                "--premise",
                "A grifter inherits a bankrupt weather station.",
                "--run-dir",
                tmp,
                "--add-cycles",
                "1",
            ]
            with mock.patch.object(sys, "argv", argv):
                args = runner_module.parse_args()
            with self.assertRaisesRegex(
                runner_module.PipelineError,
                "--add-cycles requires reports/final_status.json",
            ):
                runner_module.build_config(REPO_ROOT, args)

    def test_build_config_rejects_add_cycles_when_total_max_cycles_falls_below_min_cycles(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_add_cycles_minmax_", dir="/tmp") as tmp:
            run_dir = Path(tmp)
            (run_dir / "reports").mkdir(parents=True, exist_ok=True)
            (run_dir / "reports" / "final_status.json").write_text(
                json.dumps({"status": "PASS", "success_cycle": 2}) + "\n",
                encoding="utf-8",
            )
            argv = [
                "runner.py",
                "--premise",
                "A grifter inherits a bankrupt weather station.",
                "--run-dir",
                str(run_dir),
                "--add-cycles",
                "1",
                "--max-cycles",
                "99",
                "--min-cycles",
                "5",
            ]
            with mock.patch.object(sys, "argv", argv):
                args = runner_module.parse_args()
            with self.assertRaisesRegex(
                runner_module.PipelineError,
                "total --max-cycles smaller than --min-cycles",
            ):
                runner_module.build_config(REPO_ROOT, args)

    def test_build_config_rejects_invalid_local_window_layout(self) -> None:
        argv = [
            "runner.py",
            "--premise",
            "A grifter inherits a bankrupt weather station.",
            "--run-dir",
            "/tmp/local_window_invalid",
            "--local-window-size",
            "3",
            "--local-window-overlap",
            "3",
        ]
        with mock.patch.object(sys, "argv", argv):
            args = runner_module.parse_args()
        with self.assertRaisesRegex(
            runner_module.PipelineError,
            "--local-window-overlap must be smaller than --local-window-size",
        ):
            runner_module.build_config(REPO_ROOT, args)

    def test_build_config_supports_outline_review_flags(self) -> None:
        argv = [
            "runner.py",
            "--premise",
            "A grifter inherits a bankrupt weather station.",
            "--run-dir",
            "/tmp/outline_review_flags",
            "--provider",
            "codex",
            "--outline-review-cycles",
            "2",
            "--skip-outline-review",
        ]
        with mock.patch.object(sys, "argv", argv):
            args = runner_module.parse_args()
        cfg = runner_module.build_config(REPO_ROOT, args)
        self.assertEqual(cfg.outline_review_cycles, 2)
        self.assertTrue(cfg.skip_outline_review)

    def test_stage_specific_provider_overrides_apply_to_target_jobs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_stage_provider_jobs_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            codex_profile = runner_module.ExecutionProfile(
                provider="codex",
                agent_bin="codex",
                model="gpt-5.4",
                reasoning_effort="xhigh",
            )
            claude_profile = runner_module.ExecutionProfile(
                provider="claude",
                agent_bin="claude",
                model="claude-opus-4-6",
                reasoning_effort="max",
            )
            stage_profiles = {
                stage_group: codex_profile
                for stage_group in runner_module.STAGE_GROUP_VALUES
            }
            stage_profiles["outline_revision"] = claude_profile
            stage_profiles["cross_chapter_audit"] = claude_profile
            stage_profiles["local_window_audit"] = codex_profile
            stage_profiles["llm_aggregator"] = claude_profile
            runner.cfg = dataclasses.replace(
                runner.cfg,
                provider="codex",
                agent_bin="codex",
                model="gpt-5.4",
                reasoning_effort="xhigh",
                stage_profiles=stage_profiles,
            )
            runner._prepare_run_dir()
            run_dir = runner.cfg.run_dir
            (run_dir / "outline" / "continuity_sheet.json").write_text(
                "{}\n",
                encoding="utf-8",
            )
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id=f"chapter_{idx:02d}",
                    chapter_number=idx,
                    projected_min_words=1,
                    chapter_engine="discovery",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
                for idx in range(1, 5)
            ]

            outline_review_job = runner._build_outline_review_job(1)
            outline_revision_job = runner._build_outline_revision_job(
                1, "outline/outline_review_cycle_01.json"
            )
            cross_job = runner._build_cross_chapter_audit_job(1)
            local_window_job = runner._build_local_window_audit_job(
                1,
                ["chapter_01", "chapter_02", "chapter_03", "chapter_04"],
                {
                    f"chapter_{idx:02d}": {"start_line": idx, "end_line": idx + 10}
                    for idx in range(1, 5)
                },
            )
            aggregator_job = runner._build_revision_aggregator_job(1)
            revision_job = runner._make_job(
                job_id="revision_base_job",
                stage="chapter_revision",
                stage_group="revision",
                cycle=1,
                chapter_id="chapter_01",
                allowed_inputs=[],
                required_outputs=[],
                prompt_text="test",
            )

            self.assertEqual(outline_review_job.provider, "codex")
            self.assertEqual(outline_revision_job.provider, "claude")
            self.assertEqual(cross_job.provider, "claude")
            self.assertEqual(local_window_job.provider, "codex")
            self.assertEqual(aggregator_job.provider, "claude")
            self.assertEqual(revision_job.provider, "codex")

    def test_full_book_review_jobs_include_spatial_layout_input(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_full_book_layout_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner._prepare_run_dir()
            run_dir = runner.cfg.run_dir
            (run_dir / "outline" / "continuity_sheet.json").write_text("{}\n", encoding="utf-8")

            full_award_job = runner._build_full_award_review_job(1)
            cross_job = runner._build_cross_chapter_audit_job(1)

            self.assertIn("outline/spatial_layout.json", full_award_job.allowed_inputs)
            self.assertIn("outline/spatial_layout.json", cross_job.allowed_inputs)
            self.assertIn("outline/spatial_layout.json", full_award_job.prompt_text)
            self.assertIn("outline/spatial_layout.json", cross_job.prompt_text)

    def test_local_window_layout_uses_configured_size_and_overlap(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_local_window_layout_cfg_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.cfg = dataclasses.replace(
                runner.cfg,
                local_window_size=3,
                local_window_overlap=1,
            )
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id=f"chapter_{idx:02d}",
                    chapter_number=idx,
                    projected_min_words=1,
                    chapter_engine="engine",
                    pressure_source="pressure",
                    state_shift="shift",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["beat"],
                )
                for idx in range(1, 7)
            ]

            self.assertEqual(
                runner._window_id_for_chapters(
                    ["chapter_03", "chapter_04", "chapter_05"]
                ),
                "window_02",
            )

    def test_extracts_claude_result_and_last_message(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_claude_parse_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            log_path = Path(tmp) / "claude.jsonl"
            log_path.write_text(CLAUDE_STREAM_JSON, encoding="utf-8")
            events = runner._load_provider_events(log_path)
            result_event = runner._extract_claude_result_event(events)
            last_message = runner._extract_claude_last_message_text(events)
            usage = runner._extract_claude_usage(events)
            self.assertFalse(result_event["is_error"])
            self.assertEqual(result_event["result"], "OK")
            self.assertEqual(last_message, "OK")
            self.assertEqual(usage["input_tokens"], 2)
            self.assertEqual(usage["cache_creation_input_tokens"], 8304)
            self.assertEqual(usage["cache_read_input_tokens"], 6371)
            self.assertEqual(usage["output_tokens"], 4)

    def test_builds_claude_exec_command(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_claude_cmd_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            job = runner_module.JobSpec(
                job_id="cmd_test",
                stage="outline",
                stage_group="outline",
                cycle=0,
                chapter_id=None,
                allowed_inputs=[],
                required_outputs=[],
                prompt_text="test",
                provider="claude",
                agent_bin="claude",
                model="claude-opus-4-6",
                reasoning_effort="max",
            )
            cmd = runner._build_claude_exec_cmd(job)
            self.assertEqual(cmd[0], "claude")
            self.assertIn("-p", cmd)
            self.assertIn("--output-format", cmd)
            self.assertIn("stream-json", cmd)
            self.assertIn("--verbose", cmd)
            self.assertIn("--no-session-persistence", cmd)
            self.assertIn("--dangerously-skip-permissions", cmd)
            self.assertIn("--model", cmd)
            self.assertIn("claude-opus-4-6", cmd)
            self.assertIn("--effort", cmd)
            self.assertIn("max", cmd)

    def test_resolve_agent_bin_falls_back_to_codex_app_bundle(self) -> None:
        def fake_isfile(path: str) -> bool:
            return path == "/Applications/Codex.app/Contents/Resources/codex"

        with mock.patch.object(runner_module.shutil, "which", return_value=None), mock.patch.object(
            runner_module.os.path,
            "isfile",
            side_effect=fake_isfile,
        ):
            resolved = runner_module._resolve_agent_bin(
                "codex",
                "",
                allow_shared_overrides=False,
            )

        self.assertEqual(
            resolved,
            "/Applications/Codex.app/Contents/Resources/codex",
        )

    def test_extracts_quota_pause_from_rejected_rate_limit_event(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_claude_quota_parse_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            log_path = Path(tmp) / "claude_quota.jsonl"
            log_path.write_text(CLAUDE_RATE_LIMIT_STREAM_JSON, encoding="utf-8")
            events = runner._load_provider_events(log_path)
            with mock.patch.object(runner_module.time, "time", return_value=1999999900):
                with mock.patch.object(runner_module.random, "randint", return_value=17):
                    pause = runner._claude_quota_pause_from_events(
                        events, "You've hit your limit · resets 12am (America/New_York)"
                    )
            self.assertIsNotNone(pause)
            assert pause is not None
            self.assertEqual(pause.provider, "claude")
            self.assertEqual(pause.reset_at_epoch, 2000000000)
            self.assertEqual(pause.rate_limit_type, "five_hour")
            self.assertEqual(pause.sleep_seconds, 100 + 120 + 17)

    def test_run_job_waits_for_quota_reset_and_retries(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_claude_quota_retry_", dir="/tmp") as tmp:
            run_dir = Path(tmp)
            (run_dir / "workspaces").mkdir(parents=True, exist_ok=True)
            runner = make_runner(run_dir)
            runner.cfg = runner_module.RunnerConfig(
                premise=runner.cfg.premise,
                premise_mode=runner.cfg.premise_mode,
                premise_brief=runner.cfg.premise_brief,
                award_profile=runner.cfg.award_profile,
                premise_seed=runner.cfg.premise_seed,
                premise_reroll_max=runner.cfg.premise_reroll_max,
                premise_candidate_count=runner.cfg.premise_candidate_count,
                premise_generation_batch_size=runner.cfg.premise_generation_batch_size,
                premise_min_unique_clusters=runner.cfg.premise_min_unique_clusters,
                premise_shortlist_size=runner.cfg.premise_shortlist_size,
                run_dir=run_dir,
                max_cycles=runner.cfg.max_cycles,
                min_cycles=runner.cfg.min_cycles,
                max_parallel_drafts=runner.cfg.max_parallel_drafts,
                max_parallel_reviews=runner.cfg.max_parallel_reviews,
                max_parallel_revisions=runner.cfg.max_parallel_revisions,
                provider="claude",
                agent_bin="claude",
                model="claude-opus-4-6",
                reasoning_effort="max",
                stage_profiles=runner.cfg.stage_profiles,
                revision_pass_profiles=runner.cfg.revision_pass_profiles,
                dry_run=False,
                dry_run_chapter_count=runner.cfg.dry_run_chapter_count,
                job_timeout_seconds=runner.cfg.job_timeout_seconds,
                job_idle_timeout_seconds=runner.cfg.job_idle_timeout_seconds,
                validation_mode=runner.cfg.validation_mode,
            )
            attempts = {"count": 0}

            def fake_execute(_job: runner_module.JobSpec, _workspace: Path) -> None:
                attempts["count"] += 1
                if attempts["count"] == 1:
                    raise runner_module.ProviderQuotaPause(
                        provider="claude",
                        result_text="You've hit your limit · resets 12am (America/New_York)",
                        reset_at_epoch=2000000000,
                        sleep_seconds=137,
                        rate_limit_type="five_hour",
                    )

            runner._copy_inputs_to_workspace = lambda allowed, workspace: {}
            runner._execute_agent_job = fake_execute
            runner._validate_job_workspace = lambda job, workspace, before_hashes: None
            runner._copy_outputs_from_workspace = lambda job, workspace: None

            job = runner_module.JobSpec(
                job_id="quota_retry_job",
                stage="chapter_review",
                stage_group="review",
                cycle=1,
                chapter_id="chapter_01",
                allowed_inputs=[],
                required_outputs=[],
                prompt_text="test prompt",
                provider="claude",
                agent_bin="claude",
                model="claude-opus-4-6",
                reasoning_effort="max",
            )
            with mock.patch.object(runner_module.time, "sleep") as sleep_mock:
                runner._run_job(job)
            self.assertEqual(attempts["count"], 2)
            sleep_mock.assert_called_once_with(137)

    def test_make_job_uses_revision_pass_profile_override(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_revision_profile_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            codex_profile = runner_module.ExecutionProfile(
                provider="codex",
                agent_bin="codex",
                model="gpt-5.4",
                reasoning_effort="xhigh",
            )
            claude_profile = runner_module.ExecutionProfile(
                provider="claude",
                agent_bin="claude",
                model="claude-opus-4-6",
                reasoning_effort="max",
            )
            runner.cfg = runner_module.RunnerConfig(
                premise=runner.cfg.premise,
                premise_mode=runner.cfg.premise_mode,
                premise_brief=runner.cfg.premise_brief,
                award_profile=runner.cfg.award_profile,
                premise_seed=runner.cfg.premise_seed,
                premise_reroll_max=runner.cfg.premise_reroll_max,
                premise_candidate_count=runner.cfg.premise_candidate_count,
                premise_generation_batch_size=runner.cfg.premise_generation_batch_size,
                premise_min_unique_clusters=runner.cfg.premise_min_unique_clusters,
                premise_shortlist_size=runner.cfg.premise_shortlist_size,
                run_dir=runner.cfg.run_dir,
                max_cycles=runner.cfg.max_cycles,
                min_cycles=runner.cfg.min_cycles,
                max_parallel_drafts=runner.cfg.max_parallel_drafts,
                max_parallel_reviews=runner.cfg.max_parallel_reviews,
                max_parallel_revisions=runner.cfg.max_parallel_revisions,
                provider="codex",
                agent_bin="codex",
                model="gpt-5.4",
                reasoning_effort="xhigh",
                stage_profiles={
                    stage_group: codex_profile
                    for stage_group in runner_module.STAGE_GROUP_VALUES
                },
                revision_pass_profiles={
                    runner_module.REVISION_DIALOGUE_PASS_KEY: claude_profile
                },
                dry_run=True,
                dry_run_chapter_count=runner.cfg.dry_run_chapter_count,
                job_timeout_seconds=runner.cfg.job_timeout_seconds,
                job_idle_timeout_seconds=runner.cfg.job_idle_timeout_seconds,
                validation_mode=runner.cfg.validation_mode,
            )
            p1_job = runner._make_job(
                job_id="p1",
                stage="chapter_revision",
                stage_group="revision",
                revision_pass_key="p1_structural_craft",
                cycle=1,
                chapter_id="chapter_01",
                allowed_inputs=[],
                required_outputs=[],
                prompt_text="test",
            )
            p2_job = runner._make_job(
                job_id="p2",
                stage="chapter_revision",
                stage_group="revision",
                revision_pass_key=runner_module.REVISION_DIALOGUE_PASS_KEY,
                cycle=1,
                chapter_id="chapter_01",
                allowed_inputs=[],
                required_outputs=[],
                prompt_text="test",
            )
            self.assertEqual(p1_job.provider, "codex")
            self.assertEqual(p1_job.model, "gpt-5.4")
            self.assertEqual(p2_job.provider, "claude")
            self.assertEqual(p2_job.model, "claude-opus-4-6")


if __name__ == "__main__":
    unittest.main()
