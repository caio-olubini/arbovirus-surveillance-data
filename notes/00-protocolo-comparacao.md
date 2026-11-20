# 00 — Protocolo de comparação das representações

**Estado:** rascunho — 2026-10-07

## Por que este arquivo existe

Decidimos (2026-10-07) que 01, 02 e 03 são **representações concorrentes** do mesmo
corpus: cada uma gera seu próprio conjunto de features e o artigo responde "qual
representação da notícia prevê dengue melhor?". Comparação entre representações só
vale se todo o resto estiver fixo. É o que este arquivo fixa.

Se um braço ganhar porque usou um split melhor, um horizonte diferente ou uma
métrica que favorece o seu tipo de erro, o resultado é ruído publicado como achado.

## Revisão — 2026-11-20: a pergunta do artigo é mais larga que a notícia

O parágrafo acima diz que o artigo responde "qual representação da notícia prevê
dengue melhor?". Isso estava **estreito demais, e errado no sujeito**: o artigo
não é sobre a notícia, nem sobre os boletins. Ele pergunta se as **features
multimodais propostas carregam sinal relevante e quais vale a pena incluir**,
contra abordagens mais simples. As representações de notícia são **instâncias** de
feature multimodal — o mecanismo pelo qual a pergunta é respondida, não o assunto.

O que **não** muda é o chão comum abaixo. Comparação entre blocos de feature só
vale com alvo, calendário, split, métricas e backbone fixos; o motivo de este
arquivo existir continua de pé e agora vale para mais blocos do que três.

## Chão comum (não pode variar entre os braços)

| Item | Fixo em | Onde |
|---|---|---|
| Corpus | mesma versão congelada dos HTMLs (registrar hash + data) | `data/news/dengue/articles/` |
| Calendário | semana epidemiológica ancorada no domingo | `src/pipeline/epiweek.py` |
| Alvo | casos SINAN dengue **suspeitos** (toda notificação menos os descartados), na semana de **início de sintomas**; **BR** no número principal, UF como leitura exploratória | `SINAN_dengue_cases.parquet` |
| Covariáveis não-textuais | GT search + ERA5 UF×EW, mesmas features e lags | `GoogleTrends_search_EW`, `ERA5_UF_EW` |
| Backbone | **o mesmo** para todos os braços | TFT early-fusion (Lim et al. 2021 — DOI em [06](06-desenho-do-experimento.md)) como baseline de fusão |
| Split | rolling-origin, refit só com passado | — |
| Métricas | MAE, RMSE, MAPE **e** WIS/CRPS/cobertura | — |
| Baselines | naive, SARIMA/SARIMAX, InfoDengue-bayesiano, Google-Trends-only e **ensemble** | os que a linha usa — Xiao 2025 para os quatro primeiros, Johansson 2019 e Wu 2025 para o ensemble (DOIs em [06](06-desenho-do-experimento.md)) |

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
- [x] Definir o horizonte de previsão (1 semana? 4?). **1 semana**, para o
      primeiro número; multi-passo é o próximo eixo, não uma reescrita —
      `rolling_origin` já aceita horizonte maior.
- [x] Decidir alvo em nível ou log, e por UF ou BR. **Nível, BR.** Log é decisão
      de modelo e pertence ao modelo, não à régua; BR é onde notícia e alvo têm
      o mesmo grão, então a comparação é honesta. UF fica como exploratório, como
      já estava previsto nos riscos.
- [x] Escrever o baseline "sem texto" antes de qualquer representação — ele é a
      régua. **Meio caminho:** a régua ingênua está de pé e medida. Os dois
      ingênuos dão MAE de **4.047** (persistência, repetir a última semana) e
      **30.714** casos/semana (naive sazonal, repetir a mesma semana do ano
      anterior), em BR, horizonte 1, 557 semanas previstas de 2014 a 2026.
      A persistência é a régua de verdade: o naive sazonal é 7,6× pior porque
      dengue no Brasil pula de patamar entre anos (2024 teve média de 125.779
      casos/semana contra 32.001 em 2023). Falta o "sem texto" com GT e ERA5.

Números, comandos e o contrato compartilhado: [`src/forecast/README.md`](../src/forecast/README.md).
