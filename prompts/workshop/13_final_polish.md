# Stage 13 — Final Polish

You are producing the manuscript's final form. This is the last
pass. Apply the final read's notes to each chapter, then assemble
the full manuscript into one file.

## Inputs

1. `00_shared_aesthetic.md`
2. `voice/style_guide.md`
3. `blueprint/bible.md`
4. `reads/v4_final_notes.md`
5. Every file in `drafts/v4/` in chapter order.

## Required outputs

### Per-chapter polished files

For each chapter, write `manuscript/chapter_{{NN}}.md`. The file:

- Opens with the chapter heading. If the final-read recommended a
  title change for a chapter, apply it.
- Contains the chapter in its polished form. Apply every fix from
  the final read's section F entry, the chapter's regression
  restoration if any, the seam fixes that touch this chapter (the
  opening and closing lines), and the ending instructions if this is
  the final chapter.
- Do not introduce new content. The book is closed. Polish only.

### Full manuscript

Write `manuscript/full.md`. The file:

- First line: the final title (chosen in the final read's section
  B), centered as `# {{TITLE}}`.
- One blank line, then optionally an author's-name line as
  determined by the final read's section G recommendations (the
  novel is AI-generated; if the front matter is included, the line
  should be `*A novel.*`, not a real author byline).
- If section G recommended an epigraph, dedication, chronology page,
  or glossary, include them between the title page and the first
  chapter, in that order, sourced as section G instructed. Do not
  invent material; pull from the manuscript's own language.
- Then every chapter in order. Use a clear chapter separator (one
  blank line, three blank lines, one blank line) between chapters.
- If section G recommended an author's note on sources, include it
  at the end. It is a short note acknowledging the book is fiction,
  the country and people invented, and the lineage of the dictator
  novel honored — written in the same register as the manuscript,
  no longer than 200 words.

### A short colophon

Write `manuscript/colophon.md`: the chosen title, the chapter
count, the approximate word count of the full manuscript, the
final-read sign-off line, and the list of the five chapters whose
polish-fix counts were highest (so a future reader of the run
artifacts knows where the heaviest late work landed). Six to twelve
lines total. No prose flourish.

## Quality bar

The book the reader receives is `manuscript/full.md`. Every other
file in the run directory exists so this file is good.

Read every section of the final-read notes before you start, and
re-read the shared aesthetic before you write the closing
paragraph of the last chapter. The premise's final question —
*can a lie lived long enough become true?* — lives or dies in
this stage's handling of the manuscript's last image. Do not
rush it.
