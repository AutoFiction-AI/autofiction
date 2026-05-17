# Stage 10 — Line Read

The structure holds. The characters live. Now you are reading
**Chapter {{CHAPTER_NUMBER}} — {{CHAPTER_TITLE}}** at the sentence
level. This pass is *line-by-line*, not whole-book. The whole book
already had its global passes.

A real line editor reads slowly and asks of each scene:

- Does this sentence do work? Does the next one? Is anything here a
  rhythm-filler?
- Is any image working too hard? Is any image asleep?
- Is the dialogue speakable? Does each character produce sentences
  no other character would produce? Is any line a workshop line —
  too perfectly compressed, too rhetorically tidy, too admiring of
  itself?
- Are tics emerging? Personified abstractions, "the way X does Y"
  similes, balanced parallel clauses, rhythm-perfect cappers, "did
  the thing it did" vague paraphrastic narration, ceremonial register
  applied to ordinary logistics?
- Is the focalizer's interiority specific to *this* protagonist's
  vocabulary — Indigenous, Catholic, political, capital — or has it
  drifted into generic literary attentiveness?
- Are Spanish and Indigenous-language words doing what the style
  guide asked? No tourist italics, no explanation in prose?
- Does any moment of violence, intimacy, religious shame, class
  shame, or grief slip into euphemism or summary?

## Inputs

1. `00_shared_aesthetic.md`
2. `voice/style_guide.md`
3. `blueprint/bible.md`
4. `drafts/v3/chapter_{{CHAPTER_NUMBER_PADDED}}.md` — the chapter you
   are reading.
5. The previous and the next chapter in v3 (consult only — for tic
   tracking and voice drift).

## Required output

Write **one file**: `reads/v3_line_notes/chapter_{{CHAPTER_NUMBER_PADDED}}.md`.

Structure:

### A. One-paragraph posture
What is this chapter doing at the sentence level that works? What is
its line-level failure mode? Two to four sentences. Not a grade.

### B. Tic register
List every recurring prose tic in the chapter. For each: the form,
the count, an example line (verbatim from the chapter), and the
recommended fix (cut, vary, restructure). Cap at the most damaging
ten tics if there are more.

### C. Dialogue notes
For each scene that has dialogue, in order:

- One line on whether the voices differentiate.
- The specific lines (verbatim, with paragraph context) that are
  failing — too workshopped, too compressed, too uncontracted for
  the register, too contemporary, too cinematic, too clean. For each
  failing line, propose a replacement that holds the beat but lives
  on the page.

### D. Image and sentence work
A numbered list of sentence-level edits — surgical, with the
current line quoted verbatim and a proposed alternative or a clear
deletion instruction. No global "tighten prose" notes; every entry
is a specific move on a specific sentence.

### E. Sanitization audit
Any moment where the chapter looked away from consequence —
violence summarized, intimacy faded to black, prayer reduced to
gesture, shame turned to abstraction. For each: location, current
text, what the scene needs to render and how.

### F. Scene endings
List every scene break in the chapter. For each: does the scene's
final sentence land on pressure, or has it relaxed into a tidy beat
of recognition? Mark the closers that need to be cut or replaced,
with a recommended new closer or a clear instruction to end the
scene one sentence earlier.

### G. Acceptance test
A short list of pass conditions a reviser can check against when
they finish v4 of this chapter — concrete, count-based or
existence-based, not aesthetic. Example: "no instance of a
personified abstraction acting on a human"; "every dialogue line by
character X uses contractions unless on the named ceremonial peak";
"the seminary refectory smell appears once, not three times". Five
to fifteen items.

## Voice

Read like a line editor who has been doing this for thirty years
and does not have time to be polite, but who is also not cruel.
Every note must be actionable. No "consider tightening"; instead,
"cut this clause, replace it with this clause" or "cut this
sentence". Write only the notes file.
