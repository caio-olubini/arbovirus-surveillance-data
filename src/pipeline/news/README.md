# News pipelines

Three **competing representations** of one frozen corpus of Agência Brasil
dengue coverage. Each braço reads the same text corpus and publishes its own
feature table at the same grain — epidemiological week × location — so the
article can compare which representation predicts dengue better.

They are parallel, not layered. Nothing here is a shared model; the shared part
is the corpus and the calendar, and that is deliberate: the comparison is the
result, so the ground under it has to be fixed. See
[`notes/00-protocolo-comparacao.md`](../../../notes/00-protocolo-comparacao.md).

| Stage | CLI | Grain | Status |
|---|---|---|---|
| Text corpus | `arboili transform news-text` | article × Sunday epi-week | **complete** |
| Braço 01 — lexicon + rules | `arboili transform news-lexicon` | EW × (BR + UF) | **complete** |
| Braço 02 — dense embeddings | `arboili transform news-embeddings` | EW × (BR + UF) | **complete** |
| Braço 03 — temporal topics | `arboili transform news-topics` | EW × (BR + UF) | **complete** |

Braços 04 and 05 (LLM extraction, LLM forecaster) are not here. They are
*corredores por fora*: they consume the same corpus but produce different kinds
of output, and their notes put them after the baseline and at least one
representation exist.

```bash
uv run arboili transform news-text
uv run arboili transform news-lexicon
uv sync --extra embeddings && uv run arboili transform news-embeddings
uv sync --extra topics && uv run arboili transform news-topics
```

---

## 1. The frozen corpus

**In.** `data/news/<query>/articles/*.html` + `manifest.jsonl` (written by
`arboili ebc`).
**Out.** `data/pipeline/news/EBC_dengue_text.parquet` (+ `.csv.gz`).

Every downstream braço reads this table; none of them re-parses HTML.

| Column | Notes |
|---|---|
| `article_id` | filename stem — the join key |
| `published_at` | from the manifest; naive local datetime |
| `ew` | Sunday that starts the epi week (`floor_to_sunday`) |
| `section`, `url` | from the manifest |
| `title` | from the **article page** |
| `listing_title` | from the **search listing**, entities unescaped |
| `text` | the extracted body |
| `era`, `extractor` | which generation and which rule fired |
| `char_count` | `len(text)` |
| `lang_guess` | `pt` or `other` — see §6 |

### Two template generations

The corpus spans a site redesign at ~2014, and the boundary is not cosmetic:

| Era | Years | Body container | `<h1>` holds |
|---|---|---|---|
| `b` | 2002–2014 (2,628) | `div.inside` | the **site** name |
| `c` | 2014–2026 (1,941) | `div.node-conteudo` | the real title |

Era B keeps the real title only in `<title>`, so trusting `<h1>` would have
labelled 2,628 articles "Agência Brasil". The era is detected per article and
recorded, together with the rule that fired; a silent fallback would produce a
corpus that looks fine and is subtly wrong, which is the failure this stage
exists to prevent.

`div.inside` matches more than one element per page, so the extractor takes the
**richest** match rather than the first. That decision produced this stage's two
real bugs, both of which left every title looking correct.

1. **The first match was a header.** `select_one` returned a 20-character
   `Agência Brasil | A+ | A-` bar for all 2,628 era-B articles.
2. **"Richest" was measured by total text.** With the header gone, the next
   candidate was the "Últimas notícias" rail — 1,086 characters of link text
   against a 677-character article. Scoring on total text picked the rail for
   **1,097 of the 2,628 era-B articles (42%)**, and the rail is long enough to
   pass every length check.

The scorer now keys on `(paragraph text, link-free text)`. Paragraph text
settles it outright, because an article body has `<p>` elements and the rail has
none; link-free text is the tiebreak for a body with no `<p>` at all, where the
rail's 1,126-of-1,279 link characters are what gives it away.

The second bug was invisible in the corpus's own summary statistics — the era-B
median barely moved (1,418 → 1,390) because 58% of the era was already correct.
It surfaced only by reading a fixed article and finding a news rail where the
body should be. The same defect also corrupted `lang_guess`, which samples the
first 1,500 characters: 81 era-B articles were labelled in the wrong language
because the sample was navigation text. Both directions occurred — a Portuguese
body with a rail became `other`, and a Spanish article's rail became `pt`.

### Validation

Run over the full corpus: 4,569 articles, 45 s.

| Era | min | median | p90 | max |
|---|---|---|---|---|
| b | 40 | 1,390 | 2,812 | 34,960 |
| c | 163 | 2,452 | 5,051 | 24,938 |

Era B's minimum is *not* an article — it is the three body-less pages described
below. Excluding those, the era-B floor is 128, a one-sentence 2002 wire note,
and era C's 163 is a 2016 note about a national radio address. Both are real
copy, not truncations, which is why `MIN_CHARS` is 100 and not, say, 500: the
corpus contains genuinely terse material from the 2002–2003 wire era.

`title_agreement` compares the page title with the listing title. Two
independent reads of the same headline; they diverge when the extractor latches
onto a nav heading. 99.1% agree, and the 0.9% that do not are `&quot;` /
`&#039;` escaping on the listing side — the page extractor is the better read.
Hence a floor of 95%, not equality.

### Body-less pages

Three era-B pages (two from 2008-04-02, one from 2008-11-20) were **saved
without their body**: the HTML jumps from the headline straight to the
"Últimas notícias" rail. Their extraction is the bare byline — 40 to 45
characters, and that is the era-B minimum in the table above.

They are kept. The article was published and names dengue, so `news_volume`
should count it; only the text is absent. They are reported by
`check_bodyless_pages` (by name, never failing) and excluded from
`check_min_length`, so a length regression and a truncated fetch stay
distinguishable. Under bug 2 above these pages extracted the rail and passed
every check — the bug was *masking* a collection defect.

This is also why the corpus is regenerated rather than patched: the fix moved
4,184 → 4,369 articles past the disease-term gate, because a rail does not
contain the word "dengue" and the articles it replaced did.

---

## 2. Braço 01 — PT-BR lexicon + rules

**In.** the frozen corpus.
**Out.** `data/pipeline/news/EBC_dengue_lexicon_EW.parquet` (+ `.csv.gz`).

Hypothesis, literature and counter-evidence: [`notes/01`](../../../notes/01-lexico-regras.md).

| Feature | Definition |
|---|---|
| `news_volume` | articles scoped to this location in this week |
| `news_severity` | Σ (tier weight × non-negated severity hits) |
| `news_cases` | largest case count stated in the week |
| `news_deaths` | largest death count stated in the week |
| `news_articles_with_cases` | how many articles stated a count at all |

`news_volume`, `news_severity` and `news_cases` are the three the note fixes;
`news_deaths` comes from a rule the note's own regex list names (`"X óbitos"`), and
`news_articles_with_cases` exists to answer the note's open question about
whether `news_cases` is worth keeping. It is not: see §5.

The lexicon is versioned at
[`data/news/reference/lexico_dengue.yaml`](../../../data/news/reference/lexico_dengue.yaml).
Changing a term or a weight invalidates the comparison with braços 02 and 03.

### Scoping

Every article counts for `BR`; it also counts for each federative unit it names.
An article can therefore contribute to several locations in the same week.

- **Full state names** match case-sensitively on the original text. That is
  load-bearing: accent-folding makes `Pará` and the preposition `para` the same
  string, which would scope nearly every article to Pará.
- **Two-letter codes** (`SP`, `RJ`) match only in uppercase *and* only when a
  locative cue precedes them (`em`, `no estado de`, `interior do`, or
  parentheses). Bare codes are unusable — `SE` is the reflexive pronoun and `PA`
  collides with `p.a.`.
- **Municipalities are not resolved.** An article that says only "Araçatuba"
  counts for `BR` and not for `SP`. This is a declared limitation: the IBGE name
  list is full of homographs with common Portuguese words, the target grain is
  the UF anyway, and a wrong state assignment is worse than a missing one.

### The three gates on counts

Raw number extraction from general news prose is dominated by numbers that are
not about dengue. The corpus alone contains `700 mil mortes` (covid),
`655 mil mortes` (malária), `38.892 mortes` (violência) and `24 mil mortes
prematuras` (poluição) — each inside an article that is genuinely about dengue.
A count is kept only if it is:

1. **not negated** — no negation cue in the preceding 40 characters;
2. **not qualified by another disease** — `11.881.430 casos de DRSAI` is not ours;
3. **in a sentence that names a dengue-family disease**.

Gate 3 is load-bearing and it costs recall: `No estado de São Paulo, foram
36.791 casos` is dropped when the sentence never says "dengue". That is the
deliberate direction — a count that is an order of magnitude wrong is worse for
the model than a count that is missing, and the missing ones are what braço 04's
structured extraction is for.

Two more rules that were not obvious:

- **`mil` does not always multiply.** The corpus writes `36.791 mil casos`,
  where the dots *are* the thousands separator and the trailing `mil` is a
  redundant reading of them. Multiplying gives 36.8 million cases in one state.
  The multiplier is skipped when the number already uses dotted-thousands
  grouping; `500 mil casos` carries no dots and does multiply.
- **`news_cases` is a maximum, not a sum.** A week's coverage repeats the same
  cumulative figure across several articles; summing would scale with how many
  times the press repeated one number rather than with the epidemic.

### Measured output

965 weeks × 28 locations = 5,152 rows, from 4,369 of the 4,569 articles.

| Location | articles | | `news_volume` | `news_severity` | `news_cases` | `news_deaths` |
|---|---|---|---|---|---|---|
| BR | 4,369 | median | 2 | 4 | 59,696 | 91 |
| RJ | 1,636 | p90 | 9 | 26 | 788,809 | 1,780 |
| SP | 863 | max | 88 | 164 | 6,629,595 | 500,000 |
| DF | 388 | non-null weeks | 965 | 965 | 511 | 189 |
| PR | 353 | | | | | |

The `news_cases` maximum is the real 2024 record (6,629,595 probable cases).
The `news_deaths` maximum is **not** a dengue figure — it is a global
neglected-tropical-diseases estimate in a sentence that happens to name dengue.
One residual error of that kind survives the three gates; it is reported here
rather than smoothed away.

RJ's lead over SP (1,636 vs 863 articles) is entirely an artifact of the early
corpus, and it inverts. In 2002–2004 RJ carries 371 mentions to SP's 110 — 2002
alone is 311 to 60. From 2015 on SP leads, 514 to 467. The per-UF series
therefore inherits a decade-scale shift in *where the newsroom was looking*, not
in where dengue was; it is the clearest instance of limitation 2 below, and a
reason to treat a per-UF news feature as relative to its own history rather than
comparable across units.

---

## 3. Braço 02 — dense BERTimbau embeddings

`uv sync --extra embeddings && uv run arboili transform news-embeddings`

The competing hypothesis to §2: a pre-trained encoder reads the whole article, so
it keeps the paraphrase, the hedge and the indirect mention that a lexicon drops,
and the mean of a week's vectors is a representation of "the informative week" that
a model can consume as a dense covariate.

### The encoder is frozen, and pinned by commit

`neuralmind/bert-base-portuguese-cased`
([Souza 2020](https://doi.org/10.1007/978-3-030-61377-8_28)), 768-wide, revision
`94d69c95f98f7d5b2a8700c420230ae10def0baa`. The revision is a commit sha and not a
branch, for the same reason the lexicon is versioned: a branch moves under the
artifact, and "which BERTimbau?" would stop having an answer.

No fine-tuning, on purpose. Fine-tuning changes what the braço *is*, so it is a
sub-experiment that has to be decided before the comparison rather than during it.

`torch` and `transformers` are an **optional extra**, not core dependencies —
together they are ~800 MB and nothing else in the repository imports them. The
encoder is injectable (`transform(..., encoder=...)`), which is what lets the whole
unit suite and the notebook run without the download.

### Pooling is the masked mean, not `[CLS]`

Averaging `last_hidden_state` over the real tokens, masked by `attention_mask`, then
L2-normalized. `[CLS]` is the next-sentence-prediction signal and the pooler head is
discarded by every sentence-embedding recipe; neither is a summary of the article.

"Masked" is load-bearing: averaging over `[PAD]` positions would make a vector depend
on what it was batched with. `tests/pipeline/news/test_embeddings_steps.py` pins that
down by encoding one sentence alone and again beside a shorter one.

### The article set is braço 01's, deliberately

Same language gate, same dengue-term gate, same `UfMatcher` — imported, not
re-implemented. Protocol 00 fixes the corpus as common ground: if one braço sees
4,369 articles and another sees 4,569, the comparison measures the filter instead of
the representation. `lexicon.steps.mentions_disease` was extracted out of braço 01's
`analyse()` so both braços run the *same function* rather than two copies of it.

### Two tables

| Table | Grain | Rows | Size |
|---|---|---|---|
| `EBC_dengue_embeddings_article.parquet` | one row per article | 4,369 | 12.6 MB |
| `EBC_dengue_embeddings_EW.parquet` | EW × (BR + UF) | 5,152 | 8.7 MB |

Both are written because pooling is lossy and re-encoding is the entire cost:
re-pooling, re-scoping or chunking from the article table takes seconds, while the
run that produced it took 574.6 s. Parquet only — a 768-float column does not
survive csv text form, and the stage refuses `--formats csv_gz` rather than writing
something lossy.

`emb_std` is the **norm** of the per-dimension standard deviation, not the vector: a
768-wide std column would double the table to say one number the norm already
carries. It is the population std, so a single-article week is exactly 0.

### Measured output

4,369 of the 4,569 articles (the 200 dropped are the same ones §2 drops), 5,152 rows
over 965 weeks × 28 locations, 574.6 s on CPU (M1, batch 16, no GPU). The week range
(2002-02-17 → 2026-09-13), the 874 weeks carrying at least one UF row, and the
per-UF article counts (RJ 1,636, SP 863, DF 388, PR 353, MG 346) are all **identical
to braço 01's** — which is the check that the common ground actually held.

| | |
|---|---|
| articles encoded | 4,369 / 4,569 |
| pooled rows | 5,152 = 965 weeks × 28 locations |
| vectors | 768-wide, L2-normalized |
| elapsed | 574.6 s (CPU) |
| **truncated at 512 tokens** | **1,704 / 4,369 (39.0%)**, longest 7,624 tokens |
| token percentiles | p50 438 · p75 637 · p90 895 · p99 1,965 |
| rows pooling one article | 3,079 / 5,152 (59.8%) |

### What this braço cannot claim

1. **39% of articles lose their tail.** The 512-token limit is BERT's, not a choice.
   `n_tokens` is carried per article precisely so this is visible instead of silent —
   a 34,960-character era-B piece and a 163-character era-C note both become one
   768-vector, and only that column says which of them was cut.
2. **`emb_std` is undefined for 59.8% of rows.** A row that pools one article has no
   dispersion, not low dispersion. The feature is live on the busy weeks and constant
   on the quiet ones — usually where a covariate is wanted. This is the strongest
   argument so far for pooling at a coarser grain.
3. **The content axis is weak.** In the exploratory reading in
   `notebooks/news_embeddings_pipeline.ipynb`, PC1 of the national weekly means
   explains 20.8% of its own variance and correlates +0.119 with weekly cases, while
   `n_articles` — braço 01's `news_volume` — reaches +0.347. That is the pattern
   [Tan 2024](https://arxiv.org/abs/2406.16964) predicts, and the reason protocol 00
   mandates a shuffled-text negative control. It is **not** the protocol-00 result.
4. **768 dimensions is a lot of covariate.** No reduction is applied; whether the
   forecaster takes the vector whole or a PCA of it (and the variance that keeps) is
   a modelling decision left open in `notes/02`.
5. Everything §6 declares about single-source, national-news-versus-UF-target and
   mention-based scoping applies here unchanged. The scoping is literally the same
   code.

---

## 4. Braço 03 — temporal topic modeling

`uv sync --extra topics && uv run arboili transform news-topics`

The third competing hypothesis, and the one aimed at a different question. Braço 01
says **how much** the press wrote; braço 02 says what a week's prose *looks like* as
a dense vector. Braço 03 says **what** the week was about: a week's coverage is not a
block, it mixes cases, vector, vaccine, policy and hospital collapse, and the
mixture is the covariate.

### The model is DMR, and the covariate is the period

`tomotopy`'s DMR (Dirichlet Multinomial Regression;
[Mimno & McCallum 2012](https://arxiv.org/abs/1206.3278)) with the epidemiological
period as the per-document covariate. DMR conditions topic *prevalence* on the
covariate — it is the mechanism STM
([Roberts 2019](https://doi.org/10.18637/jss.v091.i02)) extends, so it is the
Python-native stand-in for `notes/03`'s primary candidate rather than a substitute
for it. The three reasons it was chosen over STM and BERTopic, in order of weight,
are argued in `topics/spec.py`: **no R** (the project replaced its legacy R chain
with Python products and would otherwise carry the only R runtime in the repo);
**independence from braço 02** (BERTopic's standard pipeline needs sentence
embeddings, and reusing braço 02's frozen BERTimbau would make the two braços share
an encoder — "the same embedding sliced two ways" is not an independent
comparison); and **the corpus is unevenly dense across 24 years** (`notes/03`'s own
risk, and exactly the density imbalance BERTopic's HDBSCAN step is known to be
unstable under).

LDA (`family: lda`) is the baseline the note calls for. It is the same library and
the same training loop minus the metadata, so it is a run parameter and not a second
stage.

**The covariate grain is a month, not the weekly grain the tables are keyed by.**
DMR regresses prevalence on the covariate's levels: 965 weekly levels against ~4.5
articles each would be an over-parameterised fit, while ~290 monthly levels get ~15.
The published grain stays weekly — the covariate shapes the *fit*, not the output.

### k is selected by coherence, and the sweep is published

`notes/03` fixes the criterion: coherence, never perplexity
([Greene 2014](https://doi.org/10.1007/978-3-662-44848-9_29)), because likelihood
rises with k almost mechanically while coherence does not. `k_range` is swept, `c_v`
scores each candidate, and the argmax wins — ties going to the **smaller** k, so an
uninformative plateau resolves to the more parsimonious model.

There is no `topic_count` constant in `spec.py` on purpose: pinning one would make
the selection look like a schema change. Instead the whole sweep is written to
`EBC_dengue_topics_sweep` — the models that *lost*, with their coherence and their
`ll_per_word` — so the choice can be checked rather than trusted. `ll_per_word` is
reported and deliberately not used to choose, which is the part a reader should be
able to check: it is flat-to-rising across the range while coherence turns over.

### Tokenization is deliberately light

Accent folding (`news.common.strip_accents`), a `[a-z]+` regex, and a frozen PT-BR
stopword list. No lemmatizer, no POS tagger, no spaCy — `notes/03` proposed
`pt_core_news`, set aside because it would add a several-hundred-megabyte model as
the *only* consumer of a new NLP runtime in a repository whose other news braço is
pure regex. The honest cost is recall on rare inflections, which `min_df` prunes out
of the vocabulary anyway.

Folding first is what lets the stopword list be one flat tuple: `não`/`nao` and
`está`/`esta` collapse to one entry each. The list has two deliberate groups —
function words, and news boilerplate (`disse`, `afirmou`, `segundo`). The second is
content words by part of speech, but in a corpus of attributed news prose they
cluster into an "attribution" topic that says nothing about dengue. Domain
vocabulary is deliberately *not* in it: `caso`, `morte`, `vacina`, `aedes` are what
the topics are supposed to be made of.

### Three tables

| Table | Grain | Rows | Size |
|---|---|---|---|
| `EBC_dengue_topics_EW.parquet` | EW × (BR + UF) × topic | 77,280 | 0.2 MB |
| `EBC_dengue_topics_meta.parquet` | model × topic × term | 225 | 0.02 MB |
| `EBC_dengue_topics_sweep.parquet` | one row per candidate k | 5 | <0.01 MB |

The meta table is **not optional**: "topic 7 predicts dengue" is not a finding
anyone can check, so every topic ships with its defining terms. Parquet plus
`csv.gz` for all three, unlike braço 02 — these tables are long and narrow with no
dense vector column, so they do survive csv text form and the R consumer gets them
the way braço 01 writes its own.

Shares are pooled as the **unweighted mean over articles**, so each article speaks
once regardless of length, matching braço 02's pooling rule. A document whose tokens
were all stopwords is assigned the uniform row rather than dropped: it is still in
the article set protocol 00 fixes, so it must still count toward `n_articles`.

### Measured output

4,369 of the 4,569 articles — the same 200 dropped as §2 and §3 — over 965 weeks ×
28 locations. `k=15` selected, coherence 0.7510, 221.3 s on CPU (M1, single worker).

| candidate k | 5 | 10 | **15** | 20 | 25 |
|---|---|---|---|---|---|
| `c_v` coherence | 0.7141 | 0.7165 | **0.7510** | 0.7263 | 0.7016 |
| `ll_per_word` | −8.1185 | −8.1138 | **−8.1123** | −8.1069 | −8.0915 |

The turnover is real — coherence peaks and falls on both sides of 15 — and it is the
one place the two criteria visibly disagree: likelihood keeps climbing to k=25 while
coherence turns down after 15. That is the argument for the criterion, measured on
this corpus rather than quoted.

The 5,152 (ew, location) groups are **identical to braço 02's row count**, and the
965 weeks and 28 locations are identical to both earlier braços — the check that the
common ground actually held across all three.

| | |
|---|---|
| articles modelled | 4,369 / 4,569 |
| vocabulary | 17,131 terms (`min_df` 3) |
| pooled rows | 77,280 = 5,152 groups × 15 topics |
| **k selected** | **15** (coherence 0.7510) |
| shares summing to 1 | 5,152 groups, max deviation 2.4 × 10⁻⁷ |
| elapsed | 221.3 s (CPU, 1 worker) |

All fifteen integrity checks pass on the published tables
(`topics/integrity.py`, exercised in both directions in
`tests/pipeline/news/test_topics_integrity.py`).

### What the topics turned out to be

Readable, which is the point of publishing the meta table. Topic 2 is vector control
(*mosquito, aedes, aegypti, focos, agentes, água*), topic 3 is the arbovirus-family
topic (*zika, chikungunya, microcefalia, febre amarela*), topic 10 is vaccination
(*vacina, doses, butantan, vacinação*), topic 14 is clinical presentation (*sintomas,
febre, dor, tratamento*), topic 5 is research (*fiocruz, pesquisadores, instituto*),
topic 4 is federal policy (*governo, ministério, recursos, lei*).

### What this braço cannot claim

1. **A topic model cannot see a document twice.** DMR is fit once over the whole
   corpus, so the topics are shaped by all 24 years at once — including 2024, the
   record year. `notes/03` names this risk. The sweep table makes the selection
   visible, but it does not address it; a rolling-origin refit is the declared next
   step if it turns out to matter.
2. **180 of the 4,369 articles (4.1%) are English, and they survive the language
   gate.** They are Agência Brasil's English edition, and `lang_guess` calls every
   one of them `pt` — because `common.guess_language` only separates *Spanish* from
   *not-Spanish* and defaults to Portuguese, so English has no marker to trip.
   **Topic 1 is exactly this artifact**: *the, and, that, for, with, health, will,
   brazil, cases*. Braços 01 and 02 absorbed these articles silently — a lexicon
   count does not care about language, and an embedding puts an English article next
   to its Portuguese counterpart — so braço 03 is the first representation that
   *spends a whole topic* on them and makes them visible. It is **not** fixed here:
   protocol 00 fixes the article set as common ground, and re-gating it in one braço
   would make its corpus differ from the other two and break the comparison. It is
   an open item for protocol 00 and it belongs to all three braços at once.
3. **Topic stability across seeds has not been established.** One DMR fit at one
   seed produced the published topics. A single fit does not by itself establish
   that the topics are stable, and `notes/03`'s risk list says so. Re-running the
   sweep at several seeds and reporting the topic-to-topic agreement is the
   measurement that would settle it, and it has not been run.
4. **Topic 7 is a conversational register, not a subject.** *mais, gente, pessoas,
   fazer, temos, estamos* is interview quotation — a register the boilerplate list
   does not reach. It is the topic-model equivalent of braço 02's finding that PC1
   is weak: a real property of the corpus, reported rather than hidden.
5. Everything §6 declares about single-source, national-news-versus-UF-target and
   mention-based scoping applies here unchanged. The scoping is literally the same
   code, imported from `news.corpus`.

---

## 5. What building this measured

Facts about the corpus that constrain all three braços. Each was measured on the
full corpus, not sampled.

- **The corpus is not monolingual.** 171 of 4,569 articles (3.7%) are Spanish —
  Agência Brasil publishes a Spanish edition — and the split is **not random**:
  61 are from 2016 (Zika and the Olympics) and 24 from 2002. A PT-BR lexicon
  silently under-counts exactly those weeks, so `lang_guess` is carried in the
  corpus and braço 01 filters to `pt`.
- **`lang_guess` is a marker count, and it was measured.** 92.4% of the articles
  it flags `other` contain an unambiguous Spanish-only function word, so the
  class is overwhelmingly real. In the other direction, 4 of 4,398 `pt` rows
  (0.09%) carry such a marker — all four are Spanish articles whose filenames say
  so. The heuristic is sound for article bodies; it was badly wrong when it was
  reading navigation text (see §1), which is why the corpus and the guess are
  produced together rather than independently.
- **`lang_guess` does not detect English.** The detector separates *Spanish* from
  *not-Spanish* and defaults to `pt`, so the **180 English articles (4.1% of the
  kept corpus)** from Agência Brasil's English edition are all labelled `pt` and
  all pass the language gate. The Spanish bullet above is the measurement that was
  made; this is the one that was not, and it took braço 03 — the first
  representation that spends a whole topic on a language rather than averaging it
  away — to make it visible. It constrains all three braços and is an open item for
  protocol 00 (§4.2).
- **Only 24% of articles state a case count** (1,089/4,569), and 6% a death
  count (276/4,569). So `news_cases` is non-null in 511 of 965 weeks and
  `news_deaths` in 189. This is the empirical answer to the note's open question:
  for this corpus, `news_cases` and `news_deaths` are thin, expensive to trust,
  and probably belong to braço 04's structured extraction rather than to a regex.
  `news_volume` and `news_severity` are present every week and are what braço 01
  can defend.
- **Reported counts are cumulative-to-date, not weekly.** Most articles say
  "ao longo de 2024, 6,6 milhões de casos". The weekly maximum is therefore the
  scale of the largest figure the press stated that week, *not* the week's
  incidence. Using it as a weekly covariate without modelling that difference is
  a real error and an open item for protocol 00.
- **Coverage is sparse and clustered.** 4,569 articles over 973 weeks is 4.7 per
  week on average, but 89 in the busiest week and 1 in most weeks. In the
  SINAN ∩ Google Trends window (2020–2024) it is 588 articles over 170 weeks =
  3.5/week. Per UF it is sparser still: 874 of 965 weeks have at least one UF row.
- **8 weeks lose every article** to the language and disease-term filters, so
  they are absent from the series. Absent therefore means "no usable article",
  not "no article published" — a distinction the consumer has to make explicitly.
- **A handful of pages are digests.** Five `Serviço de C&T` pages bundle several
  unrelated stories; 60 pages exceed 8,000 characters. Their extraction is
  faithful to the page, but their text is not all about dengue.

---

## 6. Declared limitations

1. **Single source, state-owned, national.** One outlet, so `news_volume` is
   media attention in one newsroom, not "the media".
2. **News is national, the target is UF.** The spatial mismatch is declared, not
   solved; per-UF features are mention-based and biased toward UFs that get
   named. The bias is not stable over time — RJ's mention lead over SP inverts
   around 2015 (§2) — so a per-UF news feature is comparable to its own history
   before it is comparable across units.
3. **Negation is a character window, not syntax.** `não apenas um surto` loses a
   real `surto`.
4. **Uncertainty and hedging are not modelled.** `pode haver surto` counts the
   same as `há surto`. The annotation study in notes/01 is what will quantify
   this.
5. **`news_severity` weights are ordinal, not calibrated** — they order
   "surto" above "alerta" and stop there.
6. **`lang_guess` is a marker count, not language detection.** It is a column
   with a caveat in its name on purpose; §5 reports how well it actually does.
7. **Three pages carry no article text.** Two 2008-04-02 pages and one
   2008-11-20 page were fetched without their body. They count toward
   `news_volume` and contribute nothing else. Re-fetching them is possible but
   the corpus is frozen, so the gap is recorded instead.

---

## 7. Validation

```python
from src.pipeline.news.text.integrity import run_all            # corpus
from src.pipeline.news.lexicon.integrity import run_all         # braço 01 features
from src.pipeline.news.embeddings.integrity import run_all      # braço 02 tables
from src.pipeline.news.topics.integrity import run_all          # braço 03 tables
```

The corpus checks are structural plus two behavioural. `min_length` catches
bug 1 outright (a 20-character header), and `title_agreement` is the independent
read that a title-level regression would trip.

Neither catches bug 2, and that is worth stating plainly: the rail is 1,086
characters and never touches the title, so every check above passes while 42% of
an era is wrong. What caught it was reading one fixed article. The checks were
left as they are rather than bent to catch it — `era_counts` and
`extractor_counts` in the transform result are the cheap signal that the
extraction still lands on the right container, and `bodyless_pages` names the
three truncated fetches by name. A silent regression with a plausible length is
the failure mode this stage cannot fully mechanise against.

The feature checks assert `locations ⊆ {BR} ∪ 27 UFs`, that counts are null or
positive, and that **every week carries a BR row** — every article contributes
to BR by construction, so a week without one means the location spread dropped
something.

The braço 02 checks repeat those plus two of its own. `check_dim_consistent`
asserts both tables are 768-wide, which is the one way a different model could slip
into a run unnoticed. `check_finite` exists because masked pooling can divide by a
zero mask and emit NaN, and nothing downstream raises on that — it propagates into
the forecaster quietly. Every check is exercised in the failing direction in
`tests/pipeline/news/test_embeddings_integrity.py`, because a check that only ever
passes is indistinguishable from no check at all.

Braço 03 publishes three tables instead of one, so its checks are as much about
their agreement as about any single table. `check_shares_sum_to_one` is the one a
topic model can break without anything else looking wrong: a mixture is a
distribution, so a week's shares over the 15 topics must add to 1, and the tolerance
is stated (`SHARE_TOLERANCE`) rather than left to `np.allclose`'s default.
`check_topic_ids_consistent` requires every topic the shares reference to have a
definition in the meta table — the failure it guards against is a shares table whose
topic 12 has no readable terms, which would make the published finding
uninterpretable. `check_sweep_selects_one` is the check that keeps the evidence
honest: the sweep must mark exactly one winner *and* that winner must be the argmax,
so the tables and the justification cannot drift apart. `check_single_model` keeps
one run to one model, since mixing two fits would make the shares meaningless.

Fixtures live under `tests/fixtures/news/`: five saved pages, one per extraction
path — an era-C article, three era-B ones (the 2002 wire note, the 2011 page
whose rail out-scores its body, and the 2008 page with no body at all), and a
synthetic page matching none of the known containers, which forces the
paragraph heuristic. They are real HTML rather than hand-written markup on
purpose: the two bugs this stage had were both about which element the site
actually wraps an article in, and a fixture written from the extractor's own
assumptions would have reproduced the mistake.

The lexicon tests build their own one-row frames for the failure paths and use
the real corpus for the rest, so there is no second text corpus to keep in sync.
