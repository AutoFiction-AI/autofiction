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
                "requires related_chapter_ids",
            ):
                runner._validate_local_window_audit_json(
                    missing_related,
                    1,
                    chapter_ids,
                    "reviews/cycle_01/local_window_01.json",
                    "snapshots/cycle_01/FINAL_NOVEL.md",
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

            self.assertTrue(review_path.is_file())
            self.assertTrue(revision_path.is_file())
            self.assertTrue(spatial_layout_path.is_file())
            self.assertTrue((run_dir / "outline" / "static_story_context.json").is_file())

            revision_payload = json.loads(revision_path.read_text(encoding="utf-8"))
            self.assertEqual(
                revision_payload["review_file"], "outline/outline_review_cycle_01.json"
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

    def test_seam_polish_job_receives_outline_and_continuity_inputs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_seam_inputs_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1000,
                    chapter_engine="discovery",
                    pressure_source="inspection pressure",
                    state_shift="Carmen leaves with a new suspicion.",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["Beat one", "Beat two", "Beat three"],
                    secondary_character_beats=["Let Harry's caution shade the exit."],
                ),
                runner_module.ChapterSpec(
                    chapter_id="chapter_02",
                    chapter_number=2,
                    projected_min_words=1000,
                    chapter_engine="discovery",
                    pressure_source="admin pressure",
                    state_shift="Carmen realizes the count is off.",
                    texture_mode="warm",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["Next beat"],
                ),
            ]

            run_dir = runner.cfg.run_dir
            (run_dir / "chapters").mkdir(parents=True, exist_ok=True)
            (run_dir / "outline").mkdir(parents=True, exist_ok=True)
            (run_dir / "config" / "prompts").mkdir(parents=True, exist_ok=True)
            (run_dir / "chapters" / "chapter_01.md").write_text(
                "# Chapter 1\n\nEnd beat.\n",
                encoding="utf-8",
            )
            (run_dir / "chapters" / "chapter_02.md").write_text(
                "# Chapter 2\n\nStart beat.\n",
                encoding="utf-8",
            )
            (run_dir / "outline" / "outline.md").write_text(
                "outline placeholder\n",
                encoding="utf-8",
            )
            (run_dir / "config" / "prompts" / "chapter_seam_polish_prompt.md").write_text(
                (REPO_ROOT / "prompts" / "chapter_seam_polish_prompt.md").read_text(
                    encoding="utf-8"
                ),
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

            captured_job_groups: list[tuple[str, list[runner_module.JobSpec]]] = []

            def capture_run_jobs_parallel(
                jobs: list[runner_module.JobSpec], _max_parallel: int, label: str
            ) -> None:
                captured_job_groups.append((label, list(jobs)))
                for job in jobs:
                    for output_rel in job.required_outputs:
                        if output_rel.endswith(".seam_report.json"):
                            output_path = run_dir / output_rel
                            output_path.parent.mkdir(parents=True, exist_ok=True)
                            output_path.write_text(
                                json.dumps(
                                    {
                                        "chapter_id": job.chapter_id,
                                        "seam_changes_made": "NO",
                                        "summary": "No seam edits needed.",
                                        "edits": [],
                                    }
                                )
                                + "\n",
                                encoding="utf-8",
                            )

            runner._run_jobs_parallel = capture_run_jobs_parallel

            runner._run_seam_polish_stage(1, ["chapter_01"])

            self.assertEqual(len(captured_job_groups), 1)
            seam_job = captured_job_groups[0][1][0]
            self.assertIn("outline/outline.md", seam_job.allowed_inputs)
            self.assertIn("context/cycle_01/continuity_sheet.json", seam_job.allowed_inputs)

            boundary_context = json.loads(
                (
                    run_dir
                    / "context"
                    / "cycle_01"
                    / "post_revision_boundary"
                    / "chapter_01.boundary.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(
                boundary_context["open_hooks_to_carry"],
                ["Beat one", "Beat two", "Beat three"],
            )
            self.assertEqual(
                boundary_context["secondary_character_beats"],
                ["Let Harry's caution shade the exit."],
            )

    def test_seam_polish_reruns_when_inputs_change_even_if_report_is_newer(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_seam_freshness_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            runner.chapter_specs = [
                runner_module.ChapterSpec(
                    chapter_id="chapter_01",
                    chapter_number=1,
                    projected_min_words=1000,
                    chapter_engine="discovery",
                    pressure_source="inspection pressure",
                    state_shift="Carmen leaves with a new suspicion.",
                    texture_mode="hot",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["Beat one"],
                ),
                runner_module.ChapterSpec(
                    chapter_id="chapter_02",
                    chapter_number=2,
                    projected_min_words=1000,
                    chapter_engine="discovery",
                    pressure_source="admin pressure",
                    state_shift="Carmen realizes the count is off.",
                    texture_mode="warm",
                    scene_count_target=2,
                    scene_count_target_explicit=True,
                    must_land_beats=["Next beat"],
                ),
            ]

            run_dir = runner.cfg.run_dir
            (run_dir / "chapters").mkdir(parents=True, exist_ok=True)
            (run_dir / "outline").mkdir(parents=True, exist_ok=True)
            (run_dir / "config" / "prompts").mkdir(parents=True, exist_ok=True)
            (run_dir / "revisions" / "cycle_01").mkdir(parents=True, exist_ok=True)
            (run_dir / "chapters" / "chapter_01.md").write_text(
                "# Chapter 1\n\nEnd beat.\n",
                encoding="utf-8",
            )
            (run_dir / "chapters" / "chapter_02.md").write_text(
                "# Chapter 2\n\nStart beat.\n",
                encoding="utf-8",
            )
            (run_dir / "outline" / "outline.md").write_text(
                "outline placeholder\n",
                encoding="utf-8",
            )
            (run_dir / "config" / "prompts" / "chapter_seam_polish_prompt.md").write_text(
                (REPO_ROOT / "prompts" / "chapter_seam_polish_prompt.md").read_text(
                    encoding="utf-8"
                ),
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
            seam_report_path = (
                run_dir / "revisions" / "cycle_01" / "chapter_01.seam_report.json"
            )
            seam_report_path.write_text(
                json.dumps(
                    {
                        "chapter_id": "chapter_01",
                        "seam_changes_made": "NO",
                        "summary": "No seam edits needed.",
                        "edits": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            runner._artifact_fresh_against_inputs = lambda *_args, **_kwargs: False

            captured_job_groups: list[tuple[str, list[runner_module.JobSpec]]] = []

            def capture_run_jobs_parallel(
                jobs: list[runner_module.JobSpec], _max_parallel: int, label: str
            ) -> None:
                captured_job_groups.append((label, list(jobs)))
                for job in jobs:
                    for output_rel in job.required_outputs:
                        if output_rel.endswith(".seam_report.json"):
                            output_path = run_dir / output_rel
                            output_path.parent.mkdir(parents=True, exist_ok=True)
                            output_path.write_text(
                                json.dumps(
                                    {
                                        "chapter_id": job.chapter_id,
                                        "seam_changes_made": "NO",
                                        "summary": "No seam edits needed.",
                                        "edits": [],
                                    }
                                )
                                + "\n",
                                encoding="utf-8",
                            )

            runner._run_jobs_parallel = capture_run_jobs_parallel

            runner._run_seam_polish_stage(1, ["chapter_01"])

            self.assertEqual(len(captured_job_groups), 1)
            self.assertEqual(captured_job_groups[0][1][0].stage, "chapter_seam_polish")

    def test_load_repaired_seam_report_normalizes_shape_and_synthesizes_summary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snp_seam_repair_", dir="/tmp") as tmp:
            runner = make_runner(Path(tmp))
            run_dir = runner.cfg.run_dir
            (run_dir / "revisions" / "cycle_01").mkdir(parents=True, exist_ok=True)
            seam_rel = "revisions/cycle_01/chapter_01.seam_report.json"
            (run_dir / seam_rel).write_text(
                json.dumps(
                    {
                        "chapter_id": "ch1",
                        "seam_changes_made": "yes",
                        "summary": "",
                        "edits": "Tightened the opening handoff.",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            repaired = runner._load_repaired_seam_report(seam_rel, "chapter_01")

            self.assertEqual(repaired["chapter_id"], "chapter_01")
            self.assertEqual(repaired["seam_changes_made"], "YES")
            self.assertEqual(repaired["edits"], ["Tightened the opening handoff."])
            self.assertTrue(repaired["summary"].strip())
            self.assertTrue(
                (
                    run_dir / "revisions" / "cycle_01" / "chapter_01.seam_report.invalid.original.json"
                ).is_file()
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
                "gate_passed_no_revision_needed",
            )
            self.assertEqual(payload["advisory_gate"]["decision"], "PASS")

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
                runner, "_write_gate", side_effect=gate_for_cycle
            ) as write_gate, mock.patch.object(
                runner, "_build_revision_packets"
            ) as build_packets, mock.patch.object(
                runner, "_run_revision_stage"
            ) as run_revision, mock.patch.object(
                runner, "_run_seam_polish_stage"
            ), mock.patch.object(
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
                "gate_passed_no_revision_needed",
            )
            self.assertEqual(cycle_two_status["cycle"], 2)

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
                "_run_revision_stage",
                return_value={
                    "status": "complete",
                    "chapter_count": 1,
                    "units": {},
                },
            ) as run_revision, mock.patch.object(
                runner,
                "_run_seam_polish_stage",
                return_value={
                    "status": "complete",
                    "chapter_count": 1,
                    "units": {},
                },
            ), mock.patch.object(
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
        ]
        with mock.patch.object(sys, "argv", argv):
            args = runner_module.parse_args()
        cfg = runner_module.build_config(REPO_ROOT, args)
        self.assertTrue(cfg.skip_local_window_audit)
        self.assertTrue(cfg.require_local_window_for_revision)

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
