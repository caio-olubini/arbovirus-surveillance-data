# Ranqueamento das abordagens — embeddings (23 fichas)

Ranqueia **abordagens**, não artigos. Várias fichas descrevem a mesma abordagem e aparecem como uma
linha só; nesse caso a evidência é a soma delas. Os dois grupos **não competem entre si** e a numeração
reinicia em cada um:

- `representacao` (17 fichas) — como transformar texto em número. São alternativas umas das outras; a
  pergunta é qual delas rende mais por unidade de esforço aqui.
- `aplicacao` (6 fichas) — onde usar notícia como fonte de vigilância, no nosso domínio. Não competem
  com as de representação; a pergunta é o que já foi feito em notícia como fonte de sinal, o que aquilo
  mediu, e o que muda para nós.

## Contexto que define "usável" — o custo de adoção é relativo a isto

Corpus de 4.369 artigos PT-BR da Agência Brasil (query dengue), 965 semanas × 28 locations (BR + 27 UFs);
**CPU only, sem GPU**; extras já fixados em `pyproject.toml` — `embeddings` (torch + transformers,
~800 MB) e `topics` (tomotopy). Braços 01 (léxico), 02 (bracket de 6 configurações de embedding) e 03
(DMR) **já construídos e medidos** (`src/pipeline/news/README.md`). `notes/00-protocolo-comparacao.md`
fixa o chão comum e exige a ablação "sem texto" e o controle de texto embaralhado. **Dependência nova é
caríssima** e o transform precisa rodar em minutos, não horas.

Duas leituras do repo que mudam o custo de várias linhas, e que valem registrar antes das tabelas:

- O braço 02 publica **um** vetor por artigo, com o pooling de tokens **já aplicado**. Trocar o pooling
  (mean ↔ `[CLS]` ↔ max) **exige re-encode**; só re-pooling *entre artigos dentro da semana* é "segundos".
- A correção de **geometria** (whitening, all-but-the-top, redução de dimensão) opera sobre o vetor já
  salvo e **não** exige re-encode.

---

## A. Representação — como transformar texto em número

Alternativas entre si. Dois "tentar agora", dois "tentar depois", dois "descartar".

| # | Abordagem | Fichas | Merit (o que entrega, contra que baseline) | Adoption cost (aqui) | Veredito |
|---|---|---|---|---|---|
| 1 | Escolha de pooling sobre encoder congelado: mean vs `[CLS]` vs max vs concat vs hierárquico/n-grama | `ni2022sentencet5`, `shen2018baseline`, `reimers2019sbert`, `cer2018use`, `wieting2015paraphrastic` | É o eixo que o braço 02 **fixa por encoder** e por isso nunca varreu. `ni2022`: a média das saídas do encoder T5 supera o primeiro token em todas as tarefas de transfer, e a média crua do T5 já bate a média crua do BERT (transfer 88,96 vs 84,94). `shen2018`: pooling **sem parâmetros** empata/supera uma CNN de 29 camadas em documento longo/tópico (Yahoo! 73,53 vs CNN 70,94 e LSTM 70,84) com 61K parâmetros (1/10 do LSTM) e 63 s de treino contra 598 s. `reimers2019` e `cer2018` usam a média como pooling padrão. Baseline = o mesmo encoder com outro pooling, e o `n_articles` (+0,297) que todo eixo denso do bracket perde. | Re-encode: 1 passada forward por modelo capturando mean + `[CLS]` + max na **mesma** rodada (~11 min para o BERTimbau base — 654,9 s medidos; ~35 min para o e5-large). Sem dependência nova (extra `embeddings` fixado); CPU. A agregação semanal a partir daí é segundos. | tentar agora |
| 2 | Pós-processamento geométrico pós-hoc sobre vetores congelados: whitening, remover média + top-PCs / all-but-the-top, normalizing flow, e a redução/seleção de dimensão do vetor de frase | `su2021whitening`, `mu2018allbutthetop`, `li2020bertflow`, `yin2018dimensionality` (princípio) | Corrige a anisotropia documentada (cosseno médio par a par 0,8792 no nosso corpus). `li2020`: +8,16 de Spearman médio sobre o BERT cru (STS-B 47,29→70,72). `su2021`: STS-B 71,43 sobre a MESMA representação, ~1/3 das dims costuma ser ótimo, complexidade O(N) tempo / O(1) espaço. `mu2018`: +4% em STS e +2,32% em classificação (34/40 casos), quase nada em analogia. **O bracket já mediu o caso simples aqui**: o whitening move a componente principal-vs-casos de 0,105 para 0,113 e derruba o cosseno de 0,8792 para −0,0002 — mexe na geometria e quase não na correlação. Baseline = a própria representação sem a correção. | Quase zero: média + SVD sobre a matriz 4.369×768 já publicada em parquet; segundos em CPU, numpy puro, sem re-encode, sem dependência nova. Já existe a variante `bertimbau-whitening`. O custo é de **desenho**: o fit é transdutivo (vê o futuro) e precisa de janela rolling-origin (`whitening_fit_until` já existe). O flow (`li2020`) exige treinar uma rede invertível pequena, sem rótulo, em CPU — custo não reportado, a medir. | tentar agora |
| 3 | Encoder multilíngue congelado adicional, drop-in no bracket | `feng2022labse`, `yang2020multilingualuse` | Cobrem português (LaBSE cobre 109+ idiomas; USE-multilíngue lista pt entre 16). Baseline = os multilíngues que o bracket **já tem** (e5-large, bge-m3). O sinal é ambíguo: LaBSE bate o LASER em recuperação de tradução (83,7 vs 65,5 no Tatoeba) mas é **pior** em similaridade fina (STS Pearson 72,8 vs 79,2 do SBERT) — viés de equivalência de tradução que pode atrapalhar agrupamento/clusterização. Nenhum dos dois mede PT-BR. | Baixo para o LaBSE: um `model_id` novo pelo extra `embeddings`, sem treino nem GPU; +1 variante ~10 min CPU. O checkpoint é pesado (BERT-Base 768, vocabulário de 501k tokens, ~1,5–1,8 GB). O USE-multilíngue exige **TensorFlow** — dependência NOVA e pesada, hoje ausente do stack torch. Valor marginal baixo: o bracket já mapeou que a escolha de encoder move a correlação 0,10–0,29 e nenhuma bate `n_articles`. | tentar depois |
| 4 | Composição de word embeddings estáticos: média ponderada tipo SIF + remoção do 1º componente, pooling sem parâmetros tipo SWEM, n-gramas treinados tipo Sent2Vec, média de vetores aprendidos tipo PARAGRAM | `arora2017sif`, `pagliardini2018sent2vec`, `wieting2015paraphrastic`, `shen2018baseline` | Baseline não supervisionado forte e barato: SIF melhora 10–30% sobre a média de GloVe em STS (ablação: +5% ponderação, +10% remoção, +13% ambos) e bate DAN/LSTM em SICK; SWEM mostra que pooling sem parâmetros basta em documento longo; `wieting2015` mostra que aprender as embeddings dentro da média bate o melhor LSTM por 16,5 de Pearson em 22 datasets. Mas não é uniforme: SIF perde em sentimento (rebaixa "não"); PARAGRAM exige PPDB em inglês e tem correlação −45,1 entre fração de palavras fora do vocabulário e desempenho. Baseline = a média não ponderada. | Exige um asset que **não temos**: vetores de palavra em PT-BR (fastText-PT ~1,2 GB, ou treinar word2vec via gensim = dependência nova; Sent2Vec é C++/FastText = dependência nova). Compute trivial (média + 1 SVD 4.369×300). É um pipeline **diferente** do braço 02 (nível de palavra, sem transformer), não uma troca de configuração. SIF é transdutivo (1º componente sobre o conjunto inteiro) — conflita com o rolling origin. | tentar depois |
| 5 | Fine-tuning do encoder: siamesa/triplet supervisionado, contrastivo, destilação multilíngue | `reimers2019sbert`, `conneau2017infersent`, `gao2021simcse`, `ni2022sentencet5`, `reimers2020multilingual` | Ganhos grandes em STS inglês: SBERT +11,7 sobre InferSent; SimCSE 76,25 não supervisionado / 81,57 supervisionado; ST5 EncDec-large 84,96. O mecanismo do SimCSE (dropout como augmentação, alignment/uniformity) é agnóstico de língua. Baseline = o encoder congelado do braço 02. | Alto e desqualificante: exige **treino**, não inferência. SimCSE assume ~10^6 frases + GPU; SBERT/InferSent exigem rótulos NLI em inglês (SNLI+MNLI) que não existem em PT-BR; o ST5 11B roda a 0,5 exemplo/s em CPU (≈2,4 h só de inferência nos 4.369). Quebra o pé não-treinado que o protocolo 00 fixa. Nenhum número de CPU reportado. | descartar |
| 6 | Sondagem do espaço cross-lingual / estudo de probing | `pires2019mbert` | Explica por que o mBERT transfere entre línguas (subespaço comum, vizinho mais próximo) e onde falha (alvo transliterado). Não é uma técnica a adotar; nenhum resultado específico de português (PT só aparece em listas de idiomas). Baseline = EN-BERT. | n/a como método. Seria re-encodar com mBERT, que o bracket já cobre em espírito (BERTimbau). Custo de computação não reportado. | descartar |

Nota de agrupamento: `su2021`, `mu2018` e `li2020` são a **mesma abordagem** (consertar a anisotropia de
vetores prontos sem treino) e por isso são uma linha só. `yin2018` entra como **princípio** dentro da
linha 2 (viés-variância da dimensão), não como linha própria: a teoria dele cobre só embeddings de
palavra por fatoração de matriz, não transformers. `arora2017sif` compartilha a remoção de componente
mas acrescenta a ponderação por frequência, então fica na linha de composição de word embeddings.
`shen2018` e `wieting2015` apoiam **duas** linhas (pooling e composição) porque medem decisões distintas.

### A1 — Pooling sobre encoder congelado (rank 1)

O bracket do braço 02 declara que o pooling **não é parâmetro livre**: cada encoder é lido do jeito que
seus autores publicaram, e só o BGE-M3 usa `[CLS]` (porque é a definição do modelo). O resultado é que
esse eixo ficou fixo por encoder e nunca foi varrido. A evidência das fichas é forte e convergente —
média ≥ primeiro token (`ni2022`), pooling simples empata com rede profunda em documento longo
(`shen2018`) — e é justamente o regime em que a escolha pesa no nosso uso (agregação/regressão semanal,
não classificação de frase curta). Custa um re-encode por modelo (~11 min para o base), sem dependência
nova, e a mesma passada já pode capturar mean, `[CLS]` e max de uma vez. É o teste mais barato de se
algum eixo de **conteúdo** recupera sinal antes de gastar com qualquer encoder novo.

### A2 — Pós-processamento geométrico pós-hoc (rank 2)

A abordagem mais barata possível aqui: opera sobre os vetores que o braço 02 já gravou, em numpy puro,
sem re-encode. Já tem um pé no bracket (`bertimbau-whitening`) e a própria medição do repo mostra que o
whitening mexe na geometria (cosseno 0,8792 → −0,0002) e quase não na correlação (0,105 → 0,113). O que
falta não é testar whitening de novo, e sim varrer a **intensidade** da correção (o D do
all-but-the-top, o k do whitening), comparar com o flow e decidir a **dimensão** final do covariate — que
o README deixa explicitamente em aberto. O prior é negativo (a whitening já medida quase não moveu a
correlação), então o teste é barato e conclusivo, não promissor.

### A3 — Encoder multilíngue drop-in (rank 3)

Baixo custo, baixo valor marginal: o bracket já tem dois multilíngues que cobrem pt. O único motivo
diferencial seria um modelo otimizado para *similaridade semântica* (nosso uso) em vez de *retrieval*
(e5/bge) — mas as fichas mostram que LaBSE e USE-multilíngue, otimizados para tradução, são piores em
similaridade fina. Vale depois dos eixos baratos.

### A4 — Composição de word embeddings (rank 4)

Resolve um slot (word vectors estáticos) que o transformer do braço 02 já superou, e o custo é um asset
novo pesado (fastText-PT ou treinar do zero) contra um pé mais fraco. Fica como baseline de sanidade *se*
o asset de vetores PT-BR aparecer por outro motivo; não vale criá-lo só para isto.

### A5–A6 — Descartes (rank 5 e 6)

Fine-tuning quebra o pé não-treinado que o protocolo 00 fixa e não tem rótulos PT-BR; o ST5 que dá os
melhores números tem 11B e roda a 0,5 exemplo/s em CPU. A sondagem M-BERT é estudo, não método, e o eixo
cross-lingual não se aplica a um corpus monolíngue.

---

## B. Aplicação — onde usar notícia como fonte de vigilância

**Não** competem com as de representação. A pergunta é o que já foi feito em notícia como fonte de sinal,
o que aquilo mediu, e o que muda para nós.

| # | Abordagem | Fichas | Merit (o que entrega, contra que baseline) | Adoption cost (aqui) | Veredito |
|---|---|---|---|---|---|
| 1 | Notícia como sinal antecedente, fundida a contagens passadas | `ghosh2017temporal`, `kim2019weeklyili`, `kim2021outbreakmedia` | É o enquadramento do próprio repo (notícia → doença), com evidência em dengue. `ghosh2017` funde tendências de tópico lagadas com contagens passadas (ARX + ElasticNet) e bate o baseline que ignora a notícia (Casecount-ARMA) em **todas** as doenças avaliadas — dengue da Índia e da China entre elas (China: NRMSE 1,076 → 0,549). `kim2019`: contagem semanal por keyword acerta 0,867 em subida/queda de ILI, mas **sem baseline**. Baseline explícito: o modelo só-contagens (`ghosh2017`). | Baixo compute (Gibbs + ElasticNet em CPU; sem GPU). Já temos `news_volume` (braço 01), o léxico (palavras-semente) e o backbone de fusão do protocolo 00. O custo é de **desenho**: definir o lag notícia→caso e montar o alvo. Nos EUA o ganho do `ghosh2017` é ruído (0,445→0,430) e não há teste de significância — o mérito é o enquadramento, não o número. | tentar agora |
| 2 | Normalização do volume de notícia por local | `kim2021outbreakmedia` | Normaliza as contagens por local para lidar com volume de publicação desigual — exatamente a limitação 2 do README (viés de menção por UF) e o descompasso espacial do protocolo 00. Baseline = modelos sem normalização. | Trivial: é uma transformação sobre `news_volume`, que já existe. Sem dependência nova, sem re-encode. O README já diz que a feature por UF deve ser lida relativa à própria história (RJ×SP invertem em ~2015). | tentar agora |
| 3 | Modelo de tópicos temporal supervisionado por palavras-semente | `ghosh2017temporal` | Variante supervisionada do braço 03: LDA com palavras-semente como prior + tendência temporal do tópico como covariável. Dengue é uma das doenças avaliadas. Mas a qualidade dos tópicos é julgada só **visualmente** (Figs. 2–5), sem métrica de tópico. Baseline = ARMA só-contagens. | tomotopy já está instalado (é o motor do braço 03); o custo é construir as sementes por doença e o modelo supervisionado, que o braço 03 (DMR não supervisionado) não tem. Sem dependência nova. Sem tempo reportado. | tentar depois |
| 4 | Filtro/classificador de relevância da notícia | `jang2019word2vec`, `gautam2025attention` | `jang2019`: word2vec+CNN bate inicialização aleatória em ~7–9 pts de acurácia para separar notícia relacionada de publicidade (0,9341 vs 0,8475), mas o baseline é **só o vetor aleatório**. `gautam2025`: Bi-LSTM+atenção (98,25%) bate um Transformer pequeno (92,76%) em manchete surto/não-surto, **sem baseline externo**. Baseline fraco ou ausente nos dois. | Nosso corpus já vem filtrado por uma query de dengue, o que reduz a necessidade de um filtro de relevância. Exigiria rótulos surto/não-surto que não temos; o encoder do `gautam2025` (all-MiniLM) é inglês; `jang2019` exige tokenizador coreano e reimplementar CNN. Sem número de tempo/CPU reportado. | tentar depois |
| 5 | Sentimento (VADER) + LDA descritivo sobre décadas de cobertura | `huang2018publicopinions` | Moldura de ler volume + sentimento + tópico como atenção pública a doença ao longo do tempo; discute o Zika no Brasil em 2016 (domínio próximo). Mas é puramente descritivo: **sem métrica, sem baseline**; VADER não foi avaliado para o corpus; LDA com K=1 fixo. | VADER é léxico inglês (não cobre PT-BR); UMLS/PheWAS são inglês-only. O LDA já é coberto por tomotopy (braço 03). Para PT-BR seria preciso um léxico de sentimento novo. Runtime não reportado. | descartar |
| 6 | Previsão de surto por matriz multi-doença × multi-local | `kim2021outbreakmedia` | Mostra que contagens de mídia por doença × país alimentam um classificador de surto (SSL 0,838 vs SVM 0,732). Mas sem baseline ingênuo, com um único ano de dados e rótulo derivado da própria contagem (circular). | Bloqueado por dados: exige o feed Medisys (não público) com 115 doenças × 237 países e ground truth por doença/país. Nosso corpus é **uma** doença (dengue) em 28 locations — a matriz não existe. Não reprodutível (dados "sob pedido"). | descartar |

### B1 — Notícia fundida a contagens passadas (rank 1)

É a ficha de aplicação que responde "a notícia prevê caso melhor que o passado da série?", que é a
pergunta do protocolo 00, e traz o baseline que o protocolo exige (Casecount-ARMA, que ignora o texto).
O ponto de adoção é honesto: o modelo conjunto supervisionado-temporal não existe pronto no tomotopy,
mas a *ideia* — tendência tópica lagada como regressor externo — pode ser testada hoje com as shares
EW×tópico que o braço 03 já publicou, num modelo linear com numpy. É "tentar agora" porque responde a
uma pergunta que temos, não porque o artigo seja metodologicamente forte (o ganho nos EUA é ruído).

### B2 — Normalização por local (rank 2)

Pequena e barata, mas ataca uma limitação que o README declara. O RJ×SP que inverte em ~2015 é a
evidência de que a feature por UF precisa ser lida relativa à própria história; normalizar por local é o
passo mínimo.

### B3 — Tópicos temporais supervisionados por sementes (rank 3)

É a evolução natural do braço 03, mas a evidência do artigo sobre a qualidade dos tópicos é visual. Vale
depois de o braço 03 atual ser avaliado no protocolo 00.

### B4 — Filtro de relevância (rank 4)

Útil só se aparecer ruído de relevância; hoje o corpus já é filtrado por query, e ambos os artigos têm
baseline fraco e rótulo autodefinido.

### B5–B6 — Descartes (rank 5 e 6)

A `huang2018` não mede nada contra nada, e a parte reaproveitável (tópicos) já existe no braço 03; a
`kim2021` exige uma matriz multi-doença × multi-país que não temos e um feed não público.

---

## C. Cross-cutting (decisão de desenho, não de artigo)

- **representacao — nenhuma ficha mede PT-BR, notícia, documento longo ou vigilância.** As 17 fichas de
  representação avaliam similaridade de frases curtas em inglês (STS/SentEval/SICK). A técnica é
  agnóstica de língua; a **evidência** não é. Nenhum número deles pode ser assumido para o nosso corpus.
- **aplicacao — a tarefa é a nossa, a língua não.** As 6 fichas de aplicação testam notícia→doença (a
  tarefa certa), mas em inglês, coreano ou chinês-traduzido; nenhuma em português. É a mesma lacuna que o
  braço 01 já declara: o caso PT-BR é a contribuição, não a dívida.
- **representacao — a unidade é diferente da nossa.** A biblioteca de representação compara **frases
  curtas**; nosso documento é o artigo inteiro (mediana 1.390–2.452 chars, p90 5.051). Só o braço 02
  enfrenta truncamento (39% em 512 tokens). Mas o repo já provou que truncar **não** é o gargalo:
  `title-only` (0% truncado) supera o texto completo (0,156 vs 0,105). "Todos assumem 512 tokens" é
  verdade sobre a biblioteca de representação; "por isso perdemos sinal" é falso sobre o repo.
- **representacao — o ganho da literatura vem de fine-tuning com rótulos NLI em inglês** (SBERT, SimCSE,
  Sentence-T5, PARAGRAM, InferSent, MKD). O repo fixou o pé oposto: tudo congelado e sem rótulo, como o
  léxico do braço 01. Os números de manchete desses artigos **não estão disponíveis** sem sair do pé do
  repo.
- **os dois grupos otimizam coisas diferentes, e por isso seus números não são comparáveis.**
  Representação otimiza similaridade de cosseno (métrica intrínseca de par de frases); aplicação usa
  **contagem** de notícia e erro a jusante. Dentro da representação, é a contagem que ganha no nosso
  corpus (`n_articles` +0,297 bate todo eixo denso do bracket) — o que a literatura de aplicação assume
  desde o início (o sinal é o volume, não a qualidade do embedding).
- **transversal — "não reportado" é o custo da maioria dos pipelines.** Quase nenhuma ficha traz tempo de
  CPU, teste de significância ou variância. Custo não reportado é incerteza, e incerteza não é barato: as
  linhas com "não reportado" ficam em "tentar depois", não em "tentar agora".
- **aplicacao — o baseline que o protocolo 00 exige (ablação "sem texto" / texto embaralhado) aparece
  explícito só em `ghosh2017` (Casecount-ARMA)** e foi omitido em `kim2019`, `kim2021`, `gautam2025`,
  `jang2019` e `huang2018`. É a lacuna mais recorrente no grupo de aplicação, e é justamente o número que
  o artigo precisa reportar.
- **representacao — a correção de geometria é transdutiva por construção.** Whitening (`su2021`), SIF
  (`arora2017`) e flow (`li2020`) estimam parâmetros sobre o conjunto inteiro de vetores, o que vê o
  futuro num problema de previsão. O braço 02 já tem `whitening_fit_until` para isso; as linhas que
  adotam essa família só entram no protocolo 00 se passarem uma origem, não o default.
- **representacao — "encoder multilíngue cobre português" não é "foi avaliado em português".** LaBSE,
  USE-multilíngue e mBERT listam pt, mas nenhum mede PT-BR; o único benchmark de transferência deles
  (SentEval) é inglês e neles o multilíngue perde para o monolíngue. Cobertura de vocabulário não é
  evidência de qualidade em português.
- **aplicacao — a feature que entra no modelo é CONTAGEM, não o embedding.** `kim2019`, `kim2021` e
  `ghosh2017` usam contagem de notícia (volume/tópico); o embedding, quando existe, serve para
  selecionar palavras-chave ou como entrada de um classificador de relevância. Isso reforça o achado do
  braço 02 (`n_articles` bate o vetor denso) e sugere que o vetor denso só se justifica se agregar além
  do volume.

---

## D. First move

Re-encodar o **BERTimbau UMA vez** capturando `mean`, `[CLS]` e `max` na mesma passada (~11 min de CPU,
sem dependência nova) e comparar a correlação da componente semanal de cada pooling com os casos contra o
+0,297 de `n_articles` — é o eixo que o bracket deixou fixo por encoder, e o teste mais barato de se
algum eixo de **conteúdo** recupera sinal antes de gastar com qualquer encoder novo.

---

## E. O que ficou de fora e por quê

- **`ni2022sentencet5`** virou evidência da linha de pooling (A1), não linha própria: seu achado central
  é "média do encoder > primeiro token", a mesma decisão; o resto (escala até 11B) cai no descarte de
  fine-tuning.
- **`cer2018use` e `yang2020multilingualuse`** idem: `cer2018` entra como evidência de pooling/média (o
  PDF é o USE de Cer et al. 2018); `yang2020` como evidência de encoder multilíngue drop-in (A3).
- **`reimers2019sbert`** aparece em A1 (pooling) e A5 (supervisionado): facets distintos do mesmo artigo.
- **`yin2018dimensionality`** entra como princípio dentro de A2 (viés-variância da dimensão), não como
  linha: a teoria cobre só embeddings de palavra por fatoração de matriz.
- **`pires2019mbert`** é estudo de probing, não método a adotar; a contribuição útil (mBERT cobre pt)
  está dobrada em A3.
- **`kim2021outbreakmedia`** entra em duas linhas de aplicação (a de fusão com contagens e a de matriz
  multi-doença) porque o artigo faz as duas coisas; a segunda é a que cai no descarte.
- **`jang2019`, `gautam2025`, `huang2018`** caem em "tentar depois"/"descartar" por resolverem um
  problema que não temos (relevância já implícita na query, matriz multi-doença inexistente), por alvo
  circular, ou por não trazerem métrica nem baseline.

---

## F. Perguntas abertas (para o planner / protocolo 00)

- Qual é o horizonte de previsão (1 semana? 4?) — o protocolo 00 ainda não fixou, e isso muda o que "prevê
  melhor" significa para todas as linhas acima.
- O alvo é nível ou log, BR ou UF? (pendência do protocolo 00.)
- O forecaster consome o vetor de 768/1024 dims inteiro ou uma PCA? A dimensão do covariate ficou
  explicitamente em aberto no README, e o whitening mostra que a resposta depende do eixo (PC1 explica
  1,1% no variant branqueado).
- Como os braços tratam as 8 semanas sem artigo e os 180 artigos em inglês que passam pelo gate de
  idioma — pendência de protocolo 00 que afeta os três braços.
- O ganho de geometria (whitening/flow) se sustenta sob rolling-origin com a origem passada, ou só existe
  na leitura transdutiva atual?
