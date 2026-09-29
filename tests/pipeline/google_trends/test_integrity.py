"""Google Trends integrity checks on the committed sample."""

from __future__ import annotations

from pathlib import Path

from src.pipeline.google_trends.integrity import run_all
from src.pipeline.google_trends.steps import build

ROOT = Path(__file__).resolve().parents[3]
FU = ROOT / "data/epidemiological/br_federative_units.csv"
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "google_trends"


def test_integrity_on_sample_skips_full_state_coverage() -> None:
    """Sample has AC/SP/BR only — schema/Sunday/value checks must still pass."""
    series = build(FIXTURES / "GoogleTrends_search_sample.csv", keep_br=True).collect()
    checks = {c.name: c for c in run_all(series, FU, keep_br=True)}
    assert checks["schema"].passed
    assert checks["unique_keys"].passed
    assert checks["weeks_start_on_sunday"].passed
    assert checks["value_domain"].passed
    # Full 27-UF membership is for the real extract, not the tiny fixture.
    assert not checks["states"].passed
