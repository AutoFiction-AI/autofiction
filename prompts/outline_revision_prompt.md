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
2. Every chapter spec must retain valid narrative fields and any setup/payoff metadata must stay coherent with the revised structure.
3. `{{SCENE_PLAN_FILE}}` must remain aligned with chapter counts and per-chapter scene targets.
4. `{{STYLE_BIBLE_FILE}}` must stay valid JSON and consistent with the revised novel's intended voice and register.
5. `{{CONTINUITY_SHEET_FILE}}` must stay valid JSON and consistent with the revised outline.
6. `{{TITLE_FILE}}` should remain a single title line.

Revision priorities:
1. Address the review's structural findings.
2. Take any strong elevation suggestion that materially improves novelty, escalation, or emotional consequence.
3. Prefer irreversible turns, sharper causal consequences, and stronger middle-book differentiation over bridge material.
4. When the premise clearly depends on layout or geography, make sure the revised outline leaves enough information for a later spatial-layout pass to formalize it cleanly.
