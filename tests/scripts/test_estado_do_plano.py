"""O estado medido do plano: o que ele conta como prova, e o que ele se recusa a inventar.

O defeito caro deste script não é gritar demais — é o inverso, e é pior. Ele
alimenta a skill que decide a semana, e a skill acredita nele. Um ✅ falso faz o
plano declarar progresso que não houve, que é exatamente a mentira que este
arquivo existe para impedir. Por isso a maior parte destes testes é sobre o que
NÃO vira ✅: artefato ausente, token entre crases que nunca foi caminho, fatia
que sumiu da contagem.

O segundo defeito caro é o silêncio: um plano de 13 fatias lido como 5 fatias
não produz erro nenhum, produz um relatório curto e confiante.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

_spec = importlib.util.spec_from_file_location(
    "estado_do_plano", REPO / "scripts" / "estado_do_plano.py"
)
estado = importlib.util.module_from_spec(_spec)
# `dataclass` procura o módulo da classe em `sys.modules` para resolver as
# anotações. Carregar por caminho não registra nada, então sem esta linha o
# próprio script estoura na importação — e o erro aparece como se fosse do
# script, não do teste.
sys.modules[_spec.name] = estado
_spec.loader.exec_module(estado)


# --- helpers -----------------------------------------------------------------

PLANO = """# Plano de entrega

**Prazo:** 2027-02-19 (13 semanas).

## 5. As fatias

| # | Fecha em | Fatia | Prova que fechou | Prosa |
|---|---|---|---|---|
| 1 | 2026-11-27 | A barra em WIS | `data/forecast/bar.parquet` | — |
| 2 | 2026-12-04 | O harness único | `data/forecast/harness.parquet` | — |
| 3 | 2026-12-11 | A nota escrita | `notes/nota.md` e a `frase solta` | Métodos |

Depois da tabela vem prosa, e ela não é fatia.
"""

REGUA = """# Forecast evaluation

| Stage | Entry point | Status |
|---|---|---|
| Target panel | `load_target` | **complete** |
| Naive baselines | `python -m src.forecast` | **complete** |
| "No text" model | — | next |

---

## 4. Open decisions

| Decision | Now | Why |
|---|---|---|
| Horizon | 1 week | Shortest path to a first number |
| Geography | BR | The comparison is honest at this grain |
"""


def _repo(tmp_path: Path) -> Path:
    """Um repositório mínimo: o plano, o avaliador, um caminho e as famílias.

    Monta o repositório e NADA MAIS — em particular, não cria artefato nenhum.
    Quem cria artefato é `_touch`, e a separação importa: um helper que monta e
    cria ao mesmo tempo reescreve o plano quando o teste só queria acrescentar
    um arquivo, e o teste passa a medir o plano errado (foi o que aconteceu).
    """
    (tmp_path / "notes").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "forecast").mkdir(parents=True, exist_ok=True)
    (tmp_path / "notes" / "plano.md").write_text(PLANO, encoding="utf-8")
    (tmp_path / "src" / "forecast" / "README.md").write_text(REGUA, encoding="utf-8")
    (tmp_path / "notes" / "01-lexico.md").write_text(
        "# 01 — Léxico\n\n**Estado:** testando — 2026-10-07\n\n"
        "## Pendências\n\n- [x] feita\n- [ ] aberta\n- [ ] outra aberta\n",
        encoding="utf-8",
    )
    familia = tmp_path / "articles" / "topicos"
    (familia / "fichas").mkdir(parents=True, exist_ok=True)
    (familia / "relatorio.md").write_text("# Relatório\n", encoding="utf-8")
    (familia / "fichas" / "a.json").write_text("{}", encoding="utf-8")
    return tmp_path


def _plano(root: Path, texto: str) -> None:
    (root / "notes" / "plano.md").write_text(texto, encoding="utf-8")


def _touch(root: Path, *relativos: str) -> None:
    for rel in relativos:
        caminho = root / rel
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text("x", encoding="utf-8")


def _report(root: Path, hoje: str = "2026-11-20") -> dict:
    return estado.build_report(root, date.fromisoformat(hoje), 7)


def _git(root: Path, *args: str) -> None:
    """Git de verdade, sem assinatura e sem identidade global.

    A distinção entre "existe" e "está no git" é do git; um dublê testaria a
    fiação, não a medição.
    """
    base = ["git", "-c", "user.email=t@t", "-c", "user.name=t", "-c", "commit.gpgsign=false"]
    subprocess.run([*base, *args], cwd=root, check=True, capture_output=True)


def _fatia(report: dict, numero: int) -> dict:
    return next(f for f in report["fatias"] if f["numero"] == numero)


# --- o prazo -----------------------------------------------------------------


def test_o_prazo_vem_do_cabecalho_do_plano(tmp_path: Path) -> None:
    report = _report(_repo(tmp_path))
    assert report["prazo"] == "2027-02-19"
    assert report["dias_restantes"] == 91


def test_a_semana_atual_e_a_primeira_que_ainda_nao_venceu(tmp_path: Path) -> None:
    report = _report(_repo(tmp_path), hoje="2026-11-28")  # a fatia 1 venceu em 27/11
    assert report["proxima_fatia"] == 2
    assert report["semana"] == {"atual": 2, "total": 3}


def test_fatia_fechada_nao_e_a_proxima(tmp_path: Path) -> None:
    """O defeito que isto conserta apareceu no plano real.

    A fatia 0 fechou um dia antes do prazo dela e continuou sendo anunciada como
    "próxima" — o relatório mandava fazer o que já estava feito.
    """
    root = _repo(tmp_path)
    _touch(root, "data/forecast/bar.parquet")  # a fatia 1 fecha; hoje é 2026-11-20
    report = _report(root)
    assert _fatia(report, 1)["status"] == "existe"
    assert report["proxima_fatia"] == 2


# --- o que conta como prova --------------------------------------------------


def test_artefato_que_existe_vira_existe(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _touch(root, "data/forecast/bar.parquet")
    assert _fatia(_report(root), 1)["status"] == "existe"


def test_artefato_ausente_vira_nao_existe_e_diz_qual_falta(tmp_path: Path) -> None:
    fatia = _fatia(_report(_repo(tmp_path)), 2)
    assert fatia["status"] == "não existe"
    assert fatia["falta"] == ["data/forecast/harness.parquet"]


def test_glob_conta_como_existe_quando_ha_mais_de_um_arquivo(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _plano(root, PLANO.replace("`data/forecast/bar.parquet`", "`data/forecast/*.parquet`"))
    _touch(root, "data/forecast/a.parquet", "data/forecast/b.parquet")
    assert _fatia(_report(root), 1)["status"] == "existe"


def test_crase_que_nao_e_caminho_nao_vira_falta(tmp_path: Path) -> None:
    """`frase solta` é markdown, não arquivo. Acusar falta disso ensina a ignorar o relatório."""
    root = _repo(tmp_path)
    _touch(root, "notes/nota.md")
    fatia = _fatia(_report(root), 3)
    assert fatia["existe"] == ["notes/nota.md"]
    assert fatia["falta"] == []
    assert fatia["status"] == "existe"


def test_prova_parcial_e_parcial_e_nao_existe(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _plano(root, PLANO.replace("`data/forecast/bar.parquet`", "`notes/nota.md` `data/forecast/bar.parquet`"))
    _touch(root, "notes/nota.md")
    assert _fatia(_report(root), 1)["status"] == "parcial"


# --- existir não basta: o artefato precisa estar no git -----------------------


def test_artefato_no_disco_e_fora_do_git_nao_fecha_a_fatia(tmp_path: Path) -> None:
    """O caso que criou esta regra: a semana 0 do plano real É colocar no git.

    Com ✅ por existência, ela apareceria pronta no dia em que nasceu, listando
    como prova exatamente os arquivos que ainda estão fora do git — e o relatório
    diria "ficou pronto" e "está em risco" na mesma linha.
    """
    if shutil.which("git") is None:
        pytest.skip("sem git não há o que medir")
    root = _repo(tmp_path)
    _touch(root, "data/forecast/bar.parquet")
    _git(root, "init", "-q")

    fatia = _fatia(_report(root), 1)
    assert fatia["status"] == "no disco, fora do git"
    assert fatia["nao_commitado"] == ["data/forecast/bar.parquet"]


def test_artefato_no_git_fecha_a_fatia(tmp_path: Path) -> None:
    if shutil.which("git") is None:
        pytest.skip("sem git não há o que medir")
    root = _repo(tmp_path)
    _touch(root, "data/forecast/bar.parquet")
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "coloca no git")

    assert _fatia(_report(root), 1)["status"] == "existe"


# --- o marcador: existir não é o mesmo que dizer ---------------------------------


def test_marcador_presente_vira_existe(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _plano(root, PLANO.replace("`data/forecast/bar.parquet`", "`notes/nota.md#WIS`"))
    (root / "notes" / "nota.md").write_text("a barra agora é WIS", encoding="utf-8")
    assert _fatia(_report(root), 1)["status"] == "existe"


def test_arquivo_que_existe_sem_o_marcador_vira_nao_existe(tmp_path: Path) -> None:
    """É o defeito que o marcador veio consertar: documento velho contando como fatia fechada."""
    root = _repo(tmp_path)
    _plano(root, PLANO.replace("`data/forecast/bar.parquet`", "`notes/nota.md#WIS`"))
    (root / "notes" / "nota.md").write_text("ainda fala em MAE", encoding="utf-8")
    fatia = _fatia(_report(root), 1)
    assert fatia["status"] == "não existe"
    assert fatia["falta"] == ["notes/nota.md#WIS"]


def test_marcador_em_arquivo_binario_nao_quebra(tmp_path: Path) -> None:
    """`.parquet` não é texto. Procurar marcador nele tem que devolver não, não estourar."""
    root = _repo(tmp_path)
    _plano(root, PLANO.replace("`data/forecast/bar.parquet`", "`data/forecast/bar.parquet#WIS`"))
    alvo = root / "data" / "forecast" / "bar.parquet"
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_bytes(b"\x00\x01\x02\xff\xfe")
    assert _fatia(_report(root), 1)["status"] == "não existe"


# --- o silêncio, que é o defeito que não levanta erro ------------------------


def test_nenhuma_fatia_e_silenciosamente_perdida(tmp_path: Path) -> None:
    report = _report(_repo(tmp_path))
    assert [f["numero"] for f in report["fatias"]] == [1, 2, 3]


def test_prosa_depois_da_tabela_nao_vira_fatia(tmp_path: Path) -> None:
    """Uma linha de prosa com pipe no meio não pode entrar como linha de tabela."""
    root = _repo(tmp_path)
    plano = (root / "notes" / "plano.md").read_text(encoding="utf-8")
    (root / "notes" / "plano.md").write_text(
        plano + "\n| 9 | 2027-01-01 | fatia de mentira | `x` | — |\n", encoding="utf-8"
    )
    # a linha está DEPOIS do fim da tabela, então não conta
    assert [f["numero"] for f in _report(root)["fatias"]] == [1, 2, 3]


# --- as outras medições ------------------------------------------------------


def test_a_regua_le_a_palavra_e_nao_so_o_emoji(tmp_path: Path) -> None:
    regua = _report(_repo(tmp_path))["regua"]
    assert regua == [
        {"estagio": "Target panel", "estado": "✅"},
        {"estagio": "Naive baselines", "estado": "✅"},
        {"estagio": '"No text" model', "estado": "⬜"},
    ]


def test_a_segunda_tabela_do_documento_nao_vira_estagio(tmp_path: Path) -> None:
    """O README do avaliador tem uma tabela de decisões em aberto, também com 3 colunas.

    Sem parar no fim da primeira tabela, "Horizon" e "Geography" entram como
    estágios — e o avaliador aparece com decisões que ele não tem.
    """
    estagios = [r["estagio"] for r in _report(_repo(tmp_path))["regua"]]
    assert "Horizon" not in estagios
    assert "Geography" not in estagios


def test_as_pendencias_de_cada_caminho_sao_contadas(tmp_path: Path) -> None:
    caminhos = _report(_repo(tmp_path))["caminhos"]
    assert len(caminhos) == 1
    assert caminhos[0]["arquivo"] == "01-lexico.md"
    assert caminhos[0]["estado"] == "testando"
    assert (caminhos[0]["abertas"], caminhos[0]["fechadas"]) == (2, 1)


def test_a_literatura_conta_as_fichas(tmp_path: Path) -> None:
    literatura = _report(_repo(tmp_path))["literatura"]
    topicos = next(f for f in literatura if f["familia"] == "topicos")
    assert topicos["relatorio"] is True
    assert topicos["ranking"] is False
    assert topicos["fichas"] == 1


def test_produto_ausente_nao_quebra_a_medicao(tmp_path: Path) -> None:
    produtos = _report(_repo(tmp_path))["produtos"]
    assert produtos and all(p["existe"] is False for p in produtos)


# --- a leitura e o formato ---------------------------------------------------


def test_o_render_sai_e_aponta_a_proxima_fatia(tmp_path: Path) -> None:
    texto = estado.render(_report(_repo(tmp_path)))
    assert "PLANO — notes/plano.md" in texto
    assert "próxima fatia: 1" in texto
    assert "AVALIADOR (src/forecast/README.md)" in texto


def test_o_render_conta_as_fatias_por_estado(tmp_path: Path) -> None:
    """A visão macro: quantas fecharam, quantas faltam. Sem isso a leitura é fatia a fatia."""
    root = _repo(tmp_path)
    _touch(root, "data/forecast/bar.parquet")
    texto = estado.render(_report(root))
    assert "fechadas: 1" in texto
    assert "não começaram: 2" in texto
    assert "pela metade" not in texto


def test_o_plano_real_do_repositorio_ainda_e_legivel() -> None:
    """Se o formato do plano mudar, é aqui que se descobre — e não numa segunda-feira."""
    report = estado.build_report(REPO, date(2026, 11, 20), 7)
    assert report["prazo"] is not None
    assert len(report["fatias"]) >= 1
