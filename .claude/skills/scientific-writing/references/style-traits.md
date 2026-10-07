# Style traits

Sixteen rhythm and voice traits for the target voice: technology and
computational articles in *Nature* and *Scientific Data*, readable by someone
from an adjacent field without losing technical precision. Read this before
the first draft of every session.

Each trait is a rule, then a verbatim excerpt from an open-access (CC BY)
*Scientific Data* article that demonstrates it. The excerpts are quoted
character-for-character; superscript citation markers appear as bare digits
(`per year8,9`), as they do in the plain-text source, and are not part of the
rhythm being shown. Sources are listed at the end.

A draft that reads well will show most of these at once. When a passage feels
flat, find which trait is missing before rewriting the words.

---

## T1. Content-first openings

The first sentence of a paragraph carries the point. No warm-up, no
announcement of what the paragraph will cover, no restatement of the heading.

> Version 1.2 of the OpenDengue dataset includes information on over 56
> million dengue cases distributed over 102 countries for the time period
> 1924–2023.

Clarke et al. 2024, Data summary.

## T2. Plain statement before jargon

Open with the object of the work and why it matters in ordinary words. Let
technical vocabulary arrive in the second sentence or later, once the reader
knows what is at stake.

> RNA viruses are a pervasive and serious threat to human health. Here, we
> provide an updated catalogue of all 239 human-infective RNA virus species
> recognised by the end of 2024.

Zhang et al. 2026, Abstract.

## T3. Concrete anchors

Where a concept appears, put something specific beside it: a number, a place, a
date, a named system. A vague quantity earns its place only when the next
clause pins it down.

> Dengue virus (DENV), transmitted by Aedes spp. mosquitoes, accounts for an
> increasingly large proportion of all vector-borne disease, with an estimated
> 400 million infections per year8,9.

Nakase et al. 2023, Background & Summary.

## T4. Verbs do the work

The actor is the subject and the action is the verb. Undo nominalisations:
"we corrected", not "a correction was applied".

> We corrected the cases where the same person was recorded on multiple rows.
> For example, if a participant recorded meeting their mother in the morning
> and then again after returning from school, these cases were merged into a
> single record (Fig. 2).

Chae et al. 2026, Logical errors.

## T5. Numbers carry uncertainty and a pointer

A reported value travels with its uncertainty or denominator and a pointer to
where it is shown. A number alone is a claim; a number with its interval and
its table is evidence.

> Validation was conducted against station observations for a single extended
> summer period spanning May–September 2010 (Table 3). For our reconstructed
> grid, air temperature RMSE was 1.70 °C with a mean bias of + 0.17 °C and a
> correlation of r = 0.97, based on nearest-neighbor station matching within
> 800 m across 2,029 stations and 6.5 million matched station-hours.

Rahai et al. 2026, Technical Validation.

## T6. Pipeline order

Methods follow the data's flow through processing, step by step, not the order
of the argument. A reader should be able to replay the pipeline from the
prose.

> The construction of the harmonized wild bird host dataset followed a
> five-step pipeline (Fig. 1). First, we retrieved influenza A virus isolates
> of animal origin from the GISAID EpiFluTM database (Step 1). Host
> information was then extracted from the isolate names and standardized to a
> consistent format (Step 2).

Du et al. 2025, Methods.

## T7. Choice with its reason

A methodological decision and its justification live in the same sentence. The
reader should never have to ask why a tool, threshold or dataset was chosen.

> We chose spaCy for its fast CPU inference and lightweight model
> architecture, which is ideal for deploying efficient NER systems at scale.

Kriesch et al. 2025, Stage 3: Named entity recognition.

## T8. Edge cases named

Irregularities, missing records, manual interventions and data quirks are
stated plainly, together with the fix. Nothing hides behind "data cleaning".

> Similarly, location and occupation data were standardized. For example, for
> a 9-year-old participant who is an elementary school student, an
> education-related contact occurring at “workplace”, we corrected the contact
> place to “educational facility”.

Chae et al. 2026, Logical errors.

## T9. Limits with extent

A limitation is given its size and the analyses it affects. "This may
introduce bias" is not a limitation statement; a scope is.

> Europe and North America are disproportionately represented due to
> well-funded invasive species monitoring programs, while large parts of
> Africa, Asia, and South America are likely under-sampled. This bias can
> severely distort model predictions if not properly accounted for.

Abdelkrim et al. 2026, Critical Consideration on Sampling Bias.

## T10. Specific nouns over category nouns

Name the thing. "Notification date", not "temporal information"; the exact
format and filename convention, not "files with metadata".

> These data are organized in comma-separated values (.csv) files, with each
> file corresponding to a monitoring year, as indicated by the “yyyy”
> designation at the end of the filename.

Branda et al. 2024, Surveillance.

## T11. Varied length

Sentence lengths differ visibly. A short declarative sentence after two long
ones is not a defect; it is the rhythm. Paragraph lengths differ too.

> A total of 2,415 participants completed the consent form and the preliminary
> demographic survey. Of these, 428 participants were excluded, resulting in
> the final dataset of 1,987 participants (52.1% female, average age = 42.01 ±
> 19.77 years, age range = 0–79, see Supplementary Material). Foreigners were
> not included in the study.

Chae et al. 2026, Participants.

## T12. Logic in sentence order

Consecutive sentences whose order does the connecting work need no
connectives. Write the sequence so that "Furthermore" and "Moreover" become
unnecessary.

> In total, 1,987 participants contributed 133,776 recorded close social
> contacts over two survey weeks. The first survey round contained 69,150
> contacts and the second round 64,626 contacts, corresponding to average
> numbers of 34.8 (standard deviation 24.55) and 32.5 (standard deviation
> 20.15) contacts per participant per week, respectively. The maximum number
> of contacts reported by a single participant over both weeks was 329, and
> the minimum was 2.

Chae et al. 2026, Data Overview.

## T13. No wrap-up endings

A paragraph stops on content: a fact, a number, a consequence. It does not
summarize itself with "This shows that...", "Overall," or "Taken together,".

> In 2023, the number of isolates reached a record high of 1,826, the highest
> value across the entire observation period.

Du et al. 2025, Overview of the dataset. Final sentence of the paragraph.

## T14. No over-explaining

Well-known tools, formats and concepts are named, not glossed. The reader is
from an adjacent field, not from outside science. Keep conventional field
phrasing; novelty in wording is not a goal.

> We collect data from the CommonCrawl News dataset and clean the text data.
> We then use a named-entity recognition model for geocoding. Finally, we
> transform the news articles into text embeddings using SBERT, enabling
> semantic searches within the news data corpus.

Kriesch et al. 2025, Abstract.

## T15. Grounded close

Close a section on something concrete: a use, a number, an availability
statement. Not a promise, not a flourish.

> These tract-level hourly heat-stress datasets enable direct linkage with
> public health data.

Rahai et al. 2026, Abstract. Final sentence.

## T16. Comparisons inside the sentence

Put a contrast in one sentence, with "whereas", "compared with", "while" or
"unlike". Splitting it across two sentences makes the reader hold the first
while reading the second.

> At the highest spatial detail, some global heat-exposure products provide
> daily fields at ~0.05° resolution, whereas others offer hourly estimates at
> coarser spatial scales (typically ~0.1°–0.25°) derived from reanalysis
> inputs29,30.

Rahai et al. 2026, Background & Summary.

---

## Sources

All excerpts are from *Scientific Data* articles published under a CC BY
licence, which permits reuse with attribution. Section names follow each
article's own headings.

- Abdelkrim et al. (2026). The global compendium of *Aedes japonicus*: an
  underappreciated arbovirus vector of growing concerns. *Scientific Data*.
  doi:10.1038/s41597-026-07481-z
- Branda et al. (2024). Dengue virus transmission in Italy: historical trends
  up to 2023 and a data repository into the future. *Scientific Data*.
  doi:10.1038/s41597-024-04162-7
- Chae et al. (2026). A nationwide social contact survey dataset for public
  health and social sciences research in South Korea. *Scientific Data*.
  doi:10.1038/s41597-026-06896-y
- Clarke et al. (2024). A global dataset of publicly available dengue case
  count data. *Scientific Data*. doi:10.1038/s41597-024-03120-7
- Du et al. (2025). A taxonomically harmonized global dataset of wild bird
  hosts for avian influenza virus surveillance. *Scientific Data*.
  doi:10.1038/s41597-025-06451-1
- Kriesch et al. (2025). A geolocated dataset of German news articles.
  *Scientific Data*. doi:10.1038/s41597-025-05422-w
- Nakase et al. (2023). Global transmission suitability maps for dengue virus
  transmitted by *Aedes aegypti* from 1981 to 2019. *Scientific Data*.
  doi:10.1038/s41597-023-02170-7
- Rahai et al. (2026). Heat stress metrics for US census tracts 1998–2020.
  *Scientific Data*. doi:10.1038/s41597-026-06909-w
- Zhang et al. (2026). A complete catalogue of human-infective RNA viruses.
  *Scientific Data*. doi:10.1038/s41597-026-07281-5
