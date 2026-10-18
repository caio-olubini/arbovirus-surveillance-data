// gt-alignment — braço didático: 2 steps de pesquisa separados por um gate.
//
//   Step 1 (Executar)  roda o transform e reporta o que MEDIU
//   Gate   (Gate)      um agente independente tenta REFUTAR o step 1
//   Step 2 (Concluir)  só roda se o gate passar
//
// A pergunta de pesquisa do step 2 é do protocolo do projeto: o AGENTS.md diz que
// tudo é "aligned temporally for surveillance modeling". Se a série do Google
// Trends não cobrir as mesmas semanas que o SINAN, o modelo não tem o que alinhar.
// Mas essa resposta só vale se o step 1 tiver produzido um artefato íntegro — é
// exatamente isso que o gate existe para decidir.

export const meta = {
  name: 'gt-alignment',
  description: 'Transform gtrends (step 1) → gate de integridade → alinhamento temporal com SINAN (step 2)',
  whenToUse: 'Exemplo didático de workflow com gate: o step 2 não roda se o artefato do step 1 não reproduzir o contrato declarado.',
  phases: [
    { title: 'Executar', detail: 'uv run arboili transform gtrends' },
    { title: 'Gate', detail: 'verificador independente tenta refutar o artefato' },
    { title: 'Concluir', detail: 'alinhamento GT × SINAN por semana epidemiológica' },
  ],
}

// --- o contrato -------------------------------------------------------------
// Congelado aqui de propósito. Um gate só é um gate se o critério for declarado
// ANTES e independente do que o step 1 reporta — senão ele só confirma o que já
// ouviu. Estes números vêm do AGENTS.md §Checkout State e foram reconferidos
// contra o disco antes de escrever este script.
const CONTRACT = {
  rows: 216720,
  weeks: 258,
  first_week: '2020-01-26',
  last_week: '2024-12-29',
  locations: 28, // 27 UFs + BR
  columns: ['ew', 'state_abbrev', 'topic', 'value'],
}

const STEP1_SCHEMA = {
  type: 'object',
  properties: {
    command: { type: 'string' },
    exit_code: { type: 'integer' },
    rows: { type: 'integer' },
    weeks: { type: 'integer' },
    first_week: { type: 'string' },
    last_week: { type: 'string' },
    locations: { type: 'integer' },
    topics: { type: 'integer' },
    columns: { type: 'array', items: { type: 'string' } },
    non_sunday_weeks: { type: 'integer' },
    outputs: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
  },
  required: [
    'command', 'exit_code', 'rows', 'weeks', 'first_week', 'last_week',
    'locations', 'topics', 'columns', 'non_sunday_weeks', 'outputs', 'summary',
  ],
}

const GATE_SCHEMA = {
  type: 'object',
  properties: {
    refuted: { type: 'boolean' },
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
    reason: { type: 'string' },
  },
  required: ['refuted', 'checks', 'reason'],
}

const STEP2_SCHEMA = {
  type: 'object',
  properties: {
    gt_weeks: { type: 'integer' },
    sinan_weeks_in_window: { type: 'integer' },
    weeks_in_both: { type: 'integer' },
    weeks_gt_only: { type: 'integer' },
    weeks_sinan_only: { type: 'integer' },
    joint_window: { type: 'string' },
    joint_locations: { type: 'integer' },
    note: { type: 'string' },
  },
  required: [
    'gt_weeks', 'sinan_weeks_in_window', 'weeks_in_both', 'weeks_gt_only',
    'weeks_sinan_only', 'joint_window', 'joint_locations', 'note',
  ],
}

// --- step 1 -----------------------------------------------------------------
phase('Executar')
log('step 1/2 — regenerando GoogleTrends_search_EW a partir do CSV de origem')

const step1 = await agent(
  `Você está no repositório arbovirus-surveillance-data. Execute exatamente este comando, a partir da raiz do repo:

    uv run arboili transform gtrends

É um rename/validate fino: lê data/google_trends/GoogleTrends_search.csv e escreve data/google_trends/GoogleTrends_search_EW.parquet (+ .csv.gz). Leva segundos.

Depois leia o parquet produzido com polars e reporte os fatos do schema, todos medidos por você:
- rows, weeks (n_unique de 'ew'), first_week, last_week (min/max de 'ew')
- locations (n_unique de 'state_abbrev'), topics (n_unique de 'topic')
- columns, na ordem publicada
- non_sunday_weeks: quantas datas distintas de 'ew' NÃO caem em domingo
- outputs: os caminhos dos arquivos que o comando escreveu

Reporte o que você MEDIU, não o que você esperava encontrar. Se algum número divergir de um valor plausível, reporte o medido de qualquer forma e diga na summary. Não edite nenhum arquivo além dos que o próprio comando escreve; não conserte nada.`,
  { label: 'step1:transform', phase: 'Executar', schema: STEP1_SCHEMA },
)

if (!step1) {
  return { status: 'aborted', reason: 'o step 1 não retornou resultado (agente morto ou pulado)' }
}

log(`step 1 mediu ${step1.rows} linhas / ${step1.weeks} semanas / ${step1.locations} locations`)

// --- o gate -----------------------------------------------------------------
// O verificador recebe as afirmações do step 1, mas a instrução é para refutá-las
// lendo os arquivos por conta própria. Ele não confia no relatório: ele re-mede.
phase('Gate')
log('gate — verificador independente vai tentar refutar o artefato do step 1')

const gate = await agent(
  `Você é um verificador ADVERSARIAL. Sua tarefa é REFUTAR a afirmação de que o artefato do Google Trends é um transform fiel e completo. Procure ativamente o erro; não confirme por educação.

A afirmação a testar (relatada por outro agente, que pode ter errado ou alucinado):
${JSON.stringify(step1, null, 2)}

O contrato declarado, congelado antes da execução, está em AGENTS.md §"Checkout State" e nos specs do módulo:
${JSON.stringify(CONTRACT, null, 2)}

Verifique, MEDINDO VOCÊ MESMO (não confie no JSON acima):
1. rows — leia data/google_trends/GoogleTrends_search_EW.parquet
2. weeks, first_week, last_week — min/max/n_unique de 'ew'
3. locations e topics — n_unique de 'state_abbrev' e 'topic'
4. columns — a ordem publicada deve ser exatamente a do contrato
5. todas as datas de 'ew' caem em domingo (dica: polars dt.weekday(), 7 = domingo)
6. INVARIANTE ESTRUTURAL: a tabela é o produto cartesiano completo? Ou seja,
   rows == weeks × locations × topics. Se não for, há buracos (combinações
   semana×local×tópico faltando) e o transform NÃO é completo.
7. FIDELIDADE À ORIGEM: leia também data/google_trends/GoogleTrends_search.csv e
   confirme que o parquet é um rename/validação dessa origem — mesmas contagens de
   linhas e de locations, e nenhuma linha inventada. Cheque o manifest
   data/google_trends/manifest_search.csv: o contrato diz 840/840 requests 'ok'.
8. Números do step 1 vs. seus: alguma divergência entre o que ele relatou e o que
   você mediu é motivo suficiente para refutar.

Regras de decisão:
- refuted=true se QUALQUER check falhar.
- refuted=true se você não conseguir verificar algo (dúvida → refutado). Nunca
  presuma que passou.
- reason: uma frase. Se refutado, diga o que exatamente quebrou.
Um check que não roda é um check que não passou.`,
  { label: 'gate:verify', phase: 'Gate', schema: GATE_SCHEMA, effort: 'high' },
)

if (!gate) {
  return { status: 'aborted', step1, reason: 'o gate não retornou veredito' }
}

for (const c of gate.checks ?? []) {
  log(`  [${c.passed ? 'PASS' : 'FAIL'}] ${c.name}: ${c.detail}`)
}

// AQUI está o gate. Sem passar, o step 2 não roda — e o motivo importa mais que
// o silêncio: um workflow que só para sem explicar é indistinguível de um bug.
if (gate.refuted) {
  log(`GATE FECHADO — step 2 não vai rodar: ${gate.reason}`)
  return {
    status: 'blocked',
    gate_reason: gate.reason,
    gate_checks: gate.checks,
    step1,
    step2: null,
  }
}

log('GATE ABERTO — liberando o step 2')

// --- step 2 -----------------------------------------------------------------
phase('Concluir')
log('step 2/2 — alinhamento temporal GT × SINAN (a pergunta de pesquisa)')

const step2 = await agent(
  `O gate liberou o artefato. Agora responda a pergunta de pesquisa.

Contexto: o objetivo do projeto exige que as fontes sejam "aligned temporally for surveillance modeling", estratificadas por UF. A série do Google Trends é a mais curta; ela define o teto do que pode ser modelado conjuntamente. Sua tarefa é medir esse teto.

Meça com polars (você mesmo, lendo os arquivos):
- gt: data/google_trends/GoogleTrends_search_EW.parquet (colunas: ew, state_abbrev, topic, value)
- sinan: data/epidemiological/SINAN/SINAN_dengue_cases.parquet (colunas incluem ew_notification e ew_symptom_onset, ambas datas ancoradas em domingo; use ew_notification)

Reporte:
- gt_weeks: semanas distintas no GT
- sinan_weeks_in_window: semanas distintas do SINAN dentro da janela do GT [min(gt.ew), max(gt.ew)]
- weeks_in_both: semanas presentes nos dois
- weeks_gt_only: semanas do GT ausentes do SINAN
- weeks_sinan_only: semanas do SINAN, dentro da janela do GT, ausentes do GT
- joint_window: a janela conjunta como "YYYY-MM-DD → YYYY-MM-DD"
- joint_locations: quantas locations têm AMBAS as séries (interseção dos conjuntos de state_abbrev; o SINAN usa abreviações de UF, o GT tem 27 UFs + 'BR')
- note: 2-3 frases. Diga se a série do GT é contígua dentro da própria janela (258 semanas entre 2020-01-26 e 2024-12-29 dão ~257 dias de intervalo — verifique, não presuma) e o que isso implica para o alinhamento.

Números medidos, não esperados. Se algo surpreender, diga na note.`,
  { label: 'step2:alignment', phase: 'Concluir', schema: STEP2_SCHEMA },
)

return {
  status: step2 ? 'completed' : 'partial',
  gate_reason: gate.reason,
  gate_checks: gate.checks,
  step1,
  step2,
}
