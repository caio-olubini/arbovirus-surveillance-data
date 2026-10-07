# 04 — Extração estruturada por LLM

**Estado:** ideia — 2026-10-07
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

## Custo

Alto e volátil. Inferência local em 4.569 artigos é viável (algumas horas em GPU
de consumidor), mas: escolher e baixar o modelo, escrever e versionar o prompt,
validar a extração, e refazer tudo se o modelo mudar.

## Refs a registrar em `articles/references.csv`

`arXiv:2408.14277` · `10.1038/s41597-025-05276-2` · `10.5220/0015231400004091` ·
`10.1007/978-981-96-8892-0_15` · `10.18653/v1/2024.emnlp-industry.91` (já presente)

## Pendências / próximo passo

- [ ] Decidir se vale rodar no escopo da dissertação ou deixar como trabalho futuro.
- [ ] Se rodar: escolher o modelo local e **congelar** antes de qualquer extração.
- [ ] Definir o schema de anotação compartilhado com o caminho 01 antes de anotar.
- [ ] Considerar a cascata regra → LLM (ver [ideias-soltas](ideias-soltas.md)).
