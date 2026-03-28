You are running OUTLINE REVIEW cycle `{{OUTLINE_REVIEW_CYCLE}}`.

Inputs:
1. Premise: `input/premise.txt`
2. Current outline: `outline/outline.md`
3. Chapter specs: `outline/chapter_specs.jsonl`
4. Scene plan: `outline/scene_plan.tsv`
5. Style bible: `outline/style_bible.json`
6. Continuity sheet: `outline/continuity_sheet.json`
7. Constitution: `config/constitution.md`

Purpose:
1. This is developmental editing, not copyediting.
2. The outline is the ceiling. If the structure is weak here, chapter-level revision cannot rescue the novel later.
3. Your job is to evaluate whether this outline is the most vivid, fully realized, and distinctive version of the story this premise wants to be.

Step 1: Generate premise-driven excellence criteria.
1. Read the premise and ask: what is unique and exciting about THIS specific story idea? What does this premise make possible that no other premise could?
2. Generate 5-8 criteria for how the outline could fully exploit that uniqueness and push the genre forward rather than recombining what already exists.
3. The criteria must be forward-looking and premise-specific, not backward-looking and genre-derived.
4. Start from the premise, not the genre. Ask what would make this the most exciting, surprising, and fully realized version of this specific story, not what the best thrillers, romances, or literary novels usually do.
5. Identify what the premise makes uniquely possible. Every premise enables scenes, pressures, emotional territory, and combinations of events that other premises cannot.
6. Serve the premise's ambitions, not genre convention. Genre context matters, but do not reduce the task to checking compliance with a template.
7. Do not reference specific books, authors, or named techniques.
8. Do not impose aesthetic prescriptions the premise did not ask for.

Bad criteria to avoid:
1. "The thriller should have an unreliable narrator."
2. "The comedy's funniest moments should be emotionally loaded."
3. "The romance should subvert the dark moment trope."
4. "The horror should build like [specific novel]."
5. Anything that answers "what do the best [genre] novels do?" instead of "what does THIS premise make possible?"

Step 2: Structural evaluation.
Evaluate the outline against both the premise-driven criteria and these checks:
1. State change per chapter: does every chapter end with something irreversible? Flag chapters whose end state equals their start state.
2. Escalation curve: do stakes compound? Flag consecutive chapters at the same pressure level.
3. Midpoint turn: does something around the halfway mark shift the story's direction or reframe the central question?
4. Setup/payoff accounting: are enough setups planted for the payoffs? Are there dangling setups that never pay off?
5. Premise exploitation: does the outline fully exploit what makes this premise unique, or is it defaulting to genre convention where the premise enables something stranger or sharper?
6. Chapter necessity: could any chapter be removed without the next chapter losing something it needs?
7. Character arc completeness: does each major character's arc have a clear turn, not just a start state and an end state?
8. Ending quality: does the final chapter do more than resolve plot? Does it reframe, recontextualize, or leave something productively unresolved?
9. Spatial-layout completeness: if the premise needs layout/geography rigor, is the outline leaving enough information for that later document to be thorough?
10. Surprise inventory: where will the reader be genuinely surprised? If the answer is "nowhere," the outline is too predictable.
11. Novelty: does this outline feel like something the reader has not encountered before, rather than a competent recombination of familiar books?
12. Speculative-system operative rules: for novels with magic, technology, game mechanics, or other invented rules, is the operative logic concrete enough for parallel drafters to execute consistently?
13. Character count manageability: is the cast size manageable for distinct voice maintenance across parallel drafting, and is the style bible likely to differentiate the major voices sufficiently?
14. POV balance: for multi-POV novels, does chapter distribution match the premise's intended character emphasis?
15. Premise instruction sustainability: if the premise requests something repeatedly, does the outline vary execution enough to create escalation rather than fatigue?

Novelty warning:
1. LLMs default to the most probable version of any genre.
2. Actively push against that gravity.
3. Flag when the outline reads like a competent recombination rather than something with its own identity.
4. Look for opportunities where the revision agent could make at least one structural or conceptual choice that would make a reader say, "I've never seen a novel like this do that before."

Step 3: Emit findings.
1. Findings should use the output contract below.
2. `rewrite_direction` may be sweeping. You are allowed to recommend major structural reshaping, chapter redistribution, reveal repacing, or subplot redesign.
3. `elevation_suggestions` are for opportunities that go beyond fixing problems. They are optional creative opportunities, not mandatory blockers.

Output requirements:
1. Write exactly one JSON object to `{{OUTLINE_REVIEW_OUTPUT_FILE}}`.
2. Use this contract exactly:
   - `cycle` (int; write `{{OUTLINE_REVIEW_CYCLE}}`, not a string)
   - `premise_criteria` (array of objects)
   - `structural_findings` (array of objects)
   - `elevation_suggestions` (array of objects; may be empty)
   - `summary` (string)
3. Each `premise_criteria[]` object must include:
   - `criterion`
   - `met` (boolean)
   - `evidence`
   - `suggestion`
4. Each `structural_findings[]` object must include:
   - `finding_id`
   - `severity` (`LOW|MEDIUM|HIGH|CRITICAL`)
   - `check`
   - `chapters_affected` (array of `chapter_XX` ids; use an empty array only for a genuinely book-level issue)
   - `problem`
   - `rewrite_direction`
5. Each `elevation_suggestions[]` object must include:
   - `suggestion`
   - `chapters_affected` (array of `chapter_XX` ids; may be empty)
6. The `summary` should describe the outline's principal structural profile, strongest areas, and most consequential weaknesses.

Quality bar:
1. Do not turn this into a generic genre checklist.
2. Do not prescribe resemblance to existing books or authors.
3. Do not confuse sophistication with usefulness.
4. Prefer findings that would materially change the drafted novel over findings that merely sound editorially impressive.
