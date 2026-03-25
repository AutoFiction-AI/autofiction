You are running the PREMISE CANDIDATES stage.

Inputs:
1. Search plan: `{{PREMISE_SEARCH_PLAN_FILE}}`

{{PREMISE_BRIEF_BLOCK}}

Task:
1. Read the seeded search plan and generate exactly one candidate premise for each candidate entry in `{{PREMISE_SEARCH_PLAN_FILE}}`.
2. Treat the search plan as steering, not as a template to fill mechanically. The output premises must feel like distinct, freeform seeds of novels, not slot-filled loglines.
3. The candidate field should be broad in mode, pressure, scale, and imaginative texture. The plan already pushes candidates into different regions of premise space; honor those differences rather than collapsing them into one prestige-safe lane.
4. Keep the judging standard award-agnostic and genre-fair. You are not trying to approximate Booker specifically. You are trying to find premises that feel novelistically alive: specific, pressure-bearing, and viable across the full length of a novel.
5. A strong premise should imply a range of possible scene textures across a full book: intimacy, labor, conflict, embarrassment, ritual, comedy, waiting, travel, aftermath, obsession, revelation, and social consequence. Do not confuse long-book viability with a repeatable bureaucratic workflow.
6. Each premise must still be clear enough for the outline stage to build from without extra metadata. Vagueness is failure, but concreteness can come from desire, labor, place, weather, ritual, rivalry, kinship, bodily dependence, travel, performance, or community memory as much as from institutions.
7. The engine of the novel should usually be people acting on one another, not systems classifying them.
8. Each candidate entry includes an abstract scaffold profile. Treat `scene_source` as where scenes naturally arise, `social_geometry` as how people press on one another, `narrative_motion` as how pressure keeps changing over the book, and `mode_overlays` as tonal leanings. These are structural cues, not templates or mandatory props.
9. Honor the scaffold profile at a deep level. A candidate with `work` as scene source and `triangle` as social geometry should not collapse into the same sort of book as one with `ritual` as scene source and `community_field` as social geometry, even if they share some axis pressure.
10. Do not name the scaffold explicitly in the premise or flatten it into a stock setup. Use it as hidden structural steering.
11. Some axis labels in the search plan are intentionally broad. "Formal recognition, naming, and social legibility" can manifest through names, vows, rumor, inheritance, debt, permission, status, or who gets believed, not only files and records. "Rule-bound collective life" can mean households, guilds, crews, shrines, schools, compounds, or neighborhoods, not only offices and agencies. "Stepwise task pressure" can mean craft, ritual, repair, concealment, or bodily work, not only protocol and compliance.
12. Do not default to records, audits, tribunals, clinics, ledgers, maps, censuses, archives, or official paperwork merely to make a premise feel serious or legible. Use those only when they are genuinely integral to that specific candidate's engine.
13. If the search plan includes a `prior_batch_repetition_warning`, treat it as real negative steering for this batch. Do not lightly re-skin a concrete engine that earlier batches have already overused.
14. The core axes, risk axes, and scaffold cues are not mandatory content checkboxes. High violence, erotic charge, comedy, profanity, fantasy, science-fiction, or strangeness are all valid modes when they are integral to the book's engine. Do not flatten candidates toward safety.
15. Do not write brainstorming notes, rationale, shortlist language, or markdown. This stage only emits the candidate file.

Required output:
1. `{{PREMISE_CANDIDATES_OUTPUT_FILE}}`

`{{PREMISE_CANDIDATES_OUTPUT_FILE}}` contract:
1. Write one JSON object per line, in the same order as the `candidates` array in `{{PREMISE_SEARCH_PLAN_FILE}}`.
2. Emit exactly one row for each `candidate_id` from the search plan.
3. Each row must contain exactly these keys:
   - `candidate_id`
   - `premise`
   - `engine_guess`
   - `protagonist_descriptor`
   - `pressure_descriptor`
   - `setting_descriptor`
   - `why_it_might_work`
   - `risk`
4. `candidate_id` must exactly match the search plan entry.
5. `premise` should be brief and freeform, usually 1-3 sentences, and should stay well below mini-treatment length.
6. `engine_guess`, `protagonist_descriptor`, `pressure_descriptor`, and `setting_descriptor` should each be short, concrete phrases.
7. `why_it_might_work` and `risk` should each be 1-3 sentences max.
8. Do not include markdown, code fences, numbering, or any file content other than valid JSONL rows.
