"""The contract `cli.main` assumes of every transform result.

`main()` ends with `return 0 if result.failed == 0 else 1`, for every stage
alike — it does not special-case any of them. So a result class that does not
carry `failed` crashes the process *after* the stage has written its outputs,
turning a successful multi-minute run into a traceback and a non-zero exit.

That is not hypothetical: it is what braço 02 did the first time it ran for real,
after encoding 4,369 articles. `SinanTransformResult` says so in its docstring
("notably `failed`, which the CLI sums into its exit code"); the new stage simply
did not follow it. This test is cheap and would have caught it.
"""

from __future__ import annotations

from dataclasses import MISSING, fields

import pytest

from src.pipeline.climate.transform import ClimateTransformResult
from src.pipeline.google_trends.transform import GTrendsTransformResult
from src.pipeline.news.embeddings.transform import NewsEmbeddingsTransformResult
from src.pipeline.news.lexicon.transform import NewsLexiconTransformResult
from src.pipeline.news.text.transform import NewsTextTransformResult
from src.pipeline.news.topics.transform import NewsTopicsTransformResult
from src.pipeline.sinan.transform import SinanTransformResult

RESULTS = [
    SinanTransformResult,
    ClimateTransformResult,
    GTrendsTransformResult,
    NewsTextTransformResult,
    NewsLexiconTransformResult,
    NewsEmbeddingsTransformResult,
    NewsTopicsTransformResult,
]


def _blank(cls):
    """An instance with every field at its default, required ones emptied.

    `SinanTransformResult` requires `disease`, so the classes cannot all be
    called with no arguments — but the fields under test all have defaults.
    """
    return cls(**{
        f.name: ""
        for f in fields(cls)
        if f.default is MISSING and f.default_factory is MISSING
    })


@pytest.mark.parametrize("cls", RESULTS, ids=lambda cls: cls.__name__)
def test_every_transform_result_reports_a_failure_count(cls) -> None:
    assert "failed" in {f.name for f in fields(cls)}, (
        "`cli.main` reads `result.failed` for the exit code on every stage"
    )
    value = _blank(cls).failed
    assert isinstance(value, int) and not isinstance(value, bool)
    assert value == 0, f"a blank {cls.__name__} claims {value} failures"


@pytest.mark.parametrize("cls", RESULTS, ids=lambda cls: cls.__name__)
def test_every_transform_result_stringifies_when_blank(cls) -> None:
    """`main` prints the result unconditionally, so `__str__` must not raise.

    A hand-written `__str__` reaching into a field the runner forgot to set is a
    second way to fail after the work is already done.
    """
    assert cls.__name__ in str(_blank(cls))
