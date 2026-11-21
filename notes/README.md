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
- **Quando** cada caminho entra e o que fica de fora é [plano.md](plano.md) — os
  caminhos dizem o estado, o plano diz a ordem e o prazo.
- Criar/atualizar à mão ou pela skill `research-notes`
  (`.claude/skills/research-notes/`).

## Índice

| # | Caminho | Papel | Estado |
|---|---------|-------|--------|
| — | [Plano de entrega](plano.md) | regra do prazo | ativo — 2026-11-20 |
| 00 | [Protocolo de comparação](00-protocolo-comparacao.md) | regra do jogo | rascunho |
| 01 | [Léxico PT-BR + regras](01-lexico-regras.md) | concorrente | testando |
| 02 | [Embeddings densos + pooling por EW](02-embeddings-densos.md) | concorrente | testando |
| 03 | [Topic modeling temporal](03-topic-modeling.md) | concorrente | testando |
| 04 | [Extração estruturada por LLM](04-llm-extracao-estruturada.md) | corredor por fora | standby — 2026-11-21 |
| 05 | [LLM como forecaster / agente](05-llm-forecaster.md) | corredor por fora | ideia |
| 06 | [Como a linha desenha o experimento](06-desenho-do-experimento.md) | apoio — baselines e modelo com citação | testando — 2026-11-21 |
| — | [Revisão de literatura](revisao-bibliografica.md) | resumo — o que a área fez, até onde chegou | ativo — 2026-11-21 |
| — | [Ideias soltas](ideias-soltas.md) | caixa de entrada | — |

## Decisões estruturais já tomadas

**2026-10-07 — os caminhos são concorrentes, não camadas.**
01, 02 e 03 são três *representações* do mesmo corpus de notícias. Cada uma gera
seu próprio conjunto de features e o artigo compara qual representa melhor a
notícia para prever dengue. Consequência: existe o [protocolo 00](00-protocolo-comparacao.md),
que fixa as condições da comparação. Sem ele a comparação não vale nada.

**2026-11-20 — o artigo é sobre o valor das features, não sobre a notícia.**
A entrada acima diz que "o artigo compara qual representa melhor a notícia para
prever dengue". **O sujeito estava errado.** O artigo pergunta se as **features
multimodais propostas carregam sinal relevante e quais vale a pena incluir**,
contra abordagens mais simples — notícia e boletins são **instâncias** de feature
multimodal, o mecanismo pelo qual a pergunta é respondida, não o assunto. Um texto
que se anuncie como "notícia prevê dengue" está respondendo outra pergunta.

Consequências, todas registradas no [protocolo 00](00-protocolo-comparacao.md):
01–03 continuam concorrentes **entre si**, mas agora como a comparação *dentro* do
conjunto de texto — uma escolha interna, não o eixo do artigo; e clima e busca
deixam de ser condições fixas para virar conjuntos comparados. A ordem e o prazo
estão em [plano.md](plano.md).

**2026-11-20 — o desenho vira comparação entre conjuntos acumulados, e a granularidade vira BR com UF declarada.**
A revisão do [protocolo 00](00-protocolo-comparacao.md) tirou clima e busca das
condições fixas e transformou os quatro blocos de feature em conjuntos: `histórico` →
`+ clima` → `+ busca` → `+ texto`, em dois tipos de modelo. O artigo reporta os três
ganhos entre conjuntos, não um número único; o conjunto de texto é comparado com
dois resultados — o conjunto anterior e o ensemble sem texto —, o que dá oito
comparações. Em
granularidade, **BR é o número principal e a UF é robustez declarada**: medida e
reportada, não "se der tempo", pelo mesmo motivo de antes — o corpus é de uma fonte
nacional e as linhas de UF são atribuição, não partição. Horizonte: **1 semana no
número principal, 4 semanas declarado**. Os baselines deixaram de ser invenção
nossa e ganharam citação (Xiao 2025, Johansson 2019, Wu 2025, Codeço 2018), com o
levantamento em [06](06-desenho-do-experimento.md). Decisões, custo e cortes em
[plano.md](plano.md) §10.

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
- Alvo: casos SINAN por semana epidemiológica (domingo), **BR no número principal e
  UF como robustez declarada**. O descompasso espacial, medido: o corpus é de **uma
  fonte nacional**, mas as tabelas de features têm **28 localidades** (BR + as 27
  UF), de 2002-02-17 a 2026-09-13. As linhas de UF são **atribuição por indicação
  locativa** no texto, não contagem por estado — um artigo que cita três estados
  conta nos três, então as linhas de UF somam 7.223 menções para 4.369 artigos
  nacionais e **não somam a linha BR**.
- **318 semanas do intervalo não têm artigo nenhum** e não aparecem na
  tabela: a linha BR tem 965 semanas com pelo menos um artigo num intervalo de
  1.283. Semana sem notícia é ausência de sinal, e o modelo precisa de um indicador
  explícito para não ler isso como sinal neutro.
- SINAN cobre 2014–2026; GT cobre **2020-01-26 a 2024-12-29**. O overlap dos três é
  curto: com 104 semanas mínimas de treino, a grade só é avaliável em
  **157 semanas** (2022-01-02 a 2024-12-29), e menos nos conjuntos que usam busca.
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
