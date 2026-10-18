# 02 — Embeddings densos de sentença + pooling por semana epidemiológica

**Estado:** testando — 2026-10-14
**Papel no artigo:** representação concorrente (ver [00](00-protocolo-comparacao.md))
**Implementação:** `src/pipeline/news/embeddings/` — roda via
`uv run arboili transform news-embeddings` (extra opcional `embeddings`). Métodos,
números medidos e limitações em `src/pipeline/news/README.md` §3.

## Hipótese

Um encoder pré-treinado captura o significado do artigo inteiro, incluindo o que
o léxico perde (paráfrase, ironia, contexto político, menção indireta). A média
dos embeddings dos artigos de uma semana é uma representação da "semana
informativa" que o modelo consegue consumir como covariável densa.

## O que produz

Por UF (ou BR) × EW, **por configuração do bracket**:

- `emb_mean[ew]` — média dos embeddings dos artigos da semana (768 ou 1024 dims).
- `n_articles[ew]` — quantos artigos entraram na linha.
- `no_news[ew]` — indicador de semana sem artigo. **Obrigatório**: sem ele o modelo
  não distingue "sem notícia" de "notícia neutra".

Duas tabelas por configuração, porque o pooling é com perda e é ele que custa a
inferência: `..._article` (uma linha por artigo, com `n_tokens`) e `..._EW`
(agregada). Re-agregar da primeira leva segundos; recodificar é a run inteira. A
configuração base mantém os nomes sem sufixo — é a tabela publicada do braço 02.

`no_news` não é coluna — é a **ausência** da linha, a mesma convenção do braço 01
(ver `pool_by_week` em `steps.py`). Um vetor zero é um ponto real do espaço e se
leria como "notícia que não significa nada", não como "sem notícia"; a ausência o
modelo já sabe tratar, porque é assim que o calendário do alvo funciona.

## `emb_std` foi removido, não consertado (2026-10-14)

A coluna de dispersão saiu do schema. O motivo não é o "59,8% indefinido" que
estava registrado aqui antes — esse era **sintoma**, não defeito.

Para vetores unitários, a identidade do eixo paralelo na esfera dá

    ‖std‖² = (1/n) Σᵢ ‖vᵢ − m‖² = 1 − ‖m‖²

ou seja, a norma do desvio por dimensão é uma **função determinística exata** de
`emb_mean`, que a tabela já carrega. Verificado nas tabelas reais: desvio máximo
de 1,6e-06 sobre as 2.073 linhas com n > 1. A coluna não acrescentava informação
nenhuma, e "indefinida em 59,8% das linhas" é o mesmo fato lido de outro ângulo —
um artigo dá ‖m‖ = 1 e portanto exatamente 0.

Nenhuma dispersão escalar de vetores unitários escapa disso: a distância de cosseno
média entre pares também é 1 − ‖m‖². Por isso a hipótese de dispersão passou a ser
lida como **absorvida pela média**, e não como um recurso próprio a ser recuperado.
O `corr(n_articles, emb_std) = +0,432` nas tabelas reais mostra o resto: o que a
coluna media, fora do volume, era volume.

## O braço virou um *bracket* (2026-10-14)

Uma configuração densa só torna um resultado nulo **ininterpretável**: não se
distingue "a representação perdeu" de "esse encoder era fraco demais". O braço
publica então seis configurações não supervisionadas e sem treino, lidas como
faixa e não como ponto (ver `spec.VARIANTS`):

| id | encoder | pooling | janela | entrada | branqueamento |
|---|---|---|---|---|---|
| `bertimbau-mean` | BERTimbau (base) | média mascarada | 512 | título + corpo | não |
| `bertimbau-whitening` | BERTimbau | média mascarada | 512 | título + corpo | **sim** |
| `e5-large` | multilingual E5-large | média mascarada | 512 | título + corpo | não |
| `bge-m3` | BGE-M3 | **[CLS]** | 512 | título + corpo | não |
| `title-only` | BERTimbau | média mascarada | 512 | **só título** | não |
| `serafim-title` | Serafim PT (100M) | média mascarada | **128** | título + corpo | não |

Três coisas variam e cada uma é declarada por configuração, não fixada no código:

- **O pooling não é parâmetro livre.** O embedding denso do BGE-M3 *é* o token
  `[CLS]` (o `1_Pooling/config.json` do checkpoint diz
  `pooling_mode_cls_token: true`). Forçar média nele mediria uma configuração que
  ninguém usa, e um BGE-M3 fraco ficaria ininterpretável — exatamente o erro que o
  bracket existe para evitar. Cada encoder é lido como os autores o publicaram.
- **A janela é 512 em todo modelo que aguenta**, para que um ganho não venha de um
  encoder lendo mais texto que outro em silêncio. Os 128 tokens do Serafim são a
  exceção declarada.
- **O branqueamento** (Su 2021, arXiv:2103.15316; WhiteningBERT,
  doi:10.18653/v1/2021.findings-emnlp.23) corrige a anisotropia documentada da
  média mascarada sem fine-tuning (Ethayarajh 2019, doi:10.18653/v1/D19-1006): os
  vetores se aglomeram num cone estreito e frases sem relação ficam parecidas. Não
  usa rótulo nem treino, então fica dentro do pé do bracket.

**Risco de vazamento declarado.** O corte de pré-treinamento do E5-large e do
BGE-M3 não está documentado no model card. O protocolo 00 pede peso aberto *com
data de corte conhecida*, e essas duas configurações não têm uma — por isso entram
com o risco registrado e validação temporal, não como se o problema não existisse.

**E o branqueamento tem a mesma questão, resolvida no código.** Ele é ajustado
sobre o corpus, então ajustá-lo sobre o corpus inteiro é ver o período previsto —
que num problema de previsão é o futuro. `transform(..., whitening_fit_until=...)`
existe para isso: a janela de ajuste é argumento explícito, e o padrão `None`
(ajustar em tudo) vale só para a leitura **descritiva** que o bracket faz hoje. A
run de origem móvel do protocolo 00 tem de passar uma origem.

## O que o bracket mediu (2026-10-14)

As seis configurações rodaram sobre o mesmo corpus congelado (92,1 min de CPU, ~5 GB
de downloads). Todas viram os mesmos 4.369 artigos e produzem as mesmas 5.152 linhas
em 965 semanas × 28 localidades — o chão comum resistiu a seis encoders diferentes.

Nos 481 semanas nacionais com série de casos, o componente principal (PC1) das
médias semanais de cada configuração correlaciona (Spearman) assim:

| configuração | PC1 explica | PC1 × casos | `n_articles` × casos |
|---|---|---|---|
| `bertimbau-mean` | 20,8% | +0,119 | +0,347 |
| `bertimbau-whitening` | 1,1% | +0,188 | +0,347 |
| `e5-large` | 6,9% | +0,243 | +0,347 |
| `bge-m3` | 7,8% | +0,282 | +0,347 |
| `title-only` | 9,8% | +0,178 | +0,347 |
| `serafim-title` | 7,6% | +0,219 | +0,347 |

Quatro leituras:

1. **A faixa é de 2,4× e nenhuma alcança a contagem.** "Embeddings densos
   correlacionam +0,12 com casos" teria sido uma frase sobre o BERTimbau com média
   mascarada, não sobre embeddings densos. O `n_articles` (+0,347) é a mesma coluna
   em toda linha — é o `news_volume` do braço 01 com outro nome.
2. **Ler o corpo atrapalhou.** `title-only` (+0,178) bate a base de texto completo
   (+0,119) sem truncar nada: o título mais longo tem 35 tokens. A janela de 512
   não é o que limita a base, então a desculpa usual ("os artigos são longos
   demais") não está disponível aqui.
3. **O branqueamento consertou a geometria, não a correlação.** O cosseno médio
   entre pares cai de +0,8792 para −0,0002 (amostra de 1.000 artigos) — o cone
   some, como [Ethayarajh 2019](https://doi.org/10.18653/v1/D19-1006) descreve. Mas
   espalhar a variância remove também a direção dominante: o PC1 cai de 20,8% para
   1,1% da variância. Um único escalar é o instrumento errado para essa
   configuração.
4. **O PC1 do braço 03 (+0,320) bate todas as configurações do braço 02**, e o
   `news_severity` do braço 01 (+0,308) bate todas menos uma. Nesta métrica
   descritiva a representação densa é a mais fraca das três, não a mais forte.

A leitura incômoda não é "os embeddings perderam": é que as duas configurações que
mais ganham sobre a base são justamente **as duas cujo corte de pré-treinamento não
está documentado**, então o ganho não se separa de vazamento por este recorte. É o
protocolo 00 com validação temporal que decide isso, e ele não rodou. Nada aqui é o
resultado do protocolo 00.

## Como testar

1. Extrair o texto dos HTMLs.
2. Codificar cada artigo com o encoder da configuração (uma passada, sem
   fine-tuning no braço base — fine-tuning vira sub-experimento, ver pendências).
3. Agregar por EW.
4. Rodar o protocolo 00, **incluindo o controle negativo** (texto embaralhado).

## Evidência

- **Encoder PT-BR.** BERTimbau é o padrão da língua e casa com notícia geral
  (pré-treinado no brWaC, corpus web).
  [Souza 2020, BRACIS, LNCS 12319](https://doi.org/10.1007/978-3-030-61377-8_28).
  Variante biomédica (vocabulário clínico, mas treinada em nota clínica e
  abstract SciELO/PubMed, **não** em notícia):
  [Schneider 2020, BioBERTpt, ClinicalNLP](https://doi.org/10.18653/v1/2020.clinicalnlp-1.7).
  O MTEB-BR (arXiv:2607.04581) põe o BERTimbau-base em 9º de 93 em classificação
  PT-BR nativa e fraco em recuperação — e a pergunta aqui está mais perto de
  classificação que de recuperação, o que faz da base um ponto defensável e não um
  espantalho.
- **Alternativas multilíngues.** E5-large é o mais forte multilíngue público do
  MMTEB (arXiv:2502.13595); BGE-M3 é o mesmo porte com pooling `[CLS]`. Serafim é o
  único treinado especificamente para português (Gomes et al. 2024,
  arXiv:2407.19527, MIT), com janela de 128 tokens.
- **Anisotropia e branqueamento.**
  [Ethayarajh 2019](https://doi.org/10.18653/v1/d19-1006) mede o cone;
  [Su 2021](https://arxiv.org/abs/2103.15316) e
  [WhiteningBERT](https://doi.org/10.18653/v1/2021.findings-emnlp.23) propõem a
  correção linear pós-hoc que o bracket usa.
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

Médio. Uma passada de inferência sobre 4.369 artigos é trivial em GPU e leva de
30 s (`title-only`) a ~35 min em CPU por configuração; medido, o bracket inteiro
são **92,1 min** e ~5 GB de downloads (E5-large ~2,2 GB, BGE-M3 ~2,3 GB, Serafim
~0,4 GB). Sem rotulagem. O custo escondido é o download do modelo e a
reprodutibilidade (fixar versão/revisão do checkpoint — feito, por sha de commit).

## Pendências / próximo passo

- [x] Escolher o encoder primário. **Decidido em 2026-10-13:** BERTimbau
      (`neuralmind/bert-base-portuguese-cased`), revisão pinada no sha
      `94d69c95f98f7d5b2a8700c420230ae10def0baa`. Fixar a revisão e não o nome do
      branch é o que torna o artefato reprodutível — mesmo princípio do léxico
      versionado no braço 01.
- [x] Decidir o comparador de encoder. **Decidido em 2026-10-14:** não se escolhe
      um comparador, publica-se um *bracket* de seis configurações (§ acima). Um
      ponto único não distingue representação fraca de encoder fraco.
- [x] Decidir o pooling. **Decidido em 2026-10-13:** média mascarada pelo
      `attention_mask` sobre `last_hidden_state`, normalizada em L2.
      **Revisado em 2026-10-14:** passa a ser por configuração — o BGE-M3 é lido
      com `[CLS]`, que é como o embedding denso dele é definido. Max-pool continua
      fora; pooling por atenção aprendida seria treinável e mudaria a natureza do
      braço.
- [x] Resolver `emb_std`. **Decidido em 2026-10-14:** removido do schema e a
      tabela regenerada (§ acima). Não é feature a consertar: é função da média.
- [ ] Vale fine-tuning no corpus (classificação de relevância) ou o braço fica
      congelado? Fine-tuning muda a natureza do braço — decidir antes de comparar.
      Por ora **congelado**, como o resto do pipeline.
- [ ] Testar no Time-MMD Health antes de ir para dengue.
- [ ] Rodar o protocolo 00 de fato — braços 01, 02 e 03 sob o mesmo modelo, mesmas
      métricas e o controle negativo (texto embaralhado), com o branqueamento
      reajustado a cada origem. A seção exploratória do notebook **não** é isso.
