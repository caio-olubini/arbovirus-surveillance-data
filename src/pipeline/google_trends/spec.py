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

TOPIC_OUTPUT_COLUMNS = (
    MONTH,
    STATE_ABBREV,
    DISEASE,
    RELATED_TITLE,
    TOPIC_ID,
    VALUE,
    KEY_SYMPTOM,
)
TOPIC_GROUP_KEYS = (MONTH, STATE_ABBREV, DISEASE, RELATED_TITLE, TOPIC_ID)

QUERY_OUTPUT_COLUMNS = (
    MONTH,
    STATE_ABBREV,
    DISEASE,
    RELATED_TITLE,
    VALUE,
)
QUERY_GROUP_KEYS = (MONTH, STATE_ABBREV, DISEASE, RELATED_TITLE)

TOPIC_OUTPUT_NAME = "GoogleTrends_related_topic_monthly"
QUERY_OUTPUT_NAME = "GoogleTrends_related_query_monthly"

# YYYY-MM from the related extractor.
MONTH_PATTERN = r"^\d{4}-\d{2}$"
