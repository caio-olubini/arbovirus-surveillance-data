# notes/ — tracking de ideias de pesquisa

Caderno de trabalho do ARBOILI. **Não** é prosa de artigo (isso é `texts/`), **não**
é bibliografia curada (isso é `articles/references.csv`). É onde os caminhos de
pesquisa ficam registrados com contexto suficiente para retomar a discussão meses
depois sem depender da memória de ninguém.

Regra de ouro: se daqui a seis meses você ler o arquivo e não souber *o que era*,
*por que importava* e *qual era o próximo passo*, o arquivo está mal escrito.

## Como usar

- Um arquivo por caminho de pesquisa, numerado.
- Estado: `ideia` → `testando` → `decidido` | `descartado`. Toda mudança leva data.
- Ideia que ainda não é caminho vai para [ideias-soltas.md](ideias-soltas.md).
- Criar/atualizar à mão ou pela skill `research-notes`
  (`.claude/skills/research-notes/`).

## Índice

| # | Caminho | Papel | Estado |
|---|---------|-------|--------|
| 00 | [Protocolo de comparação](00-protocolo-comparacao.md) | regra do jogo | rascunho |
| 01 | [Léxico PT-BR + regras](01-lexico-regras.md) | concorrente | testando |
| 02 | [Embeddings densos + pooling por EW](02-embeddings-densos.md) | concorrente | testando |
| 03 | [Topic modeling temporal](03-topic-modeling.md) | concorrente | testando |
| 04 | [Extração estruturada por LLM](04-llm-extracao-estruturada.md) | corredor por fora | ideia |
| 05 | [LLM como forecaster / agente](05-llm-forecaster.md) | corredor por fora | ideia |
| — | [Ideias soltas](ideias-soltas.md) | caixa de entrada | — |

## Decisões estruturais já tomadas

**2026-10-07 — os caminhos são concorrentes, não camadas.**
01, 02 e 03 são três *representações* do mesmo corpus de notícias. Cada uma gera
seu próprio conjunto de features e o artigo compara qual representa melhor a
notícia para prever dengue. Consequência: existe o [protocolo 00](00-protocolo-comparacao.md),
que fixa o chão comum. Sem ele a comparação não vale nada.

**2026-10-07 — notícia não é proxy de casos.**
O enquadramento é modalidade de **atenção midiática / ambiente informacional**,
com controle explícito. Motivo: cobertura *segue* a curva epidêmica, e há
evidência de que cobertura chega a alterar a contagem notificada. Escrever
"news como proxy de casos" convida a rejeição do revisor.

**2026-10-07 — corpus congelado, braços paralelos.**
01, 02 e 03 vivem em `src/pipeline/news/`, um subdiretório por braço, e os três
leem a **mesma** tabela de texto congelada (`arboili transform news-text` →
`data/pipeline/news/EBC_dengue_text.parquet`). Nenhum braço re-parseia HTML: o
solo sob a comparação tem que ser fixo, senão a comparação não isola a
representação. O que é comum a todos (extração, normalização de acento,
calendário EW) fica em `src/pipeline/news/common.py` — biblioteca compartilhada,
não camada de modelo. Granularidade: **BR e por UF** onde fizer sentido.

## Fatos do corpus que restringem tudo

- 4.569 artigos, Agência Brasil, query `dengue`, 2002–2026, PT-BR. Corpus de
  texto congelado e versionado pelo pipeline (`src/pipeline/news/README.md` §1);
  os HTMLs crus ficam em `data/news/dengue/articles/` (não versionados).
- 4,7 artigos/semana no total nacional; 3,5/semana na janela 2020–2024. Fonte
  **única**, **estatal**, cobertura **nacional**.
- Alvo: casos SINAN por UF × semana epidemiológica (domingo). Notícia é nacional,
  alvo é UF — o descompasso espacial é uma limitação declarada, não um detalhe.
- SINAN cobre 2014–2026; GT cobre 2020–2024. O overlap dos três é curto.
- **O corpus atravessa duas gerações de template** (redesign ~2014, que coincide
  com o início da cobertura do SINAN). Era B (2002–2014) põe o corpo em
  `div.inside` e o nome do site no `<h1>`; era C (2014–2026) usa
  `div.node-conteudo` e o título real no `<h1>`. Tratar as duas como uma só
  produziu dois bugs silenciosos — ver `src/pipeline/news/README.md` §1.
- **Não é monolíngue.** 171 artigos (3,7%) são espanhóis, concentrados em 2016
  (61) e 2002 (24) — falta que cai em ano de epidemia. `lang_guess` é coluna do
  corpus e o braço 01 filtra para `pt`.
- **Contagens são acumuladas, não semanais**, e só 24% dos artigos declaram
  alguma. Os fatos completos, medidos, estão em `src/pipeline/news/README.md` §4.
