You are running CONTINUITY RECONCILIATION for cycle `{{CYCLE_PADDED}}`.

Inputs:
1. Full manuscript snapshot: `{{FULL_NOVEL_FILE}}`
2. Current continuity sheet: `outline/continuity_sheet.json`
3. Spatial layout: `{{SPATIAL_LAYOUT_FILE}}`
4. Cycle story context pack: `{{GLOBAL_CYCLE_CONTEXT_FILE}}`

Task:
1. Read the full manuscript and compare every factual claim against the current continuity sheet.
2. Extract any new facts introduced by chapter drafters or revisers that are not yet in the sheet: character details, object introductions, financial amounts, dates, locations, knowledge transfers.
3. Identify conflicts: places where the manuscript contradicts the sheet OR where two chapters contradict each other.
4. Produce two outputs: an updated continuity sheet and a conflict log.

Reconciliation rules:
1. When two chapters contradict each other on a fact, choose the value that is more deeply embedded in its chapter's causal structure (harder to change without rewriting the chapter). Record the conflict and the canonical choice in the conflict log.
2. Treat the existing continuity sheet as canonical by default. A repeated manuscript drift must not become canon merely because multiple chapters agree with one another.
3. Only update a sheet value when the manuscript provides explicit, repeated, and causally central evidence that the current sheet is wrong, and when the replacement value is better supported than the existing canon. Use the story context pack as secondary evidence of planned intent when it helps distinguish an early-sheet mistake from later manuscript drift, but do not invent facts from it. Record that reasoning in the conflict log.
3b. If a current sheet value appears nowhere in the manuscript while a different value is used consistently and concretely across the book, treat this as evidence of an early-sheet mistake rather than automatic manuscript drift. Update the sheet when the manuscript's replacement value is clearly better supported, and record that reasoning in the conflict log.
4. If the manuscript contradicts the sheet but the replacement value is ambiguous, weakly supported, or would force broad reinterpretation, keep the sheet value and log the contradiction as manuscript drift rather than silently changing canon.
5. Do not invent facts. Only record what is explicitly stated or clearly implied in the manuscript text.
6. Preserve existing sheet entries that remain valid. The updated sheet should be a superset of the current sheet plus new facts from the manuscript, minus only entries that the manuscript has clearly and credibly superseded. Do not drop entries simply because the manuscript does not re-state them — facts established in earlier cycles remain canonical unless clearly replaced.
7. When in doubt, prefer canonical stability over opportunistic replacement.
8. Keep the sheet compact. Each field should contain only what downstream drafters and revisers need for consistency. Omit subjective interpretation, thematic analysis, and prose-level guidance — those belong in the style bible.
9. For `state_transitions`, only record changes that affect continuity: age changes, injuries gained or healed, objects acquired or lost, relationships formed or broken, knowledge gained. Do not track emotional arc — that is the chapter spec's job.
10. For `knowledge_state`, only track information that characters could act on incorrectly if a drafter gets it wrong: secrets, lies, things learned in specific chapters that affect later behavior.
11. Treat `{{SPATIAL_LAYOUT_FILE}}` as the authoritative source for spatial ground truth. The continuity sheet's geography section should point to that file instead of duplicating room-by-room, route-by-route, or distance-by-distance spatial facts. Only keep high-level location facts in the continuity sheet that downstream stages need for non-spatial continuity.
12. `objects[].per_chapter_state` is the canonical tracker for plot-active props. Each entry must record `chapter`, `state`, `holder`, and `location`.
13. `character_blocking[]` tracks plot-active physical presence. Use it only for characters whose entrances, exits, carried objects, or positions materially matter in a chapter.
14. When two chapters disagree on an object's state transition, log the conflict with `field: "prop_state_drift"` in the conflict log.

Required outputs:
1. `{{CONTINUITY_SHEET_OUTPUT_FILE}}` (overwrites existing sheet)
2. `{{CONFLICT_LOG_OUTPUT_FILE}}`

`{{CONTINUITY_SHEET_OUTPUT_FILE}}` contract:
Must be a valid JSON object with these top-level keys (all required, but arrays/objects may be empty if not applicable to the premise):

1. `characters` (array of objects, each with):
   - `character_id` (string, matching style bible)
   - `age_at_story_start` (number or null if unspecified)
   - `physical_details` (string)
   - `key_relationships` (object mapping character_id to relationship label)
   - `occupation_status` (string)
   - `aliases` (array of strings: all names/titles/references used for this character)
   - `literacy_languages` (string: what the character can read, write, speak)
   - `state_transitions` (array of objects with `chapter` and `change` fields)
   - `availability` (string: when the character is present, absent, or dead)

2. `timeline` (object with):
   - `story_start` (string: season, year, and context)
   - `estimated_span` (string)
   - `seasonal_track` (array of objects with `chapters` and `season` fields)
   - `key_events` (array of objects with `event`, `timing`, and `chapter` fields)

3. `geography` (object with):
   - `spatial_layout_ref` (string: set to `{{SPATIAL_LAYOUT_FILE}}`)
   - `primary_setting` (string)
   - `key_locations` (array of objects with `name` and `details` fields)
   - `distances` (array of strings: only broad spatial relationships worth tracking outside `{{SPATIAL_LAYOUT_FILE}}`; otherwise keep empty)

4. `world_rules` (array of strings: constraints on what is possible in this world — physics, magic systems, laws, social rules, technology level. Empty for realistic contemporary fiction.)

5. `power_structure` (array of objects with `holder`, `over`, and `mechanism` fields)

6. `objects` (array of objects with `name`, `owner`, `origin`, `status`, `chapter_introduced`, and `per_chapter_state`)
   - `per_chapter_state` is an array of objects with `chapter`, `state`, `holder`, and `location`

7. `financial_state` (object with):
   - `debts` (array of objects with `creditor`, `amount`, `deadline`, and `status` fields)
   - `income_sources` (array of objects with `source`, `amount`, and `reliability` fields)

8. `knowledge_state` (array of objects with `character`, `knows`, `learned_in`, and `hidden_from` fields)

9. `environmental_constants` (array of strings: persistent sensory and environmental facts about the world)

10. `character_blocking` (array of objects with `chapter`, `character`, `entrance`, `exit`, `carrying`, and `position`)

`{{CONFLICT_LOG_OUTPUT_FILE}}` contract:
Must be a valid JSON object with:

1. `cycle` (int)
2. `conflicts` (array of objects, each with):
   - `conflict_id` (string, stable identifier)
   - `field` (string: which continuity sheet field is affected)
   - `description` (string: what contradicts what)
   - `chapters_involved` (array of chapter_id strings)
   - `evidence` (string: cite `{{FULL_NOVEL_FILE}}:<line>` for each conflicting reference)
   - `canonical_value` (string: the value chosen for the updated sheet)
   - `resolution_note` (string: why this value was chosen)
3. `new_facts_added` (int: count of facts added to the sheet that were not in the previous version)
4. `facts_updated` (int: count of facts whose values changed from the previous sheet)

Hard constraints:
1. Do not modify the manuscript. This stage is read-only for prose.
2. Do not add style, voice, or thematic guidance to the continuity sheet. Facts only.
3. Aim for roughly 2000 words. Only consolidate entries if the sheet exceeds 3000 words — merge minor objects, summarize minor characters, compress environmental constants.
