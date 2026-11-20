# Plano de entrega — paper de previsão multimodal

**O que fica pronto:** um paper. O programa não exige dissertação.
**Prazo:** 2027-02-19, 13 semanas a partir de 2026-11-20.
**Pronto quer dizer:** manuscrito pronto para submeter. Escolher a revista,
formatar e submeter ficam fora dessas 13 semanas.
**Tempo:** cerca de 12 h por semana, em 2 ou 3 sessões. As semanas 5 e 6 caem no
Natal e no Ano Novo, então contam meio período.
**Versão desta lista:** 2026-11-20.

## Como esta lista funciona

- **A lista abaixo é a fonte da verdade.** A ordem é sequencial: cada passo
  assume o anterior fechado.
- **O status é decisão humana, e só vale preenchido por você**, ou por ordem
  explícita sua. Nada está pronto até você marcar — nem o que já existe no disco.
  Nenhum script, medição ou agente decide status.
- Uma tarefa fecha quando a linha de confirmação se verifica. A confirmação é um
  caminho de arquivo, ou `caminho#palavra` — aí o que se confere é o documento
  passar a **dizer** algo que ainda não diz.

## A lista

### Passo 0 — Colocar no git o que já existe · até 2026-11-21

- [ ] commitar o avaliador, as fichas das quatro famílias e os relatórios —
      confirma: esses caminhos fora do `git status`
- [ ] commitar o levantamento de literatura e a revisão do protocolo 00 —
      confirma: idem

### Passo 1 — Conferir o levantamento de literatura · até 2026-11-27

- [ ] ler [06](06-desenho-do-experimento.md) e decidir o que fica — confirma: as
      cinco fontes marcadas como não verificadas ficam resolvidas ou cortadas
- [ ] conferir a revisão do protocolo 00: clima e busca saíram das condições
      fixas, viraram conjuntos comparados; 8 células; oito comparações —
      confirma: `00-protocolo-comparacao.md` aceito ou corrigido por você

### Passo 2 — O avaliador fechado · até 2026-12-04

- [ ] conferir o avaliador como ele está hoje — painel do alvo (BR e por UF),
      rolling origin, métricas pontuais, janela de pontuação, registro de execução
- [ ] distribuições para todos os modelos, inclusive os dois ingênuos —
      confirma: `src/forecast/README.md#quantile`
- [ ] valor mínimo do ganho registrado no protocolo 00, antes de existir
      resultado — confirma: `00-protocolo-comparacao.md#mínimo`
- [ ] Métodos §avaliação escrito

### Passo 3 — Os quatro baselines que faltam · até 2026-12-11

- [ ] conferir os dois ingênuos já medidos na janela do paper — confirma:
      `data/forecast/dengue_br_h1_metrics.parquet`
- [ ] SARIMA e SARIMAX com busca — confirma: `data/forecast/baselines/*.parquet`
- [ ] só-busca — confirma: idem
- [ ] InfoDengue, com prazo de uma semana; se não convergir, vira citação do
      sistema original e o desvio fica registrado — confirma: idem
- [ ] Introdução escrita

### Passo 4 — Só histórico, nos dois tipos de modelo · até 2026-12-18

- [ ] conjunto `histórico` no modelo simples e no sequencial — confirma:
      `data/forecast/grid/historico__*_metrics.parquet`
- [ ] Trabalho relacionado: juntar as quatro famílias de literatura

### Passo 5 — Clima e busca entram · meio período, até 2026-12-25

- [ ] conjunto `+ clima` nos dois tipos de modelo — confirma:
      `data/forecast/grid/clima__*_metrics.parquet`
- [ ] conjunto `+ busca` nos dois tipos de modelo — confirma:
      `data/forecast/grid/busca__*_metrics.parquet`

### Passo 6 — A anotação manual termina · meio período, até 2027-01-01

- [ ] 150 a 200 artigos anotados à mão — confirma:
      `data/news/reference/amostra_anotada.csv` e
      [07](07-anotacao-amostra.md)
- [ ] commitado: é o único artefato que não se refaz rodando código

### Passo 7 — Texto entra, e o ensemble sem texto · até 2027-01-08

- [ ] conjunto `+ texto` nos dois tipos de modelo — confirma:
      `data/forecast/grid/texto__*_metrics.parquet`
- [ ] ensemble sem texto, a segunda barra do `+ texto` — confirma:
      `data/forecast/ensemble/*_metrics.parquet`
- [ ] Resultados §conjuntos de features escrito

### Passo 8 — Qual representação de texto · até 2027-01-15

- [ ] léxico, embeddings (uma ou duas codificadoras) e tópicos sob a mesma regra
      — confirma: `data/forecast/texto/*_metrics.parquet`
- [ ] decisão sobre a extração por LLM, tomada pelo estado da anotação —
      confirma: decisão registrada, entrando ou ficando de fora
- [ ] Métodos §representações de texto escrito

### Passo 9 — Controle negativo · até 2027-01-22

- [ ] texto embaralhado e texto constante no conjunto `+ texto` — confirma:
      `data/forecast/controle/*_metrics.parquet`
- [ ] Métodos §controle negativo escrito

### Passo 10 — O teste estatístico · até 2027-01-29

- [ ] as oito comparações pareadas por semana, com correção para comparações
      múltiplas — confirma: `data/forecast/comparacoes.parquet`
- [ ] a regra de decisão aplicada a cada conjunto — confirma: idem
- [ ] Resultados §o que vale incluir escrito

### Passo 11 — Robustez declarada e vazamento · até 2027-02-05

- [ ] UF, horizonte de 4 semanas, janela sem 2024, 2020 dentro e fora, data de
      corte de cada codificadora, sensibilidade ao valor mínimo — confirma:
      `data/forecast/robustez/*_metrics.parquet` e `src/forecast/README.md#leakage`
- [ ] decisão sobre os boletins do Ministério da Saúde
- [ ] Limitações escrita

### Passo 12 — O texto inteiro, em uma peça · até 2027-02-12

- [ ] revisão adversarial contra o próprio paper
- [ ] manuscrito em `texts/multimodal_forecasting.md`

### Passo 13 — Fechamento · até 2027-02-19

- [ ] estilo
- [ ] reprodução do zero
- [ ] artefatos depositados — confirma:
      `texts/multimodal_forecasting.md#Disponibilidade`

## O que já existe no disco, medido

Existir não é estar pronto: esta tabela é inventário, não status.

| Peça | Onde | O que ainda falta nela |
|---|---|---|
| Avaliador: painel do alvo (BR e por UF), rolling origin, métricas pontuais, janela de pontuação, registro de execução | [src/forecast/](../src/forecast/README.md) | distribuições; o modelo sem texto |
| Os dois ingênuos, medidos na janela do paper | `data/forecast/dengue_br_h1_metrics.parquet` | — |
| Representações de notícia (braços 01, 02 e 03) por semana epidemiológica | `data/pipeline/news/` | — |
| Seis codificadoras de embedding calculadas | `data/pipeline/news/` | escolher uma ou duas para a grade |
| Corpus de texto congelado: 4.569 artigos | `data/pipeline/news/` | — |
| Quatro famílias de literatura fichadas (23, 37, 48 e 10 artigos) | [articles/](../articles/README.md) | — |
| Três seções de manuscrito em inglês | [texts/](../texts/README.md) | — |
| Voz de referência para o medidor de estilo | [voz-de-referencia.md](voz-de-referencia.md) | — |

## Decisões de desenho já tomadas, todas em 2026-11-20

As regras completas estão no [protocolo 00](00-protocolo-comparacao.md); aqui fica
a frase que resume cada decisão, porque cada passo da lista depende delas.

1. **O resultado são os ganhos entre conjuntos consecutivos, não uma manchete** —
   `+ clima − histórico`, `+ busca − + clima`, `+ texto − + busca`, e cada ganho
   precisa aparecer nos dois tipos de modelo.
2. **Tipo de modelo:** dois, *simples* (gradient boosting ou regressão) e
   *sequencial* (rede neural). Com um só, um ganho da rede não distingue *a
   feature ajudou* de *a arquitetura é melhor*.
3. **Conjuntos de features:** quatro, acumulados — `histórico`, `+ clima`,
   `+ busca`, `+ texto`. Dois tipos × quatro conjuntos = 8 células.
4. **Dois horizontes:** h=1 é o número principal, h=4 é robustez declarada. Se o
   prazo apertar, h=4 cai para o modelo sequencial apenas, e a queda fica escrita.
5. **Brasil é o número principal; UF é robustez declarada** — declarado quer dizer
   medido e reportado à parte.
6. **Métrica principal: WIS/CRPS**, que pontua a distribuição; MAE ao lado.
7. **Regra de decisão:** o conjunto `+ texto` bate duas barras — o conjunto
   anterior e o ensemble sem texto. São **oito comparações** na correção para
   comparações múltiplas, e o valor mínimo do ganho é declarado antes de existir
   resultado.
8. **A ablação sem texto é o conjunto `+ busca`**, não o `histórico`.
9. **Uma ou duas codificadoras de embedding na grade**; as outras variam como
   robustez declarada.
10. **Os baselines têm citação** e ficam fora dos quatro conjuntos: persistência,
    naive sazonal, SARIMA, SARIMAX com busca, um modelo só com busca, InfoDengue
    e o ensemble. Os DOIs estão em [06](06-desenho-do-experimento.md).

**Recorte do calendário.** A série de busca congelada vai de 2020-01-26 a
2024-12-29 e o alvo vai até 2026. Com 104 semanas mínimas de treino, a grade só é
avaliável onde as fontes coexistem: de **2022-01-02 a 2024-12-29**, 157 semanas
pontuadas, e 154 nos conjuntos que usam busca. Como a comparação exige todos os
conjuntos nas mesmas semanas, a janela curta da busca vale para os outros também.

## Fora de escopo, declarado como trabalho futuro

| Dentro | Fora |
|---|---|
| Brasil, horizonte de 1 semana | UF como número principal; horizontes de 8 a 12 semanas |
| UF e horizonte de 4 semanas, como robustez declarada | — |
| 2 tipos de modelo × 4 conjuntos; 4 representações de texto | cada representação de texto como conjunto próprio |
| uma ou duas codificadoras de embedding | as outras variantes de embedding |
| métricas pontuais e probabilísticas | o caminho 05, LLM como previstor |
| notícia da EBC como corpus de texto | boletins do Ministério da Saúde — decisão no passo 11 |

## Pontos de corte

Cada um decide de antemão o que sai do escopo, na data em que a decisão importa.

| No passo | Se | Então |
|---|---|---|
| 3 | o InfoDengue não converge | sai do experimento e vira citação do sistema original, com o desvio registrado |
| 4 | o conjunto `histórico` não fecha nos dois tipos de modelo | o tipo que não fechar sai, e o desenho deixa de ser duplo — registrado, não escondido |
| 5 | clima e busca não fecham até aqui | corta as células do modelo simples nesses dois conjuntos; mantém os dois tipos no `+ texto`, que é onde a pergunta é respondida |
| 6 | a anotação não terminou | a extração por LLM sai do paper; a amostra parcial vira evidência para trabalho futuro |
| 8 | a grade de texto não fecha com duas codificadoras | fica uma, a que já estiver pronta |
| 11 | a leitura por UF não fecha | Brasil é o número principal e o descompasso espacial vira limitação declarada |
| 11 | o horizonte de 4 semanas não fecha | cai para o modelo sequencial apenas, e a queda fica declarada |
| 11 | boletins do Ministério da Saúde | fora por padrão; só entram se a grade fechou antes do prazo |
| 12 | o texto não está em uma peça | corta a robustez, não o fechamento |

## Riscos

- **A grade é o que mais consome tempo.** São 14 modelos treinados — 8 células
  mais 6 baselines — cada um rodando rolling-origin em dois horizontes: **28
  medições**, mais 2 ensembles, que são médias e não treinam.
- **Vazamento de dados.** A data de corte de treino dos codificadores de texto é
  desconhecida e o corpus vai até 2026; 2024 foi o ano recorde de dengue e está em
  toda parte.
- **Descompasso espacial.** O corpus é de uma fonte nacional e as tabelas de
  features têm 28 localidades. As linhas de UF são menção no texto, não contagem
  por estado: um artigo que cita três estados conta nos três, então elas não somam
  a linha do Brasil.
- **Contagem acumulada.** Só 24% dos artigos declaram número de casos, e é número
  acumulado, não semanal.
- **Poder estatístico.** 157 semanas pontuadas, 154 nos conjuntos com busca, para
  oito comparações pareadas com correção. Um ganho pequeno pode não ser
  detectável, e isso é limitação declarada, não desculpa depois do resultado.
- **Nenhum checkpoint externo.** O acompanhamento é de pouca interação; o que
  substitui é a revisão adversarial do passo 12.

## Perguntas em aberto

Duas que esta lista não decide sozinha, registradas para não serem resolvidas por
omissão:

- **O prazo é imposto pelo programa ou autoimposto?** Se for negociável, os passos
  11 e 12 são o que ganharia prazo. Se for imposto, os pontos de corte são a única
  alavanca.
- **O orientador e a banca precisam concordar com o redesenho?** A pergunta do
  paper mudou de "qual representação de notícia" para "quais features valem a pena
  incluir", e o desenho passou de três braços para 8 células em dois horizontes.

## Como esta lista se mantém

À mão. Você percorre os passos, marca o que fechou e ajusta prazos quando eles
mudarem. A skill `plano-entrega` pode rascunhar uma proposta de reorganização
quando você pedir — ela não marca nada. As configurações da revisão de literatura
moram em [.claude/workflows/familias/](../.claude/workflows/familias/README.md).
