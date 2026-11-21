# Ranking das abordagens — modelagem de tópicos

Artefato do workflow de pesquisa de referência sobre **modelagem de tópicos** (48 fichas). Ranqueia
**abordagens**, não artigos, e separa os dois grupos que as fichas marcam: `representacao` (como
transformar texto em número) e `aplicacao` (onde usar isso no nosso domínio). Os dois grupos **não
competem entre si** — por isso há dois `rank 1`, um em cada tabela, e a numeração reinicia.

Contexto que define "usável": corpus de 4.369 artigos da Agência Brasil (dengue, PT-BR, 965 semanas,
28 locations = BR + 27 UFs); CPU only, sem GPU; extras fixados em `pyproject.toml` (`embeddings` =
torch+transformers ~800 MB, `topics` = tomotopy); braços 01 (léxico), 02 (bracket de 6 configs de
embedding) e 03 (DMR/tomotopy, k=15 por coerência `c_v`) já construídos e medidos; custo de
dependência nova é alto, e o transform precisa rodar em CPU em minutos, não horas.

Fontes de custo: `src/pipeline/news/README.md`, `notes/00-protocolo-comparacao.md`, `pyproject.toml`.

**Nota de composição.** 34 fichas marcam `representacao` e 14 marcam `aplicacao`. A família de
representação é dominada por **modelagem de tópicos** (LDA e derivados, neurais e não), e o braço 03 já
é um modelo de tópicos; a pergunta real de representação aqui não é "qual modelo novo", é "vale a pena
trocar/adicionar um modelo ao DMR que já existe". O achado principal é que **nenhuma representação nova
é "tentar agora"**: a jogada de maior valor é endurecer a seleção de k e a estabilidade do braço 03 com
receita que as fichas dão a custo zero de dependência. No grupo `aplicacao`, o achado é o oposto — há
desenhos de notícia→série que respondem perguntas que o protocolo 00 já fez, e um deles (`ghosh2017`)
é o trabalho publicado mais próximo da nossa tarefa.

Onde eu discordo da marcação, digo na própria linha.

---

## Representação — como transformar texto em número

Alternativas entre si. Dois "tentar agora" (ambos endurecem o braço 03 que já existe), quatro "tentar
depois", oito "descartar".

| # | Abordagem | Fichas | Merit (o que entrega, contra que baseline) | Adoption cost (aqui) | Veredito |
|---|---|---|---|---|---|
| 1 | Seleção robusta de k + estabilidade de semente para o modelo de tópicos existente | `rieger2024`, `hoyle2022`, `gan2021`, `krasnov2019`, `zhao2015`, `meaney2023`, `hecking2018`, `vangara2021`, `zheng2023` | Receita medida para o que o braço 03 declara em aberto ("estabilidade entre sementes não foi estabelecida"). Rieger: escolher o **medoide** de R rodadas de LDA dá reliability 0,8858 vs 0,8425 (rodada aleatória) e 0,8674 (perplexity), ganho ~2× o da perplexity; recomenda ≥50 replicações. Hoyle: modelos neurais são **piores** que o LDA clássico em estabilidade (B=0,22 no MALLET vs 0,42-0,49 nos neurais, Wiki k=25) e em alinhamento; ensemble bate o membro mediano em 97% de 400 contextos. Gan: índice composto escolhe 13 tópicos contra os 20 reais, o mais próximo (perplexity 8, coerência 7, JS 30, HDP 59). Zhao: heurística RPC escolhe 20 em 80% de 50 execuções, entropia 1,0 vs 1,853 da perplexity. Contra-evidência útil: Meaney mostra que os índices **discordam** (nenhum escolhe o K=50 preferido por humanos); Krasnov mostra que CH/silhouette **não** determinam k; Hecking mostra que o LDA muda ao remover 50 de 6.638 documentos. Baseline = perplexity e coerência de um só índice. | Zero dependência nova para a receita tomotopy (Rieger/medoide, RPC, índice composto); reusa o `topics` já pinado, CPU puro. O custo é **multiplicativo** (R rodadas × grade de k) e o artigo não mede o nosso tamanho; o caso mais próximo (Rieger, usatoday 7.453 textos, R=100) levou ~3,4 h **em R** (economy 1.855 textos → 8 min). Reimplementar S-CLOP (medoide + Jaccard por tópico) em Python sobre as rodadas do tomotopy é engenharia modesta. Estimativa minha, não do artigo. A exceção é `zheng2023`, que exige BERT + density-peak clustering sem código liberado — esse pedaço não é barato. | **tentar agora** |
| 2 | Métricas de qualidade além da coerência (estabilidade, diversidade TSD, MPCT/JCD) | `hoyle2021`, `morstatter2016`, `wu2024` | Companheiro de medição do rank 1. Hoyle: a avaliação automática declara um vencedor quando a humana não vê diferença; o NPMI favorece tópicos esotéricos (familiaridade 70% no modelo que elege vs >90% nos outros); a melhor métrica erra ~1/5 das vezes. Morstatter: MP e MPCT medem dimensões diferentes (ρ=0,09); o melhor proxy automático é a distância Jiang-Conrath (ρ=−0,844). Wu: a métrica TSD correlaciona 0,986 com humanos vs 0,957 de TU/TD. Baseline = julgamento humano e word intrusion. | As métricas baratas (NPMI, co-ocorrência, entropia, TSD — só pares de palavras, agnóstica de língua) rodam em CPU sem dependência nova. JCD e No. Word Senses exigem **WordNet inglês** (não temos PT). MPCT exige crowdsourcing. | **tentar agora** |
| 3 | Modelo de tópicos por agrupamento de embeddings (BERTopic, CETopic, SBERT+KMeans) | `grootendorst2022`, `zhang2022`, `janssens2025` | Pipeline embed→UMAP→HDBSCAN→c-TF-IDF: melhor coerência (NPMI) contra LDA/NMF/CTM/Top2Vec nos três corpora (.166/.167/.066 vs LDA .058/.014/−.011). Clusterizar SBERT/SimCSE + seleção de palavras por TFIDF×IDFi bate NTMs (NPMI 0,206/CV 0,744 vs CombinedTM 0,001/0,443 no M10). Janssens: redução aglomerativa com c-TF-IDF dá +0,10 de diversidade sobre a redução direta; prompting em LLM é melhor mas caro. Baseline = LDA, NMF, CTM, Top2Vec, ProdLDA. | Dependência nova: `umap-learn` + `hdbscan` (não estão nos extras; reusa o encoder do extra `embeddings`). Tempo em CPU sobre 4.369 artigos não reportado (os artigos medem com GPU: T4, P100). E conflita com a **independência** que o braço 03 exige do braço 02 — o README já rejeitou o BERTopic por compartilhar encoder e por o HDBSCAN ser instável sob densidade desigual ao longo de 24 anos. | tentar depois |
| 4 | Modelos de tópico com embeddings (ETM, D-ETM, LF-LDA) | `dieng2020`, `dieng2019`, `nguyen2015` | Tópico como vetor no espaço de embeddings das palavras: robusto a vocabulário grande e a stop words. ETM-PWE: qualidade de tópico 0,0396 vs LDA 0,0182 (~2×) no NYT K=300. LF-LDA: injetar word2vec sobe F1 em >5% no corpus pequeno (Purity +4,4% em 40 tópicos). Contra: D-ETM **perde** para o D-LDA no SCIENCE e sua coerência é menor no UN; os ganhos de LF-LDA somem no corpus grande. Baseline = LDA, NVDM, ProdLDA, D-LDA. | `torch` já está no extra `embeddings`, mas o código é PyTorch próprio (repositórios dos autores), não `tomotopy`. Custo em CPU **não reportado**; D-ETM é uma VAE recorrente (LSTM) sobre timesteps e o artigo testa no máximo 46 passos contra os nossos 965 — risco de regime. | tentar depois |
| 5 | NMF como representação alternativa ao LDA (incl. dinâmico em duas camadas) | `greene2017`, `feng2020`, `albalawi2020`, `muthusami2024` | Greene: NMF bate LDA em 94,7% de 300 experimentos de coerência, e bate o DTM probabilístico em Cv (0,458 vs 0,424) — mas empata em TC-W2V (0,277 vs 0,276). A ideia central — dividir a série longa em janelas disjuntas e rodar uma **segunda camada** sobre os tópicos de cada janela — mapeia direto nas 965 semanas. Albalawi: o "melhor" muda com o recorte (PCA lidera por nº de tópicos, LDA por nº de features) e o NMF é o mais rápido. Muthusami: NMF dá clusters mais compactos que o LDA no mesmo dado (silhueta 0,955 vs 0,156). Feng (TRNMF) regulariza NMF com matriz semântica de embeddings, mas é para texto curto. Baseline = LDA (MALLET), DTM. | NMF do scikit-learn **não está** nos extras (nem scikit-learn é dependência); a coerência por TC-W2V exige `gensim` (word2vec). CPU-friendly, mas pipeline novo. Custo não reportado. | tentar depois |
| 6 | Embedding contextualizado como entrada do modelo (ZeroShotTM/CombinedTM) + concat tópico+encoder (tBERT) | `bianchi2021`, `peinelt2020` | ZeroShotTM troca o BoW por um embedding de documento SBERT **multilíngue**; permite treinar em inglês e inferir em PT-BR zero-shot, com match de tópico 78% (K=25) e português a 2,26/3. Mas **não ganha coerência**: 0,1632 vs 0,1644 (CombinedTM) e 0,1658 (Neural-ProdLDA) — empata. tBERT: concatenar distribuição de tópicos ao `[CLS]` sobe F1 sobretudo em vocabulário de domínio (SemEval A .704→.768), mas em 3 de 5 datasets o ganho é .003–.008, dentro do ruído, e cai no SemEval C. Baseline = LDA, Neural-ProdLDA, CombinedTM; BERT vanilla. | Nova dependência: `sentence-transformers` + modelo SBERT multilíngue (~470 MB); o VAE não está no tomotopy. Bianchi mede 1,2 s/época **em GPU**; CPU não reportado. A parte tBERT é de **similaridade de pares** (paráfrase), fora da nossa tarefa, e exige rótulos de par. | tentar depois |
| 7 | Modelos de tópico neurais sobre BoW (ProdLDA/AVITM, NQTM) | `srivastava2017`, `wu2020` | ProdLDA sobe coerência (0,24 vs LDA-Gibbs 0,17 no 20NG k=50) e é rápido (46 s vs 18 min), mas a perplexidade é **pior** que a do LDA (1172 vs 728) e o ganho depende de dois truques de otimização frágeis (LR alto + batch norm). NQTM mira texto curto (4,6–10,3 tokens/doc) — o regime não é o nosso. Baseline = LDA-Gibbs, DMFVI, NVDM. | Código VAE próprio (não está no tomotopy; o de 2017 é Theano); CPU não reportado; a orientação para texto curto é incompatível com notícia longa. O braço 03 já cobre "distribuição de tópicos como feature". | descartar |
| 8 | Modelos de tópico para texto curto (WNTM) | `zuo2015` | WNTM (rede de co-ocorrência) bate LDA/BTM em microblog curto (Weibo, p<0,001), mas o próprio artigo mostra que em **texto normal** (Wikipedia) **não** há ganho significativo. Baseline = LDA, BTM. | Não está no tomotopy; código novo; CPU; custo O(c) vezes o LDA, sem wall-clock medido. O benefício principal só existe em texto curto, e o nosso documento é o artigo de notícia (p50 ~438 tokens), não o tweet. | descartar |
| 9 | Modelos de tópico supervisionados / multi-anotador (MA-sLDA, PC-LDA) | `rodrigues2017` | MA-sLDAc bate os baselines de crowdsourcing (Reuters/LabelMe) modelando matriz de confusão por anotador. Baseline = votação majoritária e LDA+LogReg. | O modelo consome **rótulo por documento com identidade de anotador**; nosso alvo é agregado por semana×location, não por notícia — não há o que estimar. Código em MATLAB/C++. | descartar |
| 10 | Embeddings contextuais para mudança semântica lexical (agregação online + Wasserstein) | `montariol2021` | Agregação limitada a 200 vetores/palavra corta a memória de 768 GB para 4,7 GB/fatia; bate os baselines não-escaláveis de clusterização (0,474 vs 0,391 Spearman) mas **perde** para um baseline simples não-contextual (SGNS+OP+CD 0,533). Baseline = clusterização não-escalável; gabaritos SemEval/COHA/DURel. | Fine-tuning de BERT + extração de embeddings para todos os tokens em CPU: **não reportado**, provavelmente caro. A tarefa (drift de sentido de palavra) não é a nossa. POT para a Wasserstein. | descartar |
| 11 | STM (structural topic model) com covariáveis de documento | `roberts2019` | Metadado de documento como covariável de prevalência — mapeia nas 28 locations × 965 semanas. Benchmark: 0,7 min vs 96,7 min do CTM, held-out LL ligeiramente melhor (−6,900 vs −6,935). Baseline = CTM/topicmodels. | Pacote **R** — o repositório rejeitou explicitamente carregar R. E o mecanismo de covariável **já está no braço 03** (DMR condiciona a prevalência ao período); DMR é o substituto Python-nativo. | descartar |
| 12 | Pré-processamento: stemming e momento de remoção de stopwords | `schofield2016`, `schofield2017` | Resultados **negativos**, e por isso úteis: stemming não melhora coerência depois de controlar o vocabulário e pode piorar a verossimilhança e a estabilidade; remover stopwords antes ou depois do treino é indistinguível (NYT 10 tópicos: −10.830 vs −10.826). Baseline = controle sem stemming / sem remoção. | Nada a rodar. Estes resultados **validam** o que o braço 03 já faz (sem lematizador, lista de stopwords mínima, dobra de acentos). O único insumo ausente é um stoplist PT-BR. | descartar |
| 13 | Harness de comparação/otimização de tópicos (OCTIS) | `terragni2021` | Embrulha LDA/NMF/LSI/HDP e NTMs numa interface única e faz busca bayesiana de hiperparâmetros. Baseline = nenhum experimento (é system demo; a evidência é uma tabela de recursos). | Não é representação; dependência nova (`scikit-optimize`); a BO multiplica execuções do modelo. A lição (usar BO para k) cabe no rank 1 sem o pacote. | descartar |
| 14 | Surveys de modelos de tópico neurais | `zhao2021` | Taxonomia e catálogo de modos de falha (colapso de tópicos, tópicos repetitivos); acurácia preditiva e qualidade interpretativa frequentemente descorrelacionadas. Sem experimento próprio. | Ler não custa nada; não há modelo a adotar. Alimenta `cross_cutting`. | descartar |

### Abordagem por abordagem (representação)

**1. Seleção robusta de k + estabilidade (tentar agora).** É a única linha de representação que ataca um
item que o **braço 03 declara aberto**: "estabilidade dos tópicos entre sementes não foi estabelecida".
Rieger dá o procedimento (rodar R vezes, escolher o medoide) e Hoyle dá a métrica (distância total entre
tópicos com RBO top-weighted e emparelhamento bipartido). Nada disso exige dependência nova — reusa o
`tomotopy` já pinado. A contra-evidência de Meaney, Krasnov e Hecking (os índices discordam; nenhum
determina k; remover 50 de 6.638 documentos já muda o LDA) não enfraquece a linha: é o argumento para
reportar **vários** diagnósticos em vez de confiar no `c_v` sozinho, que é o que o braço 03 faz hoje.
Custo: refits multiplicativos, estimativa minha de minutos a poucas horas em CPU, não medido pelo artigo.
O `zheng2023` (escolher k por clustering multi-view de BERT + view temporal DF-IDF) tem a ideia certa,
mas exige BERT, density-peak clustering e código que os autores não liberaram — por isso entra aqui só
como referência, não como receita adotável.

**2. Métricas além da coerência (tentar agora).** Barato e diretamente acionável: reportar corpus de
referência, janela e top-N das métricas (Hoyle), somar diversidade (TSD de Wu é agnóstica de língua) e
não tratar coerência como verdade. É o par de medição do rank 1.

**3. BERTopic/CETopic (tentar depois).** Maior coerência medida entre os pipelines baseados em
embedding, e a redução aglomerativa do Janssens é barata. Mas exige `umap-learn`+`hdbscan` (fora dos
extras) e colide com o princípio de independência do braço 03 em relação ao braço 02 — o mesmo motivo
que fez o README rejeitar o BERTopic. Fica como candidato a uma quarta representação, não como
substituto do DMR.

**4. ETM/D-ETM/LF-LDA (tentar depois).** Ideia representacional forte — tópicos e palavras no mesmo
espaço — e robustez a vocabulário grande/stop words interessa. O bloqueio é operacional: código PyTorch
próprio, custo em CPU não medido, e a variante temporal (D-ETM) foi testada em ≤46 timesteps contra os
nossos 965.

**5. NMF (tentar depois).** Alternativa barata em CPU, com evidência de coerência competitiva/superior
(Greene 94,7%). A camada dupla por janelas de tempo é o pedaço que mapeia nas 965 semanas. Custo:
`scikit-learn`/`gensim` fora dos extras.

**6. ZeroShotTM/CombinedTM + tBERT (tentar depois).** O atrativo único é o caráter **multilíngue**: um
modelo de tópico PT-BR sem construir vocabulário BoW PT, e o português está entre as quatro línguas de
teste. Mas não há ganho de coerência sobre os baselines neurais, e a parte tBERT é de similaridade de
pares (fora da tarefa, exige rótulos).

**7–14. Descartar.** NTMs sobre BoW e modelos de texto curto não batem o regime (notícia longa) e/ou
trocam acurácia por velocidade; supervisionados exigem rótulo por documento que não existe; mudança
semântica lexical é outra tarefa; STM é R e o DMR já é o substituto; stemming/stopwords são resultados
negativos que validam o desenho atual; OCTIS é harness; surveys não se adotam.

> **Correção da rodada anterior.** "Nenhuma ficha testa a nossa tarefa" é **verdadeiro do grupo
> `representacao`** (nenhuma das 34 mede previsão de casos) e **falso da biblioteca inteira**: as de
> `aplicacao` testam notícia/série de casos — `ghosh2017` estima casos de dengue a partir de
> tendências de tópico de notícia; `chuluunsaikhan2020`, `chiu2024`, `mcgough2017` e `tizzoni2020` fazem
> previsão/atenção de série a partir de texto. A frase precisa do qualificador de grupo.

---

## Aplicação — onde usar, no nosso domínio

**Não** competem com as de representação. A pergunta é o que já foi feito em notícia (sobretudo de
língua portuguesa) como fonte de vigilância, o que aquilo mediu, e o que muda para nós.

| # | Abordagem | Fichas | Merit (o que entrega, contra que baseline) | Adoption cost (aqui) | Veredito |
|---|---|---|---|---|---|
| 1 | Sinal de notícia como regressor exógeno para a série de casos (1 passo à frente), com defasagem de 2–3 semanas | `ghosh2017`, `chuluunsaikhan2020`, `mcgough2017`, `tizzoni2020` | O desenho publicado **mais próximo da nossa tarefa**. Ghosh: tendências de tópico temporal de notícia (HealthMap) → contagem de casos, com regressão autoregressiva regularizada (EpiNews-ARNet) obtendo o menor NRMSE em **8 de 10** combinações {país, doença} (dengue China 1,076→0,549); o baseline que só usa casos passados (Casecount-ARMA) **nunca** vence. Chuluunsaikhan: LDA+TF-IDF+LSTM corta o RMSE em 37–66% vs baselines estatísticos e de ML. McGough: combinar busca+tweet+notícia com histórico bate o baseline AR (Colômbia rRMSE 40,5→30,0), mas o sinal de notícia sozinho é o mais fraco (piora até 25 pontos em alguns casos) e chega 2–3 semanas atrasado. Tizzoni: o **volume de mídia dirige a atenção** (Wikipedia) mas a **incidência da doença não** (R²=−0,398); kernel de memória τ≈2 semanas sobe o R² em ~20% (0,76). Baseline = AR/ARMA, ARIMAX, ridge, RF, GB. | Ghosh usa seed words + contagens de caso (temos SINAN) mas o modelo **não está no tomotopy**; Chuluunsaikhan é LDA+TF-IDF+LSTM (o `torch` já está). McGough depende de Google Trends/Twitter/HealthMap — **não temos** esses fluxos. Tizzoni depende de pageviews geo-localizados (sob NDA). Nenhum reporta tempo em CPU. O barato é reaproveitar o **desenho** sobre as features do braço 03, que já existem. | **tentar agora** |
| 2 | Notícia em língua portuguesa / de baixo recurso como fonte de vigilância (precedente + moldura de fonte única) | `melo2021`, `pruss2019` | Responde "já foi feito em PT-BR?". Melo: **a única referência de notícia PT-BR com LDA** (18.413 artigos UOL, COVID; coerência 0,511 na notícia vs 0,446 no Twitter) — mas teve de **traduzir tudo para inglês** para aplicar o VADER (léxico EN). Pruss: análise só em inglês perde a América Latina (menos de 3,5% dos tweets da Venezuela são em EN); volume de discurso correlaciona com incidência (ρ=0,398, p=0,009). Baseline = nenhum (são descritivos). | Moldura e precedente: valida a escolha de fonte única PT-BR e **desaconselha traduzir** (Melo). Não há nada a rodar sobre o nosso corpus além de citar. Custo do artigo: corpora minúsculos, sem baseline, metodologia manual (Melo usa MALLET/JVM + googletrans + VADER + spaCy PT — dependências novas que **não** precisamos adotar). | **tentar agora** |
| 3 | Tópicos de notícia alimentando um modelo supervisionado a jusante (incl. ablação "com vs sem texto") | `chiu2024` | O padrão que o protocolo 00 já exige. Chiu: adicionar os tópicos do BERTopic sobe o AUROC da LSTM de 0,7532 para 0,7994 (ICs 95% não se sobrepõem) — mas a acurácia de 0,9316 é medida sobre conjunto **balanceado por SMOTE** (10,59%→48,65%), o que é enganoso. Baseline = os mesmos modelos **sem** os tópicos. | A ablação "com vs sem texto" é a **nº1 do protocolo 00** e já é implementável com os braços 01–03 — não precisa adotar BERTopic+LSTM. Custo de adotar o pipeline inteiro: `bertopic`+`umap`+`hdbscan`, grid search de LSTM, SMOTE; nenhum tempo reportado. | tentar depois |
| 4 | Dinâmica de atenção/sentimento da notícia (fração de cobertura + skew de sentimento relativo) | `krawczyk2021` | Métrica de cobertura barata e comparável: Krawczyk mede COVID como **25%** da cobertura de capa de 2020 (faixa 20–30%) contra 2,50% de TRUMP, com listas de palavra-chave já feitas para EN/DE/FR/ES/IT/RU; o **Relative Sentiment Skew** normaliza por fonte e evita comparar veículos com vieses diferentes (rsskew do COVID ~−0,04 vs −0,53 do câncer). Baseline = distribuição de sentimento dos demais artigos da mesma fonte e tópicos-âncora. | A metade de cobertura (fração por palavra-chave) é trivial em CPU e não tem dependência nova. A metade de **sentimento depende do VADER, que é inglês** — não há equivalente PT oficial citado, então exigiria léxico PT novo. | tentar depois |
| 5 | Modelo de tópico de notícia com covariáveis de documento (STM/DMR aplicado a notícia) | `meier2024` | STM sobre 63.743 artigos de notícia (clima, Dinamarca) com **ano e veículo como covariáveis de prevalência** — o eixo 965 semanas × 28 locations; retém 85 tópicos após validação humana (concordância 91,11%); mantém artigos com menção única ao tema (diversidade) e usa bootstrap para comparar grupos; viés de veículo ≤~1% no nível de tema. Baseline = nenhum (descritivo). | Meier usa **R** (`stm`); o mecanismo de covariável **já está no braço 03** (DMR condiciona prevalência ao período). Não há nada a rodar além de copiar o desenho de validação humana e bootstrap. | tentar depois |
| 6 | Evidência de seleção de k/modelo específica de notícia | `weisser2022`, `doogan2023` | Corrobora o rank 1 de representação com evidência de notícia/texto curto: Weisser: a coerência pode coroar o modelo **errado** (o LDA parece vencer GSDMM/GPM por coerência, mas perde na simulação de pseudo-documentos, com >20.000 de 100.000 documentos sem tópico). Doogan (SLR de 189 artigos): LDA em 79,79% dos estudos, perplexity como medida mais comum (22,04%) — ambos criticados; "tendência preocupante" de copiar k de outro estudo. Baseline = perplexity, coerência, índices de cluster. | Ler é barato; implementar as métricas cai no rank 1. Doogan é revisão (nada a rodar); Weisser exige uma dependência nova (GPyM_TM) só para o experimento sintético. Não duplica o rank 1 — é a evidência **de notícia** que o sustenta. | tentar depois |
| 7 | Modelagem de tópicos em texto curto de mídia social (Twitter) | `egger2022`, `kagashe2017` | Comparações majoritariamente **qualitativas**: Egger conclui por julgamento humano (BERTopic/NMF > Top2Vec/LDA) sem métrica entre modelos; Kagashe filtra menções a "consumo real" antes de modelar (F1 0,82 vs 0,79 de 1-grama). Baseline = os próprios métodos entre si, ou léxico/1-grama. | A unidade é o **tweet** (≤280 chars), não o artigo de notícia; corpora minúsculos; dependências novas (spaCy, MALLET, MetaMap/Java) e inglês-específicas. Nada aqui responde às nossas perguntas. | descartar |
| 8 | Modelo de tópico sobre dado clínico codificado (PC-LDA) | `hughes2020` | PC-LDA comprime 9.256 códigos clínicos em 10 tópicos — mas os tópicos **empatam** com a baseline de alta dimensão (AUC 0,627 vs 0,628) e **perdem** para o ensemble de árvores (0,661); o ganho alegado é interpretabilidade, não discriminação. Baseline = representação de 9.256 code words + ensemble de 512 árvores. | Domínio distante (códigos ICD/CPT, não texto PT-BR); exige rótulo de desfecho que não temos; método supervisionado. | descartar |

### Abordagem por abordagem (aplicação)

**1. Notícia → série de casos (tentar agora).** É a resposta à pergunta central do protocolo 00, e vem de
um artigo (`ghosh2017`) que não está hoje entre as referências dos braços. O mérito é o desenho —
tendências de tópico temporal de notícia como variáveis externas de uma regressão autoregressiva, com
contagens de caso como verdade — e a evidência de que só-casos-passados nunca vence. Os três artigos
independentes dão o mesmo aviso de defasagem: notícia segue casos com atraso de 2–3 semanas, cobertura é
movida por interesse e decai, e o volume de mídia dirige atenção — não incidência. O custo de testar é
baixo porque as features do braço 03 **já existem**: é rodar o desenho sobre elas.

**2. PT-BR / baixo recurso (tentar agora).** `melo2021` é o único precedente de LDA em notícia PT-BR, e
a lição operacional dele é negativa: teve de traduzir para inglês para o sentimento. Isso defende a
escolha de fonte única PT-BR e a extração nativa. `pruss2019` quantifica o custo de analisar só em
inglês. Moldura, sem compute.

**3. Tópicos + supervisionado / ablação (tentar depois).** O padrão "com vs sem texto" é a
ablação nº1 do protocolo 00, mas já é implementável com os braços existentes — adotar o pipeline
BERTopic+LSTM não é necessário e traz dependências.

**4. Atenção/sentimento (tentar depois).** A fração de cobertura é barata; o sentimento está preso ao
VADER inglês.

**5. STM/DMR com covariáveis (tentar depois).** O mecanismo já está no braço 03; a instância em notícia
é R.

**6. Seleção de k em notícia (tentar depois).** Evidência que sustenta o rank 1 de representação, não uma
ação separada.

**7–8. Descartar.** Texto curto de mídia social (tweet) e dado clínico codificado não são a nossa unidade
nem o nosso domínio, e os ganhos são qualitativos ou negativos.

---

## Cross-cutting — o que é decisão de desenho, não de artigo

1. **Coerência não é qualidade; perplexity não seleciona k.** Aparece em `hoyle2021`, `hoyle2022`,
   `gan2021`, `meaney2023`, `krasnov2019`, `morstatter2016` (grupo `representacao`) e em `weisser2022`,
   `doogan2023` (grupo `aplicacao`). O braço 03 seleciona k por `c_v` — decisão correta segundo as
   fichas, mas insuficiente: os índices discordam entre si e a coerência premia tópicos esotéricos. É
   decisão de desenho reportar mais de um diagnóstico.

2. **Regime de texto curto vs notícia longa.** Boa parte das fichas de representação mira
   tweet/título/snippet (`zuo2015`, `wu2020`, `feng2020`) e de aplicação mira Twitter (`egger2022`,
   `kagashe2017`, `pruss2019`, `mcgough2017`). A nossa unidade é o artigo inteiro (p50 ~438 tokens). Os
   métodos desenhados para esparsidade extrema **não** têm o problema que resolvem no nosso caso —
   decisão: não adotá-los.

3. **Toda a evidência é em inglês ou chinês; PT-BR é a lacuna.** Só `melo2021` (notícia PT-BR) e
   `pruss2019` (tweets ES/PT) tocam o português, e `bianchi2021` testa PT como uma de quatro línguas
   zero-shot. Consequência: qualquer método adotado precisa de um recurso PT-BR que o artigo não fornece
   — embeddings PT (ETM/BERTopic), stopwords PT (NMF), WordNet-PT (JCD), léxico de sentimento PT
   (Krawczyk).

4. **"Nenhuma ficha testa a nossa tarefa" é verdadeiro só do grupo `representacao`.** Nenhuma das 34
   fichas de representação mede previsão de casos; as de `aplicacao` medem (`ghosh2017`,
   `chuluunsaikhan2020`, `chiu2024`, `mcgough2017`, `tizzoni2020`). A frase precisa do qualificador.

5. **O custo é "não reportado" em quase toda a biblioteca.** 47 das 48 fichas não medem runtime em CPU;
   as poucas que medem usam GPU (`dieng2019` <6 h; `bianchi2021` 1,2 s/época; `zhang2022` 101–149 s;
   `chuluunsaikhan2020` RTX 2080) ou R (`rieger2024` 3,4 h por 100 rodadas). Portanto qualquer estimativa
   de custo de uma representação nova é **minha**, não citada — e incerteza não é barato.

6. **Quase toda candidata nova exige dependência fora dos extras pinados.** `umap-learn`/`hdbscan`
   (BERTopic), `sentence-transformers` (ZeroShotTM), `gensim` (NMF/TC-W2V), `scikit-learn` (NMF),
   `pyDNMFk` (SeNMFk), `BigARTM` (Krasnov), R (STM/Meier), MALLET/JVM (Melo/Kagashe), WordNet
   (Morstatter), POT (Montariol). Dado que `pyproject.toml` fixa os extras e o custo de dependência é
   declarado alto, cada uma é uma decisão real.

7. **O braço 03 já cobre várias ideias das fichas.** Covariável de documento como preditor de
   prevalência (`roberts2019` STM, `meier2024` STM) é o que o DMR faz; distribuição de tópicos como
   feature (`rodrigues2017`, `srivastava2017`, `terragni2021`) é o que o braço 03 publica. Não são
   novidade.

8. **Granularidade temporal: as fichas assumem 10–46 timesteps; nós temos 965 semanas.** `dieng2019`
   testa no máximo 46 passos; o braço 03 já resolveu isso usando o nível mensal como covariável do DMR.
   Qualquer modelo temporal novo precisa enfrentar o mesmo descompasso.

9. **Supervisão por documento não existe aqui.** `rodrigues2017` (anotadores), `hughes2020` (desfecho
   clínico), `chiu2024` (readmissão), `kagashe2017` (consumo) exigem rótulo por documento; o nosso alvo
   é agregado por semana×location. É a razão de descartar toda a família supervisionada.

10. **Nenhuma ficha trata o corpus misto de línguas.** O braço 03 gasta um tópico inteiro nos 180
    artigos em inglês (4,1%) que passam pelo `lang_guess`. É item aberto do protocolo 00, não resolvido
    por nenhuma referência desta família.

---

## First move

Rodar o desenho do `ghosh2017` — tendências de tópico do braço 03 como regressor exógeno de casos, 1
passo à frente, com o **controle negativo de texto embaralhado** do protocolo 00 — sobre as features que
**já existem** (zero dependência nova, zero re-encode), porque é a ablação nº1 do protocolo e decide se
qualquer upgrade de representação vale a pena antes de gastarmos uma dependência nova.

---

## O que ficou de fora e por quê

- **Modelos de tópico supervisionados e multi-anotador** (`rodrigues2017`, `hughes2020`): exigem rótulo
  por documento/anotador que o corpus não tem; o alvo é agregado.
- **Texto curto e mídia social** (`zuo2015`, `wu2020`, `feng2020`, `egger2022`, `kagashe2017`): o regime
  que o método ataca (esparsidade de tweet) não é o nosso (notícia longa), e a evidência é qualitativa ou
  negativa.
- **Mudança semântica lexical** (`montariol2021`): outra tarefa; perde para um baseline simples.
- **STM em R** (`roberts2019`, `meier2024`): o repositório rejeitou carregar R, e o DMR já é o
  substituto Python-nativo do mecanismo de covariável.
- **OCTIS e surveys** (`terragni2021`, `zhao2021`): harness e mapas, não representações; a lição (BO para
  k, taxonomia de falhas, TSD) foi absorvida nos ranks 1 e 2.
- **Sinais externos** (Google Trends/Twitter/HealthMap/Wikipedia em `mcgough2017` e `tizzoni2020`): não
  temos esses fluxos; só o **desenho** de regressão transfere, e está no rank 1 de aplicação.

---

## Perguntas abertas

- O ganho de notícia→série do `ghosh2017` (8 de 10) sobrevive no nível UF, dado o descompasso espacial
  (notícia nacional vs alvo UF) que o protocolo 00 já aponta?
- Qual recurso PT-BR preenche a lacuna (embeddings, stopwords, WordNet, léxico de sentimento)? Nenhuma
  referência da família fornece.
- A receita de estabilidade (medoide do Rieger, ≥50 replicações) cabe no orçamento de CPU-minutos sobre
  4.369 artigos × grade de k? O artigo não mede o nosso tamanho.
- O `c_v` sobre notícia PT-BR acompanha o julgamento humano, dado o aviso de Hoyle (métrica frágil para
  modelos neurais) e de Meaney (índices discordam)?
- A cobertura de notícia é endógena (segue casos), o que torna o Granger do protocolo 00 ordenação
  preditiva e nunca mecanismo — como isso afeta o controle negativo?
