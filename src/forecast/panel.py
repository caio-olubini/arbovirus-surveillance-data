"""A série-alvo, num calendário semanal contínuo.

Todo baseline e todo modelo posterior lê o alvo por este módulo, pelo mesmo
motivo que `pipeline.sinan.cases.weekly_cases` existe: o protocolo 00 fixa o
alvo como condição fixa da comparação, então ele tem que ser uma função e não
três que por acaso concordam hoje.

O que este módulo acrescenta sobre `weekly_cases` é o **calendário contínuo**, e
isso não é detalhe. A avaliação de origem móvel indexa a série por posição: a
previsão para o passo *i* é comparada ao valor na posição *i*. Se faltar uma
semana no quadro, toda posição depois dela anda uma casa e o baseline sazonal lê
a semana errada em silêncio — um lag de 52 cai 51 ou 53 semanas atrás, e nada
levanta. Então ou o painel não tem buraco, ou a função se recusa a devolver.

**Duas formas.** O padrão devolve uma linha por semana, nacional. `by_state=True`
devolve uma linha por (estado, semana) com o mesmo alvo. A regra de buraco se
inverte entre as duas, e a inversão é o ponto: o SINAN só escreve uma linha
(estado, semana) quando aquele estado notificou algo, então uma semana quieta de
um estado não tem linha nenhuma e tratá-la como buraco recusaria toda série
real. Por estado, semana ausente é **zero caso**; um estado que não aparece no
arquivo de jeito nenhum é outra coisa — arquivo incompleto — e ainda levanta. O
nacional fica como estava: a série nacional é densa por construção, então um
buraco nela significa que a transformação derrubou algo.
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

from ..pipeline.sinan.cases import weekly_cases
from ..pipeline.sinan.spec import EW_SYMPTOM_ONSET, STATE_ABBREV
from .spec import CASES, EW, FIRST_COMPLETE_YEAR

log = logging.getLogger("forecast")


class TargetGapError(ValueError):
    """O painel-alvo não tem a forma completa que prometeu.

    Levanta quando falta uma semana prometida na série nacional, ou quando falta
    uma unidade federativa esperada da tabela de referência na série por estado.
    """


def load_target(
    cases_path: str,
    from_year: int | None = FIRST_COMPLETE_YEAR,
    to_year: int | None = None,
    by_state: bool = False,
    fu_path: str | Path | None = None,
) -> pl.DataFrame:
    """Casos suspeitos de dengue por semana epidemiológica, em calendário contínuo.

    `cases_path` é a tabela em nível de caso escrita por `arboili transform sinan`,
    não a série semanal: o filtro de notificação até caso suspeito pertence a
    `weekly_cases` e é aplicado aqui em vez de duplicado.

    A janela começa em 2014 por padrão. 2013 existe no arquivo só como a cauda de
    início de sintomas das notificações registradas em 2014, então chega com três
    semanas faltando e um primeiro ano parcial; `from_year=None` a mantém e vai
    levantar quando o buraco aparecer, que é o desfecho pretendido e não um bug a
    contornar.

    `by_state=True` fatia o alvo por unidade federativa, uma linha por
    (estado, semana). O conjunto de unidades é a **tabela de referência** que o
    resto do projeto já usa para códigos de estado (`br_federative_units.csv`,
    lida por `fu_path`, com padrão em `config.yml`, chave
    `reference.federative_units`) e não as unidades que por acaso aparecem no
    arquivo de casos. A escolha importa: o arquivo nomeia as próprias unidades,
    então lê-las do arquivo faria o painel perder em silêncio um estado que não
    notificou nada, e uma forma fixa de 27 linhas é o que uma comparação por
    estado precisa. É pegar o conjunto da tabela de referência que permite levantar
    quando um estado não tem linha nenhuma, em vez de deixá-lo passar como uma
    estação quieta.
    """
    frame = pl.read_parquet(cases_path)
    if by_state:
        return _state_panel(frame, cases_path, from_year, to_year, fu_path)

    weekly = weekly_cases(frame).rename({EW_SYMPTOM_ONSET: EW}).sort(EW)

    if from_year is not None:
        weekly = weekly.filter(pl.col(EW).dt.year() >= from_year)
    if to_year is not None:
        weekly = weekly.filter(pl.col(EW).dt.year() <= to_year)

    if weekly.height == 0:
        raise TargetGapError(
            f"No case weeks between {from_year} and {to_year} in {cases_path}."
        )

    first, last = weekly[EW].min(), weekly[EW].max()
    calendar = pl.DataFrame(
        {EW: pl.date_range(first, last, interval="1w", eager=True)}
    )
    panel = calendar.join(weekly, on=EW, how="left").sort(EW)

    missing = panel.filter(pl.col(CASES).is_null())
    if missing.height:
        weeks = ", ".join(str(w) for w in missing[EW].to_list()[:10])
        raise TargetGapError(
            f"{missing.height} week(s) missing from the target series between "
            f"{first} and {last}: {weeks}"
            + (" …" if missing.height > 10 else "")
            + ". A gap shifts every later position, so the seasonal lag would "
            "read the wrong week without raising. Narrow the window with "
            "`from_year` to a period that is complete."
        )

    log.info(
        "target: %d weeks, %s → %s, %d total cases",
        panel.height,
        first,
        last,
        panel[CASES].sum(),
    )
    return panel


def _state_panel(
    frame: pl.DataFrame,
    cases_path: str,
    from_year: int | None,
    to_year: int | None,
    fu_path: str | Path | None,
) -> pl.DataFrame:
    """O alvo por estado: um calendário contínuo para cada unidade federativa.

    Semana que um estado não notificou é zero caso, não semana faltando — o
    calendário aqui marca toda semana entre a primeira e a última do painel para
    cada unidade esperada, então a série de um estado é contígua mesmo através de
    uma sequência de semanas quietas. As semanas para as quais um estado não tem
    linha são as únicas que a soma das 27 unidades perderia, e zerá-las é o que
    faz essa soma reconstruir a série nacional.
    """
    weekly = weekly_cases(frame, by_state=True).rename({EW_SYMPTOM_ONSET: EW})

    if from_year is not None:
        weekly = weekly.filter(pl.col(EW).dt.year() >= from_year)
    if to_year is not None:
        weekly = weekly.filter(pl.col(EW).dt.year() <= to_year)

    if weekly.height == 0:
        raise TargetGapError(
            f"No case weeks between {from_year} and {to_year} in {cases_path}."
        )

    expected = _expected_states(fu_path)
    observed = set(weekly[STATE_ABBREV].unique().to_list())

    missing = sorted(expected - observed)
    if missing:
        raise TargetGapError(
            f"{len(missing)} federative unit(s) expected from the reference table "
            f"have no row at all in {cases_path}: {', '.join(missing)}. A unit "
            "missing for the whole window is an incomplete file, not a quiet "
            "season, so the panel refuses rather than dropping it silently."
        )
    unknown = sorted(observed - expected)
    if unknown:
        raise TargetGapError(
            f"{len(unknown)} federative unit(s) in {cases_path} are not in the "
            f"reference table: {', '.join(unknown)}. The panel's shape is the "
            "reference table's, so an unexpected unit would be dropped without "
            "raising."
        )

    first, last = weekly[EW].min(), weekly[EW].max()
    calendar = pl.DataFrame(
        {EW: pl.date_range(first, last, interval="1w", eager=True)}
    )
    units = pl.DataFrame({STATE_ABBREV: sorted(expected)})
    panel = (
        calendar.join(units, how="cross")
        .join(weekly, on=[EW, STATE_ABBREV], how="left")
        .with_columns(pl.col(CASES).fill_null(0))
        .sort([STATE_ABBREV, EW])
    )

    log.info(
        "target (by state): %d units × %d weeks (%s → %s), %d total cases",
        panel[STATE_ABBREV].n_unique(),
        panel.height // panel[STATE_ABBREV].n_unique(),
        first,
        last,
        panel[CASES].sum(),
    )
    return panel


def _expected_states(fu_path: str | Path | None) -> set[str]:
    """As 27 abreviações de unidade federativa, da tabela de referência comum.

    O caminho sai do `config.yml` quando o chamador não passa um, para que o
    painel e todo outro estágio leiam a mesma tabela — uma segunda cópia da lista
    de estados é o tipo de deriva que este pacote existe para evitar.
    """
    if fu_path is None:
        from ..config import load_config

        fu_path = load_config().reference("federative_units")
    return set(pl.read_csv(fu_path)["ABBREVIATION"].to_list())
