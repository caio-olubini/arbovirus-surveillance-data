#!/usr/bin/env python3
"""Estado medido do plano de entrega — o que a skill `plano-entrega` lê antes de opinar.

O plano (`notes/plano.md`) diz o que fecha em cada semana e qual artefato prova
que fechou. Este script mede a segunda metade — o artefato existe? está no git? —
e mede também o resto do repositório: o estado declarado de cada caminho em
`notes/`, os estágios do avaliador em `src/forecast/README.md`, as famílias de
literatura em `articles/`, os produtos em `data/`, e o que foi commitado.

POR QUE SCRIPT E NÃO AGENTE. A parte que se mede não pode ser lembrada de
cabeça. Um agente que "lê o repositório" relata o que esperava encontrar, e
relata na mesma voz confiante quando erra; um `Path.exists()` não tem expectativa.
O que sobra para o agente é o JULGAMENTO — o que andou, o que não andou, e qual é
a próxima fatia — que é justamente a parte que nenhuma medição decide.

O SCRIPT NÃO ESCREVE NADA. Não marca fatia como concluída, não edita o plano.
Quem edita é a skill, depois de ler isto e depois de você confirmar. Um script
que se autodeclara concluído é um script que mente: a existência de um arquivo
não é o mesmo que a fatia estar fechada, e a diferença entre as duas é
exatamente o que se quer enxergar.

O QUE ELE NÃO CONSEGUE VER, e por isso não finge ver:

  - Se o NÚMERO dentro do artefato é o número certo. Ele vê que a tabela de
    métricas existe; se ela tem 150 semanas ou 557, quem lê confere.
  - Se a fatia fez o que prometia. Existir não é o mesmo que estar correto.
  - O que está na sua cabeça. Prazo que mudou, decisão tomada numa conversa.

Uso:
    uv run python scripts/estado_do_plano.py
    uv run python scripts/estado_do_plano.py --semana 4      # simula outra data
    uv run python scripts/estado_do_plano.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = "notes/plano.md"
RULER_DOC = "src/forecast/README.md"

# Cada família de produto é um rótulo e um glob, não um nome de arquivo exato:
# o nome do produto muda quando o recorte muda (por horizonte, por nível), e um
# script que quebra a cada renomeação é um script que você para de rodar.
PRODUCTS: list[tuple[str, str]] = [
    ("SINAN — série de casos", "data/epidemiological/SINAN/SINAN_*_cases.parquet"),
    ("Clima — UF × EW", "data/climate/era5/ERA5_UF_EW.parquet"),
    ("GT busca — EW", "data/google_trends/GoogleTrends_search_EW.parquet"),
    ("GT related — mensal", "data/google_trends/GoogleTrends_related_query_monthly.parquet"),
    ("Notícia — corpus de texto", "data/pipeline/news/EBC_dengue_text.parquet"),
    ("Notícia — léxico (braço 01)", "data/pipeline/news/EBC_dengue_lexicon_EW.parquet"),
    ("Notícia — embeddings (braço 02)", "data/pipeline/news/EBC_dengue_embeddings_EW.parquet"),
    ("Notícia — tópicos (braço 03)", "data/pipeline/news/EBC_dengue_topics_EW.parquet"),
    ("Previsão — previsões", "data/forecast/*predictions.parquet"),
    ("Previsão — métricas", "data/forecast/*metrics.parquet"),
]

BACKTICK = re.compile(r"`([^`]+)`")
DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
SLICE_NUMBER = re.compile(r"^\d+$")
ESTADO = re.compile(r"\*\*Estado:\*\*\s*([^—\n]+)")
CHECKBOX_OPEN = re.compile(r"^\s*-\s*\[ \]")
CHECKBOX_DONE = re.compile(r"^\s*-\s*\[x\]", re.IGNORECASE)
STAGE_ROW = re.compile(r"^\|")


# --------------------------------------------------------------------------- #
# medição
# --------------------------------------------------------------------------- #


@dataclass
class Slice:
    """Uma fatia do plano: o que fecha, quando, e o que prova que fechou."""

    number: int
    due: date | None
    what: str
    proof: list[str]
    prose: str = ""
    found: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    uncommitted: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        if not self.proof:
            return "sem prova declarada"
        if self.missing and self.found:
            return "parcial"
        if self.missing:
            return "não existe"
        if self.uncommitted:
            # O artefato existe e o trabalho ainda não entrou no git. O plano diz,
            # em uma linha, que "trabalho que não foi colocado no git não conta
            # como progresso" — e a semana 0 tem isso como conteúdo: ela É
            # colocar no git. Se o ✅ saísse mesmo assim, a entrega nasceria
            # pronta.
            return "no disco, fora do git"
        return "existe"


@dataclass
class Plan:
    deadline: date | None
    slices: list[Slice]

    def current(self, today: date) -> Slice | None:
        """A primeira fatia que ainda não fechou e ainda não venceu. O que fazer AGORA.

        Fatia fechada sai da conta mesmo que a data dela ainda não tenha passado.
        Sem isso, uma fatia concluída um dia antes do prazo continua sendo
        anunciada como "próxima" até o prazo vencer — e o relatório manda fazer o
        que já está feito.
        """
        upcoming = [s for s in self.slices if s.due and s.due >= today and s.status != "existe"]
        return upcoming[0] if upcoming else None

    def index_of(self, today: date) -> tuple[int, int]:
        """(semana atual, total) — para dizer quanto do prazo já passou."""
        total = len(self.slices)
        done = sum(1 for s in self.slices if s.due and s.due < today)
        return (min(done + 1, total), total)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def parse_plan(plan_file: Path) -> Plan:
    """Lê o plano. O que não estiver no formato esperado é ignorado, não adivinhado."""
    text = read(plan_file)

    deadline = None
    prazo = re.search(r"\*\*Prazo:\*\*[^\n]*?(\d{4}-\d{2}-\d{2})", text)
    if prazo:
        deadline = date.fromisoformat(prazo.group(1))

    slices: list[Slice] = []
    columns: dict[str, int] = {}
    for line in text.splitlines():
        if not line.startswith("|"):
            if columns:
                break  # a tabela acabou
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if "Fecha em" in cells:
            columns = {name: i for i, name in enumerate(cells)}
            continue
        if not columns:
            continue
        if len(cells) <= max(columns.values()):
            continue
        number = cells[columns["#"]].strip("* ")
        if not SLICE_NUMBER.match(number):
            continue
        raw_date = DATE.search(cells[columns["Fecha em"]])
        proof_cell = cells[columns["Prova que fechou"]] if "Prova que fechou" in columns else ""
        slices.append(
            Slice(
                number=int(number),
                due=date.fromisoformat(raw_date.group(1)) if raw_date else None,
                what=cells[columns.get("Fatia", 2)],
                proof=parse_proof(proof_cell),
                prose=cells[columns["Prosa"]] if "Prosa" in columns else "",
            )
        )
    return Plan(deadline=deadline, slices=slices)


def parse_proof(cell: str) -> list[str]:
    """Só o que é caminho conta como prova.

    A coluna de prova é markdown, e markdown usa crase para mais do que caminho:
    um `comando`, um `nome de coluna`. Tomar todo trecho entre crases por
    caminho faria o script anunciar como FALTA algo que nunca foi um arquivo — e
    um relatório que acusa falta onde não há é um relatório que você aprende a
    ignorar. Caminho não tem espaço; prosa tem.
    """
    return [token for token in BACKTICK.findall(cell) if token and not re.search(r"\s", token)]


def measure_slices(plan: Plan, root: Path) -> None:
    """Para cada fatia: os artefatos que ela declara existem? estão no git?

    A prova aceita duas formas, porque a maioria das fatias não se prova por
    existência. `caminho` prova que o artefato foi produzido; `caminho#marcador`
    prova que ele diz o que a fatia prometia — o README do avaliador que passou a
    descrever o WIS, o plano que passou a citar o ganho mínimo declarado. Sem a segunda
    forma, todo documento que já existe apareceria como fatia fechada no dia em
    que foi criado, e a fatia nunca teria como fechar.

    Continua sendo prova fraca: o marcador mostra que a palavra está lá, não que
    o número ao lado dela está certo. Quem fecha a fatia é quem lê.
    """
    for s in plan.slices:
        for token in s.proof:
            pattern, marker = split_proof(token)
            hits = sorted(p for p in root.glob(pattern) if p.is_file())
            if not hits or (marker and not any(contains(p, marker) for p in hits)):
                s.missing.append(token)
                continue
            s.found.append(token)
            if any(is_uncommitted(p, root) for p in hits):
                s.uncommitted.append(token)


def split_proof(token: str) -> tuple[str, str]:
    """`data/forecast/*.parquet#WIS` → (`data/forecast/*.parquet`, `WIS`)."""
    path, _, marker = token.partition("#")
    return path, marker


def contains(path: Path, marker: str) -> bool:
    """Marcador em arquivo de texto. Binário não tem marcador — e não é erro."""
    try:
        return marker in path.read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeDecodeError):
        return False


def is_uncommitted(path: Path, root: Path) -> bool:
    """Artefato que existe no disco e não está no git. Trabalho em risco."""
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        return False
    out = git(["status", "--porcelain", "--", rel], root)
    return bool(out.strip())


def measure_paths(root: Path) -> list[dict[str, object]]:
    """O estado declarado de cada caminho de pesquisa, e quantas pendências restam."""
    rows: list[dict[str, object]] = []
    for f in sorted((root / "notes").glob("[0-9][0-9]-*.md")):
        text = read(f)
        estado = ESTADO.search(text)
        rows.append(
            {
                "arquivo": f.name,
                "estado": estado.group(1).strip() if estado else "(sem estado declarado)",
                "abertas": sum(1 for line in text.splitlines() if CHECKBOX_OPEN.match(line)),
                "fechadas": sum(1 for line in text.splitlines() if CHECKBOX_DONE.match(line)),
            }
        )
    return rows


def measure_ruler(root: Path) -> list[dict[str, str]]:
    """Os estágios do avaliador, lidos da tabela do próprio README dele.

    Duas armadilhas, as duas encontradas rodando isto pela primeira vez:

    1. O README escreve o estágio em palavra (`complete`, `next`), não em emoji —
       o emoji é a leitura, não a fonte.
    2. O mesmo documento tem uma SEGUNDA tabela, de decisões em aberto, também
       com três colunas. Sem parar no fim da primeira, "Horizon" e "Level"
       entram como se fossem estágios do avaliador — e uma seção que inventa
       estágios é uma seção que você aprende a pular.
    """
    rows: list[dict[str, str]] = []
    started = False
    for line in read(root / RULER_DOC).splitlines():
        if not STAGE_ROW.match(line):
            if started:
                break  # a tabela de estágios acabou; o que vem depois é outra coisa
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 3 or set(cells[0].strip("`")) <= {"-"}:
            continue
        if cells[0] in {"Stage"} or cells[0].strip("`") == "Stage":
            started = True
            continue
        status = cells[2].lower()
        if "✅" in status or "complete" in status:
            mark = "✅"
        elif "⬜" in status or "next" in status or "todo" in status:
            mark = "⬜"
        else:
            mark = "?"
        rows.append({"estagio": cells[0].strip("`"), "estado": mark})
    return rows


def measure_literature(root: Path) -> list[dict[str, object]]:
    """As famílias de literatura: o relatório existe? quantas fichas foram escritas?"""
    rows: list[dict[str, object]] = []
    for d in sorted((root / "articles").iterdir()):
        if not d.is_dir():
            continue
        rows.append(
            {
                "familia": d.name,
                "relatorio": (d / "relatorio.md").is_file(),
                "ranking": (d / "ranking.md").is_file(),
                "fichas": len(list((d / "fichas").glob("*.json"))) if (d / "fichas").is_dir() else 0,
            }
        )
    return rows


def measure_products(root: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for label, pattern in PRODUCTS:
        hits = sorted(root.glob(pattern))
        rows.append(
            {
                "produto": label,
                "existe": bool(hits),
                "arquivos": len(hits),
                "nao_commitado": any(is_uncommitted(p, root) for p in hits),
            }
        )
    return rows


def measure_git(root: Path, since_days: int) -> dict[str, object]:
    log = git(
        ["log", f"--since={since_days} days ago", "--pretty=%ad %s", "--date=short"], root
    )
    commits = [line for line in log.splitlines() if line.strip()]
    dirty = [line for line in git(["status", "--porcelain"], root).splitlines() if line.strip()]
    return {
        "commits_na_janela": len(commits),
        "commits": commits,
        "nao_commitado": len(dirty),
    }


def git(args: list[str], root: Path) -> str:
    """Git é opcional: fora de um repositório ou sem o binário, a medição continua."""
    try:
        return subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


# --------------------------------------------------------------------------- #
# leitura
# --------------------------------------------------------------------------- #


def build_report(root: Path, today: date, since_days: int) -> dict[str, object]:
    plan = parse_plan(root / PLAN_PATH)
    measure_slices(plan, root)
    week, total = plan.index_of(today)
    return {
        "hoje": today.isoformat(),
        "prazo": plan.deadline.isoformat() if plan.deadline else None,
        "dias_restantes": (plan.deadline - today).days if plan.deadline else None,
        "semana": {"atual": week, "total": total},
        "fatias": [
            {
                "numero": s.number,
                "vence": s.due.isoformat() if s.due else None,
                "o_que": s.what,
                "status": s.status,
                "existe": s.found,
                "falta": s.missing,
                "nao_commitado": s.uncommitted,
                "prosa": s.prose,
            }
            for s in plan.slices
        ],
        "proxima_fatia": (lambda s: s.number if s else None)(plan.current(today)),
        "caminhos": measure_paths(root),
        "regua": measure_ruler(root),
        "literatura": measure_literature(root),
        "produtos": measure_products(root),
        "git": measure_git(root, since_days),
        "janela_dias": since_days,
    }


def render(report: dict[str, object]) -> str:
    fatias = report["fatias"]
    caminhos = report["caminhos"]
    regua = report["regua"]
    literatura = report["literatura"]
    produtos = report["produtos"]
    git_info = report["git"]
    semana = report["semana"]
    assert isinstance(fatias, list) and isinstance(caminhos, list)
    assert isinstance(regua, list) and isinstance(literatura, list) and isinstance(produtos, list)
    assert isinstance(git_info, dict) and isinstance(semana, dict)

    out: list[str] = []
    prazo = report["prazo"] or "(sem prazo declarado)"
    dias = report["dias_restantes"]
    out.append(f"PLANO — {PLAN_PATH}")
    out.append(
        f"  hoje {report['hoje']}   prazo {prazo}"
        + (f"   faltam {dias} dias" if dias is not None else "")
        + f"   semana {semana['atual']} de {semana['total']}"
    )

    out.append("")
    out.append("FATIAS")
    for s in fatias:
        mark = {
            "existe": "✅",
            "parcial": "🟡",
            "no disco, fora do git": "⚠️",
            "não existe": "⬜",
        }.get(str(s["status"]), "·")
        out.append(f"  {mark} {s['numero']:>2}  {s['vence'] or '---------'}  {str(s['o_que'])[:58]}")
        if s["falta"]:
            out.append(f"        falta: {', '.join(s['falta'])}")
        if s["nao_commitado"]:
            out.append(f"        no disco e FORA do git: {', '.join(s['nao_commitado'])}")
    proxima = report["proxima_fatia"]
    contar = Counter(str(s["status"]) for s in fatias)
    resumo = " · ".join(
        f"{rotulo}: {contar[chave]}"
        for chave, rotulo in (
            ("existe", "fechadas"),
            ("no disco, fora do git", "no disco e fora do git"),
            ("parcial", "pela metade"),
            ("não existe", "não começaram"),
            ("sem prova declarada", "sem prova declarada"),
        )
        if contar[chave]
    )
    out.append(f"  {resumo}")
    out.append(f"  → próxima fatia: {proxima if proxima is not None else '(nenhuma no prazo)'}")

    out.append("")
    out.append("GIT")
    out.append(
        f"  commits nos últimos {report['janela_dias']} dias: {git_info['commits_na_janela']}"
    )
    for c in git_info["commits"][:10]:
        out.append(f"    {c}")
    out.append(f"  arquivos não commitados: {git_info['nao_commitado']}")

    out.append("")
    out.append("CAMINHOS (notes/)")
    for p in caminhos:
        out.append(
            f"  {str(p['arquivo'])[:34]:<34} {str(p['estado'])[:28]:<28}"
            f" abertas {p['abertas']}  fechadas {p['fechadas']}"
        )

    out.append("")
    out.append(f"AVALIADOR ({RULER_DOC}) — a medição de todo modelo")
    for r in regua:
        out.append(f"  {r['estado']}  {r['estagio']}")

    out.append("")
    out.append("LITERATURA (articles/)")
    for lit in literatura:
        rel = "relatório ✅" if lit["relatorio"] else "relatório ⬜"
        rank = "ranking ✅" if lit["ranking"] else "ranking ⬜"
        out.append(f"  {str(lit['familia']):<18} {rel}  {rank}  fichas {lit['fichas']}")

    out.append("")
    out.append("PRODUTOS (data/)")
    for prod in produtos:
        mark = "✅" if prod["existe"] else "⬜"
        danger = "  · FORA do git" if prod["nao_commitado"] else ""
        out.append(f"  {mark}  {prod['produto']}{danger}")

    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT, help="raiz do repositório")
    parser.add_argument("--hoje", type=date.fromisoformat, default=None, help="AAAA-MM-DD (para simular)")
    parser.add_argument("--janela", type=int, default=7, help="dias de histórico do git")
    parser.add_argument("--json", action="store_true", help="saída em JSON")
    args = parser.parse_args(argv)

    today = args.hoje or date.today()
    report = build_report(args.root, today, args.janela)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    else:
        print(render(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
