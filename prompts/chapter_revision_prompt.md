You are running CHAPTER REVISION for `{{CHAPTER_ID}}`.
Current revision pass: `{{REVISION_PASS_LABEL}}`

Inputs:
1. Chapter source: `{{CHAPTER_INPUT_FILE}}`
2. Pass-scoped revision packet: `{{REVISION_PACKET_FILE}}`
3. Cycle story context pack: `{{GLOBAL_CYCLE_CONTEXT_FILE}}`
4. Boundary context pack: `{{CHAPTER_BOUNDARY_CONTEXT_FILE}}`
5. Style bible: `outline/style_bible.json`
6. Continuity sheet: `{{CONTINUITY_SHEET_FILE}}`
7. Constitution: `config/constitution.md`
{{OPTIONAL_ORIGINAL_SNAPSHOT_INPUT_LINE}}
{{DIALOGUE_ANCHOR_INPUT_LINE}}

Context isolation requirement:
1. Do not read prior cycle reviews or revision narratives.
2. Use only the inputs listed above for this stage (chapter source, revision packet, context packs, style bible, continuity sheet, and constitution).

Task:
1. Revise only `{{CHAPTER_INPUT_FILE}}`.
2. Address every finding in `{{REVISION_PACKET_FILE}}`.
2b. If a finding in `{{REVISION_PACKET_FILE}}` includes `locator_excerpts`, use those excerpted spans to locate the target passage in the current chapter before revising. Treat `locator_excerpts` as search aids and scene anchors, not as text to be copied back verbatim.
3. Pass focus: `{{REVISION_PASS_FOCUS}}`
3b. Revise locally by default for isolated prose, diction, dialogue-register, or continuity fixes. But when a finding concerns structure, pacing, repetition, scene purpose, convenience, late-arriving engine, or summary drift, you may cut, merge, reorder, replace, or substantially rewrite the affected scene(s). Do not preserve broken chapter architecture just to minimize diff size.
3c. When a finding concerns sprawl, overlength, or repeated thematic restatement, compress by removing duplicate work rather than merely polishing it. Preserve the chapter's engine, state shift, and must-land beats, but cut repeated diagnosis, second-pass emotional certification, paraphrased revelation, and explanatory summary that arrives after the reader already understands the point.
3d. Preferred compression order:
   - Remove narrator explanation that restates what action or dialogue has already made legible.
   - Cut back-to-back dialogue turns that arrive at the same conclusion in different wording.
   - Compress second or third examples that prove a fact the chapter has already proved once.
   - Merge adjacent beats with the same dramatic function.
3e. When a finding concerns structural recurrence, diagnosis-scene repetition, or a bridge scene that only explains prior action, do not merely shorten the same exchange. Replace some of that space with a better dramatic form: a concrete test, a failed attempt, a public witness, a newly costly silence, a changed ask between characters, an irreversible choice, or a consequence that forces the chapter to prove something new.
3f. If a repetitive scene cannot be made to do new work without distorting the chapter, compress it to a handoff and let the next consequential beat carry the chapter's movement instead.
3g. Prefer fixing recurrence by reweighting, reordering, or sharpening material already present in the chapter before inventing new external machinery, lore, logistics, or scene furniture. Add new material only when the existing chapter genuinely cannot supply the needed proof or consequence.
4. Preserve heading contract: first non-empty line must remain `# Chapter {{CHAPTER_NUMBER}}`.
5. Preserve continuity implied by chapter packet constraints while minimizing collateral churn.
5b. Use the story context pack to recover this chapter's planned engine, pressure source, state shift, must-land beats, and any tracked `setups_to_plant` or `payoffs_to_land` when deciding how far a fix may go. Treat that planning material as a guardrail, not an absolute override of what the manuscript has productively become. If a revision would create a different chapter-ending state or new downstream obligation, it is usually the wrong fix for this pass — unless the current chapter already clearly establishes that stronger state on the page and the packet's findings can only be solved by aligning with the manuscript's actual achieved shape rather than the stale plan.
5c. If this chapter is supposed to plant a tracked setup or land a tracked payoff, preserve or sharpen that obligation rather than accidentally cutting it for economy. When a packet flags underseeded payoff or missing groundwork, strengthen the intended seed or landing already associated with this chapter before inventing a different callback device.
6. Preserve character voice and dialogue signatures from `outline/style_bible.json`.
7. Preserve prose style profile and enforce aesthetic risk policy from `outline/style_bible.json`.
8. Keep voice cues non-mechanical: reduce repetitive recurrence of fixed lexical signatures and stress-tell phrasing.
9. Do not sanitize during revision. When a finding asks you to improve, restructure, or deepen a scene, that is never an instruction to soften, euphemize, or remove raw content. Revision should make difficult material land harder, not retreat from it. If the original draft renders violence, sexuality, addiction, profanity, or moral compromise with specificity, preserve or strengthen that specificity — do not sand it down. Fade-to-black, summary substitution, and moral safety valves introduced during revision are craft regressions.
10. When dialogue is meant to sound informal/pressured, allow contractions and colloquial cadence while still avoiding clipped omission of required function words.
11. When the revision packet includes continuity findings, use `{{CONTINUITY_SHEET_FILE}}` as the single source of truth. The sheet's canonical values override any conflicting detail in the current chapter text. Do not introduce new continuity contradictions while revising — check ages, dates, object states, and spatial details against the sheet before finalizing.
12. Preserve productive spoken roughness. Do not "finish" messy human speech into balanced, polished, over-explained lines unless a finding explicitly requires it. False starts, topic-slippage, evasion, repeated words, unfinished-but-legible turns, and socially awkward pivots are often part of the character's texture, not defects to be normalized away.
12b. When addressing em-dash-density findings, target descriptive, appositional, and expository em-dashes first. Preserve em-dashes that mark genuine interruption, self-correction, aborted phrasing, pressure fracture, or live conversational overlap unless the packet explicitly identifies those specific instances as a defect.
13. Do not introduce literary polish during revision. When rewriting dialogue to fix a finding, do not upgrade the line into something sharper, more compressed, more quotable, or more rhetorically satisfying than the original. If the original line was messy but alive, the revision should be messy and alive in a different way — not cleaned into a perfectly landed insight. Revision that replaces rough speech with well-crafted speech is a regression, not an improvement.
13b. Do not mistake quiet for padding. Meals, aftermath, ritual, domestic business, low-information conversation, and pauses are worth preserving when they alter the relationship field, deepen social texture, or make a later beat land harder. Cut only beats that perform the same dramatic function twice.
14. Do not add narrator commentary that admires a character's dialogue. If you find yourself writing that a line "landed," "cut the room," "silenced" someone, or that a character "said it the way she said things that needed saying," remove it. Let the line work on its own or not at all.
{{OPTIONAL_ORIGINAL_SNAPSHOT_INSTRUCTION}}
{{DIALOGUE_ANCHOR_INSTRUCTION}}

Dialogue register enforcement:
1. Check each speaking character's `contraction_level` in the style bible. Revise toward that level while preserving legitimate formality, historical cadence, ritual language, legalistic diction, and deliberate emphasis when character- or world-true.
2. Honor `default_contraction_use` from `dialogue_rules` as the book-wide baseline.
3. When revising casual or pressured contemporary dialogue, prefer "don't", "can't", "I'm", "won't", "it's" over uncontracted forms unless the character is being deliberately formal, emphatic, or setting-true in that specific line.
4. Under scene pressure, push dialogue toward the character's pressured texture — often more contraction, truncation, and colloquial friction, but sometimes greater precision or stiffness if that is how this voice handles strain. Do not flatten distinct voices into one generic informal register.
5. If any `example_lines` from the style bible appear verbatim or near-verbatim in the chapter, replace them — example lines are calibration-only reference material and must never appear in the draft.
6. Use the character-level spoken-texture fields when present: `interruption_habit`, `self_correction_tendency`, `indirectness`, `repetition_tolerance`, `evasion_style`, and `sentence_completion_style`. These are constraints, not decorative notes.
7. If a line is alive but messy, preserve that life. Fix only the specific defect named by the packet; do not convert pressure into thesis-speech.

Required outputs:
1. `{{CHAPTER_OUTPUT_FILE}}` (revised in place)
2. `{{REVISION_REPORT_FILE}}`

`{{REVISION_REPORT_FILE}}` contract:
1. `chapter_id` (string)
2. `finding_results` (array of objects):
3. `finding_id`
4. `status_after_revision` (`FIXED|PARTIAL|UNRESOLVED`)
5. `evidence` (must cite `{{CHAPTER_OUTPUT_FILE}}:<line>`)
6. `notes`
7. `summary` (string)

Example structure only. Do not copy wording, IDs, evidence, or summary language from this example. `notes` and `summary` may be as short or as detailed as needed, but `summary` must appear at the top level of the JSON object, not inside `finding_results`.

```json
{
  "chapter_id": "chapter_01",
  "finding_results": [
    {
      "finding_id": "EXAMPLE_FINDING",
      "status_after_revision": "FIXED",
      "evidence": "chapters/chapter_01.md:12; chapters/chapter_01.md:34",
      "notes": "..."
    }
  ],
  "summary": "..."
}
```
