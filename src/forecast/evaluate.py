"""O laço de origem móvel: a máquina que vira um painel num número.

É a peça em que o resto do projeto se encaixa. Um baseline ou um modelo entra
como função do histórico e sai como uma tabela de uma linha por semana pontuada,
e todo número do artigo sai dessa tabela. Nada aqui sabe o que um baseline faz;
acrescentar o braço 01 depois é uma entrada no registro, não uma reescrita.

O contrato que torna a comparação confiável está em `splits.py` — na origem *i* o
chamador pode ler o painel até a posição *i* e nada depois. Aqui o laço
nunca entrega mais que isso: o histórico passado a cada baseline é
uma fatia que termina na origem.
"""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl

from .baselines import BASELINE_FUNCS
from .interval import error_histories, predictive_quantiles
from .metrics import (
    coverage,
    interval_width,
    mae,
    mape,
    mape_denominator,
    rmse,
    wis,
)
from .spec import (
    BASELINE,
    BASELINES,
    CASES,
    CENTRAL_INTERVALS,
    DEFAULT_HORIZON,
    DEFAULT_MIN_TRAIN,
    EW,
    HORIZON,
    MIN_ERROR_SAMPLE,
    QUANTILE_LEVELS,
)
from .splits import rolling_origin

# Nomes das colunas de resultado, guardados aqui para que quem lê o parquet
# saiba o que esperar.
ORIGIN_EW = "origin_ew"
TRUE = "y_true"
PRED = "y_pred"
N = "n"
MEAN_TRUTH = "mean_truth"
MAPE_N = "mape_n"
MAE = "mae"
RMSE = "rmse"
MAPE = "mape"

# A metade probabilística sai em tabelas próprias, e não em colunas a mais aqui.
# O motivo é de contagem: com uma amostra de erros mínima (ver `spec.py`), a
# distribuição não existe nas primeiras origens do painel, então o número de
# semanas de uma tabela não é o da outra. Duas tabelas com alturas diferentes
# dizem isso; uma linha só com um `n` e um WIS esconderia qual dos dois vale.
QUANTILE = "quantile"
WIS = "wis"
N_QUANTILE = "n_quantile"
COVERAGE_LEVEL = "coverage_level"
COVERAGE = "coverage"
WIDTH = "interval_width"

INTERVAL_COLUMNS = (BASELINE, HORIZON, COVERAGE_LEVEL, COVERAGE, WIDTH)


@dataclass(frozen=True)
class ForecastRun:
    """Uma avaliação: o que foi previsto, semana a semana, e o quanto errou.

    `predictions` guarda toda semana pontuada para que uma média ruim possa ser
    rastreada até as semanas que a causaram — um pico de epidemia errado por
    muito é um achado diferente de ruído uniforme, e só a tabela linha a linha
    distingue os dois.

    `metrics` é o resumo, agrupado por baseline e por passo do horizonte. Com
    vários passos à frente o agrupamento importa: o passo 1 e o passo 4 são
    perguntas diferentes e tirar a média dos dois esconde qual deles piorou.

    `quantile_predictions` é a mesma coisa para uma previsão que reporta
    quantis, em formato longo — uma linha por nível, e não uma coluna por nível,
    para que mexer na grade não mude a forma da tabela. `intervals` resume
    cobertura e largura de cada faixa central.
    """

    predictions: pl.DataFrame
    metrics: pl.DataFrame
    quantile_predictions: pl.DataFrame
    intervals: pl.DataFrame
    horizon: int
    min_train: int
    step: int
    baselines: tuple[str, ...]
    levels: tuple[float, ...] = QUANTILE_LEVELS
    # Quantos erros observados uma distribuição precisa antes de ser pontuada. O
    # padrão é o declarado em `spec.py`; fica na execução porque duas tabelas
    # medidas com pisos diferentes não são a mesma medição.
    min_error_sample: int = MIN_ERROR_SAMPLE
    # O primeiro ano cujas semanas foram pontuadas, ou None para "pontua tudo o
    # que o painel alcança". Fica registrado porque, sem ele, duas execuções sobre
    # o mesmo painel com janelas de pontuação diferentes devolvem números
    # diferentes com as mesmas flags — o histórico ficou fixo, só a janela de
    # correção andou.
    score_from: int | None = None

    def summary(self) -> str:
        """A tabela de métricas como texto simples, para um terminal ou célula."""
        return format_metrics(self.metrics)

    def distribution_summary(self) -> str:
        """A metade probabilística como texto: WIS por linha, cobertura por faixa.

        Separada de `summary` porque as duas tabelas respondem a perguntas
        diferentes e juntas não cabem numa linha de terminal. O WIS vai colado ao
        `n_quantile` de propósito: sozinho, um WIS não diz sobre quantas semanas
        ele foi medido.
        """
        return format_distribution(self.metrics, self.intervals)


def _render_table(header: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
    """Uma tabela de texto com as colunas alinhadas à direita.

    O repr do Polars corta a linha, e um MAE cortado é o tipo de coisa que vai
    parar errada num slide, então as tabelas são formatadas à mão.
    """
    widths = [
        max(len(header[i]), *(len(row[i]) for row in rows)) if rows else len(header[i])
        for i in range(len(header))
    ]
    lines = [
        "  ".join(h.rjust(w) for h, w in zip(header, widths)),
        "  ".join("-" * w for w in widths),
    ]
    lines += ["  ".join(c.rjust(w) for c, w in zip(row, widths)) for row in rows]
    return "\n".join(lines)


def format_metrics(metrics: pl.DataFrame) -> str:
    """Desenha a tabela de métricas pontuais como texto alinhado."""
    header = ("baseline", "step", "weeks", "MAE", "RMSE", "MAPE", "MAPE n")
    rows = [
        (
            row[BASELINE],
            str(row[HORIZON]),
            str(row[N]),
            f"{row[MAE]:,.0f}",
            f"{row[RMSE]:,.0f}",
            f"{row[MAPE] * 100:,.1f}%",
            str(row[MAPE_N]),
        )
        for row in metrics.iter_rows(named=True)
    ]
    return _render_table(header, rows)


def format_distribution(metrics: pl.DataFrame, intervals: pl.DataFrame) -> str:
    """As duas tabelas da metade probabilística: o WIS e a forma das faixas.

    Duas porque a pergunta é dupla: quanto o erro custa quando a previsão inteira
    é pontuada, e o que a distribuição fez para chegar lá. Uma faixa larga compra
    cobertura, e só a largura ao lado da cobertura diz se comprou ou se mediu.
    """
    wis_rows = [
        (
            row[BASELINE],
            str(row[HORIZON]),
            str(row[N_QUANTILE]),
            f"{row[WIS]:,.0f}" if row[WIS] is not None else "—",
        )
        for row in metrics.iter_rows(named=True)
    ]
    if metrics[N_QUANTILE].max() == 0:
        return (
            "No distribution was scored: on this run the error sample never "
            "reached the declared minimum, so WIS and coverage have nothing to "
            "average. The point metrics above are unaffected — they are scored "
            "on every week the panel reaches."
        )

    blocks = [
        _render_table(("baseline", "step", "weeks", "WIS"), wis_rows),
        "",
        _render_table(
            ("baseline", "step", "nominal", "covered", "width (cases)"),
            [
                (
                    row[BASELINE],
                    str(row[HORIZON]),
                    f"{row[COVERAGE_LEVEL] * 100:,.0f}%",
                    f"{row[COVERAGE] * 100:,.1f}%",
                    f"{row[WIDTH]:,.0f}",
                )
                for row in intervals.iter_rows(named=True)
            ],
        ),
    ]
    return "\n".join(blocks)


def evaluate(
    panel: pl.DataFrame,
    baselines: tuple[str, ...] = BASELINES,
    horizon: int = DEFAULT_HORIZON,
    min_train: int = DEFAULT_MIN_TRAIN,
    step: int = 1,
    score_from: int | None = None,
    levels: tuple[float, ...] = QUANTILE_LEVELS,
    min_error_sample: int = MIN_ERROR_SAMPLE,
) -> ForecastRun:
    """Pontua todo baseline em toda origem do painel.

    `panel` tem que vir de `panel.load_target`: o laço indexa por posição, então
    uma semana faltando faria o baseline sazonal ler a semana de referência errada
    sem levantar. Essa garantia é do painel, não desta função.

    `step` anda as origens para frente de mais de uma semana quando a execução é
    lenta demais para fazer toda semana. Muda quais semanas são pontuadas e
    portanto os números, então fica registrado na execução e pertence a qualquer
    tabela que os cite.

    `score_from` separa a janela que treina da janela que é corrigida. As origens
    continuam sendo percorridas pelo painel inteiro, então o histórico atrás da
    primeira previsão corrigida é tudo desde a primeira semana do painel; só as
    previsões cuja **semana pontuada** cai antes de 1º de janeiro de `score_from`
    são descartadas antes do cálculo das métricas. O corte é na semana pontuada,
    não na origem, porque uma previsão feita na última semana do ano costuma cair
    na seguinte — e um modelo é julgado pela semana que previu, não pela semana em
    que estava. `None` corrige toda semana que o painel alcança.

    `levels` é a grade de quantis que a metade probabilística pontua. O padrão é o
    declarado em `spec.py`; ela é um parâmetro para que um teste possa usar uma
    grade de três níveis, e não porque uma execução deva variá-la sem motivo — a
    grade viaja no registro da execução, então duas tabelas com grades diferentes
    não são comparáveis por acidente.

    `min_error_sample` é quantos erros já observados uma distribuição precisa
    antes de valer. Pelo mesmo motivo é um parâmetro e também viaja no registro:
    abaixo do piso a origem fica de fora das tabelas probabilísticas e fora de
    `n_quantile`, que conta, por baseline, as semanas que receberam distribuição —
    quem ficou de fora são as semanas que aquele baseline pontuou menos o
    `n_quantile` dele. O `scored` do registro conta linhas de todas as baselines e
    não serve para essa conta. Mexer no piso muda sobre quantas semanas o WIS foi
    medido.
    """
    unknown = [name for name in baselines if name not in BASELINE_FUNCS]
    if unknown:
        raise ValueError(
            f"unknown baseline(s): {unknown}. Known: {sorted(BASELINE_FUNCS)}."
        )
    if not baselines:
        raise ValueError("no baselines to evaluate.")

    values = [float(v) for v in panel[CASES].to_list()]
    rows: list[dict] = []
    quantile_rows: list[dict] = []
    # As origens antes dos erros, e não dentro do laço, porque quem calcula os
    # erros não sabe onde a avaliação começa. Num painel mais curto que o treino
    # mínimo, quem falava primeiro era a amostra de erro — e ela culpava o
    # baseline por um painel que não chega à primeira origem. Materializar a lista
    # aqui deixa quem sabe do assunto responder: o próprio `rolling_origin`, que
    # diz quantas semanas faltam e qual é a última origem possível. O erro também
    # passa a apontar o defeito antes de o laço ser montado, e não no meio dele.
    origins = list(rolling_origin(panel, min_train=min_train, horizon=horizon, step=step))
    # Os erros que cada baseline já cometeu no painel inteiro, uma vez por passo
    # do horizonte. O erro cometido numa posição não depende da origem — só da
    # série até ali —, então cada origem lê um prefixo do que já foi calculado, e
    # nenhum quantil pode ver a semana que a origem ainda não viu.
    errors = {
        name: error_histories(values, horizon, BASELINE_FUNCS[name], name=name)
        for name in baselines
    }

    for origin in origins:
        history = values[: origin.train_end]
        target_indices = list(origin.target_indices())

        for name in baselines:
            forecast = BASELINE_FUNCS[name](history, horizon)
            for offset, predicted in zip(target_indices, forecast):
                rows.append(
                    {
                        ORIGIN_EW: origin.ew,
                        EW: panel[EW][offset],
                        HORIZON: offset - origin.index,
                        BASELINE: name,
                        TRUE: values[offset],
                        PRED: predicted,
                    }
                )
                # A distribuição da mesma previsão: a previsão pontual é o centro
                # dela, e a largura é a dos erros que este baseline já cometeu
                # neste passo. `None` quando a amostra ainda é fina demais para
                # um quantil valer — a origem é pulada e contada, não inventada.
                step_ahead = offset - origin.index
                sample = errors[name][step_ahead].sample(origin.index)
                quantiles = predictive_quantiles(
                    predicted, sample, levels, min_sample=min_error_sample
                )
                if quantiles is None:
                    continue
                for level, value in quantiles.items():
                    quantile_rows.append(
                        {
                            ORIGIN_EW: origin.ew,
                            EW: panel[EW][offset],
                            HORIZON: step_ahead,
                            BASELINE: name,
                            TRUE: values[offset],
                            QUANTILE: level,
                            PRED: value,
                        }
                    )

    if not rows:
        raise ValueError(
            "no origin produced a forecast; the panel is shorter than min_train "
            "plus horizon."
        )

    predictions = pl.DataFrame(rows).sort([BASELINE, HORIZON, EW])

    quantile_predictions = (
        pl.DataFrame(quantile_rows).sort([BASELINE, HORIZON, QUANTILE, EW])
        if quantile_rows
        else pl.DataFrame(
            schema={
                ORIGIN_EW: pl.Date,
                EW: pl.Date,
                HORIZON: pl.Int64,
                BASELINE: pl.String,
                TRUE: pl.Float64,
                QUANTILE: pl.Float64,
                PRED: pl.Float64,
            }
        )
    )

    # A janela de pontuação. Descartada aqui, antes das métricas, e não encolhendo
    # o painel: encolher o painel encurtaria também o histórico que a primeira
    # previsão corrigida enxerga, que é o botão errado — o ponto de `score_from` é
    # manter o histórico fixo e mover só a correção. A mesma janela vale para as
    # duas tabelas, e elas ainda assim podem ficar com alturas diferentes: a
    # amostra de erros pode ser fina demais no começo do painel, então cada uma
    # reporta o próprio total em vez de o leitor supor que são o mesmo.
    if score_from is not None:
        predictions = predictions.filter(pl.col(EW).dt.year() >= score_from)
        if predictions.height == 0:
            raise ValueError(
                f"no scored week falls in {score_from} or later: the panel's last "
                f"week is before the scoring window begins. Lower score_from or "
                f"widen the panel's to_year."
            )
        quantile_predictions = quantile_predictions.filter(
            pl.col(EW).dt.year() >= score_from
        )

    wis_by_group, weeks_by_group, interval_rows = _distribution_by_group(
        quantile_predictions, levels
    )

    summaries = []
    for (name, h), group in predictions.group_by([BASELINE, HORIZON], maintain_order=True):
        truth = group[TRUE].to_list()
        pred = group[PRED].to_list()
        summaries.append(
            {
                BASELINE: name,
                HORIZON: h,
                N: len(truth),
                MEAN_TRUTH: sum(truth) / len(truth),
                MAE: mae(truth, pred),
                RMSE: rmse(truth, pred),
                MAPE: mape(truth, pred),
                MAPE_N: mape_denominator(truth),
                # Zero e None, e não dois zeros: um grupo sem distribuição não
                # errou zero, ele não foi pontuado probabilisticamente.
                N_QUANTILE: weeks_by_group.get((name, h), 0),
                WIS: wis_by_group.get((name, h)),
            }
        )

    metrics = (
        pl.DataFrame(summaries)
        .with_columns(pl.col(WIS).cast(pl.Float64))
        .sort([BASELINE, HORIZON])
    )
    intervals = pl.DataFrame(
        interval_rows,
        schema={
            BASELINE: pl.String,
            HORIZON: pl.Int64,
            COVERAGE_LEVEL: pl.Float64,
            COVERAGE: pl.Float64,
            WIDTH: pl.Float64,
        },
        orient="row",
    ).sort([BASELINE, HORIZON, COVERAGE_LEVEL])

    return ForecastRun(
        predictions=predictions,
        metrics=metrics,
        quantile_predictions=quantile_predictions,
        intervals=intervals,
        horizon=horizon,
        min_train=min_train,
        step=step,
        baselines=tuple(baselines),
        levels=tuple(levels),
        min_error_sample=min_error_sample,
        score_from=score_from,
    )


def _distribution_by_group(
    quantile_predictions: pl.DataFrame, levels: tuple[float, ...]
) -> tuple[dict[tuple[str, int], float], dict[tuple[str, int], int], list[dict]]:
    """WIS por (baseline, passo), quantas semanas o sustentam, e cada faixa central.

    Separado de `evaluate` porque é a única parte do arquivo que sabe o que é um
    quantil: o laço acima trata uma previsão por quantis como mais linhas da
    mesma coisa, e é aqui que elas viram cobertura, largura e um número só.
    """
    if quantile_predictions.height == 0:
        return {}, {}, []

    wis_by_group: dict[tuple[str, int], float] = {}
    weeks_by_group: dict[tuple[str, int], int] = {}
    interval_rows: list[dict] = []

    for (name, h), group in quantile_predictions.group_by(
        [BASELINE, HORIZON], maintain_order=True
    ):
        by_level = {
            level: group.filter(pl.col(QUANTILE) == level).sort(EW)
            for level in group[QUANTILE].unique().to_list()
        }
        # A verdade é a mesma em todo nível — a linha difere só na previsão.
        truth = next(iter(by_level.values()))[TRUE].to_list()
        quantiles = {level: frame[PRED].to_list() for level, frame in by_level.items()}

        wis_by_group[(name, h)] = wis(truth, quantiles, levels)
        weeks_by_group[(name, h)] = len(truth)

        for lower, upper, coverage_level in CENTRAL_INTERVALS:
            # Um intervalo só é reportado se os dois níveis que o formam foram
            # pontuados; um lado só não é uma faixa.
            if lower not in quantiles or upper not in quantiles:
                continue
            interval_rows.append(
                {
                    BASELINE: name,
                    HORIZON: h,
                    COVERAGE_LEVEL: coverage_level,
                    COVERAGE: coverage(truth, quantiles[lower], quantiles[upper]),
                    WIDTH: interval_width(quantiles[lower], quantiles[upper]),
                }
            )

    return wis_by_group, weeks_by_group, interval_rows
