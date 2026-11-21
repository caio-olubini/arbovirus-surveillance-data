# 04 — Extração estruturada por LLM

**Estado:** standby — 2026-11-21. Depende do orçamento de tempo, e do passo 6 do
[plano](plano.md) (a anotação manual, que é o que habilita este caminho).
**Papel no artigo:** corredor por fora (ver [00](00-protocolo-comparacao.md))

## Hipótese

Um LLM lê o artigo inteiro e devolve JSON com os slots epidemiológicos, pegando o
que regra e regex não pegam: contagem dita em prosa, localidade implícita,
negação, atribuição a fonte. Isso permitiria reconstruir uma série de casos
*reportados na imprensa*, que é o slot mais valioso e mais difícil.

## O que produz

Um registro por artigo com os campos do schema, agregado por UF (ou BR) × EW:

`disease` · `location` · `incident_type` (novo/total) · `count` (casos/óbitos) ·
`severity` · `intervention` · `outbreak` (flag) · `event_date`

Reaproveitar o schema do Health Sentinel (*Disease, Location, Incident,
Incident-Type, Number*) para permitir comparação direta com a literatura.

## Como testar

1. **Pesos abertos e locais**, não API: Qwen2.5-14B/72B-Instruct ou
   Llama-3.3-70B-Instruct. Motivo: reprodutibilidade.
2. Schema JSON estrito + 4–8 exemplos few-shot.
3. Validar contra a **mesma amostra anotada à mão** do caminho 01 — anotar uma vez,
   usar nos dois braços. Medir precisão/recall/F1 por campo e exact-match.
4. Rodar o protocolo 00.

## Evidência

- [Consoli 2024, ICICT, arXiv:2408.14277](https://arxiv.org/abs/2408.14277):
  8 LLMs + ensemble vs. baseline EpiTator para doença/país/data/contagens em
  ProMED e WHO DON; GPT-4-32k melhor no geral (F1 0,814).
- [Consoli 2025, *Sci Data* 12:970](https://doi.org/10.1038/s41597-025-05276-2) —
  **verificado**: ensemble de Mistral-7B-OpenOrca, Zephyr-7B-Beta e Llama-3-70B com
  *majority voting* extrai doença/país/data/casos/óbitos de >3.000 WHO DONs →
  **~2,9 mil eventos** em knowledge graph RDF/OWL; o ensemble supera GPT comercial
  em F1.
- **Valor preditivo:** Paudyal 2026 (DATA/SciTePress,
  [doi:10.5220/0015231400004091](https://doi.org/10.5220/0015231400004091)):
  Qwen2.5-14B local extrai sinais de 85k notícias multilíngues; os sinais de mídia
  **precedem** as notificações oficiais (WAHIS) em ~13–14 dias (mediana).
- Health Sentinel 2025 (NLP4PI, ACL): pipeline híbrido em produção com schema JSON
  estrito; few-shot sobe F1 de 0,59 para 0,68.

**Contra-evidência que precisa estar no artigo:**

- **Números são o elo fraco.** Em dengue no ProMED, GPT-4 zero-shot chega a F1
  0,882 mas TextCNN/LSTM alcançam 0,998 (Lin 2025, IEA/AIE,
  [doi:10.1007/978-981-96-8892-0_15](https://doi.org/10.1007/978-981-96-8892-0_15)).
  Tratar contagem extraída como ruidosa; preferir features de menção/volume/gravidade.
- Restrição de formato pode degradar raciocínio —
  [Tam 2024, EMNLP Industry](https://doi.org/10.18653/v1/2024.emnlp-industry.91)
  (**já está no `references.csv`**). Há réplica publicada contestando o desenho;
  citar como debate aberto.

## O que mudou em 2026-11-21 — a fronteira se encheu

Uma checagem por busca (não revisão sistemática) mostrou que **"LLM + texto +
previsão de doença" deixou de ser lacuna**. Entre 2025 e 2026 apareceu um conjunto
de trabalhos que fazem esse encadeamento:

| Trabalho | Doença | Fonte do texto | Como o texto entra |
|---|---|---|---|
| **Ye et al. 2026**, *IEEE Access* ([doi:10.1109/ACCESS.2026.3733491](https://doi.org/10.1109/ACCESS.2026.3733491)) | Respiratórias | **Notícia epidemiológica**, políticas, variantes | Llama3-8B funde série e contexto textual; tem módulo de **filtragem de texto** e ablação |
| **Auditable Context-Aware HFMD Forecasting** (arXiv:2511.23276) | Mão-pé-boca | Calendário escolar, relatórios de governo, diretrizes | Agente LLM produz um **sinal escalar** de impacto, combinado à contagem de casos; previsão semanal probabilística; baselines ARIMA, Prophet, Chronos, Moirai, TimesFM |
| **IEEE SERA 2026** ([doi:10.1109/SERA69989.2026.11618672](https://doi.org/10.1109/SERA69989.2026.11618672)) | COVID-19 | Tweets | Resumos diários por LLM → modelo de previsão; −30% no MAE de mortes |
| **"From News to Forecast"** (NeurIPS 2024, arXiv:2409.17515) | Nenhuma (domínio geral) | Notícia | LLM filtra notícia irrelevante e alinha ao movimento da série |

**O que isso muda para o caminho 04:** a extração por LLM **não é fonte de novidade
por si**. Usar um LLM porque é um LLM, em 2026, é o padrão da área. Se este caminho
entrar, entra como **uma representação entre várias** sob a mesma régua (léxico,
embeddings, tópicos, LLM) — nunca como a contribuição do paper.

**O que continua sem resposta medida — e é o que o paper mede:**

- **Dengue como alvo.** Todos os trabalhos acima são COVID, influenza, respiratórias
  ou HFMD. Nenhum é dengue.
- **Notícia em português, do Brasil.** Nenhum.
- **O texto como bloco de feature ao lado de clima e busca, sob a mesma régua e com
  baseline forte.** Os trabalhos acima põem o texto *dentro* do LLM (como contexto
  no prompt); ninguém o compara como bloco ablatável, com a persistência como referência.
- **O controle negativo** (texto embaralhado e texto constante). O Ye et al. filtra
  texto por relevância e abla presença — não testa se o sinal é real ou ruído.

**Ressalva:** a checagem foi por busca, e o corpus desta nota (10 artigos, cortado
por volume de citações) **não cobriria nada disso por construção** — que é
a limitação que a seção de seleção dos relatórios declara. Fechar a
pergunta com rigor pede varredura sistemática, que **não foi feita**.

## Decisão de 2026-11-21 — standby

O caminho **fica em standby, dependente do orçamento de tempo**. Não sai do
escopo, não entra na grade por ora. O que decide é o mesmo ponto de corte que o
[plano](plano.md) já tinha: **a anotação manual (passo 6) é o que habilita este
caminho** — o schema é compartilhado, e a validação do extrator por LLM usa a mesma
amostra anotada à mão do caminho 01. Se a anotação não fechar, o 04 fica de fora
sem levar novidade junto.

## Custo

Alto e volátil. Inferência local em 4.569 artigos é viável (algumas horas em GPU
de consumidor), mas: escolher e baixar o modelo, escrever e versionar o prompt,
validar a extração, e refazer tudo se o modelo mudar.

## Refs a registrar em `articles/references.csv`

`arXiv:2408.14277` · `10.1038/s41597-025-05276-2` · `10.5220/0015231400004091` ·
`10.1007/978-981-96-8892-0_15` · `10.18653/v1/2024.emnlp-industry.91` (já presente)

Da checagem de 2026-11-21 (entram no `references.csv` só se o caminho sair do
standby): `10.1109/ACCESS.2026.3733491` · `arXiv:2511.23276` ·
`10.1109/SERA69989.2026.11618672` · `arXiv:2409.17515`

## Pendências / próximo passo

- [ ] **Decidir se vale rodar** — em standby desde 2026-11-21, dependente do
      orçamento de tempo e do passo 6 (a anotação manual). Se rodar, entra como uma
      representação entre várias, não como a contribuição do paper.
- [ ] Se rodar: escolher o modelo local e **congelar** antes de qualquer extração.
- [ ] Definir o schema de anotação compartilhado com o caminho 01 antes de anotar.
- [ ] Considerar a cascata regra → LLM (ver [ideias-soltas](ideias-soltas.md)).
- [ ] **Varredura sistemática da fronteira 2025–2026** (LLM + texto + previsão de
      doença): a checagem foi por busca, e os quatro trabalhos acima são o que
      apareceu, não um censo. Fazer antes de o caminho sair do standby.
