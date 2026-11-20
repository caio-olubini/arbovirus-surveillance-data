"""O contador de estilo: o que ele conta, e o que ele se recusa a contar.

O linter é a metade objetiva da regra de clareza, e o defeito caro dele é o
alarme falso: um limite que dispara em prosa boa ensina quem lê a ignorar a
saída, e aí o script fica pior que a ausência dele. Por isso metade destes
testes defende o SILÊNCIO do script em texto limpo, e a outra metade defende
que ele fale quando deve.

O que mais importa aqui é a troca de 2026-11-10: o gate deixou de ser tamanho
de frase e passou a ser aninhamento. Os testes de `oracoes` são a especificação
dessa troca, incluindo as duas palavras que o contador DELIBERADAMENTE ignora.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

_spec = importlib.util.spec_from_file_location(
    "checar_estilo", REPO / "scripts" / "checar_estilo_relatorio.py"
)
estilo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(estilo)


# --- helpers -----------------------------------------------------------------
def escrever(tmp_path: Path, texto: str) -> Path:
    alvo = tmp_path / "relatorio.md"
    alvo.write_text(texto, encoding="utf-8")
    return alvo


def rodar(caminho: Path, *termos: str) -> tuple[int, dict]:
    return rodar_com(caminho, [f"--termo={t}" for t in (termos or ("pooling",))])


def rodar_com(caminho: Path, extra: list[str]) -> tuple[int, dict]:
    """Roda o script em modo --json e devolve (código de saída, relatório)."""
    import contextlib
    import io

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        codigo = estilo.main([str(caminho), "--json", *extra])
    return codigo, json.loads(buf.getvalue())


def paragrafo(texto: str) -> str:
    """Um parágrafo de prosa com palavras suficientes para não ser rótulo."""
    return texto + "\n\n"


# --- o contador de orações ---------------------------------------------------
@pytest.mark.parametrize("frase,esperado", [
    ("O modelo foi treinado em doze mil pares.", 1),
    ("O modelo foi treinado, mas o resultado não apareceu.", 2),
    ("O modelo foi treinado, mas o resultado não apareceu, porque a série é curta.", 3),
    ("O estudo que compara os dois mostra que o ganho some quando a janela encolhe.", 4),
])
def test_oracoes_conta_a_subordinacao(frase: str, esperado: int) -> None:
    assert estilo.oracoes_da_frase(frase) == esperado


def test_a_conjuncao_e_nao_conta_como_oracao() -> None:
    """"e" NÃO soma oração, e isso é decisão, não esquecimento.

    O contador mede SUBORDINAÇÃO, porque subordinação é o que aninha: "que A,
    enquanto B, o que C, porque D" obriga o leitor a segurar quatro coisas na
    cabeça antes de chegar ao ponto. Coordenação com "e" não aninha — "A, e B, e
    C" se lê em fila. E "e" é conjunção de lista na maior parte das ocorrências
    ("doença e local"), então contá-lo inflaria toda frase do relatório. É a
    mesma decisão que deixa "se" e "como" de fora.
    """
    assert estilo.oracoes_da_frase(
        "O modelo foi treinado, e o resultado apareceu, e ninguém replicou.") == 1


def test_comparativo_nao_vira_oracao() -> None:
    """"mais rápido do que o baseline" tem uma oração, não duas.

    Sem o desconto, todo comparativo somaria uma oração e o contador inflaria
    justamente a prosa que compara números — que é o que o relatório mais faz.
    """
    assert estilo.oracoes_da_frase(
        "O modelo é mais rápido do que o baseline em quatro vezes.") == 1


@pytest.mark.parametrize("frase", [
    "O modelo se comporta como o baseline.",
    "O encoder funciona como extrator de características fixas.",
])
def test_se_e_como_nao_contam(frase: str) -> None:
    """As duas palavras que o contador ignora de propósito.

    "se" é pronome reflexivo antes de ser conjunção, e "como" é preposição antes
    de ser conectivo. Contá-los inflaria toda frase do relatório. O teste existe
    para que remover a exceção seja uma decisão, não um descuido.
    """
    assert estilo.oracoes_da_frase(frase) == 1


def test_frase_com_muitas_oracoes_vira_erro(tmp_path: Path) -> None:
    """Seis orações numa frase é o teto: o script reprova, e diz quantas são."""
    caminho = escrever(tmp_path, paragrafo(
        "A leitura conjunta é que doença e local são os campos maduros, enquanto "
        "data continua raro, o que muda o desenho de qualquer modelo, porque a "
        "série fica curta, embora o efeito apareça quando a janela cresce."))

    codigo, rel = rodar(caminho)

    assert codigo == 1
    assert rel["n_erros"] == 1
    assert rel["oracoes_empilhadas"][0]["oracoes"] >= estilo.LIMITE_ORACOES


def test_frase_longa_com_poucas_oracoes_passa(tmp_path: Path) -> None:
    """Tamanho não é gate: cinquenta e cinco palavras com uma oração é prosa.

    É a asserção que justifica a troca do contador. Se este teste falhar, o
    linter voltou a medir a coisa errada.
    """
    longa = ("O levantamento cobre vinte e três artigos publicados entre dois mil e "
             "dezenove e dois mil e vinte e cinco, todos com texto completo "
             "recuperado, todos em português ou inglês, todos com a série-alvo "
             "declarada, todos com a janela de avaliação descrita em semanas "
             "epidemiológicas e todos com o desfecho primário medido sobre a mesma "
             "base de comparação.")
    assert len(estilo.palavras(longa)) > 45

    codigo, rel = rodar(escrever(tmp_path, paragrafo(longa)))

    assert codigo == 0
    assert rel["oracoes_empilhadas"] == []
    assert rel["medidas"]["palavras_por_frase_max"] > 45


# --- as três medidas de vício ------------------------------------------------
def test_adjetivo_inflado_isolado_nao_reprova(tmp_path: Path) -> None:
    """Um "relevante" em quinhentas palavras é AVISO, não ERRO.

    O gate é de DENSIDADE, e o teste existe para fixar isso: se uma ocorrência
    bastasse, o script reprovaria todo relatório que existe, e o número deixaria
    de significar qualquer coisa. AVISO é o script dizendo "olhe isto".
    """
    texto = " ".join(f"O estudo numero {i} mede a serie com cuidado." for i in range(80))
    codigo, rel = rodar(escrever(tmp_path, paragrafo(
        texto + " O achado relevante aparece no fim.")))

    assert codigo == 0
    assert rel["adjetivos_inflados"] == []
    assert rel["medidas"]["adjetivo_total"] == 1
    assert rel["adjetivos_inflados_aviso"]


def test_adjetivo_inflado_em_excesso_vira_erro(tmp_path: Path) -> None:
    texto = " ".join("O resultado robusto e abrangente e crucial e fundamental." for _ in range(20))
    codigo, rel = rodar(escrever(tmp_path, paragrafo(texto)))

    assert codigo == 1
    assert rel["adjetivos_inflados"]


def test_muleta_e_hedge_sao_contados(tmp_path: Path) -> None:
    """"vale ressaltar" e "pode potencialmente" saem nomeados, com o trecho."""
    texto = " ".join("Vale ressaltar que o modelo pode potencialmente sugerir isto." for _ in range(20))
    codigo, rel = rodar(escrever(tmp_path, paragrafo(texto)))

    assert codigo == 1
    assert {m["termo"] for m in rel["muletas"]} == {"vale ressaltar"}
    assert {h["termo"] for h in rel["hedges"]} == {"pode potencialmente"}


def test_hedge_ausente_nao_produz_categoria_vazia(tmp_path: Path) -> None:
    codigo, rel = rodar(escrever(tmp_path, paragrafo(
        " ".join("O modelo mede a serie por semana." for _ in range(40)))))

    assert codigo == 0
    assert rel["hedges"] == [] and rel["hedges_aviso"] == []
    assert rel["medidas"]["hedge_total"] == 0


# --- o que NÃO é gate --------------------------------------------------------
def test_passiva_e_travessao_saem_como_medida_e_nao_reprovam(tmp_path: Path) -> None:
    """Os dois são legítimos em prosa de método, então são medidos e não julgados.

    Sem uma referência de voz medida para comparar, limite aqui seria chute com
    cara de critério. O número existe para o revisor olhar; a reprovação não.
    """
    texto = " ".join("O modelo foi treinado — e o sinal só aparece em julho." for _ in range(20))
    codigo, rel = rodar(escrever(tmp_path, paragrafo(texto)))

    assert codigo == 0
    assert rel["n_erros"] == 0
    assert rel["medidas"]["passiva_por_mil"] > 0
    assert rel["medidas"]["travessao_por_mil"] > 0


def test_desvio_de_ritmo_e_reportado(tmp_path: Path) -> None:
    """Ritmo uniforme é o vício que só aparece no agregado, nunca na frase."""
    uniforme = paragrafo(" ".join("A serie sobe devagar no inverno." for _ in range(12)))
    _, rel = rodar(escrever(tmp_path, uniforme))

    assert rel["medidas"]["palavras_por_frase_desvio"] == 0.0
    assert rel["medidas"]["palavras_por_frase_mediana"] == 6.0


# --- a checagem de glosa continua valendo ------------------------------------
def test_termo_apresentado_antes_de_usar_passa(tmp_path: Path) -> None:
    codigo, rel = rodar(escrever(tmp_path, paragrafo(
        "Os vetores ficam todos parecidos entre si (pooling). Depois disso o "
        "pooling pode ser usado à vontade no resto do texto.")), "pooling")

    assert codigo == 0
    assert rel["termos_sem_glosa"] == []


def test_termo_solto_antes_da_glosa_e_erro(tmp_path: Path) -> None:
    codigo, rel = rodar(escrever(tmp_path, paragrafo(
        "O pooling resolve isso. Mais adiante o texto explica (pooling).")), "pooling")

    assert codigo == 1
    assert rel["termos_sem_glosa"][0]["termo"] == "pooling"


def test_citacao_nao_conta_como_glosa(tmp_path: Path) -> None:
    """(Reimers, 2019) não apresenta pooling, mesmo estando entre parênteses."""
    codigo, rel = rodar(escrever(tmp_path, paragrafo(
        "O pooling aparece em Reimers (Reimers, 2019) e resolve o problema todo.")),
        "pooling")

    assert codigo == 1
    assert rel["termos_sem_glosa"]


def test_titulo_nao_e_conferido(tmp_path: Path) -> None:
    """Título é rótulo: cobrar parêntese ali daria alarme falso em todo relatório."""
    codigo, rel = rodar(escrever(tmp_path,
        "## Eixo 1 — pooling e geometria\n\n" + paragrafo(
            "Os vetores ficam parecidos (pooling) e isso basta.")), "pooling")

    assert codigo == 0
    assert rel["termos_sem_glosa"] == []


def test_paragrafo_curto_nao_entra_na_densidade(tmp_path: Path) -> None:
    """Abaixo do piso o parágrafo é rótulo, e densidade de rótulo não diz nada.

    Os três termos vão entre parênteses para a checagem de glosa passar: o que
    este teste isola é a densidade, e um ERRO de glosa aqui esconderia o
    resultado que se quer medir.
    """
    codigo, rel = rodar(escrever(tmp_path, paragrafo(
        "Os vetores (pooling), (embedding) e (encoder) aparecem aqui.")),
        "pooling", "embedding", "encoder")

    assert codigo == 0
    assert rel["paragrafos_densos"] == []
    assert rel["paragrafos_densos_aviso"] == []


# --- a amostra de voz --------------------------------------------------------
def test_amostra_de_voz_passa_no_proprio_linter() -> None:
    """A régua tem que passar na própria régua.

    Se este teste quebra, alguém acrescentou prosa ao arquivo de referência fora
    do bloco de código — e essa prosa passou a fazer parte da amostra. Foi o que
    aconteceu na primeira versão do arquivo: a seção que explicava os vícios
    citava "vale ressaltar" como exemplo, o linter contou a citação como
    ocorrência, e a referência saiu reprovada por descrever o que evita.
    """
    caminho = REPO / "notes" / "voz-de-referencia.md"
    if not caminho.is_file():
        pytest.skip("o repositório não tem arquivo de voz de referência")

    codigo, rel = rodar(caminho)

    assert codigo == 0, rel["muletas"] + rel["adjetivos_inflados"] + rel["oracoes_empilhadas"]
    assert rel["n_erros"] == 0
    assert rel["n_avisos"] == 0


def test_referencia_de_voz_e_medida_e_comparada(tmp_path: Path) -> None:
    """A referência entra no relatório como comparação, e não como gate.

    O valor dela está em dar o número ao lado do medido. Se ela virasse gate,
    os quatro relatórios do repositório reprovariam por escreverem frases mais
    curtas e menos passivas que a referência — que é o inverso do problema.
    """
    ref = REPO / "notes" / "voz-de-referencia.md"
    if not ref.is_file():
        pytest.skip("o repositório não tem arquivo de voz de referência")

    caminho = escrever(tmp_path, paragrafo(
        " ".join("O modelo mede a serie por semana." for _ in range(40))))
    codigo, rel = rodar(caminho)

    assert codigo == 0
    assert rel["referencia"]["palavras_por_frase_max"] > 45
    assert rel["referencia"]["palavras_por_frase_mediana"] > 0


def test_sem_arquivo_de_referencia_o_linter_ainda_roda(tmp_path: Path) -> None:
    """Repositório sem a amostra continua tendo linter, só não tem comparação."""
    caminho = escrever(tmp_path, paragrafo(" ".join("O modelo mede a serie." for _ in range(40))))
    codigo, rel = rodar_com(caminho, ["--termo=pooling", "--referencia="])

    assert codigo == 0
    assert rel["referencia"] is None


# --- leitura: o que não é prosa ----------------------------------------------
def test_bloco_de_codigo_nao_e_medido(tmp_path: Path) -> None:
    """O miolo de um bloco de código não é prosa e não entra na conta.

    Antes, só as LINHAS DE CERCA eram puladas e o miolo era medido como
    parágrafo. O efeito prático era um relatório que mostrasse um trecho de
    código ter o código contado como texto — e um arquivo de referência que
    citasse os vícios para explicá-los ser reprovado por citá-los.
    """
    texto = ("# Titulo\n\n" + paragrafo(
        "O modelo mede a serie com cuidado ao longo de duzentas semanas.") +
        "```\nVale ressaltar que o resultado robusto e crucial aparece aqui.\n```\n")
    codigo, rel = rodar(escrever(tmp_path, texto))

    assert codigo == 0
    assert rel["muletas"] == [] and rel["muletas_aviso"] == []
    assert rel["adjetivos_inflados"] == [] and rel["adjetivos_inflados_aviso"] == []
    assert rel["medidas"]["muleta_total"] == 0


# --- contrato ----------------------------------------------------------------
def test_relatorio_limpo_sai_sem_erro_nem_aviso(tmp_path: Path) -> None:
    """O caso que protege o script de virar ruído."""
    limpo = paragrafo(
        "Os vetores ficam todos parecidos entre si (pooling). O estudo mede o "
        "ganho em doze por cento sobre um corpus de notícias. A série cobre "
        "duzentas semanas. Nada aqui empilha oração demais.")

    codigo, rel = rodar(escrever(tmp_path, limpo), "pooling")

    assert codigo == 0
    assert rel["n_erros"] == 0
    assert rel["n_avisos"] == 0


def test_sem_termo_sai_com_2(tmp_path: Path, capsys) -> None:
    caminho = escrever(tmp_path, paragrafo("Qualquer coisa com palavras suficientes aqui."))
    assert estilo.main([str(caminho)]) == 2
    assert "--termo" in capsys.readouterr().err


def test_arquivo_inexistente_sai_com_2(tmp_path: Path, capsys) -> None:
    assert estilo.main([str(tmp_path / "nao_existe.md"), "--termo=x"]) == 2
    assert "não existe" in capsys.readouterr().err


def test_texto_vazio_nao_divide_por_zero(tmp_path: Path) -> None:
    """Relatório sem corpo não pode derrubar o script: sai 0 e medidas zeradas."""
    codigo, rel = rodar(escrever(tmp_path, "# Só um título\n"))

    assert codigo == 0
    assert rel["palavras"] == 0
    assert rel["medidas"]["passiva_por_mil"] == 0.0
