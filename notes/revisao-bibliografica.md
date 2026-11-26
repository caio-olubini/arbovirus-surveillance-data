# Revisão de literatura — o que a área fez, até onde cada linha chegou

**Estado:** ativo — 2026-11-21
**Papel no artigo:** insumo da seção de Trabalho relacionado (passo 4 do
[plano](plano.md)) e resposta pronta para a pergunta "o que já foi feito na área,
até onde cada estudo chegou, qual o estado da arte".

## Para que serve

Esta nota responde à pergunta "o que já foi feito na área, até onde cada estudo
chegou" a partir dos artigos, não das sínteses escritas sobre eles. A base é o
que está fichado em [articles/](../articles/README.md): 118 artigos, cada um com
as afirmações que sustentam o texto, a frase literal do autor e o número da
página — 590 afirmações ao todo. Onde um número decide uma frase, ele foi
conferido no PDF do próprio artigo, porque a ficha registra cinco afirmações por
artigo, e isso é uma seleção, não a extração inteira.

**Até onde esta versão vai.** A família de léxico e de estatística de superfície
(37 artigos) já foi reescrita sobre as fichas. As de vetores densos de texto
(embeddings), de agrupamentos temáticos (tópicos), de extração estruturada por
modelo de linguagem (LLM) e o desenho de previsão ainda vêm dos relatórios de
família e da nota [06](06-desenho-do-experimento.md), e serão reescritas do
mesmo modo. A seção [Fontes](#fontes-desta-nota) dá o caminho de volta de cada
artigo citado.

Uma ressalva vale para tudo o que segue. As quatro famílias saíram de busca
sistemática com critérios explícitos de ano, volume de citações e qualidade do
veículo. A de tópicos partiu de 3.935 candidatos e reteve 48; a de vetores
densos, de 1.057 e reteve 23; a de extração por modelo de linguagem, de 916 e
reteve 10; a de léxico, de 434 e reteve 35 — mas a família tem 37 fichas, e as
duas a mais estão registradas nas [pendências](#pendências). O corte por
citações remove por construção trabalho antigo ou pouco citado. O que segue
descreve uma amostra declarada, não um censo da área.

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
vetorial, e a geometria dos vetores densos (embeddings) vira tema: a média dos
vetores de palavra
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

As duas primeiras seções vêm da família de 37 artigos fichados em
[articles/features-texto](../articles/features-texto/README.md).

### Léxico, regra e contagem

**O que faz.** Um vocabulário escrito à mão mais regras de casamento dizem se um
texto fala de doença, de que doença e onde. É a abordagem com maior histórico e
a que sustenta os sistemas em operação.

**Nos campos fáceis, a abordagem chegou ao limite do que se mede.** A extração
combinada do PADI-web acerta 95% em doença e hospedeiro e 85% em número de
casos; o classificador de relevância do BioCaster acerta 94,8%, contra 92,1% de
uma máquina de vetores de suporte no mesmo dado. Quando o PADI-web foi medido
sobre 100 artigos anotados por dois epidemiologistas, caiu para 92% — cinco
pontos abaixo dos 97,2% da validação cruzada —, e os autores registram a queda
em vez de reportar só o número maior.

**Nos campos difíceis, ainda longe.** Local é o campo fraco: 80% no PADI-web e
76,97% na extração de nome de doença no BioCaster. O HealthMap casa cada palavra
contra um dicionário de mais de 2.300 padrões de lugar e 1.100 de doença. Acerta
84% dos 778 alertas de um mês, e acerta 91% quando a fonte é o ProMED, curado à
mão, contra 81% no Google News. Os sistemas mais novos de localização não
resolvem o problema: numa comparação de 27 deles sobre 26 conjuntos públicos, 21
passam de 0,7 de precisão e só 2 passam de 0,7 de revocação, a fração dos
lugares mencionados que o sistema encontra.

**A pontualidade é o ponto mais disputado da área.** Barboza et al. (2013)
medem 10,2 dias de antecedência sobre a notificação oficial da OMS ou da OIE
(intervalo de confiança de 95%: 6,7 a 13,8 dias), e 93% de sensibilidade quando
os sete sistemas são somados. Barboza et al. (2014) medem 98% de 86 eventos
detectados antes do boletim oficial. O GPHIN, medido pela própria OMS, foi a
primeira fonte a captar 56% dos 578 surtos que a organização verificou entre
1998 e 2001. Do outro lado, Ganser et al. (2022) encontram 73,5% dos surtos
cobertos alguma vez, mas só 9,2% dentro de duas semanas em torno do início — e,
entre os 24 países do estudo, o HealthMap não detectou nenhum surto a tempo em
12 deles (50%). Bahk et al. (2015) medem o atraso pelo lado oposto: o relato
oficial chega 1,26 dia depois da notícia (p = 0,002), e em 70% dos 111 surtos a
notícia vem primeiro.

Os dois lados dessa disputa medem objetos diferentes, e a diferença não se
resolve. Barboza mede quantos dias o sinal de mídia precede a notificação
oficial de um evento que já se conhece. Ganser mede se o sinal cai dentro de uma
janela de tempo contada do início do surto, exista ou não notificação oficial.
Antecedência contra um registro oficial, portanto, não se traduz por si só em
alerta precoce, e o número de dias de vantagem depende inteiramente da
referência escolhida.

**O limite estrutural do dicionário.** Um dicionário reconhece só o que está
cadastrado, e ampliá-lo é trabalho manual. Os próprios autores do HealthMap
documentam o caso: a cidade de Fond du Lac aparece no texto de uma notícia, não
está no dicionário e não é reconhecida. Brownstein et al. (2008) descrevem a
manutenção das listas de doença e de lugar como ambígua, coloquial e sujeita a
mudança. O HealthMap erra em 11% dos alertas no campo de local e 6% no de
doença; sobre os 778 alertas de um mês, 123 (16%) precisaram de correção de um
analista humano.

**O limite que os próprios autores declaram.** Contagem de casos é o campo que
nenhum sistema entrega. Ng et al. (2020) registram que nenhum sistema de
vigilância baseada em evento incorpora um algoritmo que extraia contagem, e que
existem apenas peças soltas para montá-lo. Os esquemas de marcação manual do
texto (anotação) não carregam o campo, e a concordância entre anotadores depende
do que se mede: é alta no tipo do evento (0,87 e 0,90 em Chanlekha et al., 2010)
e baixa no número de eventos (67% em Conway et al., 2010). Carlson et al. (2023)
são a exceção — 2.789 relatos oficiais lidos à mão, com campo de casos e de
mortes —, e o preço é a leitura humana de cada relato.

**O português aparece como ausência.** Collier (2010) registra que a epidemia de
dengue no Ceará, entre julho e setembro de 2008, passou sem detecção, e atribui
a falha à falta de capacidade em português naquele momento. You et al. (2020),
sobre o Zika de 2016, encontram 162 relatos em português e 140 em espanhol,
contra apenas 65 em inglês — e analisam só os ingleses. A língua que fica de
fora é onde a doença estava.

### Estatística de superfície

**O que faz.** Conta palavras, documentos por dia e tamanho de texto, sem
vocabulário curado.

**Até onde chegou na triagem.** É suficiente para separar notícia de doença de
notícia que não é, e o resultado é alto: sobre um conjunto de textos em 6
idiomas (corpus), o BERT chega a F1 86,25 e uma máquina de vetores de suporte
sobre contagem ponderada pela raridade de cada termo (TF-IDF) chega a 80,00, com
uma rede convolucional em 77,50. O sistema especializado em multilíngue cai a
43,48, e os classificadores clássicos zeram em polonês e chinês, onde o BERT não
zera. A contagem pura também sustenta detecção de surto: Collier (2010) usa a
frequência diária de documentos por par doença-país, mede o melhor detector em
F1 0,63, e mostra que dia de semana rende 1,37 documento contra 0,49 no fim de
semana. Purgar as contagens de 1 ou 2 documentos sobe o F1 em cerca de 1 a 1,5
ponto.

**Onde a medida de superfície quebra.** Duas famílias de estudos medem isso e
chegam ao mesmo lugar. Pitler e Nenkova (2008) acham que caracteres por palavra,
palavras por frase e comprimento quase não explicam a nota humana de
legibilidade: das métricas de superfície, só o comprimento do artigo aparece, e
com correlação de −0,37. O vocabulário sobe a 0,63 e as relações entre orações a
0,48; juntas, oito medidas chegam a explicar 77,6% da variação (R² = 0,776).
Chae e Nenkova (2009) usam medidas da estrutura da frase e acham correlação
fraca: o modelo separa tradução automática de tradução humana com 87% de acerto,
separar tradução boa de ruim cai para 61%, e cruzar de domínio derruba para 57%.
Crossley et al. (2011) fecham o padrão numa tarefa de legibilidade: as fórmulas
de comprimento acertam 49,3% e 44,3% dos 300 textos, contra 60,0% de um índice
que mede coesão.

**O meio-termo entre os dois.** Lee et al. (2021) mostram que a escolha não é
entre contar e representar. O modelo híbrido, que soma 255 medidas linguísticas
a um modelo de linguagem treinado em texto massivo (transformer), chega a 99% de
acurácia, iguala o melhor concorrente usando 30% dos dados de treino, e o ganho
é maior justamente onde há menos dado. O próprio artigo registra que o ganho
encolhe conforme o conjunto de treino cresce.

**O limite.** O volume de cobertura acompanha disrupção econômica e social, não
doença. Brownstein et al. (2008) medem isso sobre o Google News: a frequência
com que um patógeno aparece na mídia se relaciona com a disrupção potencial, não
com a mortalidade, e a cobertura é enviesada para países com mais veículos de
imprensa. Duas medidas que interessam a este projeto não aparecem em nenhum
trabalho da família: comprimento de documento como variável preditiva e
densidade lexical.

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
  extração por LLM está conforme. A reescrita sobre as fichas é também a
  conferência dessa divergência, e ela já foi feita para a família de léxico: a
  troca não sobreviveu à reescrita. As outras três famílias seguem com números
  vindos do relatório até a fatia delas.
- **As sete referências não mobilizadas pela família de tópicos**, registradas
  na seção "O que ficou de fora" do relatório dela, com o motivo de cada uma.
- **O detalhe de cada estudo.** Esta nota dá o achado e o número; a ficha de
  cada artigo, com desenho, dados e ressalva, está em
  `articles/<família>/fichas/`.
- **Previsão de arbovirose no Brasil fora do eixo de texto.** Está em
  [06](06-desenho-do-experimento.md), que é o lugar dela.

## Fontes desta nota

Cada artigo citado no corpo, com a chave da ficha que guarda as afirmações, a
frase literal do autor e a página. As fichas estão em
`articles/<família>/fichas/` e os PDFs em `articles/<família>/`.

### Léxico, regra e contagem · estatística de superfície

| Autor | Ano | Grupo | Ficha |
|---|---|---|---|
| Arsevska et al. | 2018 | aplicação | `arsevska2018web` |
| Bahk et al. | 2015 | aplicação | `bahk2015timeliness` |
| Barboza et al. | 2013 | aplicação | `barboza2013evaluation` |
| Barboza et al. | 2014 | aplicação | `barboza2014performance` |
| Brownstein et al. | 2008 | aplicação | `brownstein2008surveillance` |
| Carlson et al. | 2023 | aplicação | `carlson2023who` |
| Chae & Nenkova | 2009 | representação | `chae2009fluency` |
| Chanlekha et al. | 2010 | aplicação | `chanlekha2010spatial` |
| Collier et al. | 2008 | aplicação | `collier2008biocaster` |
| Collier | 2010 | aplicação | `collier2010unusual` |
| Collier | 2011 | aplicação | `collier2011cross` |
| Consoli et al. | 2025 | aplicação | `consoli2025knowledge` |
| Conway et al. | 2010 | aplicação | `conway2010disease` |
| Crossley et al. | 2011 | representação | `crossley2011readability` |
| Freifeld et al. | 2008 | aplicação | `freifeld2007healthmap` |
| Ganser et al. | 2022 | aplicação | `ganser2022global` |
| Gritta et al. | 2020 | aplicação | `gritta2020pragmatic` |
| Hu et al. | 2023 | aplicação | `hu2023location` |
| Keller et al. | 2009 | aplicação | `keller2009unstructured` |
| Keller et al. | 2009 | aplicação | `keller2009vocabulary` |
| Klenner & Ailloud | 2009 | representação | `klenner2009coreference` |
| Kriesch & Losacker | 2025 | aplicação | `kriesch2025geolocated` |
| Lee et al. | 2021 | representação | `lee2021text` |
| Madoff et al. | 2011 | aplicação | `madoff2011monitoring` |
| de Melo & Figueiredo | 2021 | aplicação | `melo2021news` |
| Meng et al. | 2022 | aplicação | `meng2022biocaster` |
| Milinovich et al. | 2013 | aplicação | `milinovich2013internet` |
| Mutuvi et al. | 2020 | aplicação | `mutuvi2020multilingual` |
| Leal-Neto et al. | 2016 | aplicação | `neto2016digital` |
| Ng et al. | 2020 | aplicação | `ng2020nlp` |
| Pitler & Nenkova | 2008 | representação | `pitler2008revisiting` |
| Schwind et al. | 2014 | aplicação | `schwind2014local` |
| Snow et al. | 2008 | aplicação | `snow2008crowdsourcing` |
| Syed et al. | 2023 | aplicação | `syed2023geospatre` |
| Valentin et al. | 2020 | aplicação | `valentin2020padi` |
| Valentin et al. | 2021 | aplicação | `valentin2021padi` |
| You et al. | 2020 | aplicação | `you2021text` |

## Pendências

- [ ] reescrever sobre as fichas as quatro famílias que faltam — vetores densos
      (23), tópicos (48), extração por LLM (10) — e o desenho de previsão, que
      sai de [articles/references.csv](../articles/references.csv)
- [ ] decidir o que fazer com as duas fichas de léxico sem linha na bibliografia
      e fora do funil registrado em `search.json` (35 selecionados contra 37
      fichas): `klenner2009coreference` e `snow2008crowdsourcing`. Ambas têm PDF
      e ficha, e nenhuma das duas aparece em `selected`, em
      `considered_not_selected` ou em `rejected_by_gate`
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
atravessa as quatro. Comandos e contagem, em 2026-11-25:

```
python3 scripts/checar_estilo_relatorio.py notes/revisao-bibliografica.md \
    $(termos das quatro famílias) --mostrar 15
→ 1 ERRO (o falso positivo de NER) · 0 AVISO · 0 em orações empilhadas,
  parágrafo denso, adjetivo inflado, muleta e hedge
```
