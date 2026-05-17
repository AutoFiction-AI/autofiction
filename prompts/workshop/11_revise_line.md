# Stage 11 — Line Revision

You are revising **Chapter {{CHAPTER_NUMBER}} — {{CHAPTER_TITLE}}**
at the sentence level. This is the chapter's third revision pass.
Structural and character/theme work has already happened. **Do not
restructure. Do not reframe scenes. Do not relitigate.** Edit the
prose.

## Inputs

1. `00_shared_aesthetic.md`
2. `voice/style_guide.md`
3. `reads/v3_line_notes/chapter_{{CHAPTER_NUMBER_PADDED}}.md`
4. `drafts/v3/chapter_{{CHAPTER_NUMBER_PADDED}}.md`

## Required output

Write **one file**: `drafts/v4/chapter_{{CHAPTER_NUMBER_PADDED}}.md`.

The file must:

- Open with the same chapter heading as v3.
- Apply every line note. Where the note quoted a verbatim line, the
  v4 version must not contain that line; it must contain the
  proposed alternative, or be cut.
- Pass each item in the line-read's "acceptance test" section.
  Self-check before saving.
- Preserve word count within ±10% of the v3 chapter unless the line
  notes asked you to cut more aggressively.
- Carry the chapter's voice and rhythm. Line revision does not mean
  smoothing. The book's prose is alive on the page, not literary on
  the page — re-read the shared aesthetic and the style guide before
  saving.

## How to revise

Work scene by scene. Within each scene:

1. Apply the tic fixes from section B.
2. Apply the dialogue fixes from section C.
3. Apply the sentence-level edits from section D.
4. Repair any sanitization slip from section E.
5. Fix scene endings per section F.
6. Run section G as a self-check, paragraph by paragraph.

If a line note proposes a replacement you can improve on without
changing the scene's load, you may use a better replacement — but
you must hold the beat the line note targeted and you must not slip
back into the tic the note flagged. The notes are the floor of the
revision, not the ceiling.

If a line note cannot be applied without restructuring (a flag the
reviser should have caught and the line read should have routed
back), flag it at the end in a `<!-- revision-conflict ... -->`
block and leave the line as-is. The final read will catch it.

Write only the chapter file.
