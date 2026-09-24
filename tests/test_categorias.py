from pathlib import Path

import pytest

from organizador.categorias import CATEGORIAS, OUTROS, categoria_de


@pytest.mark.parametrize(
    "nome, esperado",
    [
        ("foto.jpg", "Imagens"),
        ("boleto.pdf", "Documentos"),
        ("setup.exe", "Instaladores"),
        ("Aluno.java", "Código"),
        ("modelo.drawio", "Diagramas"),
    ],
)
def test_categoria_pela_extensao(nome, esperado):
    assert categoria_de(Path(nome)) == esperado


def test_extensao_em_maiusculas():
    assert categoria_de(Path("ferias.JPG")) == "Imagens"


@pytest.mark.parametrize("nome", ["LEIAME", "arquivo.xyz", "Microsoft.Services.Store.winmd"])
def test_desconhecidos_vao_para_outros(nome):
    assert categoria_de(Path(nome)) == OUTROS


def test_nenhuma_extensao_em_duas_categorias():
    todas = [extensao for extensoes in CATEGORIAS.values() for extensao in extensoes]
    assert len(todas) == len(set(todas))
