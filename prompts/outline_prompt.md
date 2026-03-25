You are running the OUTLINE stage.

Inputs:
1. Premise: `input/premise.txt`
2. Constitution: `config/constitution.md`

Task:
1. Produce an award-caliber novel outline with 16-20 chapters.
2. Before building the chapter plan, identify the premise's primary narrative engine: literary fiction, love story, mystery, character study, thriller, coming-of-age, survival drama, satire, comedy, dark comedy, tragicomedy, comedy-drama, fantasy, science fiction, speculative fiction, or combination of multiple engines. Let this engine determine what kinds of state shifts drive chapters.
2a. Literary fiction: prioritize thematic depth, character development, and artistic control over plot-only entertainment.
2b. Love story: let relational dynamics drive the book — trust, intimacy, betrayal, discovery of the other person. Physical and sexual intimacy are narrative events with consequences, not background activity to imply offscreen.
2c. Thriller or survival drama: let external threat, tactical choices, and consequence drive chapters.
2d. Character study or coming-of-age: let psychological shifts, identity pressure, and self-revision drive chapters.
2e. Comedy, dark comedy, tragicomedy, or comedy-drama: drive the book through escalating comic situations with real human stakes underneath. Humor must arise from character, situation, and voice — not from narrator wink or meta-commentary. Do not "elevate" a comic premise into seriousness out of nervousness. In tragicomedy, let genuine pain and genuine humor coexist in the same scene when the material calls for it; do not force one register to cancel the other.
2f. Fantasy, science fiction, or speculative fiction: let invented rules create pressures, costs, and moral dilemmas that would not exist without the speculative element. Establish rules through character experience and early-chapter action rather than front-loaded exposition, but do not suppress necessary explanation when the reader genuinely cannot infer local rules from context.
2g. Do not default to crime/action escalation when the premise calls for emotional, domestic, erotic, comic, spiritual, or communal drama. The setting may be dangerous without the plot becoming a crime story.
3. Build a chapter-level plan that can support full parallel drafting.
4. Every chapter must create a meaningful state shift in the novel.
5. State shifts may be physical, relational, informational, perceptual, comic, erotic, communal, spiritual, or tonal. Not every chapter needs to center a goal-versus-obstacle structure.
6. Keep causality explicit so chapter-by-chapter drafting remains coherent, but vary chapter engines aggressively. Some chapters should move through confrontation; others through revelation, aftermath, preparation, dread, seduction, humiliation, ritual, comic escalation, delay under obligation, drift-under-pressure, or a changed understanding.
6b. Hidden rooms, uncatalogued archives, accidental discoveries, overheard secrets, and other plot-critical concealment devices must obey concrete access logic. If a character finds a concealed place, object, or source of knowledge, the outline must make clear why this character can reach it now, why other plausible seekers have not already surfaced it, and what immediate constraint, cost, or uncertainty keeps the discovery from feeling like pure convenience. A wrong turn by itself is not sufficient causal architecture for a major discovery.
6c. When a conflict, dyad, mystery, or problem recurs across multiple chapters, do not restage the same dramatic unit at the same level of abstraction. Each recurrence must introduce at least one new concrete element: new information, new cost, new witness or audience, new operational test, new public consequence, new irreversible choice, or new emotional leverage. Thematic recurrence is welcome; scene-shape repetition is not.
7. Do not invent clerks, records, audits, tribunals, compliance structures, hospitals, or formal adjudication machinery merely to make the book feel serious, legible, or causally sturdy. If the premise's pressure is domestic, erotic, comic, ecological, spiritual, familial, or local, let the outline's chapter engines arise from those pressures instead.
8. Commit to the premise's natural register. If the premise involves difficult material — poverty, addiction, grief, institutional failure, moral compromise, violence, sexuality, or any other uncomfortable reality — the outline must reflect that truthfully, not retreat into a softened or action-movie version. A love story in a harsh setting should feel harsh AND tender. A survival story should feel desperate AND specific. Do not upgrade a domestic or emotional premise into a thriller because thrillers feel more "dramatic." Sanitization at the outline level cascades into every chapter.
9. Vary chapter texture across the book: alternate high-intensity scenes with reflective interiority, vary scene count and dialogue density, and as a strong default avoid giving two consecutive chapters the same structural rhythm. Deliberate repetition is allowed for ritual, serial procedure, rehearsal, obsession, or other premise-native patterns, but only when the repeated shape is doing new work.
9b. For recurring confrontations or recurring relationship tensions, plan escalation by changed terms rather than louder restatement. A later argument should test a new condition or expose a new cost, not merely paraphrase an earlier disagreement in sharper language.
9c. Build a middle-book progression map inside `outline/outline.md` for roughly the middle third of the novel (about 40%-80% through the book). For each chapter in that span, state: what new thing becomes known, impossible, irreversible, or emotionally undeniable here; what prior understanding, tactic, or relationship equilibrium stops being sufficient here; and why this chapter cannot be swapped with the previous middle chapter without loss. If two adjacent middle chapters would produce the same answers, redesign one of them.
9d. For recurring scene types — mentor session, debrief, argument, failed attempt, investigation update, planning conversation, almost-confession, or secret-sharing exchange — a reprise must change at least two of the following: power balance, witness or audience, new information, operational constraint, public consequence, cost of failure, or what one character wants from the other. If it does not, compress it or fold it into another chapter rather than restaging it.
9e. For any major reveal, capability, reversal, interpretive breakthrough, or crisis-solving move that lands in the back half of the novel, seed it earlier in the chapter plan. Record the earlier seed in that chapter's optional `setups_to_plant` field and the later landing in the payoff chapter's optional `payoffs_to_land` field. Use `must_land_beats` when the seed or payoff must visibly register as part of the chapter's local dramatic work, but do not rely on `must_land_beats` alone for major cross-chapter setup/payoff obligations.
10. Build genuine vulnerability into the protagonist(s): they must pay real costs — emotional, relational, economic, or physical — make mistakes with lasting consequences, and face situations where competence alone is not enough. Avoid the pattern of a protagonist who succeeds at every challenge.
10b. Identify 3-6 supporting characters who need independent pressure, desire, fear, obligation, or appetite outside their plot function. In `outline/outline.md`, note what each of those characters is carrying that does not reduce to serving the protagonist, and ensure at least two chapters let that pressure materially touch the page.
11. Build emotional range into the chapter plan. A novel that operates at sustained crisis pitch from early chapters onward produces diminishing returns on its biggest moments. At least 2-3 chapters should contain genuine quiet: a meal that isn't strategic, a conversation about something other than the central conflict, a moment of beauty or humor that isn't immediately instrumentalized. These scenes build the human baseline that makes the novel's highest-stakes moments land. If every chapter is an emergency, no chapter is.

Required outputs:
1. `outline/outline.md`
2. `outline/chapter_specs.jsonl`
3. `outline/scene_plan.tsv`
4. `outline/style_bible.json`
5. `outline/continuity_sheet.json`
6. `outline/title.txt`

`outline/outline.md` should include a short section titled `Middle-Book Progression Map` that covers the middle-third chapters using the criteria above. Keep it brief but concrete.
`outline/outline.md` should also include a short section titled `Supporting Character Pressure Map` covering the 3-6 key supporting characters identified above.

`outline/title.txt` contract:
1. A single line containing the novel's title. No subtitle, no quotation marks, no attribution — just the title itself.
2. The title should be literary, evocative, and appropriate to the premise's genre register. Avoid generic one-word titles unless the word is genuinely surprising. Avoid titles that over-explain the plot or read as taglines. The best titles create tension, ambiguity, or resonance that deepens after the novel is read — consider image, metaphor, irony, pressure-bearing objects, charged phrases, idiom-twists, place names, ritual language, jokes with bite, and double meanings drawn from the story's own material.
3. Before choosing the final title, silently brainstorm at least 8 materially different candidates. Do not just permute one template. Make the candidates vary in strategy: image-based, object-based, voicey phrase, irony, place-based, and strange or abrasive options if the novel supports them.
4. Do not default to dull prestige-title formulas such as solemn abstract-noun pairings, generic "The X of Y" constructions, interchangeable place-and-profession titles, or titles that sound like any competent literary novel could have used them.
5. A strong title may be funny, eerie, sensual, ugly, or formally odd if that better matches the book. Do not sand the title down into respectability if the novel's energy is sharper or stranger than that.

`outline/chapter_specs.jsonl` contract:
1. One JSON object per line.
2. Required fields per row:
3. `chapter_id` (format: `chapter_XX`)
4. `chapter_number` (int)
5. `projected_min_words` (int, > 0)
6. `chapter_engine` (string): the dominant mode of movement in the chapter, e.g. confrontation, discovery, aftermath, preparation, seduction, comic escalation, ritual, humiliation, constraint-heavy ordeal, pursuit, concealment, drift-under-pressure
7. `pressure_source` (string): what bears down on the chapter
8. `state_shift` (string): what changes by the end of the chapter. State shifts may be physical, emotional, relational, informational, perceptual, or tonal.
9. `texture_mode` (string): e.g. hot, quiet, suspended, tender, humiliating, uncanny, formal, comic, grief-heavy
10. `scene_count_target` (integer from 1 to 4)
11. `must_land_beats` (array of strings)
12. `secondary_character_beats` (optional array of strings): chapter-local instructions for how supporting characters should carry independent pressure or humanity on the page in this chapter
13. `setups_to_plant` (optional array of objects): use only for major cross-chapter seeds that later review/revision should be able to track explicitly. Each object requires `setup_id` (stable short identifier), `description` (what must become legible on the page here), and may include `payoff_window` (chapter or chapter range where it should plausibly land) and `visibility` (e.g. `light`, `moderate`, `heavy`)
14. `payoffs_to_land` (optional array of objects): use only for major cross-chapter landings. Each object requires `setup_id` (matching an earlier setup), `description` (what resolves or pays off here), and may include `seeded_by` (array of `chapter_XX` strings) and `payoff_type` (e.g. `reveal`, `reversal`, `object use`, `emotional payoff`, `capability`)

Keep `setups_to_plant` and `payoffs_to_land` sparse. Do not turn every minor echo into tracked metadata; reserve these fields for setups and payoffs whose presence or absence would materially affect later review or revision.

`outline/scene_plan.tsv` contract:
1. Header exactly:
2. `scene_id\tchapter_id\tscene_order\tobjective\topposition\tturn\tconsequence_cost\ttension_peak`
3. Use the `scene_count_target` from each chapter spec.
4. Single-scene chapters are allowed when compression increases force. Do not split a chapter into multiple scenes merely to satisfy format.
5. `tension_peak` values must be `YES` or `NO`.

`outline/style_bible.json` contract:
1. Must be valid JSON object.
2. Required top-level keys:
3. `character_voice_profiles` (array, non-empty)
4. `dialogue_rules` (object)
5. `prose_style_profile` (object)
6. `aesthetic_risk_policy` (object)
7. Each `character_voice_profiles` row requires:
8. `character_id`
9. `public_register`
10. `private_register`
11. `syntax_signature`
12. `lexical_signature` (string guidance, broad and non-prescriptive)
13. `forbidden_generic_lines` (string guidance describing generic line types to avoid)
14. `stress_tells` (string guidance describing variable stress behavior, not fixed repeated ticks)
15. `profanity_profile`
16. `contraction_level` (one of: `high`, `moderate`, `low`, `variable` — how often this character contracts in speech)
17. `interruption_habit` (string guidance: how this character interrupts, cuts in, or refuses interruption)
18. `self_correction_tendency` (string guidance: how this character revises themselves mid-speech under pressure)
19. `indirectness` (string guidance: how directly vs obliquely this character says difficult things)
20. `repetition_tolerance` (string guidance: how much purposeful repetition fits this character before it feels false or mechanical)
21. `evasion_style` (string guidance: how this character dodges, redirects, narrows, or withholds when cornered)
22. `sentence_completion_style` (string guidance: whether this character finishes, trails off, restarts, or repairs sentences under pressure)
23. `example_lines` (optional array of strings): if provided, these are CALIBRATION-ONLY samples showing this character's voice. They must NEVER be copied, paraphrased, or echoed in any draft. They exist solely to anchor register, rhythm, and tone for the drafting agent. Label them explicitly as non-copyable reference material. IMPORTANT: do NOT make every example line a character's "best" or most quotable moment. Include at least one example that is mundane, messy, or half-formed — a line where the character fumbles, says something obvious, trails off, repeats themselves, or produces ordinary connective speech. The calibration set should represent the character's full range, including their unremarkable moments, not just their most literary ones. If every example line is sharp, compressed, and perfectly landed, the drafting agent will calibrate to that register and produce dialogue that sounds composed rather than spoken.
24. The spoken-texture fields above should protect productive roughness, not force gimmicks. They should describe how the character sounds when speech gets messy — interruption, evasion, topic-slippage, self-repair, unfinished turns — without turning those features into repeated trademarks.
24b. Write voice profiles that allow characters to be unremarkable. Most real speech is functional, not literary. If every field describes the character at their most intense, sharpest, or most distinctive, the drafting agent will produce hyperactive characterization where every line performs voiceness. Include how the character sounds when they are bored, agreeable, tired, or simply filling social space. A character who is always "on" is a character who never feels real.
25. `aesthetic_risk_policy` must explicitly state whether profanity and dark content are allowed when narratively warranted.
26. `dialogue_rules` must include:
27. `anti_transcript_cadence` (boolean): prevents expository ping-pong dialogue. Does NOT mean every exchange must shift leverage — organic texture, small talk, and circling are valid dialogue modes.
28. `required_leverage_shifts_per_scene` (integer >= 0): applies to scenes with confrontation or negotiation. Non-crisis scenes (meals, transit, aftermath) may have zero leverage shifts and rely on social texture instead.
29. `max_consecutive_low_info_replies` (integer >= 2): limits consecutive low-info replies in expository or briefing-style exchanges only. This rule does NOT restrict organic small talk, social texture, meal conversation, aftermath exchanges, or any scene where characters are circling, stalling, or producing ordinary connective speech. Set to 2 or higher. Organic low-info exchanges ("Yeah." / "I know." / "So." / "Right.") are a feature of natural dialogue, not a defect.
30. `idiolect_separation_required` (boolean)
31. `default_contraction_use` (string describing baseline contraction policy for all dialogue — e.g. "high — contractions are the norm; uncontracted forms reserved for emphasis or character-specific formality")
32. `prose_style_profile` must include:
33. `narrative_tense` (string: the tense used consistently across the entire novel — typically "past tense" or "present tense"; all chapters must use the same tense), `narrative_distance`, `rhythm_target`, `sensory_bias` (array of non-empty strings naming the dominant sensory channels or scene-pressure domains), `diction`, `forbidden_drift_patterns` (array of non-empty strings naming prose drifts to avoid)
34. `chapter_texture_variance` (string guidance on varying chapter rhythm, pacing, and structural texture across the book so no two consecutive chapters feel structurally identical)
35. `aesthetic_risk_policy` must include:
36. `sanitization_disallowed` (boolean)
37. `dark_content_allowed_when_character_true` (boolean)
38. `profanity_allowed_when_scene_pressure_warrants` (boolean)
39. `euphemism_penalty` (non-empty string)
40. `creative_risk_policy` (non-empty string): guidance encouraging the novel to take creative risks — rendering difficult, uncomfortable, or taboo material with full specificity rather than retreating to safety
41. Encode aesthetic-risk guidance in operational terms (what to lean into, and how to resolve edge cases), not generic platitudes.
42. Every required string field in `outline/style_bible.json` must be non-empty (no blank strings).
43. Keep `lexical_signature`, `forbidden_generic_lines`, `stress_tells`, and the spoken-texture fields abstract and non-mechanical; do not provide token lists that force repeated wording.
44. Prefer broad behavioral tendencies over rigid checklists of exact phrases.
45. Before finishing, self-check `outline/style_bible.json` for empty values in required string fields.

`outline/continuity_sheet.json` contract:
1. Must be a valid JSON object. This is the single source of truth for factual consistency across parallel chapter drafting. It contains only verifiable facts about the story world — not style, voice, or thematic guidance (those belong in the style bible).
2. Required top-level keys (all required; arrays/objects may be empty if not applicable to the premise):
3. `characters` (array of objects, each with):
4. `character_id` (string, matching style bible), `age_at_story_start` (number or null), `physical_details` (string), `key_relationships` (object mapping character_id to relationship label), `occupation_status` (string), `aliases` (array of strings: all names/titles/references other characters use), `literacy_languages` (string: reading, writing, language abilities), `state_transitions` (array of objects with `chapter` and `change` fields for planned age changes, injuries, status shifts), `availability` (string: when present, absent, or dead)
5. `timeline` (object with):
6. `story_start` (string: season, year, context), `estimated_span` (string), `seasonal_track` (array of objects with `chapters` string range and `season`), `key_events` (array of objects with `event`, `timing`, and `chapter`)
7. `geography` (object with):
8. `primary_setting` (string), `key_locations` (array of objects with `name` and `details`), `distances` (array of strings: spatial relationships between key locations)
9. `world_rules` (array of strings): constraints on what is possible — laws, social rules, technology, physics, magic systems. Include period-specific rules for historical fiction. Empty array for contemporary realistic fiction with no special constraints.
10. `power_structure` (array of objects with `holder`, `over`, and `mechanism`): who has authority over whom and by what right
11. `objects` (array of objects with `name`, `owner`, `origin`, `status`, `chapter_introduced`): only objects that are plot-significant or could cause continuity errors if described inconsistently
12. `financial_state` (object with `debts` array and `income_sources` array): include only if economic stakes are part of the premise. Each debt has `creditor`, `amount`, `deadline`, `status`. Each income source has `source`, `amount`, `reliability`.
13. `knowledge_state` (array of objects with `character`, `knows`, `learned_in`, `hidden_from`): secrets, lies, and information asymmetries that affect character behavior. Only track knowledge that could cause a continuity error if a parallel drafter gets it wrong.
14. `environmental_constants` (array of strings): persistent sensory and environmental facts — recurring sounds, smells, weather patterns, architectural details that multiple chapters should reference consistently.
15. Aim for roughly 2000 words. Only consolidate entries if the sheet exceeds 3000 words. Populate only what the premise requires. A contemporary two-character story may need very few entries. A historical epic with complex finances and social hierarchy will need more.
16. Every string field must be non-empty when populated. Omit optional entries rather than leaving them blank.

Important:
1. Do not draft chapter prose in this stage.
2. Keep output strictly to the required files.
