# 03 — Topic modeling temporal (STM / BERTopic)

**Estado:** ideia — 2026-10-07
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

1. Extrair o texto dos HTMLs, pré-processar em PT (lematização com spaCy `pt_core_news`).
2. **Modelo primário: STM com o tempo como covariável de prevalência** — é
   construído exatamente para isso e funciona em corpus pequeno.
   [Roberts 2019, *J Stat Softw* 91(2)](https://doi.org/10.18637/jss.v091.i02).
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

- [ ] Decidir se o primário é STM (interpretável, feito para corpus pequeno) ou
      BERTopic (estado da arte em notícia). Meu palpite: STM primário, BERTopic
      comparador.
- [ ] Definir como tópicos entram no modelo: shares diretos, ou clusters binários?
- [ ] Planejar a figura de "o que a imprensa falava quando" — provavelmente é a
      figura mais citável do artigo.
