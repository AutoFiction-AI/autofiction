# Contracts

## Stage Graph

Generated-premise mode:

1. `premise_search_plan`
2. `premise_candidates` (batched)
3. `premise_uniqueness_clustering`
4. `premise_random_selection`
5. `outline`
6. `draft_chapters`
7. `assemble_snapshot`
8. `build_cycle_context_packs`
9. `review_chapters`
10. `scene_consistency_audit`
11. `dialogue_diagnostic`
12. `full_award_review`
13. `cross_chapter_audit`
14. `local_window_audit`
15. `cold_reader_pass`
16. `plot_architecture_audit`
17. `character_arc_audit`
18. `ending_audit`
19. `prose_distinctiveness_audit`
20. `theme_coherence_audit`
21. `aggregate_findings`
22. `gate`
23. If gate fails: `build_revision_packets`
24. `revise_chapters_pass_1`
25. `revise_chapters_pass_2`
26. `revise_chapters_pass_3`
27. `merge_revision_reports`
28. `seam_polish`
29. `assemble_post_revision_snapshot`
30. `continuity_reconciliation`

Stages 10–20 (per-chapter and whole-book audits beyond `full_award_review`) all flow findings into `aggregate_findings` and through the same gate. Each is independently skippable via `--skip-<stage>` flags.

User-premise mode starts at `outline`.

## Worker Isolation Contract

Every LLM job runs from a manifest with:

- `job_id`
- `stage`
- `stage_group`
- `cycle`
- `chapter_id` when applicable
- `provider`
- `agent_bin`
- `model`
- `reasoning_effort`
- `allowed_inputs`
- `required_outputs`
- `prompt_text`

Rules:

1. Each job gets its own temporary workspace.
2. Only declared inputs are copied in.
3. Only declared outputs are copied back.
4. Undeclared input mutation is treated as a job failure.

## Provider Contract

- Provider selection changes only the job executor, CLI invocation, and log/cost parsing.
- Artifact contracts are identical across providers.
- Current supported providers:
  - `codex`
  - `claude`
- Default execution settings:
  - Codex: `gpt-5.5` with `xhigh`
  - Claude: `claude-opus-4-7` with `max`
- Optional stage-group overrides can mix providers within one run:
  - `premise`
  - `outline`
  - `draft`
  - `review`
  - `full_review`
  - `revision`
- The dialogue revision pass can also be overridden independently of the other revision passes via `--revision-dialogue-provider`.
- In the main pipeline, the cross-chapter audit currently follows the `full_review` provider profile.

## Prompt Set

Active prompts:

- `prompts/constitution.md`
- `prompts/premise_candidates_prompt.md`
- `prompts/premise_uniqueness_clustering_prompt.md`
- `prompts/outline_prompt.md`
- `prompts/chapter_draft_prompt.md`
- `prompts/chapter_review_prompt.md`
- `prompts/chapter_revision_prompt.md`
- `prompts/chapter_seam_polish_prompt.md`
- `prompts/full_award_review_prompt.md`
- `prompts/cross_chapter_audit_prompt.md`
- `prompts/local_window_audit_prompt.md`
- `prompts/scene_consistency_audit_prompt.md`
- `prompts/dialogue_diagnostic_prompt.md`
- `prompts/cold_reader_pass_prompt.md`
- `prompts/plot_architecture_audit_prompt.md`
- `prompts/character_arc_audit_prompt.md`
- `prompts/ending_audit_prompt.md`
- `prompts/prose_distinctiveness_audit_prompt.md`
- `prompts/theme_coherence_audit_prompt.md`
- `prompts/continuity_sheet_prompt.md`

Reference material wired into prompts at render time:

- `dialogue_samples/*.txt` — calibration-only samples (one prose excerpt + nine reference notes on writers in lithub's "10 short stories with great dialogue" set). Inlined into `chapter_draft_prompt.md`, `chapter_review_prompt.md`, `chapter_revision_prompt.md`, and `dialogue_diagnostic_prompt.md` via the `{{DIALOGUE_SAMPLES_BLOCK}}` placeholder in deterministic shuffled order per run. Copied into `config/dialogue_samples/` in each run for reproducibility.

## Core Artifacts

### Premise Search

- `premise/premise_search_plan.json`
- `premise/premise_candidates.jsonl`
- `premise/uniqueness_clusters.json`
- `premise/selection.json`
- `premise/premise_brainstorming.md`
- `input/premise.txt`

### Outline

- `outline/outline.md`
- `outline/outline.md` must include `Middle-Book Progression Map`, `Supporting Character Pressure Map`, and `Reader Knowledge Plan`
- `outline/chapter_specs.jsonl`
- `outline/chapter_specs.jsonl` may include per-chapter `reader_introductions` objects for concept onboarding/refresh
- `outline/scene_plan.tsv`
- `outline/style_bible.json`
- `outline/style_bible.json` `prose_style_profile` must include `exposition_density_policy`
- `outline/static_story_context.json`
- `outline/continuity_sheet.json`

### Cycles

For each cycle `XX`:

- `snapshots/cycle_XX/`
- `context/cycle_XX/`
- `reviews/cycle_XX/`
- `findings/cycle_XX/`
- `packets/cycle_XX/`
- `revisions/cycle_XX/`
- `gate/cycle_XX/gate.json`

### Review Outputs

- `reviews/cycle_XX/chapter_*.review.json`
- `reviews/cycle_XX/full_award.review.json`
- `reviews/cycle_XX/cross_chapter_audit.json`
- `reviews/cycle_XX/local_window_*.json`
- `reviews/cycle_XX/chapter_*.scene_consistency.json`
- `reviews/cycle_XX/chapter_*.dialogue_diagnostic.json`
- `reviews/cycle_XX/cold_reader.review.json`
- `reviews/cycle_XX/plot_architecture.review.json`
- `reviews/cycle_XX/character_arc_*.review.json`
- `reviews/cycle_XX/ending_audit.review.json`
- `reviews/cycle_XX/prose_distinctiveness.review.json`
- `reviews/cycle_XX/theme_coherence.review.json`

## Output Schemas

- `schemas/chapter_review.schema.json`
- `schemas/full_award_review.schema.json`
- `schemas/cross_chapter_audit.schema.json`
- `schemas/local_window_audit.schema.json`
- `schemas/scene_consistency_audit.schema.json`
- `schemas/dialogue_diagnostic.schema.json`
- `schemas/cold_reader_pass.schema.json`
- `schemas/plot_architecture_audit.schema.json`
- `schemas/character_arc_audit.schema.json`
- `schemas/ending_audit.schema.json`
- `schemas/prose_distinctiveness_audit.schema.json`
- `schemas/theme_coherence_audit.schema.json`
- `schemas/revision_packet.schema.json`
- `schemas/gate.schema.json`
- `schemas/style_bible.schema.json`

## Review Contract

Chapter review output:

- top-level `chapter_id`
- `verdicts` with keys `award`, `craft`, `dialogue`, `prose`
- `findings`
- `summary`

Full-book review output:

- top-level `cycle`
- `verdict`
- `summary`
- `findings`
- optional `pattern_findings`

Cross-chapter audit output:

- top-level `cycle`
- `summary`
- `not_x_y_count`
- `personified_abstraction_count`
- `abstract_noun_subject_count`
- `simile_count`
- `as_if_count`
- `the_way_x_count`
- `redundancy_findings`
- `consistency_findings`

Scene consistency audit output (per chapter, forensic within-scene contradiction enumeration):

- top-level `chapter_id`
- `cycle`
- `scenes_indexed` — array of scene ids the audit walked
- `summary`
- `findings` — each finding has `finding_id`, `subcategory` (one of `commonsense_physical`, `prop_state_local`, `blocking_contradiction`, `light_environment`, `time_within_scene`, `knowledge_state_local`, `emotional_continuity_local`, `action_decision_local`, `description_contradiction_local`, `social_action_coherence`, `dialogue_internal_coherence`), `severity`, `chapter_id`, `scene_id`, `evidence` (must cite the two contradicting lines), `problem`, `rewrite_direction`, `acceptance_test`, `pass_hint`. Findings are exhaustive — one per distinct contradiction; consolidation is forbidden by the prompt.

Dialogue diagnostic output (per chapter, forensic dialogue checklist):

- top-level `chapter_id`
- `cycle`
- `exchanges_indexed` — array of exchange ids the audit walked
- `summary`
- `findings` — each finding has `finding_id`, `subcategory` (one of `dialogue_does_no_work`, `interchangeable_voices`, `ceremonial_register_overapplied`, `narrator_paraphrase_dialogue_patch`, `affirmative_volley`, `adverbial_tag_or_telling_tag`, `scene_stake_unregistered`), `severity`, `chapter_id`, `exchange_id`, `evidence`, `problem`, `rewrite_direction`, `acceptance_test`, `pass_hint`. Findings are exhaustive — one per distinct failure; consolidation is forbidden by the prompt.

Cold-reader pass output (whole book, no planning artifacts; reader-experience report):

- top-level `cycle`
- `verdict` (`PASS|FAIL`)
- `summary`
- `observations` — required fields: `opening_engagement`, `drag_points`, `confusion_points`, `bookmark_failures`, `who_you_cared_about`, `central_question_legibility`, `ending_earned`, `emotional_landings`, `things_you_remember`, `would_you_recommend`, `genre_mode_recognized`, `character_function_vs_person`. The reviewer may not omit any field — if there is nothing to report, the field must say so explicitly.
- `findings` — observation-derived issues with `observation_key` keyed to the observation that produced them. Findings use plain reader language, not editorial vocabulary.

Plot architecture audit output (whole book):

- top-level `cycle`
- `verdict`
- `summary`
- `architecture_map` — `inciting_disturbance_location`, `midpoint_location`, `climax_location`, `denouement_span`, `central_dramatic_question`, `load_bearing_scenes` (with `judgment` ∈ {`strong`, `adequate`, `weak`}), `subplots` (with `convergence_status` ∈ {`converged`, `parallel`, `fizzled`}).
- `findings` — categories include `opening_promise`, `inciting_disturbance`, `rising_action_curve`, `midpoint_load_bearing`, `subplot_convergence`, `climax_placement_and_energy`, `denouement_length`, `load_bearing_scenes`, `cuttable_chapters`, `tell_dont_show_at_structure`, `intent_vs_manuscript_divergence`, `escalation_vs_repetition`.

Character arc audit output (per character; one job per `character_voice_profiles` entry):

- top-level `character_id`
- `cycle`
- `verdict`
- `summary`
- `arc_map` — `entry_state`, `exit_state`, `arc_threshold_crossed` (boolean), `pivot_chapters`, `signature_lines`, `relationship_geometries`.
- `findings` — categories include `entry_state`, `exit_state`, `arc_legibility`, `irreversibility`, `change_earned_on_page`, `pressure_distribution_across_book`, `unique_register`, `presence_continuity`, `relationship_geometries`, `function_vs_person`, `voice_profile_fidelity`, `decision_under_pressure`. Each finding carries a `character_id` field that must equal the audited character.

Ending audit output (whole book, focused on the last `ending_tail_chapters` chapters; default 4):

- top-level `cycle`
- `verdict`
- `summary`
- `ending_map` — `climax_location`, `denouement_span`, `closing_threads` (with `status` ∈ {`closed_on_page`, `closed_by_summary`, `left_open_by_design`, `fizzled`}), `last_image_summary`, `last_line_quoted`, `epilogue_present`.
- `findings` — categories include `climax_charge`, `thread_inventory`, `wrong_threads_closed`, `denouement_length`, `ending_earned_by_investment`, `last_image`, `last_paragraph`, `last_line`, `unprepared_arrivals`, `ending_register_match`, `epilogue_or_coda_audit`, `relief_vs_resolution`, `would_a_reader_underline_anything_here`.

Prose distinctiveness audit output (whole book):

- top-level `cycle`
- `verdict`
- `summary`
- `voice_map` — `signature_moves`, `quotable_passages` (≥3 expected), `averaged_register_spans`, `pov_voice_assessment`, `the_blind_test_judgment`.
- `findings` — categories include `signature_moves`, `averaged_literary_register_drift`, `paragraph_pickability_test`, `sentence_rhythm_diversity`, `image_economy`, `stylistic_risk_taken`, `transparent_prose_done_well`, `metaphor_originality`, `voice_consistency_across_pov`, `quotability_test`, `the_blind_test`, `default_LLM_prose_signature_check`. The pipeline catches over-distinctive tics in the cross-chapter audit; this stage catches under-distinctiveness — averaged literary register that nothing else flags.

Theme coherence audit output (whole book):

- top-level `cycle`
- `verdict`
- `summary`
- `theme_map` — `central_question`, `what_book_has_to_say`, `recurring_motifs` (with `judgment` ∈ {`load_bearing`, `decorative`}), `paid_for_at`, `evasion_locations`, `one_paragraph_summary`.
- `findings` — categories include `central_question`, `engagement_with_question`, `recurring_image_audit`, `motif_payoff`, `idea_tested_through_character_cost`, `evasion_pattern`, `thematic_register_match`, `thesis_speech_failure`, `narrator_thematic_underlining`, `what_book_has_to_say`, `would_a_reader_argue_with_it`, `the_one_paragraph_summary_test`.

Gate output:

- `cycle`
- `full_award_verdict`
- `unresolved_medium_plus_count`
- `chapter_review_failures`
- `decision`
- `reason`

## Gate Rule

A cycle passes only if:

1. `full_award_verdict == "PASS"`
2. unresolved `MEDIUM+` findings count is `0`
3. chapter review failures count is `0`
4. cycle index is at least `min_cycles`

Otherwise the pipeline builds revision packets and runs another revision cycle.

## Resume Rules

- Existing artifacts are reused only if they validate and are fresh against their inputs.
- Generated-premise resumes validate premise-search seed, shortlist draw, and selected premise consistency.
