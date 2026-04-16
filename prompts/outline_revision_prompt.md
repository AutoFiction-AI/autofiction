You are running OUTLINE REVISION cycle `{{OUTLINE_REVIEW_CYCLE}}`.

Inputs:
1. Premise: `input/premise.txt`
2. Outline review: `{{OUTLINE_REVIEW_FILE}}`
3. Outline: `{{OUTLINE_FILE}}`
4. Chapter specs: `{{CHAPTER_SPECS_FILE}}`
5. Scene plan: `{{SCENE_PLAN_FILE}}`
6. Style bible: `{{STYLE_BIBLE_FILE}}`
7. Continuity sheet: `{{CONTINUITY_SHEET_FILE}}`
8. Title: `{{TITLE_FILE}}`
9. Constitution: `config/constitution.md`

Mandate:
1. Do not merely patch flagged problems. Elevate the outline so the drafted novel has a stronger structure, clearer escalation, and a more distinctive identity.
2. You may make significant changes to plot events, reveal timing, chapter functions, subplot architecture, and ending mechanics.
3. Preserve the premise's core concept, core character set, genre, tone, and explicit user directives.
4. Keep the outline package internally consistent across all files.

Required outputs:
1. Rewrite the canonical planning artifacts in place:
   - `{{OUTLINE_FILE}}`
   - `{{CHAPTER_SPECS_FILE}}`
   - `{{SCENE_PLAN_FILE}}`
   - `{{STYLE_BIBLE_FILE}}`
   - `{{CONTINUITY_SHEET_FILE}}`
   - `{{TITLE_FILE}}`
2. Do not create alternate filenames or sidecar drafts.

Hard constraints:
1. `{{CHAPTER_SPECS_FILE}}` must still define 16-20 contiguous chapters from `chapter_01` upward.
2. Every chapter spec must retain valid narrative fields and the required edge fields: `opening_situation`, `closing_state`, `chronology_anchor`, `entry_obligation`, and `exit_pressure`. Keep all of them non-empty and aligned with the revised structure.
2b. If you change a chapter's function, revise its edge fields so they still agree with the chapter's role rather than leaving stale metadata behind.
2c. Any setup/payoff metadata must stay coherent with the revised structure.
3. `{{SCENE_PLAN_FILE}}` must remain aligned with chapter counts and per-chapter scene targets.
3b. If you use the optional `undercurrent` column, keep it sparse and scene-specific. Use `null` when a scene does not need subtext architecture. Do not fabricate undercurrents for every scene.
4. `{{STYLE_BIBLE_FILE}}` must stay valid JSON and consistent with the revised novel's intended voice and register.
4b. Optional depth fields such as `interpretive_lens` and `formative_experiences` should be added only when they materially improve focalizer differentiation or dialogue planning. Keep them concrete, brief, and limited to the characters who actually benefit from them.
5. `{{CONTINUITY_SHEET_FILE}}` must stay valid JSON and consistent with the revised outline.
6. `{{TITLE_FILE}}` should remain a single title line.

Revision priorities:
1. Address the review's structural findings.
2. Take any strong elevation suggestion that materially improves novelty, escalation, or emotional consequence.
3. Prefer irreversible turns, sharper causal consequences, and stronger middle-book differentiation over bridge material.
4. When the premise clearly depends on layout or geography, make sure the revised outline leaves enough information for a later spatial-layout pass to formalize it cleanly.
5. If the review identifies under-architected dialogue scenes, fix them with the lightest planning support that will actually help drafting: a specific `undercurrent`, a sharper interpretive lens for a focalizer, or a concrete formative memory. Do not spread these additions everywhere by default.
