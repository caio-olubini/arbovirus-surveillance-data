"""The mechanical ficha check: every guard fires, and the clean case stays quiet.

The two properties worth defending here are asymmetric, and both are tested:

* a defect the script can see must be reported — an invented quote is the whole
  reason the script exists;
* a *clean* ficha must come back with nothing at all — a verifier that cries
  wolf on legitimate quotes teaches whoever reads it to ignore the output, and
  then it is worse than no verifier.

The PDFs are built in-process rather than committed, so the text a quote is
checked against is visible in the test that asserts on it.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

_spec = importlib.util.spec_from_file_location(
    "conferir_fichas", REPO / "scripts" / "conferir_fichas.py"
)
conferir_fichas = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(conferir_fichas)


# --- um PDF mínimo, válido, sem dependência nova -----------------------------
def _escapar(s: str) -> str:
    return s.replace('\\', r'\\').replace('(', r'\(').replace(')', r'\)')


def _montar_pdf(paginas: list[list[str]]) -> bytes:
    """Um PDF de uma coluna, Helvetica, com as linhas dadas em cada página.

    Escrito à mão porque a alternativa era trazer uma biblioteca de escrita de
    PDF para dentro do suite de testes só para produzir um fixture de 2 KB. O
    texto vai em WinAnsi para que acento sobreviva — o script tem uma segunda
    passada sem acento, e ela precisa de um PDF acentuado para ser exercitada.
    """
    n = len(paginas)
    font, primeira_pagina, primeiro_conteudo = 3, 4, 4 + n

    objetos: dict[int, bytes] = {
        1: b'<< /Type /Catalog /Pages 2 0 R >>',
        2: ('<< /Type /Pages /Kids [' +
            ' '.join(f'{primeira_pagina + i} 0 R' for i in range(n)) +
            f'] /Count {n} >>').encode(),
        3: b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica '
           b'/Encoding /WinAnsiEncoding >>',
    }

    for i, linhas in enumerate(paginas):
        corpo = ['BT', '/F1 11 Tf', '14 TL', '72 720 Td']
        for j, linha in enumerate(linhas):
            if j:
                corpo.append('T*')
            corpo.append(f'({_escapar(linha)}) Tj')
        corpo.append('ET')
        fluxo = '\n'.join(corpo).encode('cp1252', errors='replace')

        objetos[primeira_pagina + i] = (
            f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] '
            f'/Contents {primeiro_conteudo + i} 0 R '
            f'/Resources << /Font << /F1 {font} 0 R >> >> >>'
        ).encode()
        objetos[primeiro_conteudo + i] = (
            f'<< /Length {len(fluxo)} >>\nstream\n'.encode() + fluxo + b'\nendstream'
        )

    saida = bytearray(b'%PDF-1.4\n')
    offsets: dict[int, int] = {}
    for num in sorted(objetos):
        offsets[num] = len(saida)
        saida += f'{num} 0 obj\n'.encode() + objetos[num] + b'\nendobj\n'

    maior = max(objetos)
    inicio_xref = len(saida)
    saida += f'xref\n0 {maior + 1}\n'.encode()
    saida += b'0000000000 65535 f \n'
    for num in range(1, maior + 1):
        saida += f'{offsets[num]:010d} 00000 n \n'.encode()
    saida += (f'trailer\n<< /Size {maior + 1} /Root 1 0 R >>\n'
              f'startxref\n{inicio_xref}\n%%EOF\n').encode()
    return bytes(saida)


# --- a base de fichas de um teste --------------------------------------------
PAGINAS = [
    ['Estudo sobre representacao de texto em portugues.',
     'Os autores relatam ganho de doze por cento na tarefa principal,',
     'medido sobre um corpus de noticias de dominio publico.'],
    ['Na discussao, os autores reconhecem que o metodo exige pares',
     'rotulados, o que limita a aplicacao em corpus sem anotacao.'],
    ['Como conclusao, o trabalho sugere investigar o custo de anotacao',
     'em dominios especializados antes de adotar o metodo.'],
]

CITACAO_P1 = 'Os autores relatam ganho de doze por cento na tarefa principal'
CITACAO_P2 = 'o metodo exige pares rotulados, o que limita a aplicacao'
CITACAO_P3 = 'o trabalho sugere investigar o custo de anotacao'


def _ficha(key: str, pdf: str = 'artigo.pdf', **overrides) -> dict:
    base = {
        'key': key,
        'pdf': pdf,
        'author': 'Silva',
        'year': 2024,
        'grupo': 'representacao',
        'technique': 'x',
        'ressalva_do_autor': 'exige pares rotulados',
        'afirmacoes': [{'afirmacao': 'a', 'citacao': CITACAO_P1, 'pagina': 1}],
    }
    base.update(overrides)
    return base


@pytest.fixture
def base(tmp_path: Path) -> Path:
    """Um diretório com o PDF de fixture e a pasta de fichas."""
    (tmp_path / 'artigo.pdf').write_bytes(_montar_pdf(PAGINAS))
    (tmp_path / 'fichas').mkdir()
    return tmp_path


def _escrever(base: Path, ficha: dict, nome: str | None = None) -> None:
    alvo = base / 'fichas' / f'{nome or ficha.get("key", "x")}.json'
    alvo.write_text(json.dumps(ficha, ensure_ascii=False), encoding='utf-8')


def _rodar(base: Path, *extra: str) -> tuple[int, dict]:
    """Roda o script em modo --json e devolve (código de saída, relatório)."""
    import io
    import contextlib

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        codigo = conferir_fichas.main(
            [str(base / 'fichas'), '--raiz', str(base), '--json', *extra])
    return codigo, json.loads(buf.getvalue())


# --- o caso limpo ------------------------------------------------------------
def test_ficha_limpa_nao_produz_nada(base: Path) -> None:
    """A citação existe, a página bate: nem ERRO nem AVISO.

    É o teste que protege o script de virar ruído. Se este falhar, quem lê a
    saída aprende a ignorá-la.
    """
    _escrever(base, _ficha('01'))
    _escrever(base, _ficha('02', afirmacoes=[
        {'afirmacao': 'b', 'citacao': CITACAO_P2, 'pagina': 2}]))

    codigo, rel = _rodar(base)

    assert codigo == 0
    assert rel['n_erros'] == 0
    assert rel['n_avisos'] == 0
    assert {c['estado'] for f in rel['fichas'] for c in f['citacoes']} == {'exata'}


def test_citacao_no_meio_da_frase_e_encontrada(base: Path) -> None:
    """Citação que não começa nem termina a linha continua sendo encontrada."""
    _escrever(base, _ficha('01', afirmacoes=[
        {'afirmacao': 'a', 'citacao': 'ganho de doze por cento na tarefa', 'pagina': 1}]))
    codigo, rel = _rodar(base)
    assert codigo == 0 and rel['n_erros'] == 0


# --- os defeitos que o script existe para pegar ------------------------------
def test_citacao_inventada_e_erro(base: Path) -> None:
    _escrever(base, _ficha('01', afirmacoes=[{
        'afirmacao': 'a',
        'citacao': 'os autores relatam ganho de quarenta e dois por cento em todas as tarefas',
        'pagina': 1}]))

    codigo, rel = _rodar(base)

    assert codigo == 1
    assert rel['n_erros'] == 1
    assert 'NÃO encontrada' in rel['fichas'][0]['erros'][0]
    assert rel['fichas'][0]['citacoes'][0]['estado'] == 'ausente'


def test_pagina_fora_do_intervalo_e_erro(base: Path) -> None:
    _escrever(base, _ficha('01', afirmacoes=[
        {'afirmacao': 'a', 'citacao': CITACAO_P1, 'pagina': 9}]))
    codigo, rel = _rodar(base)
    assert codigo == 1
    assert 'não existe' in rel['fichas'][0]['erros'][0]


def test_campo_obrigatorio_ausente_e_erro(base: Path) -> None:
    ficha = _ficha('01')
    del ficha['ressalva_do_autor']
    _escrever(base, ficha)

    codigo, rel = _rodar(base)

    assert codigo == 1
    assert any('ressalva_do_autor' in e for e in rel['fichas'][0]['erros'])


def test_ficha_sem_afirmacao_e_erro(base: Path) -> None:
    """Ficha sem âncora não é ficha: é um resumo, e não dá para conferir."""
    _escrever(base, _ficha('01', afirmacoes=[]))
    codigo, rel = _rodar(base)
    assert codigo == 1
    assert any('afirmacoes' in e for e in rel['fichas'][0]['erros'])


def test_pdf_ausente_e_erro(base: Path) -> None:
    _escrever(base, _ficha('01', pdf='nao_existe.pdf'))
    codigo, rel = _rodar(base)
    assert codigo == 1
    assert any('não existe' in e for e in rel['fichas'][0]['erros'])


def test_pdf_sem_texto_e_defeito_proprio(base: Path) -> None:
    """PDF digitalizado não vira 40 citações 'inventadas' — vira um aviso só.

    Acusar invenção por falha de extração seria a mentira mais cara que este
    script poderia contar: ela faria o pesquisador desconfiar de fichas boas.
    """
    (base / 'mudo.pdf').write_bytes(_montar_pdf([[]]))
    _escrever(base, _ficha('01', pdf='mudo.pdf'))

    codigo, rel = _rodar(base)

    assert codigo == 1
    erros = rel['fichas'][0]['erros']
    assert any('sem texto extraível' in e for e in erros)
    assert not any('NÃO encontrada' in e for e in erros)


# --- os avisos: podem ser extração ruim, quem lê decide ---------------------
def test_citacao_alterada_vira_aviso_nao_erro(base: Path) -> None:
    """Citação com metade reescrita: parcial, AVISO, e o número à vista."""
    _escrever(base, _ficha('01', afirmacoes=[{
        'afirmacao': 'a',
        'citacao': 'Os autores relatam ganho de doze por cento na conclusao final',
        'pagina': 1}]))

    codigo, rel = _rodar(base)

    assert codigo == 0
    assert rel['n_avisos'] == 1
    assert 'parcialmente' in rel['fichas'][0]['avisos'][0]


def test_pagina_divergente_vira_aviso(base: Path) -> None:
    """Citação da p.3 declarada como p.1: a página está errada, e isso aparece."""
    _escrever(base, _ficha('01', afirmacoes=[
        {'afirmacao': 'a', 'citacao': CITACAO_P3, 'pagina': 1}]))
    codigo, rel = _rodar(base)
    assert codigo == 0
    assert any('encontrada na p.3' in a for a in rel['fichas'][0]['avisos'])


def test_pagina_a_uma_de_distancia_nao_vira_aviso(base: Path) -> None:
    """Diferença de uma página é tolerada, e é de propósito.

    Citação que atravessa quebra de página fica com parte na p.N e parte na
    p.N+1, e a extração devolve as duas metades separadas — o script aponta a
    que tiver mais n-gramas. Diferença de uma página é esse caso, não erro de
    quem leu. A tolerância não esconde página errada: esconde no máximo um
    deslocamento de uma, que é o tamanho do ruído.
    """
    _escrever(base, _ficha('01', afirmacoes=[
        {'afirmacao': 'a', 'citacao': CITACAO_P2, 'pagina': 1}]))
    codigo, rel = _rodar(base)
    assert codigo == 0
    assert not rel['fichas'][0]['avisos']


def test_citacao_curta_demais_vira_aviso(base: Path) -> None:
    """Citação de três palavras não ancora nada, mesmo existindo no PDF."""
    _escrever(base, _ficha('01', afirmacoes=[
        {'afirmacao': 'a', 'citacao': 'ganho de doze', 'pagina': 1}]))
    codigo, rel = _rodar(base)
    assert codigo == 0
    assert any('não ancora nada' in a for a in rel['fichas'][0]['avisos'])


# --- normalização: o que a extração faz com o texto --------------------------
def test_hifenizacao_de_quebra_de_linha_nao_quebra_a_citacao(tmp_path: Path) -> None:
    """A extração devolve 'embar-\\ncações'; a citação diz 'embarcações'."""
    (tmp_path / 'artigo.pdf').write_bytes(
        _montar_pdf([['A representacao de embar-', 'cações em portugues e util.']]))
    (tmp_path / 'fichas').mkdir()
    _escrever(tmp_path, _ficha('01', afirmacoes=[
        {'afirmacao': 'a', 'citacao': 'representacao de embarcações em portugues',
         'pagina': 1}]))

    codigo, rel = _rodar(tmp_path)

    assert codigo == 0, rel['fichas'][0]['erros']


def test_acento_perdido_pela_extracao_ainda_casa(tmp_path: Path) -> None:
    """Segunda passada sem acento, para PDF cuja extração perdeu o acento."""
    (tmp_path / 'artigo.pdf').write_bytes(
        _montar_pdf([['O metodo exige pares rotulados e limita a aplicacao pratica.']]))
    (tmp_path / 'fichas').mkdir()
    _escrever(tmp_path, _ficha('01', afirmacoes=[{
        'afirmacao': 'a',
        'citacao': 'O método exige pares rotulados e limita a aplicação prática',
        'pagina': 1}]))

    codigo, rel = _rodar(tmp_path)

    assert codigo == 0, rel['fichas'][0]['erros']


def test_pdf_que_perdeu_os_espacos_ainda_casa(tmp_path: Path) -> None:
    """Terceira passada: PDF cujo extrator devolve as palavras coladas.

    O caso real é o Hu et al. (2023), cuja página 16 sai como
    "Weusedmoredatasets(26datasets, containing 39,736 places worldwide)". Ali a
    tokenização devolve um punhado de palavras gigantes, nenhum n-grama casa, e
    duas citações literais foram acusadas de invenção. A citação está lá palavra
    por palavra; o que a extração não preservou foi o espaço entre elas.
    """
    (tmp_path / 'artigo.pdf').write_bytes(_montar_pdf([
        ['Estudosobrearepresentacaodetextoemportugues.'],
        ['Osautoresrelatamganhodedozeporcentonatarefaprincipal.'],
    ]))
    (tmp_path / 'fichas').mkdir()
    _escrever(tmp_path, _ficha('01', afirmacoes=[{
        'afirmacao': 'a',
        'citacao': 'Os autores relatam ganho de doze por cento na tarefa principal',
        'pagina': 2}]))

    codigo, rel = _rodar(tmp_path)

    assert codigo == 0, rel['fichas'][0]['erros']
    assert rel['fichas'][0]['citacoes'][0]['estado'] == 'exata'


def test_espaco_colado_nao_inventa_citacao(tmp_path: Path) -> None:
    """A passada sem espaço não pode casar o que não está lá.

    Ela procura a citação como trecho contíguo, que é a comparação mais
    permissiva das três. Sem este teste, trocar uma palavra por outra de
    tamanho parecido passaria a ser aceito só porque os espaços sumiram.
    """
    (tmp_path / 'artigo.pdf').write_bytes(_montar_pdf(
        [['Osautoresrelatamganhodedozeporcentonatarefaprincipal.']]))
    (tmp_path / 'fichas').mkdir()
    _escrever(tmp_path, _ficha('01', afirmacoes=[{
        'afirmacao': 'a',
        'citacao': 'Os autores relatam perda de vinte por cento na tarefa principal',
        'pagina': 1}]))

    codigo, rel = _rodar(tmp_path)

    assert codigo == 1
    assert rel['fichas'][0]['citacoes'][0]['estado'] == 'ausente'


def test_palavra_hifenizada_na_quebra_de_linha_ainda_casa(tmp_path: Path) -> None:
    """Quarta passada: o PDF quebra a palavra e deixa um espaço antes do hífen.

    O caso real é o Mortezaagha et al. (2026): a página 13 traz
    "were discov -\\nered" — hífen com espaço antes, não colado na palavra. A
    citação, escrita como qualquer pessoa a escreveria, diz "discovered". A regra
    de hifenização exigia o hífen encostado e não casava, e o verificador acusava
    de invenção uma frase que está no artigo palavra por palavra.
    """
    (tmp_path / 'artigo.pdf').write_bytes(_montar_pdf([
        ['Preliminares.'],
        ['The pipeline processed the full corpus in a single discov -', 'ered run.'],
    ]))
    (tmp_path / 'fichas').mkdir()
    _escrever(tmp_path, _ficha('01', afirmacoes=[{
        'afirmacao': 'a',
        'citacao': 'processed the full corpus in a single discovered run',
        'pagina': 2}]))

    codigo, rel = _rodar(tmp_path)

    assert codigo == 0, rel['fichas'][0]['erros']
    assert rel['fichas'][0]['citacoes'][0]['estado'] == 'exata'


def test_numero_de_linha_da_margem_nao_quebra_a_citacao(tmp_path: Path) -> None:
    """Quinta passada: a revista numera as linhas e o extrator costura o número na frase.

    O caso real é o Valentin et al. (2020): a página 7 sai como
    "multilingual RSS feeds led 109 \\nto a 131% increase in relevant news
    articles for AS F". O "109" é o número da linha impresso na margem; o
    "AS F" é o mesmo estrago numa palavra. A citação da ficha é literal — o
    artigo escreve exatamente aquilo — e era acusada de invenção, com 38% de
    cobertura. O verificador dizendo que o artigo não escreveu o que ele
    escreveu.

    A página tem os dois estragos de propósito: o número de linha, que a
    passada tokenizada resolve, e o espaço dentro da palavra, que só a passada
    sem espaço resolve. É a combinação que o caso real apresentava.
    """
    (tmp_path / 'artigo.pdf').write_bytes(_montar_pdf([[
        'Primeira linha de contexto do artigo 101',
        'Segunda linha de contexto do artigo 102',
        'Terceira linha de contexto do artigo 103',
        'Quarta linha de contexto do artigo 104',
        'Quinta linha de contexto do artigo 105',
        'Since February 2019, th e implementation of multilingual RSS feeds led 106',
        'to a 131% increase in relevant news articles for AS F (207 in English), 107',
        'and 47% for avian 108',
        'influenza (212 in English, 99 translated).',
    ]]))
    (tmp_path / 'fichas').mkdir()
    _escrever(tmp_path, _ficha('01', afirmacoes=[{
        'afirmacao': 'a',
        'citacao': 'the implementation of multilingual RSS feeds led to a 131% '
                   'increase in relevant news articles for ASF (207 in English)',
        'pagina': 1}]))

    codigo, rel = _rodar(tmp_path)

    assert codigo == 0, rel['fichas'][0]['erros']
    assert rel['fichas'][0]['citacoes'][0]['estado'] == 'exata'


def test_numero_que_e_conteudo_no_fim_da_linha_nao_e_apagado(tmp_path: Path) -> None:
    """A remoção do número de linha é condicional, e a condição é o que este teste guarda.

    Um número no fim de uma linha pode ser CONTEÚDO: "o corpus tem 4369
    \\nartigos" é uma frase legítima. Apagá-lo faria a página casar palavra por
    palavra com uma citação que omitiu o número — e a conferência certificaria
    como literal um trecho que não é. Por isso a remoção só acontece na página
    que comprovadamente numera as linhas, e uma página com um número solto não é
    uma delas.

    A asserção é "não é exata", e não "é ausente", porque é isso que a página
    autoriza dizer: a citação tem quase todas as palavras dela, então o veredito
    honesto é o AVISO de trecho parcial, não a acusação de invenção.
    """
    (tmp_path / 'artigo.pdf').write_bytes(_montar_pdf([[
        'O corpus reunido para este estudo tem 4369',
        'artigos de noticia publicados em portugues.',
    ]]))
    (tmp_path / 'fichas').mkdir()
    _escrever(tmp_path, _ficha('01', afirmacoes=[{
        'afirmacao': 'a',
        'citacao': 'O corpus reunido para este estudo tem artigos de noticia '
                   'publicados em portugues',
        'pagina': 1}]))

    _, rel = _rodar(tmp_path)

    assert rel['fichas'][0]['citacoes'][0]['estado'] != 'exata'


def test_numeracao_de_linha_exige_sequencia_e_nao_so_numeros() -> None:
    """O que identifica numeração de linha é o conjunto, não o número solto."""
    numerada = '\n'.join(f'linha de texto qualquer {n}' for n in range(101, 120))
    assert conferir_fichas.numeracao_de_linha(numerada)

    # Mesma quantidade de números, mas com cara de conteúdo: anos, contagens,
    # resultados. Nenhuma linha foi numerada para produzir isto.
    solta = '\n'.join(
        f'linha de texto qualquer {n}' for n in (3, 47, 2019, 4369, 88, 2020, 12, 500))
    assert not conferir_fichas.numeracao_de_linha(solta)


def test_orcamento_de_parsing_e_escalado_e_devolvido(tmp_path: Path, monkeypatch) -> None:
    """PDF denso demais para o orçamento padrão do pypdf é relido com teto maior.

    O Rieger (2024) estoura na página 31, e o arquivo inteiro saía como
    ilegível — limitação da ferramenta virando "não deu para conferir". A
    escalada tem que ser DEVOLVIDA depois: o orçamento é configuração global do
    pypdf, e deixá-lo alto enfraqueceria a guarda contra PDF malformado para
    todo arquivo lido em seguida.
    """
    import pypdf
    from pypdf.errors import LimitReachedError

    (tmp_path / 'artigo.pdf').write_bytes(_montar_pdf([['Uma linha qualquer de teste.']]))

    real = pypdf.PdfReader
    vistos: list[int] = []

    class Espiao:
        def __init__(self, caminho):
            vistos.append(pypdf.get_configuration().stream_parsing_work_maximum_count)
            if len(vistos) == 1:
                raise LimitReachedError('estouro simulado')
            self._real = real(caminho)

        def __getattr__(self, nome):
            return getattr(self._real, nome)

    antes = pypdf.get_configuration().stream_parsing_work_maximum_count
    monkeypatch.setattr(pypdf, 'PdfReader', Espiao)

    pdf = conferir_fichas.Pdf(tmp_path / 'artigo.pdf')

    assert pdf.erro is None
    assert vistos[0] == antes
    assert vistos[1] == conferir_fichas.ORCAMENTO_PARSING_ESCALADO
    assert pypdf.get_configuration().stream_parsing_work_maximum_count == antes


def test_pagina_curta_ainda_e_conferida(tmp_path: Path) -> None:
    """Página com poucas palavras é conferida como qualquer outra.

    Houve aqui um filtro que pulava páginas de menos de vinte palavras para não
    casar citação com legenda de figura. O efeito colateral era pior que o
    problema: num PDF de páginas curtas NENHUMA passava do filtro, a melhor
    cobertura ficava zero, e o script acusava invenção em citação legítima —
    o defeito mais caro que um verificador pode ter, porque ensina quem lê a
    desconfiar de ficha boa. O n-grama de cinco palavras já não casa por acaso;
    o filtro não protegia nada e cegava o script.
    """
    (tmp_path / 'artigo.pdf').write_bytes(
        _montar_pdf([['Resultado principal do estudo em uma linha curta.']]))
    (tmp_path / 'fichas').mkdir()
    _escrever(tmp_path, _ficha('01', afirmacoes=[
        {'afirmacao': 'a', 'citacao': 'Resultado principal do estudo em uma linha', 'pagina': 1}]))

    codigo, rel = _rodar(tmp_path)

    assert codigo == 0, rel['fichas'][0]['erros']
    assert rel['fichas'][0]['citacoes'][0]['estado'] == 'exata'


# --- contrato do diretório ---------------------------------------------------
def test_indice_consolidado_nao_e_conferido_como_ficha(base: Path) -> None:
    """`fichas.json` é gerado a partir das fichas, não é uma delas."""
    _escrever(base, _ficha('01'))
    (base / 'fichas' / 'fichas.json').write_text(
        json.dumps({'fichas': [{'key': '01'}]}), encoding='utf-8')

    codigo, rel = _rodar(base)

    assert codigo == 0
    assert rel['n_fichas'] == 1


def test_json_ilegivel_e_erro_e_nao_derruba_o_resto(base: Path) -> None:
    _escrever(base, _ficha('01'))
    (base / 'fichas' / 'quebrada.json').write_text('{isso não é json', encoding='utf-8')

    codigo, rel = _rodar(base)

    assert codigo == 1
    assert any('JSON ilegível' in e for f in rel['fichas'] for e in f['erros'])
    # A ficha boa continua conferida: um arquivo ruim não esconde os outros.
    assert any(c['estado'] == 'exata' for f in rel['fichas'] for c in f['citacoes'])


def test_diretorio_vazio_sai_com_2(tmp_path: Path, capsys) -> None:
    (tmp_path / 'fichas').mkdir()
    assert conferir_fichas.main([str(tmp_path / 'fichas')]) == 2
    assert 'nenhuma ficha' in capsys.readouterr().err


def test_diretorio_inexistente_sai_com_2(tmp_path: Path, capsys) -> None:
    assert conferir_fichas.main([str(tmp_path / 'nao_existe')]) == 2
    assert 'não é um diretório' in capsys.readouterr().err
