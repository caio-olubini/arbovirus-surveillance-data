# Section patterns

Move order for each section type. A move is a function, not a sentence; one
move may take a clause or a paragraph. Skip moves the brief gives no material
for rather than filling them.

The default genre is a *Scientific Data* Data Descriptor, then a standard
research article. Follow the target journal's headings when the user names
one.

## Abstract (≤ 150–200 words, one paragraph)
1. Object and why it matters, one plain sentence (T2).
2. The gap, quantified if the brief allows.
3. "Here we" + what was built or found.
4. Scope in numbers: period, geography, sources, size.
5. Validation or main result with its number.
6. Use or availability, one sentence.

No citations, no abbreviations that are not reused, no "In this paper".

## Background & Summary / Introduction
1. The phenomenon, stated as fact, with the user's citations.
2. What existing data or methods do, and the specific shortfall.
3. Why the shortfall matters for an identifiable use.
4. What this work provides, with its distinguishing properties as facts
   (coverage, resolution, linkage), not adjectives.
5. Optional: one sentence on intended reuse.

Data descriptors keep this short (3–5 paragraphs). Do not preview the paper's
structure.

## Methods
- One subsection per source or processing stage, in the order data flow
  through the pipeline.
- Each subsection: source and access (provider, URL or DOI, version, access
  date), what was retrieved, transformation steps in order (T6), each choice
  with its reason in the same sentence (T7), edge cases (T8).
- Units, thresholds, time zones, calendar conventions (e.g. epidemiological
  weeks starting on Sunday) stated once, exactly.
- Software named with version when the brief gives it. Do not invent
  versions.

## Data Records
- Repository, DOI, licence, version (only as given).
- File inventory: names, formats, granularity, row/column counts if given.
- Field dictionary as a table or list (bullets allowed here, S6).
- Keys and joins between files.

## Technical Validation
- What was checked, against what reference, with what result in numbers.
- Known biases and coverage gaps with their extent (T9).
- No reassurance sentences ("These checks confirm the high quality of...").
  Let the numbers stand.

## Usage Notes
- Practical caveats a reuser needs: relative scales (e.g. Google Trends
  0–100 per request), reporting delays, revisions, missing years.
- How to combine files, with the key columns.
- Short, imperative or declarative, no salesmanship.

## Code Availability / Data Availability
Conventional boilerplate; keep it formulaic and exact.

> The code used to collect and process the data is available at [URL] under the [licence] licence. The version used in this article is archived at [DOI].

> The dataset is available at [repository] (doi:[DOI]) under a [licence] licence.

Only fill bracketed items from the brief; otherwise list them as missing
inputs.

## Results
- Paragraph opens with the finding (T1), then the number with uncertainty and
  figure pointer (T5).
- Comparisons within the sentence ("whereas", "compared with").
- Interpretation is deferred to Discussion except for one clause when needed
  for flow.

## Discussion
1. What the work establishes, restated in one or two sentences with new
   framing, not a copy of the abstract.
2. Relation to prior work, using only the user's citations.
3. Limitations with extent (T9), followed by what would remove them.
4. Implication for practice or future work, concrete.
5. Optional grounded close (T15).

## Limitations (stand-alone)
Each limitation: what it is, how large, which analyses it affects, what the
user did or recommends about it. No apologetic framing.

## Figure and table captions
Title as a declarative statement or noun phrase; then panels a, b, c in
order; then statistics (n, interval type, test). No interpretation beyond
what the figure shows.
