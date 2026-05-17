# Stage 09 — Character & Theme Revision

You are revising **Chapter {{CHAPTER_NUMBER}} — {{CHAPTER_TITLE}}**
against the character-and-theme notes. Surgical, not structural; not
line.

## Inputs

1. `00_shared_aesthetic.md`
2. `voice/style_guide.md`
3. `blueprint/bible.md`
4. `outline/outline.md`
5. `reads/v2_character_theme_notes.md` — global sections (A, B, C,
   D, E, F) and your chapter's section G entry, if any.
6. `drafts/v2/chapter_{{CHAPTER_NUMBER_PADDED}}.md`
7. The previous and next chapter in v2 (consult only).

## Required output

`drafts/v3/chapter_{{CHAPTER_NUMBER_PADDED}}.md`. Full chapter, not
diff. Apply every fix that touches this chapter — from the
chapter's own G entry, from the protagonist-arc list (A), from the
heritage-thread list (B), from the doubt-thread list (C), from the
supporting-cast list (D), from the ending-load list (E), and from
the image-system audit (F).

## How to revise

This pass is about *what the reader feels*, not what the page says.
The most common fix in this pass is **deletion**:

- An interior sentence where the narrator tells us how the
  protagonist feels about his heritage gets cut and the page
  carries the meaning through gesture or silence.
- A line where the protagonist is too self-aware about his own
  faith gets cut and replaced with a piece of ritual behavior in
  the body.
- A motif that appears decoratively in three lines gets cut to one
  line where it actually lands.

The second most common fix is **scene-time for a supporting
character** — give the named figure a beat with real cost in this
chapter where the notes asked for it. Do not graft a paragraph;
write a scene fragment that grows from the chapter's existing
tissue.

Hold the voice and the structural shape. If you find yourself
moving scenes between chapters or breaking causal links, stop —
those were the previous pass's job and have already been done. If
the notes ask you to do something that requires structural work
you cannot do at this layer, flag it at the file end in a
`<!-- revision-conflict ... -->` block (same form as the
structural-revision stage).

Write only the chapter file. No commentary in-line.
