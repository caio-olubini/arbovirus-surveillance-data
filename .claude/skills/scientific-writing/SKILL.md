---
name: scientific-writing
description: >-
  Drafts and polishes English scientific prose for articles, data papers,
  theses and dissertations in an accessible Nature-style voice, then revises
  it through at least four self-critique passes that remove LLM tells
  (dashes, meta-commentary, stacked hedging, template transitions, empty
  intensifiers). Use when the user asks to write, draft, rewrite, polish or
  edit a manuscript section or boilerplate (Abstract, Introduction, Methods,
  Data Records, Technical Validation, Usage Notes, Data/Code Availability,
  Discussion, captions), or gives a brief of what a section should say,
  including briefs written in Portuguese.
---

# Scientific writing

The user decides what the text says. The agent decides how it reads. Output
is English, whatever the language of the brief.

Target voice: technology and computational articles in *Nature* and
*Scientific Data*. Accessible to a reader from an adjacent field, without
losing technical precision. Fluid, objective, no commentary about the text
itself. The rhythm comes from `references/style-traits.md`; read it before
the first draft of every session.

## Modes

- **Draft**: the user gives a brief (bullets, notes, facts, numbers, maybe in
  Portuguese). Produce the section.
- **Polish**: the user gives their own text. Keep every claim, number,
  term and citation marker; change only expression. Stay within ±15% of the
  original length unless asked otherwise.

Infer the mode from the request. If the user pastes a reference paragraph
("write in this rhythm"), its cadence overrides the defaults in
`style-traits.md` for that session.

## Intake

Before drafting, settle silently from context:

1. Mode, section type, target journal or genre (default: *Scientific Data*
   Data Descriptor, then research article).
2. Output format: mirror the request or the user's draft (Markdown, LaTeX,
   plain). Default is plain paragraphs with no headings the user did not ask
   for.
3. Spelling: match the manuscript; otherwise US English.
4. Length: as requested; otherwise what the section conventionally needs
   (`references/sections.md`).

If a fact needed for the section is missing and no honest sentence can be
written without it, ask for it in one short list before drafting. If the gap
is a single value, use a placeholder like `[N]` and list it after the text.

## Fidelity rules

- Write only what the brief, the user's draft or earlier messages support.
  Never invent numbers, dates, versions, datasets, results or prior findings.
- Bridges are allowed only as a connective clause or at most one sentence of
  textbook-stable background. Nothing about trends, effect sizes or what
  "studies have shown".
- Keep the user's citation markers exactly. Never add citation markers to
  the body.
- Citation suggestions go only in the optional end block (see Delivery), at
  most two, only when the brief asks for literature support, and only
  canonical works any reviewer in the field would expect (e.g. Hersbach et
  al. 2020 for ERA5, Ginsberg et al. 2009 for search-based surveillance,
  Wilkinson et al. 2016 for FAIR). If the exact reference is uncertain,
  suggest nothing. Never output a DOI from memory.

## Revision loop

Write the draft to a scratch file (e.g. `/tmp/scientific-writing-draft.md`)
so the linter can read it. Then run **at least four passes**, each with its
own lens. Edit the scratch file in place after every pass.

**Pass 1: Fidelity and content.** Check every sentence against the brief
(checklist H0). Remove invented material. Confirm all requested points are
present and in the order of `references/sections.md`.

**Pass 2: Architecture and rhythm.** Paragraph level. Each paragraph opens on
content (T1); lengths differ; logic lives in sentence order (T12); concrete
anchors where a concept appears (T3); no wrap-up endings (T13). Break any
template symmetry (S8).

**Pass 3: Sentence and lexicon.** Run the linter:

```bash
python3 .claude/skills/scientific-writing/scripts/lint_prose.py /tmp/scientific-writing-draft.md
```

Run it from the repository root, so the path resolves. If the working
directory is elsewhere, use the absolute path to the script.

Fix every hard fail by rewriting the sentence, not by swapping a synonym into
the same template. Add `--allow term1,term2` only for words the brief
justifies or that are technical terms. Review soft flags and rewrite the
conspicuous ones.

**Pass 4: Cold read.** Reread as a reviewer from an adjacent field who will
read the paper once. Undo nominalisations, replace category nouns with
specific ones, check that every abbreviation is defined at first use, and
apply the human-texture checks in `references/checklist.md`. Rerun the
linter, since rewrites introduce new tells.

**Exit gate.** Deliver only when, after at least four passes, the linter
reports zero hard fails and every hard item in `references/checklist.md`
passes on manual review. If anything fails, repeat passes 3 and 4 (and pass
1 if content changed). Stop at eight passes; if a hard item still fails,
deliver and state that item in one line after the text.

Keep a short internal log per pass (what failed, what changed). Do not show
it unless the user asks ("show critique", "mostra a crítica").

## Delivery

Output, in this order and nothing else:

1. The text, in the agreed format. No preface ("Here is..."), no closing
   remark, no summary of changes.
2. `Suggested citations (optional):` only under the conditions in Fidelity
   rules. One line each: author, year, venue, and the claim it would support.
3. `Missing inputs:` only if placeholders are present.

If the user writes in Portuguese, any message outside the text itself
(questions, missing inputs) can be in Portuguese. The text stays English.

## References

- `references/style-traits.md`: sixteen rhythm and voice traits with short
  excerpts from open-access Nature and Scientific Data articles.
- `references/checklist.md`: hard fails (H0 to H7), soft flags (S3, S6, S8)
  and human-texture checks.
- `references/sections.md`: move order for each section type, including data
  paper boilerplate.
- `scripts/lint_prose.py`: lexical checker; exit code 1 on any hard fail.
