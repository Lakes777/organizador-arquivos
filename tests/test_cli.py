import argparse
import sys

import pytest

from organizador.__main__ import main, pasta_existente


def rodar(monkeypatch, *argumentos):
    """Simula o usuário digitando `python -m organizador <argumentos>`."""
    monkeypatch.setattr(sys, "argv", ["organizador", *argumentos])
    main()


def test_pasta_existente_recusa_caminho_invalido(tmp_path):
    with pytest.raises(argparse.ArgumentTypeError):
        pasta_existente(str(tmp_path / "nao-existe"))


def test_simular_nao_move_nada(tmp_path, monkeypatch, capsys):
    (tmp_path / "foto.jpg").touch()

    rodar(monkeypatch, str(tmp_path), "--simular")

    saida = capsys.readouterr().out
    assert "MODO SIMULAÇÃO" in saida
    assert "foto.jpg  ->  Imagens/" in saida
    assert (tmp_path / "foto.jpg").exists()
    assert not (tmp_path / "Imagens").exists()


def test_organizar_de_verdade(tmp_path, monkeypatch, capsys):
    (tmp_path / "foto.jpg").touch()
    (tmp_path / "Imagens").mkdir()
    (tmp_path / "Imagens" / "foto.jpg").touch()

    rodar(monkeypatch, str(tmp_path))

    saida = capsys.readouterr().out
    assert "foto.jpg  ->  Imagens/foto (1).jpg" in saida
    assert "1 renomeado(s)" in saida
    assert (tmp_path / "Imagens" / "foto (1).jpg").exists()


def test_pasta_vazia(tmp_path, monkeypatch, capsys):
    rodar(monkeypatch, str(tmp_path))

    assert "Nada para organizar" in capsys.readouterr().out


def test_opcao_por_invalida(tmp_path, monkeypatch):
    with pytest.raises(SystemExit):  # o argparse encerra o programa com erro
        rodar(monkeypatch, str(tmp_path), "--por", "mes")


def test_organizar_mostra_como_desfazer(tmp_path, monkeypatch, capsys):
    (tmp_path / "foto.jpg").touch()

    rodar(monkeypatch, str(tmp_path))

    assert f"Para desfazer: python -m organizador {tmp_path} --desfazer" in capsys.readouterr().out
    assert (tmp_path / ".organizador-historico.json").exists()


def test_simular_organizacao_nao_grava_historico(tmp_path, monkeypatch, capsys):
    (tmp_path / "foto.jpg").touch()

    rodar(monkeypatch, str(tmp_path), "--simular")

    assert "Para desfazer" not in capsys.readouterr().out
    assert not (tmp_path / ".organizador-historico.json").exists()


def test_desfazer_simulando_so_mostra(tmp_path, monkeypatch, capsys):
    (tmp_path / "foto.jpg").touch()
    rodar(monkeypatch, str(tmp_path))
    capsys.readouterr()

    rodar(monkeypatch, str(tmp_path), "--desfazer", "--simular")

    saida = capsys.readouterr().out
    assert "MODO SIMULAÇÃO" in saida
    assert "Imagens/foto.jpg  ->  foto.jpg" in saida
    assert (tmp_path / "Imagens" / "foto.jpg").exists()


def test_desfazer_de_verdade(tmp_path, monkeypatch, capsys):
    (tmp_path / "foto.jpg").touch()
    rodar(monkeypatch, str(tmp_path))
    capsys.readouterr()

    rodar(monkeypatch, str(tmp_path), "--desfazer")

    saida = capsys.readouterr().out
    assert "Imagens/foto.jpg  ->  foto.jpg" in saida
    assert "Pasta(s) vazia(s) removida(s): Imagens/" in saida
    assert sorted(p.name for p in tmp_path.iterdir()) == ["foto.jpg"]


def test_desfazer_avisa_pulados(tmp_path, monkeypatch, capsys):
    (tmp_path / "foto.jpg").touch()
    rodar(monkeypatch, str(tmp_path))
    (tmp_path / "Imagens" / "foto.jpg").unlink()
    capsys.readouterr()

    rodar(monkeypatch, str(tmp_path), "--desfazer")

    saida = capsys.readouterr().out
    assert "PULADO: Imagens/foto.jpg" in saida
    assert "saiu do histórico mesmo assim" in saida


def test_desfazer_sem_historico(tmp_path, monkeypatch, capsys):
    rodar(monkeypatch, str(tmp_path), "--desfazer")

    assert "Nada para desfazer nesta pasta." in capsys.readouterr().out


def test_desfazer_com_por_da_erro(tmp_path, monkeypatch):
    with pytest.raises(SystemExit):
        rodar(monkeypatch, str(tmp_path), "--desfazer", "--por", "data")


def test_historico_corrompido_impede_organizar(tmp_path, monkeypatch):
    (tmp_path / "foto.jpg").touch()
    (tmp_path / ".organizador-historico.json").write_text("{quebrado")

    with pytest.raises(SystemExit) as erro:
        rodar(monkeypatch, str(tmp_path))

    assert "Erro no histórico" in str(erro.value.code)
    assert (tmp_path / "foto.jpg").exists()
    assert not (tmp_path / "Imagens").exists()
