#!/usr/bin/env python3
"""Checagem OBJETIVA de estilo de um relatório do workflow reference-research.

O relatório tem uma regra de escrita — português claro, termo técnico entre
parênteses ao lado, número sempre dentro da frase — e uma parte dessa regra é
contável. Esta é a parte contável, e ela é script e não agente por um motivo
prático: agente não conta palavra igual duas vezes, e um limite que se move a
cada rodada não é um limite. O que NÃO é contável (a glosa ficou clara para
quem lê? a frase ficou opaca apesar de curta?) continua com o agente revisor.

AS SEIS MEDIDAS, e por que cada uma:

  1. ORAÇÕES POR FRASE — quantas orações a frase empilha por subordinação.
     Substitui a contagem de palavras, que media a coisa errada.
  2. TERMO SEM GLOSA  — termo técnico que aparece FORA de parênteses antes de
     qualquer ocorrência entre parênteses.
  3. DENSIDADE        — jargão por 100 palavras, por parágrafo.
  4. ADJETIVO INFLADO — "robusto", "abrangente", "crucial". Não informam: quem
     escreve não escolheu entre "robusto" e "frágil", preencheu espaço.
  5. MULETA           — "vale ressaltar", "em suma", "além disso". Anunciam que
     algo será dito em vez de dizer.
  6. HEDGE            — "pode potencialmente", "tende a sugerir". Empilham
     incerteza sobre incerteza, e a frase deixa de afirmar.

POR QUE A MEDIDA 1 MUDOU (2026-11-10). A versão anterior contava PALAVRAS por
frase, com erro acima de 45. Isso media a coisa errada. Uma frase de 50 palavras
com uma oração é longa e legível — é o ritmo de quem escreve com calma, e é o
ritmo da referência de voz desta pesquisa. Uma frase de 30 palavras com cinco
orações é curta e ilegível. O contador de palavras reprovava a primeira e
aprovava a segunda, que é exatamente o avesso do que se quer. O que torna uma
frase opaca é o ANINHAMENTO: quantas orações o leitor tem que segurar na cabeça
antes de chegar ao ponto. Contar isso acerta os dois casos.

O tamanho da frase continua sendo MEDIDO — mediana, p90, máxima e desvio-padrão
saem em `medidas` — mas não é mais GATE. O desvio-padrão entrou junto porque é o
único jeito de ver o vício de RITMO: quatro relatórios escritos por modelos
diferentes deram desvio 11,7 a 12,3, praticamente o mesmo número, o que é a
assinatura de prosa que alterna sempre no mesmo compasso.

O QUE NÃO É GATE, E POR QUÊ. Voz passiva e travessão são MEDIDOS e não julgados.
Os dois são legítimos em prosa de método ("o modelo foi treinado em 12 mil
pares") e legítimos como recurso de quem escreve ("o sinal — e só ele — aparece
em julho"). Sem uma referência de voz medida para comparar, qualquer limite que
eu inventasse seria chute com cara de critério. Eles saem em `medidas` para o
revisor olhar com o número na mão, e viram gate quando houver referência.

O QUE A CHECAGEM 2 QUER DIZER, na prática. A regra do relatório é escrever o
português primeiro e deixar o termo ao lado:

    "os vetores ficam todos parecidos entre si (anisotropia)"

Então a PRIMEIRA aparição de um termo da lista tem que estar dentro de um
parêntese. Depois disso o termo está apresentado e pode ser usado à vontade.
Parêntese que só contém citação ou chave — "(Reimers, 2019)", "(09, 10, 12)" —
NÃO conta como glosa: quem escreveu não apresentou nada. Parêntese com dígito
dentro de uma palavra, ao contrário, conta: "(word2vec)" apresenta o termo.

Uso:
    python3 -I scripts/checar_estilo_relatorio.py articles/embeddings/relatorio.md \\
        --termo pooling --termo embedding --termo encoder

Sai com código 1 se houver ERRO. `--json` para saída legível por máquina.

A LISTA DE TERMOS NÃO MORA AQUI. Ela mora em ESTILO.termos, no
.claude/workflows/reference-research.js — é lá que se sabe qual jargão é
jargão para cada família de técnicas, e é o workflow que passa a lista para cá.
Duas listas seriam duas verdades. As LISTAS DE VÍCIO (adjetivo inflado, muleta,
hedge), ao contrário, moram AQUI, junto com os limites: elas são sobre prosa em
português, não sobre uma família de técnicas, e valem igual para qualquer tema.
O script imprime os limites que usou, então divergência entre o que o workflow
acha e o que foi medido aparece na saída.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

# --- a referência de voz ----------------------------------------------------
# notes/voz-de-referencia.md guarda dois trechos escritos à mão, e é a régua das
# medidas que NÃO são gate. O script lê o arquivo e imprime a comparação ao lado
# do que mediu, em vez de ter os números da referência fixos aqui: número fixo
# vira número errado no dia em que a referência for editada, e ninguém lembra de
# atualizar constante.
#
# POR QUE A REFERÊNCIA NÃO VIROU GATE, que era o plano. Ela foi medida, e a
# medição derrubou três das quatro hipóteses:
#
#   travessão   referência 7,1 por mil — DENTRO da faixa dos relatórios (5,9 a
#               7,8). Quem escreve à mão usa travessão tanto quanto a máquina.
#   voz passiva referência 4,7 por mil — ACIMA de todos os quatro relatórios
#               (1,0 a 1,8). Se há desvio, é dos relatórios usarem de menos.
#   ritmo       desvio-padrão 11,7 na referência — na PONTA BAIXA dos relatórios
#               (11,7 a 12,3). A hipótese de compasso uniforme não se sustenta.
#   tamanho     mediana de 28 palavras e máxima de 59, contra mediana de 18 a 22
#               e máxima de 45 nos relatórios. A referência escreve MAIS longo.
#               Isto é o que justifica a troca do contador: o limite antigo, de
#               45 palavras, reprovava a própria voz que se quer produzir.
#
# As densidades (muleta, adjetivo, hedge) também não podem ser calibradas aqui:
# zero ocorrências em 424 palavras não é evidência de zero, é o resultado mais
# provável mesmo que a taxa da referência seja igual à dos relatórios. Amostra
# pequena não calibra evento raro.
#
# Então o que sobra da referência é isto: ela CONFIRMA o gate de aninhamento
# (nenhuma frase dela passa de quatro orações) e dá o número de comparação para
# o revisor. Gate que a medição não sustenta é pior que gate nenhum, porque
# carrega autoridade de número sem ter número por trás.
REFERENCIA_PADRAO = 'notes/voz-de-referencia.md'


# --- os limites -------------------------------------------------------------
# Calibrados contra os quatro relatórios que existem em articles/*/relatorio.md
# (2026-11-10). Os números medidos neles:
#
#   orações por frase    mediana 1–2 · p90 3–4 · máxima 7
#   adjetivo inflado     0,25 a 1,04 por mil palavras
#   muleta               0,37 a 0,69 por mil palavras
#   hedge                0 a 0,12 por mil palavras
#   densidade de jargão  mediana 2,2% · máxima 7,8% por parágrafo
#
# COMO LER ESTES LIMITES. Eles são ALVO, não descrição — mas só onde o alvo está
# acima do que já se escreve. Os quatro relatórios foram escritos sob a regra de
# clareza, e nas medidas de vício eles já estão no chão: meio adjetivo inflado
# por mil palavras é um em cada dois mil, e não há o que apertar aí sem inventar
# falta. Por isso essas três categorias nascem com AVISO baixo e ERRO alto: o
# AVISO mostra o número para o revisor olhar, e o ERRO só dispara em densidade
# que ninguém defende.
#
# O ANINHAMENTO É A EXCEÇÃO, e é o gate que de fato morde. A medida antiga
# (palavras por frase) já tinha achatado todo relatório em 45 palavras de
# máxima, e o efeito colateral foi empurrar o problema para dentro da frase:
# cortada em duas, a frase longa virou duas frases com as mesmas orações
# empilhadas. Seis orações numa frase é o teto do que se lê de uma vez.
LIMITE_ORACOES = 6         # ERRO: frase que empilha 6 orações ou mais
AVISO_ORACOES = 5          # AVISO a partir daqui
LIMITE_DENSIDADE = 9.0     # ERRO: % de palavras que são jargão, por parágrafo
AVISO_DENSIDADE = 6.0      # AVISO
LIMITE_INFLADO = 2.0       # ERRO: adjetivos inflados por mil palavras
AVISO_INFLADO = 0.3
LIMITE_MULETA = 1.5        # ERRO: muletas por mil palavras
AVISO_MULETA = 0.3
LIMITE_HEDGE = 1.0         # ERRO: hedges por mil palavras
AVISO_HEDGE = 0.1

MIN_PALAVRAS_PARAGRAFO = 25   # abaixo disto o parágrafo é rótulo, não prosa
MAX_EXEMPLOS = 8              # por categoria, para a saída não virar o relatório


# --- o que conta como oração ------------------------------------------------
# Marcadores de SUBORDINAÇÃO e de virada lógica. Cada um soma uma oração à frase.
#
# O contador mede subordinação, e não coordenação, porque é a subordinação que
# ANINHA: "que A, enquanto B, o que C, porque D" obriga o leitor a segurar
# quatro coisas na cabeça antes de chegar ao ponto. Coordenação com "e" não
# aninha — "A, e B, e C" se lê em fila, e é por isso que "e" está fora da lista.
#
# "se" e "como" também ficam de fora, embora sejam conectivos: os dois são
# também pronome reflexivo ("o modelo se comporta") e preposição ("funciona como
# baseline"), e a maioria das ocorrências num relatório técnico é a segunda
# leitura. Contá-los inflaria o aninhamento de toda frase. É a mesma decisão que
# mantém "atenção" fora da lista de jargão: melhor não medir do que medir
# errado, porque alarme falso recorrente ensina quem lê a ignorar a saída.
MARCADORES_DE_ORACAO = [
    r'que', r'qual', r'quais', r'quando', r'porque', r'embora', r'enquanto',
    r'cujo', r'cuja', r'cujos', r'cujas', r'onde', r'pois', r'portanto',
    r'mas', r'porém', r'contudo', r'entretanto', r'já que', r'uma vez que',
    r'de modo que', r'à medida que', r'sempre que', r'conforme', r'apesar de',
    r'tal que', r'ainda que', r'mesmo que', r'visto que', r'posto que',
]
_RE_MARCADOR = re.compile(r'\b(' + '|'.join(MARCADORES_DE_ORACAO) + r')\b', re.IGNORECASE)

# "do que" e "mais que" são comparativos, não orações: "mais rápido do que o
# baseline" tem uma oração, não duas. Descontar é mais barato que manter uma
# lista de exceções por marcador.
_RE_COMPARATIVO = re.compile(
    r'\b(do|da|dos|das|mais|menos|antes|depois|sem|para|nem|mesmo|ainda|por)\s+que\b',
    re.IGNORECASE)

# --- o que conta como vício -------------------------------------------------
# Adjetivos que não escolhem nada. Quem escreve "resultado robusto" não pesou
# robusto contra frágil: preencheu o espaço onde caberia o número.
ADJETIVOS_INFLADOS = [
    'robusto', 'robusta', 'robustos', 'robustas', 'abrangente', 'abrangentes',
    'crucial', 'cruciais', 'fundamental', 'fundamentais', 'essencial',
    'essenciais', 'significativo', 'significativa', 'significativos',
    'significativas', 'relevante', 'relevantes', 'poderoso', 'poderosa',
    'inovador', 'inovadora', 'promissor', 'promissora', 'promissores',
    'notável', 'notáveis', 'impressionante', 'impressionantes', 'sólido',
    'sólida', 'valioso', 'valiosa', 'sofisticado', 'sofisticada', 'versátil',
    'escalável', 'expressivo', 'expressiva', 'substancial', 'considerável',
    'consideráveis',
]

# Frases que anunciam que algo será dito em vez de dizer. A segunda coluna é o
# que a frase vira quando a muleta sai — é o teste de que ela não fazia falta.
MULETAS = [
    'é importante notar', 'vale ressaltar', 'vale notar', 'vale lembrar',
    'é válido', 'em suma', 'em conclusão', 'de modo geral', 'de forma geral',
    'nesse sentido', 'cabe destacar', 'cabe ressaltar', 'em outras palavras',
    'por fim', 'além disso', 'dessa forma', 'desse modo', 'assim sendo',
    'por outro lado', 'é interessante', 'não é por acaso', 'dito de outro modo',
]

# Incerteza empilhada sobre incerteza. "Pode potencialmente sugerir" não afirma
# nada, e a frase deixa de ser conferível — que é o oposto do que um relatório
# de evidência precisa ser.
HEDGES = [
    'pode potencialmente', 'talvez possa', 'parece sugerir', 'tende a sugerir',
    'pode vir a', 'de certa forma', 'em certa medida', 'possivelmente',
    'provavelmente', 'pode ajudar a', 'pode ser que', 'em algum grau',
    'até certo ponto',
]

def alternancia(itens: list[str]) -> str:
    """Alternância regex com o mais longo primeiro.

    Sem a ordenação, "promissor" casaria dentro de "promissores" se o `\\b` não
    estivesse lá — e no dia em que alguém tirar o `\\b` para permitir prefixo, o
    erro volta em silêncio. Ordenar por tamanho decrescente tira a dependência
    da ordem em que a lista foi escrita, que é a parte que ninguém lembra de
    manter.
    """
    return '|'.join(sorted(itens, key=len, reverse=True))


_RE_INFLADO = re.compile(r'\b(' + alternancia(ADJETIVOS_INFLADOS) + r')\b', re.IGNORECASE)
_RE_MULETA = re.compile(r'\b(' + alternancia(MULETAS) + r')\b', re.IGNORECASE)
_RE_HEDGE = re.compile(r'\b(' + alternancia(HEDGES) + r')\b', re.IGNORECASE)

# Medidas sem gate (ver o cabeçalho): voz passiva e travessão.
#
# A passiva conta só a forma com auxiliar de tempo — "foi treinado", "foram
# anotados". A forma com "é/são" fica de fora porque é ambígua: "é composto por
# três camadas" é passiva, "é conhecido" é cópula com adjetivo, e separar as
# duas exigiria análise sintática. Metade de uma medida honesta vale mais que
# uma medida inteira errada.
_RE_PASSIVA = re.compile(
    r'\b(foi|foram|será|serão|seria|seriam|era|eram|sendo|sido)\s+'
    r'\w+(ado|ido|ada|ida|ados|idos|adas|idas)\b', re.IGNORECASE)
_RE_TRAVESSAO = re.compile(r'—')


# --- leitura ----------------------------------------------------------------
def ler_blocos(caminho: Path):
    """Devolve (paragrafos, titulos).

    paragrafos: [(linha_do_primeiro_verso, texto)] — só prosa.
    titulos:    [(linha, texto)] — separados, e NÃO conferidos.

    Títulos ficam de fora da checagem de glosa de propósito: um título é rótulo,
    e "Eixo 1 — pooling e geometria" é como um leitor navega. Cobrar parêntese
    ali daria alarme falso em todo relatório, e um alarme falso recorrente é o
    jeito mais rápido de treinar quem lê a ignorar a saída.
    """
    linhas = caminho.read_text(encoding='utf-8').split('\n')
    paragrafos, titulos = [], []
    atual, inicio = [], None
    dentro_de_bloco = False

    for n, linha in enumerate(linhas, 1):
        s = linha.strip()

        # Bloco de código: o conteúdo entre as cercas não é prosa e não se conta.
        # Antes disto, só as LINHAS DE CERCA eram puladas e o miolo era medido
        # como parágrafo — um relatório que mostrasse um trecho de código tinha
        # o código contado como texto, e um arquivo de referência que citasse os
        # vícios para explicá-los era reprovado por citá-los.
        if s.startswith('```'):
            dentro_de_bloco = not dentro_de_bloco
            if atual:
                paragrafos.append((inicio, ' '.join(atual)))
                atual, inicio = [], None
            continue
        if dentro_de_bloco:
            continue

        estrutural = (not s or s.startswith('#') or s.startswith('|')
                      or s.startswith('---'))
        if estrutural:
            if atual:
                paragrafos.append((inicio, ' '.join(atual)))
                atual, inicio = [], None
            if s.startswith('#'):
                titulos.append((n, s))
            continue
        if not atual:
            inicio = n
        atual.append(s)

    if atual:
        paragrafos.append((inicio, ' '.join(atual)))
    return paragrafos, titulos


_CHAVE_NUMERICA = re.compile(r'\(\s*\d{1,4}(?:\s*[,;–-]\s*\d{1,4})*\s*\)')

# Citação (Autor, Ano) — a forma que o capítulo usa desde 2026-10-28, no lugar
# da chave numérica. Casa também a citação múltipla separada por ponto e vírgula
# e a letra de desambiguação de colisão autor+ano (2020a). NÃO casa parêntese de
# glosa, que é o que se quer: glosa começa em minúscula ("(pooling, a média dos
# vetores)") ou não tem vírgula imediatamente antes do ano ("(modelo de 2020)").
_CITACAO_AUTOR_ANO = re.compile(
    r'\(\s*[A-ZÀ-Ü][^()]{0,60}?,\s*\d{4}[a-z]?'
    r'(?:\s*;\s*[A-ZÀ-Ü][^()]{0,60}?,\s*\d{4}[a-z]?)*'
    r'\s*\)'
)


def sem_chaves(s: str) -> str:
    """Tira parênteses que são só citação ou chave: "(Reimers, 2019)", "(09, 10, 12)".

    Serve para contar palavra e medir frase. Sem isto, uma frase com quatro
    citações conta quatro palavras a mais e reprova por um peso que não é prosa.

    A ordem importa: a citação sai primeiro. O regex numérico sozinho não pega
    "(Reimers, 2019)" — sobra o nome — e o nome sozinho continuaria pesando.
    """
    s = _CITACAO_AUTOR_ANO.sub('', s)
    return _CHAVE_NUMERICA.sub('', s)


def palavras(s: str):
    return [w for w in re.split(r'\s+', s) if re.search(r'\w', w)]


def frases(s: str):
    return [f.strip() for f in re.split(r'(?<=[.!?])\s+', s) if f.strip()]


def spans_parenteses(s: str):
    """Intervalos (abre, fecha) dos parênteses de `s`, do mais externo ao interno."""
    spans, pilha = [], []
    for i, ch in enumerate(s):
        if ch == '(':
            pilha.append(i)
        elif ch == ')' and pilha:
            spans.append((pilha.pop(), i))
    return spans


def glosa_valida(conteudo: str) -> bool:
    """Um parêntese conta como glosa se for curto e não for citação nem chave.

    A regra antiga era "tem dígito → não é glosa", e ela era errada: existe
    termo técnico com dígito dentro — word2vec, T5, BERT-flow — e o parêntese
    "(word2vec)" apresenta o termo como qualquer outro. O que desqualifica um
    parêntese não é o dígito, é ele ser SÓ citação ou SÓ chave; os dois regex
    de `sem_chaves` já sabem reconhecer exatamente esses dois casos.
    """
    par = '(' + conteudo + ')'
    if _CITACAO_AUTOR_ANO.fullmatch(par) or _CHAVE_NUMERICA.fullmatch(par):
        return False
    return len(palavras(conteudo)) <= 5


def recorte(texto: str, i: int, margem: int = 45) -> str:
    a, b = max(0, i - margem), min(len(texto), i + margem)
    return ('…' if a else '') + texto[a:b].strip() + ('…' if b < len(texto) else '')


def por_mil(ocorrencias: int, n_palavras: int) -> float:
    return round(ocorrencias / n_palavras * 1000, 2) if n_palavras else 0.0


# --- as checagens -----------------------------------------------------------
def oracoes_da_frase(f: str) -> int:
    """Quantas orações a frase empilha: uma, mais os conectivos que a estendem."""
    m = len(_RE_MARCADOR.findall(f)) - len(_RE_COMPARATIVO.findall(f))
    return max(1, 1 + m)


def conferir_oracoes(paragrafos):
    """Frases que empilham orações demais. Substitui a contagem de palavras."""
    erros, avisos = [], []
    for linha, texto in paragrafos:
        for f in frases(sem_chaves(texto)):
            n = oracoes_da_frase(f)
            item = {'linha': linha, 'oracoes': n, 'palavras': len(palavras(f)),
                    'frase': recorte(f, 0, 90)}
            if n >= LIMITE_ORACOES:
                erros.append(item)
            elif n >= AVISO_ORACOES:
                avisos.append(item)
    return erros, avisos


def conferir_termos(termos, paragrafos):
    """Termo cuja PRIMEIRA aparição está fora de parênteses, no corpo."""
    problemas = []
    for termo in termos:
        rx = re.compile(r'\b' + re.escape(termo), re.IGNORECASE)
        for linha, texto in paragrafos:
            m = rx.search(texto)
            if not m:
                continue
            internos = [sp for sp in spans_parenteses(texto) if sp[0] < m.start() < sp[1]]
            if internos:
                a, b = max(internos, key=lambda sp: sp[0])
                if glosa_valida(texto[a + 1:b]):
                    break            # apresentado antes de usar: nada a dizer
            problemas.append({'termo': termo, 'linha': linha,
                              'trecho': recorte(texto, m.start())})
            break
    return problemas


def conferir_densidade(termos, paragrafos):
    rx = [re.compile(r'\b' + re.escape(t), re.IGNORECASE) for t in termos]
    densos = []
    for linha, texto in paragrafos:
        limpo = sem_chaves(texto)
        ws = palavras(limpo)
        if len(ws) < MIN_PALAVRAS_PARAGRAFO:
            continue
        j = sum(1 for r in rx for _ in r.finditer(limpo))
        pct = j / len(ws) * 100
        if pct > AVISO_DENSIDADE:
            densos.append({'linha': linha, 'pct': round(pct, 1), 'jargao': j,
                           'palavras': len(ws), 'trecho': recorte(limpo, 0, 70)})
    densos.sort(key=lambda d: -d['pct'])
    return densos


def conferir_vicio(rx, paragrafos, limite, aviso):
    """Ocorrências de um vício, com o trecho em volta de cada uma.

    Devolve (erros, avisos, total). O total vai para `medidas` mesmo quando não
    passa do aviso: um relatório com 0,4 muleta por mil palavras está bem, mas
    saber que são 4 e não 40 é o que permite comparar duas rodadas.
    """
    achados = []
    for linha, texto in paragrafos:
        limpo = sem_chaves(texto)
        for m in rx.finditer(limpo):
            achados.append({'linha': linha, 'termo': m.group(0).lower(),
                            'trecho': recorte(limpo, m.start())})
    n_pal = sum(len(palavras(sem_chaves(t))) for _, t in paragrafos)
    densidade = por_mil(len(achados), n_pal)
    if densidade > limite:
        return achados, [], len(achados), densidade
    if densidade > aviso:
        return [], achados, len(achados), densidade
    return [], [], len(achados), densidade


def medidas(paragrafos, corpo: str):
    """Os números que não são gate, para o revisor olhar com contexto.

    Tamanho de frase continua aqui porque ele é CONTEXTO do aninhamento: uma
    frase de 60 palavras com duas orações é longa e clara, e quem lê o número
    sabe disso. O desvio-padrão é a única medida de RITMO que dá para fazer sem
    julgar: desvio baixo é prosa que alterna sempre no mesmo compasso.
    """
    todas = [f for _, t in paragrafos for f in frases(sem_chaves(t))]
    tam = [len(palavras(f)) for f in todas] or [0]
    n_pal = len(palavras(corpo))
    ordenado = sorted(tam)
    return {
        'palavras_por_frase_mediana': round(statistics.median(tam), 1),
        'palavras_por_frase_p90': ordenado[int(len(ordenado) * 0.9)],
        'palavras_por_frase_max': max(tam),
        'palavras_por_frase_desvio': round(statistics.pstdev(tam), 1),
        'passiva_por_mil': por_mil(len(_RE_PASSIVA.findall(corpo)), n_pal),
        'travessao_por_mil': por_mil(len(_RE_TRAVESSAO.findall(corpo)), n_pal),
    }


# --- saída ------------------------------------------------------------------
def ler_referencia(caminho: Path | None) -> dict | None:
    """Mede o arquivo de voz de referência, se ele existir.

    Devolve None em silêncio quando o arquivo não está lá: um repositório sem a
    referência continua tendo linter, só não tem comparação. Falhar aqui seria
    trocar uma comparação ausente por uma checagem que não roda.
    """
    if not caminho or not caminho.is_file():
        return None
    paragrafos, _ = ler_blocos(caminho)
    if not paragrafos:
        return None
    corpo = sem_chaves(' '.join(t for _, t in paragrafos))
    return {
        'arquivo': str(caminho),
        'palavras': len(palavras(corpo)),
        'frases': sum(len(frases(sem_chaves(t))) for _, t in paragrafos),
        **medidas(paragrafos, corpo),
    }


def imprimir(rel, mostrar: int):
    p = print
    m = rel['medidas']
    ref = rel.get('referencia')
    p(f"arquivo: {rel['arquivo']}")
    p(f"corpo: {rel['palavras']} palavras · {rel['frases']} frases · {rel['paragrafos']} parágrafos")
    p(f"limites: oração ≥ {LIMITE_ORACOES} (aviso ≥ {AVISO_ORACOES}) · "
      f"jargão > {LIMITE_DENSIDADE}% (aviso > {AVISO_DENSIDADE}%) · "
      f"adjetivo > {LIMITE_INFLADO} (aviso > {AVISO_INFLADO}) · "
      f"muleta > {LIMITE_MULETA} (aviso > {AVISO_MULETA}) · "
      f"hedge > {LIMITE_HEDGE} (aviso > {AVISO_HEDGE})   [por mil palavras]")
    p(f"termos conferidos: {len(rel['termos'])} — títulos NÃO são conferidos")
    p('')

    if ref:
        p(f"contra a voz de referência ({ref['arquivo']}, {ref['palavras']} palavras):")
        for rotulo, chave, casas in [
            ('palavras por frase (mediana)', 'palavras_por_frase_mediana', 1),
            ('palavras por frase (máxima)', 'palavras_por_frase_max', 0),
            ('desvio do ritmo', 'palavras_por_frase_desvio', 1),
            ('voz passiva por mil', 'passiva_por_mil', 2),
            ('travessão por mil', 'travessao_por_mil', 2),
        ]:
            p(f"  {rotulo:32} este {m[chave]:>6.1f}   referência {ref[chave]:>6.1f}")
        p('  (estas cinco NÃO reprovam: a medição não sustenta limite para elas)')
    else:
        p("sem arquivo de referência de voz — só as medidas abaixo, sem comparação")
    p('')
    p("medidas sem limite (contexto para o revisor):")
    p(f"  frase: mediana {m['palavras_por_frase_mediana']} · p90 {m['palavras_por_frase_p90']} · "
      f"máx {m['palavras_por_frase_max']} palavras · desvio {m['palavras_por_frase_desvio']}")
    p(f"  voz passiva {m['passiva_por_mil']}/mil · travessão {m['travessao_por_mil']}/mil")
    p('')

    fmt_oracao = lambda x: (f"L{x['linha']}  [{x['oracoes']} orações, {x['palavras']} palavras]  "
                            f"{x['frase']}")
    fmt_simples = lambda x: f"L{x['linha']}  {x['termo']}  →  {x['trecho']}"

    for titulo, erros, avisos, fmt in [
        ('ORAÇÕES EMPILHADAS', rel['oracoes_empilhadas'], rel['oracoes_aviso'], fmt_oracao),
        ('JARGÃO SEM GLOSA', rel['termos_sem_glosa'], [], fmt_simples),
        ('PARÁGRAFOS DENSOS', rel['paragrafos_densos'], rel['paragrafos_densos_aviso'],
         lambda x: f"L{x['linha']}  {x['pct']}%  ({x['jargao']} de {x['palavras']} palavras)  {x['trecho']}"),
        ('ADJETIVO INFLADO', rel['adjetivos_inflados'], rel['adjetivos_inflados_aviso'], fmt_simples),
        ('MULETA', rel['muletas'], rel['muletas_aviso'], fmt_simples),
        ('HEDGE', rel['hedges'], rel['hedges_aviso'], fmt_simples),
    ]:
        p(titulo)
        if not erros and not avisos:
            p('  ok')
        for x in erros[:mostrar]:
            p(f"  ERRO   {fmt(x)}")
        if len(erros) > mostrar:
            p(f"  ERRO   … e mais {len(erros) - mostrar}")
        for x in avisos[:mostrar]:
            p(f"  AVISO  {fmt(x)}")
        if len(avisos) > mostrar:
            p(f"  AVISO  … e mais {len(avisos) - mostrar}")
        p('')

    p(f"resultado: {rel['n_erros']} ERRO, {rel['n_avisos']} AVISO")
    if rel['n_erros']:
        p('o relatório NÃO passa na parte objetiva da regra de clareza')
    return rel['n_erros'] == 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description='Checagem objetiva de estilo de um relatório de referências.')
    ap.add_argument('arquivo', type=Path)
    ap.add_argument('--termo', action='append', default=[], metavar='T',
                    help='termo técnico que precisa ser apresentado antes de usado; repetível')
    ap.add_argument('--json', action='store_true', help='saída legível por máquina')
    ap.add_argument('--referencia', type=Path, default=None,
                    help=f'arquivo de voz de referência, para comparar as medidas sem limite '
                         f'(padrão: {REFERENCIA_PADRAO}, relativo à raiz do repositório; '
                         f'use "" para não comparar)')
    ap.add_argument('--mostrar', type=int, default=MAX_EXEMPLOS,
                    help=f'exemplos por categoria (padrão {MAX_EXEMPLOS})')
    a = ap.parse_args(argv)

    if not a.arquivo.is_file():
        print(f'não existe: {a.arquivo}', file=sys.stderr)
        return 2
    if not a.termo:
        print('sem --termo não há o que conferir na checagem 2. A lista canônica '
              'está em ESTILO.termos, no .claude/workflows/reference-research.js.',
              file=sys.stderr)
        return 2

    raiz = Path(__file__).resolve().parents[1]
    if a.referencia is None:
        caminho_ref = raiz / REFERENCIA_PADRAO
    elif str(a.referencia) in ('', '.'):
        caminho_ref = None
    else:
        caminho_ref = a.referencia if a.referencia.is_absolute() else raiz / a.referencia

    paragrafos, _ = ler_blocos(a.arquivo)
    corpo = sem_chaves(' '.join(t for _, t in paragrafos))
    densos = conferir_densidade(a.termo, paragrafos)

    orac_erros, orac_avisos = conferir_oracoes(paragrafos)
    infl_erros, infl_avisos, infl_n, infl_d = conferir_vicio(
        _RE_INFLADO, paragrafos, LIMITE_INFLADO, AVISO_INFLADO)
    mul_erros, mul_avisos, mul_n, mul_d = conferir_vicio(
        _RE_MULETA, paragrafos, LIMITE_MULETA, AVISO_MULETA)
    hed_erros, hed_avisos, hed_n, hed_d = conferir_vicio(
        _RE_HEDGE, paragrafos, LIMITE_HEDGE, AVISO_HEDGE)

    rel = {
        'arquivo': str(a.arquivo),
        'palavras': len(palavras(corpo)),
        'frases': sum(len(frases(sem_chaves(t))) for _, t in paragrafos),
        'paragrafos': len(paragrafos),
        'limites': {
            'oracoes': LIMITE_ORACOES, 'oracoes_aviso': AVISO_ORACOES,
            'densidade': LIMITE_DENSIDADE, 'densidade_aviso': AVISO_DENSIDADE,
            'adjetivo': LIMITE_INFLADO, 'adjetivo_aviso': AVISO_INFLADO,
            'muleta': LIMITE_MULETA, 'muleta_aviso': AVISO_MULETA,
            'hedge': LIMITE_HEDGE, 'hedge_aviso': AVISO_HEDGE,
        },
        'termos': a.termo,
        'oracoes_empilhadas': orac_erros,
        'oracoes_aviso': orac_avisos,
        'termos_sem_glosa': conferir_termos(a.termo, paragrafos),
        'paragrafos_densos': [d for d in densos if d['pct'] > LIMITE_DENSIDADE],
        'paragrafos_densos_aviso': [d for d in densos if d['pct'] <= LIMITE_DENSIDADE],
        'adjetivos_inflados': infl_erros,
        'adjetivos_inflados_aviso': infl_avisos,
        'muletas': mul_erros,
        'muletas_aviso': mul_avisos,
        'hedges': hed_erros,
        'hedges_aviso': hed_avisos,
        'medidas': medidas(paragrafos, corpo) | {
            'adjetivo_por_mil': infl_d, 'adjetivo_total': infl_n,
            'muleta_por_mil': mul_d, 'muleta_total': mul_n,
            'hedge_por_mil': hed_d, 'hedge_total': hed_n,
        },
        'referencia': ler_referencia(caminho_ref),
    }
    rel['n_erros'] = (len(rel['oracoes_empilhadas']) + len(rel['termos_sem_glosa'])
                      + len(rel['paragrafos_densos']) + len(rel['adjetivos_inflados'])
                      + len(rel['muletas']) + len(rel['hedges']))
    rel['n_avisos'] = (len(rel['oracoes_aviso']) + len(rel['paragrafos_densos_aviso'])
                       + len(rel['adjetivos_inflados_aviso']) + len(rel['muletas_aviso'])
                       + len(rel['hedges_aviso']))

    if a.json:
        print(json.dumps(rel, ensure_ascii=False, indent=2))
    else:
        imprimir(rel, a.mostrar)
    return 0 if rel['n_erros'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
