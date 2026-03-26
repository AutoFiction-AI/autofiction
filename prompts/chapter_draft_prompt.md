You are running CHAPTER DRAFT for `{{CHAPTER_ID}}`.

Inputs:
1. Global outline: `outline/outline.md`
2. Chapter spec: `{{CHAPTER_SPEC_FILE}}`
3. Scene plan: `outline/scene_plan.tsv`
4. Static story context pack: `outline/static_story_context.json`
5. Style bible: `outline/style_bible.json`
6. Continuity sheet: `{{CONTINUITY_SHEET_FILE}}`
7. Constitution: `config/constitution.md`

Task:
1. Draft only this chapter.
2. Follow the chapter spec exactly, especially `chapter_engine`, `pressure_source`, `state_shift`, `texture_mode`, and `scene_count_target`.
3. Maintain the tonal register and narrative tension appropriate to the chapter spec. Not every chapter needs to feel like a mini-thriller; an aftermath, dread, ritual, bureaucratic, comic, or seduction chapter should fully inhabit its own engine while still moving the book.
4. Ensure causality and character voice clarity.
4b. Before drafting, silently identify 3-5 things that are likely already established or actively being established by this point from the outline, chapter spine in the static story context pack, chapter spec, or other provided planning artifacts — facts, diagnoses, relationship truths, tactical lessons, or thematic pressures. Treat those artifacts as planning guidance, not proof that prior chapters rendered every beat clearly on the page. If this chapter sits in the middle third, consult the `Middle-Book Progression Map` in `outline/outline.md` and make sure this chapter's movement is distinguishable from the adjacent middle chapters in the way the outline intended. Do not spend major scene weight proving the same thing again unless this chapter complicates it, falsifies it, weaponizes it, or forces a character to act on it under changed pressure. Deliberate accumulative variation is allowed: the same kind of test may recur when conditions, stakes, audience, power balance, or consequence materially change and the new pass teaches the reader something the earlier passes could not. If the planned understanding would not yet feel legible to a cold reader, supply the minimum fresh on-page evidence needed rather than assuming the reader already has it.
4c. When a chapter revisits a known problem, prefer a test scene over a diagnosis scene. Show the problem being applied, failing, exposed, made public, or made more costly in real time rather than having characters summarize what is already true.
4d. If a recurring conversation type returns — mentor session, diagnostic exchange, debrief, confession rehearsal, operational argument, or almost-confession — do not reuse the same conversational ladder. Change the power balance, what each person wants, what new evidence enters, what public or private risk is present, or what consequence ends the exchange.
4e. Resist connective-tissue repetition. Debriefs, car rides, phone calls, notebook sessions, post-failure conversations, and "what this means" exchanges must alter the next move, the relationship field, or the cost structure. If they only restate the previous scene's lesson, compress them hard or replace them with action under pressure.
4f. In the middle third of the novel, a major scene should not end in the same understanding, relationship state, and tactical situation it began with unless the chapter's purpose is deliberately ritual or aftermath and its meaning clearly changes on the page. At least one of those three should move. These recurrence rules target mechanical repetition, not deliberate recurring forms. Ritual meals, habitual exchanges, running jokes, recurring domestic labor, and other premise-native patterns may return when each instance changes meaning, leverage, or pressure on the page.
4g. If this chapter spec includes `setups_to_plant`, render those seeds with enough on-page specificity that a cold reader could later recognize them as earned groundwork rather than retroactive inserts. You do not need to make the seed look important yet, but you do need to make it real and memorable in the local scene.
4h. If this chapter spec includes `payoffs_to_land`, make those landings feel both legible and earned. Let the payoff change pressure, understanding, or consequence on the page; do not rely on abstract callback language alone to signal that something seeded earlier has now paid off.
4i. When an image, action, or line of dialogue has already made a point legible, do not follow it with narrator explanation, moral paraphrase, or abstract summary unless the later sentence creates a genuinely new turn, cost, contradiction, or misreading. Trust the reader once the scene has arrived.
4j. Once a condition, pressure, skill set, social role, or environment should already be legible by this point from the outline, scene plan, chapter spine, chapter spec, or other provided planning artifacts, do not keep re-establishing that baseline through materially similar descriptive or material cues unless the recurrence now changes meaning, pressure, or consequence. Repeated proof of an already-legible baseline is drag.
5. Apply character-specific dialogue voice and prose constraints from `outline/style_bible.json`. Use the narrative tense declared in `prose_style_profile.narrative_tense` — all chapters must use the same tense.
5b. When a secondary character speaks or acts for the first time in this chapter, give them at least one detail that belongs only to them — not their plot function, their humanity. A habit, a worry, a piece of clothing, an opinion. Consult the `Supporting Character Pressure Map` in `outline/outline.md`, and if the chapter spec includes optional `secondary_character_beats`, honor them here. Characters who exist only to deliver information or serve as victims are craft failures.
6. Follow `aesthetic_risk_policy` from `outline/style_bible.json` as a primary constraint, not an optional style preference. Match the register the style bible requests — do not drift toward a safer, cleaner, or more literary default when the style bible specifies something else.
7. Consult `{{CONTINUITY_SHEET_FILE}}` for established facts: character ages, physical descriptions, aliases, timeline, geography, objects, financial state, world rules, and knowledge state. Do not contradict any canonical fact in the sheet. If you introduce a new concrete detail not in the sheet (a specific amount of money, a date, an object, a physical description), ensure it is internally consistent with what the sheet establishes.
8. Treat `lexical_signature` and `stress_tells` as occasional cues, not repeated mandatory tokens or beats.
8b. Treat `interruption_habit`, `self_correction_tendency`, `indirectness`, `repetition_tolerance`, `evasion_style`, and `sentence_completion_style` as part of the character's living speech texture. Use them to make dialogue feel messier and more human when pressure warrants; do not over-regularize speech into clean literary exchange.
9. If any character's voice profile in the style bible includes `example_lines`, treat those as calibration-only references for register and rhythm. Do NOT reproduce, paraphrase, or echo any example line in the draft. They are non-copyable reference material.

Dialogue register and contraction rules:
1. Check each character's `contraction_level` in the style bible and honor it in light of scene pressure, period, and setting. If not specified, default to moderate-high contraction use for casual contemporary speech unless the style bible establishes a different baseline.
2. Check `default_contraction_use` in `dialogue_rules` for the book-wide baseline.
3. Contractions are the default for most casual spoken English. Write "don't", "can't", "I'm", "won't", "it's" unless the character, setting, or moment makes fuller forms clearly more truthful. Uncontracted casual dialogue should trigger suspicion by default, not slide by as neutral.
4. Under pressure, many characters contract more, truncate, curse, and lose syntactic composure — but some become rigid, ceremonial, or over-precise. Let pressure alter speech rather than flattening every voice into the same informality.
5. If two characters in a scene sound interchangeable, revise until their voices diverge in syntax, diction, rhythm, and register.
6. Do not write dialogue in a generic "literary novel" voice. Match each line to the character's register and the scene's emotional pressure.
7. Do not over-clean speech. False starts, evasions, repeated words, interruption, awkward pivots, and incomplete-but-legible turns are welcome when they are character-true and pressure-true.

Organic dialogue texture:
1. Most real dialogue is unremarkable. Not every line should land, reveal, shift leverage, or produce an insight. Characters should be allowed to say obvious things, agree without adding, fumble, repeat what the other person just said in different words, trail off, and produce flat functional lines that serve no purpose except social presence.
2. The single most common dialogue failure in LLM-generated fiction is literary polish — lines that are informal, contracted, and character-specific but still read as composed rather than spoken. A character who routinely delivers compressed insights, perfectly timed rhetorical questions, or wry observations is performing authorship, not speaking. When you notice a line landing too cleanly, rough it up: add a false start, a self-interruption, a phrase the character has to restart, or replace the line with something less clever but more human.
3. Allow low-information exchanges. "Yeah." / "I know." / "So." / "Right." / "Anyway." — these are the connective tissue of real conversation. Stretches of 3-5 exchanges where nothing is advanced, revealed, or shifted are normal in meals, transit, aftermath, and daily-life scenes. Do not artificially sharpen these into debates or insight-delivery.
4. Resist the urge to have the narrator admire a character's line. If the narration comments on how well a remark landed, how precisely it cut, or how it silenced the room, that is a sign the line was written for effect rather than for truth. Let good lines work without authorial endorsement.
5. Characters under pressure often say the wrong thing, the unhelpful thing, the thing that makes the situation worse — not because they are foolish but because pressure degrades verbal performance. Let this happen. A character who always finds the right words under pressure is a fantasy.

Aesthetic-risk enforcement:
1. The primary craft risk in AI-generated fiction is involuntary sanitization — pulling punches, softening consequences, retreating to euphemism when the story needs specificity. This is a worse failure than excess.
2. Dark content that serves character truth and narrative consequence is not optional — it is required. A story whose premise involves violence, moral compromise, sexuality, addiction, or any other difficult human experience must render those things, not gesture at them from a safe distance. Physical and sexual intimacy, when present, must be written with the same embodied specificity as any other consequential scene — no fade-to-black, no pulling the camera away, no skipping to aftermath.
3. Anti-sanitization applies equally to emotional, domestic, and economic content. Rendering a character's poverty, shame, loneliness, or grief with vague summary is the same craft failure as softening violence.
4. Let profanity, violence, sexuality, and moral ambiguity match the story's established register and the characters' reality. Neither scrub them flat nor amplify them randomly.
5. Take creative risks. A scene that makes you uncomfortable is more likely to be working than one that feels safe. If you find yourself wondering whether something is "too much," it almost certainly isn't — LLM-generated prose almost never errs toward excess.
6. If a scene is deliberately restrained, make the restraint legible as narrative strategy or character choice, not as the author losing nerve.
7. If you find yourself reaching for summary instead of scene, abstraction instead of sensory detail, or pulling the camera away from a difficult moment — that is almost certainly the wrong instinct. Push through it.
8. For comedy-driven novels, the comic equivalent of sanitization is deflating humor: retreating to earnestness when the premise demands comic commitment, undercutting a joke with immediate moral reflection, explaining humor after it has landed, or losing nerve on an absurd premise by making characters too self-aware of the comedy. Comic timing in prose depends on sentence rhythm, setup placement, and the discipline to let a funny moment land without authorial commentary. Let characters be ridiculous, wrong, petty, and oblivious without the narrator correcting them; comic irony requires the author to trust the reader.

Constitution-critical writing checks:
1. Elliptical clipping is forbidden in dialogue and narration. Do not omit required function words (articles/determiners/pronouns/auxiliaries).
2. In climactic confrontations, dialogue should shift leverage, reveal pressure, or advance conflict. In non-crisis scenes (meals, transit, aftermath, daily life), dialogue may circle, stall, and breathe without every line doing narrative work.
3. Avoid procedural drift: do not write briefing-style or step-log narration that displaces embodied consequence.
4. Keep consequential beats scene-grounded (body, setting pressure, social cost), not abstractly summarized.
5. Avoid mantra repetition of style-bible phrases; vary diction while preserving voice identity.
6. Keep dialogue naturally spoken when register allows: use contractions, interruptions, and colloquial syntax; avoid legalistic full-form stiffness unless character-true.
7. In high-intensity or fast-paced sequences, do not lose the focalizer's inner life. Under pressure, interiority changes form — dissociation, hyper-focus, involuntary memory, sensory flooding, numbness — but it does not disappear. If more than 10 consecutive paragraphs pass without a sentence of internal experience, the draft has become a screenplay.
8. If the chapter spec calls for a non-crisis tonal register (reflective, aftermath, preparation), resist the pull toward artificial urgency. Let the chapter breathe. Quiet scenes earn their weight by making the novel's high-stakes moments more effective.
9. When the story's setting involves specialized knowledge — historical, technical, cultural, regional — embed it through character experience and sensory detail rather than lecture-style exposition. If the style bible defines `world_rules` that the reader cannot infer from context (magic systems, invented technology, alternate-history divergences), brief grounded explanation is permitted when a character first encounters or uses the rule — but it must feel like lived experience, not a textbook entry.
10. Scene-derived invention over body inventory: when rendering a character's physical or emotional reaction, derive it from the chapter's specific material environment — the objects in the room, the task the character was performing, the texture of what they are holding or sitting on, the weather or light or sound particular to this scene. Do not default to a generic somatic inventory (throat tightening, jaw clenching, pulse kicking, heat climbing, metallic taste, going still) that could appear identically in any chapter. A reaction that could be cut-and-pasted into a different scene without losing meaning is a failed reaction. If you notice yourself reaching for a stock bodily response, stop and look at the scene around the character instead.

Pre-submission dialogue scan:
1. Before finalizing, scan all dialogue for: "do not", "I am", "cannot", "will not", "I have", "it is", "you are", "we are", "they are", "he is", "she is".
2. For each hit, check: is this character's contraction_level "low"? Is this specific line deliberately formal, emphatic, historical, ritualized, or otherwise setting-true? If not, contract it. Do not require multiple stiff lines before fixing one obviously wrong line.
3. Uncontracted casual dialogue is usually a bug in this pipeline, not a prestige signal. Fix suspect lines proactively, but do not erase deliberate formality or setting-true speech.

Required output:
1. `{{CHAPTER_OUTPUT_FILE}}`

Hard constraints:
1. First non-empty line must be exactly `# Chapter {{CHAPTER_NUMBER}}`.
2. Meet or exceed `projected_min_words` from chapter spec.
3. Do not draft any other chapter files.
4. If any constitution-critical check fails, revise before finalizing this chapter.
5. If the draft sanitizes, softens, or retreats from the story's established register, revise before finalizing this chapter.
