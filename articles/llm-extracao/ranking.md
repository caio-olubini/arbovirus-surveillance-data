# Ranking das abordagens — extração estruturada de eventos por LLM

Artefato do workflow de referência da família `llm-extracao`. Ranqueia **abordagens**, não
artigos: várias fichas podem descrever a mesma abordagem e nesse caso é uma linha só, com a
evidência somada. As duas colunas são sempre separadas — `merit` (o que a abordagem entrega, e
contra que baseline) e `adoption_cost` (o que ela custa **aqui**). O rank não é o custo: é o
valor para a pergunta que temos; o custo aparece na coluna própria e decide só o `verdict`.

Leitura dos vereditos: **tentar agora** = dá para fazer neste repositório hoje, com o que já
está instalado; **tentar depois** = desenho certo, bloqueado por compute, dependência ou
rótulo; **descartar** = não paga o custo aqui.

Contexto que define "usável": corpus de 4.369 artigos da Agência Brasil (dengue, PT-BR, 965
semanas, 28 locations = BR + 27 UFs); CPU only, sem GPU; extras fixados em `pyproject.toml`
(`embeddings` = torch+transformers ~800 MB, `topics` = tomotopy); braços 01 (léxico), 02
(bracket de 6 configs de embedding) e 03 (DMR/tomotopy) já construídos e medidos; custo de
dependência nova é alto e o transform precisa rodar em CPU em minutos, não horas. O corpus é
**texto limpo**, não PDF — a camada de OCR de uma das fichas não tem o que fazer aqui. A
pergunta que esta família serve é a do braço 04 (`notes/04-llm-extracao-estruturada.md`):
extrair os slots epidemiológicos (doença, local, tipo de incidente, contagem, gravidade,
intervenção, surto, data) de prosa PT-BR, com foco no slot de **contagem**, o mais fraco do
braço 01.

Fontes de custo: `src/pipeline/news/README.md`, `notes/00-protocolo-comparacao.md`,
`notes/04-llm-extracao-estruturada.md`, `pyproject.toml`.

**Nota de composição.** As 10 fichas marcam **todas** o grupo `aplicacao`; nenhuma é
`representacao`. Não é defeito da marcação: a definição de `representacao` é "o artigo trata de
COMO transformar texto em número — encoder, pooling, normalização, geometria, dimensionalidade,
vale independente do domínio", e nenhum dos 10 estuda representação *como representação*. Os
que tocam o eixo (Abbood 2020 compara bag-of-words tf-idf contra word2vec e contra embedding de
documento; Dewandaru 2020 usa GloVe; Kim 2020 compara CNN de caractere contra BiLSTM de
palavra) fazem isso como **meio** de uma tarefa de extração/triagem, e o próprio campo
`representation` de cada ficha diz "não é um estudo de representação". A família também é
escopada como aplicação no `familias/llm-extracao.json` (dicionário/regra e topic modeling
ficam fora de escopo). Consequência: **há um só `rank 1`, não dois** — só existe um grupo.
Quando uma rodada trouxer fichas marcadas `representacao`, elas entram em tabela própria e não
são comparadas com estas.

---

## Representação — como transformar texto em número

**Vazia nesta rodada.** Nenhuma das 10 fichas está marcada `representacao`, e não fabriquei
linhas de representação a partir de fichas que não as sustentam. A pergunta "qual representação
rende mais por unidade de esforço aqui" já foi respondida pelos braços 01–03 e pelas famílias
`embeddings`/`topicos`; esta família não a reabre. Sem linhas para ranquear e sem comparação
cruzada com a tabela de aplicação abaixo.

O que as fichas *tocam* do eixo, e por que não virou linha: as três técnicas de vetorização que
aparecem (embeddings de palavra estáticos tipo word2vec/GloVe/fastText com pooling por média;
representação aprendida em nível de caractere; embeddings de frase contextuais tipo SBERT/BERT)
são todas **meio** dentro de um pipeline de aplicação, nenhuma com estudo de pooling,
normalização, geometria ou dimensionalidade. Ranqueá-las como representação seria misturar os
dois grupos — exatamente o erro que esta correção existe para impedir. A única com uso direto
possível aqui (SBERT/BioBERT para similaridade de termos, de Consoli 2025) entra como linha de
**aplicação**, porque é lá que ela é usada.

---

## Aplicação — onde usar, no nosso domínio

Alternativas entre si dentro do grupo. Dois "tentar agora", três "tentar depois", três
"descartar".

| # | Abordagem | Fichas | Merit (o que entrega, contra que baseline) | Adoption cost (aqui) | Veredito |
|---|---|---|---|---|---|
| 1 | Extração generativa por LLM com schema estrito (zero/few-shot, sem fine-tuning) | `schmidt2024`, `mortezaagha2026` (instância de domínio: `consoli2025`) | Schmidt 2024 (GPT-4 zero-shot, 30 abstracts, 260 itens): 78% completamente corretos, 13% parciais, 10% errados contra extração humana; booleanos e números estáveis, strings abertas instáveis (69% idênticas a temperature 0; 7% de mudança substantiva). Mortezaagha 2026 (schema Pydantic + evidência verbatim + merge determinístico): o refino de schema+prompt leva desfechos de 33%→95%, presença/tipo de desfecho 50%→100% e desenho 75%→100%; evidência preenchida em >99% dos casos; 11 s/PDF contra ~30–40 min de extração manual. Baseline comum: extração humana; Mortezaagha **não tem** baseline externo (os autores declaram). Consoli 2025 dá a instância de domínio: doença F1 0,851, país 0,962, casos 0,658, data 0,869. | Precisa de um LLM. Nenhuma rota local cabe em CPU-minutos sobre 4.369 artigos (7B+ = horas); API de nuvem é paga e o custo **não é reportado** (Schmidt não dá tokens/$; Mortezaagha dá só US$2/1k páginas de OCR, irrelevante aqui). Não precisa de rótulo para o método (só para avaliar). Dependência nova: runtime de LLM local (pesado) ou credencial de API. Mortezaagha ainda exige um especialista de domínio por schema (2–4 semanas). Evidência só em inglês/outro domínio. | tentar depois |
| 2 | Contrato de saída: JSON como formato de serialização + pedido direcionado | `neveditsin2025` | JSON é o formato mais parseável (McNemar pareado: JSON>YAML χ²=167,6; JSON>XML χ²=69,4; YAML>XML χ²=32,4, todos p≪0,05); o pedido direcionado tem o maior efeito medido (V de Cramér=0,42) e modelos maiores erram menos estruturalmente (90,3% vs 82,6% vs 80,9%, efeito modesto V=0,11). Mede só validade **sintática**, não semântica; documenta os padrões de falha. Baseline: comparação entre formatos e entre tipos de prompt. | Zero: é um achado, sem dependência nova. Só importa quando o braço 04 usar um LLM; hoje não temos essa etapa. Decisão de desenho que se registra agora, custo nenhum. | tentar agora |
| 3 | Resolução/normalização de termos por similaridade de embeddings (limiar) | `consoli2025` | Agrupa sinônimos de doença/local por cosseno (SBERT all-mpnet-base-v2 / BioBERT, limiar fixado em 0,8) mais synsets do WordNet. Baseline: igualdade de string. Evidência **fraca**: limiar escolhido "experimentalmente", sem análise de sensibilidade; é utilitário, não o foco do artigo. | Baixo: CPU, e os encoders PT/multilíngues já estão no extra `embeddings` (BERTimbau, E5, BGE-M3). Roda sobre strings curtas. Normaliza **variantes de termo** (ex.: "febre da dengue" vs "dengue"), mas **não** resolve município→UF — isso é gazetteer, não cosseno. | tentar agora |
| 4 | Geoparsing de evento + resolução LOC vs pseudo-local (PLOC) + argumentos numéricos | `dewandaru2020` | A taxonomia LOC vs PLOC e a ligação evento→coordenada→números resolvem exatamente o nosso viés de menção (uma matéria cita muitos lugares, só um é o foco). +23,43% de F1 no passo PLOC (0,734→0,906); +13,88% em argumento (0,785→0,894); +2,46% em entidade (dentro do ruído). Baseline: o mesmo modelo sem as features de evento/regex. Corpus minúsculo (927 sentenças), indonésio. | Método é indonésio, supervisionado (927 frases anotadas), exige POS tagger PT + gazetteer + anotação, e novas dependências (NCRF++, MALLET/Gensim). Sem comparação com outros geoparsers. A **taxonomia** sozinha é grátis de ler e citar; o método não roda aqui. | tentar depois |
| 5 | Triagem binária de relevância (documento vs frase) antes de extrair | `kim2020`, `abbood2020` | Kim 2020 (2.864 docs): classificar por **frase** e agregar bate classificar o documento (BiLSTM+SenClass 92,9% vs DocClass 83,9%; ConvNet 89,4% vs 87,6%), porque o sinal cabe em 1–2 frases — e nossas matérias são longas. Abbood 2020 (3.236 artigos, 5% relevantes): pontuação de relevância supervisionada superajusta à classe positiva (precisão máx. 0,22); sem sobreamostragem ADASYN a sensibilidade cai a 0,03. Baseline: TF-IDF + ML clássico / sem sobreamostragem. | Exige rótulos que não temos; o corpus já passou pelo portão de termo-doença, então a triagem responde a uma pergunta que o corpus já respondeu. Kim é inglês, de sites formais de vigilância (WHO/ProMED/CDC), não agência generalista. | tentar depois |
| 6 | NER / rotulagem de sequência supervisionada (encoder transformer ou BiLSTM-CRF) | `algaradi2025`, `abbood2020`, `dewandaru2020` | Al-Garadi 2025: RoBERTa micro-F1 0,88 para NER, mas o baseline é só a comparação entre 4 transformers (ICs se sobrepõem: RoBERTa 0,88 vs ALBERT 0,86 vs BERT/BERTweet 0,84). Abbood 2020: EpiTator/heurística acerta país 85% e doença 88%, mas data e contagem 0%. Baseline: outros transformers. | Alto: exige rótulos token-level que não temos; só inglês; novas dependências (BERTweet, NCRF++, InaNLP). Sem baseline trivial. | descartar |
| 7 | Extração generativa com modelo open-weight fine-tunado / instruction-tuned | `shamsabadi2024`, `li2024aegpt` | Shamsabadi 2024 (FLAN-T5-Large 780M fine-tunado por instrução): bate GPT-3.5 (1000x maior) zero-shot em ROUGE (ROUGE-1 80,77 vs 68,44) e o melhor F1 parcial é 0,559 — absoluto modesto. Li 2024 (GPT-3.5 fine-tunado): micro-F1 0,704 estrito vs 0,68 do BERT de domínio — ganho de ~0,02, provavelmente dentro do ruído. Baseline: GPT-3.5 zero-shot / BERT de domínio. | Alto: exige rótulos que não temos (1.500 e 91 documentos anotados à mão) e treino em GPU (12–30 h; A100/V100 reportadas). O resultado principal do Li depende de API proprietária. | descartar |
| 8 | Ensemble de LLMs + votação por maioria (mitigação de alucinação) | `consoli2025` | Reduz alucinação; melhor nas 4 tarefas avaliadas, mas o ganho sobre o melhor modelo isolado está dentro do ruído (doença 0,851 vs 0,842; casos 0,658 vs 0,653; empates resolvidos por sorteio). Baseline: LLMs isolados. | Alto e inviável: 3 LLMs, incluindo Llama-3-70B — não cabe em CPU razoável, e o próprio artigo reporta inferência lenta no 70B. Sem custo reportado para estimar para baixo. | descartar |

### Abordagem por abordagem (aplicação)

**1. Extração generativa por LLM com schema estrito.** É a abordagem central da família e o
desenho que o `notes/04` já rascunha (schema JSON estrito + 4–8 exemplos few-shot). As duas
fichas dão o mesmo recado de lados opostos: Schmidt 2024 mostra que o *prompt zero-shot* de um
LLM de nuvem extrai booleanos e números de forma confiável e strings abertas de forma ruim, e
que o prompt não viaja entre domínios; Mortezaagha 2026 mostra que *restringir a geração a um
schema tipado* (vocabulário fechado, default nulo, evidência verbatim) eleva campos que estavam
em 33–75% para 95–100% — mas sem baseline externo, o que enfraquece o número. O custo é o que
decide o veredito: o repositório é CPU-only e o transform precisa rodar em minutos, então
qualquer rota local (7B+) estoura; sobra a API de nuvem, que é paga e tem custo não reportado.
Some-se a isso que nenhuma das duas mede PT-BR nem notícia. É **tentar depois**: o desenho está
certo, o acesso ao modelo é a pendência.

**2. Contrato de saída JSON.** A contribuição de Neveditsin 2025 é estreita mas acionável: se o
braço 04 existir, a saída é JSON, e há um ranking de formatos com testes pareados para justificar
a escolha. Não mede acurácia semântica em momento algum — um JSON válido pode estar
clinicamente errado — então não é evidência de extração, é evidência de formato. Custo zero;
fixa-se agora como decisão de desenho. **tentar agora.**

**3. Resolução de termos por similaridade de embeddings.** A parte barata de Consoli 2025 e a
única que roda hoje: encoders PT/multilíngues já instalados, cosseno sobre strings curtas,
limiar. A evidência da ficha é fraca (limiar sem sensibilidade) e o encaixe é **parcial**: ela
normaliza variantes de termo ("dengue" / "febre da dengue"), mas o viés de menção por UF e os
municípios não resolvidos do braço 01 (`README` §2 e §6.2) são um problema de **gazetteer**, que
cosseno não resolve. Vale testar como heurística de normalização barata, não como resposta ao
escopo. **tentar agora.**

**4. Geoparsing LOC vs PLOC.** Dewandaru 2020 nomeia exatamente o problema que o nosso braço 01
declara: uma matéria cita muitos lugares e só um é o foco do surto. A taxonomia de pseudo-locais
(metonímia, contexto GPE, nome de organização, menção não-locativa) é geral e vale para PT-BR; o
método (BiLSTM-CRF indonésio, supervisionado, com gazetteer e POS da língua) não. É a mesma
situação do Meier 2024 no ranking de tópicos: o *desenho* transfere, o *artefato* não. **tentar
depois.**

**5. Triagem binária de relevância.** O achado que transfere é a granularidade: em documento
longo com sinal localizado, classificar por frase e agregar bate classificar o documento (Kim
2020). Isso dialoga com o `title-only` do braço 02 e com o fato de as nossas matérias serem
longas. Mas a triagem exige rótulos e responde a uma pergunta que o portão de termo-doença já
respondeu; Abbood 2020 ainda mostra precisão de 0,22. **tentar depois.**

**6–8. Descartadas.** O ensemble precisa de três LLMs, um deles de 70B — frontalmente
incompatível com CPU-only. O fine-tuning exige rótulos que não temos e GPU. O NER supervisionado
exige rótulos token-level e só foi medido em inglês. As três pressupõem a extração generativa
funcionando (rank 1) e nenhuma paga o custo aqui.

---

## Cross-cutting (decisão de desenho, não de artigo)

Como esta leva é só `aplicacao`, não há afirmação cross-group; todas as frases abaixo são do
grupo `aplicacao` e estão nomeadas como tal.

- **Aplicação: nenhuma ficha mede PT-BR nem notícia de agência brasileira.** Todas medem inglês
  (WHO DON, VAERS, notas clínicas, abstracts de revisão sistemática, redes sociais dos EUA) ou
  indonésio (Dewandaru). A pergunta do grupo — o que já foi feito em notícia de língua
  portuguesa como fonte de vigilância — tem por resposta, nesta família, **nada**.
- **Aplicação: as fichas testam vigilância a partir de texto, mas não a NOSSA tarefa-alvo.** Elas
  extraem ou triam fatos de notícia/relato de surto (doença, local, data, contagem) — que é
  justamente a *entrada* do braço 04 — mas nenhuma prevê a série de casos suspeitos que os
  braços 01–03 predizem. Então "melhor" nessas fichas significa melhor na extração, não no alvo
  do protocolo 00. Dizer "nenhuma ficha testa a nossa tarefa" seria verdade sobre o **alvo**
  (previsão de série) e falso sobre a **tarefa de extração**: é exatamente aí que elas medem.
- **Aplicação: o custo escondido de todas é o rótulo humano.** Consoli (171 amostras do IDB),
  Al-Garadi (4.200 documentos), Kim (2.864), Shamsabadi (1.500 abstracts), Dewandaru (927
  sentenças), Neveditsin (105 notas), Li (91 relatos), Schmidt (30 estudos). Nenhuma dessas
  abordagens roda sem um gold standard anotado à mão para se avaliar — e nós não temos um.
- **Aplicação: a contagem numérica é o campo mais fraco de todas.** Schmidt (desenho de estudo
  47%), Consoli (casos F1 0,658), Al-Garadi (acurácia despenca para todas as causas),
  Shamsabadi (data e método <50%), Abbood (contagem com precisão 0,20). É exatamente o slot que o
  `README` §2 já marca como o mais fraco do braço 01 e para o qual o braço 04 existe. As fichas
  não prometem que o LLM resolve isso — só que ele não é trivial.
- **Aplicação: baseline fraco ou ausente é a regra.** Mortezaagha declara não ter comparação
  head-to-head; Schmidt compara só com humano; Dewandaru compara o mesmo modelo sem as features;
  Kim capou o SVM em 10% dos dados. "Funciona" nessas fichas não é comparativo.
- **Aplicação: custo computacional "não reportado" é quase universal.** Schmidt não dá tokens/$;
  Neveditsin não dá hardware; Al-Garadi não dá GPU; Shamsabadi dá só GPU (3090); Mortezaagha dá
  só o preço de OCR, irrelevante aqui. Toda estimativa de `adoption_cost` acima é minha, derivada
  do que o repositório tem — incerteza não é barato.
- **Aplicação: a camada de OCR/PDF de parte da família não tem o que fazer aqui.** O núcleo da
  contribuição de Mortezaagha é OCR de PDF denso; nosso corpus já é texto limpo. Fica só o padrão
  de schema + evidência.
- **Aplicação: vazamento e instabilidade aparecem em várias fichas.** Schmidt admite que o GPT-4
  pode ter visto parte dos dados avaliados e mede 7% de mudança substantiva a temperature 0;
  Shamsabadi seleciona a melhor instrução no conjunto de *teste*; Neveditsin usa uma única
  configuração de decodificação. É o mesmo risco que o `notes/04` marca como agudo para o nosso
  corpus (que vai até 2026 e inclui o recorde de 2024) — a regra de corte conhecido do protocolo
  00 vale para o braço 04.
- **Grupo `representacao`: vazio, e por isso não há a frase "nenhuma ficha mede a nossa tarefa"
  aplicada à biblioteca inteira.** Não há ficha de representação nesta família para medir (ou
  deixar de medir) a nossa tarefa; o grupo simplesmente não existe aqui. As fichas de aplicação
  são as que testam extração de notícia/relato de surto.

---

## First move

Rodar a extração com schema JSON estrito (few-shot) sobre uma amostra pequena anotada à mão — a
mesma que o `notes/04` manda compartilhar com o braço 01 — com um modelo open pequeno ou via
API, porque é o único experimento que responde se o braço 04 bate a regex no slot de contagem, e
ensemble, fine-tune e NER só se justificam depois que isso funcionar.

---

## Perguntas abertas

- **Qual modelo, e com que corte de treino?** Nenhuma ficha resolve a escolha de um LLM local
  que caiba em CPU-minutos; a decisão entre API paga e peso aberto pesado continua aberta, e o
  `notes/05` já registra o vazamento temporal como agudo (o corpus vai até 2026 e inclui o
  recorde de dengue de 2024).
- **Existe um caminho local barato?** Nenhuma ficha mede um LLM generativo em CPU sobre corpus
  desse tamanho; o custo é "não reportado" em todas. A estimativa de que 7B+ não cabe é minha,
  não medida.
- **A normalização por embeddings resolve alguma coisa de escopo?** A evidência (limiar 0,8 sem
  sensibilidade) é fraca e o encaixe no viés de menção é parcial; falta decidir se o ganho sobre
  o `UfMatcher` atual justifica o trabalho, e como medir isso sem um gold standard de
  localização.
- **Quanto custa o rótulo que todas as abordagens de avaliação exigem?** Nenhuma ficha mede o
  custo humano de anotação em horas ou valor, e é o gargalo comum a praticamente todas.

---

## O que ficou de fora e por quê

- **3 abordagens marcadas `descartar`** (ensemble de LLMs; fine-tuning open-weight; NER
  supervisionado). Motivos: três LLMs incluindo 70B incompatível com CPU-only; rótulos que não
  temos mais treino em GPU; rótulos token-level e medição só em inglês. Todas pressupõem a
  extração generativa funcionando.
- **Sem linhas de representação.** Esta leva é 100% `aplicacao`; não há fichas de representação
  para ranquear e não inventei nenhuma. Por isso há um só `rank 1`. As duas famílias de grupos
  não foram comparadas entre si.
- **Não incluído como linha própria (fundido):** `mortezaagha2026` foi fundido com `schmidt2024`
  na linha 1 (ambos são extração generativa com schema; o OCR do Mortezaagha é irrelevante para
  nós); `abbood2020` aparece nas linhas 5 (pontuação de relevância) e 6 (NER/EpiTator), conforme
  o eixo; `dewandaru2020` aparece nas linhas 4 (geoparsing) e 6 (BiLSTM-CRF); `consoli2025`
  aparece nas linhas 1 (instância de domínio), 3 (resolução de termos) e 8 (ensemble), conforme a
  peça que a ficha descreve.
- **Construção de grafo de conhecimento (RDF/OWL, Consoli 2025) ficou fora como linha própria.**
  O produto do artigo é um grafo ligado a ontologias biomédicas e geográficas; o nosso produto é
  uma série semanal por UF × EW, não um grafo. O que aproveitamos do Consoli é o esqueleto ETL →
  extração → validação → votação (linhas 1, 3 e 8), não o RDF.
- **Números de custo:** como quase nenhuma ficha reporta runtime ou preço, as estimativas de
  `adoption_cost` são minhas, ancoradas no que o repositório já tem (encoders instalados →
  normalização por embeddings é barata; sem runtime de LLM e sem GPU → extração local é
  caríssima).
