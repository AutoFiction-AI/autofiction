You are running FULL-BOOK AWARD REVIEW for cycle `{{CYCLE_PADDED}}`.

Inputs:
1. Full manuscript snapshot: `{{FULL_NOVEL_FILE}}`
2. Cycle story context pack: `{{GLOBAL_CYCLE_CONTEXT_FILE}}`
3. Style bible: `outline/style_bible.json`
4. Spatial layout: `{{SPATIAL_LAYOUT_FILE}}`
5. Continuity sheet: `{{CONTINUITY_SHEET_FILE}}`
6. Constitution: `config/constitution.md`

Context isolation requirement:
1. Do not read prior cycle reviews, revision reports, or gate files.
2. Judge this snapshot as a fresh major-award review assessing excellence in the novel's own mode.
3. When judging reader legibility or accidental obscurity, do not let the story context pack or continuity sheet fill in missing manuscript logic. Use those inputs to detect contradiction and prior establishment, not to rescue unclear on-page causality.

Task:
1. Evaluate major-award shortlist readiness.
2. Default to fail unless shortlist-level strength is evidenced.
3. Identify unresolved `MEDIUM+` blockers with concrete rewrite directions.
3b. Do not reward prestige-signaling over conviction.
3c. Do not penalize comedy, erotic charge, violence, fantasy, science fiction, horror, grotesquerie, or tonal strangeness merely for being non-realist, non-solemn, or aesthetically abrasive.
3d. Penalize those qualities only when they are ornamental, incoherent, or disconnected from the book's engine.
3e. Exhaustiveness requirement: do not stop once you have found enough evidence to justify `FAIL`. Continue auditing until you have identified the manuscript's most consequential remaining `MEDIUM+` blockers, including harder-to-prove dramatic, structural, pacing, POV, dialogue-architecture, and ending failures when present.
3f. Read the entire manuscript before finalizing the verdict. A decisive local or process-level failure discovered early in the book is not permission to stop looking for larger reader-facing problems elsewhere.
3g. Apply a second-pass counterfactual before finalizing: assume every currently listed finding were fixed perfectly and nothing else in the manuscript changed. If the book would still miss major-award shortlist readiness, the review is incomplete. Continue auditing and add the remaining independent blockers.
3h. Prefer consequential blockers over merely easy blockers. Findings should represent the defects most responsible for the book missing shortlist level, not only the defects that are easiest to quote, verify, or describe mechanically.
3i. Process or contract violations — including style-bible example-line leakage, copied calibration text, and other clear protocol breaches — must be reported when present, but they must not crowd out larger dramatic or structural problems. If such a violation is not actually one of the manuscript's most important reader-facing blockers, do not let it become the review's only substantial finding.
3j. When multiple failures are present, the review should reflect the book's true failure profile in ranked order of consequence. A small but decisive contract breach does not erase the obligation to report larger craft failures that would still matter after that breach was fixed.
3k. Be exhaustive, but keep findings genuinely distinct. If the same passage or chapter supports multiple materially different defects, you may emit multiple findings. Do not split one defect into near-synonymous findings with the same corrective work.
3l. Output contract discipline: write the current schema exactly. `cycle` must be the unquoted integer `{{CYCLE_INT}}`, not a zero-padded or quoted string like `"{{CYCLE_PADDED}}"`. Every chapter reference must use `chapter_XX`, not shorthand forms like `ch16`. Use current field names such as `problem` and `global_problem`, not legacy aliases like `description`.
3m. Cross-chapter redundancy and factual consistency are audited by a dedicated pass every cycle. Flag obvious cross-chapter issues such as double character introductions, contradicted facts, and near-verbatim repeated passages when you notice them, but do not pursue exhaustive cross-chapter counting or tracking at the expense of craft assessment. Your primary mandate is evaluating the manuscript's craft, structure, dialogue, and dramatic quality.
3n. `LOW` findings are allowed but optional. Use them sparingly for real non-blocking polish issues worth preserving once the major blockers are fixed. Never let `LOW` findings crowd out `MEDIUM+` blockers or pad the review with minor notes.
3o. Prose-tic counting and quantitative redundancy measurement are handled by dedicated audit stages. Your primary focus is twofold: (1) award-level craft judgment requiring full-novel context — character arcs, tonal trajectory, the ending, sanitization, thematic coherence, and reader-knowledge continuity across distant chapters; and (2) elevation findings — specific, grounded opportunities to take the novel from competent to exceptional. For ordinary full-book blockers, use `source: award_global`. For elevation findings, `source` must be `elevation` and `severity` must be `ELEVATION_HIGH` or `ELEVATION_MEDIUM`. `source` is always required for every finding. Do not encode elevation only in `severity`, and do not omit `source` on elevation findings. Every elevation finding must be grounded in specific line citations with a concrete rewrite direction, not generic workshop advice. Do not spend major attention on boundary-local or count-based issues owned more precisely by other stages.
3p. Elevation findings should stay chapter-actionable. The revision agent for the mapped chapter must be able to execute the change without needing whole-scene restructuring elsewhere.
4. Every finding must map to a specific chapter via `chapter_id` for actionable revision. Each chapter is revised independently by a separate agent that can only see and modify that chapter. Therefore: if a problem spans multiple chapters, emit a **separate finding for each affected chapter** with chapter-specific rewrite direction. Do not emit one finding covering multiple chapters — the revision agent for the mapped chapter has no ability to fix other chapters.
4b. For recurring book-wide patterns that affect 3+ chapters, you may use optional `pattern_findings` to group the shared diagnosis once while still providing chapter-local revision targets. If you use `pattern_findings`, include every materially affected chapter in `affected_chapters`, and provide a concrete `chapter_hit` with local evidence, rewrite direction, and acceptance test for each chapter you want revised. If you are unsure about weaker chapters, do not overclaim scope: only list chapters you can support concretely.
4c. Use ordinary `findings` for one-off blockers and `pattern_findings` for repeated book-wide patterns. Do not duplicate the same chapter-local hit in both places unless that chapter also has a separate independent blocker.
4d. If you cannot supply a complete `pattern_findings` object with `pattern_id`, `affected_chapters`, and chapter-local `chapter_hits`, do **not** emit a partial pattern object. Fall back to ordinary per-chapter `findings` instead. A malformed pattern block will not propagate to revision.

Elevation categories to scan for when they are genuinely high-leverage in this specific novel:
1. `E1` Subtext gaps.
2. `E2` Dramatic irony exploitation.
3. `E3` Competing desires in dialogue.
4. `E4` Emotional complexity.
5. `E5` Status transactions.
6. `E6` Withholding within scenes.
7. `E7` Lived-in specificity.
8. `E8` Silence and negative space.
9. `E9` The unsaid.
10. `E10` Object/image threading.
11. `E11` Consequence bleed.
12. `E12` Tonal contrast.
13. `E13` Endings that reframe.
14. `E14` Genre promise fulfillment.
15. `E15` Question queue management.
16. `E16` Character distinctness under pressure.
17. `E17` Information asymmetry exploitation.
18. `E18` Earned peaks.
19. `E19` Soft-middle energy curve.
20. `E20` Spatial establishment and mental-map legibility.
21. `E21` Prose and scene-level specificity. Flag scenes where the writing defaults to generic description when something concrete and particular to this world, this character, or this body would serve. The goal is specificity and surprise through detail, not through conspicuous literary craft.

Elevation routing defaults:
1. `E1`, `E6`, and `E8` route to `pass_hint: p1_structural_craft`.
2. `E3`, `E5`, and `E16` route to `pass_hint: p2_dialogue_idiolect_cadence`.
3. `E2`, `E4`, `E7`, `E9`, `E10`, `E11`, `E12`, `E13`, `E14`, `E15`, `E17`, `E18`, `E19`, and `E20` route to `pass_hint: p1_structural_craft`.
4. `E21` routes to `pass_hint: p3_prose_copyedit` by default. Override to `p1_structural_craft` only when the specificity problem truly requires scene restructuring rather than sentence-level or paragraph-level revision.
5. Include cross-chapter voice and style consistency judgment against `outline/style_bible.json`.
5b. Check narrative tense consistency across all chapters against `prose_style_profile.narrative_tense` in the style bible. If any chapter uses a different tense from the declared canonical tense, flag as HIGH. Tense drift between chapters is a fundamental coherence failure — parallel drafting makes it likely, so it must be explicitly checked.
5c. If `{{SPATIAL_LAYOUT_FILE}}` contains a non-null layout, evaluate not only factual consistency with that document but reader legibility: does the manuscript make the spatial relationships intelligible on the page, or does it rely on hidden planner knowledge?
6. Flag cross-chapter factual and logical inconsistencies as HIGH. Use `{{CONTINUITY_SHEET_FILE}}` as the canonical reference for character ages, timeline, geography, objects, financial state, world rules, and knowledge state. Flag: timeline contradictions (seasons or dates that conflict with the sheet's seasonal track), character state mismatches (age, injury, possession, or relationship status that contradicts the sheet or another chapter), spatial impossibilities, violated world rules, and dropped or contradicted plot threads. Chapters are drafted in parallel and do not see each other — these errors are expected and must be caught here.
6b. Flag convenience architecture as MEDIUM or HIGH per affected chapter. Hidden rooms, uncatalogued archives, overheard secrets, lucky wrong turns, or other plot-critical concealment devices must feel causally earned: why this character, why now, why not someone else already, and what immediate cost or constraint keeps the discovery from being a handout. Emit a separate finding for each chapter where the convenience appears.
6c. Flag accidental obscurity as MEDIUM or HIGH per affected chapter. When a scene depends on a specialized process — technical, magical, legal, financial, military, artistic, erotic, scientific, or otherwise expert — check whether the manuscript preserves deeper mystery while keeping the local operative logic legible. A cold reader should still be able to say what the character is trying to do, what visible feedback they get, what remains uncertain, and why another character can understand enough to act. If the book repeatedly relies on mystery where local causality should be, emit separate findings per affected chapter.
6d. Flag underseeded payoff or late-arriving solution per affected chapter. If a reveal, capability, object use, emotional reversal, interpretive breakthrough, or crisis escape carries major dramatic weight but lacks sufficient setup earlier in the manuscript, emit a finding for the chapter where the payoff lands and, when useful, separate companion findings for the chapters where the missing setup should have occurred. This is distinct from convenience: a beat can be causally possible yet still feel underprepared. When the chapter spine in the story context pack includes explicit `setups_to_plant` or `payoffs_to_land` metadata, use it. Emit setup-chapter findings when a planned tracked seed never becomes truly legible on the page, and payoff-chapter findings when a planned landing still feels underprepared despite the intended seed architecture.
6e. Flag recurring baseline contradictions as MEDIUM or HIGH per affected chapter. These include habitual timing claims, routine operational patterns, stable behavioral baselines, and other long-observed defaults for recurring people, places, or systems that the continuity sheet may not explicitly encode. If one chapter presents a pattern as "usually," "most nights," "always," "never," "dependable," or otherwise long-established, and a later chapter presents a materially different baseline without clearly signaling that conditions changed, treat that as a continuity failure. Examples include who is usually awake or asleep at a given hour, how long a recurring task or commute normally takes, when a shift quiets down, what equipment habitually malfunctions, or what level of competence, confusion, or vigilance a recurring character normally shows. Mark as HIGH when the contradiction materially affects plot logic, exposure windows, or reader trust in the novel's causal architecture; otherwise mark as MEDIUM.
6f. Flag reader-knowledge continuity failures as MEDIUM per affected chapter. If a later chapter spends substantial paragraph-level weight re-teaching an already-established condition, role, wound, skill set, environment, routine, institutional baseline, object baseline, or pressure in substantially the same dramatic function, treat that as a continuity failure of what the reader is already supposed to know unless the recurrence clearly changes meaning, leverage, or consequence. This includes repeated protagonist self-inventory, repeated arrival or reorientation language, repeated environmental baseline packages, and repeated material proof of already-legible hardship, competence, training, shame, desire, dependency, or institutional constraint. Do not excuse this merely because the prose is vivid, premise-true, or thematically relevant: if the chapter behaves as though the baseline is newly informative when the manuscript has already taught it, emit a finding for the later chapter. When this same baseline-reorientation failure affects 3 or more chapters, you must use `pattern_findings` with a separate `chapter_hits[]` entry for each materially affected chapter rather than burying the issue in summary prose.
7. Flag book-level sanitization patterns as HIGH: if the premise promises dark/difficult material but the prose consistently flinches from specificity, defaults to euphemism, or inserts moral safety valves after every uncomfortable moment, this is a structural craft failure. Also flag book-level timidity — where the novel consistently avoids the difficult scenes its premise demands — as MEDIUM. In particular, flag intimacy fade-to-black patterns: if the novel contains a romantic or sexual relationship but consistently cuts away from physical intimacy, summarizes it, or jumps to aftermath, this is a HIGH sanitization finding — it is the content type most prone to involuntary self-censorship.
7b. For premises with comedy, dark comedy, tragicomedy, or comedy-drama as a primary or secondary engine, sustained humor is a feature, not a flaw — do not flag it as lack of consequence or sanitization. Evaluate whether humor is character-driven and situationally earned, rather than whether the novel is "serious enough." Do not flag comic escalation as lack of consequence; absurd, humiliating, or disproportionate consequences are valid in comic novels. Flag comedy failures as findings: jokes that rely on narrator commentary rather than character action, humor that breaks the established world's internal rules for a cheap laugh, comic set-pieces that have no consequence or character development, and tonal inconsistency where the novel oscillates between committed comedy and earnest drama without earning the shifts.
7d. Flag comedy sanitization as HIGH when the style bible specifies a crude, profane, or raunchy comedy register and the manuscript delivers a materially cleaner register instead. Compare the style bible's profanity profiles, aesthetic risk policy, and dialogue rules against the actual dialogue on the page. If the gap between requested register and delivered register is significant, emit per-chapter findings for the worst offenders with specific line citations and rewrite direction to match the requested register.
7c. When assessing seriousness, distinguish between gravity and weight. A comic or strange novel may be weighty without being solemn. A dark or explicit novel may be artistically controlled without being conventionally tasteful.
8. Make rewrite directions actionable and local: include target spans/lines in `{{FULL_NOVEL_FILE}}:<line>` form; strategy options are allowed; percentage-only directives are forbidden unless scenes are explicitly named.
9. Make acceptance tests concrete and verifiable by reading the revised passage, with explicit pass/fail criteria anchored to specific lines/spans. Avoid purely mechanical bean-counting tests.
9b. Avoid underfiring. If the review produces only one or two findings, verify that fixing those findings alone would plausibly make this specific manuscript shortlist-ready. If not, the finding set is incomplete and must be expanded.
10. Flag repetitive overfitting to style-bible token lists when it creates mantra-like diction across chapters. Emit a separate finding for each chapter that contains the problematic tokens, with chapter-specific replacement guidance.
10b. Flag structural recurrence across chapters. If multiple chapters restage the same conflict, reveal, relational diagnosis, debrief, bridge exchange, or moral argument in materially the same shape, emit a separate finding for each weaker or redundant chapter. A valid reprise must introduce at least one new fact, new cost, new witness or audience, new operational test, new public consequence, new irreversible action, or changed relationship leverage. In middle-book chapters, ending with the same central understanding, relationship state, and tactical situation is strong evidence of this failure. Bridge scenes count when they mainly translate previous action into cleaner thematic language rather than creating new pressure. Do not penalize deliberate motif, obsession, ritual, running jokes, or recurring domestic routines when each recurrence changes pressure or meaning. Deliberate accumulative variation — the same kind of test under materially changed conditions — is not a defect.
10c. Flag chapter-level sprawl and overstatement. If a chapter materially exceeds the dramatic work it needs to do because later pages keep restating a turn that already landed — informationally, morally, emotionally, or relationally — emit a separate finding for that chapter. This includes chapters that land meaning through concrete scene action and then keep translating that meaning into abstract summary, moral paraphrase, or thesis language. Distinguish earned expansiveness from padding: do not penalize long chapters that carry multiple distinct turns, but do penalize chapters whose later pages mostly paraphrase an already-achieved insight, grievance, recognition, or reconciliation.
11. Flag dialogue that is globally over-formal/stilted where character and scene pressure should produce contractions, slang, interruption, and colloquial texture.
11b. Do not penalize messy, evasive, or socially awkward speech merely for being untidy. Slight disfluency, repetition, interruption, false starts, topic-slippage, and incomplete-but-legible turns are often signs of living dialogue when they are character-true.
11c. Penalize the cleaner failure instead: chapters that convert pressure into neatly balanced debate lines, explanatory mini-speeches, explicit emotional thesis statements, compressed insights, mic-drop rhetorical questions, aphoristic dialogue, or lines that sound written-to-land rather than spoken. Narrator admiration of how a line "landed," "cut," or "silenced the room" is corroborating evidence, not a separate requirement. Emit a separate finding per affected chapter with specific line citations. Mark as MEDIUM per chapter, HIGH if it is the book's dominant dialogue register.
11d. Flag dialogue-template recurrence across chapters. If a pair or class of scenes keeps reusing the same conversational ladder — question-correction-explanation, accusation-technical deflection-human rejoinder, offer-refusal-restatement, or similar — emit separate findings for the weaker or more repetitive chapters. Repeated speech habits are only a defect when they stop carrying new dramatic pressure and begin sounding generated.
11e. When auditing composed dialogue, explicitly scan for the distinct sub-modes named above — mini-speech diagnosis, aphorism, rhetorical mic-drop, balanced debate line, and narrator admiration — even if you consolidate them into one chapter finding. Consolidation should reduce duplicate findings, not reduce the thoroughness of the scan.
11f. Flag book-level dialogue-interiority suppression. If multiple chapters contain dialogue scenes where the focalizer's mind goes quiet — no recognition, relational worry, experience-based context, or social-dynamic tracking between lines of exchange — and the reader is left parsing jargon, insider shorthand, or compressed loaded exchange without the focalizer's interiority to follow alongside, emit a separate finding per affected chapter. This is the inverse of composed dialogue: where composed dialogue is too written, suppressed-interiority dialogue is too bare. Mark as MEDIUM per chapter. Mark as HIGH if it is the book's dominant dialogue texture. In `rewrite_direction`, explicitly tell the reviser to restore focalizer interiority between lines of exchange rather than merely making the dialogue more explicit or explanatory.
Dialogue register audit:
1. Check characters' `contraction_level` fields in the style bible. Flag unjustified full-form dialogue whenever it makes a line or exchange read stiffer than the character, scene, period, and world support; do not wait for chapter-scale collapse before noticing it. Do not flag deliberate formality, ritual language, legalistic speech, historical cadence, or emphatic full-form diction when character-true. If the mismatch recurs across multiple chapters, emit a separate finding per affected chapter with chapter-specific line citations.
2. Flag scenes where two or more characters sound interchangeable in register, syntax, and rhythm.
2b. When the style bible encodes interruption habits, self-correction tendencies, indirectness, repetition tolerance, evasion style, or sentence-completion style, assess whether the manuscript preserves those pressures at the level of speech texture. Do not reward chapters for sanding them away into cleaner generic dialogue.
3. If any `example_lines` from the style bible appear verbatim or near-verbatim in the manuscript, flag as a finding. Mark as MEDIUM by default. Escalate to HIGH for repeated leakage, leakage in chapter-defining emotional or structural beats, or copying conspicuous enough to damage the book's voice integrity on first read.

Required output:
1. `{{FULL_AWARD_OUTPUT_FILE}}`
2. The `summary` must describe the manuscript's principal failure modes in order of consequence. Do not summarize only the first decisive fail if deeper or broader blockers remain.
3. If the listed findings are few, the `summary` must make clear why fixing only those findings would plausibly change the verdict.
3b. If you emit any item in `findings` or any actionable `pattern_findings.chapter_hits`, the `verdict` must be `FAIL`. `PASS` is allowed only when there are no findings at all.

`{{FULL_AWARD_OUTPUT_FILE}}` contract:
1. `cycle` (int; write `{{CYCLE_INT}}`, not `"{{CYCLE_PADDED}}"`)
2. `verdict` (`PASS|FAIL`)
3. `summary` (string)
4. `findings` (array of objects) for one-off blockers. This array may be empty only if every blocker is represented in `pattern_findings`.
4a. If `findings` is non-empty, `verdict` must be `FAIL`.
4b. Use current field names only. For ordinary findings, use `problem`, not `description`. For pattern findings, use `global_problem`, not `description`.
5. Each `findings[]` object must include:
6. `finding_id`
7. `source` (`award_global|elevation`; always required. Do not omit it. Do not represent elevation solely via `severity`.)
8. `severity` (`LOW|MEDIUM|HIGH|CRITICAL|ELEVATION_MEDIUM|ELEVATION_HIGH`)
9. `chapter_id` (`chapter_XX`; never `ch16` or other shorthand)
10. `evidence` (single string; if you cite multiple locations, flatten them into one string separated by semicolons, e.g. `{{FULL_NOVEL_FILE}}:12; {{FULL_NOVEL_FILE}}:18`)
11. `problem`
12. `rewrite_direction` (must include local target spans/lines in `{{FULL_NOVEL_FILE}}:<line>` form; strategy options allowed; percentage-only directives are forbidden unless scenes are explicitly named)
13. `acceptance_test` (concrete and verifiable by reading the revised passage, with pass/fail criteria tied to specific lines/spans)
13. Optional `pattern_findings` (array of objects) for recurring book-wide patterns that affect multiple chapters. Each object should include:
13b. `pattern_findings` is required, not optional, when the same baseline-reorientation or reader-knowledge continuity failure materially affects 3 or more chapters. In that case, include one `chapter_hits[]` entry per affected chapter rather than summarizing the pattern only at book level.
13c. If any `pattern_findings` object contains actionable `chapter_hits`, `verdict` must be `FAIL`.
14. `pattern_id` (short stable identifier, e.g. `PROSE_AUTOCOMM`)
15. `severity` (`LOW|MEDIUM|HIGH|CRITICAL|ELEVATION_MEDIUM|ELEVATION_HIGH`)
16. `global_problem` (brief shared diagnosis for the whole pattern)
17. `affected_chapters` (array of `chapter_XX` ids covering every materially affected chapter you are claiming)
18. Optional `global_rewrite_principles` (shared cross-chapter correction principles)
19. `chapter_hits` (array of chapter-local actionable hits). Each `chapter_hits[]` object must include:
20. `chapter_id` (`chapter_XX`; never shorthand)
21. `evidence` (single string; flatten multiple citations into one semicolon-separated string when needed)
22. `problem` (chapter-local version of the defect; may reuse the shared diagnosis if that is still locally specific enough)
23. `rewrite_direction` (must include local target spans/lines in `{{FULL_NOVEL_FILE}}:<line>` form)
24. `acceptance_test` (chapter-local pass/fail criteria tied to specific lines/spans)
25. Optional `finding_id` on `chapter_hits[]` if you want to control the per-chapter id explicitly

Valid shape example for one ordinary `findings[]` item:
```json
{
  "finding_id": "CH07_OVEREXPLAINED_ENDING",
  "source": "award_global",
  "severity": "MEDIUM",
  "chapter_id": "chapter_07",
  "evidence": "{{FULL_NOVEL_FILE}}:1402; {{FULL_NOVEL_FILE}}:1418",
  "problem": "After the scene's central turn lands on the page, the closing paragraphs restate the same realization in cleaner thematic language rather than creating new pressure.",
  "rewrite_direction": "Revise {{FULL_NOVEL_FILE}}:1402-1420. Cut or compress the explanatory closing material so the chapter ends on the already-earned action and image instead of paraphrasing its meaning.",
  "acceptance_test": "Pass if {{FULL_NOVEL_FILE}}:1402-1420 now ends on concrete scene consequence without abstract restatement of the same insight. Fail if the revised closing still paraphrases what the reader already understood from the prior beat."
}
```

Valid shape example for one elevation `findings[]` item:
```json
{
  "finding_id": "CH09_ELEVATION_NEGATIVE_SPACE",
  "source": "elevation",
  "severity": "ELEVATION_HIGH",
  "chapter_id": "chapter_09",
  "evidence": "{{FULL_NOVEL_FILE}}:1880; {{FULL_NOVEL_FILE}}:1896",
  "problem": "The confrontation states the emotional conclusion directly instead of letting the silence and the missed response do the work.",
  "rewrite_direction": "Revise {{FULL_NOVEL_FILE}}:1880-1898. Cut the explicit interpretive lines and let the beat land through the unspoken reaction, physical business, and the deferred answer.",
  "acceptance_test": "Pass if the revised span creates sharper emotional aftershock through omission and reaction rather than explicit paraphrase. Fail if the scene still explains the feeling in direct thematic language."
}
```

Valid shape example for one `pattern_findings[]` item:
```json
{
  "pattern_id": "EM_DASH_DENSITY",
  "severity": "HIGH",
  "global_problem": "Em-dash density has become a manuscript-wide rhythmic tic, flattening emphasis and making interruption feel like the default prose texture.",
  "affected_chapters": ["chapter_07", "chapter_11"],
  "global_rewrite_principles": "Replace non-essential em-dashes with commas, periods, or colons. Keep em-dashes only where interruption or fracture is doing real dramatic work.",
  "chapter_hits": [
    {
      "finding_id": "EM_DASH_DENSITY_CH07",
      "chapter_id": "chapter_07",
      "evidence": "{{FULL_NOVEL_FILE}}:1402; {{FULL_NOVEL_FILE}}:1418",
      "problem": "Chapter 7 stacks em-dashes in explanatory narration until the prose loses pressure and starts sounding mechanically interrupted.",
      "rewrite_direction": "Revise {{FULL_NOVEL_FILE}}:1402-1420. Replace non-essential em-dashes with stronger sentence boundaries or commas.",
      "acceptance_test": "Pass if the revised span uses materially fewer em-dashes and reads with clearer clause control. Fail if interruption still feels like the default punctuation rhythm in the cited lines."
    },
    {
      "finding_id": "EM_DASH_DENSITY_CH11",
      "chapter_id": "chapter_11",
      "evidence": "{{FULL_NOVEL_FILE}}:2240; {{FULL_NOVEL_FILE}}:2261",
      "problem": "Chapter 11 repeats the same em-dash-heavy interruption rhythm, diluting emphasis.",
      "rewrite_direction": "Revise {{FULL_NOVEL_FILE}}:2240-2265. Keep only the em-dashes that mark genuine interruption or fracture.",
      "acceptance_test": "Pass if the revised span reserves em-dashes for actual interruption rather than routine apposition. Fail if the same punctuation pattern still dominates the cited lines."
    }
  ]
}
```
