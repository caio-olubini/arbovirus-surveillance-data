"""A montagem com que uma tabela de resultado foi produzida.

O protocolo 00 assenta numa premissa: um número citado no artigo tem que dizer
quais botões o produziram, porque uma comparação só é comparação enquanto tudo
menos a representação estiver fixo. `--out` escreve as previsões e o resumo, e o
resumo carrega o horizonte e o baseline — mas não a primeira semana do painel,
nem quantas semanas de histórico a primeira previsão teve, nem o quanto as
origens andaram entre uma previsão e a seguinte. Leia aquele arquivo seis meses
depois e não há como saber se o histórico era 104 semanas ou 200, e a diferença
entre esses dois números não é pequena.

A janela de pontuação pertence aqui pelo mesmo motivo: duas execuções sobre um
painel, idênticas em toda flag menos o ano em que a pontuação começa, devolvem
médias diferentes do mesmo histórico, e só o registro diz qual delas produziu o
número no slide.

Então a metade que falta é escrita ao lado dos resultados, como JSON.

Nada aqui depende de quando a execução aconteceu. Duas execuções do mesmo comando
escrevem os mesmos bytes, e é isso que torna o arquivo digno de comparação: um
registro que difere significa que uma flag diferiu.
"""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from .evaluate import ORIGIN_EW, ForecastRun
from .spec import BASELINE, CASES, EW, GEOGRAPHY, HORIZON

# Incrementado quando uma chave é renomeada ou removida, para que quem lê
# distinga uma chave faltando de uma chave que nunca existiu. A versão 2
# acrescenta a metade probabilística: sem o incremento, um leitor não saberia se
# `quantile_levels` faltou ou se a execução é anterior à grade.
SCHEMA = "forecast.run/2"


def setup_record(
    panel: pl.DataFrame,
    run: ForecastRun,
    cases_path: str | Path,
) -> dict:
    """A montagem com que uma tabela de resultado tem que viajar.

    As flags sozinhas não bastam e a execução sozinha também não. `min_train` é
    uma contagem de semanas, então não diz nada até o painel dizer quais semanas
    foram essas; dois painéis de comprimentos diferentes podem carregar o mesmo
    `min_train` e pontuar períodos diferentes. Os dois entram.
    """
    first, last = panel[EW].min(), panel[EW].max()
    return {
        "schema": SCHEMA,
        "target": {
            "source": str(cases_path),
            "geography": GEOGRAPHY,
            "weeks": panel.height,
            "first_week": first.isoformat(),
            "last_week": last.isoformat(),
            "total_cases": int(panel[CASES].sum()),
        },
        "evaluation": {
            "horizon": run.horizon,
            "min_train": run.min_train,
            "step": run.step,
            "score_from": run.score_from,
            "baselines": list(run.baselines),
            "origins": run.predictions[ORIGIN_EW].n_unique(),
            "scored": run.predictions.height,
            # A metade probabilística, com os dois números que a explicam. Os
            # níveis porque duas grades não são comparáveis; a amostra mínima
            # porque é ela que decide desde quando existe distribuição; e as
            # semanas em contagem de semanas, não de linhas — a tabela de quantis
            # tem uma linha por nível, então contar linhas diria sete vezes o que
            # `scored` diz uma vez. O horizonte entra na chave junto com o
            # baseline, pelo mesmo motivo que entra em `scored`: com mais de um
            # passo, a mesma semana é prevista mais de uma vez.
            "quantile_levels": list(run.levels),
            "min_error_sample": run.min_error_sample,
            "scored_quantiles": run.quantile_predictions.select(
                [BASELINE, HORIZON, EW]
            )
            .unique()
            .height,
        },
    }


def write_record(record: dict, path: str | Path, command: str | None = None) -> Path:
    """Escreve o registro, com o comando que o produziu quando conhecido.

    O comando entra aqui e não em `setup_record` porque ele pertence ao chamador:
    um notebook que chama `evaluate` direto não tem linha de comando, e uma vazia
    seria lida como um comando que se perdeu.
    """
    if command is not None:
        record = {**record, "command": command}
    path = Path(path)
    path.write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return path
