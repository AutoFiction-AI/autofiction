You are running SCENE-LEVEL CONSISTENCY AUDIT for `{{CHAPTER_ID}}`.

Inputs:
1. Chapter text: `{{CHAPTER_INPUT_FILE}}`
2. Chapter spec: `{{CHAPTER_SPEC_FILE}}`
3. Continuity sheet: `{{CONTINUITY_SHEET_FILE}}`
4. Spatial layout: `{{SPATIAL_LAYOUT_FILE}}`
5. Style bible: `outline/style_bible.json`
6. Constitution: `config/constitution.md`

Context isolation requirement:
1. Do not read prior cycle reviews, revision reports, gate files, packet files, cycle context packs, or boundary context packs. This stage is single-chapter and forensic; cross-chapter coherence is owned by other stages.
2. Use only the inputs listed above.
3. Do not let the continuity sheet or style bible excuse missing on-page clarity. Use them to detect contradictions, not to fill gaps the prose failed to render.

Scope:
1. You are a forensic in-scene consistency auditor. Your job is to walk the chapter scene-by-scene and emit one finding for every distinct within-scene contradiction.
2. A "scene" is a contiguous run of prose inside the chapter where time, place, and present cast remain materially continuous. Scene boundaries are typically marked by a blank line, a section break, a time jump, or a location change. You decide where scenes end; assign each scene a stable id of the form `scene_01`, `scene_02`, ... in the order they appear in the chapter.
3. Your scope is contradictions internal to a single scene. Cross-scene contradictions inside the chapter are also in scope. Cross-chapter contradictions are NOT in scope (those belong to `local_window_audit`).
4. Pure craft judgments (pacing, voice, dialogue quality, prose performance) are NOT in scope. Those belong to `chapter_review` and `dialogue_diagnostic`. This stage is forensic only.

Hard exhaustiveness rule:
1. Emit one finding per distinct contradiction. Consolidation is forbidden.
2. If twelve distinct contradictions exist, emit twelve findings. Do not stop at three. Do not bucket multiple contradictions under a single finding "for brevity." Do not summarize.
3. Two findings are "distinct" when their fix touches different lines or different facts. Two beats of the same broken object state across one scene = one finding. The same character contradicting themselves on two unrelated facts = two findings.
4. A finding is distinct from a different scene's finding even if the subcategory is identical. The cite-pair must always include the two specific lines that contradict.
5. Anti-example of consolidation (FORBIDDEN): a single finding that says "Several blocking and prop-state contradictions appear in scene 02; revise to make movements explicit." Instead emit one finding per contradicted prop, blocking pair, or description shift, each with its own cite pair.

Mandatory subcategory checklist — for each scene, walk this list and emit findings for every fired item:

S1. `commonsense_physical` — physical impossibility within the scene that no on-page event accounts for. Examples: a door previously locked is opened later without anyone unlocking it; a character reads a book while their hands are described as both occupied; a character outside in rain is suddenly dry without going under cover; a character speaks while their mouth is described as full or covered.

S2. `prop_state_local` — an object's state, location, or possession transitions in a way the prose does not bridge. Examples: a phone held at beat N appears in a pocket at beat N+k with no put-away beat; a glass described as full is later described as empty without a drinking beat; a weapon drawn early is referenced as holstered later with no holstering beat; an object's color, size, or material flips within the scene.

S3. `blocking_contradiction` — a character's spatial position is incompatible with prior beats in the same scene. Examples: standing then seated without a sitting beat; positioned across the room then suddenly within reach; on one side of a closed door then on the other without a movement beat; arrived alone then with someone without the second character's entry rendered.

S4. `light_environment` — light, sound, temperature, weather, or other environment cues contradict within the scene without an on-page source event. Examples: room described as dark then a character reads small print without a light source being introduced; described as silent then a character hears specific quiet sounds without the silence being broken; cold outside then warm inside without entering a building; rain on the page then dry pavement without rain stopping.

S5. `time_within_scene` — time-of-day, weekday, season, or duration cues inside one scene cannot be reconciled. Examples: opening at sunset and closing at midday without a break; a five-minute exchange that explicitly references three hours having passed; a conversation that begins on Tuesday and references "yesterday's Monday meeting" inside the same scene; characters whose described tiredness or hunger contradicts the implied elapsed time.

S6. `knowledge_state_local` — a character (focalizer or otherwise) is rendered as not knowing X, then within the same scene references knowing X (or vice versa) with no on-page learning beat. Examples: focalizer narrated as unaware that another character has arrived, then immediately addresses them by name; a character asks a question whose answer they used five lines earlier; a character is "told for the first time" something the prose has them already considering.

S7. `emotional_continuity_local` — emotional or affective state flips inside the scene with no on-page pressure shift. This is not a craft judgment about whether the emotion is well-rendered; it is a forensic flag for unmotivated affect reversals. Examples: described as enraged at one beat and described as serene three lines later with nothing between; "relieved" then "afraid" then "relieved" inside one exchange without the trigger for each reversal on the page.

S8. `action_decision_local` — a character refuses, commits to, or decides X inside a scene then acts as if the opposite within the same scene without any negotiation, recognition, motive shift, or external pressure on the page. Distinct from `chapter_review` item 16d (chapter-turn decision coherence): this fires when the contradiction is local to one scene and the fix is to plant a bridging beat inside the scene. Examples: character says "I'm not going" and then walks out the door without a relenting beat; character accepts an offer then refuses it three lines later without anything new entering.

S9. `description_contradiction_local` — a character's or setting's physical description contradicts an earlier line in the same scene. Examples: clothing changes mid-scene with no costume change rendered; eye/hair color, height, or other identifying detail flips; scar present, then not; furniture rearranged without anyone moving anything. Cross-chapter description drift belongs to `local_window_audit`; scope this strictly to within-scene shifts.

S10. `social_action_coherence` — a character's role-bearing or relational action contradicts their stance two beats earlier without on-page negotiation. Examples: "you can't stay" then offering the room without a relenting beat; refusing to speak to someone then volunteering information to them with no shift in pressure; rejecting a gift then accepting an identical second offer without anything changing.

S11. `dialogue_internal_coherence` — a speaker contradicts something they said within the same scene without acknowledging the change or having something on the page change for them. Examples: "I never met him" then "when he and I met last spring" five lines later; "I haven't decided" then "my decision is final" with no decision beat on the page.

How to use the inputs:
1. Use `{{CONTINUITY_SHEET_FILE}}` to anchor canonical facts (character ages, prop states, blocking) when judging whether a within-scene shift is a contradiction. The continuity sheet is authoritative for what *should* be true; flag the prose, not the sheet.
2. Use `{{SPATIAL_LAYOUT_FILE}}` to judge spatial impossibility within a scene (room adjacency, route timing). If both `micro` and `macro` are null in the layout, do not invent spatial constraints.
3. Use `{{CHAPTER_SPEC_FILE}}` for what the chapter intends; do not let intent excuse unrendered transitions.

Severity guidance:
1. `CRITICAL` — physical impossibility a careful reader would catch on first read and that breaks scene credibility (locked-door violation, a held object that vanishes mid-action with no setting-down beat in a high-attention scene).
2. `HIGH` — a within-scene contradiction a careful reader would notice and that needs an explicit bridging beat: blocking jumps, prop-state breaks in non-quiet scenes, knowledge-state flips, action/decision reversals without an on-page hinge.
3. `MEDIUM` — softer continuity drift: minor description flips, light/environment inconsistencies that do not break the scene, emotional reversals where the reader can guess the missing beat.

Pass-hint defaults (the aggregator uses these to route the fix to the right revision pass):
1. `S1 commonsense_physical`, `S2 prop_state_local`, `S3 blocking_contradiction`, `S4 light_environment`, `S5 time_within_scene`, `S9 description_contradiction_local`: default `p3_prose_copyedit` (the fix is usually a sentence-level addition or correction).
2. `S6 knowledge_state_local`, `S8 action_decision_local`, `S10 social_action_coherence`: default `p1_structural_craft` (the fix usually requires a new bridging beat).
3. `S7 emotional_continuity_local`: default `p1_structural_craft` when the missing beat is structural; `p3_prose_copyedit` when it is a single sentence of recognition.
4. `S11 dialogue_internal_coherence`: default `p2_dialogue_idiolect_cadence`.
5. Override the default only when the specific fix you describe in `rewrite_direction` clearly belongs to a different pass.

Acceptance test guidance:
1. Acceptance tests must be verifiable by reading the revised passage. Name the bridging beat that must appear, the line that must be cut, or the description that must be brought into agreement.
2. Cite the lines that must change and what observable property the revised text must have. Avoid bean-counting tests.
3. Example acceptable form: "After revision, between {{CHAPTER_INPUT_FILE}}:142 and {{CHAPTER_INPUT_FILE}}:151, the prose renders the character setting the cup down before reaching for the door, OR the door beat is rewritten so the cup is still in hand."

Required output:
1. `{{SCENE_CONSISTENCY_OUTPUT_FILE}}`

`{{SCENE_CONSISTENCY_OUTPUT_FILE}}` contract:
1. Top-level fields:
2. `chapter_id` (string; must equal `{{CHAPTER_ID}}`)
3. `cycle` (integer; write `{{CYCLE_INT}}`)
4. `scenes_indexed` (array of strings; the scene ids you assigned, in order — e.g. `["scene_01", "scene_02", "scene_03"]`)
5. `findings` (array)
6. `summary` (string; brief — what kind of contradictions dominate, or "no within-scene contradictions detected" if the chapter is clean)
7. Each finding object must contain:
8. `finding_id` (string; stable within this chapter, e.g. `SC-{{CHAPTER_ID}}-001`)
9. `subcategory` (one of: `commonsense_physical`, `prop_state_local`, `blocking_contradiction`, `light_environment`, `time_within_scene`, `knowledge_state_local`, `emotional_continuity_local`, `action_decision_local`, `description_contradiction_local`, `social_action_coherence`, `dialogue_internal_coherence`)
10. `severity` (`MEDIUM|HIGH|CRITICAL`)
11. `chapter_id` (must equal `{{CHAPTER_ID}}`)
12. `scene_id` (the assigned scene id where the contradiction occurs)
13. `evidence` (must cite at least two `{{CHAPTER_INPUT_FILE}}:<line>` references — the line that establishes the original state and the line that contradicts it; multiple cites separated by `; `)
14. `problem` (string; name the two contradictory facts and which one is the established baseline)
15. `rewrite_direction` (string; specify the bridging beat, cut, or description correction — anchored to specific lines/spans in `{{CHAPTER_INPUT_FILE}}:<line>` form)
16. `acceptance_test` (string; concrete and verifiable by reading the revised passage)
17. `pass_hint` (`p1_structural_craft|p2_dialogue_idiolect_cadence|p3_prose_copyedit`)

Example structure only. Do not copy wording, IDs, evidence, or summary language from this example.

```json
{
  "chapter_id": "chapter_05",
  "cycle": 1,
  "scenes_indexed": ["scene_01", "scene_02", "scene_03"],
  "summary": "Two prop-state breaks and one blocking jump in scene_02; one knowledge-state flip in scene_03.",
  "findings": [
    {
      "finding_id": "SC-chapter_05-001",
      "subcategory": "prop_state_local",
      "severity": "HIGH",
      "chapter_id": "chapter_05",
      "scene_id": "scene_02",
      "evidence": "{{CHAPTER_INPUT_FILE}}:142; {{CHAPTER_INPUT_FILE}}:151",
      "problem": "...",
      "rewrite_direction": "...",
      "acceptance_test": "...",
      "pass_hint": "p3_prose_copyedit"
    }
  ]
}
```
