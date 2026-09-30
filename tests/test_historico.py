import json
from pathlib import Path

import pytest

from organizador import historico
from organizador.historico import HistoricoInvalido, carregar, desfazer, pastas_novas, registrar
from organizador.organizar import Movimento, executar, planejar


def criar(caminho: Path, conteudo: str = "") -> Path:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(conteudo)
    return caminho


def organizar(pasta: Path, por: str = "tipo"):
    """Faz o mesmo que a linha de comando: planeja, move e registra."""
    movimentos = planejar(pasta, por)
    novas = pastas_novas(pasta, movimentos)
    movidos, _ = executar(movimentos)
    registrar(pasta, movidos, novas)
    return movidos


def conteudo_da_pasta(pasta: Path) -> set[str]:
    return {p.relative_to(pasta).as_posix() for p in pasta.rglob("*")}


def test_organizar_e_desfazer_volta_tudo(tmp_path):
    criar(tmp_path / "foto.jpg", "foto")
    criar(tmp_path / "boleto.pdf", "boleto")
    antes = conteudo_da_pasta(tmp_path)

    organizar(tmp_path)
    resultado = desfazer(tmp_path)

    assert len(resultado.voltaram) == 2 and resultado.pulados == []
    assert conteudo_da_pasta(tmp_path) == antes  # pastas criadas e histórico sumiram
    assert (tmp_path / "foto.jpg").read_text() == "foto"


def test_desfazer_por_data_remove_pastas_aninhadas(tmp_path):
    criar(tmp_path / "foto.jpg")

    organizar(tmp_path, por="data")
    resultado = desfazer(tmp_path)

    assert len(resultado.pastas_removidas) == 2  # '2026/09' e depois '2026'
    assert conteudo_da_pasta(tmp_path) == {"foto.jpg"}


def test_nao_remove_pasta_que_ja_existia(tmp_path):
    criar(tmp_path / "Imagens" / "minha.jpg", "do usuário")
    criar(tmp_path / "foto.jpg")

    organizar(tmp_path)
    desfazer(tmp_path)

    assert (tmp_path / "Imagens" / "minha.jpg").read_text() == "do usuário"
    assert (tmp_path / "foto.jpg").exists()


def test_nao_remove_pasta_criada_se_o_usuario_pos_algo_nela(tmp_path):
    criar(tmp_path / "foto.jpg")

    organizar(tmp_path)
    criar(tmp_path / "Imagens" / "nova.jpg")
    resultado = desfazer(tmp_path)

    assert resultado.pastas_removidas == []
    assert (tmp_path / "Imagens" / "nova.jpg").exists()


def test_arquivo_renomeado_volta_com_o_nome_original(tmp_path):
    criar(tmp_path / "Imagens" / "print.png", "antiga")
    criar(tmp_path / "print.png", "nova")

    organizar(tmp_path)
    assert (tmp_path / "Imagens" / "print (1).png").exists()
    desfazer(tmp_path)

    assert (tmp_path / "print.png").read_text() == "nova"
    assert (tmp_path / "Imagens" / "print.png").read_text() == "antiga"
    assert not (tmp_path / "Imagens" / "print (1).png").exists()


def test_pula_arquivo_apagado_ou_movido_depois(tmp_path):
    criar(tmp_path / "foto.jpg")
    criar(tmp_path / "boleto.pdf")

    organizar(tmp_path)
    (tmp_path / "Imagens" / "foto.jpg").unlink()
    resultado = desfazer(tmp_path)

    assert [m.origem.name for m in resultado.voltaram] == ["boleto.pdf"]
    assert [(m.origem.name, "não está mais lá" in motivo) for m, motivo in resultado.pulados] == [
        ("foto.jpg", True)
    ]
    assert carregar(tmp_path) == []  # sai da pilha mesmo com pulados


def test_pula_quando_a_origem_esta_ocupada_sem_sobrescrever(tmp_path):
    criar(tmp_path / "foto.jpg", "organizada")

    organizar(tmp_path)
    criar(tmp_path / "foto.jpg", "baixada depois")
    resultado = desfazer(tmp_path)

    assert len(resultado.pulados) == 1 and resultado.voltaram == []
    assert (tmp_path / "foto.jpg").read_text() == "baixada depois"
    assert (tmp_path / "Imagens" / "foto.jpg").read_text() == "organizada"
    assert resultado.pastas_removidas == []  # a pasta não ficou vazia


def test_duas_rodadas_desfeitas_da_mais_recente_para_a_mais_antiga(tmp_path):
    criar(tmp_path / "foto.jpg")
    organizar(tmp_path)
    criar(tmp_path / "boleto.pdf")
    organizar(tmp_path)

    primeira = desfazer(tmp_path)
    assert [m.origem.name for m in primeira.voltaram] == ["boleto.pdf"]
    assert (tmp_path / "Imagens" / "foto.jpg").exists()

    segunda = desfazer(tmp_path)
    assert [m.origem.name for m in segunda.voltaram] == ["foto.jpg"]
    assert conteudo_da_pasta(tmp_path) == {"foto.jpg", "boleto.pdf"}
    assert desfazer(tmp_path) is None


def test_simular_nao_mexe_em_nada_nem_tira_da_pilha(tmp_path):
    criar(tmp_path / "foto.jpg")
    organizar(tmp_path)
    antes = conteudo_da_pasta(tmp_path)
    json_antes = (tmp_path / historico.ARQUIVO).read_text()

    resultado = desfazer(tmp_path, simular=True)

    assert len(resultado.voltaram) == 1
    assert conteudo_da_pasta(tmp_path) == antes
    assert (tmp_path / historico.ARQUIVO).read_text() == json_antes


def test_sem_historico_nao_ha_nada_para_desfazer(tmp_path):
    criar(tmp_path / "foto.jpg")

    assert desfazer(tmp_path) is None
    assert conteudo_da_pasta(tmp_path) == {"foto.jpg"}


@pytest.mark.parametrize(
    "conteudo",
    [
        "{isso não é json",
        json.dumps({"versao": 99, "rodadas": []}),
        json.dumps({"versao": 1, "rodadas": [{"data": "x"}]}),
        json.dumps(
            {
                "versao": 1,
                "rodadas": [
                    {"data": "x", "movimentos": [{"origem": "../fora.txt", "destino": "a.txt"}], "pastas_criadas": []}
                ],
            }
        ),
    ],
)
def test_historico_invalido_da_erro_sem_mexer(tmp_path, conteudo):
    criar(tmp_path / "Imagens" / "foto.jpg")
    criar(tmp_path / historico.ARQUIVO, conteudo)
    antes = conteudo_da_pasta(tmp_path)

    with pytest.raises(HistoricoInvalido):
        desfazer(tmp_path)
    with pytest.raises(HistoricoInvalido):
        registrar(tmp_path, [Movimento(tmp_path / "x.jpg", tmp_path / "Imagens" / "x.jpg")], [])

    assert conteudo_da_pasta(tmp_path) == antes
    assert (tmp_path / historico.ARQUIVO).read_text() == conteudo


def test_o_proprio_historico_nao_e_organizado(tmp_path):
    criar(tmp_path / "foto.jpg")
    organizar(tmp_path)

    assert (tmp_path / historico.ARQUIVO).exists()
    assert planejar(tmp_path) == []


def test_historico_guarda_caminhos_relativos(tmp_path):
    criar(tmp_path / "foto.jpg")
    organizar(tmp_path)

    dados = json.loads((tmp_path / historico.ARQUIVO).read_text())

    assert dados["rodadas"][0]["movimentos"] == [{"origem": "foto.jpg", "destino": "Imagens/foto.jpg"}]
    assert dados["rodadas"][0]["pastas_criadas"] == ["Imagens"]


def test_desfazer_funciona_depois_de_renomear_a_pasta(tmp_path):
    pasta = tmp_path / "Downloads"
    criar(pasta / "foto.jpg")
    organizar(pasta)

    nova = pasta.rename(tmp_path / "Baixados")
    desfazer(nova)

    assert conteudo_da_pasta(nova) == {"foto.jpg"}


def test_nao_registra_rodada_sem_movimentos(tmp_path):
    registrar(tmp_path, [], [])

    assert not (tmp_path / historico.ARQUIVO).exists()


def test_pilha_guarda_so_as_ultimas_rodadas(tmp_path, monkeypatch):
    monkeypatch.setattr(historico, "LIMITE_RODADAS", 3)
    for numero in range(5):
        criar(tmp_path / f"foto{numero}.jpg")
        organizar(tmp_path)

    rodadas = carregar(tmp_path)

    assert [r.movimentos[0].origem.name for r in rodadas] == ["foto2.jpg", "foto3.jpg", "foto4.jpg"]
