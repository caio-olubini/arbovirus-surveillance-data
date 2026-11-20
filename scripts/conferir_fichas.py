#!/usr/bin/env python3
"""Conferência MECÂNICA das fichas contra os PDFs que elas dizem resumir.

A ficha é o que sobra de um artigo depois que um agente o leu: o que o estudo
estabelece, quanto mediu, o que custa adotar aqui, e — desde que este script
existe — a CITAÇÃO LITERAL e a PÁGINA que sustentam cada afirmação.

É essa âncora que torna a conferência barata. Sem ela, verificar uma ficha
significa reabrir o PDF e reler; com ela, verificar significa perguntar ao
arquivo se aquele trecho está mesmo ali. A diferença é a diferença entre um
trabalho que cresce com o número de páginas escritas e um que cresce com o
número de defeitos encontrados.

O QUE ESTE SCRIPT NÃO FAZ, e é deliberado: ele não julga se a citação SUSTENTA
a afirmação. Isso é interpretação, e interpretação não tem teste mecânico — a
citação pode existir na página 7 e não dizer o que a ficha afirma que ela diz.
O que o script entrega é a lista curta de pares (afirmação, citação) para um
humano ler, já sabendo que a citação é real. É a metade que a máquina pode
fazer sozinha, e é a metade que hoje não é feita.

TRÊS ESTADOS DE CITAÇÃO, e a distinção importa:

  exata    — o trecho aparece no PDF, palavra por palavra
  parcial  — a maior parte do trecho aparece; a extração de texto do PDF mexe
             em hifenização, acento, ordem de coluna, espaçamento e número de
             linha da margem, e o agente que leu o PDF viu a página renderizada,
             não o texto extraído. Divergência pequena é esperada e não é
             defeito.
  ausente  — o trecho não está no PDF. É invenção até prova em contrário, e é
             o defeito que este script existe para pegar.

O QUE CONTA COMO DEFEITO. `ausente` e contrato violado são ERRO. `parcial` e
página divergente são AVISO: podem ser extração ruim, e quem lê decide. A
distinção existe porque alarme falso recorrente treina quem lê a ignorar a
saída — o mesmo motivo pelo qual o script de estilo não confere título.

PDF SEM TEXTO é tratado como defeito PRÓPRIO, não como citação ausente. Um PDF
digitalizado é imagem: a extração devolve nada, e acusar todas as citações dele
de invenção seria mentira. Ele sai como `sem_texto` e o arquivo tem que ser
conferido a olho.

Uso:
    uv run python -I scripts/conferir_fichas.py articles/embeddings/fichas
    uv run python -I scripts/conferir_fichas.py articles/embeddings/fichas --json

Sai com código 1 se houver ERRO.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

# --- os limites -------------------------------------------------------------
# N-grama de 5 palavras: curto o bastante para casar apesar de hifenização e
# acento, longo o bastante para não casar por acaso. Abaixo de 5 o mesmo trecho
# aparece em qualquer parágrafo do mesmo assunto; acima, uma palavra trocada
# pela extração já derruba cinco n-gramas de uma vez.
N_GRAMA = 5

# Cobertura de n-gramas do trecho. 0,80 é "a extração mexeu em pouca coisa";
# 0,50 é "boa parte está lá, mas não confio sem olhar". Abaixo disso é ausente.
COBERTURA_QUASE = 0.80
COBERTURA_PARCIAL = 0.50

# Citação de menos de 5 palavras não ancora nada: "os resultados mostram" está
# em todo artigo já escrito. O piso é sobre a citação, não sobre a afirmação.
MIN_PALAVRAS_CITACAO = 5

# Orçamento de parsing do pypdf, em unidades internas do extrator. O padrão da
# biblioteca é 2 milhões, e ele existe como guarda: PDF malformado pode fazer o
# extrator girar sem fim. Mas artigo denso e legítimo também estoura — o Rieger
# (2024) estoura na página 31 e o arquivo inteiro saía como ilegível, o que
# transforma limitação da ferramenta em "não deu para conferir". A saída é
# escalar UMA vez, com teto: acima de 20 milhões o arquivo continua sendo
# reportado como ilegível, porque aí a guarda está fazendo o trabalho dela.
ORCAMENTO_PARSING_ESCALADO = 20_000_000

CAMPOS_OBRIGATORIOS = ('key', 'pdf', 'author', 'year', 'afirmacoes', 'ressalva_do_autor')
CAMPOS_DA_AFIRMACAO = ('afirmacao', 'citacao', 'pagina')

# O índice consolidado, se existir, não é uma ficha. Ele é gerado a partir
# delas, e conferi-lo como se fosse ficha acusaria contrato violado em tudo.
NAO_E_FICHA = {'fichas.json', 'indice.json'}


# --- normalização -----------------------------------------------------------
# A extração de texto de PDF não devolve o que está na página. Ela devolve
# glifos na ordem em que o arquivo os guarda, o que na prática significa:
# hifenização quebrada no fim da linha, espaçamento irregular, ligaduras
# ("ﬁ" no lugar de "fi"), aspas curvas, e — em layout de duas colunas — texto
# de colunas diferentes intercalado. Comparar strings cruas acusaria invenção
# em citação legítima, que é o pior defeito possível num verificador: ele
# ensina quem lê a não confiar nele.

# O `\s*` antes do hífen não é enfeite. Nem todo extrator devolve o hífen colado
# na palavra: o Mortezaagha et al. (2026) sai como "were discov -\nered", com um
# espaço entre a palavra e o hífen. Exigir o hífen encostado fazia essa citação
# legítima ser acusada de invenção — o verificador dizendo que o artigo não
# escreveu o que ele escreveu. A quebra de linha é obrigatória na regra, e é ela
# que mantém a substituição segura: hífen seguido de quebra de linha é hifenização,
# não é travessão nem sinal de menos.
_RE_HIFEN_QUEBRA = re.compile(r'(\w)\s*-\s*\n\s*(\w)')

# A quinta classe de falso positivo, encontrada no Valentin et al. (2020): a
# revista numera as linhas na margem e o extrator devolve o número DENTRO da
# frase, entre duas palavras. A página 7 sai assim:
#
#     "multilingual RSS feeds led 109 \nto a 131% increase in relevant news articles for AS F"
#
# O "109" é o número da linha, não parte do texto; o "AS F" é o mesmo estrago
# numa palavra. A citação da ficha — "led to a 131% increase in relevant news
# articles for ASF" — é literalmente o que o artigo diz, e a conferência a
# acusava de invenção, com 38% de cobertura. O verificador dizendo que o artigo
# não escreveu o que ele escreveu.
#
# A quebra de linha é obrigatória na regra, e é ela que a mantém estreita: o que
# se remove é um número SOZINHO entre uma palavra e a quebra de linha. Um número
# no meio da frase, sem quebra depois, não casa.
_RE_NUM_LINHA = re.compile(r'(?<=\w)\s+\d{1,4}\s*\n\s*(?=\w)', re.UNICODE)

# E, mesmo no fim de linha, um número pode ser CONTEÚDO — "o corpus tem 4369
# \nartigos" é uma frase legítima, e apagar o 4369 dela aceitaria como literal
# uma citação que omitiu o número. Por isso a remoção não é incondicional: ela
# só acontece na página que comprovadamente NUMERA as linhas. A prova é o
# conjunto dos números de fim de linha da página, não cada um sozinho.
_RE_FIM_DE_LINHA = re.compile(r'(?<=\w)\s+(\d{1,4})\s*\n', re.UNICODE)

# Quantos números no fim de linha a página precisa ter. Uma página numerada tem
# dezenas deles; o que a extração deixa passar varia, e 5 é o piso que separa
# "numeração" de "uns números por acaso".
MIN_NUMEROS_DE_LINHA = 5
# E eles têm que formar uma SEQUÊNCIA: quase todos distintos (cada linha é
# numerada uma vez) e cobrindo uma faixa pouco maior que a própria quantidade.
# Medido no Valentin (2020): as páginas numeradas dão faixa/quantidade entre 1,1
# e 1,8; a página que não é numerada dá 670 — um ano e um número de tabela, a
# dois mil de distância um do outro. A separação é larga, e é de propósito.
MAX_ESPALHAMENTO = 3.0
MIN_DISTINTOS = 0.8

_RE_ESPACO = re.compile(r'\s+')


def _pre_normalizar(texto: str) -> str:
    """O que as formas canônicas têm em comum: NFKC e hífen de quebra junto.

    Preserva as quebras de linha, que `_RE_NUM_LINHA` e `_RE_FIM_DE_LINHA`
    precisam ver — quem colapsa o espaço é quem chama.
    """
    t = unicodedata.normalize('NFKC', texto)
    return _RE_HIFEN_QUEBRA.sub(r'\1\2', t)


def normalizar(texto: str) -> str:
    """Forma canônica para comparação: NFKC, sem hífen de quebra, espaço único."""
    return _RE_ESPACO.sub(' ', _pre_normalizar(texto)).strip().casefold()


def numeracao_de_linha(texto: str) -> bool:
    """O texto traz numeração de linha na margem?

    Não basta haver um número no fim de uma linha — um artigo legítimo tem
    números no fim de linha o tempo todo (anos, contagens, resultados). O que
    identifica numeração de linha é o CONJUNTO: muitos números, um por linha,
    quase todos distintos, cobrindo uma faixa estreita e em ordem.
    """
    achados = [int(m.group(1)) for m in _RE_FIM_DE_LINHA.finditer(texto)]
    if len(achados) < MIN_NUMEROS_DE_LINHA:
        return False
    if len(set(achados)) / len(achados) < MIN_DISTINTOS:
        return False
    return (max(achados) - min(achados)) <= MAX_ESPALHAMENTO * len(achados)


def sem_numero_de_linha(texto: str) -> str:
    """Como `normalizar`, mas sem os números de linha que o extrator costura no texto.

    Não substitui a forma canônica: é uma segunda leitura da mesma página, para
    quando a primeira não acha o trecho por causa de um número de linha no meio
    dele. Ver `_RE_NUM_LINHA` para o caso real que a motivou. Numa página sem
    numeração isto devolve exatamente o que `normalizar` devolveria.
    """
    t = _pre_normalizar(texto)
    if numeracao_de_linha(t):
        t = _RE_NUM_LINHA.sub(' ', t)
    return _RE_ESPACO.sub(' ', t).strip().casefold()


def colado(texto: str) -> str:
    """O texto sem nenhum espaço entre as palavras.

    Existe porque há PDF cujo extrator não devolve os espaços: a página 16 do Hu
    et al. (2023) sai como "Weusedmoredatasets(26datasets, containing 39,736
    places worldwide)". Ali a tokenização devolve um punhado de palavras
    gigantes, nenhum n-grama casa, e uma citação literal é acusada de invenção.
    Sem espaço, a citação vira um trecho contíguo que se procura direto na
    página — é a mesma evidência lida no único alfabeto que a extração
    preservou.
    """
    return _RE_ESPACO.sub('', texto)


def sem_acento(texto: str) -> str:
    """Segunda tentativa, para PDF cujo acento a extração perdeu."""
    d = unicodedata.normalize('NFKD', texto)
    return ''.join(c for c in d if not unicodedata.combining(c))


_PALAVRA = re.compile(r'[\wÀ-ÿ]+', re.UNICODE)


def tokens(texto: str) -> list[str]:
    return _PALAVRA.findall(texto)


def ngramas(toks: list[str], n: int = N_GRAMA) -> set[tuple[str, ...]]:
    if len(toks) < n:
        return set()
    return {tuple(toks[i:i + n]) for i in range(len(toks) - n + 1)}


def cobertura(citacao_toks: list[str], pagina_toks: list[str]) -> float:
    """Fração dos n-gramas da citação que aparecem na página."""
    if len(citacao_toks) < N_GRAMA:
        # Citação curta demais para n-grama: cai na comparação por palavra, que
        # é mais fraca mas é a única disponível neste tamanho.
        if not citacao_toks:
            return 0.0
        alvo = set(citacao_toks)
        return len(alvo & set(pagina_toks)) / len(alvo)
    g_cit = ngramas(citacao_toks)
    g_pag = ngramas(pagina_toks)
    if not g_cit:
        return 0.0
    return len(g_cit & g_pag) / len(g_cit)


# --- leitura do PDF ---------------------------------------------------------
class Pdf:
    """Texto de um PDF, normalizado, página a página.

    Guarda várias visões do mesmo texto porque cada defeito de extração derruba
    um tipo de comparação, e tentar todas custa quase nada depois que o texto já
    foi extraído uma vez: com e sem acento (a extração às vezes perde acento de
    forma inconsistente entre páginas), sem espaço nenhum (extrator que engole
    os espaços) e sem os números de linha que a revista imprime na margem (ver
    `_RE_NUM_LINHA`). Nenhuma visão substitui a outra — são tentativas somadas,
    e a primeira que achar a citação é a que vale.
    """

    def __init__(self, caminho: Path):
        self.caminho = caminho
        self.erro: str | None = None
        self.paginas: list[list[str]] = []      # tokens por página, com acento
        self.paginas_sa: list[list[str]] = []   # idem, sem acento
        self.colada: list[str] = []             # idem, sem espaço nenhum
        self.colada_sa: list[str] = []
        self.paginas_sn: list[list[str]] = []   # idem, sem número de linha
        self.colada_sn: list[str] = []

        try:
            import pypdf
            from pypdf.errors import LimitReachedError
        except ImportError as e:                    # noqa: BLE001
            self.erro = f'pypdf não instalado: {e}'
            return

        try:
            self._extrair(pypdf.PdfReader(str(caminho)))
        except LimitReachedError:
            # O orçamento padrão do pypdf acabou antes do fim do arquivo. Uma
            # segunda tentativa com teto mais alto resolve artigo denso sem
            # abrir mão da guarda: o teto continua existindo, só que mais longe.
            anterior = pypdf.get_configuration()
            try:
                pypdf.overwrite_configuration(
                    stream_parsing_work_maximum_count=ORCAMENTO_PARSING_ESCALADO)
                self._extrair(pypdf.PdfReader(str(caminho)))
            except Exception as e:                  # noqa: BLE001
                self.erro = f'{type(e).__name__}: {e}'
            finally:
                pypdf.overwrite_configuration(anterior)
        except Exception as e:                      # noqa: BLE001 — reporta, não derruba
            self.erro = f'{type(e).__name__}: {e}'

    def _extrair(self, leitor) -> None:
        """Preenche as visões do texto. Reinicia antes, para que uma tentativa
        que falha no meio não deixe meia página para trás."""
        (self.paginas, self.paginas_sa, self.colada, self.colada_sa,
         self.paginas_sn, self.colada_sn) = [], [], [], [], [], []
        self.erro = None
        if leitor.is_encrypted:
            try:
                leitor.decrypt('')
            except Exception:                       # noqa: BLE001
                self.erro = 'PDF cifrado: a extração de texto não roda'
                return
        for pagina in leitor.pages:
            bruto = pagina.extract_text() or ''
            limpo = normalizar(bruto)
            self.paginas.append(tokens(limpo))
            self.paginas_sa.append(tokens(sem_acento(limpo)))
            self.colada.append(colado(limpo))
            self.colada_sa.append(colado(sem_acento(limpo)))
            sn = sem_numero_de_linha(bruto)
            self.paginas_sn.append(tokens(sn))
            self.colada_sn.append(colado(sn))

    @property
    def n_paginas(self) -> int:
        return len(self.paginas)

    @property
    def tem_texto(self) -> bool:
        return sum(len(p) for p in self.paginas) > 0

    def localizar(self, citacao: str) -> dict:
        """Onde a citação está, e com que cobertura.

        Devolve o estado, a página de melhor cobertura e a cobertura dela. Não
        julga se a página declarada bate — quem faz isso é o chamador, porque a
        regra de tolerância muda conforme o estado.
        """
        cit = tokens(normalizar(citacao))
        if not cit:
            return {'estado': 'vazia', 'pagina': None, 'cobertura': 0.0}

        melhor_pagina, melhor_cob = None, 0.0
        for i, toks in enumerate(self.paginas, 1):
            c = cobertura(cit, toks)
            if c > melhor_cob:
                melhor_pagina, melhor_cob = i, c

        # Segunda passada sem acento, só se a primeira não achou nada: um PDF
        # que perdeu acento derruba a cobertura de toda citação acentuada.
        if melhor_cob < COBERTURA_PARCIAL:
            for i, toks in enumerate(self.paginas_sa, 1):
                c = cobertura(tokens(sem_acento(normalizar(citacao))), toks)
                if c > melhor_cob:
                    melhor_pagina, melhor_cob = i, c

        # Terceira passada, sem os números de linha que a revista imprime na
        # margem e que o extrator costura dentro da frase — ver `_RE_NUM_LINHA`.
        # Roda depois das duas primeiras porque só faz sentido quando elas não
        # acharam: a forma canônica é a leitura preferida, esta é o remédio.
        if melhor_cob < COBERTURA_PARCIAL:
            for i, toks in enumerate(self.paginas_sn, 1):
                c = cobertura(cit, toks)
                if c > melhor_cob:
                    melhor_pagina, melhor_cob = i, c

        # Quarta passada, para PDF cujo extrator perdeu os espaços. Aqui a
        # citação é procurada como trecho contíguo do texto sem espaço: se
        # aparece, ela está lá palavra por palavra, e o estado é `exata` com
        # cobertura cheia. O gatilho é `COBERTURA_QUASE`, e não `PARCIAL`, de
        # propósito: um trecho contíguo é prova mais forte do que 80% de
        # n-gramas, então encontrá-lo deve poder promover um `parcial` a
        # `exata`. Só acha quem está lá — não inventa.
        if melhor_cob < COBERTURA_QUASE:
            for alvo, paginas in ((colado(normalizar(citacao)), self.colada),
                                  (colado(sem_acento(normalizar(citacao))), self.colada_sa),
                                  (colado(sem_numero_de_linha(citacao)), self.colada_sn)):
                if not alvo:
                    continue
                for i, pag in enumerate(paginas, 1):
                    if alvo in pag:
                        return {'estado': 'exata', 'pagina': i, 'cobertura': 1.0}

        if melhor_cob >= COBERTURA_QUASE:
            estado = 'exata'
        elif melhor_cob >= COBERTURA_PARCIAL:
            estado = 'parcial'
        else:
            estado = 'ausente'
        return {'estado': estado, 'pagina': melhor_pagina, 'cobertura': round(melhor_cob, 3)}


# --- conferência de uma ficha -----------------------------------------------
def conferir_ficha(caminho: Path, cache_pdf: dict[Path, Pdf], raiz: Path) -> dict:
    """Devolve {'arquivo', 'key', 'erros', 'avisos', 'citacoes'} para uma ficha."""
    erros, avisos, citacoes = [], [], []

    try:
        ficha = json.loads(caminho.read_text(encoding='utf-8'))
    except Exception as e:                          # noqa: BLE001
        return {'arquivo': str(caminho), 'key': caminho.stem,
                'erros': [f'JSON ilegível: {type(e).__name__}: {e}'],
                'avisos': [], 'citacoes': []}

    if not isinstance(ficha, dict):
        return {'arquivo': str(caminho), 'key': caminho.stem,
                'erros': ['o arquivo não é um objeto JSON'], 'avisos': [], 'citacoes': []}

    key = ficha.get('key') or caminho.stem

    # --- contrato ---
    for campo in CAMPOS_OBRIGATORIOS:
        if campo not in ficha or ficha[campo] in (None, '', [], {}):
            erros.append(f'campo obrigatório ausente ou vazio: {campo}')

    afirmacoes = ficha.get('afirmacoes')
    if not isinstance(afirmacoes, list) or not afirmacoes:
        erros.append('`afirmacoes` tem que ser uma lista com pelo menos um item')
        afirmacoes = []

    # --- o PDF ---
    pdf_rel = ficha.get('pdf')
    pdf = None
    if isinstance(pdf_rel, str) and pdf_rel:
        caminho_pdf = (raiz / pdf_rel) if not Path(pdf_rel).is_absolute() else Path(pdf_rel)
        if not caminho_pdf.is_file():
            erros.append(f'o PDF declarado não existe: {pdf_rel}')
        else:
            if caminho_pdf not in cache_pdf:
                cache_pdf[caminho_pdf] = Pdf(caminho_pdf)
            pdf = cache_pdf[caminho_pdf]
            if pdf.erro:
                erros.append(f'não deu para ler o PDF ({pdf_rel}): {pdf.erro}')
                pdf = None
            elif not pdf.tem_texto:
                # Defeito PRÓPRIO: acusar as citações dele de ausentes seria
                # mentira, porque o problema é a extração, não a ficha.
                erros.append(
                    f'PDF sem texto extraível ({pdf_rel}): provavelmente digitalizado '
                    f'como imagem. As citações NÃO foram conferidas — confira a olho.')
                pdf = None

    # --- cada afirmação ---
    for i, af in enumerate(afirmacoes, 1):
        if not isinstance(af, dict):
            erros.append(f'afirmação {i}: não é um objeto')
            continue
        for campo in CAMPOS_DA_AFIRMACAO:
            if campo not in af or af[campo] in (None, ''):
                erros.append(f'afirmação {i}: campo ausente ou vazio: {campo}')

        citacao = af.get('citacao') or ''
        pagina = af.get('pagina')
        n_palavras = len(tokens(normalizar(citacao)))
        if citacao and n_palavras < MIN_PALAVRAS_CITACAO:
            avisos.append(
                f'afirmação {i}: citação de {n_palavras} palavra(s) não ancora nada '
                f'(mínimo {MIN_PALAVRAS_CITACAO}) — "{citacao[:60]}"')

        if not pdf or not citacao:
            continue

        if not isinstance(pagina, int) or pagina < 1:
            erros.append(f'afirmação {i}: `pagina` tem que ser inteiro >= 1 (veio {pagina!r})')
            pagina = None
        elif pagina > pdf.n_paginas:
            erros.append(
                f'afirmação {i}: página {pagina} não existe — o PDF tem {pdf.n_paginas}')
            pagina = None

        achado = pdf.localizar(citacao)
        citacoes.append({'afirmacao': i, 'declarada': pagina,
                         'localizada': achado['pagina'], 'estado': achado['estado'],
                         'cobertura': achado['cobertura'], 'citacao': citacao[:90]})

        if achado['estado'] == 'ausente':
            erros.append(
                f'afirmação {i}: citação NÃO encontrada no PDF '
                f'(melhor cobertura {achado["cobertura"]:.0%}, p.{achado["pagina"]}) — '
                f'"{citacao[:80]}"')
        elif achado['estado'] == 'parcial':
            avisos.append(
                f'afirmação {i}: citação só parcialmente encontrada '
                f'({achado["cobertura"]:.0%} em p.{achado["pagina"]}) — "{citacao[:80]}"')

        # Página divergente: só vale como sinal quando a citação foi achada, e
        # só incomoda quando a distância é maior que uma página — página quebrada
        # em duas faz o mesmo trecho começar na anterior.
        if (pagina and achado['pagina'] and achado['estado'] != 'ausente'
                and abs(pagina - achado['pagina']) > 1):
            avisos.append(
                f'afirmação {i}: declarada na p.{pagina}, encontrada na p.{achado["pagina"]}')

    return {'arquivo': str(caminho), 'key': key, 'erros': erros, 'avisos': avisos,
            'citacoes': citacoes}


# --- saída ------------------------------------------------------------------
def imprimir(rel: dict, mostrar: int) -> None:
    p = print
    p(f"fichas conferidas: {rel['n_fichas']}  ·  citações conferidas: {rel['n_citacoes']}")
    p(f"PDFs lidos: {rel['n_pdfs']}  ·  sem texto extraível: {rel['n_sem_texto']}")
    p('')
    for titulo, chave in (('ERROS', 'erros'), ('AVISOS', 'avisos')):
        itens = [(f['key'], m) for f in rel['fichas'] for m in f[chave]]
        p(titulo)
        if not itens:
            p('  ok')
        for key, msg in itens[:mostrar]:
            p(f"  {key}  {msg}")
        if len(itens) > mostrar:
            p(f"  … e mais {len(itens) - mostrar}")
        p('')
    p(f"resultado: {rel['n_erros']} ERRO, {rel['n_avisos']} AVISO")
    if rel['n_erros']:
        p('a base de fichas NÃO passa na conferência mecânica')
    else:
        p('a metade mecânica passou — o que sobra é julgar se cada citação sustenta a afirmação')


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description='Confere mecanicamente as fichas contra os PDFs que elas resumem.')
    ap.add_argument('fichas', type=Path,
                    help='diretório com uma ficha por arquivo .json')
    ap.add_argument('--raiz', type=Path, default=None,
                    help='raiz do repositório, para resolver o campo `pdf` (padrão: deduzida)')
    ap.add_argument('--json', action='store_true', help='saída legível por máquina')
    ap.add_argument('--mostrar', type=int, default=12, help='itens por categoria (padrão 12)')
    a = ap.parse_args(argv)

    if not a.fichas.is_dir():
        print(f'não é um diretório: {a.fichas}', file=sys.stderr)
        return 2

    raiz = a.raiz or Path(__file__).resolve().parents[1]

    arquivos = sorted(p for p in a.fichas.glob('*.json') if p.name not in NAO_E_FICHA)
    if not arquivos:
        print(f'nenhuma ficha em {a.fichas} — esperava um .json por artigo. '
              f'A base de fichas existe? Ela é escrita pela fase Ler do workflow.',
              file=sys.stderr)
        return 2

    cache: dict[Path, Pdf] = {}
    rel_fichas = [conferir_ficha(p, cache, raiz) for p in arquivos]

    n_sem_texto = sum(1 for pdf in cache.values() if not pdf.erro and not pdf.tem_texto)
    rel = {
        'fichas': rel_fichas,
        'n_fichas': len(rel_fichas),
        'n_citacoes': sum(len(f['citacoes']) for f in rel_fichas),
        'n_pdfs': len(cache),
        'n_sem_texto': n_sem_texto,
        'n_erros': sum(len(f['erros']) for f in rel_fichas),
        'n_avisos': sum(len(f['avisos']) for f in rel_fichas),
    }

    if a.json:
        print(json.dumps(rel, ensure_ascii=False, indent=2))
    else:
        imprimir(rel, a.mostrar)
    return 0 if rel['n_erros'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
