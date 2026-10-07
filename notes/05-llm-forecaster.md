# 05 — LLM como forecaster / agente

**Estado:** ideia — 2026-10-07
**Papel no artigo:** corredor por fora (ver [00](00-protocolo-comparacao.md))

## Hipótese

Em vez de virar feature para um modelo clássico, o texto entra **direto** no
processo de previsão: embeddings de LLM alimentam uma cabeça de previsão, ou o
próprio LLM recebe a série serializada como texto e prevê. A pergunta é se o
conhecimento semântico do modelo sobre "o que a notícia está dizendo" agrega
algo que uma covariável numérica não agrega.

## O que produz

Depende do desenho, e isso é parte do problema — não há uma saída canônica:

- **Reprogramação:** série numérica → tokens → backbone de LLM congelado com
  camadas de projeção treináveis (Time-LLM, GPT4TS, AutoTimes).
- **Prompt:** série serializada em texto → o LLM responde com a previsão
  (LLMTime, PromptCast).
- **Raciocínio multimodal:** o LLM recebe epidemia + política + genômica +
  demografia como texto e devolve uma classe ordinal (PandemicLLM).
- **Agente/RAG:** recupera notícias recentes, resume, alimenta o LLM que prevê.

## Como testar

Não tem como testar isso antes de o baseline "sem texto" e pelo menos um braço
de representação existirem. A ordem é: protocolo 00 → baseline sem texto →
01/02/03 → só então 05.

## Evidência

- **A favor, e é forte:** [Du 2025, *Nat Comput Sci* 5:467](https://doi.org/10.1038/s43588-025-00798-6)
  (PandemicLLM): reformula a previsão como raciocínio em texto sobre múltiplos
  fluxos; backbone LLaMA2 + representação temporal recorrente; previsão ordinal
  de tendência de hospitalização em 50 estados dos EUA; **bateu os melhores
  modelos do CDC CovidHub**, especialmente em mudanças de variante e de política.
  É a evidência peer-reviewed mais forte para LLM em previsão epidêmica.
- [Gruver 2023, NeurIPS, arXiv:2310.07820](https://arxiv.org/abs/2310.07820)
  (LLMTime): tokeniza a série como dígitos espaçados e prevê por next-token;
  zero-shot empata com modelos dedicados. Seminal para previsão zero-shot.
- [Jin 2024, ICLR, Time-LLM](https://arxiv.org/abs/2310.01728) e
  [Zhou 2023, NeurIPS, GPT4TS](https://arxiv.org/abs/2302.11939): reprogam um LLM
  congelado e ficam competitivos em forecasting/classificação/anomalia.
- **Foundation models de série temporal** (não são LLMs de linguagem):
  [Ansari 2024, Chronos, *TMLR*](https://arxiv.org/abs/2403.07815),
  [Das 2024, TimesFM, ICML](https://arxiv.org/abs/2310.10688). Vale citar para
  separar "LLM" de "modelo de fundação de série temporal" — são coisas diferentes
  e a literatura às vezes confunde.

**Contra-evidência que precisa estar no artigo — e é a mais forte de todas:**

- [Tan 2024, NeurIPS, arXiv:2406.16964](https://arxiv.org/abs/2406.16964):
  ablaciona o LLM fora de Time-LLM/GPT4TS/CALF em 13 datasets. Remover o LLM
  **empata ou melhora** a acurácia, a custo ordens de magnitude menor;
  re-inicializar os pesos aleatoriamente ≈ usar os pré-treinados; embaralhar a
  entrada quase não muda a saída. Ou seja: o LLM pode não estar fazendo nada.
- O consenso de 2026 é **dividido**, e o artigo deve reportar assim. A evidência
  positiva concentra-se em cenários com **poucos dados, semanticamente ricos e
  específicos de epidemiologia** — que é exatamente o seu caso, mas isso significa
  que o componente LLM precisa ser justificado **empiricamente**, não por analogia.

## Custo

O mais alto dos cinco caminhos. Dependência pesada, treino, e a maldição de
reprodução: trocar o modelo invalida o experimento inteiro.

## Riscos

- **Vazamento temporal, agudo aqui.** O corpus vai até 2026 e qualquer LLM
  pré-treinado depois de 2015 pode "conhecer" os desfechos — inclusive o recorde
  de dengue de 2024. Mitigação: prompt restrito à data, modelo com corte
  conhecido, e idealmente avaliar em janela anterior ao corte.
- **Reprodutibilidade.** Inferência hospedada é não-determinística mesmo a
  temperatura 0; modelos são aposentados. Um levantamento de 2026 achou que 41,6%
  dos modelos citados em artigos de IA biomédica têm aposentadoria confirmada em
  até 730 dias (arXiv:2609.04699 — **não verificado**).
- **Conclusão negativa é resultado.** Se o LLM não agregar, isso é publicável e
  honesto — desde que o controle negativo exista para provar que o teste foi justo.

## Refs a registrar em `articles/references.csv`

`10.1038/s43588-025-00798-6` · `arXiv:2310.07820` · `arXiv:2310.01728` ·
`arXiv:2302.11939` · `arXiv:2403.07815` · `arXiv:2310.10688` · `arXiv:2406.16964`

## Pendências / próximo passo

- [ ] Decidir se este caminho entra no escopo da dissertação ou fica como trabalho
      futuro. É o de pior relação valor/esforço.
- [ ] Se entrar: escolher entre reprogramação, prompt ou raciocínio multimodal —
      são experimentos diferentes, não variantes do mesmo.
- [ ] Definir o protocolo de vazamento antes de escrever qualquer prompt.
