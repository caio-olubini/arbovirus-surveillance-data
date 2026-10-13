"""Schema of the temporal topic-model tables (braço 03) and its frozen choices.

Three tables. Two are published, one is the evidence for the first:

    EBC_dengue_topics_EW      one row per (ew, location, topic) — the weekly shares
    EBC_dengue_topics_meta    one row per (model, topic, term)  — what a topic *is*
    EBC_dengue_topics_sweep   one row per candidate k, with its coherence

The meta table is not optional: a topic index with no readable definition is
uninterpretable in a paper, and "topic 7 predicts dengue" is not a finding anyone
can check. The sweep table exists for the same reason — `notes/03` says the choice
of k is itself a result worth reporting, so the whole sweep is written rather than
only the winner.

## The model

**tomotopy's DMR** (Dirichlet Multinomial Regression; Mimno & McCallum 2012,
arXiv:1206.3278), with the epidemiological period as the document covariate.
DMR is the mechanism STM extends — Roberts 2019 conditions *both* prevalence and
content on covariates, DMR conditions prevalence — so it is the Python-native
stand-in for the note's primary candidate rather than a substitute for it.

It was chosen over the alternatives on 2026-10-13 for three reasons, in order of
weight:

1. **No R.** `notes/03` named STM (an R package) as primary. This machine has no
   R, and the project already replaced its legacy R chain with Python products
   (`transform sinan` supersedes `2_transform_sinan_data.R`). A new R runtime
   would be the only one in the repository and would have to be installed by
   anyone reproducing the paper.
2. **Independence from braço 02.** `notes/00` and `notes/README.md` fix 01/02/03
   as *competing* representations, not layers. BERTopic's standard pipeline needs
   sentence embeddings to cluster; reusing braço 02's frozen BERTimbau vectors
   would make the two braços share their encoder, and "the same embedding sliced
   two ways" is not an independent comparison. A second, independently pinned
   encoder would be needed to keep them apart.
3. **The corpus is unevenly dense across 24 years.** `notes/03`'s own "Riscos"
   section names the risk; BERTopic's HDBSCAN step is known to produce unstable
   clusters under exactly that density imbalance. DMR has no clustering step and
   no such failure mode.

LDA (`tomotopy.LDAModel`, no covariate) is the baseline the note calls for. It is
the same API minus the metadata, so it is a run parameter (`family`), not a second
stage.

## k is selected, not configured

`notes/03` fixes the criterion: coherence, never perplexity (Greene 2014, ECML
PKDD, LNCS 8724). `K_RANGE` is swept, `COHERENCE_METRIC` scores each candidate,
and the winner is the argmax — with `ll_per_word` *reported* in the sweep table and
deliberately not used to choose, which is the part a reader should be able to
check. There is no `TOPIC_COUNT` constant here on purpose: pinning one would make
the selection look like a schema change.

## Tokenization is deliberately light

Accent folding, a word regex, and a frozen PT-BR stopword list — no lemmatizer,
no POS tagger, no spaCy. `notes/03` proposed `pt_core_news` lemmatization; that
was set aside on 2026-10-13 because it adds a several-hundred-megabyte model
download as the *only* consumer of a new NLP runtime in a repository whose other
news braço is pure regex. Lemmatization would merge inflections, and the honest
cost of dropping it is recall on rare surface forms, which `MIN_DF` prunes anyway.
What is kept is recorded here, so the recipe is frozen and citable.
"""

from __future__ import annotations

# --- weekly share table -----------------------------------------------------

EW = "ew"
LOCATION = "location"
TOPIC_ID = "topic_id"
SHARE = "share"
N_ARTICLES = "n_articles"
MODEL_ID = "model_id"

# Keys first, then the payload, then the count and the provenance: a row printed
# without truncation shows what it identifies before what it measures.
OUTPUT_COLUMNS = (EW, LOCATION, TOPIC_ID, SHARE, N_ARTICLES, MODEL_ID)
GROUP_KEYS = (EW, LOCATION, TOPIC_ID)

OUTPUT_NAME = "EBC_dengue_topics_EW"

# `n_articles` is carried even though the grain is (ew, location, topic) and it
# therefore repeats across a week's topic rows. It is what makes a share
# interpretable — a share of 0.6 over one article and over forty are different
# claims — and it is the column `check_shares_sum_to_one` groups on.
SHARE_SCHEMA_ORDER = OUTPUT_COLUMNS

# --- topic definition table -------------------------------------------------

TERM = "term"
WEIGHT = "weight"

META_OUTPUT_COLUMNS = (MODEL_ID, TOPIC_ID, TERM, WEIGHT)
META_GROUP_KEYS = (MODEL_ID, TOPIC_ID, TERM)
META_OUTPUT_NAME = "EBC_dengue_topics_meta"

# --- k-selection sweep table ------------------------------------------------

COHERENCE = "coherence"
LL_PER_WORD = "ll_per_word"
SELECTED = "selected"

SWEEP_OUTPUT_COLUMNS = (MODEL_ID, TOPIC_ID, COHERENCE, LL_PER_WORD, SELECTED)
SWEEP_OUTPUT_NAME = "EBC_dengue_topics_sweep"

# In the sweep table `topic_id` carries the *candidate* k — the column name is
# reused rather than duplicated because the sweep is keyed by model, and every
# model_id already encodes its own k.

NATIONAL_LOCATION = "BR"

# --- the model --------------------------------------------------------------

MODEL_ID_PREFIX = "tomotopy"

# `dmr` takes the period covariate; `lda` is the baseline that ignores it. Both
# are the same library and the same training loop, so the comparison between them
# isolates the covariate rather than the implementation.
FAMILY_DMR = "dmr"
FAMILY_LDA = "lda"
MODEL_FAMILIES = (FAMILY_DMR, FAMILY_LDA)
DEFAULT_FAMILY = FAMILY_DMR

# The covariate is the period each article falls in, as a string, because that is
# what DMR's metadata argument takes. `month` is the default grain and not the epi
# week the tables are keyed by, and the reason is statistical rather than
# cosmetic: the corpus is 4,369 articles over 965 weeks, so a weekly covariate
# would give DMR ~965 levels to regress on against ~4.5 observations each, while a
# monthly one gives ~290 levels against ~15. The published grain stays weekly
# either way — the covariate shapes the *fit*, not the output.
GRAIN_MONTH = "month"
GRAIN_YEAR = "year"
GRAIN_WEEK = "week"
COVARIATE_GRAINS = (GRAIN_MONTH, GRAIN_YEAR, GRAIN_WEEK)
COVARIATE_GRAIN = GRAIN_MONTH

# Candidates for the coherence sweep. `notes/03` expects k ≈ 10–25 for a corpus of
# this size; the range brackets that and stays small enough to run in one sitting.
K_RANGE: tuple[int, ...] = (5, 10, 15, 20, 25)

# c_v rather than u_mass: u_mass is known to favour very small k and to be
# unstable on short documents, which is what 2002–2003 wire copy is.
COHERENCE_METRIC = "c_v"
COHERENCE_TOP_N = 10

# Seed and single worker, together. tomotopy warns that a fixed seed does not
# guarantee a fixed result when `workers != 1`, because the Gibbs sampler's
# scheduling becomes nondeterministic — so reproducibility here needs both, the
# same way braço 02 needed a commit sha rather than a branch name.
DEFAULT_SEED = 42
DEFAULT_ITERATIONS = 1000

# A term must appear in at least this many documents to enter the vocabulary.
# Prunes the long tail of names, typos and one-off inflections that a topic model
# would otherwise spend a topic on. Chosen against a 4,369-document corpus; it is
# a vocabulary cut, not a document filter, so it cannot change the article set
# that protocol 00 fixes.
MIN_DF = 3

# Terms published per topic in the meta table.
TOP_TERMS = 15

# --- tokenization -----------------------------------------------------------

# Accent folding first (`news.common.strip_accents`), then this regex. Only
# letters survive, so numerals are dropped without a second rule — and dropping
# them is right here: the corpus writes case counts as `36.791`, and a topic model
# has nothing to gain from a token that is one week's number.
TOKEN_PATTERN = r"[a-z]+"

# Tokens shorter than this are dropped, which covers the one- and two-letter
# function words (`a`, `o`, `de`, `em`, `no`, `se`) without listing them; the
# stopword tuple below is the three-character-and-up remainder.
MIN_TOKEN_LEN = 3

# PT-BR function words, stored **accent-folded and lowercase** to match the tokens
# `tokenize` produces — `nao`, not `não`. Two groups, both deliberate:
#
#   * function words — articles, prepositions, pronouns, conjunctions, auxiliaries
#     and the commonest adverbs. These carry no topical content in any corpus.
#   * news boilerplate — the reporting verbs Agência Brasil uses to attribute
#     everything ("disse", "afirmou", "segundo"). They are content words by
#     part of speech, but in a corpus of attributed news prose they cluster into
#     an "attribution" topic that says nothing about dengue.
#
# Domain vocabulary is deliberately *not* here: `caso`, `morte`, `vacina`,
# `aedes` are exactly what the topics are supposed to be made of.
STOPWORDS_PT: tuple[str, ...] = (
    # function words
    "que", "com", "sem", "sob", "por", "para", "pelo", "pela", "pelos", "pelas",
    "dos", "das", "nos", "nas", "aos", "num", "numa", "uma", "umas", "uns",
    "seu", "sua", "seus", "suas", "dele", "dela", "deles", "delas",
    "ele", "ela", "eles", "elas", "isso", "isto", "esse", "essa", "este", "esta",
    "estes", "estas", "esses", "essas", "aquele", "aquela", "aquilo",
    "sao", "foi", "foram", "ser", "sera", "serao", "eram", "seja", "sendo", "sido",
    # `esta` is already listed above as the demonstrative; the fold makes it the
    # same token as the verb form, so it appears once.
    "estao", "estava", "estavam", "estiver", "esteve",
    "tem", "tinha", "ter", "teve", "havia", "haver",
    "pode", "podem", "podia", "deve", "devem", "vai", "vao", "faz", "fez", "fazem",
    "nao", "sim", "mas", "porem", "entretanto", "contudo", "todavia",
    "tambem", "ainda", "apenas", "muito", "muita", "muitos", "muitas",
    "pouco", "pouca", "poucos", "poucas", "todo", "toda", "todos", "todas",
    "outro", "outra", "outros", "outras", "mesmo", "mesma", "mesmos", "mesmas",
    "tal", "tais", "qual", "quais", "quando", "onde", "como", "porque", "pois",
    "assim", "entao", "depois", "antes", "durante", "sobre", "entre", "contra",
    "desde", "ate", "apos", "cada", "qualquer", "algum", "alguma", "alguns",
    "algumas", "nenhum", "nenhuma", "ja", "la", "aqui", "ali", "agora",
    # news boilerplate
    "disse", "diz", "afirmou", "declarou", "segundo", "informou", "explicou",
    "destacou", "lembrou", "ressaltou", "conforme",
)

# --- outputs ----------------------------------------------------------------

FORMAT_PARQUET = "parquet"
FORMAT_CSV_GZ = "csv_gz"
# Both tables are long and narrow (no dense vector column), so unlike braço 02
# they do survive csv text form and the csv.gz is written for R consumers, as
# braço 01 does.
DEFAULT_FORMATS = (FORMAT_PARQUET, FORMAT_CSV_GZ)

# The optional-dependency group in pyproject.toml. Named so the error message can
# say exactly what to install.
REQUIRED_EXTRA = "topics"
