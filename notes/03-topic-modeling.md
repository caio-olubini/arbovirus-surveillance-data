# 03 — Topic modeling temporal (DMR / STM / BERTopic)

**Estado:** testando — implementado 2026-10-13 (ver §Decisão)
**Papel no artigo:** representação concorrente (ver [00](00-protocolo-comparacao.md))

## Hipótese

A notícia sobre dengue não é um bloco: ela fala de casos, de vetor, de política
pública, de vacina, de colapso hospitalar. Modelar tópicos e acompanhar a
*prevalência de cada tópico no tempo* produz features que dizem **de que** a
imprensa falava em cada semana — e isso pode ser mais preditivo do que o volume
bruto, que só diz *quanto*.

## O que produz

Por EW: um vetor de `topic_share[ew, k]` (proporção de cada tópico na semana),
mais `topic_share` defasado 1–4 semanas. Entra como covariável no mesmo backbone.

## Como testar

1. Extrair o texto dos HTMLs, pré-processar em PT. ~~Lematização com spaCy
   `pt_core_news`~~ → **folding de acento + regex de palavra + lista de stopwords
   congelada** (ver §Decisão).
2. **Modelo primário: STM com o tempo como covariável de prevalência** — é
   construído exatamente para isso e funciona em corpus pequeno.
   [Roberts 2019, *J Stat Softw* 91(2)](https://doi.org/10.18637/jss.v091.i02).
   → **Implementado como DMR** (`tomotopy`), o mecanismo que o STM estende; ver
   §Decisão para por que não é o pacote R.
3. **Comparador: BERTopic** com encoder multilíngue/PT.
   [Grootendorst 2022, arXiv:2203.05794](https://arxiv.org/abs/2203.05794).
   Semear (`random_state`) e reportar estabilidade entre seeds — é estocástico e
   não fixa k.
4. **Baseline: LDA** clássico.
   [Blei 2003, *JMLR* 3:993](https://www.jmlr.org/papers/v3/blei03a.html) (JMLR é
   anterior a DOIs).
5. Escolher k por **estabilidade + coerência**, não perplexidade.
   [Greene 2014, ECML PKDD, LNCS 8724](https://doi.org/10.1007/978-3-662-44848-9_32).
   Para um corpus deste tamanho, esperar k ≈ 10–25.
6. Rodar o protocolo 00.

## Evidência

- **O precedente mais próximo de todos — e é dengue.**
  [Ghosh 2017, *Sci Rep* 7:40841](https://doi.org/10.1038/srep40841) (**EpiNews**):
  topic model temporal supervisionado sobre notícias do HealthMap → tendências de
  tópico → autorregressão elastic-net para **estimar casos antes do relatório
  oficial**; testado em dengue (Índia) e HFMD (China). Ler com atenção: é o
  desenho que este caminho quer replicar.
- **Tópicos neurais dinâmicos em notícia.**
  [Wen 2022, *Patterns* 3(3):100435](https://doi.org/10.1016/j.patter.2022.100435)
  (EpiTopics/MixMedia: DETM sobre 1,2M artigos → 25 tópicos → classificador
  transferido) e [Li 2020, ACM BCB](https://doi.org/10.1145/3388440.3412418).
- **Longo horizonte em notícia de doença.**
  [Huang 2018, *JMIR* 20(5):e10047](https://doi.org/10.2196/10047): LDA sobre
  3,5M artigos Reuters em três décadas, rastreando deriva de tópico.
- **Arbovírus + português do Brasil.**
  [Missier 2016, LNCS 9881:80](https://doi.org/10.1007/978-3-319-46963-8_7): LDA
  vs. classificação supervisionada em tweets do Rio ao longo de ondas epidêmicas;
  achou que os tópicos cortam transversalmente as classes de especialista.
- **Dengue na mídia brasileira, análise de discurso (não computacional).**
  [Ferraz & Gomes 2012, *Rev Bras Epidemiol* 15(1)](https://doi.org/10.1590/S1415-790X2012000100006):
  291 artigos do Jornal do Commercio (PE), 2002–2008; a cobertura **segue** a curva
  epidemiológica. Citável para o argumento de direcionalidade.

## Decisão — 2026-10-13

Implementado em `src/pipeline/news/topics/`. As três escolhas que a nota deixava
abertas, e o que as fechou:

- **Modelo: `tomotopy` DMR** (Dirichlet Multinomial Regression; Mimno & McCallum
  2012, [arXiv:1206.3278](https://arxiv.org/abs/1206.3278)) com o **período como
  covariável do documento**. DMR condiciona a *prevalência* do tópico ao
  covariável — é o mecanismo que o STM estende, então é o substituto Python-nativo
  do candidato primário desta nota, não outra coisa. Três razões, em ordem de peso:
  **(1) sem R** — esta máquina não tem R e o projeto já substituiu sua cadeia R
  legada por produtos Python; um runtime R seria o único do repositório e teria de
  ser instalado por quem reproduz o artigo. **(2) Independência do braço 02** —
  `notes/00` fixa 01/02/03 como representações *concorrentes*; o pipeline padrão do
  BERTopic precisa de embeddings de frase, e reusar o BERTimbau congelado do braço
  02 faria os dois braços compartilharem o encoder ("o mesmo embedding cortado de
  dois jeitos" não é comparação independente). **(3) O corpus é desigualmente denso
  ao longo de 24 anos** — o risco que esta nota já nomeava, e exatamente o
  desequilíbrio sob o qual o passo HDBSCAN do BERTopic é conhecidamente instável.
  LDA (`family: lda`) é o baseline, mesma biblioteca e mesmo laço de treino menos
  o metadado.
- **k é selecionado, não configurado.** A faixa `k_range` é varrida, `c_v` pontua
  cada candidato, e o argmax vence — empate vai para o **menor** k. O *sweep
  inteiro* é publicado em `EBC_dengue_topics_sweep` (os modelos que perderam, com
  sua coerência e seu `ll_per_word`), para que a escolha possa ser conferida em vez
  de aceita. Não existe constante `topic_count` no `spec.py` de propósito: fixá-la
  faria a seleção parecer mudança de schema.
- **Tokenização: folding de acento + regex `[a-z]+` + lista de stopwords PT-BR
  congelada.** Sem lematizador, sem POS tagger, sem spaCy — `pt_core_news` foi
  posto de lado porque adicionaria um modelo de centenas de MB como *único*
  consumidor de um runtime novo de NLP, num repositório cujo outro braço de notícia
  é regex puro. O custo honesto é recall em flexões raras, que `min_df` poda da
  vocabulário de qualquer forma.

**Resultado (4.369 artigos, 965 semanas × 28 locais):** `k = 15` selecionado,
coerência `c_v` 0.7510, contra 0.7141 (k=5), 0.7165 (k=10), 0.7263 (k=20) e 0.7016
(k=25). A coerência **vira** dos dois lados de 15, enquanto `ll_per_word` segue
subindo até k=25 — o desacordo entre os dois critérios, medido neste corpus, é o
argumento para o critério. 221 s em CPU, worker único.

O grão do covariável é **mês**, não a semana do output: 965 níveis semanais contra
~4,5 artigos cada super-parametrizariam o DMR, enquanto ~290 níveis mensais pegam
~15. O grão publicado continua semanal — o covariável molda o *ajuste*, não a saída.

**Achado que este braço tornou visível:** **180 dos 4.369 artigos (4,1%) são em
inglês** — a edição em inglês da Agência Brasil — e todos passam pelo portão de
idioma, porque `common.guess_language` só separa *espanhol* de *não-espanhol* e
chuta `pt` por padrão. O tópico 1 é exatamente esse artefato (*the, and, that, for,
with, health*). Os braços 01 e 02 absorviam esses artigos em silêncio; este é o
primeiro que gasta um tópico inteiro neles. **Não foi corrigido aqui**: o protocolo
00 fixa o conjunto de artigos como terreno comum, e re-filtrar em um braço faria seu
corpus diferir dos outros dois e quebrar a comparação. É pendência do protocolo 00.

## Custo

Médio. STM/LDA rodam em CPU; BERTopic precisa de encoder mas é uma passada.
O custo real é o tempo de análise: escolher k, ler os tópicos, decidir se fazem
sentido — e justificar isso no artigo.

## Riscos

- **Instabilidade ao longo de 24 anos.** Vocabulário e formato da notícia mudam
  (era Zika 2015–16, era COVID 2020–21). Um tópico ajustado no corpus inteiro pode
  ser dominado por 2024.
- **Desequilíbrio temporal.** Anos iniciais têm poucos artigos e mais curtos.
  Considerar ajuste ponderado por período ou validação por fatia temporal.
- **k não tem critério universal.** Coerência, estabilidade e diversidade podem
  discordar. Documentar a escolha.
- **Cautela com estabilidade.** Reprodutibilidade não é validade — um tópico
  estável pode ser estável e errado.

## Pendências / próximo passo

- [x] Decidir se o primário é STM (interpretável, feito para corpus pequeno) ou
      BERTopic (estado da arte em notícia). → **DMR**, com LDA de baseline; ver
      §Decisão.
- [x] Definir como tópicos entram no modelo: shares diretos, ou clusters binários?
      → **shares diretos**, `share[ew, location, topic]`, média não-ponderada sobre
      os artigos da semana. Clusters binários perdem a mistura, que é o ponto.
- [ ] Planejar a figura de "o que a imprensa falava quando" — provavelmente é a
      figura mais citável do artigo. A tabela `EBC_dengue_topics_meta` já dá os
      termos por tópico; falta a série temporal de share por tópico como figura.
- [ ] **Estabilidade entre seeds não foi estabelecida.** Um ajuste, uma seed. Um
      ajuste só não estabelece que os tópicos são estáveis — rodar o sweep em várias
      seeds e reportar a concordância tópico-a-tópico é a medição que resolveria.
- [ ] **Refit com origem rolante.** O DMR é ajustado uma vez sobre o corpus
      inteiro, então os tópicos são moldados pelos 24 anos de uma vez — incluindo
      2024, o ano recorde. O sweep torna a *seleção* visível, mas não trata disso.
- [ ] **A fatia em inglês** (180 artigos, 4,1%) é pendência do protocolo 00, não
      deste braço; ver §Decisão.
