You are running LOCAL-WINDOW AUDIT for `{{WINDOW_ID}}` in cycle `{{CYCLE_PADDED}}`.

Inputs:
1. Full manuscript snapshot: `{{FULL_NOVEL_FILE}}`
2. Chapter line index: `{{CHAPTER_LINE_INDEX_FILE}}`
3. Continuity sheet: `{{CONTINUITY_SHEET_FILE}}`
4. Window chapter ids: `{{WINDOW_CHAPTER_IDS}}`
5. Window chapter specs:
{{WINDOW_CHAPTER_SPECS}}
6. Style bible: `outline/style_bible.json`
7. Constitution: `config/constitution.md`

Context isolation requirement:
1. Do not read prior cycle reviews, revision reports, gate files, or packet files.
2. Use the chapter line index to jump directly to the relevant spans in `{{FULL_NOVEL_FILE}}` rather than scanning the full manuscript sequentially.
3. Judge what it feels like to read these consecutive chapters back-to-back. This is the reading-experience auditor.
4. Do not let the continuity sheet or style bible excuse missing on-page clarity. Use them to detect contradiction and drift, not to rescue unclear prose.
5. Read the listed chapter spec files for this window. Use their edge fields (`opening_situation`, `closing_state`, `chronology_anchor`, `entry_obligation`, `exit_pressure`) as planning contracts you may validate against, not as excuses for prose the manuscript failed to render on the page.

Task:
1. Evaluate this window only. Your scope is the local reading experience across these consecutive chapters.
2. Emit findings only when the evidence depends on reading these chapters as a cluster or at their boundaries.
3. Every finding must include `fix_owner_reason`, `pass_hint`, and `related_chapter_ids`.
4. All citations must use `{{FULL_NOVEL_FILE}}:<line>` format.

Mandatory pre-scan — complete this BEFORE evaluating structural and momentum issues:

Scan for description-level, continuity, and immediate boundary-level repetition problems across the chapters in this window. These are among the most reader-visible problems in parallel-drafted novels and must not be deprioritized.

Use category `pre_scan` with the appropriate subcategory:

P1. `redundant_reintroduction`: a character's appearance, role, or backstory re-explained using the same or paraphrased information from an earlier chapter in the window.
P2. `inconsistent_description`: a character's physical details, possessions, injuries, or status contradict an earlier chapter in the window. A setting's layout, atmosphere, or physical details contradict between chapters.
P3. `chronology_gap`: a reader cannot tell how much time passed at a chapter boundary.
P4. `presence_continuity`: a character present at the end of one chapter vanishes at the start of the next without explanation, or appears at a location without having traveled there.
P5. `name_reference_shift`: the same character is referred to inconsistently across a chapter boundary without motivated context.
P6. `repeated_information`: the same plot fact is explained to the reader in two adjacent chapters through different narrative means.
P7. `pov_clarity`: in a multi-POV novel, a new chapter's POV is not clear within the first 2-3 sentences.
P8. `dangling_thread`: a character promises, threatens, or commits to something at the end of one chapter and the adjacent chapter silently ignores it.
P9. `tonal_mismatch`: the emotional register shifts so abruptly at a chapter boundary that the transition feels like two different novels spliced together.
P10. `reader_confusion`: anything that would make a reader pause in unintentional confusion. Deliberate mystery and ambiguity are fine; accidental opacity is not.
P11. `composed_seam_prose`: at a chapter boundary, the exit or entry sentence uses narrator performance, thematic summary, aphoristic contrast, or over-composed prose that would read better as transparent scene description. If a chapter ends with "Pain taught better when it wasn't being watched" or opens with "By noon he had learned another road fact: injury made distance dishonest," flag it here as a seam problem rather than letting the prose performance slide past the boundary.
P12. `conversation_redundancy`: at a chapter boundary, a moral argument, emotional reckoning, revealed wound, or relational confrontation in the later chapter substantially restages one already landed in the earlier chapter — same characters examining the same ground, same emotional weight — without materially new evidence, consequence, or changed power relationship that alters the reader's understanding of the wound. Flag the later chapter.
P13. `prop_state_continuity`: flag any object whose `per_chapter_state` transitions are non-monotonic, mutually incompatible, or physically impossible across this window, or any character whose blocking contradicts across a boundary. Use the continuity sheet as the canonical reference, but judge whether the prose actually supports the transition.

After the pre-scan, evaluate structural and momentum issues using these ten categories:

5. Use these ten categories:
5a. `factual_coherence`: action attribution across consecutive chapters, shared events across POV shifts, physical details carrying across boundaries, opening/closing coherence, and spatial or geographic contradictions across adjacent chapters.
5b. `pacing_rhythm`: monotony, repeated chapter structures, or repeated openings across consecutive chapters.
5c. `emotional_continuity`: unearned emotional whiplash or same-register drift without escalation, complication, inversion, deepening, or cumulative thickening.
5d. `information_flow`: information firehose, local stall, or setup/payoff failures whose payoff belongs inside this window.
5e. `boundary_local_voice_drift`: dialogue or narration voice drift across adjacent chapters or POV shifts.
5f. `redundant_scene_functions`: chapters serving the same narrative function or adjacent-chapter re-description and re-orientation.
5g. `cross_chapter_prose_patterns`: the same descriptor, object-state mention, location beat, sensory motif, metaphor, formulaic construction, or character-associated repetitive action recurring across adjacent chapters. Flag this when a specific descriptor or motif recurs 3 or more times within this 4-chapter window without each recurrence changing pressure, leverage, or meaning on the page. Two occurrences can read as deliberate recurrence; three or more in a short window reads as autopilot. Evidence must list every occurrence with `{{FULL_NOVEL_FILE}}:<line>` citations.
5h. `repetitive_scene_dynamics`: adjacent chapters restaging the same interpersonal dynamic, appeal/response shape, or obstacle pattern without changed terms.
5i. `character_decision_coherence`: decisions or behavior that contradict adjacent-chapter knowledge, personality, or goals without explanation.
5j. `reading_momentum`: the specific chapter where the window fails to create new pressure, new information, changed leverage, cumulative intensification, or a distinct terminal state.
5k. Composed seam prose: this boundary-specific failure must already have been checked in the mandatory pre-scan. If you emit an additional structural finding, do so only when the seam-level prose performance also creates a second distinct problem. Use existing categories rather than inventing a new one: `cross_chapter_prose_patterns` for performed prose at the seam, `boundary_local_voice_drift` when the seam abruptly changes narration register, and `reading_momentum` when a thematic summary sentence weakens exit or entry pressure.

What this stage does not emit:
1. Density or count findings.
2. Pure factual contradictions that do not depend on boundary-local reading.
3. Within-chapter voice quality judgments better owned by chapter review.

Fix-owner defaults:
1. Later chapter owns redundant re-orientation and re-description.
2. Later chapter owns a boundary contradiction unless the earlier chapter is clearly wrong against the continuity sheet or compiled text.
3. Weaker or redundant chapter owns repeated scene-function findings.
4. Boundary-local voice drift belongs to the chapter where the drift first appears.
5. Setup misses belong to the setup chapter when the seed is absent; payoff misses belong to the payoff chapter when the payoff lands underprepared.

Severity guidance:
1. `CRITICAL`: factual contradiction that would break reader trust.
2. `HIGH`: structural problem a careful reader would notice, including repeated openings, momentum stalls across multiple chapters, unearned emotional whiplash, and redundant scene functions.
3. `MEDIUM`: qualitative drift that hurts the reading experience without breaking the story.

Pass-hint defaults:
1. `pre_scan` defaults to `p1_structural_craft`, including `pre_scan/conversation_redundancy`, except `pre_scan/composed_seam_prose`, which defaults to `p3_prose_copyedit`. `factual_coherence`, `pacing_rhythm`, `emotional_continuity`, `information_flow`, `redundant_scene_functions`, `repetitive_scene_dynamics`, `character_decision_coherence`, and `reading_momentum` default to `p1_structural_craft`.
2. `boundary_local_voice_drift` defaults to `p2_dialogue_idiolect_cadence`.
3. `cross_chapter_prose_patterns` defaults to `p3_prose_copyedit`.
4. Override the default only when the finding is primarily about dialogue register or prose-level wording.

Category-conditional requirements:
1. `factual_coherence` requires `related_chapter_ids`, `boundary_span`, and `counterpart_evidence`.
2. `boundary_local_voice_drift` requires `related_chapter_ids` and `boundary_span`.
3. `redundant_scene_functions` requires `related_chapter_ids`.

Required output:
1. `{{LOCAL_WINDOW_OUTPUT_FILE}}`

`{{LOCAL_WINDOW_OUTPUT_FILE}}` contract:
1. Top-level fields:
2. `cycle` (integer; write `{{CYCLE_INT}}`)
3. `window_id` (string; write `{{WINDOW_ID}}`)
4. `chapters_reviewed` (array of the chapter ids in this window, in order)
5. `summary` (string)
6. `findings` (array)
7. Each finding object must contain:
8. `finding_id`
9. `category`
10. `subcategory`
11. `severity` (`MEDIUM|HIGH|CRITICAL`)
12. `chapter_id`
13. `related_chapter_ids`
14. `boundary_span` (required for `factual_coherence` and `boundary_local_voice_drift`; omit for other categories)
15. `counterpart_evidence` (required for `factual_coherence`; omit for other categories)
16. `pass_hint` (`p1_structural_craft|p2_dialogue_idiolect_cadence|p3_prose_copyedit`)
17. `evidence`
18. `problem`
19. `rewrite_direction`
20. `acceptance_test`
21. `fix_owner_reason`

Example structure only. Do not copy wording, ids, evidence, or summary language from this example.

```json
{
  "cycle": 1,
  "window_id": "window_02",
  "chapters_reviewed": ["chapter_03", "chapter_04", "chapter_05", "chapter_06"],
  "summary": "Dominant failure: chapters 04 and 05 repeat the same interview dynamic.",
  "findings": [
    {
      "finding_id": "LW02-001",
      "category": "factual_coherence",
      "subcategory": "action_attribution",
      "severity": "HIGH",
      "chapter_id": "chapter_04",
      "related_chapter_ids": ["chapter_03"],
      "boundary_span": "chapter_03/chapter_04",
      "counterpart_evidence": "{{FULL_NOVEL_FILE}}:445",
      "pass_hint": "p1_structural_craft",
      "evidence": "{{FULL_NOVEL_FILE}}:812",
      "problem": "...",
      "rewrite_direction": "...",
      "acceptance_test": "...",
      "fix_owner_reason": "..."
    }
  ]
}
```
