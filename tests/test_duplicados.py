import os
from datetime import datetime
from pathlib import Path

from organizador import duplicados
from organizador.duplicados import (
    GrupoDeDuplicados,
    TAMANHO_DO_PEDACO,
    encontrar_duplicados,
    espaco_liberado,
    hash_do_arquivo,
    parece_copia,
    planejar_duplicados,
    tamanho_legivel,
)
from organizador.organizar import executar


def criar(caminho: Path, conteudo: str | bytes = "x", data: datetime | None = None) -> Path:
    """Cria um arquivo de teste, opcionalmente com uma data de modificação."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(conteudo, bytes):
        caminho.write_bytes(conteudo)
    else:
        caminho.write_text(conteudo)
    if data:
        os.utime(caminho, (data.timestamp(), data.timestamp()))
    return caminho


def test_conteudo_igual_com_nomes_diferentes(tmp_path):
    criar(tmp_path / "boleto.pdf", "igual")
    criar(tmp_path / "boleto-setembro.pdf", "igual")
    criar(tmp_path / "outro.pdf", "diferente")

    grupos = encontrar_duplicados(tmp_path)

    assert len(grupos) == 1
    assert {grupos[0].fica.name, *[c.name for c in grupos[0].copias]} == {
        "boleto.pdf",
        "boleto-setembro.pdf",
    }


def test_mesmo_tamanho_e_conteudo_diferente_nao_e_duplicado(tmp_path):
    criar(tmp_path / "a.txt", "abc")
    criar(tmp_path / "b.txt", "abd")

    assert encontrar_duplicados(tmp_path) == []


def test_acha_duplicados_em_subpastas(tmp_path):
    criar(tmp_path / "foto.jpg", "pixels")
    criar(tmp_path / "Imagens" / "viagem" / "praia.jpg", "pixels")

    grupos = encontrar_duplicados(tmp_path)

    caminhos = {grupos[0].fica, *grupos[0].copias}
    assert caminhos == {tmp_path / "foto.jpg", tmp_path / "Imagens" / "viagem" / "praia.jpg"}


def test_fica_o_que_nao_tem_sufixo_de_copia(tmp_path):
    # a cópia é mais antiga e vem antes na ordem alfabética, mas o nome decide
    criar(tmp_path / "a (1).jpg", "igual", data=datetime(2020, 1, 1))
    criar(tmp_path / "b - Cópia.jpg", "igual", data=datetime(2020, 1, 1))
    criar(tmp_path / "foto.jpg", "igual", data=datetime(2026, 9, 1))

    grupo = encontrar_duplicados(tmp_path)[0]

    assert grupo.fica.name == "foto.jpg"
    assert sorted(c.name for c in grupo.copias) == ["a (1).jpg", "b - Cópia.jpg"]


def test_parece_copia():
    assert parece_copia(Path("print (1).png"))
    assert parece_copia(Path("print (12).png"))
    assert parece_copia(Path("trabalho - Copia.docx"))
    assert parece_copia(Path("trabalho - Cópia (2).docx"))
    assert not parece_copia(Path("print.png"))
    assert not parece_copia(Path("relatorio (final).pdf"))
    assert not parece_copia(Path("copia.txt"))


def test_empate_no_nome_fica_o_mais_antigo(tmp_path):
    criar(tmp_path / "a.txt", "igual", data=datetime(2026, 9, 1))
    criar(tmp_path / "b.txt", "igual", data=datetime(2025, 1, 1))

    assert encontrar_duplicados(tmp_path)[0].fica.name == "b.txt"


def test_empate_na_data_fica_o_primeiro_em_ordem_alfabetica(tmp_path):
    data = datetime(2026, 9, 1)
    criar(tmp_path / "b.txt", "igual", data=data)
    criar(tmp_path / "a.txt", "igual", data=data)

    assert encontrar_duplicados(tmp_path)[0].fica.name == "a.txt"


def test_ignora_vazios_ocultos_links_e_arquivos_de_sistema(tmp_path):
    criar(tmp_path / "vazio1.txt", "")
    criar(tmp_path / "vazio2.txt", "")
    criar(tmp_path / "nota.txt", "igual")
    criar(tmp_path / ".nota-oculta.txt", "igual")
    criar(tmp_path / ".oculta" / "nota.txt", "igual")
    criar(tmp_path / "desktop.ini", "igual")
    criar(tmp_path / "Imagens" / "Thumbs.db", "igual")
    (tmp_path / "atalho.txt").symlink_to(tmp_path / "nota.txt")

    assert encontrar_duplicados(tmp_path) == []


def test_espaco_liberado():
    grupos = [
        GrupoDeDuplicados(tamanho=100, fica=Path("a"), copias=[Path("b"), Path("c")]),
        GrupoDeDuplicados(tamanho=5, fica=Path("d"), copias=[Path("e")]),
    ]

    assert espaco_liberado(grupos) == 205


def test_tamanho_legivel():
    assert tamanho_legivel(512) == "512 bytes"
    assert tamanho_legivel(2048) == "2,0 KB"
    assert tamanho_legivel(int(3.4 * 1024 * 1024)) == "3,4 MB"
    assert tamanho_legivel(5 * 1024**3) == "5,0 GB"


def test_planejar_nao_mexe_em_nada(tmp_path):
    criar(tmp_path / "foto.jpg", "igual")
    criar(tmp_path / "foto (1).jpg", "igual")

    planejar_duplicados(tmp_path, encontrar_duplicados(tmp_path))

    assert sorted(p.name for p in tmp_path.iterdir()) == ["foto (1).jpg", "foto.jpg"]


def test_mover_preserva_o_caminho_relativo(tmp_path):
    criar(tmp_path / "foto.jpg", "igual", data=datetime(2020, 1, 1))
    criar(tmp_path / "Imagens" / "viagem" / "foto.jpg", "igual", data=datetime(2026, 1, 1))

    movidos, pulados = executar(planejar_duplicados(tmp_path, encontrar_duplicados(tmp_path)))

    assert len(movidos) == 1 and pulados == []
    assert (tmp_path / "foto.jpg").exists()
    assert not (tmp_path / "Imagens" / "viagem" / "foto.jpg").exists()
    assert (tmp_path / "Duplicados" / "Imagens" / "viagem" / "foto.jpg").read_text() == "igual"


def test_mover_nunca_sobrescreve(tmp_path):
    criar(tmp_path / "Duplicados" / "foto (1).jpg", "de uma rodada antiga")
    criar(tmp_path / "foto.jpg", "igual")
    criar(tmp_path / "foto (1).jpg", "igual")

    executar(planejar_duplicados(tmp_path, encontrar_duplicados(tmp_path)))

    assert (tmp_path / "Duplicados" / "foto (1).jpg").read_text() == "de uma rodada antiga"
    assert (tmp_path / "Duplicados" / "foto (1) (1).jpg").read_text() == "igual"


def test_segunda_rodada_ignora_a_pasta_duplicados(tmp_path):
    criar(tmp_path / "foto.jpg", "igual")
    criar(tmp_path / "foto (1).jpg", "igual")
    executar(planejar_duplicados(tmp_path, encontrar_duplicados(tmp_path)))

    assert encontrar_duplicados(tmp_path) == []


def test_so_a_pasta_duplicados_da_raiz_e_ignorada(tmp_path):
    criar(tmp_path / "foto.jpg", "igual")
    criar(tmp_path / "Projetos" / "Duplicados" / "foto.jpg", "igual")

    assert len(encontrar_duplicados(tmp_path)) == 1


def test_arquivos_maiores_que_um_pedaco(tmp_path):
    grande = b"a" * (TAMANHO_DO_PEDACO + 10)
    criar(tmp_path / "video.mp4", grande)
    criar(tmp_path / "video (1).mp4", grande)
    # mesmo tamanho, só o último byte (já no segundo pedaço) muda
    criar(tmp_path / "outro.mp4", grande[:-1] + b"b")

    grupos = encontrar_duplicados(tmp_path)

    assert len(grupos) == 1
    assert grupos[0].fica.name == "video.mp4"
    assert [c.name for c in grupos[0].copias] == ["video (1).mp4"]
    assert grupos[0].tamanho == TAMANHO_DO_PEDACO + 10


def test_hash_le_em_pedacos(tmp_path, monkeypatch):
    arquivo = criar(tmp_path / "video.mp4", b"a" * (2 * TAMANHO_DO_PEDACO + 1))
    tamanhos_lidos = []
    abrir_original = Path.open

    class ArquivoEspiado:
        """Embrulha o arquivo aberto e anota o tamanho de cada leitura."""

        def __init__(self, f):
            self.f = f

        def __enter__(self):
            return self

        def __exit__(self, *erro):
            self.f.close()

        def read(self, n=-1):
            tamanhos_lidos.append(n)
            return self.f.read(n)

    def abrir_espiando(self, *args, **kwargs):
        return ArquivoEspiado(abrir_original(self, *args, **kwargs))

    monkeypatch.setattr(Path, "open", abrir_espiando)
    hash_do_arquivo(arquivo)

    assert tamanhos_lidos and all(n == TAMANHO_DO_PEDACO for n in tamanhos_lidos)
    assert len(tamanhos_lidos) == 4  # 3 pedaços com dados + a leitura vazia do fim


def test_arquivo_que_nao_abre_fica_de_fora_sem_parar_a_busca(tmp_path, monkeypatch):
    (tmp_path / "a.txt").write_bytes(b"igual")
    (tmp_path / "a (1).txt").write_bytes(b"igual")
    (tmp_path / "travado.txt").write_bytes(b"outro")
    (tmp_path / "travado (1).txt").write_bytes(b"outro")
    original = duplicados.hash_do_arquivo

    def hash_falhando(arquivo):
        if arquivo.name == "travado.txt":  # como um arquivo aberto no Windows
            raise PermissionError("em uso")
        return original(arquivo)

    monkeypatch.setattr(duplicados, "hash_do_arquivo", hash_falhando)
    ilegiveis = []
    grupos = duplicados.encontrar_duplicados(tmp_path, ilegiveis)

    assert [g.fica.name for g in grupos] == ["a.txt"]
    assert ilegiveis == [tmp_path / "travado.txt"]
