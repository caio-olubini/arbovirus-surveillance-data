# 01 — Léxico PT-BR + regras → features semanais

**Estado:** testando — 2026-10-07 (implementado e validado; falta rodar o protocolo 00)
**Papel no artigo:** representação concorrente (ver [00](00-protocolo-comparacao.md))

## Hipótese

Menções explícitas de doença, gravidade e contagem, extraídas por dicionário e
regra, produzem uma série semanal que acompanha a epidemia e que o modelo
consegue usar como covariável. É a representação mais conservadora e a única com
precedente direto em dengue.

## O que produz

Cinco features por UF (ou BR) × EW. As três primeiras foram o plano original; as
duas últimas entraram na implementação e estão explicadas abaixo.

| Feature | Como | Intuição |
|---|---|---|
| `news_volume` | nº de artigos de dengue na semana | atenção midiática bruta |
| `news_severity` | contagem ponderada por termos de gravidade | distingue "alerta" de "epidemia" |
| `news_cases` | contagens numéricas explícitas no texto | o slot mais difícil e mais valioso |
| `news_deaths` | contagens explícitas de óbitos/mortes | regra `"X óbitos"` que já estava na lista |
| `news_articles_with_cases` | quantos artigos declararam contagem | responde se `news_cases` se sustenta |

**Implementado.** Corpus congelado em `data/pipeline/news/EBC_dengue_text.parquet`;
features em `EBC_dengue_lexicon_EW.parquet`; léxico versionado em
`data/news/reference/lexico_dengue.yaml`. Código em `src/pipeline/news/` (extração
compartilhada em `common.py`, braço em `lexicon/`). Comandos:
`arboili transform news-text` e `arboili transform news-lexicon`.

Léxico (PT-BR, flexões e acentuação normalizadas — `strip_accents` + regra
automática de plural):

- **Doença:** dengue, chikungunya, zika, febre amarela, arbovirose, *Aedes aegypti*,
  *Aedes albopictus*.
- **Clínico:** febre, dor de cabeça, dor atrás dos olhos, dor no corpo, manchas,
  náusea, vômito, sangramento, choque, plaquetas, hospitalização, UTI, óbito.
- **Gravidade / epidemia:** surto, epidemia, pandemia, alerta, emergência, crise,
  colapso, aumento de casos — com pesos ordinais 1/2/3.
- **Vetor / controle:** mosquito, criadouro, fumacê, larvicida, visita domiciliar,
  mutirão.
- **Localidades:** 27 UFs, nomes completos (case-sensitive, sobre o texto original)
  + siglas só com pista locativa. **Municípios não são resolvidos** — declarado.

Regras: regex para contagens (`"X casos"`, `"X mil casos"`, `"X óbitos"`) + janela de
negação + dois portões adicionais que só apareceram medindo (ver abaixo).

## Como testar

1. Extrair o texto dos HTMLs (o pipeline de texto **não existe ainda** — é o
   primeiro trabalho concreto deste caminho).
2. Montar o léxico e as regras; congelar como arquivo versionado.
3. Anotar à mão uma amostra estratificada (~200–400 artigos, cobrindo anos, UFs e
   períodos de surto e de calmaria) e medir precisão/recall/F1 por campo, mais
   concordância entre anotadores. **Não existe corpus anotado de dengue em PT-BR**
   — esta validação é contribuição, não burocracia.
4. Agregar em UF × EW, alinhar ao calendário do SINAN.
5. Rodar o protocolo 00.

## Evidência

Linhagem canônica da *event-based surveillance*, toda de dicionário + regra:

- **HealthMap** — dicionários de padrões de doença + gazetteer de ~25 mil
  localidades, classificação de relevância. [Brownstein 2008, *PLoS Med* 5(7):e151](https://doi.org/10.1371/journal.pmed.0050151);
  detalhe técnico em [Freifeld 2008, *JAMIA* 15(2):150](https://doi.org/10.1197/jamia.M2544).
- **BioCaster** — ontologia BCO + NER + reconhecimento de evento sobre 1.700+ feeds.
  [Collier 2008, *Bioinformatics* 24(24):2940](https://doi.org/10.1093/bioinformatics/btn534).
- **Comparação multi-sistema** (GPHIN, HealthMap, EpiSPIDER) —
  [Keller 2009, *EID* 15(5):689](https://doi.org/10.3201/eid1505.081114).
- **PADI-web** — regra + mineração sobre Google News; doença/local/data/hóspede/nº
  de casos; detectou surtos de ASF/IA/FMD **até 8 dias antes** da notificação da OIE.
  [Arsevska 2018, *PLoS ONE* 13(8):e0199960](https://doi.org/10.1371/journal.pone.0199960).
- **EventEpi / EpiTator** — NER em dois passos + Naive Bayes para os slots duros,
  inclusive contagem de casos confirmados.
  [Abbood 2020, *PLoS Comput Biol* 16(11):e1008277](https://doi.org/10.1371/journal.pcbi.1008277).
- **Dengue especificamente** — contagem de artigos vs. casos, R²≈0,88 (Índia) e
  timing do Zika no **Brasil**; jornal local bate jornal internacional.
  [Zhang 2020, *J Biomed Inform* 102:103374](https://doi.org/10.1016/j.jbi.2020.103374).
- **Dengue no Sri Lanka** — 565 hits do HealthMap 2007–2015 altamente
  correlacionados com a tendência nacional. Verificado.
  [Wilder-Smith 2016, *Glob Health Action* 9:31620](https://doi.org/10.3402/gha.v9.31620).
- **Dengue no Brasil (português, mas manual)** — análise de conteúdo de 69 artigos
  da Agência Brasil + Estadão. Único uso conhecido do *seu* corpus, e é manual.
  Tuma 2017, dissertação Unicamp (não revisado por pares).

**Contra-evidência que precisa estar no artigo:** [Ganser 2022, *JMIR Public Health
Surveill* 8(10):e36211](https://doi.org/10.2196/36211) comparou HealthMap e EIOS
contra FluNet em 24 países: detectou 73,5% dos 238 surtos, mas **só 9,2% dentro de
±2 semanas**. É a expectativa realista para volume puro de notícia. Verificado.

## Medições da implementação (2026-10-07)

Tudo medido no corpus completo (4.569 artigos, 2002–2026), não em amostra. O que
segue muda o que este braço pode reivindicar no artigo.

**1. `news_cases` é magro, e isso é a resposta à pendência original.** Só **24%**
dos artigos (1.089/4.569) declaram alguma contagem de casos, e **6%** (276/4.569)
uma de óbitos. Consequência direta: `news_cases` fica não-nulo em **511 de 965**
semanas e `news_deaths` em **189**. Ou seja, em metade das semanas o slot mais
valioso está ausente. `news_volume` e `news_severity` estão presentes em **todas**
as 965 — são o que este braço consegue defender sozinho. A recomendação que sai
daqui é levar `news_cases`/`news_deaths` para o caminho 04 (extração estruturada),
onde a leitura é do artigo inteiro e não de uma regex sobre prosa geral.

**2. As contagens relatadas são acumuladas, não semanais.** A maioria dos artigos
diz "ao longo de 2024, 6,6 milhões de casos". O máximo semanal é a *escala do maior
número que a imprensa citou naquela semana*, não a incidência da semana. Usar isso
como covariável semanal sem modelar a diferença é um erro real — item aberto para o
protocolo 00. O máximo de `news_cases` (6.629.595) é o recorde real de 2024; o de
`news_deaths` (500.000) **não** é dengue, é uma estimativa global de doenças
negligenciadas numa frase que por acaso nomeia dengue. Um resíduo desse tipo
sobrevive aos três portões e fica documentado em vez de suavizado.

**3. Os três portões nas contagens, e o que custaram.** Extrair número de prosa
jornalística é dominado por números que não são da dengue: o corpus contém
`700 mil mortes` (covid), `655 mil mortes` (malária), `38.892 mortes` (violência) e
`24 mil mortes prematuras` (poluição), cada um dentro de um artigo que *é* sobre
dengue. Daí os portões: não negado → não qualificado por outra doença
(`11.881.430 casos de DRSAI`) → **na mesma frase** que nomeia dengue. O terceiro é
o que carrega o custo: `No estado de São Paulo, foram 36.791 casos` é descartado
quando a frase não diz "dengue". Direção deliberada — contagem uma ordem de
grandeza errada é pior para o modelo que contagem faltante.

**4. `mil` nem sempre multiplica.** O corpus escreve `36.791 mil casos`, onde os
pontos *são* o separador de milhar e o `mil` final é leitura redundante deles.
Multiplicar dá 36,8 milhões de casos num estado. A regra: pula o multiplicador
quando o número já vem pontuado; `500 mil casos` não tem pontos e multiplica.

**5. O corpus não é monolíngue, e a fatia não é aleatória.** 171 dos 4.569 artigos
(3,7%) são espanhóis — a Agência Brasil publica edição em espanhol — e **61 são de
2016** (Zika e Olimpíadas), 24 de 2002. Um léxico PT-BR subconta exatamente essas
semanas, e a falta cai em ano de epidemia. Por isso `lang_guess` é coluna do corpus
e o braço filtra para `pt`. A heurística foi medida: 92,4% do que ela marca `other`
contém palavra funcional espanhola inequívoca, e só 4 de 4.398 linhas `pt` (0,09%)
têm esse marcador.

**6. Dois bugs de extração, ambos invisíveis nas estatísticas-resumo.** O primeiro
pegava um cabeçalho de 20 caracteres; o segundo pegava a barra "Últimas notícias"
em **1.097 dos 2.628 artigos da era B (42%)** — a barra é mais longa que o artigo e
passava em todo check de tamanho. O segundo só apareceu lendo um artigo extraído. O
que salvou a segunda rodada foi a extração ser revista: o corpus foi **regenerado**,
não remendado, e isso moveu 4.184 → 4.369 artigos pelo filtro de termo de doença
(uma barra de navegação não contém a palavra "dengue"). Detalhe completo em
`src/pipeline/news/README.md` §1.

**7. O viés por UF não é estável no tempo.** RJ lidera SP em menções (1.636 vs 863),
mas isso é inteiramente artefato do começo do corpus: em 2002–2004 é 371 vs 110
(2002 sozinho: 311 vs 60) e **inverte** a partir de 2015 (SP 514 vs RJ 467). Uma
feature por UF deve ser lida contra a própria história antes de ser comparada entre
UFs — é a limitação 2 do README, agora quantificada.

## Custo

Baixo. Sem GPU, sem rotulagem em massa, sem dependência de modelo pré-treinado.
O custo real é o trabalho manual do léxico PT-BR e da amostra anotada. É o braço
que se consegue fechar primeiro.

## Refs a registrar em `articles/references.csv`

`10.1371/journal.pmed.0050151` · `10.1197/jamia.M2544` · `10.1093/bioinformatics/btn534` ·
`10.3201/eid1505.081114` · `10.1371/journal.pone.0199960` · `10.1371/journal.pcbi.1008277` ·
`10.1016/j.jbi.2020.103374` · `10.3402/gha.v9.31620` · `10.2196/36211`

## Pendências / próximo passo

- [x] ~~Escrever o extrator de texto dos HTMLs~~ — feito, com corpus congelado
      (ver medições acima).
- [x] ~~Definir os pesos do `news_severity`~~ — pesos ordinais 1/2/3
      (alerta/surto/epidemia), versionados no YAML.
- [x] ~~Decidir se `news_cases` vale o esforço~~ — respondido pelos dados: 24% dos
      artigos, metade das semanas vazias. Fica no braço, mas com a expectativa
      calibrada, e a extração estruturada é do caminho 04.
- [ ] **Anotar à mão a amostra estratificada (~200–400 artigos)** e medir
      precisão/recall por campo. É a validação que falta e é contribuição do
      artigo: não existe corpus anotado de dengue em PT-BR. Ainda não começou.
- [ ] Rodar o protocolo [00](00-protocolo-comparacao.md) contra 02 e 03.
- [ ] Resolver como tratar contagem acumulada vs. semanal no modelo (medição 2).
- [ ] Considerar re-buscar as 3 páginas de 2008 que vieram sem corpo
      (`check_bodyless_pages` as nomeia); hoje contam para `news_volume` e nada mais.
