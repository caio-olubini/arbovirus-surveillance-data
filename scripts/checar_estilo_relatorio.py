#!/usr/bin/env python3
"""Checagem OBJETIVA de estilo de um relatório do workflow reference-research.

O relatório tem uma regra de escrita — português claro, termo técnico entre
parênteses ao lado, número sempre dentro da frase — e uma parte dessa regra é
contável. Esta é a parte contável, e ela é script e não agente por um motivo
prático: agente não conta palavra igual duas vezes, e um limite que se move a
cada rodada não é um limite. O que NÃO é contável (a glosa ficou clara para
quem lê? a frase ficou opaca apesar de curta?) continua com o agente revisor.

Três medidas:

  1. FRASES LONGAS     — palavras por frase, no corpo
  2. TERMO SEM GLOSA   — termo técnico que aparece FORA de parênteses antes de
                         qualquer ocorrência entre parênteses
  3. DENSIDADE         — jargão por 100 palavras, por parágrafo

O que a checagem 2 quer dizer, na prática. A regra do relatório é escrever o
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
Duas listas seriam duas verdades. Os LIMITES, ao contrário, moram aqui: eles
são sobre prosa em português, não sobre uma família de técnicas, e valem
igual para qualquer tema. O script imprime os limites que usou, então
divergência entre o que o workflow acha e o que foi medido aparece na saída.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# --- os limites -------------------------------------------------------------
# Calibrados contra o primeiro relatório que este script mediu
# (articles/embeddings/relatorio.md, 2026-10-21), escrito ANTES da regra de
# clareza existir: mediana de 25 palavras por frase, p90 de 51, máxima de 110;
# densidade de jargão mediana de 2,2% por parágrafo, máxima de 7,8%.
#
# Os números abaixo são ALVO, não descrição. Aquele relatório reprova neles, e é
# isso mesmo que se quer: ele é a linha de base a ser batida, não o padrão.
# Quando o relatório passar limpo com folga, estes limites descem.
LIMITE_FRASE = 45          # ERRO acima disto
AVISO_FRASE = 35           # AVISO, se passar de 10% das frases
LIMITE_DENSIDADE = 9.0     # ERRO: % de palavras que são jargão, por parágrafo
AVISO_DENSIDADE = 6.0      # AVISO

MIN_PALAVRAS_PARAGRAFO = 25   # abaixo disto o parágrafo é rótulo, não prosa
MAX_EXEMPLOS = 8              # por categoria, para a saída não virar o relatório


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

    for n, linha in enumerate(linhas, 1):
        s = linha.strip()
        estrutural = (not s or s.startswith('#') or s.startswith('|')
                      or s.startswith('```') or s.startswith('---'))
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


# --- as três checagens ------------------------------------------------------
def conferir_frases(paragrafos):
    longas, avisos = [], []
    for linha, texto in paragrafos:
        for f in frases(sem_chaves(texto)):
            n = len(palavras(f))
            if n > LIMITE_FRASE:
                longas.append({'linha': linha, 'palavras': n, 'frase': recorte(f, 0, 90)})
            elif n > AVISO_FRASE:
                avisos.append({'linha': linha, 'palavras': n, 'frase': recorte(f, 0, 90)})
    return longas, avisos


def conferir_glosa(termos, paragrafos):
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


# --- saída ------------------------------------------------------------------
def imprimir(rel, mostrar: int):
    p = print
    p(f"arquivo: {rel['arquivo']}")
    p(f"corpo: {rel['palavras']} palavras · {rel['frases']} frases · {rel['paragrafos']} parágrafos")
    p(f"limites: frase > {LIMITE_FRASE} palavras (aviso > {AVISO_FRASE}) · "
      f"densidade > {LIMITE_DENSIDADE}% (aviso > {AVISO_DENSIDADE}%)")
    p(f"termos conferidos: {len(rel['termos'])} — títulos NÃO são conferidos")
    p('')

    for titulo, erros, avisos, fmt in [
        ('FRASES LONGAS', rel['frases_longas'], rel['frases_aviso'],
         lambda x: f"L{x['linha']}  [{x['palavras']} palavras]  {x['frase']}"),
        ('JARGÃO SEM GLOSA', rel['termos_sem_glosa'], [],
         lambda x: f"L{x['linha']}  {x['termo']}  →  {x['trecho']}"),
        ('PARÁGRAFOS DENSOS', rel['paragrafos_densos'], rel['paragrafos_densos_aviso'],
         lambda x: f"L{x['linha']}  {x['pct']}%  ({x['jargao']} de {x['palavras']} palavras)  {x['trecho']}"),
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

    paragrafos, _ = ler_blocos(a.arquivo)
    corpo = sem_chaves(' '.join(t for _, t in paragrafos))
    longas, avisos = conferir_frases(paragrafos)
    densos = conferir_densidade(a.termo, paragrafos)

    rel = {
        'arquivo': str(a.arquivo),
        'palavras': len(palavras(corpo)),
        'frases': sum(len(frases(sem_chaves(t))) for _, t in paragrafos),
        'paragrafos': len(paragrafos),
        'limites': {'frase': LIMITE_FRASE, 'frase_aviso': AVISO_FRASE,
                    'densidade': LIMITE_DENSIDADE, 'densidade_aviso': AVISO_DENSIDADE},
        'termos': a.termo,
        'frases_longas': longas,
        'frases_aviso': avisos,
        'termos_sem_glosa': conferir_glosa(a.termo, paragrafos),
        'paragrafos_densos': [d for d in densos if d['pct'] > LIMITE_DENSIDADE],
        'paragrafos_densos_aviso': [d for d in densos if d['pct'] <= LIMITE_DENSIDADE],
    }
    rel['n_erros'] = len(rel['frases_longas']) + len(rel['termos_sem_glosa']) + len(rel['paragrafos_densos'])
    rel['n_avisos'] = len(rel['frases_aviso']) + len(rel['paragrafos_densos_aviso'])

    if a.json:
        print(json.dumps(rel, ensure_ascii=False, indent=2))
    else:
        imprimir(rel, a.mostrar)
    return 0 if rel['n_erros'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
