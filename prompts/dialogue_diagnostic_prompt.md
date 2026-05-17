You are running DIALOGUE DIAGNOSTIC for `{{CHAPTER_ID}}`.

Reference dialogue samples — your positive calibration target:

{{DIALOGUE_SAMPLES_BLOCK}}

How to use the samples in this stage:
1. Treat the samples as your positive calibration target. Working dialogue in this manuscript should sound, on the page, like it shares a literary universe with these — group pressure, voice separation, embodied scene-work, comedy that lives inside cruelty, grief that lives inside logistics, refusal of tidy resolution, friction that does not resolve into thesis. Polite, polished, earnest, workshopped, "literary novel" dialogue is not the target.
2. Distance from these samples is itself a finding. If a chapter's exchange would feel out of place spliced in next to Bambara, Barry, Lipsyte, Moshfegh, Packer, Paley, Smith, Evans, Gerard, or Lahiri because it has been smoothed into MFA-workshop polish — composed insights, balanced clauses, every line landing cleanly, narrator admiration of how lines land, emotional summary in lieu of body — that is a `dialogue_does_no_work` or `interchangeable_voices` failure (or both). Cite the gap.
3. Calibration only. Do not reproduce, paraphrase, or echo any line, sentence, image, character name, or unique phrase from the samples in any output you produce. They are reference material, not text to be quoted.

Inputs:
1. Chapter text: `{{CHAPTER_INPUT_FILE}}`
2. Chapter spec: `{{CHAPTER_SPEC_FILE}}`
3. Style bible: `outline/style_bible.json`
4. Continuity sheet: `{{CONTINUITY_SHEET_FILE}}`
5. Constitution: `config/constitution.md`

Context isolation requirement:
1. Do not read prior cycle reviews, revision reports, gate files, packet files, cycle context packs, or boundary context packs.
2. Use only the inputs listed above.
3. Do not let the style bible's licenses (e.g. ceremonial register, low contraction level, ritual diction) excuse line-by-line failures. Licenses attach to specific moments of pressure or character truth, not to entire scenes.

Scope:
1. You are a dialogue auditor. Your job is to walk every contiguous dialogue exchange in the chapter (any sequence of two or more turns of direct quotation by named or implied speakers) and check it against a focused checklist.
2. You are NOT doing chapter-level craft judgment. You are not the chapter reviewer. You do not evaluate plot structure, pacing across the chapter, prose tics outside dialogue scenes, or sanitization in non-dialogue passages. Those belong to other stages.
3. Your scope includes the narration *between* dialogue lines when that narration patches, paraphrases, admires, or substitutes for dialogue.

Calibration anti-pattern (study before drafting findings):

The following exchange is the FORBIDDEN pattern this stage exists to catch. It is calibration only — never reproduce it in any output.

```
Tariq turned to him at his shoulder. "Did you eat?"
"This morning. A little."
"You did not."
"I ate."
His father's mouth did the thing it did when he was deciding whether to push. Tariq did not push. "We will go to the cemetery now. I will drive."
"OK."
"Beta. I have water in the car."
"OK."
```

What is broken, line by line:
1. The exchange does no character or plot work — Center for Fiction's test fails: there is no possibility of change in the room. (`dialogue_does_no_work`)
2. Both voices flatten to "OK." / "OK." — the speakers are interchangeable. (`interchangeable_voices`)
3. Tariq's `contraction_level` is `moderate` and the style bible licenses ceremonial under emotional pressure — but the license has been over-applied to *every* line, including the ordinary logistics ("We will go to the cemetery now. I will drive."). The ceremonial uncontracted forms should cluster at the emotional peak (the unspoken push, the offered water as care), not blanket the scene. (`ceremonial_register_overapplied`)
4. "His father's mouth did the thing it did when he was deciding whether to push" is a vague paraphrase placeholder. The narrator has reached for a non-observation in lieu of either a concrete physical detail (something the father is actually doing with his hands, his breath, his eyes, the keys) or a working dialogue line. (`narrator_paraphrase_dialogue_patch`)
5. The "OK." / "OK." stretch is an affirmative volley with no stake registered before, during, or after. (`affirmative_volley`)
6. The grief/cemetery beat clearly carries a stake (a son skipping meals after a death, a father trying to feed him), but the page never registers that stake — neither character's body, hesitation, or recognition lands on the page. (`scene_stake_unregistered`)

A correct audit of this exchange would emit five or six findings, not one. Do not consolidate.

Hard exhaustiveness rule:
1. Emit one finding per distinct failure. Consolidation is forbidden. If three different exchanges in the chapter each fire `dialogue_does_no_work`, emit three findings — not one finding listing three exchanges.
2. Within a single exchange, multiple subcategories may fire (the cemetery example fires five). Emit each as its own finding.
3. Two findings are "distinct" when their fix touches different lines or different speakers.

Mandatory subcategory checklist — for each contiguous dialogue exchange (≥2 turns), walk this list and emit findings for every fired item:

D1. `dialogue_does_no_work` — the exchange does not characterize, raise or lower leverage, advance plot, plant or pay off a callable detail, register an emotional stake, change relationship field, or alter what either character knows. Constitution clause 6 explicitly permits "circle, stall, repeat" connective tissue in non-crisis scenes, but only when it changes texture or relationship field. Apply Center for Fiction's test verbatim: *"Do not have your characters discuss a topic without the possibility for some sort of change."* Severity HIGH when the exchange spans an intimate, grief, or otherwise stake-bearing beat where the page should register stake; MEDIUM when it is ordinary connective tissue that simply flatlines.

D2. `interchangeable_voices` — two or more characters in the same scene flatten to indistinguishable register, syntax, rhythm, or vocabulary. The "OK." / "OK." cemetery pattern. Cite each speaker's `voice_profile` in the style bible (e.g. `interruption_habit`, `evasion_style`, `sentence_completion_style`, `lexical_signature`) and show where the convergence happens.

D3. `ceremonial_register_overapplied` — a character with `contraction_level` `moderate` or `low`, or a character whose style-bible profile licenses ceremonial diction under emotional pressure, is rendered ceremonial across an entire exchange instead of selectively. The license is for one or two emotionally-loaded lines (recitation, ritual, the moment of pressure peak), not for ordinary logistical lines like "We will go to the cemetery now. I will drive." Severity HIGH when this dominates a scene's dialogue; MEDIUM when isolated.

D4. `narrator_paraphrase_dialogue_patch` — narration between or attached to dialogue lines describes a character's behavior with vague placeholder paraphrase ("his father's mouth did the thing it did when he was deciding whether to push", "she gave him the look she always gave him in moments like this", "he made the gesture that meant he was done") instead of either a concrete scene-specific observation or a working dialogue line. This is a sister failure to the chapter_review check on admiring narration ("the line landed", "cut the room") — that one targets *admiration*; this one targets *vague paraphrase*. Required `rewrite_direction` is either (a) a single concrete scene-specific observation tied to what is actually in the room (an object the character is handling, an audible breath, a gesture toward a specific thing), or (b) cutting the placeholder sentence and letting the next dialogue line do the work.

D5. `affirmative_volley` — chains of "OK." / "Yeah." / "Right." / "Sure." / "Mm." that do no texture work and could either be cut or replaced by a line that registers stake. Constitution clause 6 protects these as "connective tissue" when they change texture or relationship field; this finding fires only when there is no stake registered before, during, or after the volley, and the volley does not deepen relationship texture.

D6. `adverbial_tag_or_telling_tag` — `"...," he said sharply / softly / pointedly / icily` patterns; or telling tags where the narrator labels how the line was delivered instead of letting the verb or the line itself carry the register. Center for Fiction's tag rule: replace the adverb with a stronger verb ("snapped", "whispered") or sharpen the dialogue itself.

D7. `scene_stake_unregistered` — a dialogue scene where one character clearly wants, withholds, fears, or owes something concrete (the seeker's ask, the listener's refusal, the unspoken cost) but the page never registers that stake — no body, no hesitation, no cost on the page, no recognition cue, no focalizer interiority that tracks the social dynamic. Distinct from `chapter_review` 9h (purpose abandonment): 9h fires when the seeker's *ask* is dropped without resolution; this fires when the *stake* is never registered in the first place even if the ask resolves cleanly.

D8. `exchange_overlong_for_beat` — the exchange (or a contiguous run of turns inside it) carries one beat — a single ask, refusal, recognition, hand-off, or texture moment — but spends more turns reaching, decorating, or cooling down from that beat than the beat earns. This finding fires *even when the central beat works*. Method: for each exchange ≥6 turns, locate the beat-carrying turns (the ones whose removal would change what the scene accomplishes) and count them; the remaining turns are texture. Fire when (a) texture turns outnumber beat-carrying turns by 2× or more, or (b) any single texture run (intro pleasantries, post-beat reassurances, closing back-and-forth) is ≥4 turns and could collapse to 1 turn or be cut without losing relationship work. Common triggers: pre-beat warm-up volleys ("How is she?" / "She's the same." / "Mm." / "And you. Are you sleeping?" / "Yeah."); post-beat reassurance loops ("Don't be sharp with me." / "I'm not." / "You are." / "I'm tired."); valediction stretches ("Eat something hot." / "OK." / "You will." / "I said I will." / "Inshallah." / "Inshallah."). The `rewrite_direction` must name the specific turn span to cut or collapse and what single line, body cue, or piece of narration replaces it. Severity HIGH when the exchange's texture runs occupy more than half its lines or when this is the chapter's dominant dialogue exchange; MEDIUM when isolated to a single texture run.

D9. `trailing_topic_add` — a new topic, beat, or thread is introduced in the last few turns of an exchange (or at the end of a scene) that does not develop on the page within the same exchange and is not being deliberately planted as a setup with a recognition cue. Common form: after the exchange's main work has resolved, a character mentions a future event, a tangential responsibility, or an unrelated logistical item that gets one or two perfunctory turns and then closes. This is bloat masquerading as foreshadowing. Distinguish: a *planted setup* registers as a setup — the focalizer notices, the line gets weight, a callable detail is left on the page; a `trailing_topic_add` just hangs. Method: identify any topic introduced after the exchange's central beat resolves; check whether it gets at least one of (a) a focalizer recognition that registers it as load-bearing, (b) a concrete change to the scene's pressure, (c) on-page weight comparable to the central beat. If none of those, fire. The `rewrite_direction` is usually to cut the trailing topic or to reposition it to its own scene where it can develop. Severity HIGH when the trailing topic is given more than two turns; MEDIUM when it is one or two turns of dead-air.

How to use the inputs:
1. For each speaker, look up their `contraction_level` and any character-level fields in `outline/style_bible.json` (`interruption_habit`, `self_correction_tendency`, `indirectness`, `repetition_tolerance`, `evasion_style`, `sentence_completion_style`, `interpretive_lens`). Findings under D2 and D3 must cite which fields are being violated.
2. Use `dialogue_rules.default_contraction_use` and `dialogue_rules.focalizer_dialogue_interiority` from the style bible as book-wide defaults.
3. Use the chapter spec's `chapter_engine`, `pressure_source`, `state_shift`, and `texture_mode` to judge whether an exchange should be carrying stake or is licensed as pure texture.

Severity guidance:
1. `HIGH` — the failure dominates a chapter beat that the spec or the surrounding scene clearly intends to carry stake (intimate, grief, confrontation, decision, hand-off); or the failure pattern is the chapter's dominant dialogue register.
2. `MEDIUM` — isolated occurrence; the surrounding chapter still does dramatic work even though this exchange flatlines.

Pass-hint defaults:
1. `D1 dialogue_does_no_work`, `D8 exchange_overlong_for_beat`, `D9 trailing_topic_add`: default `p1_structural_craft` (the fix is usually structural — cut, replace, restructure, or relocate — not polish).
2. `D2 interchangeable_voices`, `D3 ceremonial_register_overapplied`, `D5 affirmative_volley`, `D6 adverbial_tag_or_telling_tag`, `D7 scene_stake_unregistered`: default `p2_dialogue_idiolect_cadence`.
3. `D4 narrator_paraphrase_dialogue_patch`: default `p3_prose_copyedit` (the fix is on the narration side).
4. Override the default only when the specific fix in `rewrite_direction` clearly belongs to a different pass.

No-holistic-pass rule:
1. Do not credit an exchange as "doing real chapter work overall" and skip per-turn auditing inside it. The fact that an exchange contains one working beat does not exempt the surrounding turns. Walk every contiguous run of ≥4 turns inside every exchange and check D5 and D8 against that run specifically. If the central beat occupies turns 12–18 of a 30-turn exchange, turns 1–11 and 19–30 are still in scope — fire D8 against the runs that bloat them.
2. The exchange-level `summary` field may note that a central beat works, but it must also name the bloat or texture failures inside the same exchange when D5/D8/D9 fire.

Acceptance test guidance:
1. Acceptance tests must be verifiable by reading the revised passage. Name what the revised exchange must do — what stake it must register, which lines must diverge in voice, which ceremonial lines must contract, which paraphrase must be cut.
2. Avoid bean-counting tests. Anchor to specific lines.
3. Example acceptable form: "After revision, between {{CHAPTER_INPUT_FILE}}:142 and {{CHAPTER_INPUT_FILE}}:151, at least two of Benjamin's responses register a body or recognition (a refusal, a flinch, an unspoken counter), and Tariq's logistical lines (`We will go to the cemetery now`, `I will drive`) contract while the offered-water line keeps its ceremonial register."

Required output:
1. `{{DIALOGUE_DIAGNOSTIC_OUTPUT_FILE}}`

`{{DIALOGUE_DIAGNOSTIC_OUTPUT_FILE}}` contract:
1. Top-level fields:
2. `chapter_id` (string; must equal `{{CHAPTER_ID}}`)
3. `cycle` (integer; write `{{CYCLE_INT}}`)
4. `exchanges_indexed` (array of strings; the dialogue-exchange ids you assigned, in order — e.g. `["exchange_01", "exchange_02"]`. Assign one id per contiguous dialogue exchange you walked.)
5. `findings` (array)
6. `summary` (string; brief — what kind of dialogue failures dominate, or "no dialogue failures detected" if the chapter is clean)
7. Each finding object must contain:
8. `finding_id` (string; stable within this chapter, e.g. `DD-{{CHAPTER_ID}}-001`)
9. `subcategory` (one of: `dialogue_does_no_work`, `interchangeable_voices`, `ceremonial_register_overapplied`, `narrator_paraphrase_dialogue_patch`, `affirmative_volley`, `adverbial_tag_or_telling_tag`, `scene_stake_unregistered`, `exchange_overlong_for_beat`, `trailing_topic_add`)
10. `severity` (`MEDIUM|HIGH|CRITICAL`)
11. `chapter_id` (must equal `{{CHAPTER_ID}}`)
12. `exchange_id` (the assigned exchange id where the failure occurs)
13. `evidence` (must cite at least one `{{CHAPTER_INPUT_FILE}}:<line>` reference; multiple cites separated by `; `; for D2/D3, cite at least one line per speaker)
14. `problem` (string; for D2 and D3, name the specific style-bible fields being violated; for D4, quote the paraphrase placeholder)
15. `rewrite_direction` (string; specify the cut, the structural replacement, the contracted form, or the concrete observation — anchored to specific lines/spans in `{{CHAPTER_INPUT_FILE}}:<line>` form)
16. `acceptance_test` (string; concrete and verifiable by reading the revised passage)
17. `pass_hint` (`p1_structural_craft|p2_dialogue_idiolect_cadence|p3_prose_copyedit`)

Example structure only. Do not copy wording, IDs, evidence, or summary language from this example.

```json
{
  "chapter_id": "chapter_05",
  "cycle": 1,
  "exchanges_indexed": ["exchange_01", "exchange_02"],
  "summary": "Cemetery-pattern flattening in exchange_01 (no stake registered, voices interchangeable, ceremonial register over-applied); narrator paraphrase patch in exchange_02.",
  "findings": [
    {
      "finding_id": "DD-chapter_05-001",
      "subcategory": "dialogue_does_no_work",
      "severity": "HIGH",
      "chapter_id": "chapter_05",
      "exchange_id": "exchange_01",
      "evidence": "{{CHAPTER_INPUT_FILE}}:142; {{CHAPTER_INPUT_FILE}}:151",
      "problem": "...",
      "rewrite_direction": "...",
      "acceptance_test": "...",
      "pass_hint": "p1_structural_craft"
    }
  ]
}
```
