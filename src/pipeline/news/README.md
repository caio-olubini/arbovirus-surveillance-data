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
| Braço 02 — dense embeddings | `arboili transform news-embeddings` | EW × (BR + UF) | stub |
| Braço 03 — topic modeling | `arboili transform news-topics` | EW × (BR + UF) | stub |

Braços 04 and 05 (LLM extraction, LLM forecaster) are not here. They are
*corredores por fora*: they consume the same corpus but produce different kinds
of output, and their notes put them after the baseline and at least one
representation exist.

```bash
uv run arboili transform news-text
uv run arboili transform news-lexicon
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
| `lang_guess` | `pt` or `other` — see §5 |

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
whether `news_cases` is worth keeping. It is not: see §4.

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

## 3. Braços 02 and 03 — stubs

`embeddings/` and `topics/` carry the schema each braço will publish and refuse
to run. What is missing is a **research decision**, not code: which encoder for
02, and how many topics for 03 (selected on held-out likelihood or coherence,
which is itself a result worth reporting). Neither `torch`, `transformers`,
`bertopic` nor `stm` is installed or pinned today, so writing the stage would
have meant inventing a model choice that the notes leave open.

Both schemas are written down now so the three representations stay swappable in
the same model.

---

## 4. What building this measured

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

## 5. Declared limitations

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
   with a caveat in its name on purpose; §4 reports how well it actually does.
7. **Three pages carry no article text.** Two 2008-04-02 pages and one
   2008-11-20 page were fetched without their body. They count toward
   `news_volume` and contribute nothing else. Re-fetching them is possible but
   the corpus is frozen, so the gap is recorded instead.

---

## 6. Validation

```python
from src.pipeline.news.text.integrity import run_all            # corpus
from src.pipeline.news.lexicon.integrity import run_all         # features
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
