"""Integrity checks for monthly related topics/queries fixtures."""

from __future__ import annotations

from pathlib import Path

from src.pipeline.google_trends.integrity import run_all_related
from src.pipeline.google_trends.related_steps import build_queries, build_topics

ROOT = Path(__file__).resolve().parents[3]
FU = ROOT / "data/epidemiological/br_federative_units.csv"
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "google_trends"


def test_related_topics_integrity_partial_ok() -> None:
    series = build_topics(FIXTURES / "GoogleTrends_related_topic_sample.csv").collect()
    checks = {c.name: c for c in run_all_related(series, FU, kind="topics")}
    assert checks["schema"].passed
    assert checks["unique_keys"].passed
    assert checks["month_format"].passed
    assert checks["value_domain"].passed
    assert checks["related_titles"].passed
    assert checks["states"].passed  # require_complete_ufs=False


def test_related_queries_integrity_partial_ok() -> None:
    series = build_queries(FIXTURES / "GoogleTrends_related_query_sample.csv").collect()
    checks = {c.name: c for c in run_all_related(series, FU, kind="queries")}
    assert checks["schema"].passed
    assert checks["unique_keys"].passed
    assert checks["month_format"].passed
    assert checks["states"].passed
