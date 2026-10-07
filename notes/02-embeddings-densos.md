# 02 — Embeddings densos de sentença + pooling por semana epidemiológica

**Estado:** ideia — 2026-10-07
**Papel no artigo:** representação concorrente (ver [00](00-protocolo-comparacao.md))

## Hipótese

Um encoder pré-treinado captura o significado do artigo inteiro, incluindo o que
o léxico perde (paráfrase, ironia, contexto político, menção indireta). A média
dos embeddings dos artigos de uma semana é uma representação da "semana
informativa" que o modelo consegue consumir como covariável densa.

## O que produz

Por UF (ou BR) × EW:

- `emb_mean[ew]` — média (ou max-pool) dos embeddings dos artigos da semana.
- `emb_std[ew]` — dispersão; semana com artigos heterogêneos ≠ semana homogênea.
- `no_news[ew]` — indicador binário de semana sem artigo. **Obrigatório**: sem ele
  o modelo não distingue "sem notícia" de "notícia neutra".

Dimensão típica 384–1024. Se ficar largo demais para o backbone, reduzir com PCA
(registrar variância explicada) — mas isso é decisão de modelagem, não de representação.

## Como testar

1. Extrair o texto dos HTMLs.
2. Codificar cada artigo com o encoder escolhido (uma passada, sem fine-tuning
   no braço base — fine-tuning vira sub-experimento, ver pendências).
3. Agregar por EW.
4. Rodar o protocolo 00, **incluindo o controle negativo** (texto embaralhado).

## Evidência

- **Encoder PT-BR.** BERTimbau é o padrão da língua e casa com notícia geral
  (pré-treinado no brWaC, corpus web).
  [Souza 2020, BRACIS, LNCS 12319](https://doi.org/10.1007/978-3-030-61377-8_28).
  Variante biomédica (vocabulário clínico, mas treinada em nota clínica e
  abstract SciELO/PubMed, **não** em notícia):
  [Schneider 2020, BioBERTpt, ClinicalNLP](https://doi.org/10.18653/v1/2020.clinicalnlp-1.7).
  Alternativas multilíngues para comparação: E5 multilíngue, BGE-M3.
- **Benchmark pronto para validar a fusão antes do seu corpus.**
  [Liu 2024, *Time-MMD*, NeurIPS D&B, arXiv:2406.08627](https://arxiv.org/abs/2406.08627):
  9 domínios incluindo Saúde, texto alinhado a cada timestep, ganho reportado de
  >15% de MSE (até 40% em domínios ricos em texto). Usar para separar
  "a fusão funciona?" de "o sinal de dengue existe?".
- **Fusão que dá certo com texto defasado.** DSA acopla encoder numérico e encoder
  de manchete por atenção cruzada bidirecional; a direção texto→numérico é a mais
  forte e o texto é tratado como ruidoso e defasado.
  Hashemi 2026, arXiv:2608.23373 (recente — confirmar versão final).
  [Liu 2024, CALF, arXiv:2403.07300](https://arxiv.org/abs/2403.07300) é a variante
  de fine-tuning cruzado.

**Contra-evidência que precisa estar no artigo:**
[Tan 2024, NeurIPS, arXiv:2406.16964](https://arxiv.org/abs/2406.16964) — ablaciona
o LLM fora de Time-LLM/GPT4TS/CALF em 13 datasets: remover empata ou melhora, a
custo ordens de magnitude menor; re-inicializar aleatoriamente ≈ pré-treinado.
Existe também uma auditoria de 2026 argumentando que o ganho de texto multimodal
muitas vezes desaparece quando se remove uma coluna numérica co-empacotada
(arXiv:2608.22321 — **não verificado**, checar antes de citar). O controle negativo
do protocolo 00 existe exatamente por causa disso.

## Custo

Médio-baixo. Uma passada de inferência sobre 4.569 artigos é trivial (minutos em
GPU, dezenas de minutos em CPU). Sem rotulagem. O custo escondido é o download do
modelo e a reprodutibilidade (fixar versão/revisão do checkpoint).

## Pendências / próximo passo

- [ ] Escolher o encoder primário (BERTimbau é o palpite) e o comparador.
- [ ] Decidir: pooling por média, max, ou atenção aprendida?
- [ ] Vale fine-tuning no corpus (classificação de relevância) ou o braço fica
      congelado? Fine-tuning muda a natureza do braço — decidir antes de comparar.
- [ ] Testar no Time-MMD Health antes de ir para dengue.
