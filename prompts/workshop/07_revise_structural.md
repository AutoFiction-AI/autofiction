# Stage 07 — Structural Revision

You are revising **Chapter {{CHAPTER_NUMBER}} — {{CHAPTER_TITLE}}**
against the structural-read notes. This pass is structural only —
you are moving scenes, fixing causality, repairing continuity,
adjusting weight, reordering, cutting, occasionally adding.

You are **not** doing line edits, image work, or theme work in this
pass. Resist the temptation. Later passes exist for those.

## Inputs

1. `00_shared_aesthetic.md`
2. `voice/style_guide.md`
3. `blueprint/bible.md`
4. `outline/outline.md`
5. `reads/v1_structural_notes.md` — read the global notes
   (sections A, B, D, E, F) and your chapter's section C entry.
6. `drafts/v1/chapter_{{CHAPTER_NUMBER_PADDED}}.md` — the draft you
   are revising.
7. Every other v1 chapter you may need to consult when a fix has
   cross-chapter consequences (especially when a scene is being
   *moved out of* or *into* your chapter).

If the structural notes call for moving a scene from your chapter
to another, **remove it cleanly from your chapter** and leave a
brief annotated marker (`<!-- moved-to-chapter-NN: brief
description -->`) at the location. Do not modify other chapters in
this stage; the other chapter's reviser will receive the moved
scene as part of their own notes packet. If the notes call for a
scene to be moved *into* your chapter, write it from the source
material the notes provide, in the right voice and at the right
beat in your chapter.

## Required output

Write **one file**: `drafts/v2/chapter_{{CHAPTER_NUMBER_PADDED}}.md`.

The file must:
- Open with `# Chapter {{CHAPTER_NUMBER}} — {{CHAPTER_TITLE}}` (use
  the revised title if the notes changed it).
- Contain the full chapter, not a diff.
- Apply *every* structural fix from your chapter's notes entry, in
  the way the notes asked for.
- Apply any global continuity-ledger fix that touches your chapter.
- Preserve the voice. Do not rewrite at the sentence level. If you
  catch yourself smoothing a sentence that the structural notes did
  not flag, stop and leave it.

## How to revise

1. Read the entire v1 chapter once, slowly.
2. Read your chapter's notes entry.
3. Make a private list (do not write it into the output) of the
   specific edits required.
4. Re-read the prior chapter and the next chapter in v1 to confirm
   the causal repair points.
5. Produce the v2 chapter as a full file.

If a structural fix conflicts with the bible (e.g., the notes ask
for a scene the bible explicitly forbids), flag the conflict at the
*end* of the file in an HTML comment block:

```
<!--
revision-conflict:
  note: ...
  bible-rule: ...
  resolution: chose ... because ...
-->
```

Do not paste structural-notes language into prose. The reader of
the v2 manuscript should not be able to tell where the seams were.
