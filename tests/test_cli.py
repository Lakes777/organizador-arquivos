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
