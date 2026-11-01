# Ranking das abordagens — features de texto (dicionario, regras e contagens)

Artefato do workflow de extracao de features de texto. Ranqueia **abordagens**, nao artigos, e
separa os dois grupos que as fichas marcam: `representacao` (como transformar texto em numero) e
`aplicacao` (onde usar isso no nosso dominio). Os dois grupos nao competem entre si — por isso ha
dois `rank 1`.

Contexto que define "usavel": corpus de 4.369 artigos da Agencia Brasil (dengue, PT-BR, 965 semanas,
28 locations = BR + 27 UFs); CPU only, sem GPU; extras fixados em `pyproject.toml`
(`embeddings` = torch+transformers ~800 MB, `topics` = tomotopy); bracos 01 (lexico), 02 (6 configs
de embedding) e 03 (DMR/tomotopy) ja construidos; custo de dependencia nova e alto, e o transform
precisa rodar em CPU em minutos, nao horas.

Fontes de custo: `src/pipeline/news/README.md`, `notes/00-protocolo-comparacao.md`,
`pyproject.toml`.

---

## Representacao — como transformar texto em numero

| # | Abordagem | Fichas | Merit (o que entrega, contra que baseline) | Adoption cost (aqui) | Veredito |
|---|---|---|---|---|---|
| 1 | Features superficiais de contagem (caracteres, palavras, silabas, TTR, razoes) | `lee2021text`, `crossley2011readability` | Lee 2021: o ramo de contagem e deterministico e barato, mas o artigo nao o isola contra baseline (o ganho vem do hibrido com transformer). Crossley 2011: comprimento de palavra/frase (a base das formulas) acerta 44-49% contra chance de 33%. Nenhuma das duas mede dengue — o alvo e nivel de leitura. | ~zero: Python puro, sem dependencia nova, sem GPU, segundos sobre 4.369 artigos. `char_count` ja existe no corpus. Nao precisa de rotulo. | **tentar agora** |
| 2 | Formulas de legibilidade (Flesch-Kincaid, Flesch Reading Ease) recalibradas para PT-BR | `crossley2011readability` | Crossley 2011: Flesch-Kincaid 49,3%, Flesch Reading Ease 44,3% contra chance 33,3%. Baseline = a outra formula; ganho modesto. Calibradas em ingles, nada medido em portugues. | Contar silabas em PT-BR e regra simples (barato), mas recalibrar exige rotulos de dificuldade que nao temos. Sem GPU. | tentar depois |
| 3 | Indice de coesao/lexical tipo Coh-Metrix L2 (frequencia lexical + similaridade sintatica + sobreposicao de palavras) | `crossley2011readability` | Crossley 2011: 60,0% de acuracia vs 49,3% da melhor formula tradicional (Kappa 0,400), mas erro grande na classe intermediaria (39%) e ground truth e nivel de leitura, nao doenca. | Precisa de base de frequencia (CELEX e ingles) + parser sintatico (dependencia nova). A sobreposicao de palavras e barata e portavel; a similaridade sintatica nao. | tentar depois |
| 4 | Pipeline hibrido completo do LingFeat (255 features handcrafted + soft labels de transformer) | `lee2021text` | Lee 2021: ganho grande so em dataset pequeno (OneStopEnglish 0,965 -> 0,990); no maior (WeeBit) o ganho e 0,889 -> 0,905 (+0,016, dentro do ruido). Sem avaliacao cross-domain (os autores admitem). | Alto: LingFeat + spaCy + SuPar + Gensim + bases lexicais inglesas (SubtlexUS, Kuperman AoA); treino de transformer em GPU V100 (1.202-3.617 s/fold). | descartar |
| 5 | Resolucao de correferencia por ILP (Klenner & Ailloud) | `chae2009fluency` | F 61,83 -> 64,27 (all mentions) e 71,47 -> 78,90 (true mentions); a tese de que otimizacao e dispensavel e so empirica (-0,086% de F). Alemao, TuBa-D/Z. | Precisa de anotacao gold de correferencia e de parsing sintatico (POS, fronteiras de NP) que nao temos em PT-BR; sem GPU. | descartar |

### Abordagem por abordagem (representacao)

**1. Features superficiais de contagem** — o ramo count-based do LingFeat (Lee 2021) e os insumos das
formulas de Flesch (Crossley 2011). Comprimento de texto, contagem de tokens, silabas, razao
type-token, densidade. E exatamente a familia que o pedido nomeia ("contagem de caracteres, coisas
do texto"). O merito e honesto e modesto: nao ha nenhuma medicao de que isso prevea doenca — o que
existe e que um punhado de contagens descreve dificuldade de leitura melhor que o acaso. O custo e
praticamente nulo e o `char_count` ja esta no corpus, entao tentar e racional mesmo com expectativa
baixa.

**2. Formulas de legibilidade** — Flesch-Kincaid e Flesch Reading Ease. Duas estatisticas de
superficie (palavras/frase e silabas/palavra) combinadas linearmente. Baseline e a outra formula, e
o ganho e de poucos pontos sobre o acaso. Os coeficientes sao de ingles; sem rotulos PT-BR o numero
nao significa nada. Estimativa de custo e minha, nao da ficha (o artigo nao reporta runtime).

**3. Indice de coesao tipo Coh-Metrix** — tres features (frequencia lexical, similaridade sintatica,
sobreposicao de palavras entre frases adjacentes) com pesos fixos. Bate a formula tradicional por
~11 pontos de acuracia, mas depende de recursos so-ingles (CELEX, parser) e o alvo e outro. A ideia
de "medir repeticao/coesao com poucas features" transfere; o artefato nao.

**4. Hibrido LingFeat** — features + transformer. So ingles, dependencias pesadas, treino em GPU, e
a tarefa (legibilidade de texto didatico) e distante de vigilancia. Nada no artigo justifica trazer
para ca.

**5. Correferencia por ILP** — ficha com arquivo trocado: o PDF e Klenner & Ailloud (EACL 2009),
correferencia, nao o Chae & Nenkova de fluencia que o nome promete. Topico fora do escopo de
features de texto e avaliado so em alemao. Nada a aproveitar.

---

## Aplicacao — onde usar, no nosso dominio

| # | Abordagem | Fichas | Merit (o que entrega, contra que baseline) | Adoption cost (aqui) | Veredito |
|---|---|---|---|---|---|
| 1 | Extracao lexico/gazetteer de doenca+local com cascata (manchete->corpo) e container relationships | `freifeld2007healthmap`, `brownstein2008surveillance`, `collier2008biocaster`, `keller2009unstructured`, `arsevska2018web`, `valentin2020padi`, `conway2010disease`, `chanlekha2010spatial`, `carlson2023who`, `ng2020nlp` | freifeld2007: 84% de acuracia (655/778), sem baseline; collier2008: 94,8% na classificacao de topico (baseline SVM 92,1%); arsevska2018: F 0,95 doenca/hospedeiro mas sobre 352 noticias anotadas e com 32-68% de sinais irrelevantes; valentin2020: 97,2% CV / 92% externo (sem baseline, treino desbalanceado). O ganho real e o desenho (cascata + eliminar o local/doenca generico quando ha especifico), nao um numero. | E o que o braco 01 ja e. A cascata e o container relationship mapeiam direto no nosso problema BR+UF (artigo cita pais e UF). Sem dependencia nova; o custo e curadoria do lexico PT-BR, que ja existe em parte. | **tentar agora** |
| 2 | Deteccao de aberracao temporal sobre contagens semanais (EARS C2/C3/W2/F-stat/EWMA; Bayesian change point) | `collier2010unusual`, `collier2011cross`, `ganser2022global` | collier2010: melhor F1 0,63 (W2), PPV 0,56; collier2011: F1 0,53-0,60, sensibilidade ate 0,87, 2-8 dias antes do ProMED; ganser2022 (cautela): so 9,2% de sensibilidade oportuna contra o FluNet. Baseline = ProMED/serie oficial (padrao-prata). | ~zero: estatistica pura sobre a serie semanal de contagens; o braco 01 ja produz `news_volume`. Sem dependencia nova (numpy/scipy), sem GPU, segundos em CPU. | **tentar agora** |
| 3 | Heuristicas de qualidade de extracao de texto de noticia + corpus geolocalizado com SBERT | `kriesch2025geolocated` | kriesch2025: NER F1 93,87%; 7 heuristicas de qualidade removem conteudo ruim (minimo de frases, fracao nao-alfabetica, palavras/linha, tamanho, duplicatas); busca semantica correlaciona r=0,84 com Google Trends. Sem baseline para o embedding (so a propria quantizacao Float32). | As 7 heuristicas sao agnosticas de dominio e de graca (Python). O modelo SBERT do artigo e alemao — trocar por BERTimbau cai no extra `embeddings` ja instalado. Sem GPU. | **tentar agora** |
| 4 | Geoparsing: reconhecimento de toponimo + resolucao para unidade administrativa (UF) | `hu2023location`, `gritta2020pragmatic`, `syed2023geospatre`, `keller2009vocabulary` | hu2023: unidades administrativas (exatamente BR+27 UFs) sao a categoria mais facil — 13/27 metodos >60% de recall, e noticia e mais facil que tweet. gritta2020: F 88,6 de geotagging mas so ingles, e a heuristica de populacao empata com o resolver. syed2023: P/R/F 0,90/0,88/0,88 mas regras em ingles. Nenhum baseline em PT-BR em nenhuma. | Dependencias novas (spaCy PT, geopandas/shapely); todos os recursos e modelos avaliados sao ingles. Rebuild completo para PT-BR; o gazetteer de UFs e barato. | tentar depois |
| 5 | Classificacao supervisionada de relevancia de noticia (TF-IDF/BoW + ML classico; BERT) | `mutuvi2020multilingual`, `valentin2021padi`, `valentin2020padi` | mutuvi2020: TF-IDF+LR/SVM ~80 F1, BERT fine-tunado 86,25 (ganho real ~6 pts, nao os ">50%" contra o baseline fraco DANIEL); achado forte: titulo+lead carrega o sinal (inicio+fim 87,82 vs corpo 77,94). valentin2021: F 0,66 (evento) / 0,49 (tipo de informacao) — evidencia fraca, sem baseline, precisa rotulo. | Precisa de corpus rotulado que nao temos (mutuvi: 7.574 artigos; arsevska: 352). TF-IDF+LR e leve (sklearn nao esta nos extras); BERT fine-tuning pede GPU. | tentar depois |
| 6 | Framework de avaliacao de EBS contra notificacao oficial (sensibilidade oportuna, timeliness, DR/EPPV/F1) | `barboza2013evaluation`, `barboza2014performance`, `bahk2015timeliness` | barboza2013: pool de sistemas detecta 93% de sensibilidade e 10,2 dias antes; barboza2014: moderacao humana +53% de sensibilidade intrinseca (RR 1,53; IC 1,34-1,75), mas gold-standard frances pequeno (86 eventos); bahk2015: fonte informal precede a formal em 1,26 dia (p=0,002). Baseline = notificacao oficial. | O desenho transfere; precisariamos de um padrao-ouro (SINAN `cases.py` e candidato) e os sistemas avaliados sao proprietarios (nao temos acesso). Sem dependencia nova para rodar o desenho. | tentar depois |
| 7 | Pipeline PT-BR de noticia: LDA de topicos + sentimento + NER (spaCy PT) | `melo2021news` | melo2021: coerencia LDA 0,511 (noticia) / 0,446 (tweet); NER ~85% medido so nos 20 termos mais frequentes de cada classe; zero baseline, estudo descritivo. Dominio = noticia PT-BR de doenca (UOL). | LDA ja temos (braco 03/tomotopy). O sentimento exige traduzir PT->EN (googletrans, dependencia fragil presa a rede) + VADER; NER exige spaCy PT + sementes + treino. Custo alto para payoff fraco. | tentar depois |
| 8 | Rotulos baratos por crowdsourcing com correcao de vies | `pitler2008revisiting` | Snow 2008 (arquivo com nome "pitler"): 10 nao-especialistas empatam 1 expert em afeto/similaridade (RTE 89,7% vs 91-96% de expert); correcao de vies +4% (RTE). So ingles, tarefas nao-doenca. | Exige plataforma paga + gold em PT-BR (nao reportado para portugues; o estudo gastou ~US$26 por 21,7 mil rotulos curtos em ingles). Sem GPU. | tentar depois |
| 9 | Vigilancia por volume de busca (Google Flu/Dengue Trends) | `milinovich2013internet`, `madoff2011monitoring` | milinovich2013: r 0,83-0,99 em estudos citados, mas o GFT original caiu para r=0,29 na H1N1; o confundidor central e que o volume segue interesse midiatico, nao incidencia. madoff2011: comentario, sem numeros proprios. | Nao aplicavel: o sinal e volume de consulta, nao texto de noticia. Nao temos (nem teremos) logs de busca; o Google Dengue Trends foi descontinuado. | descartar |
| 10 | Extracao neural de campos (BERT/LLM) — BioCaster 2021 e Consoli 2025 | `meng2022biocaster`, `consoli2025knowledge` | consoli2025: F1 doenca 0,851, pais 0,962, casos 0,658; o ensemble supera o melhor modelo unico por margem pequena (dentro do ruido para 171 amostras); mortes nem avaliado. meng2022: zero avaliacao quantitativa, ganho so qualitativo. | Inviavel aqui: 3 LLMs (um de 70B) ou PubMedBERT+SapBERT + traducao comercial + UMLS; GPU/HPC, dezenas de GB. Inferencia sobre 4.369 artigos em CPU seria horas-dias, nao minutos. | descartar |
| 11 | Extracao de palavras-chave por TextRank + rede de co-ocorrencia (nao supervisionado) | `you2021text` | you2021: sem baseline nem metrica; "validacao" e alinhamento qualitativo com fases da OMS (circular). Erros reconhecidos (nao extrai "Ogun state", nao resolve sinonimos). Corpus e ProMED (e-mail curado), nao noticia. | Barato em CPU (NLTK + Gephi), nao supervisionado; mas o pre-processamento e ingles e os autores descartaram explicitamente os relatorios em portugues. | descartar |
| 12 | Vigilancia por leitura humana de midia impressa local | `schwind2014local` | schwind2014: 82% dos eventos locais nao apareciam no HealthMap — achado de dominio (noticia local carrega sinal que agregador global perde). Sem teste estatistico, n=87. | Nao e transform: exige leitores humanos de impresso em dialetos locais; nada roda sobre os 4.369 artigos digitais. Custo nao reportado (e humano). | descartar |
| 13 | Overview de plataformas de vigilancia digital no Brasil | `neto2016digital` | neto2016: sem metrica, sem baseline; tabela qualitativa de 11 sistemas. Nenhum sistema foi rodado. | Nao ha artefato computacional para rodar. | descartar |

### Abordagem por abordagem (aplicacao)

**1. Extracao lexico/gazetteer com cascata e container relationships** — a familia dominante (10
fichas). O que ela ensina de concreto para nos: (a) extrair em cascata manchete -> descricao -> corpo,
parando quando acha local+doenca (freifeld2007); (b) o "container relationship" que elimina o local
generico quando ha um especifico — exatamente o caso de um artigo que cita Brasil e uma UF
(freifeld2007); (c) o alerta de que nomes de doenca tem variantes e a geografia e grafada de formas
inconsistentes num corpus de prosa (carlson2023); (d) o mapa de tarefas de extracao de Ng et al.
(classificacao por tipo de ameaca, local, tempo, contagem de casos, sumarizacao) como checklist
(ng2020nlp). O custo e o lexico PT-BR, que o braco 01 ja construiu em parte. E o unico braco que hoje
empata ou ganha dos embeddings (0,297 vs 0,291).

**2. Deteccao de aberracao sobre contagens semanais** — tres fichas, uma linha so. collier2010/2011
rodam EARS C2/C3/W2/F-statistic/EWMA (linha de base de 7 dias, sem treino) sobre a contagem diaria de
eventos doenca-pais; ganser2022 roda Bayesian change point sobre a contagem semanal de reportagens.
Merito: e o teste mais barato de "a noticia tem valor de vigilancia?" — alimenta-se do `news_volume`
do braco 01 e mede antecipacao contra SINAN sem treinar nada. Custo ~zero. A ressalva de ganser2022
(9,2% de sensibilidade oportuna) e o motivo de nao prometer demais.

**3. Heuristicas de qualidade de extracao** — kriesch2025. Sete filtros de qualidade de texto
(comprimento, fracao nao-alfabetica, palavras por linha, duplicatas etc.) que sao agnosticos de
dominio e de lingua. Aplicam-se direto ao nosso corpus, que tem digests de 8.000+ caracteres e
paginas sem corpo. Custo zero. A parte de busca semantica SBERT depende de trocar o modelo alemao
por BERTimbau (ja disponivel no extra `embeddings`).

**4. Geoparsing para unidade administrativa** — hu2023 (survey), gritta2020 (avaliacao), syed2023
(relacoes espaciais), keller2009vocabulary (geo-parser neural treinado de gazetteer). Relevante
porque as nossas 28 locations sao exatamente unidades administrativas, a categoria mais facil do
survey. Mas todos os recursos e modelos avaliados sao ingleses e nenhum baseline PT-BR existe; a
versao gazetteer simples o braco 01 ja faz via `UfMatcher`.

**5. Classificacao supervisionada de relevancia** — mutuvi2020, valentin2020/2021. Trava na falta de
rotulo. O achado aproveitavel ja: titulo+lead carrega o sinal, o que reforca o que o braco 02 viu
(`title-only` 0,156 > full-text 0,105). O ganho do BERT sobre TF-IDF e ~6 pontos, nao os ">50%" do
abstract (que e contra um baseline nao supervisionado fraco).

**6. Framework de avaliacao de EBS** — barboza2013/2014, bahk2015. Da o vocabulario para medir o que
queremos: sensibilidade oportuna (dentro de +/-2 semanas do inicio oficial), timeliness em dias de
antecedencia, deteccao bruta vs precoce vs intrinseca. Depende de fixar um padrao-ouro antes; SINAN
`cases.py` e o candidato.

**7. Pipeline PT-BR de noticia** — melo2021. O mais proximo do nosso dominio em lingua e fonte
(noticia PT-BR de doenca). O LDA ja esta coberto pelo braco 03; o eixo novo (sentimento ao longo do
tempo) exige traduzir PT->EN e um NER spaCy PT, ambos caros e nao reportados.

**8. Rotulos baratos por crowdsourcing** — Snow 2008 (arquivo com nome "pitler"). So interessa se
decidirmos treinar um classificador de relevancia (linha 5) e precisarmos de rotulos; ai mostra que
rotulo barato agregado pode bastar. Sem essa decisao, nao e acao.

**9-13. Descartadas.** Vigilancia por volume de busca (modalidade errada: temos noticia, nao query);
extracao neural BERT/LLM (GPU/inviavel em CPU-minutos, ganho marginal); TextRank (evidencia nula,
lingua errada, braco 03 ja cobre); leitura humana de impresso (nao ha pipeline); overview Brasil (sem
tecnica).

---

## Cross-cutting

Decisoes de desenho que aparecem em varias fichas, nao de um artigo so. Onde a afirmacao so vale
dentro de um grupo, o grupo esta dito.

- **Aplicacao:** praticamente todo o corpus de vigilancia assume um gazetteer de doencas+lugares
  curado a mao, e nenhum e PT-BR — o portugues estava "em desenvolvimento" no HealthMap
  (brownstein2008) e o BioCaster nao detectou dengue no Ceara por falta dele (collier2010). Confirma
  que o custo do braco 01 e lexico, nao compute.
- **Aplicacao:** o volume de noticia segue atencao/disrupcao percebida, nao incidencia
  (brownstein2008, collier2010, milinovich2013, madoff2011, ganser2022). Como o nosso corpus E midia,
  isso e restricao de desenho para os tres bracos, nao um achado lateral.
- **Aplicacao:** agregar por pais esconde diversidade regional — ganser2022 cita Brasil e China
  nominalmente e collier2010 quer descer para provincia. Nosso grao e UF (melhor que pais), mas o
  aviso vale para as 27 UFs, e o braco 01 ja mede que a mencao por UF nao e estavel no tempo.
- **Ambos os grupos:** o sinal informativo esta no titulo/lead, nao no corpo — mutuvi2020 (inicio+fim
  87,82 vs corpo 77,94) e o proprio braco 02 (title-only 0,156 vs full-text 0,105). E decisao de
  desenho da representacao, nao um numero de um artigo.
- **Aplicacao:** baseline fraco ou ausente e a regra — freifeld2007, brownstein2008, valentin2020,
  ganser2022, you2021 e melo2021 nao comparam com metodo alternativo. "Funciona" nessas fichas nao e
  comparativo.
- **Ambos os grupos:** custo computacional "nao reportado" e quase universal. Toda estimativa de
  custo de adocao aqui e minha, nao das fichas — incerteza nao e barato.
- **Aplicacao:** a literatura de extracao/avaliacao e anglocentrica; so melo2021 (noticia PT-BR) e
  neto2016 (overview Brasil) tocam o portugues. PT-BR e sub-atendido, e e onde estamos.
- **Grupo representacao:** nenhuma das 3 fichas mede a nossa tarefa — o alvo delas e nivel de
  leitura/fluencia, nao dengue. So o grupo aplicacao tem fichas que testam noticia-de-doenca
  (melo2021; barboza2014 inclui dengue; ganser2022).
- **Qualidade das fichas:** duas estao com arquivo trocado — `chae2009fluency` contem Klenner &
  Ailloud (correferencia) e `pitler2008revisiting` contem Snow et al. (crowdsourcing). Foram
  ranqueadas pelo conteudo real do PDF, nao pelo nome.

---

## First move

Adicionar o bloco de features superficiais de contagem (caracteres, palavras, silabas, TTR, razoes)
como um setimo braco do bracket, porque e a representacao que o pedido nomeia, custa segundos em CPU,
nao exige dependencia nova, e independente de idioma — e e a unica familia do pedido que o repo ainda
nao tem para comparar com o lexico (01) e os embeddings (02).

---

## O que ficou de fora e por que

- **5 abordagens marcadas `descartar`** (9-13 em aplicacao, 4-5 em representacao): modalidade errada
  (volume de busca), inviavel em CPU-minutos (BERT/LLM generativo), evidencia nula (TextRank),
  sem pipeline executavel (leitura humana, overview Brasil), dependencias so-ingles pesadas (hibrido
  LingFeat), topico fora de escopo com arquivo trocado (correferencia).
- **Nao incluido como linha propria:** `meng2022biocaster` foi fundido com `consoli2025knowledge`
  (extracao neural, sem avaliacao util); `ng2020nlp` e `keller2009unstructured` foram fundidos com a
  linha 1 (mapa de tarefas e overview de EBS, sem tecnica propria); `carlson2023who`, `conway2010disease`
  e `chanlekha2010spatial` foram fundidos com a linha 1 (esquemas de anotacao / achado de variantes de
  nome de doenca).
- **Fichas nao usadas como evidencia de representacao:** as de aplicacao nao competem com as de
  representacao e foram mantidas no grupo delas, conforme a marcacao.
