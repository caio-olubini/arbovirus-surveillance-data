---
name: research-notes
description: >-
  Maintains the ARBOILI research-idea tracker under `notes/`. Capture mode turns
  a loose idea or a literature finding into a new path file (or appends it to
  `notes/ideias-soltas.md` when it is not yet a path) and registers it in the
  `notes/README.md` index. Update mode changes a path's status
  (ideia → testando → decidido | descartado) and appends the evidence or the
  decision with a date, without rewriting the file. Use when the user says
  "anota essa ideia", "registra esse caminho", "atualiza o status do caminho 2",
  "isso vira nota de pesquisa", "guarda isso pra depois", "marca como
  descartado", or when a literature search or a conversation produces a research
  path worth tracking. Notes are written in Brazilian Portuguese, informal, one
  file per path.
---

# Research notes

Keeps `notes/` useful months later. The bar is simple: someone who was not in the
conversation must be able to read a path file and know **what it is**, **why it
matters**, **how to test it** and **what the next step is**. A note that fails
that bar is worse than no note.

Output language is **Brazilian Portuguese**, informal. Technical terms stay in
English when that is the established name (`early fusion`, `pooling`, `lead-lag`,
`rolling-origin`).

## Layout

```
notes/
├── README.md                  ← index; the source of truth for what exists
├── 00-protocolo-comparacao.md ← shared ground for the competing paths
├── NN-<slug>.md               ← one file per research path
└── ideias-soltas.md           ← inbox for ideas that are not paths yet
```

`notes/` is for working ideas. It is **not** `texts/` (manuscript prose) and
**not** `articles/references.csv` (curated bibliography). Do not move content
between them unless asked.

## Mode: capture

Triggered by a loose idea, a literature finding, or an explicit "anota isso".

1. **Decide the destination.**
   - Has a hypothesis and a way to test it → new path file `NN-<slug>.md`.
   - Just an observation, a maybe, a tangent → append to `ideias-soltas.md`.
   When unsure, ask. Do not inflate an idea into a path to look productive.
2. **Number it.** Next free `NN`, zero-padded, after the highest existing one.
   Never renumber an existing file — the numbers are referenced in conversation.
3. **Write the file** using the template below. Fill every section. If a section
   is genuinely unknown, write the question instead of leaving it blank.
4. **Register it** in the `notes/README.md` index table with its role and status.
5. **Cross-link.** Add relative markdown links (`[00](00-protocolo-comparacao.md)`)
   to related paths, and add a reciprocal line in those files when the
   relationship is real.

## Mode: update

Triggered by "o caminho 2 avançou", "isso não deu certo", "marca como descartado",
or when new evidence lands.

1. Read the file first.
2. Change the `**Estado:**` line **and append the date**:
   `**Estado:** testando — 2026-11-02`.
3. Append the new evidence or the reason for the decision in the relevant
   section. **Never delete the old reasoning** — a discarded path with its reason
   recorded is more valuable than a clean file.
4. Update the index row in `notes/README.md`.
5. If the state becomes `decidido` or `descartado`, add one line saying what the
   decision was and what it implies for the other paths.

## Template for a path file

```markdown
# NN — <nome do caminho>

**Estado:** ideia | testando | decidido | descartado — AAAA-MM-DD
**Papel no artigo:** concorrente | corredor por fora | apoio (ver 00)

## Hipótese
O que este caminho afirma e por que isso deveria ajudar a prever dengue.

## O que produz
As features concretas, com o grão (UF × EW), e como entram no modelo.

## Como testar
Passos numerados. O que precisa existir antes.

## Evidência
O que a literatura mostra, com o que exatamente cada trabalho demonstra.
Separar **evidência a favor** de **contra-evidência** — a segunda é obrigatória.

## Custo
Esforço, dependências, tempo, GPU. Comparável com os outros caminhos.

## Refs a registrar em `articles/references.csv`
Lista de DOIs.

## Pendências / próximo passo
Checklist. É a seção que mais importa ao retomar.
```

## Hard rules

- **Never invent a citation.** Every reference must be real and verifiable. If a
  DOI or venue was not confirmed, say so inline: `(**não verificado** — checar)`.
  A plausible-looking fabricated reference poisons the whole tracker.
- **Never leave a path file without a `Pendências` section.** It is what makes the
  note resumable.
- **Dates are absolute** (`2026-10-07`), never "hoje" or "semana passada".
- **Contra-evidência is mandatory.** A path note that only lists supporting work
  is advocacy, not research.
- Do not touch `texts/`, `articles/references.csv`, or `AGENTS.md` from this
  skill unless the user explicitly asks in that turn.
