# Ideias soltas

Caixa de entrada. Ideia que ainda não virou caminho com hipótese e plano fica
aqui. Quando amadurecer, sai daqui e ganha arquivo próprio numerado.

Formato: uma linha de título, um parágrafo curto de contexto, e uma linha de
referência se houver.

---

## Sentimento / emoção no texto

Além de "quanto se falou", "como se falou" (medo, alarme, normalização). Precedente
mais próximo: Konhar 2026, *PLoS NTD* 20(3):e0013378 — VADER + LDA sobre notícias
e comentários na Índia; achou descompasso atenção-carga (dengue = 89,9% da carga,
53,2% da atenção digital). VADER é inglês; para PT precisaria de léxico próprio
ou modelo multilíngue. Encaixaria como feature extra do caminho 01, não como braço.

## Peso por gravidade tipo "Heat Index"

HealthMap tem um índice de calor e o Argus tem estágios P0–P4/R. Ideia: em vez de
contar artigos, pontuar cada artigo por gravidade declarada. Já está contemplado
como `news_severity` no caminho 01 — registrar aqui só para não perder a origem.

## Boletins do Ministério da Saúde como segundo corpus textual

204 PDFs, 2019–2026, sem parser. Vantagem: são nacionais, semanais (irregular),
oficiais — o oposto da notícia em termos de viés. Poderiam virar um braço extra
ou um controle para separar "sinal epidemiológico" de "atenção midiática".
Custo: parser de PDF + extração de tabelas. Fora do escopo atual.

## Geoparsing fino (município)

Tentador, mas Krauer & Schmid 2022, *Epidemics* 41:100656
([doi:10.1016/j.epidem.2022.100656](https://doi.org/10.1016/j.epidem.2022.100656))
mostra geocoding correto só em ~34–60% dos casos, e piora com topônimo histórico
ou regional. Além disso a notícia é nacional — geocodificar não cria resolução
espacial que o texto não tem. Manter em UF/BR.

## Menções a vetor e controle como proxy de mobilização

Contar "Aedes", "fumacê", "criadouro", "mutirão", "visita domiciliar" ao longo do
tempo. É léxico (caminho 01) mas com hipótese diferente: não mede a doença, mede
a *resposta*. Pode ser um subconjunto interessante do léxico.

## Cascata regra → LLM

Usar regra/regex para os casos fáceis (a maioria) e LLM só nos ambíguos. Reduz
custo do caminho 04 e reaproveita o léxico do 01. Só faz sentido se o 04 for
adiante.

## Anotação: uma amostra, dois usos

A amostra anotada à mão serve ao caminho 01 (precisão/recall do léxico) **e** ao
caminho 04 (validação da extração por LLM). Anotar uma vez, com schema que sirva
aos dois. Decidir o schema antes de começar a anotar.
