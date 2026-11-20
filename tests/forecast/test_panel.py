"""O painel-alvo. O trabalho dele é recusar uma série com buraco."""

from __future__ import annotations

import datetime as dt

import polars as pl
import pytest

from src.forecast.panel import TargetGapError, load_target
from src.forecast.spec import CASES, EW
from src.pipeline.sinan.spec import (
    CASE_COUNT,
    EW_SYMPTOM_ONSET,
    FINAL_CLASSIFICATION,
    STATE_ABBREV,
)
from tests.forecast.conftest import DISCARDED, START, SUSPECTED

# Nome curto para a coluna de estado, usado só dentro destes testes.
STATE = STATE_ABBREV


def write(tmp_path, frame: pl.DataFrame) -> str:
    path = tmp_path / "SINAN_dengue_cases.parquet"
    frame.write_parquet(path)
    return str(path)


def test_a_continuous_series_becomes_a_continuous_panel(tmp_path, cases_from_weeks):
    frame = cases_from_weeks({i: [(10, SUSPECTED)] for i in range(5)})
    panel = load_target(write(tmp_path, frame), from_year=None)
    assert panel.height == 5
    assert panel[CASES].null_count() == 0
    assert panel[EW].to_list()[0] == START


def test_the_calendar_has_one_row_per_week_and_no_repeats(tmp_path, cases_from_weeks):
    frame = cases_from_weeks({i: [(1, SUSPECTED)] for i in range(30)})
    panel = load_target(write(tmp_path, frame), from_year=None)
    weeks = panel[EW].to_list()
    assert weeks == sorted(set(weeks))
    assert (weeks[-1] - weeks[0]).days == 29 * 7


def test_a_missing_week_is_refused_not_filled(tmp_path, cases_from_weeks):
    """A guarda que impede o lag sazonal de ler a semana errada."""
    weeks = {i: [(1, SUSPECTED)] for i in range(10)}
    del weeks[5]
    with pytest.raises(TargetGapError, match="1 week"):
        load_target(write(tmp_path, cases_from_weeks(weeks)), from_year=None)


def test_the_error_names_the_missing_week(tmp_path, cases_from_weeks):
    weeks = {i: [(1, SUSPECTED)] for i in range(10)}
    del weeks[5]
    missing = START + dt.timedelta(weeks=5)
    with pytest.raises(TargetGapError, match=str(missing)):
        load_target(write(tmp_path, cases_from_weeks(weeks)), from_year=None)


def test_an_absent_tail_outside_the_window_is_not_a_gap(tmp_path, cases_from_weeks):
    """A janela é definida pela própria primeira e última semana, então semanas
    que nunca estiveram nos dados simplesmente não fazem parte da pergunta."""
    frame = cases_from_weeks({i: [(1, SUSPECTED)] for i in (4, 5, 6)})
    panel = load_target(write(tmp_path, frame), from_year=None)
    assert panel.height == 3


def test_a_partial_year_raises_and_from_year_is_the_way_out(tmp_path, cases_from_weeks):
    """O 2013 real se comporta assim: presente, mas com semanas faltando.

    Sem filtro o painel recusa; estreitado para o ano completo ele fica usável.
    """
    weeks = {i: [(1, SUSPECTED)] for i in list(range(50)) + [55]}
    frame = cases_from_weeks(weeks)
    with pytest.raises(TargetGapError):
        load_target(write(tmp_path, frame), from_year=None)

    panel = load_target(write(tmp_path, frame), from_year=2021)
    assert panel.height == 1
    assert panel[EW].to_list() == [START + dt.timedelta(weeks=55)]


def test_discarded_notifications_are_not_cases(tmp_path, cases_from_weeks):
    frame = cases_from_weeks({0: [(7, SUSPECTED), (1000, DISCARDED)]})
    panel = load_target(write(tmp_path, frame), from_year=None)
    assert panel[CASES].to_list() == [7.0]


def test_cases_awaiting_classification_count_as_suspected(tmp_path, cases_from_weeks):
    """A classificação nula é a semana mais recente, não uma semana ausente."""
    frame = cases_from_weeks({0: [(5, SUSPECTED)]}).with_columns(
        pl.lit(None, dtype=pl.Int32).alias("final_classification")
    )
    panel = load_target(write(tmp_path, frame), from_year=None)
    assert panel[CASES].to_list() == [5.0]


def test_rows_in_the_same_week_are_summed(tmp_path, cases_from_weeks):
    frame = cases_from_weeks({0: [(3, SUSPECTED), (4, SUSPECTED)]})
    panel = load_target(write(tmp_path, frame), from_year=None)
    assert panel[CASES].to_list() == [7.0]


def test_a_window_with_no_cases_is_refused(tmp_path, cases_from_weeks):
    frame = cases_from_weeks({0: [(1, DISCARDED)]})
    with pytest.raises(TargetGapError, match="No case weeks"):
        load_target(write(tmp_path, frame), from_year=None)


def test_the_panel_is_sorted_by_week(tmp_path, cases_from_weeks):
    shuffled = pl.DataFrame(
        {
            "ew_symptom_onset": [
                START + dt.timedelta(weeks=w) for w in (2, 0, 1)
            ],
            "case_count": [3, 1, 2],
            "final_classification": [SUSPECTED] * 3,
        }
    )
    panel = load_target(write(tmp_path, shuffled), from_year=None)
    assert panel[CASES].to_list() == [1.0, 2.0, 3.0]


def test_a_to_year_narrows_the_end_of_the_window(tmp_path, cases_from_weeks):
    frame = cases_from_weeks({i: [(1, SUSPECTED)] for i in range(60)})
    panel = load_target(write(tmp_path, frame), from_year=2020, to_year=2020)
    assert panel[EW].max().year == 2020
    assert panel.height < 60


# --- o painel por estado ----------------------------------------------------
#
# `by_state=True` inverte a regra de buraco: uma semana de um estado sem
# notificação é zero caso, não buraco. Estes testes fixam essa inversão e a
# tabela de referência que diz quais estados o painel tem que carregar.


def a_reference(tmp_path, *states: str):
    """Uma tabela de unidades federativas com exatamente os estados nomeados."""
    path = tmp_path / "br_federative_units.csv"
    lines = ["CODE,NAME,ABBREVIATION,REGION"]
    lines += [f"{35 + i},{state},{state},SE" for i, state in enumerate(states)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def state_cases(rows: list[tuple[int, str, int]]) -> pl.DataFrame:
    """Um quadro em nível de caso com coluna de estado: (offset, estado, casos)."""
    return pl.DataFrame(
        {
            EW_SYMPTOM_ONSET: [START + dt.timedelta(weeks=w) for w, _, _ in rows],
            CASE_COUNT: [count for _, _, count in rows],
            FINAL_CLASSIFICATION: [SUSPECTED] * len(rows),
            STATE_ABBREV: [state for _, state, _ in rows],
        }
    )


def test_a_quiet_state_week_is_zero_not_a_gap(tmp_path):
    """Semana de um estado sem linha vira 0, e todo estado mantém toda semana."""
    reference = a_reference(tmp_path, "SP", "RJ")
    cases = state_cases([(0, "SP", 10), (4, "SP", 7), (2, "RJ", 3)])
    panel = load_target(
        write(tmp_path, cases), from_year=None, by_state=True, fu_path=reference
    )
    assert panel.height == 5 * 2  # 5 semanas, 2 estados
    sp = panel.filter(pl.col(STATE) == "SP").sort(EW)
    rj = panel.filter(pl.col(STATE) == "RJ").sort(EW)
    assert sp[CASES].to_list() == [10.0, 0.0, 0.0, 0.0, 7.0]
    assert rj[CASES].to_list() == [0.0, 0.0, 3.0, 0.0, 0.0]
    # O mesmo calendário sem buraco para os dois, que é o que permite a um modelo
    # por estado indexar por posição sem um estado derivar em relação ao outro.
    assert sp[EW].to_list() == rj[EW].to_list()


def test_the_state_panel_carries_week_state_and_cases(tmp_path):
    reference = a_reference(tmp_path, "SP")
    cases = state_cases([(0, "SP", 1)])
    panel = load_target(
        write(tmp_path, cases), from_year=None, by_state=True, fu_path=reference
    )
    assert panel.columns == [EW, STATE, CASES]


def test_a_state_absent_for_the_whole_window_is_refused(tmp_path):
    """Uma unidade faltando é arquivo incompleto, não estação quieta."""
    reference = a_reference(tmp_path, "SP", "RJ", "MG")
    cases = state_cases([(0, "SP", 1), (0, "RJ", 2)])
    with pytest.raises(TargetGapError, match="MG"):
        load_target(
            write(tmp_path, cases), from_year=None, by_state=True, fu_path=reference
        )


def test_a_state_outside_the_reference_table_is_refused(tmp_path):
    """A forma do painel é a da tabela de referência, então uma unidade a mais não é
    descartada em silêncio."""
    reference = a_reference(tmp_path, "SP")
    cases = state_cases([(0, "SP", 1), (0, "XX", 2)])
    with pytest.raises(TargetGapError, match="XX"):
        load_target(
            write(tmp_path, cases), from_year=None, by_state=True, fu_path=reference
        )


def test_the_states_sum_to_the_national_series(tmp_path):
    """O invariante, em escala de fixture: somar as unidades reconstrói o todo."""
    reference = a_reference(tmp_path, "SP", "RJ")
    rows = [(w, "SP", w) for w in range(6)] + [
        (w, "RJ", 2 * w) for w in range(6) if w != 3  # RJ quieto na semana 3
    ]
    path = write(tmp_path, state_cases(rows))

    national = load_target(path, from_year=None).sort(EW)
    by_state = load_target(path, from_year=None, by_state=True, fu_path=reference)
    per_week = (
        by_state.group_by(EW).agg(pl.col(CASES).sum().alias("from_states")).sort(EW)
    )
    joined = national.join(per_week, on=EW, how="left")
    assert joined.filter(pl.col(CASES) != pl.col("from_states")).height == 0
    assert int(national[CASES].sum()) == int(per_week["from_states"].sum())


# --- o invariante na série real ---------------------------------------------


@pytest.mark.integration
def test_the_states_sum_to_the_national_series_on_real_data(real_cases_path, fu_path):
    """O painel de 27 unidades reconstrói a série nacional, nos dados de verdade?

    Toda notificação na tabela de casos carrega um estado (a transformação faz um
    inner join nos códigos da referência), então a soma por unidade em cada semana
    deve ser igual ao número nacional exatamente. Este teste afirma exatamente
    zero. Se algum dia falhar, o tamanho e o sinal da diferença são o achado — uma
    notificação que perdeu o estado, ou um estado que falta na tabela de
    referência — e o trabalho do teste é expor isso, não ser afrouxado até passar.
    """
    national = load_target(real_cases_path).sort(EW)
    by_state = load_target(real_cases_path, by_state=True, fu_path=fu_path)
    assert by_state[STATE].n_unique() == 27

    per_week = (
        by_state.group_by(EW).agg(pl.col(CASES).sum().alias("from_states")).sort(EW)
    )
    joined = national.select(EW, CASES).join(per_week, on=EW, how="left")
    difference = joined.select(
        (pl.col(CASES).cast(pl.Int64) - pl.col("from_states").cast(pl.Int64)).alias("d")
    )
    assert difference["d"].abs().max() == 0
    assert int(national[CASES].sum()) == int(per_week["from_states"].sum())
