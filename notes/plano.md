# Plano de entrega — paper de forecasting multimodal

**Entregável:** um paper. O programa não exige dissertação; o texto da dissertação
não é o produto.
**Prazo:** 2027-02-19 (13 semanas a partir de 2026-11-20).
**Pronto significa:** **manuscrito submetível**. Escolha de revista, formatação e
o processo de submissão ficam fora das 13 semanas.
**Orçamento:** ~12 h/semana em 2–3 sessões ≈ 150 h, das quais **~110 efetivas** —
as semanas 5 e 6 caem em Natal e Ano Novo, e este plano as trata como meio
período em vez de fingir que rendem uma semana cheia.
**Snapshot:** 2026-11-20.

Os caminhos em [00](00-protocolo-comparacao.md)–[05](05-llm-forecaster.md) dizem o
**estado** de cada frente. Este arquivo diz **quando**. Se os dois discordarem, o
estado é o fato e este plano está desatualizado — conserte este.

Rode `uv run python scripts/estado_do_plano.py` antes de mexer aqui. O plano é
**regerado** da medição, não digitado de memória; a skill `plano-entrega` é quem
faz o laço.

---

## 1. A afirmação do paper

> **Existe sinal relevante nas features multimodais propostas, e quais valem a
> pena incluir** — medido contra abordagens mais simples, sob o mesmo alvo e as
> mesmas métricas.

**A notícia não é o assunto.** Ela é uma instância de feature multimodal — o
mecanismo pelo qual a pergunta é respondida. O mesmo vale para os boletins. Um
texto que se anuncie como "notícia prevê dengue" está respondendo outra pergunta,
e é a que a revisão derruba primeiro.

A lacuna que isso cobre está medida em duas frentes da própria literatura lida:

- A ponte entre a literatura de representação (ganho medido em similaridade
  intrínseca, em inglês, sobre pares de frases curtas) e a de vigilância (que
  reduz notícia a contagem e quase nunca compara contra um baseline sem texto)
  **não foi construída** — [articles/embeddings/relatorio.md:71](../articles/embeddings/relatorio.md).
- **Nenhum trabalho liga o texto a um alvo preditivo**: "a extração é sempre por
  documento, nunca como série" — [articles/llm-extracao/relatorio.md:113](../articles/llm-extracao/relatorio.md).

## 2. Desenho: a escada dupla

Famílias de modelo × degraus de feature. A grade responde a pergunta porque separa
**o efeito da feature** do **efeito da arquitetura** — sem as duas famílias, um
ganho que só aparece na rede neural não distingue uma coisa da outra.

| Degrau | O que entra |
|---|---|
| `historico` | histórico do alvo (lags, sazonalidade) — o piso |
| `clima` | + ERA5 UF × EW |
| `busca` | + Google Trends |
| `texto` | + o bloco de texto (as representações de notícia) |

Duas famílias: **simples** (gradient boosting / regressão sobre features
tabulares) e **sequencial** (rede neural). A grade são 8 células.

**Consequência que veio do grill:** clima e busca **deixam de ser chão comum** e
passam a ser degraus sob teste. A tabela do chão comum no protocolo 00 ainda os
fixa como covariáveis — isso é uma contradição viva, e a fatia 1 a resolve.

**Dentro do bloco de texto**, as quatro representações (léxico, embeddings,
tópicos, extração por LLM) são comparadas — é o material que já existe pronto em
três quartos. O bloco responde "vale incluir texto?"; a comparação interna
responde "qual texto?".

**A grade final depende da fatia 1.** As quatro células de `clima` e `busca`, e a
metade da família simples, podem encolher conforme o que a literatura mostrar e o
que o calendário aguentar. Depois da fatia 1 este plano é **replanejado** — é o
modo `replanejar` da skill, com a grade deixando de ser incógnita.

## 3. Métrica e regra de decisão

**Métrica primária: WIS/CRPS.** MAE ao lado, secundária.

**Regra de decisão pré-declarada.** Um bloco "vale incluir" quando:

1. o ganho aparece **nas duas famílias**;
2. o intervalo exclui zero, no teste pareado sobre as semanas avaliadas;
3. o ganho passa de um **piso de tamanho declarado antes de olhar qualquer
   número** — o piso é fixado na fatia 2, junto com a régua, e não depois.

O piso é declarado cedo por um motivo: um limite escolhido depois de ver a tabela
não é um limite, é uma narrativa. E o número de comparações da grade é declarado
junto, para que a correção de comparações múltiplas seja decidida antes e não
depois de o resultado aparecer. Os dois ficam escritos no protocolo 00, que é o
documento onde as regras da comparação moram — não aqui, que é o documento do
prazo.

**A regra vale para os dois sinais.** Se nenhum bloco passar, isso é resultado, e
é publicável — desde que o controle negativo exista para provar que o teste foi
justo. Um nulo com desenho forte vale mais que um positivo com desenho frouxo.

## 4. Linha de corte

| Dentro | Fora (trabalho futuro declarado) |
|---|---|
| Alvo BR, horizonte 1 semana | Horizonte multi-passo |
| Quatro degraus × duas famílias; quatro representações dentro do bloco de texto | Representação par a par como degrau próprio |
| Ablação sem texto (é o degrau `historico`) e **controle negativo** | Leitura por UF — só se sobrar tempo; senão vira limitação declarada |
| Métricas pontuais **e** probabilísticas | Caminho 05 (LLM como previstor) |
| Notícia (EBC) como o corpus textual | Boletins do MoH — **default fora**, decisão adiada para a fatia 10 |

## 5. O que já existe — não refazer

| Peça | Onde | Estado |
|---|---|---|
| Régua: painel do alvo, rolling origin, métricas pontuais, run record | [src/forecast/](../src/forecast/README.md) | pronto, **sem quantis** |
| Barra ingênua medida | idem | MAE 4.047 (persistência) / 30.714 (sazonal) |
| Representações 01, 02 e 03 como tabelas EW | `data/pipeline/news/` | prontas |
| Corpus de texto congelado — 4.569 artigos | idem | pronto |
| Quatro famílias de literatura fichadas (23/37/48/10 artigos) | [articles/](../articles/README.md) | pronto — é o trabalho relacionado |
| Três seções de manuscrito em inglês | [texts/](../texts/README.md) | prontas |
| Voz de referência + linter de estilo | [notes/voz-de-referencia.md](voz-de-referencia.md) | pronto |

## 6. Caminho crítico e dependências

1. **A régua precisa emitir quantis** antes de qualquer célula da grade. Com WIS
   primária, o piso ingênuo também precisa de distribuição — hoje ele emite um
   número por semana. É pré-requisito, não detalhe: a barra do paper deixa de ser
   MAE 4.047 e passa a ser um WIS.
2. **A passada de literatura fecha a grade** — baselines que o campo reconhece
   (para a "abordagem mais simples" ter citação, não invenção) e as famílias de
   modelo usadas em fusão multimodal.
3. **A anotação manual é o relógio de calendário.** 150–200 artigos anotados à
   mão custam uma semana inteira do orçamento, é o único item que depende do
   *seu* tempo, e não paraleliza com o meu. Ela paga duas vezes: valida o léxico
   do degrau de texto e a extração por LLM.
4. **A revisão do protocolo** (clima e busca viram degraus) precisa entrar antes
   de o harness congelar.
5. **A prosa corre em paralelo, uma seção por semana.** Com 12 h/semana, escrever
   é metade do trabalho, e texto corrido no fim é onde a voz se perde.

**Restrição dura que o plano embute:** a Google Trends congelada termina em
**2024-12-29** e o alvo vai a 2026. Com 104 semanas mínimas de treino, a grade só
é avaliável onde as fontes coexistem: **~2022-01 a 2024-12, cerca de 150 semanas
pontuadas** — não as 557 da barra atual. Esse é o recorte do paper, e ele tem que
estar declarado no texto, não descoberto na revisão.

## 7. As fatias

Cada linha termina em algo que você consegue **conferir**. A coluna de prova diz
o que o script vai medir: um caminho, ou `caminho#marcador` quando o que prova a
fatia é o documento **dizer** algo novo. Se o artefato sair com outro nome,
corrija a prova — não deixe o ⬜ mentir.

O marcador tem que ser uma palavra que o documento **ainda não tem** — é isso que
faz dele uma prova. `#degrau` no protocolo só vira ✅ quando a revisão que
transforma clima e busca em degraus estiver escrita: hoje o protocolo não diz
"degrau" em lugar nenhum. Um marcador escolhido por engano, com palavra que o
documento já usa, fecha a fatia no dia em que ela nasce — e aí a medição inteira
perde o sentido.

A coluna de prosa fica vazia em quatro linhas, de propósito: a fatia 0 e a 1 são
de arrumação e leitura, e as semanas 5 e 6 são meio período. Fora elas, uma seção
por semana — com 12 h semanais, escrever é metade do trabalho e um texto corrido no
fim é onde a voz se perde.

Os artefatos de execução seguem uma convenção, para que a grade se nomeie sozinha:
`data/forecast/grid/<degrau>__<familia>_metrics.parquet`,
`data/forecast/texto/<representacao>__<familia>_metrics.parquet`,
`data/forecast/controle/<variante>_metrics.parquet`.

| # | Fecha em | Fatia | Prova que fechou | Prosa |
|---|---|---|---|---|
| 0 | 2026-11-21 | **Landar o que já existe** — a régua, as fichas, os relatórios e a voz de referência estão no disco e fora do git. Só fecha quando a lista de "fora do git" do relatório estiver vazia | `src/forecast/__init__.py` `tests/forecast/test_record.py` `notes/voz-de-referencia.md` `articles/topicos/relatorio.md` | — |
| 1 | 2026-11-27 | **A passada de literatura** — baselines consagrados + famílias de modelo para fusão multimoda; e a revisão do protocolo que tira clima e busca do chão comum | `notes/06-baselines-e-familias.md` `notes/00-protocolo-comparacao.md#degrau` | — |
| 2 | 2026-12-04 | **A régua em WIS e o piso declarado** — quantis para todo modelo, inclusive os dois ingênuos; o piso de tamanho e o número de comparações ficam registrados ANTES de qualquer célula da grade existir | `src/forecast/README.md#quantile` `notes/00-protocolo-comparacao.md#piso` | Métodos §régua |
| 3 | 2026-12-11 | **O piso da escada** — o degrau `historico` nas duas famílias; é o número que clima tem que bater | `data/forecast/grid/historico__simples_metrics.parquet` `data/forecast/grid/historico__sequencial_metrics.parquet` | Introdução |
| 4 | 2026-12-18 | **Clima e busca entram** — os dois degraus seguintes, nas duas famílias | `data/forecast/grid/clima__*_metrics.parquet` `data/forecast/grid/busca__*_metrics.parquet` | Trabalho relacionado: condensar as quatro famílias |
| 5 | 2026-12-25 | *meio período* — **o topo da escada**: o bloco de texto nas duas famílias | `data/forecast/grid/texto__*_metrics.parquet` | — |
| 6 | 2027-01-01 | *meio período* — **a anotação fechada**. É o relógio de calendário, e é o único artefato que não se regenera rodando nada: vai para o git | `data/news/reference/amostra_anotada.csv` `notes/07-anotacao-amostra.md` | — |
| 7 | 2027-01-08 | **Dentro do bloco de texto** — as quatro representações sob a regra de decisão | `data/forecast/texto/lexico__*_metrics.parquet` `data/forecast/texto/embeddings__*_metrics.parquet` `data/forecast/texto/topicos__*_metrics.parquet` | Resultados §a escada |
| 8 | 2027-01-15 | **O controle negativo** — texto embaralhado e texto constante no topo da escada. Se o erro não mudar, o texto não estava sendo usado | `data/forecast/controle/*_metrics.parquet` | Métodos §controle negativo |
| 9 | 2027-01-22 | **A estatística da afirmação** — teste pareado sobre as semanas, intervalo, correção pelo número de comparações, e a decisão da regra aplicada célula a célula | `data/forecast/comparacoes.parquet` | Resultados §o que vale incluir |
| 10 | 2027-01-29 | **A extração por LLM entra ou vira trabalho futuro** — decidido pelo estado da anotação, não por otimismo. Na mesma semana: a decisão adiada dos boletins | `data/forecast/texto/extracao__*_metrics.parquet` | Métodos §extração |
| 11 | 2027-02-05 | **Auditoria de vazamento e robustez** — janela sem o ano recorde, corte de pré-treinamento de cada encoder, sensibilidade ao piso | `src/forecast/README.md#leakage` | Limitações |
| 12 | 2027-02-12 | **O texto em uma peça**, depois do passe adversarial contra o próprio paper | `texts/multimodal_forecasting.md` | Discussão |
| 13 | 2027-02-19 | **Fechamento** — estilo, reprodução do zero, artefatos depositados | `texts/multimodal_forecasting.md#Disponibilidade` | — |

**Fatia 0 é hoje ou amanhã.** A régua, as quatro famílias de fichas e os relatórios
estão no disco e fora do git — o número exato está no relatório, e ele muda a cada
sessão. Trabalho que não foi landado não conta como progresso e fica em risco de se
perder; foi por isso que a medição parou de marcar ✅ em artefato que existe só no
disco.

## 8. Pontos de corte

Sem estes, o plano não falha de uma vez: falha devagar, e ninguém percebe até a
fatia 13. Cada um é uma data em que a decisão já está tomada.

| Na | Se | Então |
|---|---|---|
| 1 | a busca não fecha a lista de baselines | usa os quatro já listados no protocolo 00 e declara a lista provisória |
| 3 | o degrau `historico` não fecha nas duas famílias | a família que não fechar sai e o desenho deixa de ser duplo — **declarado como desvio**, nunca escondido |
| 5 | a grade não fecha até aqui | corta as células da família simples em `clima` e `busca`; mantém as duas famílias no topo, que é onde a afirmação vive |
| 6 | a anotação não fechou | a extração por LLM sai do paper; a amostra parcial vira evidência de trabalho futuro |
| 10 | boletins (decisão adiada para cá) | **default: fora.** Só entram se a grade fechou adiantada |
| 11 | a leitura por UF não fecha | BR é o número principal; o descompasso espacial vira limitação, como o protocolo já previa |
| 12 | o texto não está em uma peça | corta robustez, não o fechamento — texto corrido é o que a banca lê |

## 9. Riscos que este plano não resolve

- **A grade é o maior consumidor de tempo.** 8 células, mais a comparação interna
  do bloco de texto, mais o controle negativo. Cada uma é um refit em rolling
  origin. Se a família sequencial for pesada, ela come o orçamento — é por isso
  que o ponto de corte da fatia 3 existe.
- **Vazamento temporal.** E5 e BGE-M3 têm corte de pré-treinamento desconhecido e
  o corpus vai até 2026 — dengue 2024 foi recorde e está em toda parte.
- **Descompasso espacial.** Notícia é nacional, alvo é UF. É por isso que o número
  principal é BR.
- **Contagem acumulada.** Só 24% dos artigos declaram número de casos, e
  acumulado, não semanal. É o que a extração por LLM tenta recuperar — e é a mais
  frágil das quatro representações, segundo a própria literatura de extração.
- **Comparações múltiplas.** Uma grade com ~15 execuções e uma regra de decisão
  declarada exige declarar o número de comparações. Está na fatia 2 por isso.
- **Nenhum checkpoint externo por semanas.** O acompanhamento é de pouca
  interação. O substituto é o passe adversarial da fatia 12: eu ataco o próprio
  paper antes de escrever a discussão, procurando o que uma revisão procuraria.

## 10. Registro de decisões

Do grill de 2026-11-20, para que daqui a seis semanas o raciocínio esteja aqui e
não na memória de ninguém:

| Decisão | Data |
|---|---|
| O entregável é um paper; a dissertação não é exigida | 2026-11-20 |
| A tese é o valor de features multimodais, não a notícia | 2026-11-20 |
| Desenho de escada dupla (modelos × features) | 2026-11-20 |
| Clima e busca deixam de ser chão comum | 2026-11-20 |
| WIS/CRPS primária, MAE secundária | 2026-11-20 |
| Ganho nas duas famílias, intervalo excluindo zero, piso declarado antes | 2026-11-20 |
| Só o caminho 04 entra; 05 é trabalho futuro | 2026-11-20 |
| Boletins: default fora, decisão na fatia 10 | 2026-11-20 |
| Prazo 2027-02-19; pronto = manuscrito submetível | 2026-11-20 |

## 11. Como este arquivo se mantém

A skill `plano-entrega`, no laço semanal. Ela **mede** o repositório com
`scripts/estado_do_plano.py` — quais provas de fatia existem, o que está fora do
git, o estado de cada caminho, os estágios da régua, as fichas — e só então
compara com esta tabela e reescreve.

O plano é **regerado** da medição, não digitado. Um plano escrito à mão hoje mente
na semana que vem, e um plano que mente é pior que nenhum: é a mesma lição que já
está em [.claude/workflows/familias/README.md](../.claude/workflows/familias/README.md)
— configuração que só existe na conversa é memória, não configuração.
