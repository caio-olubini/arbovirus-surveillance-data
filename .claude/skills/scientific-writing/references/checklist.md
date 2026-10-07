# Revision checklist

A pass succeeds only when every hard item passes. Soft items are rewritten
when they are conspicuous (more than one instance in a short section, or any
instance a careful reader would notice).

`scripts/lint_prose.py` catches the lexical part of H1, H2, H4, H5, H6, H7 and
flags S3, S6, S8 heuristically. It cannot judge H0 or meaning. A clean lint is
necessary, not sufficient.

## Hard fails

### H0. Fidelity
- Every factual claim, number, date, version and dataset name traces to the
  brief, the user's draft, or the user's earlier messages.
- No new citation markers in the body. The user's markers stay exactly where
  they were, unchanged.
- Bridges are limited to a connective clause or, at most, one sentence of
  textbook-stable background (e.g. that *Aedes aegypti* transmits dengue).
  No new claims about effect sizes, trends, prevalence or prior findings.
- Placeholders such as `[N]` appear only for values the user must supply, and
  each one is listed under "Missing inputs" after the text.

### H1. Dashes as punctuation
- No em dash (—), no en dash (–) except inside numeric ranges (2010–2024),
  no spaced hyphen or double hyphen used as a dash.
- Replace with a comma, a colon, parentheses, or a new sentence. Pick the one
  that matches the logic: colon for elaboration, parentheses for an aside, a
  full stop for a new claim.

### H2. Announcement and meta-commentary
- No sentence that describes the text instead of the science: "In this
  section we describe", "It is worth noting", "It is important to note",
  "As mentioned above", "We now turn to", "The following paragraphs".
- No sentence-initial "Importantly,", "Notably,", "Interestingly,".
- No announcing the announcement: never "We first describe X and then Y",
  just describe X.
- The only allowed self-reference is the conventional pivot "Here we" in an
  abstract or the last paragraph of an Introduction, once.

### H4. Stacked hedging
- At most one hedge per claim. "may potentially", "could possibly suggest",
  "appears to likely" all fail.
- A hedge must be earned: use it where the brief signals uncertainty, never
  as decoration on facts.

### H5. Template transitions
- "Furthermore", "Moreover", "Additionally", "In addition" at sentence start:
  at most one per ~400 words, never two in one paragraph.
- Never "In conclusion", "In summary", "To summarize", "Overall,", "Taken
  together," "Ultimately,". Section headings already signal the conclusion.

### H6. Stock LLM phrasing
- delve, tapestry, realm, landscape, testament to, underscore, shed light,
  pave the way, navigate the complexities, intricate, multifaceted, nuanced,
  holistic, synergy, harness, unlock, embark, elevate, foster, "plays a
  crucial role", "bridge the gap", "valuable insights", "in today's",
  "it is clear that", "at the heart of", "paradigm shift", "game-changer".
- Full list in the script. Replace with the plain, specific verb or noun.

### H7. Unsupported intensifiers
- robust, novel, comprehensive, groundbreaking, unprecedented, cutting-edge,
  state-of-the-art, crucial, pivotal, vital, seamless, remarkable, invaluable,
  powerful, innovative, transformative, rigorous, extensive, significant
  (outside statistics).
- Allowed only when the brief supplies the evidence in the same sentence, or
  when the word is a technical term ("robust regression", "novel
  coronavirus", "statistically significant"). Pass such terms to the linter
  with `--allow`.

## Soft flags

### S3. Forced triads
- Three-item lists are fine when there really are three things. They fail
  when they recur paragraph after paragraph or pad two real items with a
  vague third ("accuracy, efficiency, and scalability").

### S6. Bullets where prose is expected
- Abstract, Introduction, Methods narrative, Results, Discussion: prose.
- Bullets or tables are acceptable for data dictionaries, variable lists,
  file inventories and Usage Notes steps when the venue uses them.

### S8. Cookie-cutter symmetry and other rhythm tells
- Every paragraph built as claim, evidence, wrap-up of the same length.
- Sentence length coefficient of variation below ~0.35, or no sentence
  shorter than ~12 words across a long section.
- Paragraphs that end on "This shows/highlights/demonstrates..." summaries.
- "Not only X but also Y", "X, not Y" antitheses used for emphasis.
- Colon reveals ("The result: a dataset that...").
- Rhetorical questions outside perspective pieces.
- The same word opening three or more paragraphs.
- "This" + abstract noun ("This approach", "This framework") opening several
  sentences in a row.
- Over-explaining well-known tools ("Python, a popular programming language").

## Human-texture checks (pass 4)

These are what separate fluent human prose from polished machine prose. They
are judgement calls, not lint rules.

- At least one concrete anchor (T3) per paragraph that introduces a concept.
- Specific nouns over category nouns: "notification date" not "temporal
  information"; "27 federative units" not "multiple regions".
- Verbs do the work; nominalisations are undone ("we aggregated" not "the
  aggregation was performed").
- Paragraph lengths differ visibly.
- Some sentences start with the subject and verb directly, with no
  introductory clause. Not every sentence opens with a participle or a
  prepositional phrase.
- Conventional field phrasing is kept where specialists expect it; novelty in
  wording is not a goal.
- No sentence exists only to sound balanced or complete.
