# 06 — Como a linha desenha o experimento

**Estado:** testando — 2026-11-20
**Papel no artigo:** apoio — dá citação aos baselines e ao backbone do
[protocolo 00](00-protocolo-comparacao.md), e é o levantamento de literatura do
passo 1 do [plano](plano.md). As citações já foram levadas para lá em 2026-11-20.

**O que este arquivo cobre:** o *desenho* dos estudos — alvo, granularidade,
horizonte, janela, split, métrica, baselines, tipo de modelo. Não é revisão de
resultado, e não substitui os relatórios de cada família de literatura (que são
sobre representação de texto).

## Por que este arquivo existe

O protocolo 00 fixa as condições que valem em todos os conjuntos, mas escrevia "TFT
early-fusion" como backbone e listava quatro baselines **sem uma citação sequer** —
e o [plano](plano.md) §6 diz que o levantamento de literatura é o que fecha a
grade, porque "abordagem mais simples" precisa de citação, não de invenção. (A
pendência foi fechada em 2026-11-20: o protocolo 00 agora nomeia e cita.)

O caminho foi ler como os estudos da linha montam o experimento e extrair: o que
dá para **copiar com citação**, o que precisa ser declarado como **desvio**, e o
que **ninguém faz** (logo, é onde a contribuição mora).

## O nosso desenho, para comparar

| Item | O nosso | Onde |
|---|---|---|
| Alvo | casos SINAN dengue **suspeitos**, por semana de início de sintomas | [protocolo 00](00-protocolo-comparacao.md) |
| Grão espacial | **BR** no número principal; **UF como robustez declarada** | idem — revisado em 2026-11-20 |
| Grão temporal | semana epidemiológica ancorada no domingo | `src/pipeline/epiweek.py` |
| Horizonte | **1 semana** no número principal; **4 semanas declarado** | idem — revisado em 2026-11-20 |
| Janela pontuada | **157 semanas**: 2022-01-02 a 2024-12-29, com treino desde 2014 | [plano](plano.md) §6 |
| Split | rolling-origin, refit só com o passado | [src/forecast/README.md](../src/forecast/README.md) |
| Janela mínima | 104 semanas de treino | idem (tabela de decisões) |
| Métricas | MAE, RMSE, MAPE **e** WIS/CRPS/cobertura | [protocolo 00](00-protocolo-comparacao.md) |
| Baselines | naive (persistência e sazonal), SARIMA/SARIMAX, InfoDengue-bayesiano, só-busca e ensemble — **com citação** | idem; tabela de baselines abaixo e [protocolo 00](00-protocolo-comparacao.md) |
| Backbone | TFT early-fusion, o mesmo para todos os braços | idem — citação: Lim 2021 |
| Barra medida | persistência MAE **9.022**, naive sazonal **39.552** casos/semana, na janela do paper (157 semanas); na janela longa (470 semanas, 2016–2024), 4.358 e 23.618 | [src/forecast/README.md](../src/forecast/README.md) |

## A tabela da linha

| Estudo | Alvo | Grão espacial | Grão temporal | Horizonte | Janela | Métricas |
|---|---|---|---|---|---|---|
| Johansson 2019 (PNAS) | 3 alvos sazonais: incidência do pico, **semana** do pico, incidência total da temporada | 2 cidades: Iquitos (PE), San Juan (PR) | semanal | temporada inteira (previsão prospectiva por temporada) | 8 temporadas, 16 equipes | probabilístico, skill por alvo; ensemble multi-modelo vence |
| Wu 2025 (PNAS) | casos | província | **mensal** | **1 a 3 meses** | 180+ localidades, 2–3+ anos cada; avaliação prospectiva em 2022–2023 | ensemble fica no top-3; nenhum modelo é ótimo em toda parte |
| Xiao 2025 (PLOS NTD) | casos "verdadeiros" = reportados **15 semanas** depois (corte que captura ~95% das notificações) | **26 estados** (ES sai: parou de reportar na EW 16/2024) | semanal (EW) | **nowcast da semana corrente**, com as 4 semanas mais recentes fora do treino ("4 semanas à frente"); sensibilidade em 4 posições de lead | treino de **156 semanas** (EW 06/2021 a EW 06/2024), **exclui 2020** (COVID); avaliação EW 10/2024 a EW 03/2025 = **46 nowcasts** em janela móvel de 1 semana | RMSE, RMSPE, logscore, cobertura 50% e 95% |
| Freitas 2025 (Infect Dis Model) | casos **prováveis** | **118 distritos sanitários** | semanal | **até 52 semanas** | 2015-10-11 a 2024-10-05, temporadas EW 41 → EW 40 | **quatro bandas preditivas**, sem score numérico de skill |
| Chen & Moraga 2025 (Trop Med Health) | casos | **município** (Rio de Janeiro) | semanal | **1–4 semanas** e **8–12 semanas** | **janela móvel** (dynamic window) | erro, intervalos de incerteza, custo computacional |
| Bastos 2019 (Stat Med) | correção de atraso de notificação (run-off triangle) | dengue RJ, SARI PR | semanal | — (é o insumo do nowcast) | — | bayesiano hierárquico, INLA |
| Codeço 2018 (InfoDengue) | nowcast de arboviroses | **município** | semanal | sistema em produção | — | — |
| Zhu 2025; Chen & Moraga 2025; Sebastianelli 2024 (clima) | — | microregião × EW; 27 UF × EW; 27 unidades federativas × **mês** | diário→EW, grade→unidade administrativa ponderada por população | — | — | — |

Fontes internas das três últimas linhas de clima: [articles/README.md](../articles/README.md).

## Os oito eixos onde a decisão acontece

### 1. Horizonte — o nosso é o mais curto da linha

A linha trabalha em três faixas: **1–4 semanas** (Xiao 2025; Chen & Moraga 2025),
**temporada inteira** (Johansson 2019) e **até 52 semanas ou 1–3 meses** (Freitas
2025; Wu 2025). O nosso **1 semana à frente é o mais curto de todos**.

Não é erro — é o passo que o modelo precisa acertar antes de qualquer multi-passo,
e o avaliador já aceita horizonte maior. Mas **passa a ser desvio declarado**, não
padrão do campo, e por isso **h=4 entra medido como robustez** em vez de ficar como
trabalho futuro (decidido em 2026-11-20).

O custo de teto é real e agora está medido na janela certa: na janela do paper a
persistência dá MAE **9.022** em BR — 2,1× o número da janela de 2016–2024 (4.358),
porque 2024 foi ano recorde e a curva sobe de patamar. Em horizonte curto a série é
quase toda autocorrelação, então o espaço para a feature multimodal aparecer é
pequeno ([src/forecast/README.md](../src/forecast/README.md)).

### 2. Alvo — a decisão mais consequente, e a mais fácil de confundir

Três coisas diferentes circulam na literatura sob o nome "prever dengue":

- **Nowcast**: casos que já ocorreram e ainda não foram notificados. O "verdadeiro"
  é definido por um corte de maturidade — Xiao 2025 usa *reportado 15 semanas
  depois*. Depende inteiramente do corte escolhido.
- **Forecast**: casos que ainda não ocorreram (Freitas 2025, Wu 2025, Chen &
  Moraga 2025).
- **Proxy**: casos prováveis em vez de suspeitos (Freitas 2025), ou hospitalizações.

O SINAN **reescreve a série** retroativamente, e é isso que torna a distinção
obrigatória: Bastos 2019 modela exatamente esse atraso (estrutura de run-off
triangle, INLA bayesiano), ilustrando com dengue no Rio de Janeiro e SARI no Paraná.
Sem declarar o corte de maturidade, dois números de "nowcast" não são comparáveis.

**O nosso alvo é forecast 1 semana à frente de casos suspeitos por início de
sintomas.** Não é o alvo do Xiao (nowcast, 15 semanas de maturidade) nem o do
Freitas (prováveis). A diferença tem que estar escrita no texto, senão a comparação
com eles vira maçã com laranja.

### 3. Granularidade espacial — o nosso BR é o grão mais grosso da linha

A linha desce até onde o dado permite: **município** (InfoDengue/Codeço 2018; Chen
& Moraga 2025), **distrito sanitário** (118 no Freitas 2025), **estado** (26 no
Xiao 2025), **microregião** no clima (Zhu 2025, via [articles/README.md](../articles/README.md)),
e sobe a **província** (Wu 2025) e **cidade** (Johansson 2019).

Nosso BR é a escolha mais grossa, e o motivo é honesto: é onde a notícia (nacional)
e o alvo têm o mesmo grão, como o protocolo 00 já registra. A consequência é que
**não somos diretamente comparáveis a nenhum deles** em nível espacial — declarar.

**O que "a notícia é nacional" quer dizer, medido (2026-11-20).** As tabelas de
features de notícia têm **28 localidades** — BR e as 27 UF — de 2002-02-17 a
2026-09-13. Então não é que falte grão por UF: é que as linhas de UF são
**atribuição por indicação locativa** no texto de um corpus de fonte única, não
contagem por estado. Um artigo que cita três estados conta nos três, e as linhas de
UF somam 7.223 menções para 4.369 artigos nacionais — elas não somam a linha BR,
que por construção contém todo artigo. A linha BR também tem 318 semanas vazias
dentro do intervalo (965 com artigo em 1.283): semana sem notícia não é sinal
neutro.

**UF passa a robustez declarada** (2026-11-20): a leitura por UF é feita e
reportada à parte, e o número principal não depende dela. Não é o grão do número
principal porque a atribuição acima não sustenta isso — e é melhor declarar do que
descobrir na revisão.

### 4. Granularidade temporal e calendário

Semanal por semana epidemiológica domina em arbovirose (Johansson 2019, Xiao 2025,
Freitas 2025, Chen & Moraga 2025). **Mensal aparece quando o horizonte é longo**
(Wu 2025, 1–3 meses) ou quando a covariável é mensal (Sebastianelli 2024, via
[articles/README.md](../articles/README.md)). O nosso EW ancorado no domingo está
alinhado com o padrão — não é eixo de divergência.

### 5. Janela de treino, e o que se exclui

Duas práticas que a linha adota e nós não:

- **Janela explícita em semanas**: Xiao 2025 usa 156 semanas (3 anos), com
  sensibilidade em 1 e 2 anos, e **exclui 2020** como ano anômalo (COVID). Nosso
  mínimo é 104 semanas e **não excluímos ano nenhum** — a barra inclui 2020 e
  inclui 2024, que foi recorde. A nossa janela pontuada é de 157 semanas (a do
  Xiao, de avaliação, tem 46 nowcasts), então a comparação de tamanho é favorável
  a nós; a de alvo, não (ver eixo 2).
- **Janela móvel**: Xiao 2025 e Chen & Moraga 2025 usam janela que avança; é a
  mesma linhagem de avaliação do nosso rolling-origin.

Excluir 2020 é uma decisão declarada deles, não uma verdade. A nossa versão disso
já existe como robustez (o avaliador mede com e sem 2024), mas 2020 ainda não foi
testado — e é o ano que pode estar inflando a barra de persistência para cima.

### 6. Split

Tashman 2000 é a referência canônica de avaliação fora da amostra por origem
móvel ("rolling origin"), com refit a cada origem — exatamente o que
`rolling_origin` faz. Bergmeir & Benítez 2012 é o complemento: mostra **quando** a
validação cruzada é uma aproximação aceitável de erro fora da amostra em séries
temporais, e quando não é. O nosso desenho (refit só com o passado) está no lado
conservador dos dois — não é eixo de divergência, mas agora tem citação.

### 7. Métrica — a linha migrou para probabilístico, nós já estamos lá

- **Pontual**: MAE/RMSE/MAPE/RMSPE continuam sendo o que mais se reporta (Xiao 2025
  usa RMSE e RMSPE).
- **Probabilística**: Johansson 2019 avalia distribuições desde 2019; Bracher 2021
  fixa o **WIS** (weighted interval score) como o padrão para previsão em formato
  de intervalo — é o artigo que dá citação à nossa métrica primária. A base
  teórica das regras de pontuação próprias é Gneiting & Raftery 2007.
- **Logscore e cobertura**: Xiao 2025 reporta logscore e cobertura de 50% e 95%.
  Detalhe revelador: **InfoDengue ficou de fora da comparação de cobertura** (emite
  no nível municipal, não no estadual) e **o naive também** (é pontual). É
  exatamente o buraco que a fatia 2 fecha ao exigir quantis de **todo** mundo,
  inclusive dos dois ingênuos. Nenhum número de WIS é comparável entre estudos se
  um deles não emite distribuição.
- **MAPE**: é o que a linha mais reporta e o que menos aguenta alvo perto de zero.
  O nosso avaliador já registra que o denominador do MAPE está em aberto
  ([src/forecast/README.md](../src/forecast/README.md) §3) — enquanto estiver, o
  MAPE não é reportável com honestidade.

### 8. Modo de avaliação — retrospectivo, prospectivo e competição

O padrão mais forte é **prospectivo com previsão congelada antes do desfecho**:
Johansson 2019 (8 temporadas, 16 equipes) e Wu 2025 (2022–2023 em tempo real) fazem
isso. Xiao 2025 é retrospectivo com janela móvel. O formato competição (múltiplas
equipes, submissões cegas) é o da Dengue Forecasting Sprint brasileira
(Araujo et al. 2025 — ver ressalva nas fontes).

**O nosso é retrospectivo.** Isso é uma limitação a declarar, não a esconder. Para
não deixar buraco no reporte, a lista de itens mínimos exigidos de um paper de
previsão epidêmica é **EPIFORGE 2020** (Pollett 2021) — 19 itens, feita por Delphi
com modeladores e usuários finais. Vale rodar o manuscrito contra ela antes da
fatia 12.

## Baselines consagrados — a lista que o protocolo 00 pode citar

A melhor notícia desta leitura: **o conjunto de baselines do Xiao 2025 é quase
idêntico ao que o protocolo 00 declarou de memória.** O protocolo deixa de ser
"nossos baselines" e passa a ser "os baselines que a linha usa".

| Baseline | Quem usa | O que ele testa |
|---|---|---|
| Persistência (casos da semana anterior) | Xiao 2025 ("naive"); a tradição vem de Tashman 2000 | a barra mínima de qualquer modelo |
| SARIMA só com casos | Xiao 2025 ("DC"); Chen & Moraga 2025 (ARIMA) | o que o histórico sozinho entrega |
| SARIMAX casos + Google Trends | Xiao 2025 ("DCGT"); Chen & Moraga 2025 (SARIMAX) | o que a busca acrescenta ao histórico |
| Modelo linear **só** com Google Trends | Xiao 2025 ("GT") | se a busca substitui o alvo |
| InfoDengue bayesiano (binomial negativa hierárquica) | Xiao 2025; Codeço 2018; Bastos 2019 | o padrão operacional brasileiro |
| Naive sazonal (mesma semana do ano anterior) | tradição de competição (Tashman 2000); já medido por nós em 39.552 (janela do paper) | quanto custa ignorar a tendência entre anos |
| **Ensemble de todos os modelos** | Johansson 2019; Wu 2025 | o teto realista — é o que ganha nos dois |
| **Sem texto / controle negativo** | não é baseline do campo; é nosso | se o texto está sendo usado — Tan et al. 2024 (arXiv:2406.16964) |

**Já no nosso protocolo:** o ensemble. Johansson 2019 mostra que ensemble
multi-modelo e multi-equipe bate modelo individual de forma consistente, e Wu 2025
mostra o ensemble no top-3 em 180+ localidades. É barato (média das células da
grade). **Entra — decidido em 2026-11-20**, com um detalhe que a leitura forçou: o
ensemble **sem texto** é que entra na regra de decisão, como segunda barra do conjunto
de texto; o ensemble **global** fica descritivo, porque ele contém as células que
estão sendo julgadas.

**E o InfoDengue entra com prazo fechado** (2026-11-20). Ele é o único baseline
caro da lista: reimplementar a binomial negativa hierárquica é um projeto dentro do
projeto. Fica com prazo declarado de uma semana e, se não convergir, sai do
experimento, vira citação do sistema original e o desvio é registrado — o que não
acontece é ele consumir o prazo do paper.

## Tipos de modelo para os dois eixos do desenho

- **Simples (tabular)**: regressão, random forest, XGBoost, SVM — é o que Chen &
  Moraga 2025 compara contra os estatísticos, e o que Wu 2025 usa como componentes.
  É o tipo *simples* da grade.
- **Sequencial**: LSTM/GRU — no Chen & Moraga 2025 o LSTM com covariáveis de clima
  foi o ML mais acurado (e o mais lento); Chen & Moraga 2025 também é a fonte do
  grão de clima UF × EW com lags lidos por SHAP.
- **Fusão multimoda**: **TFT** (Lim et al. 2021, Int. J. Forecasting 37(4):1748–1764,
  arXiv:1912.09363) é a citação que falta para o backbone do protocolo 00 —
  multi-horizonte, atenção interpretável, aceita covariáveis estáticas e
  conhecidas no futuro, que é exatamente o formato do nosso problema (o calendário
  é conhecido; a notícia não é).
- **Controle negativo**: Tan et al. 2024 (arXiv:2406.16964) — remover o componente
  de LLM empata ou melhora. Já citado no protocolo 00, e é o que justifica a
  ablação obrigatória.

**A lacuna que sobra é a nossa.** As quatro famílias de literatura lidas
(embeddings, features de texto, tópicos, extração por LLM) não têm um tipo de
modelo consagrado para fundir texto com um alvo preditivo: a ponte entre representação e
vigilância não foi construída ([articles/embeddings/relatorio.md:71](../articles/embeddings/relatorio.md))
e a extração é sempre por documento, nunca como série
([articles/llm-extracao/relatorio.md:113](../articles/llm-extracao/relatorio.md)).
Ou seja: **a grade é nossa**, e é isso que ela tem de contribuição.

## O que isso muda no nosso desenho

1. **Baselines e backbone ganham citação** — Xiao 2025 e Chen & Moraga 2025 para
   os seis baselines, Johansson 2019 e Wu 2025 para o ensemble, Lim 2021 para o
   TFT. Era a pendência que o protocolo 00 tinha em aberto, e ela está fechada.
2. **Horizonte 1 semana vira desvio declarado, e h=4 entra medido como robustez**
   (2026-11-20) — deixar o multi-passo só como trabalho futuro deixaria o desenho
   mais estreito que o próprio campo.
3. **Alvo BR é o grão mais grosso da linha** — declarar como limitação, junto com
   o descompasso espacial que o protocolo já registra. **UF entra como robustez
   declarada**, não como número principal, porque as linhas de UF são atribuição
   locativa e não partição dos artigos (ver eixo 3).
4. **2020 não é excluído** enquanto Xiao exclui. Testar como robustez, ao lado do
   corte de 2024 que já existe.
5. **Quantis para todo mundo, inclusive os ingênuos**, deixa de ser capricho
   nosso: é o que o Xiao 2025 não conseguiu fazer e por isso comparou cobertura
   com dois modelos a menos.
6. **Ensemble entra como baseline** — decidido em 2026-11-20 (Johansson 2019; Wu
   2025). É o adversário que a linha de fato considera, e é barato: a média das
   células da grade.
7. **Retrospectivo** é limitação declarada; **EPIFORGE 2020** é o checklist de
   reporte para rodar na fatia 12.

**O que a revisão de 2026-11-20 mudou no desenho**, além dos itens 2, 3 e 6 acima:

8. **O resultado são os ganhos acumulados entre conjuntos, não um número.** São três
   ganhos (`+clima − histórico`, `+busca − +clima`, `+texto − +busca`), cada um nos dois
   tipos de modelo. Não existe "o ganho da notícia" em número único — o campo
   reporta número único porque compara modelos, e nós comparamos **blocos de
   feature**.
9. **O conjunto de texto bate duas barras**: o conjunto anterior e o ensemble sem
   texto. Wu 2025 e Johansson 2019 dizem por quê — em horizonte curto a média de
   vários modelos é adversário forte, então "ganhou do conjunto anterior" pode ser o
   texto compensando um modelo mal ajustado. São **oito comparações** ao todo.
10. **A barra é remedida na janela do paper.** A persistência passa de MAE 4.047
    (557 semanas, 2014–2026) para **9.022** (157 semanas, 2022–2024). Não é
    mudança de método: é que o número antigo media outra janela, e uma janela com
    2024 dentro é mais difícil. Reportar 4.047 como "a barra" fazia o problema
    parecer mais fácil do que é.
11. **Uma ou duas codificadoras de embedding na grade**, não uma por variante —
    há **seis** no disco. As outras viram robustez declarada. Foi o maior corte de
    escopo da revisão: cada codificadora é uma grade inteira.
12. **A ablação sem texto é o conjunto `+ busca`** (alvo + clima + busca), e não o
    `histórico`: o `histórico` é o conjunto mais simples e mede outra coisa.

## Fontes trazidas

**Lançadas em `articles/references.csv` em 2026-11-20** — 13 linhas novas, com os
metadados puxados do Crossref (nada digitado de memória). Abaixo a versão legível,
com o motivo de cada uma:

| Citação | DOI | Por que importa |
|---|---|---|
| Johansson MA et al. 2019. An open challenge to advance probabilistic forecasting for dengue epidemics. *PNAS* 116(48):24268–24274 | 10.1073/pnas.1909865116 (correção: 10.1073/pnas.2014829117) | o estudo canônico de desenho: 3 alvos sazonais, 2 cidades, 8 temporadas, 16 equipes, avaliação prospectiva, ensemble vence |
| Bracher J, Ray EL, Gneiting T, Reich NG 2021. Evaluating epidemic forecasts in an interval format. *PLoS Comput Biol* 17(2):e1008618 | 10.1371/journal.pcbi.1008618 (correção: 10.1371/journal.pcbi.1010592, em 18(10)) | define o **WIS**, a nossa métrica primária |
| Gneiting T, Raftery AE 2007. Strictly proper scoring rules, prediction, and estimation. *JASA* 102(477):359–378 | 10.1198/016214506000001437 | base teórica de logscore/CRPS/WIS |
| Tashman LJ 2000. Out-of-sample tests of forecasting accuracy: an analysis and review. *Int J Forecasting* 16(4):437–450 | 10.1016/S0169-2070(00)00065-0 | citação canônica do rolling-origin |
| Bergmeir C, Benítez JM 2012. On the use of cross-validation for time series predictor evaluation. *Information Sciences* 191:192–213 | 10.1016/j.ins.2011.12.028 | quando a validação cruzada é válida em série temporal |
| Pollett S, Johansson MA, Reich NG, et al. 2021. Recommended reporting items for epidemic forecasting and prediction research: EPIFORGE 2020. *PLoS Med* 18(10):e1003793 | 10.1371/journal.pmed.1003793 (correção: 10.1371/journal.pmed.1004316) | checklist de reporte, 19 itens — rodar na fatia 12 |
| Wu S, Meyer AG, Clemente L, et al. 2025. Ensemble approaches for short-term dengue fever forecasts: a global evaluation study. *PNAS* 122(33):e2422335122 | 10.1073/pnas.2422335122 | ensemble em 180+ localidades, 1–3 meses, retrospectivo + prospectivo |
| Xiao Y, Soares G, Bastos L, Izbicki R, Moraga P 2025. Dengue nowcasting in Brazil by combining official surveillance data and Google Trends information. *PLoS Negl Trop Dis* 19(8):e0012501 | 10.1371/journal.pntd.0012501 | **o mais próximo de nós**: 26 estados, semanal, baselines idênticos, logscore + cobertura |
| Freitas LP et al. 2025. A statistical model for forecasting probabilistic epidemic bands for dengue cases in Brazil. *Infectious Disease Modelling* 10(4):1479–1487 | 10.1016/j.idm.2025.07.014 | horizonte de 52 semanas, 118 distritos, bandas preditivas; mostra que a linha aceita avaliar sem score numérico |
| Chen X, Moraga P 2025. Assessing dengue forecasting methods: a comparative study of statistical models and machine learning techniques in Rio de Janeiro, Brazil. *Trop Med Health* 53:52 | 10.1186/s41182-025-00723-7 | horizontes 1–4 e 8–12 semanas, janela móvel, estatísticos × ML × ensemble |
| Codeço C, Coelho F, Cruz O, Oliveira S, Castro T, Bastos L 2018. Infodengue: a nowcasting system for the surveillance of arboviruses in Brazil. *Rev Épidémiol Santé Publique* 66:S386 | 10.1016/j.respe.2018.05.408 | citação canônica do InfoDengue, o baseline operacional brasileiro |
| Bastos LS, Economou T, Gomes MFC, et al. 2019. A modelling approach for correcting reporting delays in disease surveillance data. *Stat Med* 38(22):4363–4377 | 10.1002/sim.8303 | o atraso de notificação que obriga a declarar o corte de maturidade |
| Lim B, Arik SO, Loeff N, Pfister T 2021. Temporal Fusion Transformers for interpretable multi-horizon time series forecasting. *Int J Forecasting* 37(4):1748–1764 | 10.1016/j.ijforecast.2021.03.012 (arXiv:1912.09363) | a citação que falta para o backbone TFT do protocolo 00 |

## Fontes candidatas — ainda não verificadas

Nenhuma afirmação desta nota depende delas. Ficam como leads, com o que falta
checar:

- **Dengue Forecasting Sprint brasileira, 2024/2025** — Araujo et al., medRxiv
  (**não verificado** — checar; 10.1101/2025.05.12.25327419). O preprint deu 403 no
  acesso direto. O que apareceu em busca (6 equipes, 5 estados, temporadas EW 41 →
  EW 40, foco probabilístico, ensemble adotado para 2025) **não foi confirmado no
  texto** e não deve ser citado como número.
- **Silva & Nery, "Comparative evaluation of machine learning strategies for
  short-term dengue forecasting in Brazilian capital municipalities"** —
  Int J Biometeorol (**não verificado** — checar; PubMed 42599321). Se confirmado,
  é o par brasileiro mais próximo em grão municipal.
- **"Predicting dengue incidence leveraging internet-based data sources. A case
  study in 20 cities in Brazil"** — *PLoS Negl Trop Dis* e0010071
  (**não verificado** — checar). Interessa pelo desenho multi-cidade com dado de
  internet.
- **ARBOALVO** — *PLoS Negl Trop Dis* (**não verificado** — checar;
  10.1371/journal.pntd.0012984).
- **"Dengue hospitalizations in Brazil: Forecasting with climatic and physicians'
  digital search data under real-world reporting delays"** — *PLOS Digital Health*
  (**não verificado** — checar). Alvo alternativo (hospitalizações) com atraso de
  reporte declarado; pode ser o desenho mais próximo em tratamento de atraso.
- Os **detalhes do Chen & Moraga 2025** (horizontes, lista de modelos) vêm do
  resumo de busca: o texto completo no PMC deu reCAPTCHA e o medRxiv deu 403.
  A citação em si está verificada; os **números** de desenho, não.

## Contra-evidência

- **O ganho pode simplesmente não existir.** Johansson 2019: skill baixo no início
  da temporada, e **mais baixo nas temporadas de alta incidência** — justamente
  onde a previsão valeria mais. Modelos que incluíam mais dado biologamente
  informativo tiveram skill **médio menor** que os simples.
- **Nenhum modelo domina em toda parte.** Wu 2025, em 180+ localidades: o que ganha
  é o ensemble, não um método. Isso enfraquece a expectativa de que *um* bloco de
  feature ganhe de forma limpa em todos os cortes.
- **Texto pode não estar sendo usado.** Tan et al. 2024: remover o componente de
  LLM empata ou melhora. É a razão do controle negativo obrigatório.
- **A linha aceita avaliar sem número.** Freitas 2025 não reporta score de skill
  nenhum — só bandas. Isso corta os dois lados: por um lado mostra que "WIS é o
  padrão" é mais nosso que do campo; por outro, um paper que reporta WIS **e** MAE
  está acima da média da linha.
- **Horizonte curto é o pior lugar para procurar ganho de feature.** Quanto mais
  curto o horizonte, mais da variância já está no próprio histórico.
- **A janela do nosso experimento é curta, e agora está contada.** A série de busca
  congelada vai de 2020-01-26 a 2024-12-29 e o alvo vai a 2026; com 104 semanas
  mínimas de treino, a grade só é avaliável em **157 semanas** (2022-01-02 a
  2024-12-29), e em 154 nos conjuntos que usam busca, contra as 557 do painel
  padrão (2014–2026), que não é a janela do paper ([plano](plano.md) §6). Menos semanas pontuadas = menos poder nas oito
  comparações pareadas da fatia 10. E como a comparação exige todos os conjuntos nas
  mesmas semanas, **uma feature só confina o paper inteiro**.

## Pendências / próximo passo

- [x] **Levar as citações para dentro do protocolo 00**: os seis baselines mais o
      ensemble, e o backbone TFT (Lim 2021) — **feito em 2026-11-20**, na revisão
      abaixo.
- [x] **Revisar o protocolo 00 tirando clima e busca das condições fixas** — o
      marcador `#comparados` da fatia 1. **Feito em 2026-11-20**: a revisão também
      fixou os conjuntos acumulados, o grão BR com UF declarada, os dois horizontes e as oito
      comparações.
- [x] **Decidir o ensemble como baseline** (Johansson 2019; Wu 2025) — **entra**,
      com o sem-texto na regra de decisão e o global descritivo, em 2026-11-20.
- [ ] **Registrar o valor mínimo do ganho no protocolo 00** — semana 2 do plano,
      antes de a primeira célula da grade ser calculada.
- [ ] **Escolher uma ou duas codificadoras de embedding** para a grade, e declarar
      as outras quatro como robustez.
- [ ] **Medir o InfoDengue com prazo fechado** — semana 3; se não convergir em uma
      semana, ele vira citação e o desvio fica registrado.
- [ ] **Medir UF e h=4 como robustez declarada** — semana 11.
- [ ] **Testar 2020 como robustez**, ao lado do corte de 2024 já medido.
- [ ] **Declarar o corte de maturidade do alvo** e por que o nosso não é nowcast
      (Bastos 2019; Xiao 2025).
- [ ] **Declarar horizonte 1 semana e grão BR como desvios** do padrão da linha —
      este arquivo já diz o porquê; falta a redação no manuscrito.
- [ ] **Rodar o manuscrito contra EPIFORGE 2020** antes da fatia 12.
- [x] **Inserir os DOIs da tabela de fontes no `articles/references.csv`** — feito
      em 2026-11-20 (13 linhas).
- [ ] **Verificar as cinco candidatas** marcadas acima.
- [ ] **Baixar os PDFs de acesso aberto** (Bracher 2021, Xiao 2025, Freitas 2025,
      Johansson 2019/PMC, Wu 2025, Chen & Moraga 2025) e arquivar em
      `articles/` — lembrando que PDF sob `articles/` é gitignored de propósito.
