You are running ENDING AUDIT for cycle `{{CYCLE_PADDED}}`.

Inputs:
1. Full manuscript snapshot: `{{FULL_NOVEL_FILE}}`
2. Chapter line index: `{{CHAPTER_LINE_INDEX_FILE}}`
3. Ending span: the last `{{ENDING_TAIL_CHAPTERS}}` chapters of the book
4. Outline: `outline/outline.md` (used only to identify the book's threads — the things the book promised to deal with)
5. Constitution: `config/constitution.md`

Context isolation requirement:
1. Do not read prior cycle reviews, gate files, or revision reports.
2. Use the chapter line index to jump to the ending span; you may also read earlier chapters when checking whether a thread the ending closes was actually planted.

Scope:
1. The ending is where most LLM-drafted novels collapse. The model wants to close cleanly. The ending is also where award juries form their lasting impression. This stage exists because the prior gates do not focus enough on the last 15–20% of the book.
2. You audit the ending forensically. Walk every closing thread, judge each in turn, and judge the last image / last paragraph / last line as their own scrutiny.

Mandatory checks — for each, anchor findings to specific lines in `{{FULL_NOVEL_FILE}}:<line>` form:

EA1. `climax_charge` — the climax should arrive with the energy the book has invested. Locate the climax. Was it undercharged, deferred, displaced into summary, or arrived too clean? Award books often pay for their climaxes with cost; flag if the climax pays no cost.

EA2. `thread_inventory` — list every named thread the book opened (relational, plot, thematic, mystery, promise of consequence). For each: closed-on-page (cite), closed-by-narrator-summary (cite — this is usually a craft failure), left-open-by-design (state why this is earned), or fizzled (cite).

EA3. `wrong_threads_closed` — sometimes endings close threads that should remain open and leave open threads that should resolve. Award endings choose carefully. Report any closures that read as the book tying off something that was meant to remain a wound, and any open thread that reads as evasion rather than design.

EA4. `denouement_length` — the post-climax material. Long enough to land consequence, short enough not to dissipate it. Identify the line where the climax's energy starts to drain, and the line where the book ends. Is the gap between them load-bearing or padding?

EA5. `ending_earned_by_investment` — does the ending land emotional or moral weight commensurate with what the book invested? An ending that lands a profundity the book did not earn is a craft failure; an ending that lands less than the book earned is also a failure. Both are common.

EA6. `last_image` — the final scene. Is the closing image specific, scene-grounded, and chosen — or is it generic, abstract, or summarizing? Cite the line and judge it.

EA7. `last_paragraph` — the closing paragraph. Read it three times. Is it doing work, or is it a coda that says "and so"? Award endings end on a sentence that earns its singularity. Generic codas are a tell of the book not trusting its scene.

EA8. `last_line` — the final sentence. Specifically. What is it doing? Is it the right last line? If the book has a better last line two paragraphs earlier, identify it.

EA9. `unprepared_arrivals` — anything in the ending that arrives without setup. A reveal, a capability, a relationship, a shift in understanding, a piece of evidence. If the ending depends on something the earlier book did not plant, that is a structural defect, not a polish problem.

EA10. `ending_register_match` — the ending should commit to the same register the book established. A book that ran rough and uncomfortable should not end on consoling sentiment; a comic novel should not end with a sudden literary-novel hush; a horror book should not end on a hug. Identify any register drift in the ending.

EA11. `epilogue_or_coda_audit` — if the ending includes an epilogue or coda, does it earn its place? Or is it the book reassuring the reader after the climax? Many endings would be stronger if their epilogue were cut.

EA12. `relief_vs_resolution` — distinguish the reader's *relief that the book is ending* from the reader's *experience of resolution*. If the ending feels like the book is finally letting you stop reading, that is not the ending working — that is the book being too long.

EA13. `would_a_reader_underline_anything_here` — name any sentence in the ending span a careful reader would underline or remember. If you cannot name one, the ending is doing nothing the prose pays attention to.

Severity guidance:
1. `CRITICAL` — the climax does not land, or the ending depends on an unprepared arrival that breaks reader trust.
2. `HIGH` — the wrong threads are closed; the last image is generic; the denouement dissipates the climax; the ending sanitizes what the book promised.
3. `MEDIUM` — softer ending drift: epilogue too long, last line not the best last line available, relief outweighing resolution by a small margin.

Pass-hint default: `p1_structural_craft` for climax, threads, denouement length, unprepared arrivals, register match. `p3_prose_copyedit` for last-image, last-paragraph, last-line refinements.

Required output:
1. `{{ENDING_AUDIT_OUTPUT_FILE}}`

`{{ENDING_AUDIT_OUTPUT_FILE}}` contract:
1. Top-level fields:
2. `cycle` (integer; write `{{CYCLE_INT}}`)
3. `verdict` (`PASS|FAIL` — PASS only if EA1, EA2, EA5, EA6, EA9 all hold)
4. `summary` (string; what does this ending do, in plain language)
5. `ending_map` (object — see below)
6. `findings` (array)
7. Each finding object must contain:
8. `finding_id` (string; stable, e.g. `EA-001`)
9. `category` (one of: `climax_charge`, `thread_inventory`, `wrong_threads_closed`, `denouement_length`, `ending_earned_by_investment`, `last_image`, `last_paragraph`, `last_line`, `unprepared_arrivals`, `ending_register_match`, `epilogue_or_coda_audit`, `relief_vs_resolution`, `would_a_reader_underline_anything_here`)
10. `severity` (`MEDIUM|HIGH|CRITICAL`)
11. `chapter_id` (the chapter where the failure registers)
12. `evidence` (must cite `{{FULL_NOVEL_FILE}}:<line>`)
13. `problem`
14. `rewrite_direction`
15. `acceptance_test`
16. `pass_hint` (`p1_structural_craft|p2_dialogue_idiolect_cadence|p3_prose_copyedit`)

`ending_map` object fields:
- `climax_location` (string `chapter_NN:<line>`)
- `denouement_span` (string `chapter_NN:<line>` — `chapter_NN:<line>`)
- `closing_threads` (array of objects `{thread, status, evidence}` where status is `closed_on_page`, `closed_by_summary`, `left_open_by_design`, `fizzled`)
- `last_image_summary` (string)
- `last_line_quoted` (string — the actual last sentence, quoted)
- `epilogue_present` (boolean)

Example structure only. Do not copy wording, IDs, or evidence from this example.

```json
{
  "cycle": 1,
  "verdict": "FAIL",
  "summary": "...",
  "ending_map": {
    "climax_location": "chapter_17:7841",
    "denouement_span": "chapter_18:7960 — chapter_18:8312",
    "closing_threads": [
      {"thread": "...", "status": "closed_on_page", "evidence": "{{FULL_NOVEL_FILE}}:8123"}
    ],
    "last_image_summary": "...",
    "last_line_quoted": "...",
    "epilogue_present": false
  },
  "findings": [
    {
      "finding_id": "EA-001",
      "category": "ending_earned_by_investment",
      "severity": "HIGH",
      "chapter_id": "chapter_18",
      "evidence": "{{FULL_NOVEL_FILE}}:8200",
      "problem": "...",
      "rewrite_direction": "...",
      "acceptance_test": "...",
      "pass_hint": "p1_structural_craft"
    }
  ]
}
```
