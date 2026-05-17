You are running THEME COHERENCE AUDIT for cycle `{{CYCLE_PADDED}}`.

Inputs:
1. Full manuscript snapshot: `{{FULL_NOVEL_FILE}}`
2. Chapter line index: `{{CHAPTER_LINE_INDEX_FILE}}`
3. Outline: `outline/outline.md` (used to know what the book *intended* to be about; you judge what the book is *actually* about)
4. Constitution: `config/constitution.md`

Context isolation requirement:
1. Do not read prior cycle reviews, gate files, or revision reports.
2. The outline tells you what the book set out to mean. The manuscript shows what it landed. Where the manuscript means more than the outline planned, that is good; where the manuscript means less, that is the finding.

Scope:
1. Award-level fiction usually means something cumulatively. Not "has a theme" in the high-school sense — but accumulates a moral, philosophical, or felt intelligence across its length that the reader leaves the book carrying.
2. Plot can pass without meaning. A novel can be competently constructed and forgettable. This stage exists because the other gates measure construction; this gate asks whether the construction is *for* anything.
3. Be specific. "The book lacks thematic resonance" is useless. Name what the book is about, what it is trying to ask, and where it engages or evades the question.

Mandatory checks — for each, anchor findings to specific lines or chapter spans in `{{FULL_NOVEL_FILE}}:<line>` form:

TC1. `central_question` — what is the central question, problem, or pressure the book is engaging? Name it in one sentence in your own words. Cite the lines that establish it most clearly. If you cannot identify a central question, the book is not yet about anything; report this as a HIGH finding.

TC2. `engagement_with_question` — does the book engage its central question, or does it dance around it while being about something more familiar? Specifically: (a) does the book *test* the question through scene material (action, decision, cost, consequence), or only *gesture* at it through reflection? (b) does the question accumulate weight as the book progresses, or stall after the first establishment?

TC3. `recurring_image_audit` — name every recurring image, motif, object, or refrain that appears three or more times across the book. For each: load-bearing (the recurrences accumulate meaning) or decorative (the recurrences are repetition without accumulation). Cite three of the recurrences for each.

TC4. `motif_payoff` — for each load-bearing recurrence: where does it pay off? Does the final recurrence carry weight the earlier recurrences set up, or does the final one merely repeat the earlier? Award books usually finish their motifs with a payoff that depends on the prior plantings.

TC5. `idea_tested_through_character_cost` — the test of whether a book engages an idea is not whether characters discuss it, but whether characters *pay* for it. Identify where in the book the central question costs a character something concrete — a relationship, a body, a commitment, a future. If the question is never paid for, the book is not yet engaging it.

TC6. `evasion_pattern` — the most common failure of meaning is evasion: the book gestures at the harder version of its question and then lands on a softer adjacent question that is easier to resolve. Identify any place where the book had the chance to push into harder ground and chose easier ground. Cite the evasion.

TC7. `thematic_register_match` — does the book's prose register match the seriousness of what it is trying to mean? A book asking grave questions in chatty register, or trivial questions in heavy register, has a register mismatch with its theme. Identify any mismatch.

TC8. `thesis_speech_failure` — many books that lack thematic legibility try to fix it with a character giving a thesis speech that names the theme out loud. This is the worst possible solution; it converts what should be felt into what is told. Identify any thesis speeches and flag them. The fix is not to remove the speech and substitute a quieter narrator paraphrase — the fix is to plant the meaning in scene material so the thesis is unnecessary.

TC9. `narrator_thematic_underlining` — narrator sentences that interpret what a scene means after the scene already showed it. The chapter_review and revision prompts target this at the prose level; you judge it at the thematic level: is the book's narrator constantly repackaging meaning into abstract closing sentences? Identify clusters.

TC10. `what_book_has_to_say` — in one paragraph, in your own words: what does this book have to say? Not what is its plot, not what does it depict, but what does it *say* about its subject? If you cannot fill this paragraph, the book has not yet said anything.

TC11. `would_a_reader_argue_with_it` — books that mean something invite agreement, disagreement, or unsettlement. Books that mean nothing leave nothing to argue with. After reading this book, is there anything a reader might want to argue with — a moral position, a verdict on a character, a stance on the central question? If not, the book has not yet committed.

TC12. `the_one_paragraph_summary_test` — write a one-paragraph summary of the book that you might give a friend. Read it back. Does the summary make this book sound like every other contemporary novel about the same general subject, or does it locate what makes this one specifically necessary? If the latter is hard, the book has not yet earned its specific necessity.

Severity guidance:
1. `CRITICAL` — the book has no identifiable central question (TC1 fails), or the central question is never paid for in scene material (TC5 fails entirely).
2. `HIGH` — major evasion patterns; thesis-speech failure on the central question; recurring images that are decorative rather than load-bearing; the book has no specific necessity (TC12 fails).
3. `MEDIUM` — softer thematic drift, narrator thematic underlining clusters, register mismatches in localized scenes.

Pass-hint default: `p1_structural_craft` for question, engagement, evasion, thesis-speech, idea-tested-through-cost findings (these need scene work). `p3_prose_copyedit` for narrator-thematic-underlining and register-mismatch findings.

Required output:
1. `{{THEME_COHERENCE_OUTPUT_FILE}}`

`{{THEME_COHERENCE_OUTPUT_FILE}}` contract:
1. Top-level fields:
2. `cycle` (integer; write `{{CYCLE_INT}}`)
3. `verdict` (`PASS|FAIL` — PASS only if TC1, TC2, TC5, TC10, TC12 all hold)
4. `summary` (string; in plain language, name what the book is about and what it has to say about it — or report explicitly that it does not yet have either)
5. `theme_map` (object — see below)
6. `findings` (array)
7. Each finding object must contain:
8. `finding_id` (string; stable, e.g. `TC-001`)
9. `category` (one of: `central_question`, `engagement_with_question`, `recurring_image_audit`, `motif_payoff`, `idea_tested_through_character_cost`, `evasion_pattern`, `thematic_register_match`, `thesis_speech_failure`, `narrator_thematic_underlining`, `what_book_has_to_say`, `would_a_reader_argue_with_it`, `the_one_paragraph_summary_test`)
10. `severity` (`MEDIUM|HIGH|CRITICAL`)
11. `chapter_id` (where the failure principally registers; for whole-book findings, the chapter where the missing engagement most needed to land)
12. `evidence` (must cite `{{FULL_NOVEL_FILE}}:<line>`)
13. `problem`
14. `rewrite_direction`
15. `acceptance_test`
16. `pass_hint` (`p1_structural_craft|p2_dialogue_idiolect_cadence|p3_prose_copyedit`)

`theme_map` object fields:
- `central_question` (string)
- `what_book_has_to_say` (string; the paragraph from TC10)
- `recurring_motifs` (array of objects `{motif, occurrence_cites, judgment}`; judgment is `load_bearing` or `decorative`)
- `paid_for_at` (array of `{{FULL_NOVEL_FILE}}:<line>` cites — places where the central question costs a character something concrete)
- `evasion_locations` (array of `{{FULL_NOVEL_FILE}}:<line>` cites)
- `one_paragraph_summary` (string)

Example structure only. Do not copy wording, IDs, or evidence from this example.

```json
{
  "cycle": 1,
  "verdict": "FAIL",
  "summary": "...",
  "theme_map": {
    "central_question": "...",
    "what_book_has_to_say": "...",
    "recurring_motifs": [
      {"motif": "...", "occurrence_cites": ["{{FULL_NOVEL_FILE}}:..."], "judgment": "load_bearing"}
    ],
    "paid_for_at": ["{{FULL_NOVEL_FILE}}:..."],
    "evasion_locations": ["{{FULL_NOVEL_FILE}}:..."],
    "one_paragraph_summary": "..."
  },
  "findings": [
    {
      "finding_id": "TC-001",
      "category": "engagement_with_question",
      "severity": "HIGH",
      "chapter_id": "chapter_12",
      "evidence": "{{FULL_NOVEL_FILE}}:6201",
      "problem": "...",
      "rewrite_direction": "...",
      "acceptance_test": "...",
      "pass_hint": "p1_structural_craft"
    }
  ]
}
```
