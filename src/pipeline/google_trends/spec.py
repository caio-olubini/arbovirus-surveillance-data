"""Google Trends transform schemas: weekly search + monthly related."""

from __future__ import annotations

# --- weekly search index ----------------------------------------------------

EW = "ew"
STATE_ABBREV = "state_abbrev"
TOPIC = "topic"
VALUE = "value"

OUTPUT_COLUMNS = (EW, STATE_ABBREV, TOPIC, VALUE)
GROUP_KEYS = (EW, STATE_ABBREV, TOPIC)

OUTPUT_NAME = "GoogleTrends_search_EW"

# National aggregate rows use this location code in the extractor output.
NATIONAL_LOCATION = "BR"

# --- monthly related topics / queries ---------------------------------------

MONTH = "month"
DISEASE = "disease"
RELATED_TITLE = "related_title"
TOPIC_ID = "topic_id"
KEY_SYMPTOM = "key_symptom"

# --- provenance -------------------------------------------------------------
# The related tables concatenate two sources that used different clients, so
# every row records which one produced it. On an overlapping group key the
# earlier entry in SOURCE_PRECEDENCE wins: the frozen seed is the published
# reference (Borges et al., Zenodo 10.5281/zenodo.17102575) and our own extract
# only extends the months the seed does not reach. See the seed's README and
# src/pipeline/google_trends/README.md.
SOURCE = "source"
SOURCE_SEED = "zenodo"        # frozen seed, produced with the R gtrendsAPI client
SOURCE_EXTRACT = "pytrends"   # this repo's own extractor
SOURCE_PRECEDENCE = (SOURCE_SEED, SOURCE_EXTRACT)

TOPIC_OUTPUT_COLUMNS = (
    MONTH,
    STATE_ABBREV,
    DISEASE,
    RELATED_TITLE,
    TOPIC_ID,
    VALUE,
    KEY_SYMPTOM,
    SOURCE,
)
TOPIC_GROUP_KEYS = (MONTH, STATE_ABBREV, DISEASE, RELATED_TITLE, TOPIC_ID)

QUERY_OUTPUT_COLUMNS = (
    MONTH,
    STATE_ABBREV,
    DISEASE,
    RELATED_TITLE,
    VALUE,
    SOURCE,
)
QUERY_GROUP_KEYS = (MONTH, STATE_ABBREV, DISEASE, RELATED_TITLE)

TOPIC_OUTPUT_NAME = "GoogleTrends_related_topic_monthly"
QUERY_OUTPUT_NAME = "GoogleTrends_related_query_monthly"

# YYYY-MM from the related extractor.
MONTH_PATTERN = r"^\d{4}-\d{2}$"
