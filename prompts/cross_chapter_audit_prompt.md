You are running CROSS-CHAPTER AUDIT for cycle `{{CYCLE_PADDED}}`.

Inputs:
1. Full manuscript snapshot: `{{FULL_NOVEL_FILE}}`
2. Chapter specs: `outline/chapter_specs.jsonl`
3. Continuity sheet: `{{CONTINUITY_SHEET_FILE}}`
4. Style bible: `outline/style_bible.json`
5. Novel outline: `outline/outline.md`
6. Spatial layout: `{{SPATIAL_LAYOUT_FILE}}`
7. Constitution: `config/constitution.md`

Context isolation requirement:
1. Do not read prior cycle reviews, revision reports, or gate files.
2. Judge this snapshot only on cross-chapter redundancy and cross-chapter consistency.
3. Do not spend time on general craft, dialogue quality, pacing, dramatic architecture, or award readiness. Those belong to other stages.

Tool-use requirement:
1. You have access to shell tools and file-reading tools within the workspace.
2. For density and counting checks in this audit, you MUST use tools to produce exact counts. Do not estimate or eyeball frequencies.
3. In your private reasoning process, cite the exact command or method used before reporting a count.
4. When reporting a density percentage in a finding or summary, state both numerator and denominator explicitly.
5. Use exact counting methods. Do not use line-count shortcuts that count matching lines when you actually need token or sentence counts.

Counting definitions:
1. Prose lines: lines in `{{FULL_NOVEL_FILE}}` that contain at least one alphabetic character, excluding blank lines, markdown heading lines beginning with `#`, and horizontal rules.
2. Sentences: sentence-ending punctuation tokens (`.` `!` `?`) followed by whitespace or end-of-line. Count tokens, not matching lines.
3. Prose words: total word count of prose lines only (exclude heading lines and blank lines). Use a method equivalent to filtering to prose lines first, then counting words.
4. Word-count denominators for hedge density should be based on prose words, not headings.

Critical workflow constraint:
1. Do NOT read the manuscript sequentially from beginning to end. This will exhaust your context window before you perform any analysis. Use grep to locate specific passages, then read only the targeted line ranges you need for each comparison.
2. Do not read the continuity sheet, style bible, outline, or constitution cover-to-cover unless a specific check requires a specific field. Read targeted sections only.
3. After completing the mandatory comparison protocol (Steps 1-3 below), write a PRELIMINARY version of the output JSON to `{{CROSS_CHAPTER_AUDIT_FILE}}` with whatever character/setting findings you have so far. This ensures findings are preserved even if the session runs out of context during later density counting. Overwrite this file with the complete version when all checks are done.

Task:
1. Audit the full manuscript for two classes of defect only: redundancy and consistency.
2. Focus exclusively on what is repeated that should not be and what contradicts itself across chapters.
3. Every emitted finding must be mapped to the specific chapter that should be revised.
3b. Boundary-local rhythm, handoff quality, and chapter-to-chapter momentum are primarily judged by the local window audit stage. Focus your attention on quantitative redundancy, factual consistency, and prose-tic density across the full manuscript.
3c. Include spatial and geographic layout in your consistency checks. Use grep to find all mentions of key locations and verify that physical relationships are consistent across all chapters. This applies at both scales: micro-scale (rooms, floors, corridors, adjacency, visibility within a building or compound) and macro-scale (distance between settlements or landmarks, travel time, terrain, cardinal directions, relative positions). Spatial contradictions are HIGH findings. Chapters are drafted in parallel and spatial/geographic drift is expected and common.
3d. Flag character-associated repetitive actions across the full manuscript. Use grep to find recurring physical details or gestures co-occurring with specific character names. When the same character is described with the same physical action in 3 or more chapters with the same dramatic function, flag as MEDIUM on the later chapters. The first instance may be kept; subsequent repetitions should be varied or removed.
4. If a pattern affects multiple chapters, emit one finding per affected chapter rather than one shared omnibus finding.
5. Prefer concrete, revision-driving findings over vague commentary.
6. Be exhaustive within each check. Do not stop after finding the first few instances of a pattern — continue scanning the full manuscript for every affected chapter.
7. All grep commands, line counts, and line-number references must target `{{FULL_NOVEL_FILE}}` directly. Do not grep individual chapter files — their line numbers will not match the compiled manuscript.
8. Complete PART A (redundancy) fully before starting PART B (consistency). Within PART A, follow the mandatory comparison protocol below before any density counting.

Mandatory comparison protocol (complete before emitting ANY findings):

Step 1 — Character introduction registry: Use grep on `{{FULL_NOVEL_FILE}}` to find every chapter where each recurring named character's name appears. For each character, read the FIRST passage in the manuscript that physically describes them or states their role. Record the chapter, line numbers, and the specific descriptive phrases used (hair, build, clothing, age markers, distinguishing features, role or title, self-identifying dialogue). Then read EVERY subsequent chapter's first mention of that character and check whether it re-describes any of the same traits in the same or synonymous phrasing. The test is whether a reader who has been reading in order would experience the later description as redundant information they already have. Adjacent chapters (N and N+1) are the highest priority because same-character or same-setting re-description one chapter apart is the most jarring form of redundancy — and the form most commonly missed because the two chapters may have been drafted independently.

Step 2 — Setting arrival registry: Use grep on `{{FULL_NOVEL_FILE}}` to find every chapter where each recurring-space family is described on entry. Think in recurring-space families, not just exact place names: workplace/campus/building/lobby/floor/office/conference-room variants, and home/apartment/room/kitchen/hallway variants, belong to the same-space family when they are serving the same orienting function for the reader unless the text clearly establishes a genuinely different location. For each recurring-space family, record the chapter of first arrival and the key descriptive elements (exterior, interior layout, sensory inventory, atmosphere, condition). Then check every subsequent arrival in that same-space family for re-inventory of the same elements. Two visits to the same recurring-space family in consecutive or nearby chapters that both describe the space from scratch — even if the wording differs — constitute a re-description finding on the later chapter. The second visit should enter through what has changed, not through what remains.

Step 2b — Consecutive chapter descriptor cross-check: For every character introduced or recurring-space family first described in chapter N, grep for the KEY DESCRIPTIVE PHRASES and IDENTITY/ORIENTATION SIGNALS from that introduction in chapter N+1. Do not limit this to adjective reuse. Also compare repeated name-plus-role packages, self-identifying dialogue (`I'm X`, `I run Y here`, `I work on Z`), identity-summary sentences, and repeated orienting work for recurring spaces (exterior/entry/lobby/floor/layout/inventory). If chapter N introduces a character as having "dark hair with early gray" and chapter N+1 describes that same character with "dark hair showing early gray" or any synonymous phrasing of the same physical trait, that is a re-introduction finding on chapter N+1. Likewise, if chapter N teaches the reader who someone is through a name/role package and chapter N+1 re-teaches that same identity package, or chapter N teaches the reader a workplace/building/home orientation and chapter N+1 re-orients through the same entry/layout function even with different nouns, that is a finding on chapter N+1 — regardless of whether the narrative context differs (interview vs. first day, first visit vs. return visit, etc.). Do not rationalize away matches by classifying them as "intentional motifs," "deliberate evolution," or "earned re-description." If the same physical trait, identity package, or orienting function appears in both chapters, it is redundant for the reader. This step is mandatory even if the broader registry from Steps 1-2 found nothing, because adjacent-chapter redundancy is the form most commonly missed.

Step 3 — Formalize all character re-introduction and setting re-description findings from Steps 1-2b into finding objects. Then WRITE a preliminary version of the output JSON to `{{CROSS_CHAPTER_AUDIT_FILE}}` containing these findings (with `consistency_findings` as an empty array for now). This checkpoint ensures findings are preserved even if the session runs out of context during later steps. After writing the preliminary output, proceed to proof-of-baseline, image density, and counting tasks. Character re-introduction, setting re-description, and proof-of-baseline findings still have highest editorial priority, but they do NOT excuse skipping later count-based checks. This audit is exhaustive, not budgeted. If a later counting or density check identifies multiple affected chapters, emit one finding per affected chapter rather than collapsing to only the worst few. Overwrite `{{CROSS_CHAPTER_AUDIT_FILE}}` with the complete output when all checks are done.

PART A — Redundancy audit:

Checks 1-2 below define the CRITERIA for character re-introduction and setting re-description findings. The PROCEDURE for detecting them is the mandatory comparison protocol above. Do not re-do the comparison — apply these criteria to what the protocol found.

1. Character re-introductions. Flag any later chapter that re-describes a character's physical appearance, clothing style, build, distinguishing features, full name plus role, or self-identifying dialogue as if the reader has not already met them. The first full introduction is correct; later chapters should use only the minimum identifying detail needed. Social plausibility inside the scene does not excuse reader-facing redundancy: a line can be realistic for the characters to say and still be a re-introduction bug for the reader. Do not classify repeated descriptors as "intentional motifs," "deliberate evolution," "farewell rendering," or any other editorial rationalization — if the same physical trait appears in multiple chapter-entry passages, flag it and let the revision agent decide whether to keep or cut. Cite the original establishment location in `problem`.
2. Setting re-descriptions. Flag any later chapter that inventories a previously established space from scratch rather than re-entering it through change, contrast, or the new local pressure. Treat recurring-space families broadly, not narrowly: workplace/campus/building/lobby/floor/office/conference-room variants, and home/apartment/room/kitchen variants, belong to the same-space family when they are serving the same orienting function for the reader unless the text clearly establishes a genuinely different location. Repeated orienting work counts even when the wording differs: if the later chapter again teaches exterior, entry, lobby, layout, floor, or room inventory rather than entering through what has changed, that is a re-description defect.
3. Proof-of-baseline accumulation. Track how many times the manuscript independently proves the same character property or baseline condition: financial state, professional skill, occupation, physical condition, emotional disposition, institutional status, dependency, or constraint. Include repeated protagonist self-inventory and repeated middle-of-scene reminders, not just chapter openings. Flag later chapters when the same property has been proved more than three times without materially new information, leverage, or consequence. Also flag local-cluster redundancy regardless of the total count: if the same baseline is re-proved in adjacent chapters or in two of three nearby chapters without materially new leverage or consequence, that is a finding even if the manuscript-wide count is only two or three.
3b. Conversation and confrontation redundancy. Track conversations where the same moral argument, emotional reckoning, revealed wound, or relational confrontation is restaged across chapters with similar dramatic weight. This is distinct from proof-of-baseline (which tracks factual properties being re-proved) — it targets scenes where the same emotional or moral ground is covered again through dialogue or confrontation, even when the wording is entirely different. To locate candidates, grep for recurring character pairs that appear together in dialogue-heavy passages across multiple chapters, then read the relevant scenes to compare their dramatic function. The test is functional redundancy: if a reader would experience the later scene as ground already covered — the same wound re-examined, the same accusation relitigated, the same confession replayed — without materially new evidence, changed power dynamics, or consequence that alters the reader's relationship to the wound, flag the LATER chapter. Mark as MEDIUM when the later scene adds some new context, witness, or consequence. Mark as HIGH when the emotional content substantially overlaps and the later scene does not change what the reader understands about the relationship. In the evidence, cite the earlier establishment scene so the revision agent knows what has already landed.
4. Image and motif density. Count specific recurring nouns, sensory details, colors, sounds, smells, objects, and physical markers across the manuscript. Flag any specific image that appears more than 10 times unless it is explicitly functioning as a tracked motif or setup/payoff element in `outline/outline.md`. For images appearing 10-20 times, target keeping the strongest 4-6 instances. For images appearing 20+ times, target keeping at most 8-10. Emit one finding per affected chapter whose instance(s) should be cut, keeping the strongest retained locations implicit in `problem` and explicit where possible in `evidence`.
4b. Count `"It wasn't X. It was Y"`, `"It was not X. It was Y"`, and `"Not X. Y."` constructions across the manuscript. Report the total as `not_x_y_count`. Threshold: 4 per book. Emit one finding per affected chapter where the pattern materially contributes to the overuse.
4c. Count personification-of-abstraction constructions where an abstract noun is the grammatical subject performing a physical or human action. Report the total as `personified_abstraction_count`. Threshold: 8 per book. Emit one finding per affected chapter where the pattern materially contributes to the overuse.
4d. Count sentences where the grammatical subject is an abstract noun from this list: loss, grief, silence, absence, pain, weight, truth, fear, relief, anger, shame, dread, hope, loneliness, exhaustion, meaning, distance, cost, power. Report the total as `abstract_noun_subject_count`. This is a recurrence signal, not a finding, and does not carry severity by itself.
4e. Count figurative similes in prose lines and report the total as `simile_count`. Use exact tool-based counting. Focus on `like`- and comparison-based similes in narration, excluding dialogue, headings, and fixed-phrase predicate usages that are not functioning as comparisons. Threshold: about 1 per 1200 prose words book-wide. Emit one finding per affected chapter for chapters materially contributing above that rate, citing the strongest local instances and directing revision toward literal description unless the comparison is specific to the focalizer.
4f. Count `as if` constructions in prose lines and report the total as `as_if_count`. Use exact tool-based counting. Threshold: 1 per 2000 prose words. Emit one finding per affected chapter when the chapter materially contributes to the overuse, naming which instances should be cut or converted to literal observation.
4g. Count `the way` comparison templates in prose lines and report the total as `the_way_x_count`. Target constructions such as `the way he`, `the way she`, `the way they`, `the way you`, `the way someone`, and `the way people` followed by a verb phrase that functions as filler comparison rather than scene-specific recognition. Threshold: 4 per book. Emit one finding per affected chapter when the chapter materially contributes to the overuse, and direct revision toward literal description of what the focalizer actually sees.
4h. Voice convergence. Use exact grep-based evidence to scan for dominant sarcasm/wry-deflection lexical patterns across named speaking characters — for example `dry`, `dryly`, `deadpan`, `wry`, `wryly`, rhetorical `really?`, `sure`, `right`, and `"not that"` minimizations. If more than 2 named characters share the same register density without clear support from `outline/style_bible.json`, emit a MEDIUM finding per affected chapter identifying which character voice should be recentered to their style-bible fields (`public_register`, `private_register`, `indirectness`, `evasion_style`).
5. Em-dash and punctuation density. Count prose lines containing at least one em-dash (`—`). Compute density as em-dash-containing prose lines divided by total prose lines. If manuscript-wide density exceeds 10%, emit one finding for EVERY chapter whose own em-dash density materially exceeds 10%, not just the worst offenders. Chapters far above threshold may be HIGH; lesser but still noncompliant chapters may be MEDIUM. Each finding should give that chapter a concrete target that contributes to bringing manuscript-wide density below 8%.
6. Sentence-opener monotony. Count sentences beginning with common pronouns such as `He`, `She`, `They`, `I`, and `It`. Compute density as pronoun-opener sentences divided by total sentences. If any single pronoun opener exceeds 7% of total sentences manuscript-wide, emit one finding for EVERY chapter whose local contribution materially exceeds 7% for that opener or otherwise makes that manuscript-wide pattern worse.
7. Near-verbatim passages. Search for repeated multi-word sequences across chapter boundaries. A near-verbatim match is any passage of 10+ consecutive content words that appears in substantially the same form in more than one chapter, allowing minor inflection changes but not semantic rewording. This includes chapter-seam recaps and repeated scene-entry templates.
8. Qualifier and hedge-word density. Count occurrences of common hedging patterns such as `something`, `somehow`, `the particular [noun] of`, `the kind of`, `which was`, `as if`, `seemed to`, and `almost`. Compute per-pattern density as occurrences per total prose word count. Flag any pattern exceeding 1 occurrence per 800 words, and emit one finding per affected chapter where the pattern materially contributes to the manuscript-wide overuse.

PART B — Consistency audit:
1. Character details. Verify that named characters' physical descriptions, name spellings, ages, occupations, and key relationships remain consistent across chapters, using the continuity sheet as canonical where applicable.
2. Timeline. Verify that dates, seasons, day-of-week references, time-of-day references, and duration claims are internally consistent.
3. Geography and spatial continuity. Verify that locations, distances, travel times, and spatial relationships remain consistent. When `{{SPATIAL_LAYOUT_FILE}}` contains a non-null layout, treat it as the authoritative spatial ground truth for those facts.
4. Objects and possessions. Track significant objects, documents, vehicles, clothing, tools, supplies, and other meaningful possessions across chapters. Flag appearances, disappearances, and property changes that contradict prior state.
5. Financial and quantitative continuity. Track specific numbers such as money amounts, counts, measurements, and ages across chapters. Use tools to locate all relevant mentions when verifying a suspected contradiction.
6. Knowledge state. Track what each character knows and when they learn it. Flag action taken on not-yet-acquired knowledge or failure to act on already-acquired knowledge when that failure reads like a continuity bug rather than a dramatic choice.
7. World rules and mechanism continuity. Track recurring world mechanisms, institutional processes, and governing rules established in the novel. Flag unexplained changes in operation.
8. Progressive state tracking. Track significant characters' evolving capabilities, possessions, relationships, and knowledge chapter by chapter. Flag newly invoked capabilities or states that were not yet established, and established capabilities or possessions that disappear without explanation.
9. Pacing mismatch against `beat_budget`. Use `outline/chapter_specs.jsonl` and compare each chapter's actual rendered length against its declared `beat_budget` and `plot_importance`. When non-primary beats (importance `secondary` or `bridge`) render at more than 1.5x their `target_words`, emit a `pacing_mismatch_findings` entry for that chapter. This is specifically for cases where side-business swallows the chapter's primary dramatic work. Each entry must include `finding_id`, `chapter_id`, `beat`, `importance`, `target_words`, `actual_words`, `evidence`, `severity`, `problem`, `rewrite_direction`, and `acceptance_test`. Count these in `pacing_mismatch_count`.

Output requirements:
1. Write exactly one JSON object to `{{CROSS_CHAPTER_AUDIT_FILE}}`.
2. Use the current contract exactly. `cycle` must be the unquoted integer `{{CYCLE_INT}}`.
3. Always include `not_x_y_count`, `personified_abstraction_count`, `abstract_noun_subject_count`, `simile_count`, `as_if_count`, `the_way_x_count`, and `pacing_mismatch_count` as non-negative integers, even when they are zero.
4. Every finding must use `chapter_XX`, never shorthand.
5. Use `rewrite_direction`, not legacy names like `revision_directive`.
6. `evidence` must be a single string; flatten multiple citations into one semicolon-separated string.

`{{CROSS_CHAPTER_AUDIT_FILE}}` contract:
1. `cycle` (int)
2. `summary` (string)
3. `not_x_y_count` (int, >= 0)
4. `personified_abstraction_count` (int, >= 0)
5. `abstract_noun_subject_count` (int, >= 0)
6. `simile_count` (int, >= 0)
7. `as_if_count` (int, >= 0)
8. `the_way_x_count` (int, >= 0)
9. `pacing_mismatch_count` (int, >= 0)
10. `redundancy_findings` (array)
11. `consistency_findings` (array)
12. `pacing_mismatch_findings` (array)

Each finding object must include:
1. `finding_id`
2. `category` (`redundancy` or `consistency`)
3. `subcategory`
4. `severity` (`MEDIUM|HIGH|CRITICAL`)
5. `chapter_id`
6. `evidence`
7. `problem`
8. `rewrite_direction`
9. `acceptance_test`

Each `pacing_mismatch_findings` object must include:
1. `finding_id`
2. `chapter_id`
3. `beat`
4. `importance` (`primary|secondary|bridge`)
5. `target_words`
6. `actual_words`
7. `evidence`
8. `severity`
9. `problem`
10. `rewrite_direction`
11. `acceptance_test`

Finding quality requirements:
1. `problem` for redundancy findings must identify the earlier establishment location or strongest retained instance.
1b. `evidence` for redundancy findings should include both the earlier establishment citation and the later redundant citation whenever both are available.
2. `rewrite_direction` must say what to cut, keep, replace, or correct in the mapped chapter.
3. `acceptance_test` must be concrete and verifiable by reading the revised passage.
4. Do not emit empty arrays because you ran out of time. If the manuscript truly has no issues in one category, that array may be empty, but the summary should still reflect what you checked.
