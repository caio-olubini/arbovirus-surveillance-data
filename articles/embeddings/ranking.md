# Ranqueamento das 23 fichas — por abordagem, não por artigo

Contexto de uso (é ele que define "usável"): corpus de 4.369 artigos PT-BR da
Agência Brasil (query dengue), 965 semanas × 28 locations; **CPU only, sem GPU**;
os extras já fixados em `pyproject.toml` são `embeddings` (torch + transformers,
~800 MB) e `topics` (tomotopy); braços 01 (léxico), 02 (6 configurações de
embedding) e 03 (DMR) **já construídos e medidos** (`src/pipeline/news/README.md`);
`notes/00-protocolo-comparacao.md` fixa o chão comum e exige a ablação "sem texto"
e o controle de texto embaralhado. **Dependência nova é caríssima** e o transform
precisa rodar em minutos, não horas.

Os dois grupos **não competem entre si**. `representacao` são alternativas umas das
outras (qual converte texto em número rende mais por unidade de esforço aqui);
`aplicacao` responde outra pergunta (o que já foi feito em notícia como fonte de
vigilância, e o que muda para nós). A numeração reinicia em cada grupo.

Uma correção de leitura que vale registrar: o braço 02 publica **um** vetor por
artigo (o pooling já aplicado). Trocar o pooling de tokens (mean ↔ [CLS] ↔ max)
**exige re-encode**; só a re-pooling *entre artigos dentro da semana* é que é
"segundos". A correção de geometria (whitening/ABTT), essa sim, opera sobre o vetor
já salvo e não exige re-encode.

---

## A. Representação (como transformar texto em número)

| rank | abordagem (fichas) | merit | adoption_cost | verdict |
|---|---|---|---|---|
| 1 | Escolha de pooling sobre encoder congelado: mean vs [CLS] vs max vs concat vs hier/n-grama (07 Ni 2022, 19 Shen 2018, 01 Reimers 2019, 04 Cer 2018 = dup, 21 Wieting 2016) | Ni 2022: mean do encoder T5 88.96 vs primeiro token 83.38 no transfer, e STS desaba a 10.37 no primeiro token. Shen 2018: pooling sem parâmetros empata/supera CNN de 29 camadas em documento longo e tópico (Yahoo 73.53 vs 73.43) com 1/10 dos parâmetros do LSTM. Reimers 2019 (Tab. 6): sob classificação MEAN≈CLS≈MAX (80.78/79.80/79.07), mas sob regressão MAX colapsa (69.92 vs MEAN 87.44). Baseline = o mesmo encoder com outro pooling. | Re-encode: 1 passada forward por modelo capturando mean+[CLS]+max na mesma rodada (~11 min p/ BERTimbau base; ~35 min p/ e5-large). Nenhuma dependência nova (extra `embeddings` já fixado); CPU, minutos. A agregação semanal a partir daí é segundos. | tentar agora |
| 2 | Correção de geometria pós-hoc sobre vetores congelados: whitening (10 Su 2021), remover média + top-PCs / all-but-the-top (09 Mu 2017), normalizing flow (12 Li 2020) | Su 2021: STS-B 59.04→67.51 (+8.5) sobre a MESMA representação sem correção. Mu 2017: +4% Pearson em STS, +2.5% em categorização (mas piora em MSRpar e em analogia). Li 2020: +8.16 médio sobre o BERT cru. Baseline = a própria representação sem a correção. **Aqui o bracket já mediu**: whitening move PC1-vs-casos de 0.105 para 0.113 e derruba o cosseno médio de 0.8792 para −0.0002. | Quase zero: média + SVD sobre a matriz 4369×768 já publicada em parquet; segundos em CPU, numpy puro, sem re-encode, sem dependência. Já existe 1 variante (`bertimbau-whitening`). O custo é de desenho: o fit é transdutivo (vê o futuro) e precisa de janela rolling-origin (`whitening_fit_until` já existe). | tentar agora |
| 3 | Encoder multilíngue/destilado pré-treinado, drop-in no bracket (06 Reimers 2020 destilação, 14 Yang 2020 USE-multilíngue, 13 Pires 2019 M-BERT) | Cobrem português (Reimers 2020 tab. 9 "por" 94.8 no Tatoeba; Yang 2020 lista pt entre 16 línguas; Pires 2019 lista pt-br no UD) e a destilação maximiza **similaridade semântica**, não tradução — o inverso de LaBSE/USE. Baseline: encoders multilíngues crus (mBERT mean 54.0, XLM-R mean 42.7 em STS). | Baixo: um `model_id` novo pelo extra `embeddings`, sem treino nem GPU; +1 variante ~10 min CPU. Mas o ganho marginal é baixo — o bracket JÁ tem dois multilíngues que cobrem pt (e5-large, bge-m3). | tentar depois |
| 4 | Vetores de palavra estáticos + SIF: média ponderada por frequência + remoção da 1ª componente (11 Arora 2017) | Baseline não supervisionado forte: +10% a +30% sobre média de GloVe em STS (por tarefa, +7% a +58%); ablação W+R = +13%; ganha de DAN/LSTM em SICK. Não é uniforme: PIORA em MSRpar (47.7→35.6) e perde em sentiment; o topo (PSL+WR) embute supervisão (PPDB). | Compute trivial (média + 1 SVD 4369×300), mas exige vocabulário de vetores de palavra **PT-BR** que não temos nem está nos extras — fastText-PT ~1.2 GB, ou treinar word2vec (gensim = dependência nova). O custo real é o artefato novo. | descartar |
| 5 | Embedding de sentença composicional treinado do zero sobre n-gramas, sem transformer (20 Pagliardini 2018, Sent2Vec) | Média de unigramas+bigramas treinada para prever palavras: +3.8 macro-STS sobre SOTA não supervisionado; treino de 19.7B palavras em 6.5 h em CPU (30 threads). Mas perde do C-PHRASE no subtarefa STS "News" (0.62 vs 0.69) e o bigrama piora similaridade. | Sem modelo PT publicado → treinar do zero sobre 4.369 artigos. Compute provavelmente minutos (nosso corpus é ordens de magnitude menor que o menor do artigo, 0.9B palavras — NÃO reportado nesse regime), mas a implementação é C++/FastText (dependência nova) e o corpus é pequeno para treinar embeddings de qualidade. | descartar |
| 6 | Fine-tuning siamesa/contrastivo do encoder no corpus (02 Gao 2021 SimCSE, 01 Reimers 2019 SBERT, 03 Conneau 2017 InferSent) | SimCSE não supervisionado +4.2 Spearman sobre o melhor anterior em STS (76.25); o mecanismo (dropout como augmentation) é agnóstico de língua; SBERT mostra NLI supervisionado gerando vetor transferível (74.9 vs InferSent 65.0). Mas SBERT perde para o cross-encoder BERT na tarefa supervisionada (86.10 vs 88.77) e cai ~7 pts cross-topic. | Alto e desqualificante: exige **treino** (não inferência) — SimCSE assume ~10^6 frases e grid de LR em GPU; temos ~4.3k artigos. Nenhum número de CPU. SBERT/InferSent exigem rótulos NLI em inglês (SNLI+MNLI) que não existem em PT-BR. Quebra o footing não-treinado do braço 02. | descartar |
| 7 | Receita de treino cross-lingual: translation ranking + additive margin / destilação por pares paralelos (05 Feng 2022 LaBSE, 06 Reimers 2020) | LaBSE +18 no Tatoeba (83.7 vs 65.5) e a destilação +~40 pts em línguas de baixo recurso — mas em recuperação de **tradução**. No STS monolíngue LaBSE é PIOR que SBERT (72.8 vs 79.2); a destilação perde do LASER/LaBSE no bitext (85.7/88.6 vs 93.0/93.5). | Inviável: TPU (32–512 núcleos) + corpora paralelos da ordem de bilhões; releases só em TF Hub, fora do stack torch. Sem pares de tradução e sem GPU. O artefato é consumível, mas otimizado para a tarefa errada. | descartar |
| 8 | Seleção teórica de dimensionalidade de embeddings de palavra por PIP loss (08 Yin 2018) | Critério principiado de k* (trade-off viés-variância) que coincide com grid search; 80–90% do ótimo se mantém mesmo super-parametrizando. Baseline = a grade empírica; auto-referente, sem tarefa extrínseca, só nível-palavra em inglês (Text8). | Compute baixo (1 SVD da co-ocorrência), mas a teoria vale só para embeddings que são fatoração de matriz (LSA/skip-gram/GloVe) — **não cobre** embeddings de transformer, que são o braço 02. Construir a matriz de co-ocorrência PT-BR é trabalho novo não reportado. | descartar |

Nota de agrupamento: 09, 10 e 12 são a **mesma abordagem** (consertar a anisotropia
de vetores prontos sem treino) e por isso são uma linha só; a evidência é a soma das
três. A 11 (SIF) compartilha a remoção de componente mas acrescenta a ponderação por
frequência, que é uma alavanca distinta, então fica separada. A 04 é **duplicata** da
01 (o PDF de `04_cer_2018_universal_sentence_encoder.pdf` é o SBERT, não o USE), então
entra como evidência de pooling, não como encoder independente.

---

## B. Aplicação (onde usar notícia como fonte de vigilância, no nosso domínio)

| rank | abordagem (fichas) | merit | adoption_cost | verdict |
|---|---|---|---|---|
| 1 | Tendência de tópico temporal supervisionada como regressor em ARX/ElasticNet para estimar casos 1 passo à frente (22 Ghosh 2017, EpiNews-ARNet) | Único dos 23 que avalia **exatamente o nosso desenho** — local×tempo, palavras-semente, 1-step-ahead — com baselines explícitos, inclusive um que ignora a notícia (Casecount-ARMA); NRMSE menor em 8/10 pares país-doença, com dengue da Índia e da China entre os casos. Baseline: ARMA só de contagens. | Baixo compute: Gibbs + ElasticNet em CPU, sem GPU. Exige contagens de caso reais (temos SINAN) e palavras-semente (= léxico do braço 01). O modelo conjunto supervisionado-temporal **não existe pronto no tomotopy**; aproximação barata: usar as shares EW×tópico que o braço 03 **já publica** como regressores lagados num modelo linear (numpy/lstsq, sem dependência nova). Ganho nos EUA é 0.01–0.03 e não há teste de significância. | tentar agora |
| 2 | Sinal semanal por contagem de keywords (léxico expandido por word2vec) + indicadores técnicos + classificador sobe/desce (15 Kim 2019) | Mostra o padrão braço-01 (contagem por keyword/semana) funcionando para uma doença (acurácia 0.867) e um desenho de backtest por seções de 12 semanas reaproveitável. Mas **não tem baseline algum** (nem persistência, nem classe majoritária, nem tf-idf): o 0.867 não tem contra o que ser lido. | Baixo compute: word2vec + SVM em CPU, sem GPU, sem transformer. Exige alvo semanal rotulado sobe/desce (a SINAN cobre); keywords são de influenza em inglês (retrabalho p/ dengue/pt). O word2vec aqui é só para achar keywords — não é representação. | tentar depois |
| 3 | Prever aparição de surto por país a partir de contagens de notícia por doença (16 Kim 2021) | Moldura geral notícia↔severidade; modelos clássicos baratos em CPU (SSL 0.838 acc vs SVM 0.732). Mas só compara três modelos entre si, sem baseline externo, e o rótulo (+1 = apareceu notícia da doença) é **circular** com as features (contagens de notícia da mesma fonte). | Bloqueado por dados: exige feed Medisys (não público) com 115 doenças×237 países e contagem real por doença/país; nosso corpus é 1 doença (dengue) e sem ground truth por doença. Não reprodutível (dados "sob pedido"). | descartar |
| 4 | Classificador binário de relevância de notícia (17 Gautam 2025: SBERT/MiniLM + LSTM/BiLSTM+atenção/Transformer) | Confirma all-MiniLM-L6-v2 como front-end barato em CPU e que atenção ajuda num classificador de texto de notícia (BiLSTM+MHA 98.25%). Mas não há benchmark nem baseline externo (os autores admitem), os rótulos vêm de regras spaCy (supervisão fraca) e o encoder nunca é comparado. | Nosso corpus já é 100% query dengue → o rótulo "surto/não surto" é **degenerado**; exigiria rótulos que não temos e deps novas (TensorFlow/Keras, spaCy). Contradição interna: tabela diz embedding_dim=128 mas MiniLM é 384. | descartar |
| 5 | Filtro de relevância word2vec + CNN (18 Jang 2019, coreano) | word2vec supera inicialização aleatória (~+9 F1 em notícia); CBOW>Skip-gram em notícia. Baseline único e fraco (vetores aleatórios), sem TF-IDF+SVM, sem teste de significância, monolíngue coreano. | Exige pos/neg rotulados que não temos, tokenizador coreano, reimplementar CNN (deeplearning4j/GPU no artigo); arquitetura word-level não dialoga com os braços 02/03. gensim não está instalado (dependência nova). | descartar |
| 6 | Sentimento (VADER) + LDA descritivo sobre décadas de cobertura de doença (23 Huang 2018) | Moldura de ler volume+sentimento+tópico como atenção a doença ao longo do tempo; discute o Zika no Brasil 2016 — domínio próximo. Mas é puramente descritivo: sem baseline, sem F1/acuidade; VADER não avaliado para Reuters; LDA com K=1 fixo. | VADER é inglês-only e UMLS/PheWAS inglês-only; o LDA já é coberto por tomotopy (braço 03). Para PT-BR seria preciso léxico de sentimento novo. Não reporta runtime/memória. | descartar |

---

## C. Notas por abordagem

### Representação

**R1 — Pooling sobre encoder congelado.** É o eixo que o bracket deliberadamente
**não** varreu: o braço 02 fixa o pooling por encoder e só o BGE-M3 usa `[CLS]`
(porque é a definição do modelo). A evidência das fichas é forte e no mesmo sentido
(mean ≥ primeiro token; pooling simples empata com CNN profunda em documento longo),
e a nuance importante vem do próprio SBERT: **sob classificação o pooling quase não
importa, sob regressão o MAX colapsa**. Nosso uso é agregação/regressão semanal, que
é o regime em que a escolha importa. Custa um re-encode por modelo (~11 min para o
base), sem dependência nova.

**R2 — Correção de geometria pós-hoc.** É a abordagem mais barata possível aqui:
opera sobre os vetores que o braço 02 já gravou, em numpy puro, sem re-encode. Já tem
um pé no bracket (`bertimbau-whitening`) e a própria medição do repo mostra o maior
movimento de correlação entre as variantes mean-pooled (0.105→0.113, em magnitude). O que falta
não é testar whitening de novo, e sim varrer a **intensidade** da correção (D do ABTT,
k do whitening) e comparar com o flow — que as fichas dão como a variante mais forte
em STS, mas que exige uma implementação de flow (dependência nova, custo incerto).

**R3 — Encoder multilíngue/destilado drop-in.** Baixo custo, mas baixo valor marginal:
o bracket já tem dois multilíngues que cobrem pt. O único motivo diferencial é que
modelos destilados otimizam *similaridade semântica* (nosso uso) e não *retrieval*
(e5/bge) — e os próprios fichas mostram que LaBSE/USE, otimizados para tradução, são
piores em similaridade fina. Vale depois dos eixos baratos.

**R4–R8 — descartes.** SIF e Sent2Vec resolvem um slot (word vectors estáticos) que o
transformer do braço 02 já superou, e o custo é um asset novo pesado (fastText-PT ou
treinar do zero) contra um footing não supervisionado mais fraco. Fine-tuning quebra o
footing não-treinado que o protocolo 00 fixa e não tem rótulos PT-BR. A receita
cross-lingual é treino em TPU sobre bilhões de pares. O PIP loss é nível-palavra e
fatoração de matriz — não cobre os 768/1024 dims de um transformer.

### Aplicação

**A1 — Tendência tópica + ARX.** É a única ficha de aplicação que responde "a notícia
prevê caso melhor que o passado da série?", que é a pergunta do protocolo 00, e traz
o baseline que o protocolo exige (Casecount-ARMA, que ignora o texto). O ponto de
adoção é honesto: o modelo conjunto supervisionado-temporal não existe pronto no
tomotopy, mas a *ideia* — tendência tópica lagada como regressor externo — pode ser
testada hoje com as shares EW×tópico que o braço 03 já publicou, num modelo linear
com numpy. É "tentar agora" porque responde a uma pergunta que temos, não porque o
artigo seja metodologicamente forte (o ganho nos EUA é ruído e não há significância).

**A2 — Contagem semanal + classificador.** O desenho de backtest por seções é
aproveitável e barato, mas o artigo não tem baseline: a acurácia 0.867 não é
evidência. Fica como moldura secundária.

**A3–A6 — descartes.** A 16 tem alvo circular e um feed (Medisys) que não existe aqui;
a 17 e a 18 resolvem um problema que não temos (relevância já é implícita na query
dengue) e a 17 ainda se contradiz no próprio encoder; a 23 não mede nada contra nada e
a parte reaproveitável (tópicos) já existe no braço 03.

---

## D. Cross-cutting (decisões de desenho, não de artigo)

- **representacao — toda a evidência é intrínseca e em inglês.** Só LaBSE (05), a
  destilação (06) e o USE-multilíngue (14) chegam a pt, e **nenhuma mede PT-BR de
  notícia**. O que transfere é o mecanismo, não o número.
- **representacao — o eixo convergente é anisotropia/geometria** (01, 07, 09, 10, 12,
  19, 21): mean-pooling trabalhado supera arquitetura mais caro, mas o **mean cru é
  ruim**. É decisão de desenho do braço 02, não de um único artigo.
- **representacao — a janela curta NÃO é o gargalo, e o repo já provou isso.** Todas
  as fichas assumem janela curta (a 512 trunca 39% do nosso corpus; o Serafim 128,
  94,8%), mas o braço 02 mediu que `title-only` (0% truncado) **supera** o texto
  completo: truncar não é o que limita. A afirmação "todos assumem 512" é verdadeira
  sobre a biblioteca; a conclusão de que isso limita é falsa sobre o repo.
- **aplicacao — zero trabalho prévio em PT-BR/notícia brasileira.** Os idiomas são
  inglês, coreano e chinês-traduzido. A distância idioma+país+fonte é assumida pequena
  por simpatia temática, nunca medida.
- **aplicacao — nenhuma isola o efeito da representação.** 15 usa word2vec só para
  achar keywords, 16/18 não têm embedding, 17 contradiz o próprio encoder, 22 é
  bag-of-words. Elas medem "notícia como sinal", não "representação melhor".
- **transversal — "não reportado" é o custo da maioria dos encoders e pipelines
  novos.** Quase nenhuma ficha traz teste de significância, variância ou número de
  compute. Custo não reportado é incerteza, e incerteza não é barato.
- **transversal — o baseline que o protocolo 00 exige (ablação "sem texto" / texto
  embaralhado) aparece explícito só em 22** (Casecount-ARMA) e foi **omitido** em 15 e
  18. É a lacuna mais recorrente, e é justamente o número que o artigo precisa
  reportar.
- **representacao — a ficha 04 não é o paper do USE.** O PDF em
  `04_cer_2018_universal_sentence_encoder.pdf` é um duplicado de 01 (SBERT); o USE
  real está ausente do checkout. A biblioteca tem evidência de pooling do SBERT, não
  do USE.

---

## E. First move

Re-encodar o **BERTimbau UMA vez** capturando `mean`, `[CLS]` e `max` na mesma
passada (~11 min de CPU, sem dependência nova) e comparar a correlação da componente
semanal de cada pooling com os casos contra o +0.297 de `n_articles` — é o eixo que o
bracket deixou fixo por encoder e o teste mais barato de se algum eixo de conteúdo
recupera sinal antes de gastar com qualquer encoder novo.

---

## F. O que ficou de fora e por quê

- **07 (Sentence-T5)** virou evidência da linha de pooling, não linha própria: seu
  achado central é "mean do encoder > primeiro token", a mesma decisão de R1.
- **04 e 14 (USE)** idem: 04 é evidência de pooling (e é duplicata de 01), 14 é
  evidência de que há modelo multilíngue drop-in — dobrados em R1 e R3.
- **01 (SBERT)** aparece em R1 (pooling) e R6 (supervisionado), que são facets
  distintos do mesmo artigo.
- **13 (M-BERT)** não é método a adotar (é estudo de probing); sua contribuição útil
  é "M-BERT cobre pt e o pooling exclui [CLS]/[SEP]", dobrada em R3.
- **16, 17, 18, 23** descartadas por resolverem um problema que não temos (relevância
  já implícita no corpus), por alvo circular, ou por não trazerem representação nem
  avaliação (descritivo).
