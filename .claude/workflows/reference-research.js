// reference-research — pesquisa de artigos de referência de uma família de técnicas.
//
//   Passo 1 (Buscar)     acha os artigos de uma família de técnicas, aplica os
//                        gates, baixa os PDFs para articles/<slug>/
//          (Conferir)    um agente confere que o registro escrito obedece o contrato
//   Passo 2 (Ler)        um agente por artigo lê o PDF e devolve uma ficha
//          (Rankear)     um agente sintetiza as fichas em ranking.md
//   Passo 3 (Relatar)    um agente por EIXO escreve uma seção do capítulo
//          (Sintetizar)  um agente costura as seções em relatorio.md
//          (Revisar)     um agente confere o capítulo escrito contra as fichas
//
// Por que a leitura é uma fase separada: o rankeador precisa das fichas de TODOS
// os artigos ao mesmo tempo para compará-las entre si, e um agente só não cabe
// dezoito PDFs de contexto. "Ler" existe para tornar "Rankear" possível. Vale
// igual para "Relatar": 23 fichas num contexto só dão um parágrafo raso por
// artigo, então o relatório é escrito por eixo e costurado depois.
//
// O RANKING E O RELATÓRIO NÃO RESPONDEM À MESMA PERGUNTA, e é isso que impede o
// segundo de ser uma recompressão do primeiro. O ranking responde "o que eu faço
// NESTE repo, em que ordem, a que custo" — ele dá veredito. O relatório responde
// "o que esta área é": onde os artigos concordam, onde se contradizem, qual a
// trajetória no tempo, onde a evidência é fina. Ele é PROIBIDO de dar veredito e
// custo, e o sintetizador por isso recebe o ranking SEM as colunas de mérito e
// custo: o que ele não tem, ele não pode repetir. Se um dia alguém colar o
// ranking inteiro no prompt do sintetizador, esta separação morre.
//
// O CAPÍTULO É ESCRITO EM PORTUGUÊS CLARO, e isso é regra do desenho, não
// tempero. O leitor é um cientista de área paralela — entende regressão e vetor,
// não entende pooling. Então o português vem primeiro e o termo técnico ao lado,
// entre parênteses: "os vetores ficam todos parecidos entre si (anisotropia)".
// O que NÃO se faz com isso é explicar o domínio: glosar custa cinco palavras,
// ensinar custa um parágrafo e transformaria estado da arte em introdução à área.
// E o número nunca sai da frase — clareza comprada cortando o dado é clareza
// falsa, porque é o dado que torna a afirmação valiosa e conferível.
//
// O CAPÍTULO É UM CAPÍTULO DE REVISÃO DE LITERATURA, e o que ele NÃO PODE
// MOSTRAR é o andaime deste workflow. "Ficha", "eixo", "força" e "funil" são
// língua franca dos prompts — servem para instruir o agente sobre a arquitetura
// daqui — e nada disso é vocabulário do texto entregue. Quando vaza, o capítulo
// lê como processo interno: "o portão mecânico deixou passar 429 fichas, com 12
// acertos únicos no eixo 3" é o defeito, e é por isso que o vocabulário proibido
// é conferido LITERALMENTE na fase Revisar, não deixado ao gosto do escritor.
// A mesma regra vale para a classificação de força da evidência: ela é auditoria
// (campo `forca` de cada claim) e vira PROSA no texto ("há um amplo consenso de
// que...", "um único estudo relata..."), nunca uma etiqueta "Força: consenso"
// impressa no meio do parágrafo. E o andaime estrutural some junto: o cabeçalho
// de cada seção é o TÍTULO do tema, não "Eixo 3 —", e a abertura fala do
// problema de pesquisa, não de quantas fichas e quantos eixos produziram isto.
//
// A CITAÇÃO É (AUTOR, ANO), e as chaves das fichas não aparecem no texto. A
// chave ("reimers2019sbert") é o identificador interno que liga a ficha ao
// search.json, e o leitor não tem esse índice na mão: "(01, 12, 07, 02)" obriga
// a consultar uma tabela externa para saber de quem se fala. Então cada ficha
// carrega `author`/`year` extraídos do PRÓPRIO PDF (nunca do references.csv nem
// do search.json — a leitura tem que ser independente das duas, senão um erro
// de metadados numa delas vira erro de citação no capítulo), e o script do
// workflow deriva `cita` = "Sobrenome, Ano" depois que todas as fichas voltaram.
// A derivação é no SCRIPT e não no agente de leitura por um motivo estrutural:
// as fichas são lidas em paralelo e cada agente vê UM artigo, então nenhum deles
// pode saber que outra ficha da mesma família tem o mesmo autor e o mesmo ano.
// A desambiguação ("Sobrenome, 2020a"/"2020b") só é possível com o conjunto
// completo na mão — e é o script que tem esse conjunto.
//
// A PARTE CONTÁVEL DESSA REGRA É MEDIDA POR SCRIPT, não por agente:
// scripts/checar_estilo_relatorio.py mede comprimento de frase, termo usado
// antes de ser apresentado e densidade de jargão por parágrafo. A fase Revisar
// roda o script e reporta os números dele; o que não é contável (a glosa ficou
// clara para quem lê?) continua sendo julgamento do revisor. Ver ESTILO abaixo,
// que é onde mora a lista de termos — ela é da família, não do script.
//
// Toda afirmação do capítulo carrega uma citação (Autor, Ano) das fichas que a
// sustentam, e a fase Revisar lê o ARQUIVO EM DISCO para conferir. Conferir o
// que o agente diz que escreveu, em vez do que ficou no disco, foi o defeito
// nº 3 da primeira rodada — ver o bloco de lições abaixo.
//
// A entrada é a FAMILY abaixo. Edite ali, ou passe um objeto em `args` — que
// também aceita `gates` (o piso de ano, por exemplo) e `estilo` (a lista de
// jargão da família). Os dois são configuração de RODADA, não parte da família:
// o FAMILY é serializado no prompt do agente de busca, e descrever a família não
// é descrever os gates dela.
//
// CAMINHO DE REUSO. Por padrão a fase Buscar procura de novo. Com
// `args.reuse_search: true`, ela em vez disso CARREGA o articles/<slug>/search.json
// que já existe e vai direto para a leitura e o ranking. Existe porque refazer a
// busca custa ~15 min de API e devolve números diferentes toda vez — as citações
// crescem a cada dia, então o registro nunca é o mesmo duas vezes.
//
// É um interruptor EXPLÍCITO, nunca automático: reusar em silêncio um registro
// velho é indistinguível de ter buscado. Quem lê o resultado precisa poder saber
// qual dos dois aconteceu, e é por isso que o reuso também é logado na saída.
//
// A fase Conferir roda nos dois casos, e vira mais importante no reuso: ela é o
// que garante que o arquivo carregado obedece o contrato antes de alguém confiar
// nele.
//
// --- o que a primeira rodada (2026-10-17) ensinou, e o que mudou -------------
// A rodada funcionou de ponta a ponta (12 agentes, 20 min, 18 PDFs verificados),
// mas errou de um jeito que vale registrar porque a correção está no desenho:
//
// 1. Havia um teto de 10 artigos para ganhar ficha, tomado como um prefixo da
//    lista que o próprio agente de busca ordenou. Os 10 primeiros eram o cânone
//    genérico de embeddings; os 8 cortados eram os quatro artigos sobre notícia
//    × vigilância de doença e três sobre multilíngue/português — justamente o
//    recorte de domínio que o SCOPE pedia. O rankeador avaliou a metade que o
//    projeto já conhece e não viu a que responde à pergunta do projeto.
//    ERRADO: duas curadorias em série, a segunda cega para a lógica da primeira.
//    AGORA: sem teto. Quem a busca selecionou, ganha ficha.
//
// 2. O registro da busca explicava 22 dos 282 candidatos que passaram nas regras
//    objetivas. Os outros 260 sumiram sem motivo escrito — e num desenho sem
//    supervisão humana o registro é o único controle que existe.
//    AGORA: motivo individual para todo mundo que passou nas regras objetivas;
//    contagem por categoria (nome da regra) para quem foi reprovado por regra,
//    porque aí o número da regra já é o motivo.
//
// 3. O arquivo escrito tinha forma diferente da que o contrato pedia — o agente
//    achou uma organização melhor e ninguém notou, porque a verificação conferia
//    o que o agente RESPONDE, não o arquivo que fica no disco.
//    AGORA: a organização do agente virou o contrato oficial (bloco CONTRATO
//    abaixo), e uma fase "Conferir" lê o arquivo e compara.
//
// Ponto 5 da mesma rodada: a família tinha duas metades que não conversam (como
// representar o texto × onde aplicar). A fase Rankear agora separa as duas.
//
// ARMADILHA CONHECIDA, ANTES DE RODAR: o .gitignore deste repo tinha
// `articles/*.pdf`, e `*` não atravessa `/`. Os PDFs que este workflow baixa em
// articles/<slug>/ não estavam ignorados. Corrigido para `articles/**/*.pdf`.

export const meta = {
  name: 'reference-research',
  description: 'Pesquisa artigos de referência de uma família de técnicas, baixa os PDFs para articles/<slug>/, ranqueia as abordagens por usabilidade neste repo e escreve o capítulo de revisão de literatura da área em português claro, com citação (Autor, Ano)',
  whenToUse: 'Antes de implementar um braço novo em src/pipeline/news/: produz o insumo de leitura (articles/<slug>/), o ranking de abordagens e o capítulo de revisão de literatura que o planner consome.',
  phases: [
    { title: 'Buscar', detail: 'OpenAlex + Semantic Scholar, gates, download dos PDFs (ou carrega o registro existente, com reuse_search)' },
    { title: 'Conferir', detail: 'o registro escrito obedece o contrato?' },
    { title: 'Ler', detail: 'um agente por artigo lê o PDF e devolve uma ficha' },
    { title: 'Rankear', detail: 'mérito × custo de adoção neste repo → ranking.md' },
    { title: 'Relatar', detail: 'um agente por eixo escreve uma seção do capítulo, em prosa e com citação (Autor, Ano)' },
    { title: 'Sintetizar', detail: 'costura as seções em relatorio.md, sem veredito e sem custo' },
    { title: 'Revisar', detail: 'o capítulo em disco confere com as fichas? número por número, citação rastreável, sem vocabulário de sistema, mais o script de clareza' },
  ],
}

// --- a entrada: a família de técnicas ---------------------------------------
// É isto que muda de uma rodada para outra. Um objeto passado em `args` ganha
// do DEFAULT_FAMILY campo a campo, então dá para rodar duas famílias sem editar
// o arquivo.
//
// ATENÇÃO ao SCOPE: na primeira rodada ele listava três coisas de naturezas
// diferentes — como representar (encoders, pooling) e onde aplicar (notícia,
// português) — e a busca voltou com dois grupos disjuntos que o rankeador
// comparou entre si como se fossem alternativas. Se você mantiver as duas
// naturezas no mesmo scope, a fase Rankear separa por GRUPO (ver abaixo). Se
// quiser dois rankings limpos, separe em duas famílias e rode duas vezes.
const DEFAULT_FAMILY = {
  slug: 'embeddings',
  label: 'Embeddings densos como features de notícia',
  scope: [
    'encoders de frase/documento usados como feature para série temporal ou regressão',
    'pooling e normalização de embeddings (mean, CLS, whitening, SIF, remoção do primeiro componente)',
    'domínio: texto curto, português ou multilíngue, e notícia/jornalismo',
  ],
  out_of_scope: [
    'embeddings de grafo, de imagem, de usuário, de produto',
    'fine-tuning supervisionado para uma tarefa de classificação específica',
  ],
  queries: [
    'sentence embeddings as features time series forecasting',
    'text embeddings news articles disease surveillance',
    'sentence transformer pooling strategies comparison',
    'multilingual sentence embeddings Portuguese',
  ],
  // Os eixos do relatório (passo 3). Cada um é uma PERGUNTA, não um conjunto de
  // artigos: a mesma ficha pode aparecer em mais de um eixo, e isso é esperado —
  // o mesmo achado visto por duas perguntas é informação, desde que o
  // sintetizador não o apresente como novidade duas vezes.
  //
  // Estes eixos são da família `embeddings` e saíram do que as 23 fichas de fato
  // cobrem. Outra família precisa dos eixos dela: edite aqui, ou passe `eixos`
  // em `args`. Sem eixos declarados o relatório cai num eixo genérico em vez de
  // não rodar — ver EIXO_GENERICO abaixo.
  eixos: [
    {
      slug: 'geometria',
      titulo: 'Como o texto vira vetor: pooling, normalização e a geometria do espaço',
      pergunta: 'Por que a média crua dos vetores é fraca, e o que de fato conserta — pooling melhor, remoção do componente dominante, branqueamento?',
    },
    {
      slug: 'encoders',
      titulo: 'Encoders: o que vem pronto e o que exige treino',
      pergunta: 'Qual o custo real de cada família de encoder, e o que se ganha em troca dele?',
    },
    {
      slug: 'vigilancia',
      titulo: 'Notícia como fonte de vigilância de doença',
      pergunta: 'O que já foi feito no nosso domínio, e o que aquilo mediu de fato?',
    },
    {
      slug: 'lingua',
      titulo: 'Português e multilíngue: o que a área cobre',
      pergunta: 'A distância de idioma foi medida, ou é assumida pequena por simpatia temática?',
    },
  ],
}

// `args` é a entrada da rodada. Duas chaves dele NÃO são da família e por isso
// não viajam dentro do FAMILY: `gates` e `estilo`. O FAMILY é serializado no
// prompt do agente de busca; se os gates fossem junto, o buscador os veria duas
// vezes, uma delas como se fossem escopo da família.
const ARGS = (args && typeof args === 'object' && !Array.isArray(args)) ? args : {}

const FAMILY = { ...DEFAULT_FAMILY, ...ARGS }
delete FAMILY.gates
delete FAMILY.estilo

// Interruptor de reuso — ver o cabeçalho. Explícito de propósito.
const REUSAR = !!ARGS.reuse_search

// --- os eixos do relatório ---------------------------------------------------
// Vêm da família, sobrescrevíveis por `args`. Sem eixos declarados a fase Relatar
// cai num eixo genérico em vez de não rodar: pular em silêncio leria como "o
// relatório não é necessário para esta família", quando o que aconteceu foi
// falta de configuração. Um relatório raso é um defeito visível; um relatório
// ausente sem aviso é um defeito invisível.
const EIXO_GENERICO = {
  slug: 'geral',
  titulo: 'O que esta família de técnicas estabelece',
  pergunta: 'O que os artigos selecionados estabelecem sobre esta família de técnicas, e onde eles se contradizem?',
}
const EIXOS = Array.isArray(FAMILY.eixos) && FAMILY.eixos.length > 0 ? FAMILY.eixos : [EIXO_GENERICO]

// --- o registro do relatório -------------------------------------------------
// Para QUEM o relatório é escrito, e em que língua. Não é enfeite: um relatório
// de estado da arte que só um especialista entende não serve para o que ele
// existe — situar quem vai implementar sem obrigar a ler 23 PDFs.
//
// O alvo NÃO é leigo, e o alvo NÃO é o especialista da área. É um cientista de
// área paralela: sabe o que é uma regressão e o que é um vetor, não sabe o que é
// pooling. Por isso a regra não é EXPLICAR o domínio — isso viraria tutorial e
// afogaria o conteúdo, que é justamente o que não se quer. A regra é escrever em
// português e deixar o termo técnico ao lado, entre parênteses, quando ele for
// de fato necessário:
//
//     "os vetores ficam todos parecidos entre si (anisotropia)"
//
// A partir daí o termo está apresentado e pode ser usado à vontade. É o mesmo
// movimento que uma bula faz, e ele custa cinco palavras.
//
// O NÚMERO NÃO SAI DA FRASE. Encurtar a frase cortando o dado é o jeito errado
// de ficar claro: o número é o que torna a afirmação valiosa e conferível, e a
// fase Revisar confere número contra ficha. A clareza tem que vir do resto da
// frase, não da amputação dela.
//
// A PARTE OBJETIVA DESTA REGRA É MEDIDA POR SCRIPT, não por agente. Agente não
// conta palavra igual duas vezes, e um limite que se move a cada rodada não é um
// limite. Ao script (scripts/checar_estilo_relatorio.py) cabe o que é contável —
// comprimento de frase, termo antes da glosa, densidade de jargão por parágrafo;
// ao revisor cabe o que não é contável — a glosa ficou clara para quem lê?
//
// A LISTA DE TERMOS É DA FAMÍLIA, e por isso mora aqui e não no script: `pooling`
// é jargão para nós e não seria para uma família de, digamos, epidemiologia.
// Outra família precisa da lista dela. Os LIMITES, ao contrário, ficam no script,
// porque são sobre prosa em português e valem para qualquer tema.
const DEFAULT_ESTILO = {
  leitor: 'cientista de área paralela — capaz, com noções básicas, NÃO especialista desta área e NÃO leigo',
  regra: 'português claro primeiro, termo técnico entre parênteses ao lado; apresentado uma vez, o termo pode ser usado à vontade',
  // O verbo tem que ser este: apresentar o termo, não traduzir o conceito. Se a
  // glosa virar uma explicação de duas linhas, a seção deixa de ser estado da
  // arte e passa a ser introdução.
  script: 'scripts/checar_estilo_relatorio.py',
  // Termos cuja PRIMEIRA aparição no corpo tem que estar dentro de parênteses.
  // São RADICAIS de propósito ("branqueament" pega branqueamento e branqueado),
  // então escolha radicais que não se sobreponham — dois radicais que casam com
  // a mesma palavra contariam a mesma ocorrência duas vezes na densidade.
  //
  // A LISTA CRESCE POR RECORRÊNCIA, não por observação. Na primeira rodada com
  // esta regra o revisor achou seis frases opacas que o script não vê, porque a
  // lista não tem MEAN, MAX, [CLS], concat, hier/n-gram — os nomes das variantes
  // de pooling. A tentação é acrescentar os seis na lista. Não: lista que cresce
  // a cada saída é lista que ninguém mantém, e o revisor pegou os seis sozinho,
  // que é para isso que ele existe. A regra é a mesma dos gates — só entra na
  // lista o termo que aparecer em DUAS rodadas seguidas. Aí ele deixou de ser
  // surpresa e passou a ser parte previsível do vocabulário da família.
  //
  // "atenção" NÃO está na lista embora o relatório a use no sentido técnico
  // (attention): em português é palavra comum ("chamar a atenção") e o script
  // acusaria toda ocorrência banal. Um alarme falso recorrente é o jeito mais
  // rápido de treinar quem lê a ignorar a saída — melhor não medir do que medir
  // errado.
  termos: [
    'pooling', 'embedding', 'encoder', 'branqueament', 'whitening', 'anisotrop',
    'componente principal', 'transdutiv', 'cosseno', 'transformer', 'fine-tun',
    'token', 'NLI', 'word2vec', 'bag-of-words', 'saco de palavras', 'destila',
    'retrieval', 'NRMSE', 'SVD', 'dimensionalidade', 'stopword', 'pré-trein', 'LDA',
  ],
}

// A lista acima é da família `embeddings`, e por isso é substituível pela rodada:
// `args.estilo.termos` troca a lista inteira. Os LIMITES continuam no script,
// porque são sobre prosa em português e valem para qualquer tema.
const ESTILO = ARGS.estilo ? { ...DEFAULT_ESTILO, ...ARGS.estilo } : DEFAULT_ESTILO

// A linha de comando que o revisor roda. As aspas simples em volta de cada termo
// são necessárias para os que têm espaço ("componente principal"). Nenhum termo
// da lista contém aspas simples.
const TERMOS_FLAG = ESTILO.termos.map((t) => `--termo '${t}'`).join(' ')

// --- os gates ---------------------------------------------------------------
// Congelados ANTES da busca, como o CONTRACT do gt-alignment.js. Um gate que se
// ajusta depois de ver o resultado não é um gate: ele só confirma o que o
// agente já achou. O agente recebe estes números e não os move.
//
// PONTO CEGO CONHECIDO, medido na primeira rodada: o registro do SBERT (o paper
// do EMNLP, dos mais citados da área) volta com `source: null` no OpenAlex — é
// buraco de metadados, não venue fraca. Com o gate como está, um artigo assim é
// reprovado por FALTA DE DADO. Por isso o gate de venue aceita duas saídas:
// h-index suficiente OU nome na allow-list. Se aparecerem mais casos de
// `source: null` em venue boa, o certo é o gate distinguir "venue fraca" de
// "venue desconhecida" e mandar a segunda para a busca na web, não para o lixo.
const DEFAULT_GATES = {
  // Não há Date.now() em workflow (quebraria o resume). Atualize a cada ano.
  as_of_year: 2026,
  min_year: 2015,
  citations: { mature_age_years: 2, mature_min: 10, recent_min: 3 },
  venue: {
    min_h_index: 30,
    allow_any_of: [
      'ACL', 'EMNLP', 'NAACL', 'EACL', 'COLING', 'TACL',
      'NeurIPS', 'ICLR', 'ICML', 'AAAI', 'JMLR',
    ],
  },
  require_pdf: true,
}

// Os gates são congelados no LANÇAMENTO, e é por isso que eles são substituíveis
// por `args` e não ajustáveis depois: quem troca o piso de ano é quem lança o
// workflow, antes de ver qualquer resultado. O agente de busca recebe os números
// e não os move — um gate que se move depois de ver o resultado não é um gate.
// O merge é raso: `{ min_year: 2005 }` troca o piso e deixa o resto como está.
const GATES = ARGS.gates ? { ...DEFAULT_GATES, ...ARGS.gates } : DEFAULT_GATES

// --- o nosso contexto -------------------------------------------------------
// O que o rankeador precisa saber para dizer "isto roda aqui" com honestidade.
// Números do AGENTS.md §Checkout State; reconfira antes de confiar neles.
const CONTEXT = {
  corpus: '4.369 artigos da Agência Brasil (query dengue), texto PT-BR, 965 semanas, 28 locations (BR + 27 UFs)',
  machine: 'CPU only. Sem GPU.',
  installed_extras: [
    'embeddings — torch + transformers, ~800 MB',
    'topics — tomotopy',
  ],
  already_built: 'braços 01 (léxico), 02 (6 configurações de embedding), 03 (DMR/tomotopy). Ver src/pipeline/news/README.md',
  cost_of_a_new_dependency: 'alta: os extras estão fixados em pyproject.toml e o transform precisa rodar em CPU em minutos, não horas',
}

// --- O CONTRATO do registro da busca ----------------------------------------
// Esta é a forma oficial de articles/<slug>/search.json. Ela veio do arquivo que
// o agente escreveu na primeira rodada — a organização dele é melhor que a que
// eu havia pedido, porque separa três coisas que são de fato diferentes: o que
// foi achado, o que passou nas regras objetivas, e o que foi escolhido por
// julgamento. A fase "Conferir" lê o arquivo e compara contra isto.
//
//   {
//     family:      { slug, label },
//     as_of_year:  int,
//     generated:   "YYYY-MM-DD",
//     gates:       <cópia literal dos GATES acima>,
//     citations_per_year_formula: "citada assim, para o número ser reconferível",
//     sources:     [ { name, url_base, role } ],   // os bancos consultados
//     notes:       [ "o que surpreendeu; lacunas declaradas" ],
//     counts: {
//       total_unique_hits:       int,   // candidatos distintos, somando as queries
//       mechanical_gate_passers: int,   // passaram em TODAS as regras objetivas
//       selected_with_pdf:       int,   // ganharam PDF baixado e verificado
//     },
//     queries:     [ { source, query, url, hits } ],
//     selected: [ {
//       key, file, title, year, venue, venue_h_index,
//       doi, citations, citations_per_year, pdf, decision: "selected",
//     } ],
//     rejected_by_gate: { <nome da regra>: int },   // CONTAGEM por regra
//     considered_not_selected: [ { title, gate: "relevance", detail } ],
//   }
//
// INVARIANTES — é isto que a fase Conferir checa, e é isto que garante que o
// funil não tem fundo (o defeito nº 2 da primeira rodada):
//
//   counts.mechanical_gate_passers == selected.length + considered_not_selected.length
//   counts.selected_with_pdf       == selected.length
//   sum(rejected_by_gate.values())  == total_unique_hits - mechanical_gate_passers
//   selected[*].file existe em articles/<slug>/ e é PDF de verdade
//
// `file` é o caminho a partir da RAIZ do repositório (articles/<slug>/NN_....pdf),
// para o leitor de cada artigo não ter que adivinhar onde o PDF está. No
// references.csv, a coluna File Attachments leva só o nome do arquivo.
//
// Regra de granularidade, decidida depois da primeira rodada:
//   - quem passou nas regras objetivas e NÃO foi selecionado → linha individual
//     com o motivo escrito (considered_not_selected). É o julgamento, e é o que
//     precisa ser auditável.
//   - quem reprovou numa regra objetiva → só a contagem por regra
//     (rejected_by_gate). O número da regra já é o motivo.

// --- contratos de saída -----------------------------------------------------
const DISCOVERY_SCHEMA = {
  type: 'object',
  properties: {
    family: { type: 'string' },
    counts: {
      type: 'object',
      properties: {
        total_unique_hits: { type: 'integer' },
        mechanical_gate_passers: { type: 'integer' },
        selected_with_pdf: { type: 'integer' },
      },
      required: ['total_unique_hits', 'mechanical_gate_passers', 'selected_with_pdf'],
    },
    rejected_by_gate: {
      type: 'object',
      additionalProperties: { type: 'integer' },
    },
    considered_not_selected: { type: 'integer' },
    queries_run: { type: 'integer' },
    articles: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          key: { type: 'string' },
          file: { type: 'string' },
          title: { type: 'string' },
          authors: { type: 'string' },
          year: { type: 'integer' },
          venue: { type: 'string' },
          venue_h_index: { type: 'integer' },
          doi: { type: 'string' },
          citations: { type: 'integer' },
          citations_per_year: { type: 'number' },
        },
        required: [
          'key', 'file', 'title', 'authors', 'year', 'venue', 'doi',
          'citations', 'citations_per_year',
        ],
      },
    },
    outputs: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
  },
  required: [
    'family', 'counts', 'rejected_by_gate', 'considered_not_selected',
    'queries_run', 'articles', 'outputs', 'summary',
  ],
}

const VERIFY_SCHEMA = {
  type: 'object',
  properties: {
    conforms: { type: 'boolean' },
    checks: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          name: { type: 'string' },
          passed: { type: 'boolean' },
          detail: { type: 'string' },
        },
        required: ['name', 'passed', 'detail'],
      },
    },
    divergencias: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
  },
  required: ['conforms', 'checks', 'divergencias', 'summary'],
}

const CARD_SCHEMA = {
  type: 'object',
  properties: {
    key: { type: 'string' },
    grupo: { type: 'string', enum: ['representacao', 'aplicacao'] },
    // author/year existem para o relatório poder citar (Autor, Ano) em vez da
    // chave da ficha. São extraídos do PRÓPRIO PDF, não do references.csv nem
    // do search.json: a leitura tem que ser independente das duas, senão um
    // erro de metadados numa delas vira erro de citação no relatório.
    author: { type: 'string' },
    year: { type: 'integer' },
    read: { type: 'string' },
    technique: { type: 'string' },
    representation: { type: 'string' },
    evidence: { type: 'string' },
    needs: { type: 'string' },
    cost_here: { type: 'string' },
    transferable: { type: 'string' },
    red_flags: { type: 'array', items: { type: 'string' } },
  },
  required: [
    'key', 'grupo', 'author', 'year', 'read', 'technique', 'representation',
    'evidence', 'needs', 'cost_here', 'transferable', 'red_flags',
  ],
}

const RANKING_SCHEMA = {
  type: 'object',
  properties: {
    ranked: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          rank: { type: 'integer' },
          grupo: { type: 'string', enum: ['representacao', 'aplicacao'] },
          key: { type: 'string' },
          approach: { type: 'string' },
          merit: { type: 'string' },
          adoption_cost: { type: 'string' },
          verdict: { type: 'string', enum: ['tentar agora', 'tentar depois', 'descartar'] },
          why: { type: 'string' },
        },
        required: ['rank', 'grupo', 'key', 'approach', 'merit', 'adoption_cost', 'verdict', 'why'],
      },
    },
    cross_cutting: { type: 'array', items: { type: 'string' } },
    first_move: { type: 'string' },
    open_questions: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
  },
  required: ['ranked', 'cross_cutting', 'first_move', 'open_questions', 'summary'],
}

// --- contratos de saída do relatório (passo 3) ------------------------------
// `claims` e `lacunas` são ESTRUTURA DE AUDITORIA, não texto do relatório. A
// partir da terceira rodada, o texto que vai para o arquivo é `narrativa`, em
// prosa acadêmica corrida. O motivo é a diferença entre listar e sintetizar: um
// array de afirmações independentes, impresso como está, empilha achados sem
// nunca dizer o que eles têm em comum nem onde se contradizem — que é o
// trabalho de uma revisão de literatura e o que ninguém faz por você depois.
//
// A separação também é o que impede a redundância que a rodada anterior tinha:
// o mesmo achado aparecia como bullet e, em seguida, reescrito na seção
// "Consenso do eixo". Com `consenso`/`contradicoes` removidos do schema, não
// existe mais o segundo lugar onde a mesma coisa pode ser dita de novo.
const SECTION_SCHEMA = {
  type: 'object',
  properties: {
    eixo: { type: 'string' },
    pergunta: { type: 'string' },
    claims: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          claim: { type: 'string' },
          from: {
            type: 'array',
            items: { type: 'string' },
            description: 'chaves das fichas que sustentam a afirmação; vazio só se a afirmação for sobre a ausência de evidência',
          },
          forca: { type: 'string', enum: ['consenso', 'parcial', 'contradito', 'isolado'] },
        },
        required: ['claim', 'from', 'forca'],
      },
      description: 'AUDITORIA INTERNA. Nunca é impressa no relatório. É o que permite ao revisor conferir se a prosa de `narrativa` reflete a força real de cada achado.',
    },
    narrativa: {
      type: 'string',
      description: 'O TEXTO da seção — prosa acadêmica corrida, em parágrafos, agrupando achados convergentes e contrastando os divergentes, com citação (Autor, Ano). É este campo, e não `claims`, que vai para o relatório.',
    },
    // `lacunas` é estruturada como `claims`, e não como string solta, por um
    // motivo que só apareceu na segunda rodada: o sintetizador NÃO tem as
    // fichas, então quando a lacuna vinha como texto puro ele tinha que
    // INVENTAR quais fichas a sustentavam — e inventou errado duas vezes
    // (pôs a ficha 20 numa lista de fichas que não reportam custo, quando ela
    // reporta; e escreveu o intervalo "(01-13)" incluindo uma ficha que não
    // mede similaridade). Chave que o agente que leu o PDF não deu é chave que
    // ninguém rio abaixo tem como conferir.
    lacunas: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          lacuna: { type: 'string' },
          from: {
            type: 'array',
            items: { type: 'string' },
            description: 'chaves das fichas que mostram a lacuna (tipicamente as que NÃO medem aquilo)',
          },
        },
        required: ['lacuna', 'from'],
      },
    },
    summary: { type: 'string' },
  },
  required: ['eixo', 'pergunta', 'claims', 'narrativa', 'lacunas', 'summary'],
}

const REPORT_SCHEMA = {
  type: 'object',
  properties: {
    arquivo: { type: 'string' },
    secoes: { type: 'array', items: { type: 'string' } },
    claims_no_relatorio: { type: 'integer' },
    claims_sem_fonte: { type: 'integer' },
    fichas_citadas: { type: 'array', items: { type: 'string' } },
    fichas_nunca_citadas: {
      type: 'array',
      items: { type: 'string' },
      description: 'fichas que o relatório não citou nenhuma vez — a lista que denuncia o artigo lido e esquecido',
    },
    summary: { type: 'string' },
  },
  required: [
    'arquivo', 'secoes', 'claims_no_relatorio', 'claims_sem_fonte',
    'fichas_citadas', 'fichas_nunca_citadas', 'summary',
  ],
}

const REVIEW_SCHEMA = {
  type: 'object',
  properties: {
    conforme: { type: 'boolean' },
    claims_conferidas: { type: 'integer' },
    claims_orfas: {
      type: 'array',
      items: {
        type: 'object',
        properties: { claim: { type: 'string' }, onde: { type: 'string' } },
        required: ['claim', 'onde'],
      },
    },
    numeros_divergentes: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          afirmacao: { type: 'string' },
          citado: { type: 'string' },
          na_ficha: { type: 'string' },
          ficha: { type: 'string' },
        },
        required: ['afirmacao', 'citado', 'na_ficha', 'ficha'],
      },
    },
    citacoes_sem_ficha: {
      type: 'array',
      items: {
        type: 'object',
        properties: { citacao: { type: 'string' }, onde: { type: 'string' } },
        required: ['citacao', 'onde'],
      },
      description: 'citações (Autor, Ano) do relatório que não casam com o author+year/cita de NENHUMA ficha — o equivalente, no desenho antigo, à chave inventada',
    },
    autores_inventados: {
      type: 'array',
      items: {
        type: 'object',
        properties: { citacao: { type: 'string' }, ficha: { type: 'string' }, onde: { type: 'string' } },
        required: ['citacao', 'ficha', 'onde'],
      },
      description: 'o relatório nomeia um autor para uma ficha cujo author é "não identificado" — nome inventado, mesma gravidade da sigla inventada',
    },
    vocabulario_proibido: {
      type: 'array',
      items: { type: 'string' },
      description: 'ocorrências literais de "ficha(s)", "portão mecânico", "acertos"/"acertos únicos", cabeçalho "Eixo N —", ou "Força: <consenso|parcial|contradito|isolado>" no arquivo; vazio é o esperado',
    },
    forca_nao_refletida: {
      type: 'array',
      items: {
        type: 'object',
        properties: { claim: { type: 'string' }, forca: { type: 'string' }, onde: { type: 'string' } },
        required: ['claim', 'forca', 'onde'],
      },
      description: 'claim de auditoria com forca=parcial/isolado/contradito cuja prosa correspondente não carrega ressalva nem contraste — lida como se fosse consenso',
    },
    veredictos_no_relatorio: {
      type: 'array',
      items: { type: 'string' },
      description: 'frases que dão veredito, recomendação ou custo — o relatório foi proibido de fazer isso; vazio é o esperado',
    },
    divergencias: { type: 'array', items: { type: 'string' } },
    // O veredito de clareza, separado em duas metades que não se misturam: o que
    // o script mediu (contável, igual toda rodada) e o que só um leitor julga.
    // Misturar as duas faria a parte objetiva herdar a variância da subjetiva.
    estilo: {
      type: 'object',
      properties: {
        script_rodou: {
          type: 'boolean',
          description: 'true só se o script rodou e você leu a saída dele; false significa que a checagem objetiva NÃO aconteceu',
        },
        frases_longas: { type: 'integer', description: 'ERROs do script: frases acima do limite' },
        termos_sem_glosa: { type: 'integer', description: 'ERROs do script: termos usados antes de serem apresentados' },
        paragrafos_densos: { type: 'integer', description: 'ERROs do script: parágrafos acima do limite de densidade' },
        prosa_opaca: {
          type: 'array',
          items: { type: 'string' },
          description: 'frases que o script NÃO pega (curtas, sem termo da lista) mas que um leitor de área paralela não entende — a metade que só você pode julgar',
        },
        glossas_vazias: {
          type: 'array',
          items: { type: 'string' },
          description: 'termos que estão entre parênteses, e portanto passam no script, mas cuja glosa não apresenta nada ("(pooling)" depois de "pooling" não explica o que é)',
        },
      },
      required: ['script_rodou', 'frases_longas', 'termos_sem_glosa', 'paragrafos_densos', 'prosa_opaca', 'glossas_vazias'],
    },
    summary: { type: 'string' },
  },
  required: [
    'conforme', 'claims_conferidas', 'claims_orfas', 'numeros_divergentes',
    'citacoes_sem_ficha', 'autores_inventados', 'vocabulario_proibido',
    'forca_nao_refletida', 'veredictos_no_relatorio', 'divergencias', 'estilo', 'summary',
  ],
}

// --- passo 1: buscar --------------------------------------------------------
const BUSCAR = `Você está no repositório arbovirus-surveillance-data (a raiz é o seu diretório de trabalho).
Sua tarefa: achar os artigos de referência de UMA família de técnicas e baixá-los.

A família (esta é a entrada; não a reinterprete, mas se algo estiver ambíguo diga na summary):
${JSON.stringify(FAMILY, null, 2)}

Os gates, congelados antes da busca. Você NÃO os ajusta — se um artigo não passa, ele não passa:
${JSON.stringify(GATES, null, 2)}

Regra dos gates, explícita:
- ano >= GATES.min_year
- citações: se (GATES.as_of_year - ano) >= GATES.citations.mature_age_years, exige >= mature_min;
  senão exige >= recent_min
- venue: h_index do source >= venue.min_h_index, OU o nome do source casa (case-insensitive, por
  substring) com algum de venue.allow_any_of
- PDF: só entra em selected[] quem tiver um PDF baixado e VERIFICADO (ver abaixo)

Fontes, nesta ordem:

1. OpenAlex — a espinha dorsal. Sem chave, JSON estável, e é a única que dá o h_index do venue e o
   melhor link de OA no mesmo payload.
     https://api.openalex.org/works?search=<query>&filter=from_publication_date:YYYY-01-01,is_oa:true&per-page=50&mailto=arboili@example.org
   Campos úteis: display_name, publication_year, cited_by_count, doi, authorships,
   primary_location.source.display_name, primary_location.source.summary_stats.h_index,
   open_access.is_oa, best_oa_location.pdf_url
   Se o source vier null (buraco de metadados, acontece com registros do ACL), resolva o h_index
   pelo endpoint /sources antes de reprovar o artigo — não confunda venue desconhecida com venue fraca.

2. Semantic Scholar — para conferir contagem de citações e achar PDF OA que o OpenAlex não deu.
     https://api.semanticscholar.org/graph/v1/paper/search?query=<query>&fields=title,year,citationCount,venue,externalIds,openAccessPdf
   Sem chave ele limita a ~1 req/s e devolve 429 com frequência: espaçe as chamadas.

3. Web (WebSearch/WebFetch) — SÓ para lacunas: quando um artigo que deveria estar na lista não tem PDF
   OA em nenhuma das duas, ou quando a família tem um preprint/relatório técnico que nenhuma indexa.
   Registre nas notes o que a web achou que as APIs não acharam.

Use curl via Bash para as APIs, e processe o JSON com python3 -I -c ou jq.

CUIDADO (macOS, proxy corporativo): este repo documenta que a máquina fica atrás de um proxy que
inspeciona TLS, e o Python recusa o certificado. Se o curl falhar com erro de certificado, tente
\`curl --cacert logs/macos-ca-bundle.pem\` (o arquivo existe se scripts/resume_gt_related.sh já rodou).
Diga nas notes se precisou disso.

Baixe os PDFs para articles/${FAMILY.slug}/, no padrão de nome que já existe na pasta articles/:
  NN_primeiroautor_ano_slugcurto.pdf     (ex.: 01_zhu_2025_spatiotemporal_dengue_climate_factors.pdf)
NN é a ordem que você decidir; use dois dígitos.
Antes de baixar, OLHE o que já existe em articles/${FAMILY.slug}/: se um artigo selecionado já tem PDF
lá, reaproveite o arquivo em vez de baixar de novo (confira com \`file\` que ele é PDF de verdade).
Pegue o PDF de best_oa_location.pdf_url. Se vier HTML (uma landing page), siga os redirects e procure o
link real do PDF. VERIFIQUE cada download: \`file <caminho>\` tem que dizer "PDF document". Um HTML salvo
com extensão .pdf não conta, e é o erro mais comum desta fase. Se não conseguir um PDF real, o artigo
NÃO entra em selected[] e conta em rejected_by_gate sob a chave "pdf".

Escreva em articles/${FAMILY.slug}/:

- search.json — siga EXATAMENTE a forma abaixo. Ela já foi acordada com o dono do repo e uma fase
  seguinte confere o arquivo contra ela; divergir deixa de ser criatividade e vira defeito.

  {
    family: { slug, label },
    as_of_year: <número>,
    generated: "<YYYY-MM-DD>",
    gates: <cópia literal dos gates acima>,
    citations_per_year_formula: "<a fórmula, escrita>",
    sources: [ { name, url_base, role } ],
    notes: [ "<o que surpreendeu, o que ficou ambíguo>" ],
    counts: {
      total_unique_hits:       <candidatos distintos, somando as queries>,
      mechanical_gate_passers: <passaram em TODAS as regras objetivas>,
      selected_with_pdf:       <ganharam PDF baixado e verificado>
    },
    queries: [ { source, query, url, hits } ],
    selected: [ { key, file, title, year, venue, venue_h_index, doi,
                  citations, citations_per_year, pdf, decision: "selected" } ],
    rejected_by_gate: { "<nome da regra>": <contagem> },
    considered_not_selected: [ { title, gate: "relevance", detail } ]
  }

  REGRA DE GRANULARIDADE — é o ponto mais importante deste arquivo:
  * Todo candidato que passou nas regras objetivas e NÃO foi selecionado ganha uma linha própria
    em considered_not_selected, com o motivo escrito em detail. Nenhum pode faltar. Se você julgou
    irrelevante, diga POR QUE em uma frase. "Fora do escopo" não basta; diga que escopo.
  * Quem reprovou numa regra objetiva entra só como contagem em rejected_by_gate, sob o nome da
    regra que o reprovou ("year", "citations", "venue", "pdf"). Se reprovou em mais de uma, use a
    primeira na ordem em que as regras estão declaradas acima.
  * Os três números de counts têm que fechar com as listas:
      mechanical_gate_passers == len(selected) + len(considered_not_selected)
      selected_with_pdf       == len(selected)
      soma dos valores de rejected_by_gate == total_unique_hits - mechanical_gate_passers
    Se não fecharem, você errou a contagem — não arredonde para fazer fechar.

  O campo \`file\` é o caminho a partir da raiz do repositório: "articles/${FAMILY.slug}/NN_....pdf".

- references.csv — o índice das referências, no formato do articles/references.csv que já existe
  (export do Zotero). Use um SUBCONJUNTO dos mesmos nomes de coluna, nesta ordem exata:
  Key,Item Type,Publication Year,Author,Title,Publication Title,DOI,Url,Abstract Note,Date Added,Extra,Manual Tags,File Attachments,Library Catalog
  Não invente nomes de coluna novos. Em File Attachments, só o NOME do arquivo (sem pasta).

- README.md — o índice humano, no padrão do articles/README.md: uma tabela com arquivo, citação, e uma
  coluna dizendo o que aquele artigo faz aqui. É a primeira coisa que um humano abre depois da rodada.

Regras:
- Reporte o que você MEDIU, não o que você esperava. Se um número surpreender, reporte de qualquer forma
  e diga na summary.
- Não invente DOI, citação, venue ou contagem de citações. Se um campo não veio da API, deixe vazio e
  diga nas notes.
- Não edite nenhum arquivo fora de articles/${FAMILY.slug}/.
- Se menos de 5 artigos passarem nos gates, diga na summary e NÃO relaxe os gates para compensar. Um
  resultado pequeno é uma resposta; um gate afrouxado é um resultado que não vale nada.
- No retorno estruturado, articles[] são só os selecionados (o arquivo tem a lista completa).`

// --- passo 1 alternativo: carregar um registro que já existe -----------------
// Só roda com args.reuse_search. Não procura nada: lê o search.json que está no
// disco e devolve no MESMO formato que o agente de busca devolveria, para o
// resto do workflow não precisar saber de qual dos dois veio.
const CARREGAR = `Você NÃO vai procurar nada. Não chame nenhuma API, não baixe nada, não escreva nada.
Sua tarefa é carregar um registro de busca que já existe e devolvê-lo no formato pedido.

Leia articles/${FAMILY.slug}/search.json com python3 -I (json.load).

- Se o arquivo não existir ou não for JSON válido: retorne counts zerados, articles vazio, e escreva
  na summary exatamente isso. Não tente consertar, não procure na web, não invente.
- Se existir: leia as chaves counts, rejected_by_gate, considered_not_selected, queries e selected.

Devolva:
- counts: copie os três números como estão no arquivo
- rejected_by_gate: copie o objeto como está
- considered_not_selected: o NÚMERO de itens da lista (não a lista)
- queries_run: o número de itens em queries
- articles: um item por entrada de selected[], com os campos key, file, title, authors, year, venue,
  venue_h_index, doi, citations, citations_per_year.
    * \`file\` — copie EXATAMENTE como está (é o caminho a partir da raiz do repo). Não normalize,
      não troque por nome de arquivo.
    * \`authors\` — o registro de busca não guarda autores. Pegue-os de articles/${FAMILY.slug}/references.csv,
      casando pela coluna Title. Se não achar, deixe string vazia.
- outputs: os caminhos dos arquivos que você leu
- summary: diga que isto é um REUSO de um registro existente, a data em \`generated\` do arquivo, e
  qualquer coisa que você tenha notado ao ler (contagens que não fecham, campo faltando).

Reporte o que está NO ARQUIVO. Não melhore, não complete, não corrija a contagem. Se algo estiver
errado ou faltando, isso é exatamente o que a summary deve dizer — a fase seguinte confere o arquivo
contra o contrato, e esconder um defeito aqui só faz o defeito chegar mais longe.`

// --- passo 1b: conferir -----------------------------------------------------
const CONFERIR = `Você confere UM arquivo contra um contrato declarado. Não conserte nada — só reporte.

O arquivo: articles/${FAMILY.slug}/search.json
O contrato: as regras abaixo, que estão escritas em .claude/workflows/reference-research.js no bloco
"O CONTRATO do registro da busca". Leia o arquivo com python3 -I (json.load) e compare.

Cheque, MEDINDO VOCÊ MESMO (não confie na descrição de ninguém sobre o arquivo):

1. FORMA — o arquivo tem as chaves de topo: family, as_of_year, generated, gates,
   citations_per_year_formula, sources, notes, counts, queries, selected, rejected_by_gate,
   considered_not_selected. Lista qualquer uma que falte e qualquer extra inesperada.

2. INVARIANTE 1 — counts.mechanical_gate_passers == len(selected) + len(considered_not_selected).
   Esta é a que garante que o funil não tem fundo: se falhar, houve candidato que passou nas regras
   e não foi explicado em lugar nenhum.

3. INVARIANTE 2 — counts.selected_with_pdf == len(selected).

4. INVARIANTE 3 — a soma dos valores de rejected_by_gate == total_unique_hits - mechanical_gate_passers.

5. INVARIANTE 4 — para CADA item de selected, o caminho em \`file\` (relativo à raiz do repo) existe
   em disco e o comando \`file <caminho>\` diz "PDF document". Reporte o nome de todo arquivo que
   falhar. É o erro clássico desta fase: HTML salvo com extensão .pdf.

6. GRANULARIDADE — todo item de considered_not_selected tem um \`detail\` não vazio e que de fato
   explica o motivo (não apenas "fora do escopo" sem dizer de que escopo). Conte quantos têm detail
   vazio ou genérico.

7. coerência dos números em counts com o que as listas de fato contêm.

Regras de decisão:
- conforms = false se QUALQUER check falhar. Se você não conseguir verificar algo, isso é uma falha
  (dúvida → não conforme); nunca presuma que passou.
- divergencias: uma frase por divergência encontrada, com os números medidos.
- Se o arquivo não existir ou não for JSON válido, conforms = false e diga isso — é o caso mais grave.
- Você NÃO corrige o arquivo. Quem corrige é o agente de busca, numa próxima rodada.`

// --- passo 2a: ler ----------------------------------------------------------
const fichaPrompt = (a) => `Você é o leitor de UM artigo de referência. Sua saída é uma ficha estruturada
sobre ele — não um resumo do artigo.

Leia ${a.file} (é um PDF: use a ferramenta Read com o parâmetro \`pages\`, ou pdftotext se preferir).

O contexto onde a técnica seria usada:
${JSON.stringify(CONTEXT, null, 2)}

O GRUPO: classifique este artigo em um dos dois, e seja honesto — a primeira rodada errou justamente
por misturar os dois e comparar um com o outro.
- "representacao" — o artigo trata de COMO transformar texto em número: encoder, pooling, normalização,
  geometria do espaço, dimensionalidade. Vale independente do domínio.
- "aplicacao" — o artigo trata de ONDE usar embeddings: notícia, vigilância de doença, português,
  texto curto. Vale pelo que ele mediu no domínio, não pela técnica.

O que importa na ficha, em ordem:

0. IDENTIFICAÇÃO — \`key\`, \`author\` e \`year\`. É o que permite o relatório citar (Autor, Ano) em vez
   da chave da ficha, e é o que amarra a sua ficha ao resto do registro.
   - \`key\`: copie EXATAMENTE esta string, sem inventar numeração nova e sem trocar por um índice
     sequencial: "${a.key}". Uma rodada anterior renumerou as fichas de 1 a 23 por conta própria, e o
     relatório saiu citando "(01, 12, 07, 02)" — chave que não existe em lugar nenhum do registro e
     que ninguém consegue conferir. A chave é a identidade da ficha, não um rótulo de leitura.
   - \`author\` / \`year\`: extraia do PRÓPRIO PDF — da capa, do cabeçalho ou da folha de rosto. NÃO
     consulte o references.csv nem o search.json para isto: a leitura é independente dos dois, e é
     justamente essa independência que faz a conferência depois valer.
     * Formato de citação acadêmica padrão, pela contagem de autores:
       1 autor  → "Sobrenome"
       2 autores → "Sobrenome1 & Sobrenome2"
       3 ou mais → "Sobrenome1 et al."
     * \`year\` é o ano de publicação, inteiro.
     * Se a capa não deixar claro quem é o primeiro autor (scan ruim, preprint sem metadados), escreva
       \`author: "não identificado"\` e \`year: 0\`. É o mesmo espírito do "não reportado" que você já usa
       para custo: não adivinhe, não deduza de um DOI, não copie o ano de uma citação dentro do texto.
       Uma citação inventada é pior que uma citação ausente, porque a ausente o leitor percebe.

1. technique / representation — o que a técnica é e como o texto vira número, em linguagem que alguém que
   não leu o artigo entenda. Não copie o abstract. Se for artigo de aplicação, diga qual técnica ele usa
   e o que ele mediu no domínio.

2. evidence — que evidência os autores dão de que funciona, e CONTRA QUE BASELINE. "Melhora 2 pontos de
   F1 sobre mean-pooling de BERTimbau" vale; "supera os baselines" não vale. Se o artigo não compara com
   nada, diga isso — é uma informação.

3. needs / cost_here — o que ela exige para rodar (modelo, tamanho, GPU, língua, dados rotulados) e quanto
   custaria rodar sobre o NOSSO corpus em CPU. Dê número quando o artigo der; diga "não reportado" quando
   não der. Não estime para baixo: se você não sabe, é "não reportado", não "barato".

4. transferable — o que transfere para o nosso caso e o que não. Preste atenção na distância de domínio:
   um resultado bom em tweet em inglês pode não transferir para notícia em português. Diga onde a distância
   é grande, em vez de assumir que é pequena.

5. red_flags — o que faria você desconfiar: benchmark só em inglês, ganho dentro do ruído, avaliação só
   intrínseca, baseline fraco, correção medida em um único modelo.

Em \`read\`, diga o que você de fato leu (seções, páginas, tabelas). Não leia só o abstract: limitações e
resultados costumam estar em outro lugar, e é lá que mora o custo real.

Reporte o que o artigo DIZ. Não elogie e não recomende — quem ranqueia é outro agente.`

// --- passo 2b: ranquear -----------------------------------------------------
const rankearPrompt = (cards) => `Você é o ranqueador. Recebeu as fichas de ${cards.length} artigos de
referência sobre UMA família de técnicas, lidas por agentes que abriram os PDFs. Sua tarefa: ranquear as
ABORDAGENS (não os artigos) por quão usáveis elas são NESTE repo.

O contexto — é ele que define "usável":
${JSON.stringify(CONTEXT, null, 2)}

As fichas:
${JSON.stringify(cards, null, 2)}

Antes de ranquear, leia no repo o que já existe, para o custo de adoção ser relativo ao que está de pé e
não ao vácuo:
- src/pipeline/news/README.md — os braços 01/02/03 e o que já foi medido
- notes/00-protocolo-comparacao.md — o protocolo que fixa o terreno comum da comparação
- pyproject.toml — os extras e o que já é dependência

SEPARE OS DOIS GRUPOS. As fichas vêm marcadas com \`grupo\`, e a primeira rodada deste workflow errou
por tratar as duas coisas como concorrentes:

- \`representacao\` — como transformar texto em número. Ranqueie estas ENTRE SI: são alternativas umas
  das outras, e a pergunta é qual delas rende mais por unidade de esforço aqui.
- \`aplicacao\` — onde usar embeddings, no nosso domínio. Estas NÃO competem com as de representação.
  A pergunta é outra: o que já foi feito em notícia/cultura de língua portuguesa como fonte de
  vigilância, o que aquilo mediu, e o que muda para nós. Uma abordagem de aplicação pode ser
  "tentar agora" mesmo sendo metodologicamente simples, se ela responde a uma pergunta que temos.

O campo \`grupo\` de cada linha do ranking diz em qual dos dois ela está. Numere dentro de cada grupo
(dois rank 1 é esperado). Nunca compare uma linha de representação com uma de aplicação.

Como ranquear:

- Ranqueie ABORDAGEM, não artigo. Várias fichas podem descrever a mesma abordagem (whitening aparece em
  três artigos): nesse caso é uma linha só, e a evidência é a soma delas.

- Duas colunas separadas, sempre: \`merit\` (o que a abordagem entrega, e contra que baseline) e
  \`adoption_cost\` (o que ela custa AQUI: dependência nova? GPU? tempo de encode sobre 4.369 artigos em
  CPU? precisa de rótulo?). Não misture as duas num veredito — o custo é um número que o planner precisa
  ver, não uma penalidade escondida.

- \`verdict\` ∈ {tentar agora, tentar depois, descartar}. "descartar" é resposta legítima e esperada: se a
  família rendeu 18 artigos e 3 prestam, diga 3. Não infle a lista para parecer produtivo.

- Desconfie do que as fichas não sustentam. Se o custo é "não reportado", isso é uma incerteza, e
  incerteza não é barato. Marque "tentar depois", ou diga explicitamente que a estimativa é sua.

- \`cross_cutting\`: o que aparece em vários artigos e por isso é decisão de desenho, não de artigo — por
  exemplo, "todos assumem janela de 512 tokens, o que trunca 39% do nosso corpus". Se uma afirmação geral
  só se sustenta dentro de um grupo, DIGA o grupo na própria frase. A primeira rodada escreveu "nenhuma
  ficha testa a nossa tarefa" quando as de aplicação testavam: era verdade sobre o grupo e falso sobre a
  biblioteca.

- \`first_move\`: se você tivesse que testar UMA coisa primeiro, qual e por quê. Uma frase.

Escreva articles/${FAMILY.slug}/ranking.md — é o artefato que um humano lê. Uma tabela ranqueada POR
GRUPO (seção de representação, seção de aplicação), cada uma com as duas colunas visíveis; depois uma
seção curta por abordagem; depois cross_cutting; depois first_move; e por fim o que ficou de fora e por
quê. Markdown simples, sem emoji.`

// --- passo 3a: relatar (um agente por eixo) ---------------------------------
// Por que por eixo e não um agente só: 23 fichas num contexto dão um parágrafo
// raso por artigo — o mesmo motivo que fez "Ler" ser fase separada de "Rankear".
// Cada agente recebe TODAS as fichas e escreve só a sua seção; não há roteamento
// de ficha para eixo, porque rotear erra em silêncio e cada eixo precisa poder
// dizer "nada nesta lista responde à minha pergunta".
const eixoPrompt = (eixo, cards) => `Você é um pesquisador acadêmico sênior escrevendo UMA seção do capítulo de revisão de literatura de uma dissertação de mestrado. O capítulo é escrito por várias pessoas, uma por seção, e um editor costura as partes depois. Sua parte é só esta seção.

O QUE O CAPÍTULO PRECISA FAZER: sintetizar os artigos levantados num texto coeso, fluido e analítico, que conecte o estado da arte à aplicação prática deste projeto — a previsão de séries temporais epidemiológicas com métodos neurais e dados multimodais (o volume de notícia). Quem lê é a banca e o orientador: gente que entende epidemiologia e série temporal, e que não é especialista em processamento de linguagem natural.

A SUA SEÇÃO responde a esta PERGUNTA — repare que é uma pergunta, não uma lista de artigos:
  título:   ${eixo.titulo}
  pergunta: ${eixo.pergunta}

As fichas dos ${cards.length} artigos selecionados. Elas foram escritas por agentes que abriram os PDFs e reportaram o que o artigo DIZ. Você NÃO abre PDF nenhum e NÃO procura nada: trabalhe só com o que está aqui.
${JSON.stringify(cards, null, 2)}

O que a sua seção entrega:

1. \`narrativa\` — O TEXTO. É isto que vai para o capítulo, e é o produto principal da sua seção: prosa acadêmica corrida, em parágrafos, nunca em bullets.

   O QUE FAZ UMA SÍNTESE, e não uma lista:
   - Agrupe por tema convergente, não por artigo. Vários estudos que medem a mesma coisa viram UM parágrafo que diz o que eles juntos mostram, com o número de cada um dentro da frase.
   - Escreva as transições e os contrastes — é o parágrafo que ninguém escreve sozinho. Diga o que os achados têm em comum e onde eles brigam: "Enquanto a maioria dos estudos aponta X, a abordagem Y demonstra que...". Sem isso o capítulo vira uma pilha de resumos.
   - Contradição entra na prosa como contradição, nomeada, com os dois lados e de quem é cada lado. Nunca escolha um lado em silêncio, e nunca deixe a contradição só implícita.
   - A força da evidência entra como LINGUAGEM, nunca como etiqueta. Veja o item 3.

2. \`claims\` — a AUDITORIA da sua narrativa, e não texto do capítulo. Cada afirmação que a sua prosa sustenta, com \`from\` (as CHAVES das fichas) e \`forca\`. Este campo não é impresso: ele existe para um revisor conferir, depois, se a prosa reflete a força real de cada achado e se todo número tem de onde vir. Se você não consegue apontar de onde uma afirmação veio, ela não entra nem na prosa nem aqui. Se as fichas não cobrem a sua pergunta, devolva \`claims\` vazio, escreva na \`narrativa\` que a literatura levantada não responde a esta pergunta, e diga isso na summary — "não temos evidência sobre isto" é um resultado, e costuma ser o mais útil dos que você pode dar.

3. \`forca\` de cada claim, e seja rigoroso com ela — a força existe para virar prosa, não para virar rótulo:
   - "consenso"  — vários artigos independentes chegam à mesma conclusão. Na prosa: "Há um amplo consenso na literatura de que...", "Múltiplos estudos independentes convergem para..."
   - "parcial"   — um ou dois artigos, sem replicação. Na prosa: "Evidência mais restrita sugere que...", "Um ou dois estudos, ainda sem replicação, indicam que..."
   - "isolado"   — resultado de um grupo só, que ninguém mais testou. Na prosa: "Um único estudo relata que... resultado que nenhum outro grupo nesta revisão replicou."
   - "contradito" — algum artigo desta lista diz o contrário. Na prosa: contraste nomeado, os dois lados e os autores de cada lado.
   A maior parte do que uma área diz é "parcial", não "consenso". Não infle: uma seção com sete afirmações "consenso" e uma ficha cada é uma seção que não foi pensada.

   Exemplo do que NÃO fazer, e do que fazer no lugar:
   - ERRADO: "Os vetores de frase extraídos de um transformer pré-treinado são fracos para similaridade por cosseno (01, 12, 07, 02). Força: consenso."
   - CERTO: "Há um amplo consenso na literatura de que os vetores de frase extraídos diretamente de um transformer pré-treinado são fracos para medir similaridade por cosseno: a média das saídas do BERT marca 54,81 contra 61,32 da média de vetores de palavra estáticos (GloVe) (Reimers & Gurevych, 2019), achado replicado com a média do BERT em 46,35 contra 58,02 do GloVe (Li et al., 2020) e com o T5 sem ajuste fino em 55,97 (Ni et al., 2022)."

4. CITAÇÃO. Cada ficha traz um campo \`cita\` — a citação (Autor, Ano) já pronta. Use \`cita\` TAL COMO VEIO. Não monte a citação você mesmo a partir de \`author\` + \`year\`: quando duas fichas desta família têm o mesmo autor e o mesmo ano, o \`cita\` já traz a letra que as distingue (2020a, 2020b), e remontar por conta própria perde a letra e deixa as duas citações indistinguíveis. Se \`cita\` vier \`null\` (a ficha não trouxe autor confiável), NÃO invente um nome: descreva o estudo pela técnica — "o estudo que treina um codificador supervisionado sobre pares do SNLI mostra que..." — em vez de citar um autor que a ficha não deu.
   NUNCA cite por número de ficha: "(01, 12, 07)" obriga quem lê a procurar um índice que ele não tem, e "(Reimers & Gurevych, 2019)" ele confere na hora.

5. \`lacunas\` — o que a área NÃO mediu, como LISTA de objetos, cada um com \`lacuna\` (uma frase) e \`from\` (as chaves das fichas que mostram a lacuna — em geral as fichas que NÃO medem aquilo, e cuja ausência de medição é o próprio achado). Valem as mesmas regras das afirmações: sem chave, não escreva. Você é o único agente que tem as fichas; quem escreve o capítulo final não as tem, e vai copiar as suas chaves. \`lacunas\` é a parte mais valiosa da seção: é o que a área não mediu, e portanto onde este projeto pode contribuir em vez de repetir o que já se sabe.

6. O REGISTRO DA ESCRITA. A seção é lida por ${ESTILO.leitor}. Ele entende uma regressão e um vetor; não entende pooling. Escreva o português primeiro e ponha o termo técnico ao lado, entre parênteses, quando ele aparecer pela primeira vez: "os vetores ficam todos parecidos entre si (anisotropia)". Apresentado uma vez, o termo pode ser usado à vontade no resto da seção.

   O que NÃO fazer com isso: explicar o domínio. Você não está escrevendo uma introdução à área, está reportando o estado dela. Glosar "anisotropia" custa cinco palavras; explicar por que a anisotropia acontece custa um parágrafo e não é o que a sua seção entrega. Apresente o termo e siga.

   O NÚMERO FICA NA FRASE. Encurtar a frase cortando o dado é o jeito errado de ficar claro: o número é o que torna a afirmação valiosa e conferível, e a fase Revisar confere número contra ficha. A clareza tem que vir do resto da frase, não da amputação dela.

   Nesta família, estes termos contam como jargão e precisam da apresentação na primeira vez em que aparecerem: ${ESTILO.termos.join(', ')}.

   E NUNCA INVENTE O SIGNIFICADO DE UMA SIGLA. Se a ficha traz "HFMD" e você não sabe o que a sigla significa, escreva "HFMD" e siga — não traduza por palpite, não deduza pelo contexto, não escolha a doença que parece mais provável. Uma sigla crua o leitor confere; uma expansão errada ele acredita, porque vem em português e soa como fato. Isto não é hipótese: um agente leu HFMD numa ficha e escreveu "febre aftosa" no relatório, que é outra doença, de outra espécie. Na dúvida, a sigla crua é a resposta certa.

7. VOCABULÁRIO PROIBIDO NO TEXTO. A ficha, o eixo e a força são andaime DESTE workflow: servem para você pensar e para o revisor conferir, e não existem para o leitor do capítulo. Nada disso pode aparecer na \`narrativa\`:
   - "ficha" / "fichas" → escreva "artigo", "estudo", "a literatura", "os trabalhos levantados".
   - "portão mecânico", "gate", "acertos", "hits" → escreva "critérios de triagem", "critérios de elegibilidade", "registros candidatos".
   - "Força: consenso/parcial/isolado/contradito" como etiqueta → converta em prosa, como no item 3. A etiqueta só existe no campo \`forca\`.
   - "Eixo N —" no começo da seção, ou qualquer menção a quantos artigos ou quantos agentes compuseram esta seção → isso é processo de produção do capítulo, não conteúdo dele. A seção começa pelo conteúdo.
   Se uma dessas palavras for inevitável para descrever o desenho de um artigo, descreva o desenho sem ela: "o estudo aplica três filtros sucessivos" em vez de "o estudo tem três gates".

O que você NÃO faz, em nenhuma hipótese:
- NÃO dá veredito sobre o que devemos implementar. NÃO estima custo, esforço, dependência ou tempo. Isso é o trabalho de outro artefato do mesmo workflow (o ranking), e repetir aqui é o que transformaria este relatório numa versão em prosa dele.
- A FRONTEIRA DO CUSTO, que é onde se erra com mais facilidade. PODE descrever o que um método é e o que exige como insumo: "não supervisionado", "precisa de rótulos", "opera por álgebra linear sobre vetores já extraídos", "reporta complexidade O(N)". NÃO PODE precificar: "barato", "caro", "dispensa GPU", "cabe em minutos", "sem dependência nova". Descrever o insumo é o relatório; precificar o insumo é o ranking. Dizer que a literatura não reporta um número é uma lacuna, e lacuna deve ser dita.
- NÃO cita número que não esteja nos artigos que você leu. Se você precisaria de um número que o estudo não traz, escreva "o estudo não reporta esse número" — não estime, não arredonde, não deduza.
- NÃO escreve o capítulo inteiro. Só a sua seção.

Escreva em português, na voz do capítulo — não em primeira pessoa de agente. Reporte o que as fichas dizem, não o que você acha que a área diz.`

// --- passo 3b: sintetizar ---------------------------------------------------
// O sintetizador recebe o ranking SEM mérito e SEM custo. É de propósito e é o
// que sustenta a proibição de veredito: o que ele não tem, ele não pode copiar.
// Se um dia alguém colar o ranking inteiro aqui, esta garantia morre em silêncio.
const sintetizarPrompt = (secoes, ranking, busca, citacoes) => `Você é o editor do capítulo de revisão de literatura de uma dissertação de mestrado. Costura as seções escritas por outros autores num texto único, coeso e fluido. Você NÃO lê PDF nenhum e NÃO tem as fichas: trabalhe só com o que está aqui.

O QUE O CAPÍTULO PRECISA FAZER: sintetizar os artigos levantados num texto analítico que conecte o estado da arte à aplicação prática deste projeto — a previsão de séries temporais epidemiológicas com métodos neurais e dados multimodais (o volume de notícia). Quem lê é a banca e o orientador: gente que entende epidemiologia e série temporal, e que não é especialista em processamento de linguagem natural.

AS SEÇÕES (uma por eixo, cada uma escrita por alguém que viu as fichas). Cada seção traz \`narrativa\` — o texto pronto —, \`claims\` e \`lacunas\` — que são auditoria, e NÃO devem ser impressas:
${JSON.stringify(secoes, null, 2)}

O FUNIL DA BUSCA — como estes artigos chegaram até aqui:
${JSON.stringify({ counts: busca.counts, reprovados_por_regra: busca.rejected_by_gate, nao_selecionados_com_motivo: busca.considered_not_selected }, null, 2)}

AS ABORDAGENS QUE O RANKING DO MESMO WORKFLOW APROVOU — só o nome e o grupo. De propósito: sem mérito, sem custo, sem posição e sem veredito:
${ranking ? JSON.stringify(ranking.ranked.map((r) => ({ grupo: r.grupo, abordagem: r.approach })), null, 2) : 'o ranking não rodou nesta rodada — escreva o relatório sem a seção que situa as nossas candidatas, e diga na summary que ela faltou'}

O MAPA DE CITAÇÕES — chave da ficha → citação (Autor, Ano) já resolvida. Use-o SÓ para traduzir uma chave em citação quando precisar nomear um estudo na prosa das lacunas (as seções escrevem as chaves ali). Chave com valor \`null\` não tem autor confiável: descreva o estudo pela técnica, nunca invente um nome.
${JSON.stringify(citacoes, null, 2)}

Escreva articles/${FAMILY.slug}/relatorio.md. É o artefato que um humano abre para entender a área sem abrir PDF nenhum.

ESTRUTURA:
1. Abertura — o que esta família de técnicas é e o problema de pesquisa que motiva revisá-la: conectar o estado da arte da representação vetorial de texto à previsão de séries temporais epidemiológicas com métodos neurais e dados multimodais. Um ou dois parágrafos. Sem preâmbulo do tipo "este relatório tem como objetivo", e SEM descrever como o capítulo foi produzido: não diga quantos artigos foram lidos, nem quantos "eixos" ou agentes escreveram as seções, nem monte tabela de correspondência entre chave e autor. Isso é andaime de produção e não tem lugar no capítulo.
2. A seleção do corpus — o que a busca viu e por que cortou. CURTO: uma seção, não uma análise dos descartados. Diga os números e o que eles implicam para quem lê o resto: o corpo do capítulo fala de uma amostra escolhida por critérios explícitos, não da área inteira. Sem esta seção o capítulo mente por omissão. Veja o exemplo de reescrita nas REGRAS abaixo: esta seção é onde o vocabulário de sistema vazou na rodada anterior.
3. Uma seção por eixo, na ordem em que vieram. O CABEÇALHO é o título do eixo (ex.: "Como o texto vira vetor: pooling, normalização e a geometria do espaço"), nunca "Eixo 1 — ...": a numeração de eixo é andaime do workflow. O CORPO é a \`narrativa\` da seção, preservada. Você costura: elimina a repetição entre seções, escreve as transições entre uma e outra, e unifica a voz. Costurar NÃO é reescrever para outro tom nem reconstruir o texto a partir de \`claims\` — \`claims\` é auditoria e não se imprime.
4. Onde as nossas candidatas ficam nisto — uma seção curta situando as abordagens aprovadas dentro do que as seções descrevem. É a ÚNICA parte em que você usa a lista do ranking, e você a recebeu SEM posição e SEM veredito: NÃO escreva "tentar agora", "descartar", nem "rank 1" em lugar nenhum. Quem quer a decisão lê o ranking.md; esta seção existe para dizer em que ponto do campo cada abordagem encosta. Se você mencionar um achado específico aqui, cite-o como as seções citam — (Autor, Ano) —, nunca por número de ficha.
5. Lacunas — junte as lacunas das seções, sem repetir. Escreva em PARÁGRAFOS agrupados por tema (idioma e corpus; unidade de análise; tarefa a jusante; e assim por diante), não em bullets, e nomeie os estudos com o mapa de citações quando quiser apontar um caso concreto. Cada lacuna chega das seções com as chaves das fichas que a sustentam (\`from\`) — mas chave NÃO vai para o texto: na prosa, quem sustenta a lacuna aparece como (Autor, Ano), ou não aparece. NÃO monte lista nova de fontes e NÃO escreva intervalo ("01-13"): você não tem as fichas, e portanto não tem como saber se uma ficha que você não viu sustenta a lacuna. Foi exatamente assim que a rodada anterior pôs uma ficha que reporta custo numa lista de fichas que não reportam. Se uma lacuna chegar sem chave, escreva a lacuna e diga que ela veio sem fonte.
   FECHE a seção com um parágrafo que ligue as lacunas JÁ LEVANTADAS ao problema deste projeto: a ausência de avaliação nativa em português para estas técnicas e a limitação dos embeddings de frase quando aplicados a documentos jornalísticos longos. Aponte, entre as lacunas que as seções deram, quais são precisamente essas duas. NÃO invente lacuna nova para chegar nelas: se nenhuma das lacunas levantadas tocar nesses dois pontos, diga isso — é um resultado, não um defeito a esconder.
6. O que ficou de fora — artigos que nenhuma seção usou, e por quê.

REGRAS QUE VALEM MAIS QUE A FLUÊNCIA:

- O REGISTRO DA ESCRITA. O leitor é ${ESTILO.leitor}, e o texto é um capítulo de dissertação: prosa acadêmica corrida, impessoal, em parágrafos. As seções já chegam escritas nesse registro — preserve-o, e onde elas se repetirem, corte a repetição em vez de reescrever o trecho. Onde um termo técnico aparecer pela PRIMEIRA vez no capítulo, o português vem primeiro e o termo ao lado entre parênteses: "os vetores ficam todos parecidos entre si (anisotropia)". A partir daí o termo é livre. NÃO explique o domínio: isto é estado da arte, não introdução à área.
- VOCABULÁRIO PROIBIDO NO ARQUIVO. A ficha, o eixo, a força e o funil são andaime DESTE workflow: servem para produzir o capítulo, não para o leitor lê-lo. Nada disso pode aparecer no texto:
  * "ficha" / "fichas" → "artigo", "estudo", "a literatura", "os trabalhos levantados".
  * "portão mecânico", "gate", "acertos", "acertos únicos", "hits" → "critérios de triagem", "critérios de elegibilidade", "registros candidatos".
  * "Força: consenso/parcial/isolado/contradito" como etiqueta → converta em linguagem: "Há um amplo consenso na literatura de que...", "Evidência mais restrita sugere que...", "Um único estudo relata que...". A etiqueta não existe no capítulo; ela é auditoria.
  * "Eixo N —" como cabeçalho → o título do eixo, sem número.
  * contagem de artigos, de eixos ou de agentes que produziram o capítulo → não entra no texto.
  Exemplo do que NÃO fazer, e do que fazer no lugar (a seção 2 da rodada anterior saiu exatamente assim):
  - ERRADO: "A busca produziu 1057 acertos únicos. Um portão mecânico deixou passar 429, e desses 23 foram selecionados com PDF."
  - CERTO: "A busca sistemática identificou 1.057 registros únicos candidatos. Após a aplicação dos critérios de elegibilidade — ano de publicação, volume de citações e qualidade do veículo —, 429 artigos os atenderam integralmente, dos quais 23 tiveram o texto completo recuperado e foram incluídos nesta revisão."
- A CITAÇÃO É (Autor, Ano). Toda afirmação que se apoia na literatura carrega a citação entre parênteses — (Reimers & Gurevych, 2019), (Gao et al., 2021) — ou nomeia o autor na própria frase. NUNCA cite por número de ficha: "(09, 10, 12)" obriga quem lê a procurar um índice que ele não tem. As seções já escrevem assim; se você reescrever um trecho, mantenha. Use o mapa de citações para as lacunas; se uma citação que chegou não casar com o mapa, mantenha como está e diga na summary — não corrija por conta própria.
- NÃO DESCARTE A SIGLA AO MANTER A GLOSA, e não invente expansão que a seção não deu. "febre aftosa (HFMD)" continua "febre aftosa (HFMD)" — nunca só "febre aftosa". O parêntese é o único vestígio que permite a quem lê desconfiar de uma glosa errada, e foi descartando ele que a rodada anterior escondeu um erro de espécie no meio de uma frase correta. Se a glosa que chegou parece duvidosa, mantenha as duas formas lado a lado; a dúvida vai para a summary, não para o lixo.
- O NÚMERO FICA NA FRASE, sempre, e a clareza vem do resto da frase. Frase longa se conserta dividindo em duas — nunca cortando o dado, que é o que torna a afirmação valiosa e conferível. "Frase com mais de 45 palavras" não é questão de gosto: é defeito contado por script (${ESTILO.script}), e a fase Revisar roda ele no arquivo que você escrever.
- NENHUM veredito, NENHUMA recomendação, NENHUM custo. Você recebeu o ranking sem as colunas de mérito, custo, posição e veredito exatamente para não poder repeti-los. A seção 4 SITUA as candidatas dentro do campo; ela não re-justifica a escolha delas.
- A FRONTEIRA DO CUSTO, que é onde este relatório erra com mais facilidade. Você PODE descrever o que um método é e o que ele exige como insumo: "não supervisionado", "precisa de rótulos em inglês", "opera por álgebra linear sobre vetores já extraídos", "reporta complexidade O(N)". Você NÃO PODE precificar a adoção, aqui ou em qualquer lugar: "barato", "caro", "dispensa GPU", "cabe em minutos", "sem dependência nova", "custo baixo" são todos do ranking. Descrever o insumo é o relatório; precificar o insumo é o ranking. E o mesmo vale ao contrário: o que a LITERATURA deixa de reportar ("nenhum dos artigos revisados traz número de inferência") é uma lacuna da área e deve ser dita — isso não é preço.
- NÃO invente número, autor, ano ou venue que não esteja nas seções. Se um número não veio, escreva que não veio.
- Se duas seções se contradizem, NÃO escolha uma em silêncio: diga que se contradizem e de onde vem cada lado. Contradição resolvida por omissão é o defeito mais caro deste tipo de documento, porque some justamente onde o leitor mais precisava saber.
- Markdown simples, sem emoji, sem negrito decorativo.

No retorno estruturado, liste as fichas que você de fato citou e as que NUNCA citou — para isso, inverta o mapa de citações: cada (Autor, Ano) que aparece no texto corresponde a uma chave, e uma chave que não aparece em lugar nenhum é um artigo lido e depois esquecido. Liste as nunca citadas pelas CHAVES (é o vocabulário interno de quem vai conferir), mesmo que o texto cite por autor.`

// --- passo 3c: revisar ------------------------------------------------------
// Lê o ARQUIVO EM DISCO, não o retorno do sintetizador. O defeito nº 3 da
// primeira rodada foi exatamente conferir o que o agente dizia ter feito.
const revisarPrompt = (cards, secoes) => `Você confere um capítulo de revisão de literatura escrito contra as fichas que ele deveria resumir. Você NÃO conserta nada — só reporta.

O arquivo: articles/${FAMILY.slug}/relatorio.md
LEIA O ARQUIVO EM DISCO. Não confie em nenhuma descrição de terceiro sobre ele, e não confie no que o agente que o escreveu disse ter escrito. A primeira rodada deste workflow errou exatamente aí: a verificação conferia o que o agente RESPONDIA, e o arquivo no disco tinha outra forma.

As fichas, que são a fonte de tudo que o capítulo afirma. Cada uma traz \`key\`, \`author\`, \`year\` e \`cita\` — a citação (Autor, Ano) já pronta, com letra (2020a/2020b) quando duas fichas desta família compartilham autor e ano:
${JSON.stringify(cards, null, 2)}

A AUDITORIA DAS SEÇÕES — só o que as seções que compuseram o capítulo declararam sustentar, com a força de cada achado. Isto NÃO é texto entregue e você não confere nada aqui contra o arquivo: é a régua para o check 5, e sem ela o check 5 não tem como rodar.
${JSON.stringify(secoes.map((s) => ({ eixo: s.eixo, claims: s.claims })), null, 2)}

ANTES DE CONFERIR, monte você mesmo o mapa citação→ficha a partir de \`cita\`/\`author\`/\`year\` das fichas acima. Não confie na memória: toda citação do capítulo tem que casar com uma entrada desse mapa. Fichas com \`author: "não identificado"\` não têm citação e não entram no mapa.

Confira, afirmação por afirmação do capítulo:

1. TODA afirmação que se apoia na literatura carrega uma citação entre parênteses — (Reimers & Gurevych, 2019), (Gao et al., 2021) — ou nomeia o autor na própria frase; e o mesmo vale para toda lacuna que nomeia um estudo. Conte as que não carregam: são órfãs, e órfã é defeito. Uma afirmação sobre AUSÊNCIA de evidência é a única que pode legitimamente não ter citação — não a conte como órfã, mas conte-a se ela afirmar ausência sobre um tema que alguma ficha cobre.
   A EXCEÇÃO, e não a conte como órfã: as afirmações da seção que descreve a SELEÇÃO DO CORPUS, que contam o processo de busca (quantos candidatos, quantos passaram nos critérios, quantos caíram em cada critério). A fonte delas é o registro da busca, não a literatura — não existe ficha para citar, e cobrar citação ali é cobrar a coisa errada. Confira os números dessa seção contra o registro, se quiser, mas não os acuse de órfãos.
   E NÃO conte como órfã a frase de SÍNTESE ou de TRANSIÇÃO — a que amarra o parágrafo ("A leitura conjunta é que não há pooling vencedor universal", "O que aproxima os três usos é...") sem afirmar fato novo sobre um artigo. Citar ali seria ruído; a citação pertence às frases que trazem o achado, e o capítulo é escrito em prosa justamente para que essas frases existam. Órfã é a frase que afirma achado de literatura sem dizer de onde ele veio.

2. As citações existem? Liste em \`citacoes_sem_ficha\` toda citação do capítulo que não case com nenhuma entrada do mapa que você montou. Citação que não existe é o pior caso, porque parece rastreável e não é. Atenção à colisão: quando duas fichas compartilham autor e ano, a citação esperada tem letra (2020a/2020b) — se o capítulo usar o ano cru, ou a letra trocada, reporte.

3. AUTOR INVENTADO. Para toda ficha cujo \`author\` seja "não identificado", confira se o capítulo, em algum trecho, nomeia um autor para ela. Se nomear, é nome inventado — mesma gravidade da sigla inventada. Reporte em \`autores_inventados\`, com a ficha e o trecho.

4. VOCABULÁRIO PROIBIDO. Procure LITERALMENTE no arquivo, e reporte cada ocorrência em \`vocabulario_proibido\`:
   - "ficha" ou "fichas"
   - "portão mecânico", "gate", "acertos", "acertos únicos", "hits"
   - cabeçalho que comece com "Eixo" seguido de número e travessão ("Eixo 1 —")
   - "Força: " seguido de consenso/parcial/contradito/isolado
   - menção a quantos artigos, eixos ou agentes produziram o capítulo (isso é processo de produção, não conteúdo)
   Lista vazia é o esperado. Este vocabulário é andaime do workflow: se ele aparece no texto entregue, o capítulo lê como processo interno, não como revisão de literatura.

5. FORÇA REFLETIDA EM PROSA. A AUDITORIA DAS SEÇÕES acima traz \`claims\` com \`forca\` — é auditoria, e não deve ser impressa, mas ela diz a força real de cada achado. Para cada claim com \`forca\` = parcial, isolado ou contradito, confira que a prosa correspondente no capítulo carrega a ressalva ou o contraste (não precisa ser frase a frase; a leitura daquele trecho tem que soar com a incerteza que a força indica, e não como se fosse consenso). Reporte em \`forca_nao_refletida\` toda claim cuja prosa não refletiu a força.
   E o inverso, que é o defeito simétrico: prosa que afirma um consenso amplo onde a auditoria não tem nenhuma claim "consenso" por trás.

6. VEREDITO E CUSTO. O capítulo foi proibido de dar veredito, recomendação, preço, e de reproduzir a decisão do ranking — a duplicação é o defeito de desenho que este passo existe para pegar. Liste toda frase que caia em qualquer um destes três casos:
   - veredito ou recomendação própria: "vale tentar", "deveríamos usar", "é o caminho"
   - rótulo de veredito ou posição do ranking reproduzido: "tentar agora", "descartar", "rank 1"
   - preço da adoção, aqui ou em qualquer lugar: "barato", "caro", "dispensa GPU", "cabe em minutos", "sem dependência nova", "custo baixo"
   O que NÃO é violação, e você não deve acusar: descrever o que um método é ou o que exige como insumo ("não supervisionado", "precisa de rótulos", "reporta complexidade O(N)"), e dizer que a LITERATURA não reporta um número ("nenhum dos artigos revisados traz custo de inferência") — isso é lacuna da área, e é o que o capítulo deve dizer. Descrever o insumo é o capítulo; precificar o insumo é o ranking.
   Também NÃO é violação, e a rodada anterior acusou por engano: dizer que uma capacidade não alcança o NOSSO RECORTE — "a força cross-lingual dos modelos multilíngues é irrelevante para o nosso caso, que é monolíngue". A seção de idioma existe justamente para responder se a distância de idioma foi medida ou assumida pequena por simpatia temática, e uma seção não responde à própria pergunta sem dizer se a capacidade nos alcança. A fronteira é o que a frase faz com a informação: dizer o que uma capacidade NÃO ALCANÇA é escopo; dizer o que FAZER com a abordagem ("vale tentar", "deveríamos usar", "é o caminho") é veredito, e veredito é do ranking. Não confunda as duas: acusar escopo de veredito empurra o capítulo a não responder a própria pergunta.
   E o parágrafo de fechamento da seção de lacunas, que conecta as lacunas já levantadas ao problema de pesquisa do projeto (falta de avaliação nativa em português, limitação de embeddings de frase para documentos jornalísticos longos), NÃO é veredito: é escopo, e é esperado que ele exista. Só é violação se ele propuser o que fazer, ou se inventar lacuna que a auditoria não levantou.
   Se não houver nenhuma frase nos três casos, devolva a lista vazia: é o esperado, e lista vazia aqui é resultado, não ausência de resultado.

7. FORMA — o arquivo tem as seções prometidas: abertura, seleção do corpus, uma por tema, onde as nossas candidatas ficam nisto, lacunas, o que ficou de fora? Liste o que falta.
   E confira a forma do corpo: cada seção temática é composta de PARÁGRAFOS de prosa, agrupando achados convergentes e contrastando os divergentes — não de bullets empilhando um estudo por linha. Bullet solto por estudo é o defeito que esta rodada existe para eliminar; liste onde isso aconteceu. Uma tabela de candidatas é aceitável e não é bullet de resultado.

8. CLAREZA — em duas metades, e a primeira você NÃO julga de cabeça: você RODA O SCRIPT.

   A parte objetiva, medida:
       python3 -I ${ESTILO.script} articles/${FAMILY.slug}/relatorio.md ${TERMOS_FLAG}
   Rode exatamente isso, com o arquivo em disco, e copie para o retorno os três contadores de ERRO que ele imprime (frases longas, termos sem glosa, parágrafos densos). NÃO conte você mesmo: o script existe justamente para o número ser o mesmo em toda rodada, e um número contado a mão não é. Se o script não rodar, \`script_rodou\` = false e você diz por quê — checagem objetiva que não aconteceu é falha, não é neutro.
   O que a checagem de glosa quer dizer, para você não achar que é ruído: o capítulo escreve o português primeiro e o termo ao lado, então a PRIMEIRA aparição de um termo da lista tem que estar entre parênteses — "os vetores ficam todos parecidos entre si (anisotropia)". Depois disso o termo é livre. O script acusa o termo que aparece solto antes de qualquer apresentação. Títulos não são conferidos, e é de propósito: título é rótulo.
   A citação (Autor, Ano) NÃO é glosa e não conta como uma: o script já sabe disso e a ignora antes de contar palavra e medir frase, então uma frase com três citações não infla por causa delas. Se você vir o script reclamando de um parêntese que é citação, o script está errado e você reporta — mas confira antes, porque o caso comum é a citação estar correta.

   A parte subjetiva, que é sua e só sua:
   - \`prosa_opaca\` — frases que o script não pega porque são curtas e não têm termo da lista, mas que um leitor de área paralela não entende. É o que sobra depois do contador, e costuma ser a maior parte do problema: "a correção é transdutiva, então a janela tem que ser rolling-origin" é curta, tem termo da lista, e não diz nada a quem não é da área.
   - \`glossas_vazias\` — termo entre parênteses que não apresenta nada. "(pooling)" ao lado de "pooling" passa no script e não apresenta coisa alguma; "(pooling, a média dos vetores de cada palavra)" apresenta. O parêntese tem que dizer o que a coisa É, não repetir o nome dela.
   Julgue com o leitor em mente: ${ESTILO.leitor}. Ele entende regressão e vetor; não entende pooling. NÃO exija explicação do domínio — o capítulo é proibido de virar introdução à área, e glosar não é o mesmo que ensinar.

   LIMITE DA SUA AÇÃO: você reporta, não reescreve. Não "conserte" a frase no retorno para mostrar como ficaria — o retorno é veredito, e a correção é do sintetizador numa próxima rodada.

Regras de decisão:
- conforme = false se QUALQUER check falhar. Se você não conseguir verificar algo, isso é uma falha (dúvida → não conforme). Nunca presuma que passou.
- No check 8, os ERROs do script e as suas duas listas subjetivas pesam igual: qualquer ERRO do script ou qualquer item em \`prosa_opaca\` ou \`glossas_vazias\` já é conforme = false. O script mede o que é contável; ele não substitui o seu julgamento, e passar nele com prosa opaca não é passar.
- divergencias: uma frase por divergência, com os números medidos dos dois lados.
- Se o arquivo não existir ou não for markdown legível, conforme = false e diga isso — é o caso mais grave.
- Você NÃO corrige o arquivo. Quem corrige é o sintetizador, numa próxima rodada.`

// --- execução ---------------------------------------------------------------
phase('Buscar')
log(`família: ${FAMILY.slug} — ${FAMILY.label}`)

if (REUSAR) {
  log(`REUSO LIGADO — carregando articles/${FAMILY.slug}/search.json em vez de buscar de novo`)
} else {
  log(`gates: ano>=${GATES.min_year} · citações>=${GATES.citations.mature_min} (ou >=${GATES.citations.recent_min} se <${GATES.citations.mature_age_years} anos) · h-index>=${GATES.venue.min_h_index} · PDF obrigatório`)
}

const busca = REUSAR
  ? await agent(CARREGAR, { label: 'carregar', phase: 'Buscar', schema: DISCOVERY_SCHEMA })
  : await agent(BUSCAR, { label: 'buscar', phase: 'Buscar', schema: DISCOVERY_SCHEMA })

if (!busca) {
  return {
    status: 'aborted',
    reuso: REUSAR,
    reason: REUSAR
      ? `o carregamento não retornou resultado — confira se articles/${FAMILY.slug}/search.json existe e é JSON válido`
      : 'a busca não retornou resultado (agente morto ou pulado)',
  }
}

log(`busca: ${busca.counts.total_unique_hits} candidatos → ${busca.counts.mechanical_gate_passers} passaram nas regras → ${busca.counts.selected_with_pdf} com PDF`)
log(`reprovados por regra: ${JSON.stringify(busca.rejected_by_gate)} · não selecionados com motivo escrito: ${busca.considered_not_selected}`)

// --- o arquivo obedece o contrato? ------------------------------------------
// A primeira rodada escreveu um arquivo com forma diferente da que o contrato
// pedia, e ninguém notou, porque nada conferia o arquivo. Isto confere.
phase('Conferir')
log('conferindo articles/' + FAMILY.slug + '/search.json contra o contrato')

const conferencia = await agent(CONFERIR, { label: 'conferir', phase: 'Conferir', schema: VERIFY_SCHEMA })

if (!conferencia) {
  log('a conferência não retornou veredito — seguindo sem ela')
} else {
  for (const c of conferencia.checks ?? []) {
    log(`  [${c.passed ? 'PASS' : 'FALHA'}] ${c.name}: ${c.detail}`)
  }
  if (!conferencia.conforms) {
    // Não aborta: os artefatos continuam utilizáveis, e jogar fora vinte minutos
    // de busca por um nome de campo errado seria pior. Mas fica impossível não ver.
    log(`CONTRATO VIOLADO — ${conferencia.divergencias.length} divergência(s):`)
    for (const d of conferencia.divergencias) log(`  · ${d}`)
  }
}

// Zero resultado é uma resposta, não um erro — e é a única que não vale a pena
// continuar. As fases seguintes custam um agente por artigo; sem artigo, não há
// o que ler.
if (!busca.articles || busca.articles.length === 0) {
  return {
    status: 'empty',
    family: FAMILY.slug,
    reuso: REUSAR,
    reason: REUSAR
      ? `o reuso não achou artigos em articles/${FAMILY.slug}/search.json — confira se o arquivo existe e se tem a chave selected. Detalhe do carregador: ${busca.summary}`
      : `nenhum artigo passou nos gates em ${busca.counts.total_unique_hits} candidatos. A trilha está em articles/${FAMILY.slug}/search.json — comece por rejected_by_gate.`,
    busca,
    conferencia,
    ranking: null,
  }
}

// SEM TETO, de propósito. Na primeira rodada havia um teto de 10 tomado como
// prefixo da lista ordenada pelo próprio buscador, e ele cortou exatamente os
// artigos de domínio. Quem a busca selecionou ganha ficha. Se um dia a lista
// vier grande demais para o bolso, o corte tem que ser por GRUPO ou por
// relevância declarada — nunca por posição na lista.
phase('Ler')
log(`${busca.articles.length} agentes, um por artigo — cada um abre o PDF e devolve uma ficha`)

const fichas = (await parallel(busca.articles.map((a) => () =>
  agent(fichaPrompt(a), { label: `ler:${a.key}`, phase: 'Ler', schema: CARD_SCHEMA })
))).filter(Boolean)

if (fichas.length === 0) {
  return { status: 'aborted', family: FAMILY.slug, busca, reason: 'nenhuma ficha voltou — sem elas o ranking não tem insumo' }
}

if (fichas.length < busca.articles.length) {
  log(`ATENÇÃO: ${busca.articles.length - fichas.length} artigo(s) ficaram sem ficha (agente morreu ou foi pulado). O ranking NÃO os vê.`)
}

const porGrupo = {}
for (const f of fichas) porGrupo[f.grupo] = (porGrupo[f.grupo] ?? 0) + 1
log(`fichas: ${fichas.length} — ${JSON.stringify(porGrupo)}`)

// --- a citação (Autor, Ano) de cada ficha -----------------------------------
// Feito AQUI, em JS puro, e não dentro do fichaPrompt, por um motivo
// estrutural: as fichas são lidas em paralelo e cada agente só vê UM artigo.
// Nenhum deles pode saber se outra ficha desta mesma família tem o mesmo autor
// e o mesmo ano — e é exatamente esse o caso que exige desambiguação (2020a /
// 2020b). Só este ponto, depois que todas voltaram, tem o conjunto completo.
//
// A regra é determinística e não especulativa: a letra só aparece quando a
// colisão EXISTE neste conjunto de fichas. Nenhum agente decide isso, e
// portanto nenhum agente pode errar isso.
const porAutorAno = {}
for (const f of fichas) {
  if (!f.author || f.author === 'não identificado' || !f.year) {
    f.cita = null // sem autor confiável não há citação; quem escreve descreve o estudo pela técnica
    continue
  }
  const chave = `${f.author}|${f.year}`
  ;(porAutorAno[chave] ??= []).push(f)
}
const LETRAS = 'abcdefghij'
for (const grupo of Object.values(porAutorAno)) {
  grupo.forEach((f, i) => {
    f.cita = grupo.length > 1 ? `${f.author}, ${f.year}${LETRAS[i]}` : `${f.author}, ${f.year}`
  })
}

const semCitacao = fichas.filter((f) => !f.cita)
if (semCitacao.length) {
  log(`ATENÇÃO: ${semCitacao.length} ficha(s) sem citação confiável (autor não identificado na capa): ${semCitacao.map((f) => f.key).join(', ')} — o relatório vai descrevê-las pela técnica, nunca por um nome inventado.`)
}
const colisoes = Object.values(porAutorAno).filter((g) => g.length > 1)
if (colisoes.length) {
  log(`desambiguação aplicada em ${colisoes.length} par(es) autor+ano: ${colisoes.map((g) => g.map((f) => f.cita).join('/')).join(' · ')}`)
}

// O mapa chave→citação que o sintetizador usa para nomear um estudo dentro da
// prosa das lacunas, onde ele só tem as chaves que as seções copiaram.
const citacoes = Object.fromEntries(fichas.map((f) => [f.key, f.cita]))

phase('Rankear')
log(`ranqueando ${fichas.length} fichas → articles/${FAMILY.slug}/ranking.md`)

const ranking = await agent(rankearPrompt(fichas), {
  label: 'ranquear',
  phase: 'Rankear',
  schema: RANKING_SCHEMA,
  effort: 'high', // a única fase em que o julgamento é o trabalho inteiro
})

if (!ranking) {
  // O relatório continua: ele não depende do ranking para existir. Só perde a
  // seção que situa as nossas candidatas, e o sintetizador é avisado disso.
  log('o ranking não voltou — o relatório vai rodar sem a seção que situa as candidatas')
}

// --- passo 3: relatar -------------------------------------------------------
// Roda DEPOIS do ranking de propósito: é a seção 4 do relatório que situa as
// abordagens aprovadas dentro do que o campo descreve, e para isso o ranking
// precisa existir antes.
phase('Relatar')
log(`relatório: ${EIXOS.length} eixo(s), um agente por eixo — cada um vê as ${fichas.length} fichas e escreve só a sua seção`)

const secoes = (await parallel(EIXOS.map((eixo) => () =>
  agent(eixoPrompt(eixo, fichas), { label: `eixo:${eixo.slug}`, phase: 'Relatar', schema: SECTION_SCHEMA })
))).filter(Boolean)

if (secoes.length === 0) {
  return {
    status: 'partial',
    family: FAMILY.slug,
    reuso: REUSAR,
    reason: 'nenhuma seção do relatório voltou — sem elas o sintetizador não tem o que costurar',
    fichas: fichas.length,
    ranking,
    relatorio: null,
    revisao: null,
  }
}

if (secoes.length < EIXOS.length) {
  log(`ATENÇÃO: ${EIXOS.length - secoes.length} eixo(s) ficaram sem seção. O relatório vai sair sem eles, e a fase Revisar vai acusar a falta — não é para corrigir aqui.`)
}

const lacunasDeclaradas = secoes.reduce((n, s) => n + (s.lacunas?.length ?? 0), 0)
log(`seções: ${secoes.length} — ${secoes.reduce((n, s) => n + (s.claims?.length ?? 0), 0)} afirmações, ${lacunasDeclaradas} lacunas declaradas`)

phase('Sintetizar')
log(`costurando ${secoes.length} seções → articles/${FAMILY.slug}/relatorio.md`)

const relatorio = await agent(sintetizarPrompt(secoes, ranking, busca, citacoes), {
  label: 'sintetizar',
  phase: 'Sintetizar',
  schema: REPORT_SCHEMA,
  effort: 'high', // escrever o relatório é julgamento do começo ao fim
})

if (!relatorio) {
  return {
    status: 'partial',
    family: FAMILY.slug,
    reuso: REUSAR,
    reason: 'o sintetizador não voltou — as seções existem, mas o relatório não foi escrito',
    fichas: fichas.length,
    ranking,
    secoes: secoes.length,
    relatorio: null,
    revisao: null,
  }
}

if (relatorio.claims_sem_fonte > 0) {
  log(`ATENÇÃO: o próprio sintetizador reportou ${relatorio.claims_sem_fonte} afirmação(ões) sem ficha. A fase Revisar confere se ele contou certo.`)
}
if (relatorio.fichas_nunca_citadas?.length) {
  log(`fichas lidas e nunca citadas no relatório: ${relatorio.fichas_nunca_citadas.join(', ')}`)
}

phase('Revisar')
log(`conferindo articles/${FAMILY.slug}/relatorio.md contra as ${fichas.length} fichas — afirmação por afirmação`)

const revisao = await agent(revisarPrompt(fichas, secoes), {
  label: 'revisar',
  phase: 'Revisar',
  schema: REVIEW_SCHEMA,
  effort: 'high', // conferir número contra ficha é trabalho de atenção, não de resumo
})

if (!revisao) {
  log('a revisão não voltou — o relatório fica no disco sem veredito sobre ele')
} else if (!revisao.conforme) {
  // Não apaga o arquivo: um relatório com defeito declarado é mais útil que
  // nenhum, e o defeito fica registrado. Mas fica impossível não ver.
  log(`RELATÓRIO NÃO CONFORME — ${revisao.divergencias.length} divergência(s):`)
  for (const d of revisao.divergencias) log(`  · ${d}`)
}

// O estilo do capítulo, em números. Tudo zero é o esperado, e é o que diz que a
// reescrita pegou: se o vocabulário de sistema voltou a vazar para a prosa, ou
// se a força das evidências parou de aparecer, aparece aqui e não só na leitura.
if (revisao) {
  const vazios = [
    ['citações sem ficha', revisao.citacoes_sem_ficha],
    ['autores inventados', revisao.autores_inventados],
    ['vocabulário proibido', revisao.vocabulario_proibido],
    ['força não refletida na prosa', revisao.forca_nao_refletida],
  ]
  const sujos = vazios.filter(([, v]) => v?.length)
  if (sujos.length) {
    for (const [nome, v] of sujos) log(`ATENÇÃO: ${nome} — ${v.length}: ${v.join(' · ')}`)
  } else {
    log('estilo do capítulo: citação rastreável, nenhum autor inventado, nenhum vocabulário de sistema, força refletida na prosa')
  }
}

// A clareza é logada SEPARADA da conformidade, e mesmo quando conforme. Se ela
// fosse só mais uma linha de divergencia, um relatório que passou raspando no
// script ficaria indistinguível de um que passou com folga — e é a folga que
// diz se o limite pode descer na próxima rodada.
if (revisao) {
  const e = revisao.estilo
  if (!e.script_rodou) {
    log('ATENÇÃO: a checagem objetiva de clareza NÃO rodou nesta revisão — os contadores abaixo não existem')
  } else {
    log(`clareza (script ${ESTILO.script}): ${e.frases_longas} frase(s) longa(s), ${e.termos_sem_glosa} termo(s) sem glosa, ${e.paragrafos_densos} parágrafo(s) denso(s)`)
  }
  if (e.prosa_opaca?.length || e.glossas_vazias?.length) {
    log(`clareza (julgamento do revisor): ${e.prosa_opaca?.length ?? 0} frase(s) opaca(s), ${e.glossas_vazias?.length ?? 0} glosa(s) vazia(s)`)
  }
}

return {
  status: (ranking && relatorio) ? 'completed' : 'partial',
  family: FAMILY.slug,
  reuso: REUSAR, // true = o registro da busca é de uma rodada anterior, não desta
  busca: {
    candidatos: busca.counts.total_unique_hits,
    passaram_regras: busca.counts.mechanical_gate_passers,
    selecionados: busca.counts.selected_with_pdf,
    reprovados_por_regra: busca.rejected_by_gate,
    nao_selecionados_com_motivo: busca.considered_not_selected,
  },
  contrato: conferencia ? { conforme: conferencia.conforms, divergencias: conferencia.divergencias } : null,
  fichas: fichas.length,
  por_grupo: porGrupo,
  ranking,
  relatorio: relatorio
    ? {
      arquivo: relatorio.arquivo,
      secoes: relatorio.secoes,
      claims_no_relatorio: relatorio.claims_no_relatorio,
      claims_sem_fonte: relatorio.claims_sem_fonte,
      fichas_citadas: relatorio.fichas_citadas.length,
      fichas_nunca_citadas: relatorio.fichas_nunca_citadas,
    }
    : null,
  revisao: revisao
    ? {
      conforme: revisao.conforme,
      claims_conferidas: revisao.claims_conferidas,
      claims_orfas: revisao.claims_orfas.length,
      numeros_divergentes: revisao.numeros_divergentes.length,
      citacoes_sem_ficha: revisao.citacoes_sem_ficha.length,
      autores_inventados: revisao.autores_inventados.length,
      vocabulario_proibido: revisao.vocabulario_proibido.length,
      forca_nao_refletida: revisao.forca_nao_refletida.length,
      veredictos_no_relatorio: revisao.veredictos_no_relatorio.length,
      estilo: revisao.estilo
        ? {
          script_rodou: revisao.estilo.script_rodou,
          frases_longas: revisao.estilo.frases_longas,
          termos_sem_glosa: revisao.estilo.termos_sem_glosa,
          paragrafos_densos: revisao.estilo.paragrafos_densos,
          prosa_opaca: revisao.estilo.prosa_opaca,
          glossas_vazias: revisao.estilo.glossas_vazias,
        }
        : null,
      divergencias: revisao.divergencias,
    }
    : null,
}