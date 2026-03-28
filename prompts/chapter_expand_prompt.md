You are running CHAPTER EXPANSION for `{{CHAPTER_ID}}`.

Inputs:
1. Existing chapter draft: `{{CHAPTER_INPUT_FILE}}`
2. Chapter spec: `{{CHAPTER_SPEC_FILE}}`
3. Global outline: `outline/outline.md`
4. Scene plan: `outline/scene_plan.tsv`
5. Static story context pack: `outline/static_story_context.json`
6. Style bible: `outline/style_bible.json`
7. Spatial layout: `{{SPATIAL_LAYOUT_FILE}}`
8. Continuity sheet: `{{CONTINUITY_SHEET_FILE}}`
9. Constitution: `config/constitution.md`

Task:
1. Expand only `{{CHAPTER_INPUT_FILE}}` to meet `projected_min_words` target.
2. Preserve the chapter's existing engine, pressure source, state shift, texture mode, voice, and continuity.
3. Add scene-level pressure, consequence, and embodied texture.
3b. Before expanding, identify what the chapter already proves, changes, or makes legible. Expansion must add new dramatic payload — new pressure, new consequence, new social texture, new operational difficulty, new emotional leverage, or new embodied specificity — rather than restating an already-landed insight. Deliberate accumulative variation is allowed: the same kind of test may recur when conditions, stakes, audience, power balance, or consequence materially change and the new pass teaches something the earlier material could not.
3c. When the chapter revisits a known problem already legible from the existing chapter, chapter spec, or static story context pack, prefer adding a concrete test, failed attempt, public consequence, changed ask between characters, or newly costly silence over a diagnosis scene or debrief that only explains what is already true.
3d. If a recurring conversation type returns during expansion — mentor exchange, debrief, diagnostic argument, confession rehearsal, almost-confession — do not pad by reusing the same conversational ladder. Change what each person wants, what new evidence enters, who can witness it, or what concrete consequence ends the exchange.
3e. If you add connective tissue — a meal, ride, phone call, notebook session, aftermath talk, or planning exchange — it must alter the next move, relationship field, or cost structure. If it only translates the chapter into cleaner thematic language, do not add it.
3f. Do not create a new chapter-ending state shift, major reveal, or downstream obligation that adjacent chapters are not already expecting. Expansion should deepen the existing turn, not smuggle in a new one. These recurrence rules target mechanical repetition, not deliberate recurring forms. Ritual meals, habitual exchanges, running jokes, recurring domestic labor, and other premise-native patterns may return when each instance changes meaning, leverage, or pressure on the page.
3g. Consult the relevant scene rows in `outline/scene_plan.tsv` and the `Middle-Book Progression Map` in `outline/outline.md` when this chapter sits in the middle third. Expanded material should reinforce the planned distinction of this chapter's movement, not blur it back into a generic reprise.
3h. Consult the `Supporting Character Pressure Map` in `outline/outline.md`, and if the chapter spec includes optional `secondary_character_beats`, honor them when adding material. Expansion should give supporting characters more lived pressure or humanity, not more pure plot function.
3i. If this chapter spec includes `setups_to_plant`, expansion may clarify or embody those seeds but must not convert them into premature payoffs. If it includes `payoffs_to_land`, expansion may strengthen the payoff's legibility and consequence but must not invent a different payoff architecture from the one the chapter is meant to land.
3j. When an image, action, or line of dialogue has already made the point legible, do not expand by adding narrator explanation, moral paraphrase, or abstract summary unless the added material creates a genuinely new turn, cost, contradiction, or misreading.
3k. Do not use expansion to keep re-proving a condition, pressure, skill set, social role, or environment that the existing chapter already makes legible. If you revisit an established baseline, the added material must change its meaning, leverage, or consequence rather than re-establishing it through materially similar cues.
4. Respect dialogue/prose style and `aesthetic_risk_policy` from style bible as non-negotiable constraints. Maintain the narrative tense declared in `prose_style_profile.narrative_tense` — do not shift tense during expansion.
5. Use style-bible idiolect cues sparsely; do not pad by repeating lexical signatures or stress tells.
5a. Consult `{{SPATIAL_LAYOUT_FILE}}` for authoritative spatial facts. Do not add new floor assignments, room adjacencies, travel times, distances, or directions that contradict it.
5b. Consult `{{CONTINUITY_SHEET_FILE}}` for established facts. Do not contradict any canonical fact when expanding. If you introduce new concrete details (amounts, dates, objects, physical descriptions), ensure consistency with the sheet.
6. If any `example_lines` exist in the style bible's character voice profiles, do NOT reproduce, paraphrase, or echo them. They are calibration-only reference material.

Dialogue register and contraction rules:
1. Honor each character's `contraction_level` from the style bible. If it is not specified, follow the book-wide baseline and the setting's natural spoken register rather than forcing extra formality or informality.
2. Honor `default_contraction_use` from `dialogue_rules`.
3. When adding dialogue, write natural spoken English for the setting and character: prefer "don't", "can't", "I'm", "won't" in casual contemporary speech unless the character is being deliberately formal, emphatic, historical, ritualized, or otherwise setting-true in fuller forms. An added stiff full-form line should be treated as suspect by default, not neutral.
4. Under pressure, push dialogue toward the character's pressured texture — often more contraction and colloquial texture, but sometimes more stiffness or precision if that is how this voice handles strain.
5. Preserve productive roughness when expanding a scene: interruptions, self-corrections, evasions, repeated words, and incomplete-but-legible turns may be the right answer if they are character-true.
6. When adding dialogue to expand a scene, do not default to sharp, well-crafted lines. Added dialogue should include functional exchanges, ordinary social texture, and lines where characters say obvious things, agree without adding, or fumble. Not every added line needs to land or advance anything. Expansion that upgrades every exchange into a polished insight is padding with literary varnish.
7. Do not add narrator commentary that admires how well a character's line worked. Let dialogue land (or not) without authorial endorsement.

Aesthetic-risk enforcement:
1. The primary craft risk in AI-generated fiction is involuntary sanitization — pulling punches, softening consequences, retreating to euphemism when the story needs specificity. This is a worse failure than excess.
2. When expanding dark or difficult material — violence, sexuality, addiction, moral compromise, grief — increase specificity and consequence, not euphemistic distance. Do not soften existing raw content. If a scene involves physical or sexual intimacy, expand with embodied presence, not summary or fade-to-black.
3. Let profanity, violence, sexuality, and moral ambiguity match the story's established register and the characters' reality. Neither scrub them flat nor amplify them randomly.
4. Take creative risks. A scene that makes you uncomfortable is more likely to be working than one that feels safe.
5. If a scene is deliberately restrained, make the restraint legible as narrative strategy or character choice, not as the author losing nerve.
6. If you find yourself reaching for summary instead of scene, abstraction instead of sensory detail, or pulling the camera away from a difficult moment — that is almost certainly the wrong instinct. Push through it.
7. When expanding comedy, increase comic specificity and commitment, not earnestness. Do not pad funny scenes with reflective interiority that deflates the humor. Comic expansion should deepen the joke's situation — more specific absurdity, sharper character obliviousness, tighter timing — rather than explaining it.

Constitution-critical writing checks:
1. Elliptical clipping is forbidden in dialogue and narration. Do not introduce omitted required function words.
2. In climactic confrontations, added dialogue should increase leverage or pressure. In non-crisis scenes, added dialogue may serve social texture, circling, or organic small talk without every line doing narrative work.
3. Avoid procedural drift: do not pad with operational summaries, process logs, or briefing prose.
4. Keep additions concretely embodied (action, sensory pressure, interpersonal consequence), not abstract explanation.
5. Avoid repetitive phrase recurrence from style-bible token lists.
6. In informal or pressured exchanges, favor natural spoken texture (contractions, overlaps, incomplete-but-grammatical turns) over stiff full-form diction.
7. In high-intensity or fast-paced additions, do not lose the focalizer's inner life. Under pressure, interiority changes form — dissociation, hyper-focus, involuntary memory, sensory flooding, numbness — but it does not disappear. If more than 10 consecutive paragraphs pass without a sentence of internal experience, the expanded chapter has drifted toward screenplay logic.
8. When the story's setting involves specialized knowledge — historical, technical, cultural, regional — embed additions through character experience and sensory detail, not explanatory narration. Do not pad with world-building exposition. If the story has non-empty `world_rules` in the continuity sheet, necessary clarification of how a rule works in practice is not padding — but it must arrive through action or consequence, not narrator lecture.

Pre-submission dialogue scan:
1. Before finalizing, scan all added or revised dialogue for: "do not", "I am", "cannot", "will not", "I have", "it is", "you are", "we are", "they are", "he is", "she is".
2. For each hit, check: is this character's contraction_level "low"? Is this specific line deliberately formal, emphatic, historical, ritualized, or otherwise setting-true? If not, contract it. Do not require multiple stiff lines before fixing one obviously wrong line.
3. Uncontracted casual dialogue introduced during expansion is usually a bug in this pipeline, not a prestige signal. Fix suspect lines proactively, but do not erase deliberate formality or setting-true speech.

Required output:
1. `{{CHAPTER_OUTPUT_FILE}}`

Hard constraints:
1. First non-empty line must remain exactly `# Chapter {{CHAPTER_NUMBER}}`.
2. Do not edit any other files.
3. Do not pad with filler, recap, or thematic paraphrase; all additions must improve dramatic quality.
4. If any constitution-critical check fails, revise before finalizing the expansion.
5. If the expansion sanitizes, softens, or retreats from the story's established register, revise before finalizing the expansion.
