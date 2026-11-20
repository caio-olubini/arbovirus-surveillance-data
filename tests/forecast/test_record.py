"""O registro que viaja com uma tabela de resultado.

Estes testes são sobre um arquivo que existe para ser lido *depois*, que é o único
tipo de teste que consegue verificá-lo: nada na execução em si depende de o
registro estar certo.
"""

from __future__ import annotations

import datetime as dt
import json

import polars as pl

from src.forecast.__main__ import main
from src.forecast.evaluate import evaluate
from src.forecast.record import SCHEMA, setup_record, write_record
from src.forecast.spec import CASES, EW, GEOGRAPHY
from src.pipeline.sinan.spec import CASE_COUNT, EW_SYMPTOM_ONSET, FINAL_CLASSIFICATION

SUSPECTED = 1


def rising(n: int) -> list[float]:
    return [float(i) for i in range(1, n + 1)]


def a_run(panel: pl.DataFrame, **kwargs):
    """Uma execução de persistência, para as asserções serem sobre o registro."""
    defaults = {"baselines": ("persistence",), "min_train": 104, "horizon": 1}
    return evaluate(panel, **{**defaults, **kwargs})


# --- o que entra ------------------------------------------------------------


def test_the_record_names_the_panel_it_read(panel_from_values):
    panel = panel_from_values(rising(120))
    record = setup_record(panel, a_run(panel), "/tmp/cases.parquet")
    assert record["schema"] == SCHEMA
    assert record["target"]["source"] == "/tmp/cases.parquet"
    assert record["target"]["geography"] == GEOGRAPHY
    assert record["target"]["weeks"] == 120
    assert record["target"]["first_week"] == panel[EW][0].isoformat()
    assert record["target"]["last_week"] == panel[EW][-1].isoformat()
    assert record["target"]["total_cases"] == int(panel[CASES].sum())


def test_the_record_names_every_flag_that_moves_the_number(panel_from_values):
    panel = panel_from_values(rising(120))
    run = evaluate(panel, baselines=("persistence",), min_train=104, horizon=1, step=2)
    setup = setup_record(panel, run, "cases.parquet")["evaluation"]
    assert setup["horizon"] == 1
    assert setup["min_train"] == 104
    assert setup["step"] == 2
    assert setup["baselines"] == ["persistence"]


def test_the_same_flags_on_a_different_panel_are_a_different_record(panel_from_values):
    """`min_train` é uma contagem de semanas, então não diz nada sem a janela."""
    short = panel_from_values(rising(120))
    long = panel_from_values(rising(140))
    run = a_run(short)
    assert (
        setup_record(short, run, "c.parquet")["target"]
        != setup_record(long, run, "c.parquet")["target"]
    )


def test_origins_counts_weeks_scored_not_rows_written(panel_from_values):
    panel = panel_from_values(rising(120))
    one = setup_record(panel, a_run(panel), "c.parquet")["evaluation"]
    both = setup_record(
        panel, a_run(panel, baselines=("persistence", "seasonal_naive")), "c.parquet"
    )["evaluation"]
    assert one["origins"] == both["origins"]
    assert both["scored"] == 2 * one["scored"]


# --- o arquivo --------------------------------------------------------------


def test_the_record_round_trips_through_json(tmp_path, panel_from_values):
    panel = panel_from_values(rising(120))
    path = write_record(setup_record(panel, a_run(panel), "c.parquet"), tmp_path / "r.json")
    assert json.loads(path.read_text(encoding="utf-8"))["target"]["weeks"] == 120


def test_an_unknown_command_is_left_out_rather_than_faked(tmp_path, panel_from_values):
    panel = panel_from_values(rising(120))
    record = setup_record(panel, a_run(panel), "c.parquet")
    assert "command" not in json.loads(
        write_record(record, tmp_path / "r.json").read_text(encoding="utf-8")
    )


def test_the_command_is_quoted_so_it_can_be_pasted_back(tmp_path, panel_from_values):
    panel = panel_from_values(rising(120))
    path = write_record(
        setup_record(panel, a_run(panel), "c.parquet"),
        tmp_path / "r.json",
        command="python -m src.forecast --cases 'a b/c.parquet'",
    )
    assert json.loads(path.read_text(encoding="utf-8"))["command"].endswith("'a b/c.parquet'")


def test_the_same_setup_writes_the_same_bytes(tmp_path, panel_from_values):
    """Um registro que difere significa que uma flag diferiu — nada dependente do tempo."""
    panel = panel_from_values(rising(120))
    record = setup_record(panel, a_run(panel), "c.parquet")
    first = write_record(record, tmp_path / "a.json").read_bytes()
    second = write_record(record, tmp_path / "b.json").read_bytes()
    assert first == second


# --- e a linha de comando realmente o escreve -------------------------------


def test_the_cli_writes_the_record_beside_the_results(tmp_path):
    """Ponta a ponta: o ponto do arquivo é que a execução que carrega flags deixe um."""
    start = dt.date(2020, 1, 5)
    weeks = [start + dt.timedelta(weeks=i) for i in range(120)]
    cases = pl.DataFrame(
        {
            EW_SYMPTOM_ONSET: weeks,
            CASE_COUNT: [10] * len(weeks),
            FINAL_CLASSIFICATION: [SUSPECTED] * len(weeks),
        }
    )
    cases_path = tmp_path / "SINAN_dengue_cases.parquet"
    cases.write_parquet(cases_path)
    out = tmp_path / "out"

    assert main(["--cases", str(cases_path), "--out", str(out), "--min-train", "104"]) == 0

    record = json.loads((out / "dengue_br_h1_run.json").read_text(encoding="utf-8"))
    assert record["evaluation"]["min_train"] == 104
    assert record["target"]["weeks"] == 120
    assert "--min-train 104" in record["command"]
    assert (out / "dengue_br_h1_predictions.parquet").exists()
    assert (out / "dengue_br_h1_metrics.parquet").exists()


def test_the_scoring_window_is_recorded_and_changes_what_is_graded(tmp_path):
    """Duas execuções que só diferem em `--score-from` pontuam semanas diferentes.

    O registro é o único lugar onde essa diferença sobrevive: as duas tabelas de
    métricas se parecem, e sem `score_from` no JSON o número no slide não poderia
    ser rastreado até a janela sobre a qual foi calculado.
    """
    start = dt.date(2018, 1, 7)  # um domingo
    weeks = [start + dt.timedelta(weeks=i) for i in range(320)]
    cases = pl.DataFrame(
        {
            EW_SYMPTOM_ONSET: weeks,
            CASE_COUNT: [10] * len(weeks),
            FINAL_CLASSIFICATION: [SUSPECTED] * len(weeks),
        }
    )
    cases_path = tmp_path / "SINAN_dengue_cases.parquet"
    cases.write_parquet(cases_path)

    scored: dict[int, int] = {}
    for year in (2021, 2022):
        out = tmp_path / f"out_{year}"
        assert (
            main(
                [
                    "--cases",
                    str(cases_path),
                    "--out",
                    str(out),
                    "--min-train",
                    "104",
                    "--score-from",
                    str(year),
                ]
            )
            == 0
        )
        record = json.loads((out / "dengue_br_h1_run.json").read_text(encoding="utf-8"))
        assert record["evaluation"]["score_from"] == year
        predictions = pl.read_parquet(out / "dengue_br_h1_predictions.parquet")
        assert all(week.year >= year for week in predictions[EW].to_list())
        scored[year] = predictions[EW].n_unique()

    assert scored[2021] > scored[2022] > 0  # começar depois pontua menos semanas
