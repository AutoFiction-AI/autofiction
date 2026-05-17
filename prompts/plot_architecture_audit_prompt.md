You are running PLOT ARCHITECTURE AUDIT for cycle `{{CYCLE_PADDED}}`.

Inputs:
1. Full manuscript snapshot: `{{FULL_NOVEL_FILE}}`
2. Chapter line index: `{{CHAPTER_LINE_INDEX_FILE}}`
3. Outline: `outline/outline.md` (for the *intended* architecture; you will compare actual against intended)
4. Static story context: `outline/static_story_context.json`
5. Constitution: `config/constitution.md`

Context isolation requirement:
1. Do not read prior cycle reviews, chapter reviews, gate files, revision reports, or context packs.
2. Do not let the outline excuse the manuscript. The outline is what the book *intended*; the manuscript is what the book *is*. Where they diverge, judge the manuscript.

Scope:
1. You audit the dramatic architecture of the whole novel as it exists on the page. Are the load-bearing scenes structurally where they need to be? Does the curve of the book support the weight the ending puts on it?
2. This is not chapter-level craft (other stages own that). This is the shape of the book.

Mandatory architectural checks — for each, anchor findings to specific lines or chapter spans:

PA1. `opening_promise` — within the first 10–15% of the book, does the manuscript establish (a) a focalizer the reader can follow, (b) a dramatic question or pressure that gives the reader a reason to keep reading, and (c) the operational rules of the world (genre, mode, what kind of book this is)? Cite where each is established or flag what is missing.

PA2. `inciting_disturbance` — locate the chapter and scene where the book's central pressure first becomes irreversible. If you cannot locate it, that is a finding. If it lands too late (e.g. past 25% of the book) or too early (the disturbance has already happened before the reader is invested), flag it.

PA3. `rising_action_curve` — does pressure escalate across the book, or does the middle stall, repeat, or rotate around the same conflict at the same temperature? Identify the longest stretch where pressure does not change, and explain what the book is doing instead in that stretch.

PA4. `midpoint_load_bearing` — is there a scene roughly in the middle of the book that materially changes what the focalizer believes, can do, or knows is at stake? Locate it. If the middle of the book is not load-bearing, the back half is being asked to carry the front half, and this is a structural defect.

PA5. `subplot_convergence` — name each named subplot. For each, report whether it converges with the main line by the end (with cite), runs parallel without converging (with cite), or fizzles unmotivated (with cite). Subplots that do not earn their place should be cut or merged.

PA6. `climax_placement_and_energy` — locate the climax. Is it where the architecture wants it (typically 80–90% of the way through)? Does it carry the energy the rising action invested? If the climax is undercharged or arrives flat, identify why — is the setup underspecified, the pressure already discharged, the wrong character at the center.

PA7. `denouement_length` — locate the denouement (post-climax material). Is it long enough to land the consequences and short enough not to dissipate them? Award books usually have lean denouements that do specific small work; over-long denouements are a tell of the book not trusting its climax.

PA8. `load_bearing_scenes` — name the five scenes the book genuinely depends on (its weight rests on them). For each, evaluate: is this one of the strongest scenes in the book? If a load-bearing scene is among the *weaker* scenes, the book is structurally inverted and the fix is not polish — it is making the load-bearing scene actually carry weight.

PA9. `cuttable_chapters` — read each chapter and ask: if this chapter were removed and the next chapter recapped what the reader needed in two paragraphs, would the book be better or worse? Name any chapter that is genuinely cuttable. Award books are usually shorter than people expect; the question is which chapters earn their pages.

PA10. `tell_dont_show_at_structure` — places where the book *summarizes* what should have been a scene that earns its weight. This is the structural cousin of sanitization: a key turn told in retrospective summary instead of rendered as the scene it deserved.

PA11. `intent_vs_manuscript_divergence` — where the outline planned an architecture (named beats, named turns) and the manuscript landed something different. The manuscript is authoritative; the outline is the planning artifact. But where the manuscript dropped a planned beat without compensating elsewhere, that is a structural hole.

PA12. `escalation_vs_repetition` — distinguish recurrence-with-variation (good — the same kind of test under changed conditions) from mechanical repetition (bad). For the recurring scene types in this book, judge each recurrence: did pressure, leverage, knowledge, or relationship change?

Severity guidance:
1. `CRITICAL` — a structural defect that would prevent the book from working at all (no inciting disturbance, no climax, denouement that erases the climax's meaning).
2. `HIGH` — a structural problem a careful reader would notice and that materially damages the book (midpoint not load-bearing, subplot fizzle, cuttable middle chapters).
3. `MEDIUM` — softer architectural drift that the book can live with but should not.

Pass-hint default: `p1_structural_craft` for nearly all findings. Architecture is a structural concern.

Required output:
1. `{{PLOT_ARCHITECTURE_OUTPUT_FILE}}`

`{{PLOT_ARCHITECTURE_OUTPUT_FILE}}` contract:
1. Top-level fields:
2. `cycle` (integer; write `{{CYCLE_INT}}`)
3. `verdict` (`PASS|FAIL` — PASS only if PA1–PA8 are all sound and no CRITICAL findings)
4. `summary` (string; describe the book's architecture in plain language — what shape the book has, not just what is wrong with it)
5. `architecture_map` (object with structured slots for the architectural skeleton — see below)
6. `findings` (array)
7. Each finding object must contain:
8. `finding_id` (string; stable, e.g. `PA-001`)
9. `category` (one of: `opening_promise`, `inciting_disturbance`, `rising_action_curve`, `midpoint_load_bearing`, `subplot_convergence`, `climax_placement_and_energy`, `denouement_length`, `load_bearing_scenes`, `cuttable_chapters`, `tell_dont_show_at_structure`, `intent_vs_manuscript_divergence`, `escalation_vs_repetition`)
10. `severity` (`MEDIUM|HIGH|CRITICAL`)
11. `chapter_id` (the chapter where the failure principally registers, in `chapter_NN` form)
12. `related_chapter_ids` (array of related `chapter_NN` ids; may be empty)
13. `evidence` (must cite `{{FULL_NOVEL_FILE}}:<line>`)
14. `problem`
15. `rewrite_direction`
16. `acceptance_test`
17. `pass_hint` (`p1_structural_craft|p2_dialogue_idiolect_cadence|p3_prose_copyedit`)

`architecture_map` object fields (all strings; cite chapter_NN where applicable):
- `inciting_disturbance_location`
- `midpoint_location`
- `climax_location`
- `denouement_span`
- `central_dramatic_question`
- `load_bearing_scenes` (array of objects `{chapter_id, scene_summary, judgment}`; judgment is one of `strong`, `adequate`, `weak`)
- `subplots` (array of objects `{name, convergence_status, evidence}`; convergence_status is one of `converged`, `parallel`, `fizzled`)

Example structure only. Do not copy wording, IDs, or evidence from this example.

```json
{
  "cycle": 1,
  "verdict": "FAIL",
  "summary": "...",
  "architecture_map": {
    "inciting_disturbance_location": "chapter_03",
    "midpoint_location": "chapter_09",
    "climax_location": "chapter_17",
    "denouement_span": "chapter_18",
    "central_dramatic_question": "...",
    "load_bearing_scenes": [
      {"chapter_id": "chapter_04", "scene_summary": "...", "judgment": "strong"}
    ],
    "subplots": [
      {"name": "...", "convergence_status": "converged", "evidence": "{{FULL_NOVEL_FILE}}:..."}
    ]
  },
  "findings": [
    {
      "finding_id": "PA-001",
      "category": "midpoint_load_bearing",
      "severity": "HIGH",
      "chapter_id": "chapter_09",
      "related_chapter_ids": ["chapter_08", "chapter_10"],
      "evidence": "{{FULL_NOVEL_FILE}}:4521",
      "problem": "...",
      "rewrite_direction": "...",
      "acceptance_test": "...",
      "pass_hint": "p1_structural_craft"
    }
  ]
}
```
