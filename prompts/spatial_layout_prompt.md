You are generating the novel's SPATIAL LAYOUT document.

Inputs:
1. Premise: `input/premise.txt`
2. Outline: `outline/outline.md`
3. Chapter specs: `outline/chapter_specs.jsonl`
4. Scene plan: `outline/scene_plan.tsv`
5. Continuity sheet: `outline/continuity_sheet.json`
6. Constitution: `config/constitution.md`

Purpose:
1. Create one authoritative spatial reference so parallel drafting does not invent contradictory geography.
2. Generate layout detail only when spatial relationships are actually load-bearing.
3. If the novel does not need a meaningful spatial reference, say so explicitly and emit null sections instead of filler.

Output requirements:
1. Write exactly one JSON object to `{{SPATIAL_LAYOUT_FILE}}`.
2. Required top-level keys:
   - `summary` (string)
   - `micro` (object or null)
   - `macro` (object or null)
3. If `micro` is present, include:
   - `setting_name`
   - `structure_type`
   - `locations` (array of objects with at least `name`)
   - optional `floor_summary`
   - optional `key_routes`
4. If `macro` is present, include:
   - `world_name`
   - `locations` (array of objects with at least `name`)
   - optional `routes`
   - optional `cardinal_anchors`
5. At least one of `micro` or `macro` may be null. Both may be null only when the summary clearly states why a dedicated spatial layout is not load-bearing for this premise.

Guidance:
1. Use `micro` for buildings, compounds, ships, stations, campuses, or other confined settings where adjacency matters.
2. Use `macro` for travel novels, named-location networks, or stories where route distance and relative direction matter.
3. Be concrete about adjacency, access, travel time, or direction when those facts will matter on the page.
4. Do not pad with generic world-building if the outline does not support it.
