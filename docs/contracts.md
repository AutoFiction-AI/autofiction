# Contracts

## Stage Graph

Generated-premise mode:

1. `premise_search_plan`
2. `premise_candidates` (batched)
3. `premise_uniqueness_clustering`
4. `premise_random_selection`
5. `outline`
6. `draft_chapters`
7. `draft_expand_retry`
8. `assemble_snapshot`
9. `build_cycle_context_packs`
10. `review_chapters`
11. `full_award_review`
12. `cross_chapter_audit`
13. `aggregate_findings`
14. `gate`
15. If gate fails: `build_revision_packets`
16. `revise_chapters_pass_1`
17. `revise_chapters_pass_2`
18. `revise_chapters_pass_3`
19. `merge_revision_reports`
20. `seam_polish`
21. `assemble_post_revision_snapshot`
22. `continuity_reconciliation`

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
  - Codex: `gpt-5.4` with `xhigh`
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
- `prompts/chapter_expand_prompt.md`
- `prompts/chapter_review_prompt.md`
- `prompts/chapter_revision_prompt.md`
- `prompts/chapter_seam_polish_prompt.md`
- `prompts/full_award_review_prompt.md`
- `prompts/cross_chapter_audit_prompt.md`
- `prompts/continuity_sheet_prompt.md`

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

## Output Schemas

- `schemas/chapter_review.schema.json`
- `schemas/full_award_review.schema.json`
- `schemas/cross_chapter_audit.schema.json`
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
