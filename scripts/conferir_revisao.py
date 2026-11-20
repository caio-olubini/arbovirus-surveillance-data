#!/usr/bin/env python3
"""Responde "está tudo conforme?" olhando só o repositório.

POR QUE ESTE SCRIPT EXISTE. Até 2026-11-10 o veredito sobre cada capítulo —
"o capítulo diz o que as fichas dizem?" — vivia apenas no objeto de retorno da
rodada do workflow, dentro da sessão que a executou. O capítulo ficava no disco;
o julgamento sobre ele, não. A consequência prática é que a pergunta "está tudo
conforme?" não tinha resposta no repositório: dava para reconferir as citações e
o estilo (os dois rodam de novo a qualquer momento), mas o julgamento de
interpretação evaporava junto com a conversa. É o mesmo defeito que o README das
famílias descreve para as configurações — o que só existe no histórico da
conversa não é artefato, é memória.

O QUE ESTE SCRIPT CONFERE, por família:

  1. as citações das fichas existem nos PDFs   (mecânico, refeito a cada chamada)
  2. existe um veredito de revisão em disco    (articles/<slug>/revisao.json)
  3. o veredito é `conforme`
  4. o veredito é sobre o TEXTO ATUAL          (o hash do capítulo bate)

O item 4 é o que separa um veredito de um carimbo. O veredito é um julgamento
sobre um texto específico; se alguém corrige uma frase depois, o julgamento
antigo deixa de valer — não porque ficou errado, mas porque ficou sobre outro
texto. Sem o hash, um capítulo editado depois da revisão apareceria como
conforme para sempre, que é a pior forma de estar errado: a que parece certa.
Um veredito sem hash nenhum é um estado à parte (`sem_hash`): não dá para dizer
que o texto mudou, porque ele nunca disse sobre qual texto valia. Nos dois casos
o resultado prático é o mesmo — não serve como prova.

Uso:
    uv run python -I scripts/conferir_revisao.py
    uv run python -I scripts/conferir_revisao.py articles/embeddings --json

Sai com código 1 se alguma família não estiver conforme.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
NOME_DO_VEREDITO = 'revisao.json'


def _carregar(nome: str):
    """Importa um script irmão sem depender de ele ser um pacote."""
    spec = importlib.util.spec_from_file_location(nome, RAIZ / 'scripts' / f'{nome}.py')
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def hash_do_arquivo(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def familias_em(raiz: Path) -> list[Path]:
    """Uma família é um diretório de articles/ que tem base de fichas."""
    base = raiz / 'articles'
    if not base.is_dir():
        return []
    return sorted(d for d in base.iterdir() if d.is_dir() and (d / 'fichas').is_dir())


def conferir_citacoes(pasta: Path, raiz: Path) -> dict:
    """Roda a conferência mecânica das fichas e resume o resultado."""
    modulo = _carregar('conferir_fichas')
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            modulo.main([str(pasta / 'fichas'), '--raiz', str(raiz), '--json'])
        except SystemExit as e:                     # o script sai com 2 em erro de uso
            return {'ok': False, 'detalhe': f'saiu com {e.code}'}
    try:
        rel = json.loads(buf.getvalue())
    except json.JSONDecodeError:
        return {'ok': False, 'detalhe': 'a conferência não devolveu JSON'}

    ausentes = [c for f in rel['fichas'] for c in f['erros']]
    return {
        'ok': not ausentes,
        'fichas': rel['n_fichas'],
        'citacoes': rel['n_citacoes'],
        'erros': len(ausentes),
        'avisos': rel['n_avisos'],
        'exemplos': ausentes[:3],
    }


def conferir_veredito(pasta: Path) -> dict:
    """Lê o veredito da revisão e diz se ele ainda vale para o texto atual."""
    capítulo = pasta / 'relatorio.md'
    arquivo = pasta / NOME_DO_VEREDITO

    if not arquivo.is_file():
        return {'estado': 'ausente',
                'detalhe': f'não há {NOME_DO_VEREDITO} — o capítulo não tem veredito gravado, '
                           f'então não dá para saber se ele foi aprovado'}
    if not capítulo.is_file():
        return {'estado': 'sem_capitulo', 'detalhe': 'o veredito existe mas o capítulo não'}

    try:
        veredito = json.loads(arquivo.read_text(encoding='utf-8'))
    except Exception as e:                          # noqa: BLE001
        return {'estado': 'ilegivel', 'detalhe': f'{type(e).__name__}: {e}'}

    atual = hash_do_arquivo(capítulo)
    gravado = veredito.get('relatorio_sha256')
    if not gravado:
        # Não é o mesmo caso de "venceu": aqui não dá para afirmar que o texto
        # mudou, porque o veredito nunca disse sobre qual texto ele valia. Dizer
        # "mudou depois da revisão" seria inventar um fato. O que se sabe é menos
        # — e é isso que a mensagem tem que dizer.
        return {'estado': 'sem_hash',
                'detalhe': 'o veredito não traz o hash do capítulo, então não dá para saber '
                           'sobre qual texto ele vale — na prática, vale para nenhum'}
    if gravado != atual:
        return {'estado': 'vencido',
                'detalhe': 'o capítulo mudou depois da revisão — o veredito é sobre outro texto, '
                           'e a única forma de saber se o texto novo passa é revisar de novo',
                'divergencias': veredito.get('divergencias') or []}

    return {
        'estado': 'conforme' if veredito.get('conforme') else 'nao_conforme',
        'divergencias': veredito.get('divergencias') or [],
        'estilo': veredito.get('estilo'),
        'claims_conferidas': veredito.get('claims_conferidas'),
    }


def conferir_familia(pasta: Path, raiz: Path) -> dict:
    return {
        'familia': pasta.name,
        'citacoes': conferir_citacoes(pasta, raiz),
        'veredito': conferir_veredito(pasta),
    }


def _marca(ok: bool) -> str:
    return 'ok  ' if ok else 'FALHA'


def imprimir(resultados: list[dict]) -> None:
    for r in resultados:
        c, v = r['citacoes'], r['veredito']
        ok_c = c.get('ok', False)
        ok_v = v['estado'] == 'conforme'
        print(f"{r['familia']}")
        if c.get('erros') is None:
            print(f"  {_marca(False)} citações das fichas: {c.get('detalhe', '?')}")
        else:
            print(f"  {_marca(ok_c)} citações das fichas: {c['fichas']} fichas, "
                  f"{c['citacoes']} citações conferidas, {c['erros']} ERRO, {c['avisos']} aviso")
            for e in c.get('exemplos', []):
                print(f"        · {e}")
        print(f"  {_marca(ok_v)} veredito da revisão: {v['estado']}")
        if v.get('detalhe'):
            print(f"        · {v['detalhe']}")
        for d in (v.get('divergencias') or [])[:5]:
            print(f"        · {d[:160]}")
        if v['estado'] == 'conforme' and v.get('estilo'):
            e = v['estilo']
            print(f"        estilo no momento da revisão: {e.get('oracoes_empilhadas')} oração empilhada, "
                  f"{e.get('termos_sem_glosa')} termo sem glosa, {e.get('adjetivos_inflados')} adjetivo inflado, "
                  f"{e.get('muletas')} muleta, {e.get('hedges')} hedge")
        print()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description='Diz se cada família está conforme, olhando só o repositório.')
    ap.add_argument('pastas', nargs='*', type=Path, default=None,
                    help='diretórios de família (padrão: todas em articles/)')
    ap.add_argument('--raiz', type=Path, default=RAIZ)
    ap.add_argument('--json', action='store_true', help='saída legível por máquina')
    a = ap.parse_args(argv)

    pastas = a.pastas or familias_em(a.raiz)
    if not pastas:
        print(f'nenhuma família com base de fichas em {a.raiz / "articles"}', file=sys.stderr)
        return 2

    resultados = [conferir_familia(p, a.raiz) for p in pastas]

    if a.json:
        print(json.dumps(resultados, ensure_ascii=False, indent=2))
    else:
        imprimir(resultados)

    todas_ok = all(r['citacoes'].get('ok') and r['veredito']['estado'] == 'conforme'
                   for r in resultados)
    if not a.json:
        print('tudo conforme' if todas_ok else 'NEM TUDO CONFORME — o que falta está acima')
    return 0 if todas_ok else 1


if __name__ == '__main__':
    sys.exit(main())
