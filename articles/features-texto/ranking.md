# Ranking das abordagens — features de texto

Artefato do workflow de extração de features de texto. Ranqueia **abordagens**, não artigos, e
separa os dois grupos que as fichas marcam: `representacao` (como transformar texto em número) e
`aplicacao` (onde usar isso no nosso domínio). Os dois grupos **não competem entre si** — por isso há
dois `rank 1`, um em cada tabela, e a numeração reinicia.

Contexto que define "usável": corpus de 4.369 artigos da Agência Brasil (dengue, PT-BR, 965 semanas,
28 locations = BR + 27 UFs); CPU only, sem GPU; extras fixados em `pyproject.toml`
(`embeddings` = torch+transformers ~800 MB, `topics` = tomotopy); braços 01 (léxico), 02 (bracket de 6
configs de embedding) e 03 (DMR/tomotopy) já construídos e medidos; custo de dependência nova é alto, e
o transform precisa rodar em CPU em minutos, não horas.

Fontes de custo: `src/pipeline/news/README.md`, `notes/00-protocolo-comparacao.md`, `pyproject.toml`.

**Nota de composição.** As 35 fichas marcam **três** como `representacao` (`lee2021text`,
`crossley2011readability`, `chae2009fluency`) e 32 como `aplicacao`. Duas das três de representação são
de **legibilidade** e a terceira é **correferência** — nenhuma mede a nossa tarefa. Isso não é defeito
da marcação: esta família, na prática, é uma família de aplicação, e o grupo `representacao` existe
para dizer que a única coisa rotulada "como representar" aqui não serve. Onde eu discordo da marcação,
digo na própria linha.

---

## Representação — como transformar texto em número

Alternativas entre si. Um "tentar depois", dois "descartar".

| # | Abordagem | Fichas | Merit (o que entrega, contra que baseline) | Adoption cost (aqui) | Veredito |
|---|---|---|---|---|---|
| 1 | Híbrido: features linguísticas artesanais ⊕ soft labels de transformer | `lee2021text` | Único desenho da família que mede representação *como representação*: concatena as probabilidades por classe de um transformer fine-tuned a um vetor de features artesanais e treina um classificador leve por cima. Ganho maior sob rótulo escasso (BERT-GB iguala o SOTA anterior no WeeBit com 30% do treino) e as features de "semântica avançada" — riqueza/clareza/ruído sobre a distribuição de um LDA — são declaradas ortogonais ao encoder. Baseline explícito: o SOTA anterior e cada modelo isolado. Os 99% no OneStopEnglish são artefato de corpus paralelo e não contam como mérito. | Nenhuma das 255 features tem equivalente PT-BR pronto (SubtlexUS, AoA de Kuperman, spaCy EN). A parte barata — usar a distribuição de tópicos como feature — o **braço 03 já faz** via tomotopy. O concat com soft labels exige um transformer fine-tuned (o braço 02 declarou fine-tuning fora de escopo: "muda a natureza do braço") e rótulos de relevância que não temos. Sem GPU; CPU viável. | tentar depois |
| 2 | Features artesanais puras / fórmulas de legibilidade (superfície, coesão, parsing) | `crossley2011readability`, `lee2021text` (ramo não-híbrido) | Crossley 2011: índice Coh-Metrix L2 acerta 60,0% contra 49,3% (Flesch-Kincaid) e 44,3% (Flesch Reading Ease), com acaso em 33,3% e Kappa 0,400 vs 0,240/0,165. A lição de desenho que sobrevive — features de superfície (comprimento de palavra/frase) são fracas, coesão/parsing carregam mais sinal — é boa. Baseline = as fórmulas tradicionais entre si. | Coh-Metrix é ferramenta externa, inglês-only (normas CELEX), sem equivalente PT-BR; a tarefa é nível de leitura de texto didático, não sinal epidemiológico; exige rótulos de simplificação que o corpus não tem. Sem GPU. Dependência nova alta. | descartar |
| 3 | Correferência como ILP 0-1 sobre classificador de pares (Klenner & Ailloud) | `chae2009fluency` | Ficha marcada `representacao`, mas o PDF é Klenner & Ailloud (EACL 2009), **não** o Chae & Nenkova de fluência. O que entrega: formular correferência como ILP com restrições intencionais; Balas-First iguala a solução ótima em >90% dos casos e sobe a F de 61,83→64,27 (todas as menções) e 71,47→78,90 (só menções verdadeiras) sobre o classificador de pares. Baseline = a saída crua do TiMBL. | Não é "como transformar texto em número" e não é a nossa tarefa (correferência, não sinal de dengue); exigiria corpus-ouro PT-BR de correferência e um classificador de pares que não temos. Nada aqui toca encoder/pooling/dimensionalidade. | descartar |

### Abordagem por abordagem (representação)

**1. Híbrido features + soft labels.** É o único desenho da família que mede representação *como
representação*, e a ideia central — features artesanais ajudam quando o dado rotulado é escasso — é
boa. Mas a instanciação é inglês-only, a parte barata (features de distribuição de tópicos) já está no
braço 03, e a parte nova (fine-tuning + concat) depende de rótulos que o repo ainda não tem. Por isso
`tentar depois`, não `tentar agora`.

**2. Features puras / legibilidade.** As fórmulas e os índices são de inglês, o alvo é legibilidade de
texto didático, e o próprio artigo admite erro grande na classe intermediária. Nada disso toca dengue.
`descartar` — fica só a lição de desenho.

**3. Correferência por ILP.** Ficha com arquivo trocado (é Klenner & Ailloud, não Chae). Ranqueei pelo
conteúdo real do PDF, que é correferência — fora da nossa tarefa e exigindo um corpus-ouro PT-BR que
não temos. `descartar`.

> As **três** fichas de representação são de legibilidade (2) e correferência (1). **Nenhuma** mede a
> nossa tarefa — isso é verdade do grupo `representacao`, e **não** da biblioteca inteira: as fichas de
> aplicação testam notícia de doença (`melo2021` é notícia PT-BR; `barboza2014` e `ganser2022` incluem
> arbovírus/influenza com padrão-ouro). A frase "nenhuma ficha testa a nossa tarefa" seria falsa sobre
> a biblioteca, só verdadeira sobre `representacao`.

---

## Aplicação — onde usar, no nosso domínio

**Não** competem com as de representação. A pergunta é o que já foi feito em notícia como fonte de
sinal, o que aquilo mediu, e o que muda para nós.

| # | Abordagem | Fichas | Merit (o que entrega, contra que baseline) | Adoption cost (aqui) | Veredito |
|---|---|---|---|---|---|
| 1 | Protocolo de avaliação contra padrão-ouro (DR + sensibilidade oportuna + timeliness) | `barboza2013evaluation`, `barboza2014performance`, `bahk2015timeliness`, `ganser2022global`, `schwind2014local` | É a resposta direta à pergunta do protocolo 00: como medir o sinal de notícia. Define detecção bruta/precoce/intrínseca, EPPV/F1 e timeliness contra um padrão-ouro curado, e calibra a expectativa — frequência de reports sozinha dá só **9,2%** de sensibilidade oportuna (`ganser2022`); notícia informal antecede a formal em ~1,26 dia (`bahk2015`); agrupar sistemas complementares sobe a sensibilidade a 93% e antecipa 10,2 dias (`barboza2013`). Baseline = o próprio padrão-ouro (ProMED/FluNet/BHI/OMS). | Ler não custa nada; replicar exige um padrão-ouro (temos SINAN `cases.py`) e adjudicação manual. Os números **não transferem** (H5N1, influenza, 1 mês). `ganser2022` usa R/bcp — fora do stack Python. | **tentar agora** |
| 2 | Extração por dicionário + regra (cascata manchete→corpo, container relationships) | `freifeld2007healthmap`, `brownstein2008surveillance`, `collier2008biocaster`, `valentin2020padi`, `valentin2021padi`, `arsevska2018web`, `keller2009unstructured`, `ng2020nlp` | É literalmente o braço 01. A linhagem canônica fixa as expectativas: PADI-web detectou surtos até 8 dias antes da OIE; o container relationship (descarta o local genérico quando há específico) mapeia direto em BR+UF; o slot de contagem é o mais fraco em **todo** sistema (F1 0,658 vs 0,851 doença / 0,962 país em `consoli2025`; F 85% vs 95% em `arsevska2018`; ausente em produção em `ng2020nlp`). PT-BR é a lacuna que o braço trabalha (`brownstein2008`: "under development"; `collier2010` perdeu o surto do Ceará por falta de PT). Baseline interno: cascata vs sem cascata. | Sem modelo, sem GPU, CPU em segundos. O custo é o léxico PT-BR (feito) e a amostra anotada (não feita) — o item aberto nº1 do braço 01. | **tentar agora** |
| 3 | Anotação não-experta com correção de viés | `pitler2008revisiting` (PDF = Snow 2008) | Desbloqueia a amostra anotada do braço 01: em média **4 anotações não-expertas por item igualam a concordância inter-anotador de um especialista**, e um modelo de calibração por anotador (peso por log-likelihood ratio contra um pequeno gabarito) supera votação majoritária (+3,4% em eventos, +4,0% em RTE). Independente de língua e domínio. Baseline = votação majoritária e anotador especialista. | Exige anotadores pagos e um pequeno gabarito; nenhum modelo/GPU. Não há infra de crowd no repo. Custo em dinheiro: US$25,82 por 21.690 rótulos (tarefa de afeto) — escala não reportada para o nosso tamanho. | **tentar agora** |
| 4 | Enquadramento de fonte única / mídia local | `schwind2014local`, `neto2016digital` | Precedente direto para defender uma fonte PT-BR única: o LMS capturou **71 de 87** eventos que o agregador global (HealthMap) não pegou, porque não estavam disponíveis digitalmente; e o Brasil já tem plataformas de detecção digital nos CIEVS. Não é técnica — é o argumento **medido** de que uma fonte local carrega sinal que o agregador perde. Baseline = o próprio HealthMap. | Nada a rodar; é moldura. Custo do artigo é citar sem superdimensionar (corpora minúsculos, método manual, latência ~7 dias). | **tentar agora** |
| 5 | Detecção de aberração temporal sobre contagens de notícia | `collier2010unusual`, `collier2011cross`, `ganser2022global` | O passo "contagens → alarme": EARS C2/C3/W2/EWMA/F-stat sobre baseline deslizante de 7 dias, medidos contra ProMED (W2 F1 0,63). Achados: viés de dia da semana (1,37 úteis vs 0,49 fim de semana); purgar contagens de 1–2 documentos sobe o F1; agregação por país esconde sinal sub-nacional; acrescentar línguas além do inglês melhora F1 e sensibilidade. Baseline = ProMED (padrão-prata). | Roda em CPU sem dependência nova em princípio, mas o extrator do artigo é SRL/EN e `ganser2022` usa R/bcp. Fica a jusante de uma série validada — só faz sentido depois do rank 1. | tentar depois |
| 6 | Classificação supervisionada de relevância, TF-IDF → BERT | `valentin2020padi`, `valentin2021padi`, `arsevska2018web`, `mutuvi2020multilingual`, `meng2022biocaster` | Random Forest sobre TF-IDF chega a 97,2% (5-fold) / 92% (validação externa) com 600 rótulos; BERT fine-tuned bate TF-IDF e FastText no mesmo problema (`mutuvi2020`: F1 86,25 vs ~80 do ML clássico). Achado de pooling reaproveitável: **início+fim do documento é a porção mais informativa** (`mutuvi2020`, 87,82 vs corpo 77,94) — decisão de truncamento para o braço 02. Baseline = o sistema especializado DANIEL e cada modelo isolado. `meng2022` é nota de sistema sem nenhum número. | CPU, sem GPU; precisa de conjunto rotulado PT-BR (o corpus já é pré-filtrado por termo de doença, então a relevância é parcialmente moot). scikit-learn não está nos extras. `mutuvi2020` exige rótulos; `meng2022` exige UMLS + motor de tradução comercial. | tentar depois |
| 7 | Modelagem de tópicos / grafo de palavras-chave em notícia | `you2021text`, `melo2021news` | Braço 03 já cobre tópicos. `melo2021` é a **única** referência de notícia PT-BR com LDA+MALLET+sentimento+NER (18.413 artigos UOL); `you2021` mostra TextRank (grafo de coocorrência) como alternativa não-supervisionada e barata para acompanhar o estágio do surto. Baseline: **nenhum** — ambos descritivos, sem métrica contra nada. | `you2021` exige NLTK + stopwords/stemmer PT (não instalados); `melo2021` exige googletrans (traduz tudo para inglês), VADER, spaCy PT e MALLET/JVM — dependências novas e serviço externo. | tentar depois |
| 8 | Esquema de anotação / corpus padrão-ouro | `conway2010disease`, `chanlekha2010spatial`, `carlson2023who`, `gritta2020pragmatic` | Moldes de anotação reaproveitáveis: event frame com slots de entidade + slots booleanos ancorados no Anexo 2 do RSI/OMS (`conway2010`); zonas espaço-temporais (`chanlekha2010`); metadados de surto do DON (`carlson2023`); taxonomia literal vs associativo de topônimo (`gritta2020`, 53%/47% num corpus de 200 notícias). Números de concordância: evento é difícil (67%), entidade-chave é fácil (doença 100%, país 97,7%). | Anotação manual, sem modelo; **tudo inglês**; nenhum esquema PT-BR. `conway2010` não é distribuível (copyright) e só 176/200 docs seguiam online. | tentar depois |
| 9 | Notícia geolocalizada → série regional + validação externa | `kriesch2025geolocated` | O desenho mais próximo do nosso: notícia → série semanal por região subnacional (NUTS-3), busca semântica por tema, validada contra fonte externa independente (Google Trends, Pearson 0,84). Checagem de plausibilidade: artigos escalam quase com a população (coef 0,99, R² 0,507). Quantização Int8 retém 93,55% da acurácia com 4× menos memória. | O modelo é **alemão** (inútil em PT-BR); escala de 49,4M artigos; exigiria spaCy + gazetteer BR + Nominatim + um LLM 8B para anotar o treino do NER. Só a **receita de validação** transfere. | tentar depois |
| 10 | Geoparsing / reconhecimento de topônimo | `keller2009vocabulary`, `hu2023location`, `gritta2020pragmatic`, `syed2023geospatre`, `chanlekha2010spatial` | `hu2023` é o melhor comparativo: só 2 de 27 ferramentas passam de recall 0,7; unidades administrativas (o nosso caso: BR + UFs) são a categoria **mais fácil** (13/27 >60%); deep learning é o mais preciso e o mais lento (6 min a 33 h). `gritta2020` dá métricas de avaliação (Accuracy@161km, AUC) e mostra que a heurística de população é um baseline forte. | Tudo inglês; exigiria modelos PT-BR (spaCy pt, BERTimbau, Stanza-pt) não avaliados; dependências novas (spaCy, geopandas, Nominatim). E o ganho é pequeno: o repo já decidiu que notícia nacional não cria resolução espacial (município não resolvido é limitação declarada). | descartar |
| 11 | Extração por ensemble de LLM | `consoli2025knowledge` | Ensemble com majority voting supera cada LLM isolado nas 4 tarefas (doença F1 0,851, país 0,962); SBERT com limiar 0,8 agrupa sinônimos; contagem de casos continua a pior (0,658). Baseline = 10 LLMs comerciais e abertos. | LLMs de 7B a 70B — **inviável em CPU** (minutos por documento a horas); exige UMLS; é terreno do braço 04, explicitamente "corredor por fora". | descartar |
| 12 | Vigilância por consulta de busca / mídia social | `milinovich2013internet`, `madoff2011monitoring` | Avisos que valem: busca **acompanha** (não antecipa) a dengue; interesse movido pela mídia é o maior confundidor; resolução espacial limitada (estado/cidade só nos EUA). Baseline = vigilância tradicional. | A entrada é log de busca do Google — modalidade que **não temos** e não é pública nessa granularidade; nada a rodar sobre o corpus de notícia. | descartar |

### Abordagem por abordagem (aplicação)

**1. Protocolo de avaliação contra padrão-ouro.** O item mais valioso da família, e o mais barato de
adotar: não é um modelo, é um desenho. O protocolo 00 já pede exatamente isso (rolling-origin,
controle negativo de texto embaralhado, timeliness + erro contra SINAN) e as notas registram que ele
não rodou. Estes artigos dão o vocabulário (detecção bruta/precoce/intrínseca, EPPV) e o piso de
expectativa (9,2% de sensibilidade oportuna com frequência pura). Custo: fixar o padrão-ouro — SINAN
`cases.py` é o candidato.

**2. Extração por dicionário + regra.** É o braço 01; a linhagem confirma as escolhas de desenho
(cascata, container relationships) e diz onde ela é mais frágil (contagem). O que falta não é técnica,
é a validação — a amostra anotada.

**3. Anotação não-experta.** É o método para fechar o item aberto nº1 do braço 01 sem especialista em
tempo integral. `pitler2008revisiting` contém Snow 2008 (arquivo trocado), que é sobre anotação AMT —
ranqueei a abordagem que o PDF realmente descreve.

**4. Enquadramento de fonte única / mídia local.** `schwind2014` dá o número que o artigo precisa
(71/87 eventos únicos à fonte local) e `neto2016` dá o contexto brasileiro. Não é pipeline; é
justificativa medida.

**5. Detecção de aberração.** Leve e diretamente ligada à tarefa (news → alarme), mas fica a jusante
da série validada; `tentar depois`.

**6. Classificação supervisionada de relevância.** Barata e com um achado de pooling útil
(início+fim), mas trava na falta de rótulo e é parcialmente desnecessária num corpus já filtrado por
termo de doença.

**7. Tópicos / grafo de palavras-chave.** O braço 03 já cobre tópicos; o que presta aqui é a
referência PT-BR (`melo2021`) e o desenho de estágio (`you2021`), ambos com dependências pesadas e
sem baseline.

**8. Esquema de anotação.** Moldes úteis para a amostra anotada, mas exigem tradução do esquema para
PT-BR/dengue.

**9. Notícia geolocalizada → série regional.** A receita de validação (série regional contra fonte
externa independente; checagem de escala por população) transfere de graça; o ferramental concreto é
alemão e de escala errada.

**10–12. Descartadas.** Geoparsing (alvo é UF, notícia é nacional, tudo inglês, dependências novas);
ensemble de LLM (CPU-only inviável, é o braço 04); vigilância por busca/social (modalidade errada —
temos notícia, não query).

---

## Cross-cutting (decisão de desenho, não de artigo)

- **O slot de contagem é o mais fraco em toda a linhagem** (`consoli2025` 0,658; `arsevska2018` 85%
  vs 95%; `ng2020nlp` ausente em produção; braço 01: 24% dos artigos). Decisão: não apostar o artigo
  em contagem extraída — mandar para extração estruturada (braço 04).
- **PT-BR é lacuna documentada em toda a família** (`brownstein2008` "under development";
  `collier2010` perdeu o Ceará 2008; `meng2022`/`mutuvi2020` traduzem para inglês; todo o geoparsing é
  inglês; `kriesch2025` é alemão). Nenhum sistema mede extração sobre notícia PT-BR — é a contribuição
  do nosso corpus.
- **Toda avaliação é contra um padrão-ouro curado (silver), nunca ground truth** (`ganser2022`: "a
  proper gold standard does not exist"; `collier2010`: ProMED como "approximate gold standard";
  `barboza2013`: padrão-ouro incompleto). Consequência: qualquer lead-time nosso é vs SINAN, que é
  reescrito — declarar.
- **Frequência/volume sozinho é sinal fraco e confundido** (`ganser2022` 9,2% oportuno; `collier2010`
  viés de dia da semana; `brownstein2008`/`milinovich2013` cobertura segue mídia/infra, não carga).
  Reforça o controle negativo do protocolo 00.
- **O sinal informativo está no título/lead, não no corpo** — `mutuvi2020` (início+fim 87,82 vs corpo
  77,94) e o próprio braço 02 (`title-only` 0,156 vs full-text 0,105). É decisão de desenho da
  representação, e vale para os dois grupos.
- **Truncamento/pooling não é parâmetro neutro** — `mutuvi2020` corta em 512 e acha início+fim mais
  informativo; o braço 02 corta 39% dos artigos na janela 512. Regra de truncamento/pooling única a
  fixar no protocolo 00.
- **Classificação de relevância é assumida a montante em todo sistema** (`collier2008` NB gate,
  `valentin2020` classifier) — o nosso corpus já é pré-gated por termo de doença, o que pula esse
  passo e é uma escolha de desenho a declarar.
- **Baseline fraco ou ausente é a regra** (`freifeld2007`, `brownstein2008`, `valentin2020`,
  `ganser2022`, `you2021`, `melo2021`). "Funciona" nessas fichas não é comparativo.
- **Custo computacional "não reportado" é quase universal** — toda estimativa de custo de adoção
  neste documento é minha, não das fichas. Incerteza não é barato.
- **Grupo representação:** as três fichas são de legibilidade (2) e correferência (1) e nenhuma mede
  a nossa tarefa. O grupo aplicação, em contraste, tem fichas que testam notícia de doença — a frase
  "nenhuma ficha testa a nossa tarefa" seria falsa sobre a biblioteca, só verdadeira sobre
  `representacao`.
- **Qualidade das fichas:** duas estão com arquivo trocado — `chae2009fluency` contém Klenner &
  Ailloud (correferência) e `pitler2008revisiting` contém Snow et al. (crowdsourcing). Ranqueei pelo
  conteúdo real do PDF, não pelo nome.

---

## First move

Rodar o desenho de avaliação da linhagem EBS — sensibilidade oportuna + timeliness do `news_volume`
do braço 01 contra a série de casos suspeitos do SINAN, com o controle negativo de texto embaralhado
que o protocolo 00 já exige — porque toda a família de aplicação diz que é a medição, não o modelo,
que decide, e as notas registram que o protocolo 00 ainda não rodou.

---

## O que ficou de fora e por quê

- **Correferência por ILP** (`chae2009fluency`): ranqueada como `representacao` rank 3 e descartada —
  não é a nossa tarefa e exigiria um corpus-ouro PT-BR de correferência. O PDF é Klenner & Ailloud
  (EACL 2009), não o Chae & Nenkova que o nome promete.
- **Cross-lingual como técnica** (`collier2011cross`, `mutuvi2020multilingual`, `meng2022biocaster`):
  descartada como técnica — o corpus é mono-PT-BR e não temos as outras 12 línguas. Sobrevive só o
  achado de que Dengue-Brasil tem cobertura PT massiva, muito maior que em inglês, o que sustenta a
  fonte PT-BR.
- **Fundidos em linha própria:** `meng2022biocaster` entra como evidência fraca da linha 6 (extração
  neural, sem número); `ng2020nlp` e `keller2009unstructured` fundidos na linha 2 (mapa de tarefas e
  overview de EBS, sem técnica própria); `carlson2023who`, `conway2010disease` e `chanlekha2010spatial`
  fundidos nas linhas 2/8 (esquemas de anotação).
- **Fichas de aplicação não competem com as de representação** e foram mantidas no grupo delas,
  conforme a marcação.
