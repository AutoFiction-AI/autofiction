You are running CHARACTER ARC AUDIT for character `{{CHARACTER_ID}}` in cycle `{{CYCLE_PADDED}}`.

Inputs:
1. Full manuscript snapshot: `{{FULL_NOVEL_FILE}}`
2. Chapter line index: `{{CHAPTER_LINE_INDEX_FILE}}`
3. Character voice profile (the entry for this character from `outline/style_bible.json` — used to know the character's name, register, and any planned formative experiences, NOT to excuse the manuscript)
4. Constitution: `config/constitution.md`

Context isolation requirement:
1. Do not read prior cycle reviews, chapter reviews, gate files, or revision reports. Other reviewers have judged the chapters; you are auditing this character's whole-book trajectory.
2. Do not read the outline's intended arc for this character. The outline is the plan; the book is what landed. You judge the landing.
3. The voice profile is provided so you know who the character is and what their declared register/formative-experiences/interpretive-lens are — those are facts you are owed. Do not let the profile excuse a manuscript that does not render the character.

Scope:
1. You are reading the whole novel for this one character's arc end-to-end. Walk every chapter where they appear (even briefly) and trace what changes for them — in belief, capability, knowledge, relationship, role, cost, posture toward the world, posture toward themselves.
2. The other reviewers see chapter slices. You are the only reviewer who reads this character as a person across the whole book.

Mandatory checks — for each, anchor findings to specific lines or chapter spans in `{{FULL_NOVEL_FILE}}:<line>` form:

CA1. `entry_state` — describe in one sentence who this character is when the book first lets the reader meet them: what they want, what they fear, what they do not yet know. Cite the establishing lines.

CA2. `exit_state` — describe in one sentence who this character is in the last scene where they appear: what they want, what they fear, what they now know. Cite the lines.

CA3. `arc_legibility` — is the change between entry and exit legible to a reader who has never met this character before? If the character ends in functionally the same place they started (same wants, same fears, same lessons unlearned), that is a finding — flat arcs are a structural defect for any character whose arc is supposed to matter.

CA4. `irreversibility` — at the exit, can the character return to where they started? Award-level arcs cross thresholds the character cannot cross back. If the character could pick up tomorrow and live the same life as the opening, the arc has not crossed.

CA5. `change_earned_on_page` — the change the character undergoes must be evidenced on the page through scene material — action, decision, refusal, body, recognition cue. Narrator summary that the character "had grown" or "had begun to understand" without scene evidence is a craft failure. Locate where each meaningful change happens on the page; flag any change that is asserted in narration without earning it as a scene.

CA6. `pressure_distribution_across_book` — across the chapters where this character appears, does pressure on them escalate, hold, or flatten? Identify long stretches where this character has nothing materially at stake, and ask whether those stretches earn their place or are dead weight in their arc.

CA7. `unique_register` — does this character speak, think, and act in a register that is theirs and not interchangeable with the focalizer or other named characters? Cite three lines that could only have come from this character; if you cannot find three, that is a finding.

CA8. `presence_continuity` — for chapters where this character is offstage, does their absence register on the focalizer (does the focalizer think about them, miss them, dread them, want them) or do they simply vanish from the book until reintroduced? A character who vanishes is treated by the book as a function, not a person.

CA9. `relationship_geometries` — name each meaningful relationship this character has in the book. For each, report whether the geometry of that relationship changed across the book or stayed static. Static relationships in books that bill themselves on relational pressure are a structural defect.

CA10. `function_vs_person` — is this character drawn richly enough to feel like a person, or are they doing plot work as a function (the wise grandmother, the disapproving father, the helpful peer, the institutional adversary) without the specificity that makes function turn into character? Cite specific moments that read as function and specific moments that read as person; if the latter list is empty or thin, this is a HIGH finding.

CA11. `voice_profile_fidelity` — does the character's rendered voice on the page match the declared `voice_profile` (interruption habit, evasion style, indirectness, repetition tolerance, sentence completion style)? Or does it drift into a generic literary register? Cite lines where the rendered voice is true to the profile and lines where it drifts.

CA12. `decision_under_pressure` — name two or three moments where this character makes a decision under pressure that materially redirects their arc. For each, evaluate: was the decision earned by setup, was it character-true, was it visible on the page (not narrated as having been made offstage). If you cannot name two or three, the character's arc is not load-bearing.

Severity guidance:
1. `CRITICAL` — a flat arc for a character whose arc is structurally load-bearing for the book.
2. `HIGH` — change asserted but not earned on the page; function-not-person across the book; missing on-page decisions for major arc turns; voice profile not honored across the book.
3. `MEDIUM` — softer arc drift, presence-continuity gaps, relationship geometry that holds when it should move.

Pass-hint default: `p1_structural_craft` for arc, irreversibility, change-earned, decision, function-vs-person findings (these need scene-level work). `p2_dialogue_idiolect_cadence` for voice-profile-fidelity findings.

Required output:
1. `{{CHARACTER_ARC_OUTPUT_FILE}}`

`{{CHARACTER_ARC_OUTPUT_FILE}}` contract:
1. Top-level fields:
2. `character_id` (string; must equal `{{CHARACTER_ID}}`)
3. `cycle` (integer; write `{{CYCLE_INT}}`)
4. `verdict` (`PASS|FAIL` — PASS only if CA3, CA4, CA5, CA10 all hold)
5. `summary` (string; describe this character's arc in plain language — entry to exit)
6. `arc_map` (object with structured arc slots — see below)
7. `findings` (array)
8. Each finding object must contain:
9. `finding_id` (string; stable, e.g. `CA-{{CHARACTER_ID}}-001`)
10. `category` (one of: `entry_state`, `exit_state`, `arc_legibility`, `irreversibility`, `change_earned_on_page`, `pressure_distribution_across_book`, `unique_register`, `presence_continuity`, `relationship_geometries`, `function_vs_person`, `voice_profile_fidelity`, `decision_under_pressure`)
11. `severity` (`MEDIUM|HIGH|CRITICAL`)
12. `chapter_id` (the chapter where the failure principally registers; for whole-arc findings, the earliest chapter in the affected span)
13. `related_chapter_ids` (array; may be empty)
14. `character_id` (must equal `{{CHARACTER_ID}}`)
15. `evidence` (must cite `{{FULL_NOVEL_FILE}}:<line>`)
16. `problem`
17. `rewrite_direction`
18. `acceptance_test`
19. `pass_hint` (`p1_structural_craft|p2_dialogue_idiolect_cadence|p3_prose_copyedit`)

`arc_map` object fields:
- `entry_state` (string)
- `exit_state` (string)
- `arc_threshold_crossed` (boolean; true if CA4 holds)
- `pivot_chapters` (array of `chapter_NN` ids where the character's arc materially turns)
- `signature_lines` (array of strings, with `{{FULL_NOVEL_FILE}}:<line>` cites — lines that could only have come from this character)
- `relationship_geometries` (array of objects `{counterpart_character_id, change_summary}`)

Example structure only. Do not copy wording, IDs, or evidence from this example.

```json
{
  "character_id": "{{CHARACTER_ID}}",
  "cycle": 1,
  "verdict": "FAIL",
  "summary": "...",
  "arc_map": {
    "entry_state": "...",
    "exit_state": "...",
    "arc_threshold_crossed": false,
    "pivot_chapters": ["chapter_09", "chapter_15"],
    "signature_lines": ["..."],
    "relationship_geometries": [
      {"counterpart_character_id": "...", "change_summary": "..."}
    ]
  },
  "findings": [
    {
      "finding_id": "CA-{{CHARACTER_ID}}-001",
      "category": "irreversibility",
      "severity": "HIGH",
      "chapter_id": "chapter_18",
      "related_chapter_ids": ["chapter_01"],
      "character_id": "{{CHARACTER_ID}}",
      "evidence": "{{FULL_NOVEL_FILE}}:8123",
      "problem": "...",
      "rewrite_direction": "...",
      "acceptance_test": "...",
      "pass_hint": "p1_structural_craft"
    }
  ]
}
```
