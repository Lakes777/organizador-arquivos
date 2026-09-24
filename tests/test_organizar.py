import os
from datetime import datetime
from pathlib import Path

from organizador.organizar import executar, nome_livre, planejar


def criar(caminho: Path, conteudo: str = "", data: datetime | None = None) -> Path:
    """Cria um arquivo de teste, opcionalmente com uma data de modificação."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(conteudo)
    if data:
        os.utime(caminho, (data.timestamp(), data.timestamp()))
    return caminho


def test_planejar_por_tipo(tmp_path):
    criar(tmp_path / "foto.jpg")
    criar(tmp_path / "boleto.pdf")

    destinos = {m.origem.name: m.subpasta for m in planejar(tmp_path)}

    assert destinos == {"foto.jpg": "Imagens", "boleto.pdf": "Documentos"}


def test_planejar_nao_mexe_em_nada(tmp_path):
    criar(tmp_path / "foto.jpg")

    planejar(tmp_path)

    assert [p.name for p in tmp_path.iterdir()] == ["foto.jpg"]


def test_planejar_por_data(tmp_path):
    criar(tmp_path / "antigo.pdf", data=datetime(2025, 12, 31, 12))
    criar(tmp_path / "novo.jpg", data=datetime(2026, 9, 1, 12))

    destinos = {m.origem.name: m.subpasta for m in planejar(tmp_path, por="data")}

    assert destinos == {"antigo.pdf": "2025/12", "novo.jpg": "2026/09"}


def test_ignora_subpastas_ocultos_e_arquivos_de_sistema(tmp_path):
    criar(tmp_path / "Imagens" / "velha.jpg")
    criar(tmp_path / ".bashrc")
    criar(tmp_path / "desktop.ini")
    criar(tmp_path / "Thumbs.db")

    assert planejar(tmp_path) == []


def test_nome_livre_quando_nao_existe(tmp_path):
    assert nome_livre(tmp_path / "print.png") == tmp_path / "print.png"


def test_nome_livre_pula_numeros_ocupados(tmp_path):
    criar(tmp_path / "print.png")
    criar(tmp_path / "print (1).png")

    assert nome_livre(tmp_path / "print.png") == tmp_path / "print (2).png"


def test_nome_livre_sem_extensao(tmp_path):
    criar(tmp_path / "LEIAME")

    assert nome_livre(tmp_path / "LEIAME") == tmp_path / "LEIAME (1)"


def test_executar_move_e_cria_pastas(tmp_path):
    criar(tmp_path / "foto.jpg", "conteúdo", data=datetime(2026, 9, 1, 12))

    movidos, pulados = executar(planejar(tmp_path, por="data"))

    assert len(movidos) == 1 and pulados == []
    assert not (tmp_path / "foto.jpg").exists()
    assert (tmp_path / "2026" / "09" / "foto.jpg").read_text() == "conteúdo"


def test_executar_nunca_sobrescreve_arquivo_existente(tmp_path):
    criar(tmp_path / "Imagens" / "print.png", "antiga")
    criar(tmp_path / "print.png", "nova")

    executar(planejar(tmp_path))

    assert (tmp_path / "Imagens" / "print.png").read_text() == "antiga"
    assert (tmp_path / "Imagens" / "print (1).png").read_text() == "nova"


def test_executar_pula_arquivo_que_surgiu_depois_do_plano(tmp_path):
    criar(tmp_path / "print.png", "nova")
    movimentos = planejar(tmp_path)
    criar(tmp_path / "Imagens" / "print.png", "chegou depois")  # ex.: um download terminando

    movidos, pulados = executar(movimentos)

    assert movidos == [] and len(pulados) == 1
    assert (tmp_path / "Imagens" / "print.png").read_text() == "chegou depois"
    assert (tmp_path / "print.png").read_text() == "nova"
