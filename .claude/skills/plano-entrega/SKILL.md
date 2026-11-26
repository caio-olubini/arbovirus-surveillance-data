---
name: plano-entrega
description: >-
  Maintains the ARBOILI delivery plan in `notes/plano.md`: the deadline, the
  order of work, the weekly slices, the cut points. Revise mode runs the weekly
  loop — measures the real repository state with `scripts/estado_do_plano.py`,
  compares it against the plan, reports what moved and what slipped, and proposes
  the next slice with its verifiable done-criterion. Replan mode rewrites the
  plan's structure when a decision is made (the set of models is defined, the
  deadline moves, a cut point fires). Use when the user says "como estamos",
  "o que eu faço essa semana", "atualiza o plano", "replanejar", "isso atrasou",
  "mudou o prazo", "fechando a semana", or when a week of work ends and the plan
  needs to be checked against reality. The plan is written in Brazilian
  Portuguese.
---

# Plano de entrega

Mantém `notes/plano.md`, o plano de entrega do paper. O critério: alguém que não
estava na conversa abre o plano e sabe **o que fica pronto nesta semana**, **como
vai saber que ficou pronto** e **o que fazer se não ficar**.

Os arquivos `notes/00` a `notes/05` dizem em que **estado** está cada frente de
pesquisa. Nenhum deles diz **quando** cada frente entra. Este plano é a única
camada do repositório com data.

**Escreva seguindo a seção "How to write here" do [`AGENTS.md`](../../../AGENTS.md).**
Ela vale para o plano, para os relatórios que ele gera e para as respostas no chat.
Vale em especial a regra de não usar metáfora como nome de coisa: o plano já foi
reescrito uma vez porque "escada", "degrau" e "piso" obrigavam o leitor a carregar
um glossário, e "piso" chegou a nomear duas coisas diferentes.

## A medição vem de fora, nunca da cabeça

O estado do repositório **não se lê de memória**. Rode primeiro:

```bash
uv run python scripts/estado_do_plano.py
```

Ele mede, sem opinar: quais provas de cada entrega existem, o que está no disco e
fora do git, o estado declarado de cada frente em `notes/`, os estágios do
avaliador em `src/forecast/`, as fichas de cada família de literatura, os produtos
em `data/`, e o que foi commitado na janela. A saída em `--json` existe para
consumir sem reinterpretar.

**Por que a separação é rígida.** Um agente que "lê o repositório" relata o que
esperava encontrar, e relata com a mesma confiança quando erra. Um
`Path.exists()` não tem expectativa. O que sobra para você é o que nenhuma medição
decide: **o que andou, o que não andou, e qual é a próxima entrega.**

## Modo: revisar

O ciclo semanal. É o modo padrão.

1. **Meça.** Rode o script. Não substitua esta etapa por leitura de arquivos: o
   valor dele é ser a mesma medição toda semana.
2. **Leia o plano** (`notes/plano.md`) inteiro — a tabela sozinha não basta.
3. **Compare e relate**, nesta ordem:
   - **A entrega da semana passada ficou pronta?** E ficou pronta mesmo: o
     artefato existe **e** o número dentro dele é o que a entrega prometia?
     Existir não é o mesmo que estar certo, e a diferença é o que se quer
     enxergar.
   - **O que entrou no git?** Trabalho que está no disco e fora do git não conta
     como progresso e pode se perder. Diga quantos arquivos estão nessa situação,
     e quais.
   - **O que está atrasado**, com o número de dias.
   - **Algum ponto de corte disparou?** Se disparou, a decisão já estava tomada.
     Leia no plano o que ela manda e siga, em vez de tentar a mesma coisa de novo.
   - **O que a próxima entrega desbloqueia.** Uma entrega que não desbloqueia nada
     é candidata a sair do plano.
4. **Proponha a entrega da semana**, em uma frase e com o critério de pronto:
   "sexta eu consigo te mostrar X". Se a entrega prevista no plano não for mais a
   certa diante do que andou, diga por quê e proponha outra.
5. **Escreva de volta, com confirmação.** Atualize no plano a data da versão e o
   estado das entregas. Nunca marque uma entrega como pronta só porque o arquivo
   existe: quem fecha a entrega é você, não o script.

## Modo: replanejar

Quando uma decisão é tomada — a lista de modelos ficou definida, o prazo mudou, um
ponto de corte disparou, uma frente mudou de escopo.

1. Meça do mesmo jeito.
2. **Reescreva a estrutura**, além da tabela: a ordem de dependências, o que fica
   de fora, a lista de entregas e os pontos de corte.
3. **Toda data que muda, muda com motivo escrito.** Uma data que se move sem
   motivo faz quem lê parar de confiar no plano e voltar a confiar na memória, que
   é justamente o que o plano veio substituir.
4. Deixe no arquivo o registro da decisão que motivou o replanejamento, com data.
   Um plano reescrito sem esse registro não explica por que a semana 7 mudou.

## Formato do plano

**O plano em vigor não tem essa tabela.** Desde 2026-11-20 `notes/plano.md` é uma
lista de passos preenchida à mão, com a confirmação de cada passo escrita na própria
linha (`confirma: caminho` ou `caminho#palavra`). O script que mede o plano
(`scripts/estado_do_plano.py`) lê avaliador, literatura e produtos normalmente, mas
procura as fatias numa tabela de colunas fixas que não existe mais — por isso a
seção FATIAS sai vazia e ele reporta `semana 0 de 0`. Isso é um descompasso
conhecido, não uma medida do plano.

A tabela abaixo é o formato que o leitor de fatias entende. Se uma reorganização
voltar a usar fatias medidas, é esta a forma; enquanto não voltar, não invente a
tabela só para a medição ter o que ler. Não existe teste no repositório que guarde
o formato do plano real — os testes de `scripts/estado_do_plano.py` montam planos
sintéticos em `tmp_path`.

| # | Fecha em | Fatia | Prova que fechou | Prosa |
|---|---|---|---|---|

- **`Fecha em`** — data absoluta `AAAA-MM-DD`. A semana é a unidade de trabalho; a
  data é o que torna a semana conferível.
- **`Prova que fechou`** — o caminho do artefato, entre crases. **Só caminho**: um
  trecho entre crases com espaço é ignorado pela medição, por escolha, para que
  prosa entre crases não vire uma falta. Aceita glob
  (`data/forecast/*metrics.parquet`).
- **`Prosa`** — a seção de texto escrita naquela semana. O plano busca **uma seção
  por semana**: com 12 h por semana, escrever é metade do trabalho, e escrever tudo
  no fim perde a voz. Fica vazia só nas semanas de arrumação e nas de meio período,
  e o plano diz quais são.

### O marcador de prova

`caminho#palavra` prova que o documento passou a **dizer** algo novo. A palavra
precisa ser uma que o documento **ainda não tem** — é isso que faz dela uma prova.
Antes de escrever um marcador no plano, confira que ele não existe no alvo:

```bash
grep -ci -- "comparados" notes/00-protocolo-comparacao.md   # tem que dar 0
```

Um marcador que já está no documento fecha a entrega no dia em que ela nasce, e a
medição inteira perde o sentido. O mesmo cuidado vale para um artefato que já
existe: prova que já era verdadeira não mede nada.

**Prova que está no disco e fora do git não fecha a entrega.** Ela aparece como ⚠️,
e a semana 0 de um plano costuma ser isso: colocar no git o que já
existe.

Fora da tabela, o plano carrega: prazo, tempo disponível, a pergunta do paper, o
desenho do experimento, a regra de comparação, o que fica de fora, a ordem de
dependências e os pontos de corte.

## Regras duras

- **Nunca invente o estado.** Rode a medição. Se não rodou, diga que não rodou.
- **Nunca mova o prazo em silêncio.** Data nova exige motivo escrito e a sua
  confirmação.
- **Artefato que existe não é entrega pronta.** O script vê o arquivo; ele não vê
  se o número dentro está certo. Quem fecha a entrega é você.
- **Entrega que atrasou duas vezes não ganha uma terceira tentativa.** Ela vira um
  ponto de corte: ou entra pela metade agora, ou sai do escopo com o corte
  declarado.
- **Datas absolutas** (`2027-02-19`), nunca "semana que vem".
- **Idioma:** português do Brasil, claro e direto, como o resto de `notes/`.
- **Não edite `notes/00`–`05`** por conta própria — o `**Estado:**` de cada frente
  é da skill `research-notes`. Diga o que mudou e proponha a atualização.
- **Não toque em `texts/` nem em `articles/`.** O plano aponta para eles; não os
  mantém.
