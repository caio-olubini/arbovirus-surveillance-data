# Plano de entrega — paper de previsão multimodal

**O que fica pronto:** um paper. O programa não exige dissertação.
**Prazo:** 2027-02-19, que são 13 semanas a partir de 2026-11-20.
**Pronto quer dizer:** manuscrito pronto para submeter. Escolher a revista,
formatar e submeter ficam fora dessas 13 semanas.
**Tempo disponível:** cerca de 12 h por semana, em 2 ou 3 sessões. As semanas 5 e 6
caem no Natal e no Ano Novo, então este plano as trata como meio período, e não
como se rendessem uma semana cheia.
**Data desta versão:** 2026-11-20.

Os arquivos [00](00-protocolo-comparacao.md) a [05](05-llm-forecaster.md) dizem em
que **estado** está cada frente de pesquisa. Este arquivo diz **quando** cada uma
entra. Se os dois discordarem, o estado é o fato e este plano está desatualizado.

Antes de mexer aqui, rode `uv run python scripts/estado_do_plano.py`. O plano é
reescrito a partir dessa medição, não de memória — a skill `plano-entrega` faz
esse ciclo toda semana.

---

## 0. Visão macro

Medido em **2026-11-20** por `scripts/estado_do_plano.py`, que é quem decide o que
existe no disco e no git. A skill reescreve esta seção a cada semana, da mesma
medição que reescreve a tabela do §7.

**Fechadas: 1 das 14.** A fatia 0 — colocar no git o que já existe. Fechou um dia
antes do prazo.

**Pela metade: 1.** A fatia 1, o levantamento de literatura. A nota
[06](06-desenho-do-experimento.md) existe e ainda está fora do git, e a revisão do
protocolo 00 que tira clima e busca das condições fixas não foi escrita.

**Não começaram: 12.** As fatias 2 a 13, na ordem da tabela do §7. Cada uma existe
porque a anterior fechou, e a ordem não é preferência: começar pela 9 sem ter a 3
não produz nada.

**Agora:** a fatia 1, que fecha em 2026-11-27.

## 1. A pergunta do paper

> As features multimodais propostas carregam sinal relevante? Quais delas valem a
> pena incluir?

A comparação é sempre contra uma abordagem mais simples, com o mesmo alvo e as
mesmas métricas.

**A notícia não é o assunto do paper.** Ela é uma das features multimodais — o
meio de responder à pergunta, não a pergunta. O mesmo vale para os boletins do
Ministério da Saúde. Um texto que se apresente como "notícia prevê dengue" está
respondendo outra pergunta, e é a primeira que uma revisão derruba.

A lacuna que isso cobre está medida na própria literatura já fichada neste
repositório:

- O texto é sempre extraído por documento, nunca como série ao longo do tempo —
  [articles/llm-extracao/relatorio.md:113](../articles/llm-extracao/relatorio.md).
- Nada liga a qualidade de uma representação de texto a um alvo de previsão: os
  ganhos medidos são de similaridade entre frases curtas, em inglês —
  [articles/embeddings/relatorio.md:71](../articles/embeddings/relatorio.md).

## 2. O desenho do experimento

Dois eixos, e só eles variam entre as comparações.

**Tipo de modelo** — dois: *simples* (gradient boosting ou regressão sobre
features tabulares) e *sequencial* (rede neural).

**Conjunto de features** — quatro, cada um somando um bloco ao anterior:

| Conjunto | O que entra |
|---|---|
| `histórico` | lags e sazonalidade do próprio alvo |
| `+ clima` | ERA5 por unidade federativa e semana epidemiológica |
| `+ busca` | Google Trends |
| `+ texto` | a representação de notícia escolhida |

São 8 combinações: 2 tipos de modelo × 4 conjuntos de features.

**Por que dois tipos de modelo.** Com um só, um ganho que aparece apenas na rede
neural não distingue *a feature ajudou* de *a arquitetura é melhor*. Se o ganho
aparece nos dois, ele vem da feature.

**Mudança em relação ao protocolo atual.** Clima e busca hoje são condições fixas,
iguais em todos os braços. Passam a ser **conjuntos comparados**, porque a pergunta
do paper é quais features vale a pena incluir. Isso exige uma revisão do protocolo
00, que entra na fatia 1.

**Dentro do conjunto `+ texto`**, as quatro representações — léxico, embeddings,
tópicos e extração por LLM — são comparadas entre si. O conjunto responde "vale
incluir texto?"; a comparação interna responde "qual texto?".

**A lista final de modelos depende da fatia 1.** O levantamento de literatura
define quais comparações o campo já reconhece e que tipos de modelo são usados para
combinar modalidades. Até lá, esta seção é um rascunho.

## 3. Métrica e regra de decisão

**Métrica principal: WIS/CRPS**, que pontua a distribuição prevista, e não só o
valor central. MAE fica ao lado, como métrica secundária.

**Regra de decisão.** Um conjunto de features vale a pena incluir quando:

1. o ganho aparece nos **dois tipos de modelo**;
2. o intervalo de confiança do ganho, numa comparação pareada por semana, não
   inclui o zero;
3. o ganho passa de um **valor mínimo** fixado antes de os resultados existirem.

O valor mínimo e o número de comparações da grade ficam registrados no protocolo 00
na semana 2, antes de a primeira combinação ser calculada.

**A regra vale nos dois sentidos.** Se nenhum conjunto passar, esse é o resultado,
e ele é publicável — desde que o controle negativo da semana 8 mostre que o teste
foi justo. Um resultado nulo com desenho correto vale mais que um positivo com
desenho fraco.

## 4. O que fica de fora

O §8 diz, para cada item condicional desta tabela, a data e a condição em que ele
sai ou entra. Aqui está só o que fica de fora.

| Dentro | Fora, declarado como trabalho futuro |
|---|---|
| Alvo Brasil, horizonte de 1 semana | Horizonte de várias semanas |
| 2 tipos de modelo × 4 conjuntos de features; 4 representações de texto | Cada representação de texto como conjunto próprio |
| O conjunto `histórico` faz o papel de ablação sem texto; há controle negativo | Leitura por unidade federativa — decisão na semana 11 |
| Métricas pontuais **e** probabilísticas | O caminho 05, LLM como previstor |
| Notícia da EBC como corpus de texto | Boletins do Ministério da Saúde — decisão na semana 10 |

## 5. O que já existe

| Peça | Onde | Estado |
|---|---|---|
| Avaliador (chamado de "régua" no protocolo 00): painel do alvo, rolling origin, métricas pontuais, registro de cada execução | [src/forecast/](../src/forecast/README.md) | pronto, **sem distribuições** |
| Barra ingênua medida | idem | persistência 4.047 casos por semana; ingênuo sazonal 30.714 |
| Representações de notícia (braços 01, 02 e 03) como tabelas por semana epidemiológica | `data/pipeline/news/` | prontas |
| Corpus de texto congelado: 4.569 artigos | idem | pronto |
| Quatro famílias de literatura fichadas (23, 37, 48 e 10 artigos) | [articles/](../articles/README.md) | prontas; é o trabalho relacionado |
| Três seções de manuscrito em inglês | [texts/](../texts/README.md) | prontas |
| Amostra de voz para calibrar o medidor de estilo | [notes/voz-de-referencia.md](voz-de-referencia.md) | pronta |

## 6. Ordem de dependências

1. **O avaliador precisa emitir distribuições antes de qualquer outro cálculo.**
   Com WIS como métrica principal, até os modelos ingênuos precisam prever uma
   distribuição. Hoje eles emitem um número por semana.
2. **O levantamento de literatura fecha a lista de modelos** — quais comparações o
   campo já reconhece, para a "abordagem mais simples" ter citação em vez de ser
   inventada.
3. **A anotação manual depende só de você.** De 150 a 200 artigos anotados à mão
   custam uma semana inteira do tempo disponível, e não dá para fazer em paralelo
   com o resto. Ela serve duas vezes: valida o léxico do braço 01 e a extração por
   LLM do caminho 04.
4. **A revisão do protocolo 00** precisa entrar antes de o avaliador ser congelado.
5. **A escrita corre em paralelo, uma seção por semana.** Com 12 h por semana,
   escrever é metade do trabalho. Deixar tudo para o fim é o que perde a voz.

**Restrição de calendário que o plano já assume.** A extração do Google Trends
congelada termina em 2024-12-29, e o alvo vai até 2026. Com 104 semanas mínimas de
treino, a grade só pode ser avaliada onde as fontes coexistem: de janeiro de 2022 a
dezembro de 2024, cerca de **150 semanas pontuadas**, e não as 557 da barra atual.
Esse é o recorte do paper, e ele precisa estar escrito no texto.

## 7. As fatias

Cada linha termina em algo que você consegue conferir. A coluna de prova diz o que
o script vai medir: um caminho de arquivo, ou `caminho#palavra` quando o que prova
a fatia é o documento passar a dizer algo novo. A palavra depois do `#` precisa ser
uma palavra que o documento **ainda não tem** — é isso que faz dela uma prova.
`#comparados` no protocolo 00 só acende quando a revisão que transforma clima e
busca em conjuntos comparados estiver escrita; uma palavra que o documento já usa
fecharia a fatia no dia em que ela nasceu.

A coluna `Prosa` fica vazia em quatro linhas, de propósito: as semanas 0 e 1 são de
arrumação e leitura, e as semanas 5 e 6 são meio período. Fora elas, uma seção
escrita por semana.

Os resultados ficam em arquivos nomeados pelo que são:
`data/forecast/grid/<conjunto>__<tipo-de-modelo>_metrics.parquet`,
`data/forecast/texto/<representacao>__<tipo-de-modelo>_metrics.parquet` e
`data/forecast/controle/<variante>_metrics.parquet`.

| # | Fecha em | Fatia | Prova que fechou | Prosa |
|---|---|---|---|---|
| 0 | 2026-11-21 | **Colocar no git o que já existe** — o avaliador, as fichas e os relatórios estão no disco e fora do git. Fecha quando não sobrar nenhum arquivo fora do git | `src/forecast/__init__.py` `tests/forecast/test_record.py` `notes/voz-de-referencia.md` `articles/topicos/relatorio.md` | — |
| 1 | 2026-11-27 | **Levantamento de literatura: baselines e tipos de modelo** — quais comparações o campo já reconhece, e a revisão do protocolo que tira clima e busca das condições fixas | `notes/06-desenho-do-experimento.md` `notes/00-protocolo-comparacao.md#comparados` | — |
| 2 | 2026-12-04 | **O avaliador em WIS, e o ganho mínimo declarado** — distribuições para todos os modelos, inclusive os dois ingênuos; o ganho mínimo e o número de comparações ficam registrados antes de existir qualquer resultado | `src/forecast/README.md#quantile` `notes/00-protocolo-comparacao.md#mínimo` | Métodos §avaliação |
| 3 | 2026-12-11 | **A base: só histórico, nos dois tipos de modelo** — é o resultado que clima e busca precisam superar | `data/forecast/grid/historico__simples_metrics.parquet` `data/forecast/grid/historico__sequencial_metrics.parquet` | Introdução |
| 4 | 2026-12-18 | **Clima e busca entram** — os dois conjuntos seguintes, nos dois tipos de modelo | `data/forecast/grid/clima__*_metrics.parquet` `data/forecast/grid/busca__*_metrics.parquet` | Trabalho relacionado: juntar as quatro famílias |
| 5 | 2026-12-25 | *meio período* — **Texto entra**: o quarto conjunto, nos dois tipos de modelo | `data/forecast/grid/texto__*_metrics.parquet` | — |
| 6 | 2027-01-01 | *meio período* — **A anotação manual termina** — 150 a 200 artigos anotados à mão. É o único artefato que não se refaz rodando código, então vai para o git | `data/news/reference/amostra_anotada.csv` `notes/07-anotacao-amostra.md` | — |
| 7 | 2027-01-08 | **Qual representação de texto** — léxico, embeddings, tópicos e extração, sob a mesma regra de decisão | `data/forecast/texto/lexico__*_metrics.parquet` `data/forecast/texto/embeddings__*_metrics.parquet` `data/forecast/texto/topicos__*_metrics.parquet` | Resultados §conjuntos de features |
| 8 | 2027-01-15 | **Controle negativo** — texto embaralhado e texto constante no conjunto `+ texto`. Se o erro não mudar, o modelo não estava usando o texto | `data/forecast/controle/*_metrics.parquet` | Métodos §controle negativo |
| 9 | 2027-01-22 | **O teste estatístico** — comparação pareada por semana, intervalo de confiança, correção para o número de comparações, e a regra aplicada a cada combinação | `data/forecast/comparacoes.parquet` | Resultados §o que vale incluir |
| 10 | 2027-01-29 | **A extração por LLM entra ou fica de fora** — decidido pelo estado da anotação, não por otimismo. Na mesma semana, a decisão adiada sobre os boletins | `data/forecast/texto/extracao__*_metrics.parquet` | Métodos §extração |
| 11 | 2027-02-05 | **Vazamento de dados e robustez** — janela sem 2024, data de corte de cada codificador de texto, sensibilidade ao ganho mínimo | `src/forecast/README.md#leakage` | Limitações |
| 12 | 2027-02-12 | **O texto inteiro, em uma peça** — depois de uma revisão adversarial contra o próprio paper | `texts/multimodal_forecasting.md` | Discussão |
| 13 | 2027-02-19 | **Fechamento** — estilo, reprodução do zero, artefatos depositados | `texts/multimodal_forecasting.md#Disponibilidade` | — |

## 8. Pontos de corte

Cada ponto de corte decide de antemão o que sai do escopo, na data em que a decisão
importa. Sem eles, o corte acontece no fim, quando não há mais tempo.

| Na semana | Se | Então |
|---|---|---|
| 1 | o levantamento não fecha a lista de baselines | usa os quatro já listados no protocolo 00 e declara a lista como provisória |
| 3 | o conjunto `histórico` não fecha nos dois tipos de modelo | o tipo de modelo que não fechar sai, e o desenho deixa de ser duplo — registrado como desvio, não escondido |
| 5 | a grade não fecha até aqui | corta as combinações do modelo simples em `+ clima` e `+ busca`; mantém os dois tipos de modelo no conjunto `+ texto`, que é onde a pergunta do paper é respondida |
| 6 | a anotação não terminou | a extração por LLM sai do paper; a amostra parcial vira evidência para trabalho futuro |
| 10 | boletins do Ministério da Saúde, decisão adiada para cá | fora por padrão. Só entram se a grade fechou antes do prazo |
| 11 | a leitura por unidade federativa não fecha | o Brasil é o número principal e o descompasso espacial vira limitação declarada, como o protocolo já previa |
| 12 | o texto não está em uma peça | corta a robustez, não o fechamento: o texto corrido é o que a banca lê |

## 9. Riscos

- **A grade é o que mais consome tempo.** São 8 combinações, mais a comparação
  interna do conjunto de texto, mais o controle negativo. Cada uma exige reajustar
  o modelo em várias origens de previsão. Se o modelo sequencial for pesado, o
  ponto de corte da semana 3 é o que evita perder o prazo.
- **Vazamento de dados.** Os codificadores de texto têm data de corte de
  treinamento desconhecida, e o corpus vai até 2026. 2024 foi o ano recorde de
  dengue e está em toda parte.
- **Descompasso espacial.** A notícia é nacional e o alvo é por unidade federativa.
  Por isso o número principal é o Brasil.
- **Contagem acumulada.** Só 24% dos artigos declaram número de casos, e o número é
  acumulado, não semanal. É o que a extração por LLM tenta recuperar, e é a mais
  frágil das quatro representações.
- **Comparações múltiplas.** Cerca de 15 execuções na grade. Um ganho que aparece
  em uma delas por acaso é o positivo falso que o §3 e a fatia 9 existem para
  barrar.
- **Nenhum checkpoint externo.** O acompanhamento é de pouca interação. O que
  substitui é a revisão adversarial da semana 12, em que eu ataco o próprio paper
  procurando o que uma revisão procuraria.

## 10. Registro de decisões

Todas as decisões de escopo deste plano foram tomadas em **2026-11-20**, na sessão
de levantamento, e o conteúdo de cada uma está escrito nas seções acima — a
pergunta no §1, os dois eixos e a mudança de clima e busca no §2, a métrica e a
regra no §3, o que fica de fora no §4, o prazo no cabeçalho.

Este registro existe para **datar** a decisão, não para repeti-la. Decisão nova
entra aqui com a data, e é ela que muda o plano de forma; o resto é consequência.

**2026-11-20 — o ensemble entra como comparação obrigatória.** O levantamento de
literatura ([06](06-desenho-do-experimento.md)) mostrou que o campo trata o
ensemble como o adversário de verdade — ele vence em 180+ localidades
(Johansson 2019; Wu 2025) — e o protocolo 00 não o tinha. Custo baixo: é a média
das células da grade.

## 11. Como este arquivo se mantém

A skill `plano-entrega`, no ciclo semanal. Ela roda
`scripts/estado_do_plano.py` para medir quais provas de fatia existem, o que está
fora do git, o estado de cada frente em `notes/`, os estágios do avaliador, as
fichas de cada família de literatura e os produtos em `data/`. Só depois de medir
ela compara com esta tabela e reescreve.

Um plano escrito à mão fica desatualizado em uma semana. A mesma regra vale para as
configurações da revisão de literatura, que moram em
[.claude/workflows/familias/](../.claude/workflows/familias/README.md) em vez de
morar na conversa.
