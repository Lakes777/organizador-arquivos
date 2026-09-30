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


def test_duplicados_simular_nao_move_nada(tmp_path, monkeypatch, capsys):
    (tmp_path / "foto.jpg").write_bytes(b"a" * 2048)
    (tmp_path / "Imagens").mkdir()
    (tmp_path / "Imagens" / "foto (1).jpg").write_bytes(b"a" * 2048)

    rodar(monkeypatch, str(tmp_path), "--duplicados", "--simular")

    saida = capsys.readouterr().out
    assert "MODO SIMULAÇÃO" in saida
    assert "fica:   foto.jpg" in saida
    assert "cópia:  Imagens/foto (1).jpg" in saida
    assert "Espaço que seria liberado: 2,0 KB" in saida
    assert (tmp_path / "Imagens" / "foto (1).jpg").exists()
    assert not (tmp_path / "Duplicados").exists()


def test_duplicados_de_verdade(tmp_path, monkeypatch, capsys):
    (tmp_path / "foto.jpg").write_text("igual")
    (tmp_path / "foto (1).jpg").write_text("igual")

    rodar(monkeypatch, str(tmp_path), "--duplicados")

    saida = capsys.readouterr().out
    assert "foto (1).jpg  ->  Duplicados/foto (1).jpg" in saida
    assert "1 cópia(s) movida(s)" in saida
    assert "apague-a" in saida
    assert (tmp_path / "foto.jpg").exists()
    assert (tmp_path / "Duplicados" / "foto (1).jpg").read_text() == "igual"


def test_sem_duplicados(tmp_path, monkeypatch, capsys):
    (tmp_path / "a.txt").write_text("um")
    (tmp_path / "b.txt").write_text("outro")

    rodar(monkeypatch, str(tmp_path), "--duplicados")

    assert "Nenhum arquivo duplicado." in capsys.readouterr().out


def test_duplicados_recusa_por(tmp_path, monkeypatch, capsys):
    with pytest.raises(SystemExit):
        rodar(monkeypatch, str(tmp_path), "--duplicados", "--por", "data")

    assert "--duplicados não combina com --por" in capsys.readouterr().err
