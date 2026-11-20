"""O placar de conformidade: o que ele aceita como prova, e o que ele recusa.

O defeito caro deste script é o inverso do usual. Um verificador que grita
demais ensina quem lê a ignorá-lo; este aqui erra para o outro lado, e o erro
caro é ACEITAR COMO PROVA um veredito que já não vale. Por isso a maior parte
destes testes é sobre o hash: um capítulo editado depois da revisão tem que
aparecer como não verificado, mesmo que o arquivo do veredito diga "conforme"
em letras garrafais.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

_spec = importlib.util.spec_from_file_location(
    "conferir_revisao", REPO / "scripts" / "conferir_revisao.py"
)
conferir_revisao = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(conferir_revisao)


# --- helpers -----------------------------------------------------------------
CAPITULO = "# Capítulo\n\nUma frase qualquer de prosa suficiente para medir.\n"


def _familia(tmp_path: Path, slug: str = "topicos") -> Path:
    pasta = tmp_path / "articles" / slug
    pasta.mkdir(parents=True)
    (pasta / "fichas").mkdir()
    return pasta


def _gravar_veredito(pasta: Path, **overrides) -> None:
    """Grava um veredito com o hash do capítulo COMO ELE ESTÁ AGORA."""
    veredito = {
        "familia": pasta.name,
        "relatorio": f"articles/{pasta.name}/relatorio.md",
        "relatorio_sha256": conferir_revisao.hash_do_arquivo(pasta / "relatorio.md"),
        "conforme": True,
        "divergencias": [],
        "estilo": {"oracoes_empilhadas": 0, "termos_sem_glosa": 0,
                   "adjetivos_inflados": 0, "muletas": 0, "hedges": 0},
    }
    veredito.update(overrides)
    (pasta / "revisao.json").write_text(
        json.dumps(veredito, ensure_ascii=False), encoding="utf-8")


# --- o veredito ---------------------------------------------------------------
def test_sem_arquivo_de_veredito_nao_e_conforme(tmp_path: Path) -> None:
    """O capítulo existe e o julgamento sobre ele não: isso é não verificado."""
    pasta = _familia(tmp_path)
    (pasta / "relatorio.md").write_text(CAPITULO, encoding="utf-8")

    r = conferir_revisao.conferir_veredito(pasta)

    assert r["estado"] == "ausente"
    assert "não dá para saber" in r["detalhe"]


def test_veredito_conforme_sobre_o_texto_atual_passa(tmp_path: Path) -> None:
    pasta = _familia(tmp_path)
    (pasta / "relatorio.md").write_text(CAPITULO, encoding="utf-8")
    _gravar_veredito(pasta)

    assert conferir_revisao.conferir_veredito(pasta)["estado"] == "conforme"


def test_capitulo_editado_depois_da_revisao_invalida_o_veredito(tmp_path: Path) -> None:
    """O teste que justifica o hash existir.

    O arquivo do veredito continua dizendo `conforme: true`. Se o script
    acreditasse nele, um capítulo corrigido (ou piorado) depois da revisão
    apareceria como aprovado para sempre — a pior forma de estar errado, porque
    parece certa.
    """
    pasta = _familia(tmp_path)
    (pasta / "relatorio.md").write_text(CAPITULO, encoding="utf-8")
    _gravar_veredito(pasta)

    (pasta / "relatorio.md").write_text(CAPITULO + "\nUma frase acrescentada depois.\n",
                                        encoding="utf-8")

    r = conferir_revisao.conferir_veredito(pasta)

    assert r["estado"] == "vencido"
    assert "mudou depois da revisão" in r["detalhe"]


def test_veredito_nao_conforme_e_reportado_com_as_divergencias(tmp_path: Path) -> None:
    pasta = _familia(tmp_path)
    (pasta / "relatorio.md").write_text(CAPITULO, encoding="utf-8")
    _gravar_veredito(pasta, conforme=False, divergencias=["linha 61: atribui a Consoli o oposto do que a ficha diz"])

    r = conferir_revisao.conferir_veredito(pasta)

    assert r["estado"] == "nao_conforme"
    assert len(r["divergencias"]) == 1


def test_veredito_sem_hash_nao_pode_afirmar_que_o_texto_mudou(tmp_path: Path) -> None:
    """Veredito sem hash é um estado próprio, não um 'vencido'.

    A diferença não é cosmética: 'vencido' afirma um fato — o capítulo mudou
    depois da revisão. Um veredito que nunca trouxe o hash não autoriza essa
    afirmação. O verificador tem que dizer o que sabe, e o que ele sabe aqui é
    menos.
    """
    pasta = _familia(tmp_path)
    (pasta / "relatorio.md").write_text(CAPITULO, encoding="utf-8")
    _gravar_veredito(pasta, relatorio_sha256=None)
    veredito = json.loads((pasta / "revisao.json").read_text(encoding="utf-8"))
    del veredito["relatorio_sha256"]
    (pasta / "revisao.json").write_text(json.dumps(veredito), encoding="utf-8")

    r = conferir_revisao.conferir_veredito(pasta)

    assert r["estado"] == "sem_hash"
    assert "mudou depois" not in r["detalhe"]


def test_veredito_ilegivel_nao_derruba_o_script(tmp_path: Path) -> None:
    pasta = _familia(tmp_path)
    (pasta / "relatorio.md").write_text(CAPITULO, encoding="utf-8")
    (pasta / "revisao.json").write_text("{ isto não é json", encoding="utf-8")

    r = conferir_revisao.conferir_veredito(pasta)

    assert r["estado"] == "ilegivel"


def test_veredito_sem_capitulo_e_estado_proprio(tmp_path: Path) -> None:
    """Capítulo apagado com o veredito no lugar: 'vencido' seria enganoso.

    Dizer que o texto mudou sugeriria que ainda há texto. Não há — e a diferença
    importa para quem for consertar.
    """
    pasta = _familia(tmp_path)
    (pasta / "relatorio.md").write_text(CAPITULO, encoding="utf-8")
    _gravar_veredito(pasta)
    (pasta / "relatorio.md").unlink()

    assert conferir_revisao.conferir_veredito(pasta)["estado"] == "sem_capitulo"


# --- o placar ----------------------------------------------------------------
def test_familia_em_articles_e_so_a_que_tem_fichas(tmp_path: Path) -> None:
    """Sem base de fichas não há família: `notes/` não é uma."""
    _familia(tmp_path, "topicos")
    (tmp_path / "articles" / "vazia").mkdir(parents=True)

    nomes = [p.name for p in conferir_revisao.familias_em(tmp_path)]

    assert nomes == ["topicos"]


def test_familia_sem_fichas_sai_com_2(tmp_path: Path, capsys) -> None:
    (tmp_path / "articles").mkdir()

    assert conferir_revisao.main(["--raiz", str(tmp_path)]) == 2
    assert "nenhuma família" in capsys.readouterr().err


def test_placar_completo_sai_com_1_quando_falta_veredito(tmp_path: Path, capsys) -> None:
    """Capítulo e fichas presentes, veredito ausente: o placar reprova."""
    pasta = _familia(tmp_path, "topicos")
    (pasta / "relatorio.md").write_text(CAPITULO, encoding="utf-8")

    codigo = conferir_revisao.main(["--raiz", str(tmp_path)])

    saida = capsys.readouterr().out
    assert codigo == 1
    assert "NEM TUDO CONFORME" in saida
    assert "veredito da revisão: ausente" in saida


def test_placar_em_json_nao_imprime_veredito_de_prosa(tmp_path: Path, capsys) -> None:
    pasta = _familia(tmp_path, "topicos")
    (pasta / "relatorio.md").write_text(CAPITULO, encoding="utf-8")

    conferir_revisao.main(["--raiz", str(tmp_path), "--json"])

    saida = capsys.readouterr().out
    assert "NEM TUDO CONFORME" not in saida
    json.loads(saida)  # o stdout inteiro é JSON, nada mais


def test_todo_estado_de_veredito_rende_sem_quebrar(capsys) -> None:
    """O placar tem que saber imprimir TODOS os estados, inclusive os que reprovam.

    `nao_conforme` é o único estado que não traz `detalhe` — só as divergências —,
    e a primeira versão do renderizador assumiu que todo estado não-conforme
    trazia. Quebrou exatamente contra os dados reais, na primeira execução. Um
    placar que quebra quando encontra um problema é pior que inútil: é a hora em
    que alguém mais precisa dele.
    """
    estados = [
        {"estado": "ausente", "detalhe": "não há veredito gravado"},
        {"estado": "sem_capitulo", "detalhe": "o veredito existe mas o capítulo não"},
        {"estado": "ilegivel", "detalhe": "JSONDecodeError: ..."},
        {"estado": "vencido", "detalhe": "o capítulo mudou depois da revisão", "divergencias": []},
        {"estado": "sem_hash", "detalhe": "o veredito não traz o hash do capítulo"},
        {"estado": "nao_conforme", "divergencias": ["uma divergência qualquer"]},
        {"estado": "conforme", "divergencias": [], "estilo": None},
    ]
    for veredito in estados:
        conferir_revisao.imprimir([{
            "familia": "topicos",
            "citacoes": {"ok": True, "fichas": 1, "citacoes": 1, "erros": 0, "avisos": 0},
            "veredito": veredito,
        }])
        assert f"veredito da revisão: {veredito['estado']}" in capsys.readouterr().out
