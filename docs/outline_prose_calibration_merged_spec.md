# Outline + Prose Calibration Spec

Combines the latest versions of:

- `~/Downloads/prose_calibration_spec.md`
- `~/Downloads/chapter_edge_structure_spec.md`

The goal is to reduce narrator performance at the source, strengthen chapter boundary contracts, improve middle-book structural variety, and preserve secondary-character depth in forms the pipeline will keep rather than cut.

---

## Part I: Prose Calibration at the Source

These changes target narrator performance upstream in the style bible, draft prompt, expand prompt, and revision prompt rather than relying solely on review and revision to catch it after the fact.

### Change 1: Style Bible Prose Profile (Outline Prompt)

#### Problem

The outline agent generates `prose_style_profile` fields that describe literary targets: "Comma-heavy run-ons in panic or exhilaration," "longer sentences that build to turns," "varied by chapter texture and scene pressure." The draft agent treats these as per-sentence mandates and produces narrator performance trying to hit them on every line. The one novel where the prose profile said "Plain, direct, Anglo-Saxon-dominant... The prose should be invisible" (The Drawer) had the least narrator-performance problem.

#### Fix

Add to the outline prompt's `prose_style_profile` guidance:

> The `prose_style_profile` should describe how the novel sounds at its most ordinary, not at its peaks. Most paragraphs in a well-written novel are plain and specific — they deliver what happens in the room without drawing attention to the sentence. Set `diction` and `rhythm_target` for the default baseline register: the prose between the big moments, not the big moments themselves. Exceptional pressure, variation, and craft belong in `chapter_texture_variance`, not in `diction` or `rhythm_target`. The draft agent will treat `diction` and `rhythm_target` as its primary voice reference for every line it writes. If `diction` says "compressed, imagistic," the draft agent will try to compress and image on every line. If `diction` says "plain, concrete, specific to the physical world of the story," the draft agent will write transparent prose and save the craft for moments that earn it.

### Change 2: Draft Prompt — Last Sentence Check

#### Problem

Narrator performance clusters at the end of scene beats. The model lands an image or a dialogue exchange, then adds one more sentence that interprets, repackages, or elevates what the scene already conveyed. This is the single most common location for composed narration.

#### Fix

Add to the "Constitution-critical writing checks" section of `chapter_draft_prompt.md`:

> The last sentence of a scene beat or paragraph cluster where a local turn has already landed is the most likely location for narrator commentary. After completing a beat, reread the final sentence. If it restates, interprets, or repackages what the preceding action or dialogue already conveyed — cut it. If it adds something the reader doesn't yet have — new information, a changed condition, an unanswered question, a concrete detail that reframes what came before — keep it.

### Change 3: Expand Prompt — Anti-Commentary Expansion

#### Problem

The expand step adds words to thin chapters. The easiest way to add words is narrator interpretation — commentary, thematic reflection, interior monologue explaining what the scene means. This is the step most prone to narrator performance because the agent is explicitly trying to increase word count.

#### Fix

Add to `chapter_expand_prompt.md`:

> When expanding, add scene material — sensory detail, character behavior, environmental texture, functional dialogue. Do not expand by adding explanatory interior monologue that translates the scene into cleaner meaning. Interior thought is still valuable when it creates a new fear, choice, misreading, or pressure — but not when it summarizes what the action already showed. A scene that needs more words needs more of what happens in the room, not more of the narrator reflecting on what happened.
>
> When expanding a passage, do not cap it with a sentence that interprets or frames the material you just added. If your final added sentence restates, summarizes, or repackages what the expanded scene already conveyed, delete it. Expansion should end on something the reader doesn't yet have — not on the narrator explaining what they just received.

### Change 4: Revision Prompt — Last Sentence Check Mirror

#### Problem

Revision can introduce or preserve interpretive cappers just as drafting can. When the revision agent rewrites a passage to fix a finding, its natural instinct is to close the rewritten material with a neat, literary sentence — the same narrator-performance pattern the draft produces.

#### Fix

Add to `chapter_revision_prompt.md`:

> When rewriting a passage to address a finding, check the last sentence of the rewritten material. If it restates, interprets, or repackages what the revised action or dialogue already conveyed, cut it. Revision should not introduce interpretive cappers that the draft did not have, and should remove cappers that the draft did have when they are redundant with the scene.

---

## Part II: Chapter Edge Structure + Middle Repetition

These changes target recurring structural problems observed across every novel the pipeline has produced.

### Change 5: Chapter Edge Fields in `chapter_specs.jsonl`

#### Problem

The current chapter specs have strong mid-chapter structure (`chapter_engine`, `pressure_source`, `state_shift`, `texture_mode`, `scene_count_target`, `must_land_beats`) plus `scene_plan.tsv`. But they don't anchor how chapters enter and exit. This produces the same edge failures in every novel:

- **Opening reorientation drag** — chapters re-establish setting, characters, and situation the reader already knows
- **Repeated openings** — consecutive chapters open with the same structure (retrospective time-jump, status briefing, character-waking-up)
- **Chronology gaps at boundaries** — reader can't tell how much time passed between chapters
- **Closing over-explanation** — narrator paraphrases the scene's meaning after it already landed
- **Soft exits** — chapters end on resolved states rather than live pressure

#### Fix

Add five lightweight fields to each chapter in `chapter_specs.jsonl`:

**`opening_situation`** (one sentence)  
Where we are, what pressure is already live, and what is different from the prior chapter's exit. This tells the draft agent what the reader already knows, preventing re-briefing.

Example: "Mara is in the rented Accord two blocks from campus. The fragment transfer is seven minutes in. She hasn't heard from Dex since the badge alert."

**`closing_state`** (one sentence)  
The concrete new condition, decision, exposure, loss, or unresolved pressure the reader should leave with. Not a theme — a fact.

Example: "Dex has lied to Mara about the routing anomaly. The transfer is complete. He is driving home alone."

**`chronology_anchor`** (short phrase)  
How this chapter relates in time to the previous chapter's ending.

Examples: "immediate," "minutes later," "same afternoon," "three hours later," "next morning," "two days later," "after the arraignment." Use whatever phrasing is natural for the gap — this is a human-readable anchor, not a fixed enum.

**`entry_obligation`** (one sentence)  
What the opening movement (roughly the first 3-5 paragraphs) must accomplish besides reorienting. What new information, pressure, or situation should the reader encounter there?

Example: "The reader learns the anomaly detection threshold has moved up by two days."

**`exit_pressure`** (one sentence)  
What must still feel active and unresolved at the chapter's cutoff. This prevents soft endings where the chapter resolves its tension before cutting.

Example: "Callum has seen something in the backup logs he hasn't told anyone about yet."

#### Why These Fields, Not Opening/Closing Scenes

Full scene descriptions would over-constrain the draft agent and produce templated chapters. These five fields are operational contracts — they tell the draft agent what the reader's state should be at entry and exit without prescribing how to get there. The draft agent still invents the scenes.

#### Canonical Full-Row Example

To reduce validation failures, the outline prompt should include one concrete `chapter_specs.jsonl` example showing all five edge fields in context:

```json
{
  "chapter_id": "chapter_08",
  "chapter_number": 8,
  "projected_min_words": 4200,
  "chapter_engine": "consequence",
  "pressure_source": "the previous failed transfer has exposed a new vulnerability in Dex's route",
  "state_shift": "Mara realizes the anomaly is inside their own workflow, not outside it",
  "texture_mode": "tight, suspicious, aftermath-heavy",
  "scene_count_target": 2,
  "must_land_beats": [
    "Mara sees the altered threshold",
    "Dex conceals that he has already noticed it"
  ],
  "opening_situation": "The morning after the failed transfer, Mara is back in the rented office with Dex, reviewing logs that should have matched overnight behavior.",
  "closing_state": "Mara has seen enough to know the anomaly is real, but she still does not know Dex is the one hiding part of it.",
  "chronology_anchor": "next morning",
  "entry_obligation": "The opening movement must make clear that the failed transfer changed the team's confidence and that the logs now contain something newly wrong.",
  "exit_pressure": "Dex must still be withholding the routing truth when the chapter cuts."
}
```

This example is useful because it shows the distinction between:

- `opening_situation`: where/when/what is already live
- `entry_obligation`: what the opening movement must newly accomplish
- `closing_state`: what concrete condition has changed by the end
- `exit_pressure`: what remains active and unresolved at the cut

Without an example like this, the outline agent is likely to collapse the fields into near-duplicates.

#### Outline Prompt Changes

Add to the chapter specs contract in `outline_prompt.md`:

> Each chapter spec must include five edge fields: `opening_situation` (one sentence: where we are, what's live, what changed), `closing_state` (one sentence: the concrete new condition the reader leaves with), `chronology_anchor` (how this chapter relates in time to the previous), `entry_obligation` (what the opening movement must accomplish beyond reorienting), and `exit_pressure` (what must still feel unresolved at the cut). These fields define what the reader should already know at entry and what should still be live at exit, helping prevent reorientation drag, chronology gaps, and closing over-explanation.

#### Runner Validation Changes

Because downstream stages rely on these fields as real planning data, the runner should validate them strictly when loading `chapter_specs.jsonl`.

- Every chapter spec must include all five edge fields.
- Every edge field must be a non-empty string.
- Missing or blank edge fields should fail outline validation rather than silently defaulting.
- Minimal normalization is fine (trim whitespace, normalize internal spacing), but the runner should not invent values for missing fields. If `chronology_anchor` or `exit_pressure` is absent, that is an outline-stage failure that should be repaired in the outline rather than guessed downstream.

#### Outline Review Changes

Add to the outline review's structural checks:

> Check that each chapter's `opening_situation` does not materially duplicate the previous chapter's `closing_state`. If they describe substantially the same condition, the chapter is opening where the previous one already ended — flag as reorientation drag.
>
> Check that `chronology_anchor` values form a coherent timeline across the full chapter sequence. Flag gaps where the reader cannot reconstruct elapsed time.
>
> Check that `exit_pressure` values are distinct across consecutive chapters. If three chapters in a row exit on the same type of pressure (e.g., "will the next attempt work?"), the middle is repetitive.
>
> Check that each chapter's edge fields are internally consistent with the rest of that chapter's planning artifacts. `opening_situation`, `closing_state`, `entry_obligation`, and `exit_pressure` should agree with the chapter's prose summary in `outline.md`, its `must_land_beats`, and its `scene_plan.tsv` rows. If the edge fields describe a different chapter from the one the beats and scene plan describe, flag it. These fields are additive metadata, not an alternate outline that is allowed to drift from the main one.

#### Draft Prompt Changes

Add to `chapter_draft_prompt.md`:

> The chapter spec includes edge fields: `opening_situation`, `closing_state`, `chronology_anchor`, `entry_obligation`, and `exit_pressure`. Use `opening_situation` to enter the chapter without re-briefing — the reader already knows what it describes. Use `chronology_anchor` to orient the reader in time within the first few lines. Use `entry_obligation` to ensure the opening does more than reorient. Use `closing_state` and `exit_pressure` to end the chapter cleanly — land the closing state and cut while the exit pressure is still live. Do not paraphrase the chapter's meaning after the closing beat has landed.

#### Expand Prompt Changes

Add to `chapter_expand_prompt.md`:

> The chapter spec's edge fields still apply during expansion. Use `opening_situation` and `entry_obligation` to avoid padding the opening with repeated setup. Use `closing_state` and `exit_pressure` to avoid expanding past the chapter's intended exit point. Expansion may deepen the scene material that leads to the closing state, but it must not continue past the beat the chapter is meant to end on or resolve the live pressure that should still be active at the cut.

#### Local Window Audit Changes

The local window's pre-scan already checks for chronology gaps (P3), repeated information (P6), and dangling threads (P8). Local-window jobs should read the per-chapter spec files for the chapters in their window, not just the manuscript text, so these checks can validate against the edge fields directly. If `chronology_anchor` says "next morning" but the chapter opens with no time marker, P3 fires. If `opening_situation` duplicates the previous chapter's content, P6 fires.

#### Chapter Review Changes

Add to `chapter_review_prompt.md`:

> Check the chapter's opening movement (first 3-5 paragraphs) against its `entry_obligation` from the chapter spec. If the obligation is not met in the opening movement, flag it. Check the chapter's closing against its `closing_state` and `exit_pressure`. If the chapter ends past its closing state (narrator continues after the beat has landed) or resolves the exit pressure before cutting, flag it.

### Change 6: Dramatic Function Variety Check in Outline Review

#### Problem

Every novel the pipeline produces has a middle-section repetition problem. The outline agent generates consecutive chapters with the same dramatic function:

- Burn Rate: Ch 5-8 all end on campfire-rule pattern (camp, take stock, derive a rule)
- Noise Floor: Ch 4-5 are the same planning night split arbitrarily
- Secondhand Thoughts: Ch 2-4 repeat public-event/probe/contact-handoff
- The Drawer: Ch 6-10 cycle through attempt → fail → debrief with Sterling

The beginning of a novel is inherently varied (setup, different characters, world establishment). The ending is inherently unique (climax, resolution). The middle is "characters working toward the goal," which defaults to the same shape repeated: attempt → complication → partial progress → reflection.

#### Fix

Add to the outline review's structural checks (#16 or next available number):

> **Dramatic function variety.** Among any 3 consecutive chapters in the middle third of the novel, flag when any pair shares the same `chapter_engine` AND the same `state_shift` shape or `exit_pressure` shape. Matching engine labels alone are not sufficient to flag — legitimate reprises that do genuinely new work should not be false-positived. The true test is: same engine plus same trajectory (attempt/fail/reflect three times, or briefing/operation/debrief three times, where the state shift and exit pressure are structurally interchangeable). Each middle chapter should have a different primary mode: escalation, revelation, betrayal, loss, alliance shift, world-expansion, character backstory surfacing under pressure, a test with new rules, a consequence that changes the terms. The middle is where novels lose readers. Structural variety is what keeps them.
>
> When flagging, the rewrite direction should suggest specific alternative functions for the repeated chapters. "Ch 8 is the third attempt-fail chapter in a row. Replace its engine with a consequence chapter — instead of another attempt, show what the previous failures have cost, and let that cost change what Ch 9's attempt looks like."

#### How This Interacts with Edge Fields

The `exit_pressure` field reinforces this check. If consecutive chapters exit on the same type of pressure ("will the next attempt work?" three times in a row), the outline review catches it through both the variety check and the exit-pressure repetition check. The two mechanisms are complementary: the variety check catches same-shape chapters, the exit-pressure check catches same-tension chapters.

#### Outline Revision Response

When the outline revision agent receives a dramatic-function-variety finding, it should:

- Change the `chapter_engine` of the repeated chapter to a different mode
- Update the `state_shift` to reflect the new engine
- Update the edge fields (`opening_situation`, `closing_state`, `entry_obligation`, `exit_pressure`) to match
- Ensure the `scene_plan.tsv` entries for that chapter reflect the new function
- Verify that the change doesn't break the adjacent chapters' `opening_situation` or `entry_obligation`

The revision should NOT simply relabel the same events with a different engine name. The chapter must actually do something different, not just be described differently.

### Change 7: Secondary Character Depth Through Scenes, Not Narration

#### Problem

The pipeline now correctly removes narrator commentary that explains what scenes already show. But in ensemble novels, secondary characters' depth often lives in that narrator commentary — delivered through the protagonist's internal reflections about what other characters are feeling, thinking, or representing. When the revision cuts Sterling's meditation on Ratchet's declining grip, Ratchet's depth disappears with it.

This happened systematically in The Drawer: the draft gave secondary characters (butter knives, Somm, Ratchet, the Chopsticks) their depth through Sterling's narrator-mediated observations. The revision correctly cut those observations. The result: a tighter novel with a thinner world.

The root cause: secondary character depth was stored in a format (narrator commentary) that the pipeline is trained to remove. The depth needs to be stored in a format (scenes, dialogue, independent action) that the pipeline preserves.

#### Fix: Outline Review Check

Add to the outline review's structural checks:

> **Secondary character scene independence.** Verify that significant secondary characters have moments where they act, speak, or reveal themselves independently — not observed by the protagonist, not filtered through the protagonist's interiority. For ensemble novels, at least 3 significant secondary characters need independent moments. For smaller-cast novels, enough non-protagonist characters that the world does not collapse into protagonist-only perception. If every secondary character's depth is delivered through the protagonist thinking about them, the revision will correctly cut that narration and the depth will disappear with it. Each significant secondary character needs at least one moment the reader witnesses directly: a conversation overheard, an action taken when no one is watching, a POV paragraph in a shared scene, a dialogue exchange where they drive the conversation rather than responding to the protagonist.
>
> When flagging, suggest where in the chapter sequence each secondary character's independent moment should live. "Ratchet's declining grip is described through Sterling's narration in Ch 6 and Ch 10. Give Ratchet a direct moment — a scene where the reader watches the grip fail without Sterling interpreting it."

#### Fix: Chapter Specs

The edge fields can occasionally be used to place secondary character beats — for example, an `entry_obligation` that opens on a secondary character acting independently, or a `closing_state` that names a secondary character's changed condition. But this should be a tactical choice for specific chapters, not the default container for all secondary character depth. Overusing it produces its own repetitive pattern (every chapter opens with a side character doing something). Secondary character moments can live anywhere in a chapter — openings, mid-scene beats, dialogue exchanges, brief POV shifts — and the outline's `scene_plan.tsv` is a better place to track them than the edge fields.

#### Fix: Draft Prompt

Add to the ensemble/character guidance in `chapter_draft_prompt.md`:

> When the chapter spec names a secondary character beat, render it as a direct scene — the reader watches the character act, speak, or react — not as the protagonist's internal commentary about the character. A secondary character whose depth exists only in the protagonist's narration about them will lose that depth during revision. Give them their own moments on the page.

#### Why This Works

The revision pipeline cuts narrator commentary and preserves scenes. If secondary character depth is delivered through scenes (Ratchet dropping a can, the butter knives arguing about classification, Somm counting days alone), the revision preserves it. If it's delivered through narration (Sterling thinking about how Ratchet's grip must feel, Sterling observing the butter knives' anxiety), the revision cuts it. The outline and draft stages need to put the depth in the right container.
