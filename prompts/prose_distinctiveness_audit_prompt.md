You are running PROSE DISTINCTIVENESS AUDIT for cycle `{{CYCLE_PADDED}}`.

Inputs:
1. Full manuscript snapshot: `{{FULL_NOVEL_FILE}}`
2. Chapter line index: `{{CHAPTER_LINE_INDEX_FILE}}`
3. Style bible: `outline/style_bible.json` (used to know the *declared* register; you judge the actual prose against an external standard, not against the style bible)
4. Constitution: `config/constitution.md`

Context isolation requirement:
1. Do not read prior cycle reviews, gate files, or revision reports. Other reviewers have judged the prose against the style bible. You are judging it against contemporary literary work as a category.
2. The cross-chapter audit catches *over*-distinctive tics. You catch *under*-distinctiveness — averaged literary register, prose that could appear in any contemporary novel without remark, sentences a reader would not pause on.

Scope:
1. Award-level prose has a voice. A reader who has read a few of an author's books can pick out their paragraphs from a stack. The pipeline's other gates make sure the prose is not *bad*. This stage asks whether the prose is *distinctive* — whether it has a voice you could pick out blind.
2. Be specific. Vague claims that prose "lacks voice" are useless. Cite paragraphs, name what is generic about them, and identify what the book's voice actually is when it is working — or report that it is not working.

Sampling rule:
1. Read the entire manuscript, but anchor your specific evaluations to representative samples. Take at least one sample of 8–12 consecutive sentences from each of: the opening, an early-middle chapter, the late-middle chapter, the climax, and the closing. For each sample, judge it as if you were reading it isolated from the rest of the book.

Mandatory checks — for each, anchor findings to specific lines in `{{FULL_NOVEL_FILE}}:<line>` form:

PD1. `signature_moves` — name the three signature prose moves of this book, if it has any. A "signature move" is a sentence-level, image-level, or structural choice the book makes consistently and that no other contemporary novel would make in quite this way. Cite three examples per signature move. If you cannot identify three signature moves, the book does not yet have a voice — report this as a HIGH finding.

PD2. `averaged_literary_register_drift` — identify the longest stretches where the prose retreats to averaged contemporary literary-novel register. Common tells: vaguely lyrical sentences that summarize feeling; "the way" similes; restrained third-person interiority that could belong to fifty other novels published this year; abstract nouns doing thematic work; transitional sentences that any drafter would write. Cite each stretch.

PD3. `paragraph_pickability_test` — sample five paragraphs at random from the manuscript. For each, ask: if I read this paragraph aloud to a reader who knows contemporary literary fiction and asked them to guess the author or the book, would they have any signal to work with? Cite each paragraph and report your judgment. A book where four out of five paragraphs are unpickable has a voice problem.

PD4. `sentence_rhythm_diversity` — across the samples, do the sentences have varied rhythm and length, or do they cluster around a single comfortable medium-length cadence? Award prose typically has rhythmic discipline that varies by scene pressure; default LLM prose tends to a medium-cadence average. Cite stretches where the rhythm is varied and stretches where it is flat.

PD5. `image_economy` — does the book have images that recur load-bearing across the book and accumulate meaning, or are its images decorative and replaceable? Cite recurring images that do work; cite images that are decorative.

PD6. `stylistic_risk_taken` — name two or three places where the book takes a genuine stylistic risk: a passage that does something unusual at the sentence or paragraph level. If you cannot name two or three, the book is not yet doing what award books do.

PD7. `transparent_prose_done_well` — note: transparent prose (the constitution's default) is not the same as undistinctive prose. The most rigorous transparent prose is invisible because the reader is too in-scene to notice the sentence — but it is still distinctive in selection, rhythm, and image precision. Distinguish transparent-and-distinctive from transparent-and-generic.

PD8. `metaphor_originality` — find every figurative comparison in your samples. For each, judge: original to the book, conventional, or stock-LLM. Cite stock-LLM metaphors specifically — they are the most common form of voicelessness.

PD9. `voice_consistency_across_pov` — if the book has multiple POVs, does each POV have a distinguishable register and habit of attention, or do all POVs sound like the same narrator with different name tags? Cite paragraphs from each POV and judge.

PD10. `quotability_test` — find three sentences or short passages from the manuscript that you would quote in a review. If you cannot find three, the book has not yet earned the line-level attention award books earn. Cite them. If you find them with effort, the book is on its way; if you cannot find them at all, this is a HIGH finding.

PD11. `the_blind_test` — pick the strongest paragraph in the manuscript. Mentally place it inside the openings of three other recent contemporary novels of the same mode. Would a careful reader pick it out? Why or why not? This is a calibration check on PD1.

PD12. `default_LLM_prose_signature_check` — there are sentence patterns LLMs produce by default that no human writer reaches for as often: "the way X does Y" similes, "It wasn't X, it was Y" constructions, parallel balanced clauses without rhetorical purpose, abstract noun subjects acting on humans ("loneliness pressed against the door"), transitional sentences that close paragraphs by interpreting the action just rendered. The cross-chapter audit grep-counts some of these; you judge whether they are *clustered* in a way that tells the reader they are reading LLM-trained prose. Cite specific clusters and judge.

Severity guidance:
1. `CRITICAL` — the book has no identifiable voice across the manuscript (PD1 fails entirely).
2. `HIGH` — averaged literary register dominates one or more major spans; metaphors are predominantly stock; quotability test finds nothing; multiple POVs are interchangeable.
3. `MEDIUM` — softer voice drift in specific spans, default-LLM-pattern clusters in localized scenes, decorative image economy.

Pass-hint default: `p3_prose_copyedit` for sentence-level findings (rhythm, image, metaphor, default-LLM signatures). `p1_structural_craft` for findings that require restructuring scenes to give the prose room to do its work (PD6, PD11). `p2_dialogue_idiolect_cadence` only when the finding is specifically about dialogue voice indistinctness.

Required output:
1. `{{PROSE_DISTINCTIVENESS_OUTPUT_FILE}}`

`{{PROSE_DISTINCTIVENESS_OUTPUT_FILE}}` contract:
1. Top-level fields:
2. `cycle` (integer; write `{{CYCLE_INT}}`)
3. `verdict` (`PASS|FAIL` — PASS only if PD1, PD3, PD10, PD12 all hold)
4. `summary` (string; in plain language, name the book's voice — what it does that no one else's prose does — or name explicitly that it has not yet found one)
5. `voice_map` (object — see below)
6. `findings` (array)
7. Each finding object must contain:
8. `finding_id` (string; stable, e.g. `PD-001`)
9. `category` (one of: `signature_moves`, `averaged_literary_register_drift`, `paragraph_pickability_test`, `sentence_rhythm_diversity`, `image_economy`, `stylistic_risk_taken`, `transparent_prose_done_well`, `metaphor_originality`, `voice_consistency_across_pov`, `quotability_test`, `the_blind_test`, `default_LLM_prose_signature_check`)
10. `severity` (`MEDIUM|HIGH|CRITICAL`)
11. `chapter_id` (where the failure principally registers)
12. `evidence` (must cite `{{FULL_NOVEL_FILE}}:<line>`)
13. `problem`
14. `rewrite_direction`
15. `acceptance_test`
16. `pass_hint` (`p1_structural_craft|p2_dialogue_idiolect_cadence|p3_prose_copyedit`)

`voice_map` object fields:
- `signature_moves` (array of objects `{move, examples}`; `examples` is an array of `{{FULL_NOVEL_FILE}}:<line>` cites)
- `quotable_passages` (array of `{{FULL_NOVEL_FILE}}:<line>` cites; should be at least three)
- `averaged_register_spans` (array of `{{FULL_NOVEL_FILE}}:<line>` ranges)
- `pov_voice_assessment` (array of objects `{pov_label, voice_summary, distinguishable_from_other_pov}`; if single-POV, one entry)
- `the_blind_test_judgment` (string)

Example structure only. Do not copy wording, IDs, or evidence from this example.

```json
{
  "cycle": 1,
  "verdict": "FAIL",
  "summary": "...",
  "voice_map": {
    "signature_moves": [
      {"move": "...", "examples": ["{{FULL_NOVEL_FILE}}:..."]}
    ],
    "quotable_passages": ["{{FULL_NOVEL_FILE}}:..."],
    "averaged_register_spans": ["{{FULL_NOVEL_FILE}}:4321-4480"],
    "pov_voice_assessment": [
      {"pov_label": "Benjamin (focalizer)", "voice_summary": "...", "distinguishable_from_other_pov": true}
    ],
    "the_blind_test_judgment": "..."
  },
  "findings": [
    {
      "finding_id": "PD-001",
      "category": "averaged_literary_register_drift",
      "severity": "HIGH",
      "chapter_id": "chapter_08",
      "evidence": "{{FULL_NOVEL_FILE}}:4321; {{FULL_NOVEL_FILE}}:4480",
      "problem": "...",
      "rewrite_direction": "...",
      "acceptance_test": "...",
      "pass_hint": "p3_prose_copyedit"
    }
  ]
}
```
