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
from .metrics import mae, mape, mape_denominator, rmse
from .spec import (
    BASELINE,
    BASELINES,
    CASES,
    DEFAULT_HORIZON,
    DEFAULT_MIN_TRAIN,
    EW,
    HORIZON,
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
    """

    predictions: pl.DataFrame
    metrics: pl.DataFrame
    horizon: int
    min_train: int
    step: int
    baselines: tuple[str, ...]
    # O primeiro ano cujas semanas foram pontuadas, ou None para "pontua tudo o
    # que o painel alcança". Fica registrado porque, sem ele, duas execuções sobre
    # o mesmo painel com janelas de pontuação diferentes devolvem números
    # diferentes com as mesmas flags — o histórico ficou fixo, só a janela de
    # correção andou.
    score_from: int | None = None

    def summary(self) -> str:
        """A tabela de métricas como texto simples, para um terminal ou célula."""
        return format_metrics(self.metrics)


def format_metrics(metrics: pl.DataFrame) -> str:
    """Desenha a tabela de métricas como texto alinhado.

    O repr do Polars corta a linha, e um MAE cortado é o tipo de coisa
    que vai parar errada num slide, então a tabela é formatada à mão.
    """
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
    widths = [
        max(len(header[i]), *(len(r[i]) for r in rows)) if rows else len(header[i])
        for i in range(len(header))
    ]
    lines = [
        "  ".join(h.rjust(w) for h, w in zip(header, widths)),
        "  ".join("-" * w for w in widths),
    ]
    lines += ["  ".join(c.rjust(w) for c, w in zip(r, widths)) for r in rows]
    return "\n".join(lines)


def evaluate(
    panel: pl.DataFrame,
    baselines: tuple[str, ...] = BASELINES,
    horizon: int = DEFAULT_HORIZON,
    min_train: int = DEFAULT_MIN_TRAIN,
    step: int = 1,
    score_from: int | None = None,
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

    for origin in rolling_origin(panel, min_train=min_train, horizon=horizon, step=step):
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

    if not rows:
        raise ValueError(
            "no origin produced a forecast; the panel is shorter than min_train "
            "plus horizon."
        )

    predictions = pl.DataFrame(rows).sort([BASELINE, HORIZON, EW])

    # A janela de pontuação. Descartada aqui, antes das métricas, e não encolhendo
    # o painel: encolher o painel encurtaria também o histórico que a primeira
    # previsão corrigida enxerga, que é o botão errado — o ponto de `score_from` é
    # manter o histórico fixo e mover só a correção.
    if score_from is not None:
        predictions = predictions.filter(pl.col(EW).dt.year() >= score_from)
        if predictions.height == 0:
            raise ValueError(
                f"no scored week falls in {score_from} or later: the panel's last "
                f"week is before the scoring window begins. Lower score_from or "
                f"widen the panel's to_year."
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
            }
        )

    metrics = pl.DataFrame(summaries).sort([BASELINE, HORIZON])
    return ForecastRun(
        predictions=predictions,
        metrics=metrics,
        horizon=horizon,
        min_train=min_train,
        step=step,
        baselines=tuple(baselines),
        score_from=score_from,
    )
