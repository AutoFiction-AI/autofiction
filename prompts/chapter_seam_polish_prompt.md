You are running CHAPTER SEAM POLISH for `{{CHAPTER_ID}}`.

Inputs:
1. Chapter text: `{{CHAPTER_INPUT_FILE}}`
2. Boundary context: `{{CHAPTER_BOUNDARY_CONTEXT_FILE}}`
3. Global outline: `outline/outline.md`
4. Continuity sheet: `{{CONTINUITY_SHEET_FILE}}`
5. Style bible: `outline/style_bible.json`
6. Constitution: `config/constitution.md`

Task:
1. Make minimal edits to improve entry/exit continuity with adjacent chapters.
2. Keep all core chapter beats and meaning intact.
3. Preserve character voice, prose style, and aesthetic-risk posture. Do not soften, euphemize, or sanitize raw content during polish — if a passage renders violence, sexuality, profanity, or moral compromise with specificity, that specificity must survive the polish pass unchanged.
4. Do not introduce new plot events that alter outline-level causality, tracked setup/payoff obligations, or canonical continuity.
5. Preserve each character's dialogue register and contraction level from the style bible. Do not flatten informal dialogue into formal register during polish.
6. Do not over-tidy living speech during polish. Preserve character-true roughness such as interruptions, self-corrections, evasions, repeated words, and incomplete-but-legible turns unless they create a specific seam problem.
7. If any `example_lines` from the style bible appear verbatim or near-verbatim in the text, replace them — they are calibration-only and must not appear in the draft.
8. Opening-construction diversity: compare this chapter's opening paragraph with the adjacent chapter openings visible in the boundary context. If this chapter's opening uses the same structural scaffold as either neighbor (e.g., both start with a transit/commute/weather arrival, both start with a character waking, both use the same "By the time [character]..." temporal construction), adjust the opening sentence or two — and only if a lighter touch cannot solve it, the opening paragraph — so it uses a distinct entry point (different spatial anchor, temporal frame, or first action) while preserving the same narrative information and tone.
9. Closing-state distinction: compare this chapter's ending movement with the adjacent chapter endings visible in the boundary context. If this chapter closes on substantially the same insight, emotional certification, or handoff shape as a neighbor, make minimal edits so the transition preserves continuity without sounding like the same beat twice.
10. Use `{{CONTINUITY_SHEET_FILE}}` as the canonical guardrail for names, time references, injuries, object states, relationship states, and knowledge state if a seam edit touches any of them.
11. Use `outline/outline.md` and the chapter-level planning data included in the boundary context (`open_hooks_to_carry`, `secondary_character_beats`, tracked setups/payoffs, and state deltas) as guardrails. Preserve those obligations while polishing the seam; do not cut or blur them away for smoothness.

Required outputs:
1. `{{CHAPTER_OUTPUT_FILE}}`
2. `{{SEAM_REPORT_FILE}}`

`{{SEAM_REPORT_FILE}}` contract:
1. JSON object with:
2. `chapter_id`
3. `seam_changes_made` (`YES|NO`)
4. `summary`
5. `edits` (array of short strings)

Example structure only. Do not copy wording from these examples.

```json
{
  "chapter_id": "chapter_01",
  "seam_changes_made": "YES",
  "summary": "...",
  "edits": ["...", "..."]
}
```

```json
{
  "chapter_id": "chapter_01",
  "seam_changes_made": "NO",
  "summary": "...",
  "edits": []
}
```

Hard constraints:
1. First non-empty line must remain exactly `# Chapter {{CHAPTER_NUMBER}}`.
2. Keep edits surgical.
