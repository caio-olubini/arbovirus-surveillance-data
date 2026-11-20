# As famílias de técnicas, em arquivo

Cada `.json` aqui é a entrada de uma rodada do
[`../reference-research.js`](../reference-research.js): o recorte de escopo, as
consultas de busca, os eixos do relatório e a lista de jargão daquela família.

## Por que estes arquivos existem

Até 2026-11-10 eles não existiam. Cada rodada recebia a configuração da família
como argumento avulso, e depois que a rodada acabava a configuração sumia junto
com a conversa — sobrava o produto (`articles/<slug>/relatorio.md`,
`search.json`, os PDFs) e não sobrava o que o produziu. A consequência prática
apareceu quando foi preciso rerodar as famílias com o esquema novo de fichas:
as três configurações das famílias já rodadas tiveram que ser **garimpadas do
histórico de conversas**, e uma delas teria sido irrecuperável se a conversa
tivesse sido apagada.

Configuração que só existe no histórico do chat não é configuração: é memória.
Estes arquivos são a parte que se versiona.

## Como rerodar uma família

O `args` da chamada é o conteúdo do arquivo, mais `reuse_search`. Com
`reuse_search: true` a fase Buscar **não busca nada**: ela carrega o
`articles/<slug>/search.json` que já está no disco e segue dali. É o que torna
a rerodada barata — os PDFs e o resultado da busca são reaproveitados, e o que
roda de novo é a leitura, a conferência das fichas, o ranking e a prosa.

```
Workflow({
  scriptPath: '.claude/workflows/reference-research.js',
  args: { ...require('./familias/llm-extracao.json'), reuse_search: true },
})
```

**Lance por `scriptPath`, não por `name`.** `Workflow({ name })` roda uma cópia
em cache do script, e a cópia em cache é de antes da última edição — o sintoma é
a rodada se comportar como a versão antiga sem avisar.

O que a rerodada produz de novo, além do que já existia: `articles/<slug>/fichas/`,
uma ficha por artigo, cada afirmação ancorada numa citação literal com página, e
a fase Conferir fichas provando que cada citação existe no PDF. Essa pasta é o
ativo durável — a prosa é renderização dela.

## O que cada família é

| Arquivo | Família | Artigos selecionados |
|---|---|---|
| `llm-extracao.json` | Extração estruturada de eventos por LLM | 10 |
| `embeddings.json` | Embeddings densos como feature de notícia | 23 |
| `features-texto.json` | Features manuais: léxico, regras e contagens | 35 |
| `topicos.json` | Modelagem por tópicos como feature de notícia | 48 |

`embeddings.json` ainda não está aqui: aquela família é a `DEFAULT_FAMILY` do
workflow, então rodá-la é rodar sem `args` de família. Quando ela for rerodada
com o esquema novo, vale copiar a configuração para cá também, para que as
quatro fiquem no mesmo lugar.

## O `estilo` de cada uma

A chave `estilo.termos` é a lista de jargão **daquela** família, e é o que o
workflow passa para o `scripts/checar_estilo_relatorio.py`. `pooling` é jargão
para a família de embeddings e não seria para a de tópicos; por isso a lista é
da família e não do script. Os LIMITES, ao contrário, ficam no script, porque
são sobre prosa em português e valem para qualquer tema.
