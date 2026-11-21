# Revisão de literatura — o que a área fez, até onde cada linha chegou

**Estado:** ativo — 2026-11-21
**Papel no artigo:** insumo da seção de Trabalho relacionado (passo 4 do
[plano](plano.md)) e resposta pronta para a pergunta "o que já foi feito na área,
até onde cada estudo chegou, qual o estado da arte".

## Para que serve

Esta nota junta num texto só o que está espalhado em cinco lugares: os quatro
relatórios de estado da arte das famílias de representação de texto — [léxico e
regras](../articles/features-texto/relatorio.md), [vetores densos de texto
(embeddings)](../articles/embeddings/relatorio.md), [agrupamentos temáticos
(tópicos)](../articles/topicos/relatorio.md) e [extração estruturada por modelo
de linguagem (LLM)](../articles/llm-extracao/relatorio.md) — mais o levantamento
de desenho de experimento de [06](06-desenho-do-experimento.md). Todo número
citado abaixo vem de um desses arquivos, e o caminho de volta aparece fechando
cada seção.

Uma ressalva vale para tudo o que segue. As quatro famílias saíram de busca
sistemática com critérios explícitos de ano, volume de citações e qualidade do
veículo. A de tópicos partiu de 3.935 candidatos e reteve 48; a de embeddings,
de 1.057 e reteve 23; a de léxico, de 434 e reteve 35; a de LLM, de 916 e
reteve 10. O corte por citações remove por construção trabalho antigo ou pouco
citado. O que segue descreve uma amostra declarada, não um censo da área.

## A resposta curta

A área aprendeu a ler notícia e aprendeu a prever casos, em duas linhas de
trabalho que quase nunca se cruzam. Do lado da leitura há mais de vinte anos de
acúmulo: sistemas de regras escritas à mão (HealthMap, BioCaster, PADI-web),
depois classificadores estatísticos sobre palavras, depois vetores densos de
frase e de documento, depois modelos de tópicos e, desde 2023, extração
estruturada por modelo de linguagem. Do lado da previsão a área fechou um
protocolo rigoroso: janela de origem móvel, reajuste só com dados passados,
métrica probabilística, baselines declarados e comparação contra um modelo que
só repete o último valor observado.

**A ponte entre os dois lados quase não existe.** Medir quanto uma representação
de notícia agrega a uma previsão de casos, contra uma previsão que dispensa a
notícia, foi feito com esse desenho por um único grupo — Ghosh et al. (2017) —,
em inglês e chinês. O resto da literatura de texto mede acerto de leitura —
precisão, revocação e a média harmônica das duas (F1) — ou correlação
transversal, e não ganho preditivo.

**O estado da arte, em três frases.** A extração de eventos de notícia por
modelo de linguagem acerta país e doença com F1 entre 0,85 e 0,96 e erra
contagem de casos — o campo que a vigilância mais precisaria. A representação
densa de texto carrega problemas de geometria conhecidos e sem correção
pacífica. E a avaliação da qualidade dos modelos de tópicos é, ela própria,
pouco confiável: as métricas automáticas discordam entre si e do julgamento
humano.

**Onde este projeto entra.** O recorte — notícia de arbovirose em português,
agregada por semana, como conjunto de features de uma previsão avaliada por
ablação — não tem precedente direto em nenhuma das famílias levantadas. O
estudo mais próximo cede um dos três atributos em cada caso.

## O histórico

| Era | O que entra | O que a área mede |
|---|---|---|
| até ~2010 | Regras e dicionários escritos à mão; primeiros sistemas de alerta | Acurácia de classificação e de extração de nome; rapidez da detecção |
| ~2010–2017 | Classificadores estatísticos sobre palavras; volume de busca na internet | F1 em triagem; correlação entre volume de busca e casos |
| ~2013–2020 | Vetores densos (word2vec, GloVe, BERT); tópicos aplicados a notícia de doença | Qualidade intrínseca da representação; erro de previsão em poucos casos |
| ~2020–2026 | Tópicos neurais, BERTopic, LLMs; revisões sistemáticas | Reprodutibilidade e estabilidade; F1 de extração; custo |

**Até 2010, a leitura era um dicionário.** HealthMap carrega mais de 2.300
padrões de local e 1.100 de doença e declara 84% de acurácia sobre 778 relatos
num mês. BioCaster chega a 94,8% com naïve Bayes contra 92,1% de uma máquina de
vetores de suporte. PADI-web reporta 97,2% em validação cruzada e 92% em
avaliação externa. O limite desses sistemas é a localização: 80% de acerto no
campo de local contra 95% em doença e hospedeiro, e 68% dos sinais irrelevantes
vêm de local errado. O português aparece nesse período como "em desenvolvimento":
um surto de dengue no Ceará entre julho e setembro de 2008 não foi detectado.

**De 2010 a 2017, a estatística de superfície tomou conta da triagem.** A
contagem simples de termos (saco de palavras), ponderada pela raridade de cada
termo no acervo analisado (TF-IDF), basta para separar notícia que fala de
doença da que não fala, e os números são altos (F1 0,93 num dos sistemas, 94,8%
noutro). Mutuvi et al. (2020) mostram onde isso quebra: BERT chega a F1 86,25
contra 80,00 de uma máquina de vetores com TF-IDF e 77,5 de uma rede
convolucional, enquanto o sistema especializado em multilíngue cai a 43,48; os
classificadores clássicos zeram em polonês e chinês, e o BERT não. É também a
era do primeiro susto com sinal de busca: as correlações para dengue chegam a
0,83–0,99 incluindo o Brasil, e o Google Flu Trends colapsa de 0,91 para 0,29.
Madoff et al. (2011) mostram que a busca segue a epidemia em vez de antecedê-la.

**De 2013 a 2020, a representação passa a ser vetorial.** Ghosh et al. (2017)
acoplam um modelo de tópicos temporal a uma regressão autorregressiva e estimam
a contagem de casos uma semana à frente usando as tendências de tópico como
regressor externo. É o primeiro trabalho da amostra a confrontar uma
representação de notícia com um baseline que dispensa notícia, e continua sendo
o único a fazer isso com notícia de doença na escala de uma série temporal.
No mesmo período, Dieng et al. (2019) põem tópicos e palavras no mesmo espaço
vetorial, e a geometria dos embeddings vira tema: a média dos vetores de palavra
de um texto rende 54,81 de acurácia contra 29,19 do vetor do primeiro elemento
da frase (token) e 61,32 do GloVe.

**De 2020 a 2026, a área passa a medir a si mesma.** As revisões sistemáticas
chegam e o diagnóstico é desconfortável: dos 35 artigos que propõem modelos
neurais de tópicos entre 2019 e 2022, nenhum comparou os modelos em estabilidade
(Hoyle et al., 2022); numa revisão de 189 aplicações a texto curto, a medida de
quão bem o modelo prevê palavras que não viu (perplexidade) aparece em 22,04% dos
estudos, e copiar o número de tópicos de trabalhos anteriores sem testar
alternativas é classificado como tendência preocupante (Doogan et al., 2023).
Desde 2023 entra a extração estruturada por modelo de linguagem, com resultados
altos em país e doença e nulos em contagem.

## As cinco famílias, uma a uma

As duas primeiras seções vêm do mesmo relatório
([léxico](../articles/features-texto/relatorio.md)).

### Léxico, regra e contagem

**O que faz.** Um vocabulário escrito à mão mais regras de casamento dizem se um
texto fala de doença, de que doença e onde. É a abordagem com maior histórico e
a que sustenta os sistemas em operação.

**Até onde chegou.** Nos campos fáceis, quase no limite: 95% em doença e
hospedeiro, 94,8% no classificador do BioCaster. Nos campos difíceis, longe:
80% em local, F1 76,97% na extração de nome de doença, 0,66 por sentença na
classificação de evento do PADI-web. A pontualidade é o ponto mais disputado da
área — Barboza et al. (2013) medem 10,2 dias de antecedência sobre a fonte
oficial (intervalo de confiança de 95%: 6,7 a 13,8 dias) e o GPHIN é o primeiro
a reportar 56% de 578 surtos, enquanto Ganser et al. (2022) encontram 73,5% dos
eventos detectados alguma vez mas apenas 9,2% dentro de duas semanas, e 12 de 24
países sem nenhuma detecção oportuna.

**O limite declarado pelos próprios autores.** Ng et al. (2020) registram que
nenhum sistema de vigilância baseada em evento incorpora um algoritmo de
contagem de casos, e que os esquemas de marcação manual (anotação) não preveem o
campo de contagem (Conway 2010, Chanlekha 2010). A concordância entre anotadores
na contagem de eventos fica em 67%. Contagem acumulada não é tratada por nenhum
trabalho da família.

### Estatística de superfície

**O que faz.** Conta palavras, documentos por dia e tamanho de texto, sem
vocabulário curado.

**Até onde chegou.** É suficiente para triagem, e os números são estáveis entre
estudos independentes: 97,2% e 92% de acurácia, 0,94 de área sob a curva ROC,
F1 0,93. Collier et al. (2010) medem a frequência diária de documentos com
melhor detector em F1 0,63, e mostram que dia de semana rende 1,37 documento por
dia contra 0,49 no fim de semana. Na legibilidade, Crossley et al. (2011)
comparam fórmulas de comprimento com um índice de coesão: 49,3% e 44,3% contra
60,0% (t(598) = −2,635, p < 0,010). Lee et al. (2021) chegam a 99% de acurácia
com um modelo híbrido, igualam o melhor concorrente usando 30% dos dados de
treino, e o ganho é maior justamente quando há pouco dado.

**O limite.** O volume de cobertura acompanha disrupção econômica e social, não
morbidade. E há duas features que ninguém mediu: comprimento de documento como
variável preditiva e densidade lexical não aparecem em nenhum trabalho da
amostra.

### Embeddings densos

**O que faz.** Cada palavra, frase ou documento vira um vetor de números reais
com centenas de dimensões, obtido de um modelo treinado em texto massivo, no
lugar de uma contagem de palavras.

**Até onde chegou.** A conversão de texto em vetor é onde a família gasta mais
esforço, e os resultados mostram que a escolha de como agregar importa mais que
o modelo: 54,81 de acurácia com média dos vetores de palavra, 29,19 com o vetor
do primeiro elemento da frase (token), 61,32 com GloVe. Há um problema
geométrico conhecido: no BERT, duas palavras arbitrárias têm similaridade de
direção (cosseno) de 0,99, quase idênticas, o que exige correção — por agregação,
por remoção da direção que domina todas as representações (componente principal)
ou por reescalonamento das dimensões (branqueamento). Três linhas de correção
existem e elas discordam: Gao et al. (2021) relatam que uniformidade não leva a
melhores embeddings para transferência, enquanto Mu et al. (2018) e Su et al.
(2021) reportam ganho nessa métrica.

No uso para vigilância, a família é mais descritiva que preditiva: Huang et al.
(2018) descrevem, Jang et al. (2019) e Gautam et al. (2025) classificam texto e
não doença, Kim e Ahn (2021) detectam evento binário. Só dois trabalhos produzem
um valor epidemiológico quantitativo, e só Ghosh et al. (2017) confrontam esse
valor com um baseline sem notícia: o erro quadrático médio normalizado (NRMSE)
cai de 1,078 para 0,549 na dengue na China e de 1,574 para 0,626 na doença
mão-pé-boca, com ganho marginal na raiva (0,875 para 0,865).

**O limite.** O português aparece nas listas de modelos multilíngues e nunca é
avaliado; a distância entre línguas é suposta, não medida. Ghosh et al. (2017)
traduziram 87,94% dos artigos chineses para o inglês antes de processá-los. Não
há um único número de custo computacional na família.

### Tópicos

**O que faz.** Resume cada documento, ou cada semana de documentos, como uma
mistura de um número pequeno de temas latentes. O modelo mais usado da família é
o modelo probabilístico de temas (LDA, latent Dirichlet allocation): cada
documento é uma mistura de temas e cada tema uma distribuição sobre as palavras.
É a única família que produz, por construção, uma variável numérica por semana
pronta para entrar num modelo de série temporal.

**Até onde chegou.** Quando o alvo é o rótulo de um documento, o uso é amplo e
quase sempre com ganho reportado: o modelo supervisionado de Rodrigues et al.
(2018) supera os baselines da própria família; Chiu et al. (2024) concatenam o
vetor de tópicos a 22 preditores estruturados e elevam a área sob a curva ROC de
0,7532 para 0,7994. Quando o alvo é uma série temporal, a literatura encolhe
para dois trabalhos: Chuluunsaikhan et al. (2020) reduzem o RMSE do preço do
porco em 37% a 66% frente a quatro concorrentes, e Ghosh et al. (2017) já
descrito acima.

**O limite, e ele é o achado da família.** As métricas que a área usa para dizer
que um modelo de tópicos é bom não são confiáveis. Quatro critérios clássicos
aplicados ao mesmo conjunto de textos (corpus) escolhem 35, 45, 36 e 45 tópicos;
num conjunto de teste com 20 tópicos verdadeiros, cinco critérios escolhem 13, 8,
7, 30 e 59. Hoyle et al. (2021) mostram que a medida de quão associadas as
palavras de topo de um tema aparecem juntas (coerência) elege um vencedor quando
a avaliação humana não vê diferença, e que o modelo com a maior nota nessa
medida produz os tópicos com as palavras menos familiares aos anotadores (70% de
familiaridade contra mais de 90% dos demais). A estabilidade é pior que a média:
remover 50 de 6.638 documentos já muda os tópicos (Hecking e Leydesdorff, 2018),
e mesmo o método desenhado para maximizar reprodutibilidade chega a 0,8816 de
confiabilidade, abaixo de 1.

E o modo de falha que mais importa para nós está documentado pelos próprios
autores: para doenças de baixo interesse público, a cobertura de notícia pode
ser baixa mesmo durante um surto em curso, e nesse caso a estimativa fica
atrasada em relação ao pico real.

### Extração estruturada por LLM

**O que faz.** Em vez de contar palavras ou resumir temas, o modelo de linguagem
devolve campos explícitos — doença, local, data, número de casos — em formato
estruturado.

**Até onde chegou.** Nos campos fáceis, é a família com melhor desempenho
medido: Consoli et al. (2025) reportam F1 0,962 para país, 0,851 para doença e
0,869 para data. Al-Garadi et al. (2025) chegam a 0,88 de F1 e 95,9% a 98% de
acurácia na causa do óbito, contra 97,9% a 99,5% de anotadores humanos. O que
mais move o resultado não é o tamanho do modelo, e sim o formato pedido para a
saída em texto estruturado (JSON), que supera as alternativas (YAML e XML) com χ²
de 167,607 e 69,351 no teste de McNemar; o tipo de instrução pesa mais que o
tamanho do modelo (V de Cramér 0,42 contra 0,11).
Refinar o esquema de saída leva um mesmo modelo de 33% para 95% de acerto.
Modelo pequeno ajustado vence modelo grande sem ajuste: um FLAN-T5 de 780
milhões ajustado supera um GPT-3.5 de 175 bilhões sem ajuste.

**O limite.** Contagem de casos é o ponto fraco: 0,658 de F1 no melhor sistema
medido, e 0% numa heurística de linha de base. Duas ressalvas de reprodutibilidade
pesam. Ninguém mede se a saída muda quando a versão do modelo muda. E Schmidt et
al. (2024), medindo a mesma versão duas vezes, encontram texto idêntico em 69%
das vezes e diferença de conteúdo em 7%. Custo está medido em um trabalho só
(US$ 2 por 1.000 páginas, 11 segundos por arquivo contra 30 a 40 minutos
manuais). Fora um estudo em indonésio sobre desastres naturais, toda a amostra é
em inglês sobre notícia de surto, com gabaritos de 19 a 171 itens.

## O outro lado: como a área prevê casos

Enquanto a leitura de texto se desenvolvia, a previsão de arbovirose fechou um
protocolo próprio, levantado em [06](06-desenho-do-experimento.md). Oito eixos
organizam as decisões, e em cada um há uma escolha dominante.

- **Horizonte.** Uma semana é o mais comum; horizontes longos são mais raros e
  mais duros.
- **Alvo.** Agora-cast (estimar o presente ainda incompleto), previsão adiante ou
  um indicador indireto. A série do SINAN é reescrita retroativamente, o que
  torna o alvo móvel.
- **Grão espacial.** Município, estado ou país. Este projeto usa o mais grosso
  dos três, e as linhas por estado são atribuição — um artigo que cita três
  estados conta nos três, somando 7.223 menções para 4.369 artigos nacionais —,
  não partição.
- **Grão temporal e janela de treino.** Xiao et al. (2025) excluem 2020 do
  treino; os desenhos mais recentes discutem se isso é defensável.
- **Divisão de treino e teste.** Tashman (2000) e Bergmeir e Benítez (2012) são
  as referências para origem móvel.
- **Métrica.** Bracher et al. (2021) fixam o WIS (weighted interval score, uma
  métrica que pontua a distribuição de previsão inteira, além do valor
  central); a teoria vem de Gneiting e Raftery (2007).
- **Modo de avaliação.** Prospectivo ou retrospectivo, com EPIFORGE (2020) e
  Pollett et al. (2021) como listas de conferência.
- **Baseline.** Persistência, naive sazonal e, no caso brasileiro, o InfoDengue.

O ponto de referência concreto: na janela deste projeto, o erro absoluto médio
da persistência é 9.022 casos; na janela longa de 470 semanas, é 4.358. O mesmo
baseline muda de patamar conforme a janela, o que é o argumento para declarar a
janela sempre junto com o número.

## O que converge entre estudos independentes

Três achados aparecem em grupos de estudos que não se citam:

1. **A geolocalização é o campo fraco.** 80% de acerto contra 95% em doença,
   68% dos sinais irrelevantes vindos de local errado, e apenas 2 de 27
   sistemas de localização acima de 0,7 de revocação.
2. **A cobertura de notícia segue interesse público, não incidência.** Ghosh et
   al. (2017), Tizzoni et al. (2020) e Pruss et al. (2019) chegam ao mesmo ponto
   por caminhos distintos, e McGough et al. (2017) quantificam o atraso em duas a
   três semanas.
3. **As métricas de qualidade de tópicos não concordam entre si nem com o
   julgamento humano.** Zheng et al. (2023), Gan e Qi (2021), Meaney et al.
   (2023), Morstatter e Liu (2016) e Hoyle et al. (2021) medem sistemas
   diferentes e chegam à mesma discordância.

## O que está em disputa

Nem tudo na área converge. A tabela abaixo dá os pares em conflito, com quem
está de cada lado.

| Divergência | Um lado | O outro |
|---|---|---|
| Notícia ajuda a prever casos? | Ghosh et al. (2017): reduz o erro em 8 de 10 combinações país-doença | McGough et al. (2017): melhora no máximo 7% e piora até 60% |
| A notícia chega antes? | Barboza et al. (2013, 2014), PADI-web, GPHIN: dias a semanas à frente | Ganser et al. (2022): só 9,2% em duas semanas; Bahk et al. (2015): fonte formal atrasada 1,26 dia |
| Tópicos agregam além de features brutas? | Rodrigues et al. (2018), Chiu et al. (2024): sim | Hughes et al. (2020): 10 tópicos igualam 9.256 códigos clínicos, e ficam abaixo de árvores sobre as features brutas |
| O LDA clássico é estável? | Hoyle et al. (2022): 0,22 de distância contra 0,42 a 0,49 dos modelos neurais | Hecking e Leydesdorff (2018): menos robusto que a análise de componentes principais |
| Correção de geometria ajuda? | Mu et al. (2018), Su et al. (2021): ganho na métrica de uniformidade | Gao et al. (2021): uniformidade não leva a melhor transferência |
| Modelo mais complexo compensa na extração? | Kim et al. (2020) | Abbood et al. (2020) |

A leitura que reconcilia o primeiro par, e que os próprios dados de McGough et
al. (2017) sustentam: a notícia ajuda quando se extrai dela uma estrutura
latente e estável, e falha quando se usa a contagem bruta de menções. Essa
reconciliação é uma hipótese de trabalho, não um resultado replicado.

## A ponte que quase ninguém construiu

Somando as cinco famílias, o que existe é isto: a área sabe medir se um sistema
lê bem uma notícia, e sabe medir se um modelo prevê bem uma série. O desenho que
liga as duas coisas — a representação de texto entra como conjunto de features
numa previsão, e o ganho é medido contra a mesma previsão sem o texto — aparece
em Ghosh et al. (2017) e, na família de tópicos, em Chuluunsaikhan et al.
(2020), com o defeito de não ter baseline ingênuo nem ablação só-série.

Fora esses dois, o que a literatura oferece são correlações transversais
(Pruss et al., 2019), medições de atenção em vez de casos (Tizzoni et al.,
2020), tarefas de classificação de documento (Rodrigues et al., 2018; Chiu et
al., 2024) ou descrições temáticas (de Melo e Figueiredo, 2021). E nenhum mede
se a estabilidade da representação se traduz em estabilidade da previsão.

## Onde o nosso recorte fica

O recorte tem três atributos: notícia de arbovirose, em português, agregada por
semana. Nenhum estudo levantado reúne os três.

| Estudo | Arbovirose | Semanal | Português |
|---|---|---|---|
| Ghosh et al. (2017) | dengue entre outras | sim | não — inglês e chinês |
| McGough et al. (2017) | Zika | sim | não |
| Chuluunsaikhan et al. (2020) | não — preço de mercado | sim | não — coreano |
| Pruss et al. (2019) | Zika | não — correlação transversal | sim, entre outras línguas |
| de Melo e Figueiredo (2021) | não — COVID-19 | não — descritivo | sim |
| Tizzoni et al. (2020) | Zika | sim | não — mede atenção, não casos |

Duas coisas que o texto do artigo precisa declarar. A primeira: a pergunta sobre
contribuição relativa de features já foi feita para clima e busca no Brasil, por
Koplewitz et al. (2022), em 20 cidades. A segunda: arquitetura não é a
contribuição — Silva e Nery (2026), Palmer et al. (2026) e o trabalho do Sprint
et al. no PNAS publicam modelos preditivos de dengue no Brasil em ritmo
constante. O que este projeto pode reivindicar é a combinação: representação de
texto em português, medida como ganho sobre um desenho que já tem clima, busca e
histórico, com ablação e controle negativo.

## Contra-evidência

O que joga contra a nossa hipótese, e que o artigo precisa tratar e não
contornar:

- **A notícia pode não agregar nada.** McGough et al. (2017) mediram piora de até
  60% no erro relativo com sinal de notícia. Se o mesmo acontecer aqui, o
  resultado é negativo e é isso que se reporta.
- **O ganho pode não ser detectável.** 157 semanas pontuadas (154 nos conjuntos
  com busca) para oito comparações pareadas com correção para comparações
  múltiplas. Um ganho pequeno pode ficar dentro do ruído, e isso é limitação
  declarada antes do resultado, não desculpa depois.
- **A cobertura da nossa fonte pode ser baixa onde importa.** O corpus tem 318
  semanas sem artigo nenhum no intervalo de 1.283 semanas, e 4,7 artigos por
  semana no total nacional. Semana sem notícia precisa de indicador explícito
  para o modelo não ler ausência como sinal neutro.
- **Vazamento de dados.** A data de corte de treino dos codificadores de texto é
  desconhecida, o corpus vai até 2026 e 2024 foi o ano recorde de dengue.
- **O descompasso espacial.** O corpus é de uma fonte nacional e as linhas por
  estado são menção no texto. As linhas de estado não somam a linha do Brasil.
- **Contagem acumulada.** Só 24% dos artigos declaram número de casos, e é
  número acumulado, não semanal. Nenhum trabalho da literatura de léxico trata
  disso.

## O que ficou fora desta nota

- **A auditoria de conformidade das famílias.** Cada família tem um
  `revisao.json` que confere se as fichas sustentam o relatório. Três das quatro
  estão marcadas como não conformes: embeddings (uma divergência, atribuição de
  país em Ghosh 2017), léxico (uma troca de atribuição entre BioCaster e
  Brownstein) e tópicos (quatro erros de glosa e sete afirmações órfãs). A de
  extração por LLM está conforme. Os números citados acima vieram dos
  relatórios, não das fichas; onde a divergência toca um número usado aqui, ele
  precisa ser reconferido na ficha antes de entrar no manuscrito.
- **As sete referências não mobilizadas pela família de tópicos**, registradas
  na seção "O que ficou de fora" do relatório dela, com o motivo de cada uma.
- **O detalhe de cada estudo.** Esta nota dá o achado e o número; a ficha de
  cada artigo, com desenho, dados e ressalva, está em
  `articles/<família>/fichas/`.
- **Previsão de arbovirose no Brasil fora do eixo de texto.** Está em
  [06](06-desenho-do-experimento.md), que é o lugar dela.

## Pendências

- [ ] reconferir nas fichas os números desta nota que caem nas três famílias
      marcadas como não conformes, antes de o texto virar manuscrito
- [ ] decidir se esta nota vira a seção de Trabalho relacionado do passo 4 ou se
      serve só de fonte para ela
- [ ] registrar em [articles/references.csv](../articles/references.csv) as
      referências citadas aqui que ainda não estejam lá
- [ ] escrever a versão em inglês quando a seção de manuscrito for redigida — o
      manuscrito é em inglês, esta nota é em português
- [ ] o medidor de estilo acusa um erro que é falso positivo: o sobrenome "Nery",
      na citação Silva e Nery (2026), casa com o termo `NER` da lista de jargão.
      Não há glosa possível para um sobrenome. O erro fica registrado aqui para
      não passar por termo sem apresentação numa revisão futura.

O medidor foi rodado com a lista de termos das quatro famílias juntas
(`--termo` de cada `.claude/workflows/familias/*.json`), uma vez que esta nota
atravessa as quatro. Comandos e contagem, em 2026-11-21:

```
python3 scripts/checar_estilo_relatorio.py notes/revisao-bibliografica.md \
    $(termos das quatro famílias) --mostrar 12
→ 1 ERRO (o falso positivo de NER) · 2 AVISO (parágrafo denso na abertura e a
  lista de pendências lida como prosa) · 0 em orações empilhadas, adjetivo
  inflado, muleta e hedge
```
