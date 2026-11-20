---
name: plano-entrega
description: >-
  Maintains the ARBOILI delivery plan in `notes/plano.md`: the deadline, the
  critical path, the weekly slices, the cut points. Revise mode runs the weekly
  loop — measures the real repository state with `scripts/estado_do_plano.py`,
  compares it against the plan, reports what moved and what slipped, and proposes
  the next slice with its verifiable done-criterion. Replan mode rewrites the
  plan's structure when a decision lands (the experiment grid gets defined, the
  deadline moves, a cut point fires). Use when the user says "como estamos",
  "o que eu faço essa semana", "atualiza o plano", "replanejar", "isso atrasou",
  "mudou o prazo", "fechando a semana", or when a week of work ends and the plan
  needs to be checked against reality. The plan is written in Brazilian
  Portuguese.
---

# Plano de entrega

Mantém `notes/plano.md`, o plano de entrega do paper. O barômetro: alguém que
não estava na conversa abre o plano e sabe **o que fecha nesta semana**, **como
vai saber que fechou** e **o que fazer se não fechar**.

Este plano existe por um motivo específico: os caminhos em `notes/00`–`05` dizem
o **estado** de cada frente de pesquisa, e nada neles diz **quando**. Frente de
pesquisa não tem prazo; entrega tem. O plano é a única camada com data.

## A medição vem de fora, nunca da cabeça

O estado do repositório **não se lê de memória**. Rode primeiro:

```bash
uv run python scripts/estado_do_plano.py
```

Ele mede, sem opinar: quais artefatos de cada fatia existem, o que está no disco
e fora do git, o estado declarado de cada caminho, os estágios da régua, as
fichas de cada família de literatura, os produtos em `data/`, e o que foi
commitado na janela. A saída em `--json` existe para você consumir sem
reinterpretar.

**Por que a separação é rígida.** Um agente que "lê o repositório" relata o que
esperava encontrar, e relata com a mesma confiança quando erra. Um
`Path.exists()` não tem expectativa. O que sobra para você é o que nenhuma
medição decide: **o que andou, o que não andou, e qual é a próxima fatia.**

## Modo: revisar

O laço semanal. É o modo padrão.

1. **Meça.** Rode o script. Não pule esta etapa nem a substitua por leitura de
   arquivos: o valor dele é ser a mesma régua toda semana.
2. **Leia o plano** (`notes/plano.md`) inteiro, não só a tabela.
3. **Compare e relate**, nesta ordem:
   - **A fatia da semana passada fechou?** E fechou de verdade — o artefato
     existe **e** o número dentro dele é o que a fatia prometia? Existir não é o
     mesmo que estar certo, e a diferença é justamente o que se quer enxergar.
   - **O que entrou no git?** Trabalho no disco e fora do git não conta como
     progresso e está em risco de se perder. Diga quantos arquivos estão nessa
     situação, e quais.
   - **O que está atrasado**, com o número de dias.
   - **Algum ponto de corte disparou?** Se disparou, a decisão já estava tomada
     — leia-a no plano e siga o que ela manda, em vez de tentar de novo.
   - **O que a próxima fatia desbloqueia.** Uma fatia que não desbloqueia nada é
     candidata a sair.
4. **Proponha a fatia da semana**, em uma frase e com o critério de pronto:
   "sexta eu consigo te mostrar X". Se a fatia do plano não for mais a certa
   face ao que andou, diga por quê e proponha outra.
5. **Escreva de volta, com confirmação.** Atualize no plano a data do snapshot e
   o estado das fatias. Nunca marque uma fatia como concluída apenas porque o
   arquivo existe — a conclusão é sua palavra, não do script.

## Modo: replanejar

Quando uma decisão cai — a grade de experimentos ficou definida, o prazo mudou,
um ponto de corte disparou, um caminho mudou de escopo.

1. Meça do mesmo jeito.
2. **Reescreva a estrutura**, não só a tabela: o caminho crítico, a linha de
   corte, a lista de fatias e os pontos de corte.
3. **Toda data que muda, muda com motivo escrito.** Prazo que se move em
   silêncio é o começo do fim de um plano: quem lê deixa de confiar na data e
   passa a confiar na memória, que é o que o plano veio substituir.
4. Deixe no arquivo o registro da decisão que motivou o replanejamento, com
   data. Um plano reescrito sem rastro não explica por que a semana 7 mudou.

## Formato do plano

O script lê a tabela de fatias, então ela tem colunas fixas. Alterar a coluna
`Fecha em` ou `Prova que fechou` quebra a medição — e o teste
`tests/scripts/test_estado_do_plano.py::test_o_plano_real_do_repositorio_ainda_e_legivel`
existe para avisar disso.

| # | Fecha em | Fatia | Prova que fechou | Prosa |
|---|---|---|---|---|

- **`Fecha em`** — data absoluta `AAAA-MM-DD`. A semana é a unidade; a data é o
  que torna a semana conferível.
- **`Prova que fechou`** — o caminho do artefato, entre crases. **Só caminho**:
  um trecho entre crases com espaço é ignorado pela medição, de propósito, para
  que prosa em crase não vire "falta". Aceita glob (`data/forecast/*metrics.parquet`).
- **`Prosa`** — a seção de texto que anda em paralelo naquela semana. O plano
  busca **uma seção escrita por semana**: com 12 h/semana, escrever é metade do
  trabalho, e um texto corrido no fim é onde a voz se perde. Fica vazia só nas
  semanas de arrumação e nas de meio período, e o plano diz quais são.

O **marcador** (`caminho#marcador`) precisa ser uma palavra que o documento
**ainda não tem** — é isso que faz dele prova de que algo novo foi dito. Antes de
escrever um marcador no plano, confira que ele não existe no alvo:

```bash
grep -ci -- "degrau" notes/00-protocolo-comparacao.md   # tem que dar 0
```

Um marcador que já está no documento fecha a fatia no dia em que ela nasce, e a
medição inteira perde o sentido. O mesmo cuidado vale para um artefato que já
existe: prova que já era verdadeira não mede nada.

**Uma prova no disco e fora do git não fecha a fatia.** Ela aparece como ⚠️, e a
fatia 0 de um plano costuma ser exatamente isso — landar o que já existe.

Fora da tabela, o plano carrega: prazo, orçamento de horas, a afirmação do
paper, a linha de corte, o caminho crítico com as dependências, e os pontos de
corte.

## Regras duras

- **Nunca invente o estado.** Rode a medição. Se não rodou, diga que não rodou.
- **Nunca mova o prazo em silêncio.** Data nova exige motivo escrito e sua
  confirmação.
- **Artefato que existe não é fatia concluída.** O script vê o arquivo; ele não
  vê se o número dentro está certo. Quem fecha a fatia é você.
- **Fatia que escorregou duas vezes não ganha uma terceira tentativa** — ela vira
  um ponto de corte: ou entra pela metade agora, ou sai do escopo com o corte
  declarado. Plano que reenfileira a mesma fatia para sempre não é plano.
- **Datas absolutas** (`2027-02-19`), nunca "semana que vem".
- **Idioma:** português do Brasil, informal, como o resto de `notes/`.
- **Não edite `notes/00`–`05`** por conta própria — o `**Estado:**` de cada
  caminho é da skill `research-notes`. Diga o que mudou e proponha a atualização.
- **Não toque em `texts/` nem em `articles/`.** O plano aponta para eles; não
  os mantém.
