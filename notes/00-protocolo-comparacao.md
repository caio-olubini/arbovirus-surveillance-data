# 00 — Protocolo de comparação das representações

**Estado:** rascunho — 2026-10-07

## Por que este arquivo existe

Decidimos (2026-10-07) que 01, 02 e 03 são **representações concorrentes** do mesmo
corpus: cada uma gera seu próprio conjunto de features e o artigo responde "qual
representação da notícia prevê dengue melhor?". Comparação entre representações só
vale se todo o resto estiver fixo. É o que este arquivo fixa.

Se um braço ganhar porque usou um split melhor, um horizonte diferente ou uma
métrica que favorece o seu tipo de erro, o resultado é ruído publicado como achado.

## Chão comum (não pode variar entre os braços)

| Item | Fixo em | Onde |
|---|---|---|
| Corpus | mesma versão congelada dos HTMLs (registrar hash + data) | `data/news/dengue/articles/` |
| Calendário | semana epidemiológica ancorada no domingo | `src/pipeline/epiweek.py` |
| Alvo | casos SINAN dengue, UF × EW | `SINAN_dengue_cases.parquet` |
| Covariáveis não-textuais | GT search + ERA5 UF×EW, mesmas features e lags | `GoogleTrends_search_EW`, `ERA5_UF_EW` |
| Backbone | **o mesmo** para todos os braços | TFT early-fusion como baseline de fusão |
| Split | rolling-origin, refit só com passado | — |
| Métricas | MAE, RMSE, MAPE **e** WIS/CRPS/cobertura | — |
| Baselines | naive, SARIMA/SARIMAX, InfoDengue-bayesiano, Google-Trends-only | — |

**Só varia a representação do texto.** Um braço = uma representação → features →
mesmo modelo → mesmas métricas.

## Ablações obrigatórias

1. **Sem texto** (SINAN + GT + ERA5). O delta em relação a isso é *o valor da
   notícia* — é o número que o artigo precisa reportar.
2. Cada representação isolada (01, 02, 03).
3. Representações combinadas (par a par, depois as três).
4. **Controle negativo:** substituir o texto por vazio / constante / embaralhado.
   Se o erro não mudar, o texto não está sendo usado e o ganho é artefato de
   arquitetura. Ver `Tan et al. 2024` (arXiv:2406.16964) — remover o LLM de
   arquiteturas tipo Time-LLM empata ou melhora.

## Regras de vazamento

- Nenhum artigo publicado **depois** da origem da previsão entra no braço.
- O corpus vai até 2026 e os modelos pré-treinados podem "conhecer" os desfechos
  (dengue 2024 foi recorde e está em toda parte). Preferir pesos abertos com data
  de corte conhecida; registrar o corte de cada modelo usado.
- SINAN tem atraso de notificação e revisão — a série de uma EW é reescrita depois.
  Isso afeta qualquer avaliação de nowcasting.

## Riscos do desenho

- **Descompasso espacial.** Notícia é nacional, alvo é UF. Testar também em nível BR,
  onde a comparação é honesta, e tratar UF como exploratório.
- **Esparsidade.** ~3,6 artigos/semana nacionalmente. Em UF, a maioria das semanas
  fica em zero. Mascarar semana sem artigo e usar um indicador explícito de
  "sem notícia" para o modelo distinguir ausência de sinal de sinal neutro.
- **Endogeneidade.** Cobertura segue casos. Granger aqui é ordenação temporal
  preditiva, nunca mecanismo. Ver a literatura de viés de notificação (caxumba,
  Cryptosporidium) citada em 01.
- **Comparação de métricas.** Métricas pontuais e probabilísticas podem escolher
  modelos diferentes. Reportar as duas e dizer quando divergirem.

## Pendências / próximo passo

- [ ] Congelar e versionar a versão do corpus usada (hash dos HTMLs + data).
- [ ] Definir o horizonte de previsão (1 semana? 4?). Isso muda tudo a jusante.
- [ ] Decidir alvo em nível ou log, e por UF ou BR.
- [ ] Escolher o backbone exato e escrever o baseline "sem texto" antes de
      qualquer representação — ele é a régua.
