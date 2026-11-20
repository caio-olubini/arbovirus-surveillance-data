# 00 — Protocolo de comparação das features

**Estado:** rascunho — 2026-10-07
**Última revisão:** 2026-11-20

## Por que este arquivo existe

Decidimos (2026-10-07) que 01, 02 e 03 são **representações concorrentes** do mesmo
corpus: cada uma gera seu próprio conjunto de features e o artigo responde "qual
representação da notícia prevê dengue melhor?". Comparação entre representações só
vale se todo o resto estiver fixo. É o que este arquivo fixa.

Se um braço ganhar porque usou um split melhor, um horizonte diferente ou uma
métrica que favorece o seu tipo de erro, o resultado é ruído publicado como achado.

## Revisão — 2026-11-20: o artigo compara features, não representações

O parágrafo acima está **estreito demais, e errado no sujeito**: o artigo não é
sobre a notícia, nem sobre os boletins. Ele pergunta se as **features multimodais
propostas carregam sinal relevante e quais vale a pena incluir**, contra abordagens
mais simples. As representações de notícia (01, 02, 03) são **instâncias** de
feature multimodal — o mecanismo pelo qual a pergunta é respondida, não o assunto.

A revisão de hoje tira quatro coisas do lugar, e todas as quatro estavam aqui
escritas de outro jeito:

1. **Clima e busca saem das condições fixas e viram conjuntos comparados.** Eram
   iguais em todos os braços; passam a entrar um a um, porque a pergunta é
   exatamente quais features incluir. As demais condições fixas continuam valendo.
2. **O resultado são os ganhos acumulados, sem manchete.** Não existe "o ganho do
   texto" em número único: existem três ganhos, cada um medido contra o conjunto
   imediatamente anterior, e o mesmo bloco tem que ganhar nos dois tipos de
   modelo.
3. **Granularidade espacial: BR no número principal, UF como robustez
   declarada** — não como leitura exploratória. A leitura por UF é feita e
   reportada; o número principal não depende dela. Motivo em "Riscos".
4. **Horizonte: 1 semana no número principal, 4 semanas como robustez
   declarada.** O horizonte maior deixa de ser trabalho futuro e passa a ser
   medido, porque a literatura da linha trabalha em 1–4 semanas e um desenho só de
   1 semana seria o mais estreito do campo ([06](06-desenho-do-experimento.md),
   eixo 1).

## Condições fixas (não podem variar entre os conjuntos)

| Item | Fixo em | Onde |
|---|---|---|
| Corpus | mesma versão congelada dos HTMLs (registrar hash + data) | `data/news/dengue/articles/` |
| Calendário | semana epidemiológica ancorada no domingo | `src/pipeline/epiweek.py` |
| Alvo | casos SINAN dengue **suspeitos** (toda notificação menos os descartados), na semana de **início de sintomas** | `SINAN_dengue_cases.parquet` |
| Grão espacial | **BR** no número principal; **UF como robustez declarada** | — |
| Horizonte | **1 semana**; **4 semanas** como robustez declarada | — |
| Janela pontuada | de **2022-01-02 a 2024-12-29** (157 semanas), com treino desde 2014 | [plano](plano.md) §6 |
| Backbone | **o mesmo** para todos os conjuntos | TFT early-fusion (Lim et al. 2021) como baseline de fusão — [06](06-desenho-do-experimento.md) |
| Split | rolling-origin, refit só com passado | `rolling_origin` |
| Métricas | MAE, RMSE, MAPE **e** WIS/CRPS/cobertura | `src/forecast/README.md` |

**Só varia o bloco de feature.** Um conjunto = um bloco de features → o mesmo
modelo → as mesmas métricas.

A janela pontuada é curta por uma razão que não se contorna: a série de busca
congelada começa em 2020-01-26 e termina em 2024-12-29, e o desenho exige 104
semanas de histórico antes da primeira previsão. Os conjuntos que usam busca só têm
feature a partir de 2022-01-23, então têm 154 semanas pontuadas em vez de 157. A
diferença entra declarada, não escondida.

## Os conjuntos acumulados: o que entra em cada um

| Conjunto | O que esse conjunto soma |
|---|---|
| `histórico` | lags e sazonalidade do próprio alvo |
| `+ clima` | ERA5 por UF e semana epidemiológica |
| `+ busca` | Google Trends |
| `+ texto` | a representação de texto escolhida |

Dois tipos de modelo — *simples* (gradient boosting ou regressão sobre tabela) e
*sequencial* (rede neural) — × quatro conjuntos = **8 células da grade**.

**O que o artigo reporta são três ganhos, um por conjunto:** `+clima − histórico`,
`+busca − +clima`, `+texto − +busca`. Não existe "o ganho da notícia" em número
único, e um paper que apresente um só estará escondendo de onde ele veio.

**São oito comparações pareadas**, e todas entram na correção para comparações
múltiplas: seis entre conjuntos consecutivos (três níveis × dois tipos de modelo) e
duas contra o **ensemble sem texto**. O conjunto `+ texto` tem que bater duas barras,
não uma — o conjunto anterior e a média de tudo que não usa texto. Motivo: em
horizonte curto a média de vários modelos é um adversário forte (Johansson 2019;
Wu 2025), e um ganho que só aparece contra o conjunto anterior pode ser o texto
compensando um modelo mal ajustado.

**Dentro do conjunto `+ texto`**, as representações (léxico, embeddings, tópicos e
extração por LLM) são comparadas entre si, sob a mesma regra de decisão. Entram na
grade **uma ou duas codificadoras de embedding**; as outras variantes ficam como
robustez declarada, porque cada codificadora é uma grade inteira e não uma coluna a
mais.

**A ablação sem texto é o conjunto `+ busca`** — tudo menos texto, alvo e clima e
busca juntos. É o delta que o artigo precisa reportar. O conjunto `histórico` é o
conjunto mais simples, não a ablação: sem clima nem busca, ele mede outra coisa.

**Controle negativo:** substituir o texto por vazio / constante / embaralhado. Se o
erro não mudar, o texto não está sendo usado e o ganho é artefato de arquitetura.
Ver `Tan et al. 2024` (arXiv:2406.16964) — remover o LLM de arquiteturas tipo
Time-LLM empata ou melhora.

## Baselines — fora dos quatro conjuntos, e com citação

| Baseline | Citação | O que ele testa |
|---|---|---|
| Persistência (casos da semana anterior) | Xiao 2025 ("naive"); tradição de Tashman 2000 | a barra de qualquer modelo |
| Naive sazonal (mesma semana do ano anterior) | tradição de competição (Tashman 2000) | quanto custa ignorar a tendência entre anos |
| SARIMA só com casos | Xiao 2025 ("DC"); Chen & Moraga 2025 (ARIMA) | o que o histórico sozinho entrega |
| SARIMAX casos + Google Trends | Xiao 2025 ("DCGT"); Chen & Moraga 2025 (SARIMAX) | o que a busca acrescenta ao histórico, num modelo estatístico em vez de aprendizado de máquina |
| Modelo linear **só** com Google Trends | Xiao 2025 ("GT") | se a busca substitui o alvo |
| InfoDengue bayesiano (binomial negativa hierárquica) | Codeço 2018; Bastos 2019; Xiao 2025 | o padrão operacional brasileiro |
| **Ensemble de todos os modelos** | Johansson 2019; Wu 2025 | o teto realista — é o que ganha nos dois |

Os DOIs estão em [06](06-desenho-do-experimento.md).

**O baseline só-busca fica fora dos quatro conjuntos**, como comparação independente: ele
responde "a busca substitui o alvo?", que não é um dos conjuntos.

**O ensemble entra de dois jeitos, e os dois papéis são diferentes.** O ensemble
**sem texto** (a média dos conjuntos que não usam texto) entra na regra de decisão: o
conjunto de texto tem que batê-lo. O ensemble **global** (a média de tudo, texto
incluído) fica descritivo, porque ele contém as células que estão sendo julgadas —
usá-lo na regra seria julgar o réu com o júri.

**O InfoDengue entra com prazo fechado.** Ele é reimplementado aqui, com um prazo
declarado de uma semana; se não convergir dentro do prazo, ele sai do experimento,
vira citação do sistema original e o desvio fica registrado. O que não acontece é
ele consumir o prazo inteiro do paper.

**A barra medida hoje** (persistência e naive sazonal, BR, horizonte 1) tem dois
números, e é preciso dizer qual se está usando: na janela longa (2016–2024, 470
semanas pontuadas) a persistência dá MAE **4.358** e o naive sazonal **23.618**
casos/semana; na janela do paper (2022-01-02 a 2024-12-29, 157 semanas) a
persistência dá MAE **9.022** e o naive sazonal **39.552**. A janela longa é
robustez declarada; o número do paper é o da segunda. Os dois vivem em
`data/forecast/`, e a tabela das três janelas — com o comando que produz cada uma —
está em [`src/forecast/README.md`](../src/forecast/README.md) §1. A janela do paper
exige as duas flags juntas (`--to-year 2024 --score-from 2022`); só `--score-from`
deixa o painel ir até 2026 e devolve 244 semanas pontuadas, não 157.

## Regras de vazamento

- Nenhum artigo publicado **depois** da origem da previsão entra no braço.
- O corpus vai até 2026 e os modelos pré-treinados podem "conhecer" os desfechos
  (dengue 2024 foi recorde e está em toda parte). Preferir pesos abertos com data
  de corte conhecida; registrar o corte de cada modelo usado.
- SINAN tem atraso de notificação e revisão — a série de uma EW é reescrita depois.
  Isso afeta qualquer avaliação de nowcasting.
- O nosso alvo é **forecast** de casos suspeitos por início de sintomas, com 1
  semana à frente. Não é nowcast e não tem corte de maturidade; a diferença em
  relação ao Xiao 2025 (nowcast com 15 semanas de maturidade) tem que estar escrita
  no texto ([06](06-desenho-do-experimento.md), eixo 2).

## Riscos do desenho

- **Descompasso espacial, com o tamanho medido.** O corpus é de **uma fonte
  nacional** (Agência Brasil, 4.569 artigos), mas as tabelas de features têm
  **28 localidades** — BR e as 27 UF — de 2002-02-17 a 2026-09-13. As linhas de UF
  são **atribuição por indicação locativa** no texto, não contagem por estado: um
  artigo que cita três estados conta nos três, e por isso as linhas de UF somam
  7.223 menções para 4.369 artigos nacionais — elas **não somam a linha BR e não
  devem ser lidas como contagem por estado**. A linha BR contém todo artigo, por
  construção. É a razão de o número principal ser BR.
- **Semanas sem artigo.** A linha BR tem **965 semanas com pelo menos um artigo**
  dentro de um intervalo de 1.283 semanas — 318 semanas sem nenhum artigo, que
  simplesmente não aparecem na tabela. Mascarar semana sem artigo e usar um
  indicador explícito de "sem notícia", para o modelo distinguir ausência de sinal
  de sinal neutro. Nacionalmente são ~3,6 artigos/semana; numa UF, a maioria das
  semanas fica em zero.
- **Poder estatístico.** 157 semanas pontuadas é pouco para um teste pareado com
  correção para oito comparações, e o horizonte de 1 semana é onde o histórico
  sozinho explica quase tudo ([06](06-desenho-do-experimento.md), eixo 1). Um
  ganho pequeno pode não ser detectável, e isso entra como limitação declarada, não
  como desculpa depois.
- **Endogeneidade.** Cobertura segue casos. Granger aqui é ordenação temporal
  preditiva, nunca mecanismo. Ver a literatura de viés de notificação (caxumba,
  Cryptosporidium) citada em 01.
- **Comparação de métricas.** Métricas pontuais e probabilísticas podem escolher
  modelos diferentes. Reportar as duas e dizer quando divergirem.

## Pendências / próximo passo

- [ ] Congelar e versionar a versão do corpus usada (hash dos HTMLs + data).
- [x] Definir o horizonte de previsão. **1 semana** no número principal, **4
      semanas** como robustez declarada — os dois medidos, porque a linha trabalha
      em 1–4 semanas e o avaliador já aceita horizonte maior.
- [x] Decidir alvo em nível ou log, e por UF ou BR. **Nível, BR** no número
      principal; **UF como robustez declarada**, com o tamanho do descompasso
      medido (ver "Riscos"). Log é decisão de modelo e pertence ao modelo.
- [x] Escrever o baseline "sem texto" antes de qualquer representação — ele é a
      barra. **Medido:** persistência MAE **9.022** e naive sazonal **39.552**
      casos/semana na janela do paper (157 semanas, 2022-01-02 a 2024-12-29), com
      treino desde 2014; na janela longa (470 semanas) 4.358 e 23.618. A
      persistência é a barra de verdade: em horizonte de 1 semana a curva é quase
      toda autocorrelação, e o naive sazonal paga 4,4× por ignorar a tendência
      entre anos. Falta o "sem texto" com busca e clima, que é o conjunto `+ busca`.
- [ ] **Registrar aqui o ganho que conta como ganho**, em casos por semana, no
      passo 2 do [plano](plano.md), antes de a primeira célula da grade ser
      calculada. O número de comparações já está registrado acima (**oito**).
      A palavra exata que o plano usa como confirmação deste registro não aparece
      neste arquivo de propósito: escrevê-la antes da decisão faria o passo
      parecer pronto.
- [ ] Decidir quais **uma ou duas codificadoras de embedding** entram na grade, e
      declarar as outras como robustez.

Números, comandos e o contrato compartilhado: [`src/forecast/README.md`](../src/forecast/README.md).
