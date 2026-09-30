import argparse
import sys
from pathlib import Path

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


def test_desfazer_devolve_os_duplicados_separados(tmp_path, monkeypatch, capsys):
    (tmp_path / "foto.jpg").write_bytes(b"a" * 2048)
    (tmp_path / "foto (1).jpg").write_bytes(b"a" * 2048)

    rodar(monkeypatch, str(tmp_path), "--duplicados")
    assert "Para desfazer" in capsys.readouterr().out
    assert not (tmp_path / "foto (1).jpg").exists()

    rodar(monkeypatch, str(tmp_path), "--desfazer")
    assert (tmp_path / "foto (1).jpg").exists()
    assert not (tmp_path / "Duplicados").exists()  # a pasta criada ficou vazia e saiu


def test_desfazer_recusa_duplicados_junto(tmp_path, monkeypatch, capsys):
    with pytest.raises(SystemExit):
        rodar(monkeypatch, str(tmp_path), "--desfazer", "--duplicados")

    assert "use --desfazer sozinho" in capsys.readouterr().err


def test_arquivo_em_uso_nao_impede_desfazer_os_outros(tmp_path, monkeypatch, capsys):
    (tmp_path / "a.jpg").touch()
    (tmp_path / "b.pdf").touch()
    rename_original = Path.rename

    def rename_falhando(self, destino):
        if self.name == "b.pdf":
            raise PermissionError(13, "Permission denied")
        return rename_original(self, destino)

    monkeypatch.setattr(Path, "rename", rename_falhando)
    rodar(monkeypatch, str(tmp_path))
    saida = capsys.readouterr().out
    assert "PULADO: b.pdf (não foi possível mover: Permission denied" in saida
    assert "Para desfazer" in saida

    monkeypatch.setattr(Path, "rename", rename_original)
    rodar(monkeypatch, str(tmp_path), "--desfazer")
    assert (tmp_path / "a.jpg").exists() and not (tmp_path / "Imagens").exists()


def test_desfazer_pula_arquivo_em_uso(tmp_path, monkeypatch, capsys):
    (tmp_path / "a.jpg").touch()
    (tmp_path / "b.pdf").touch()
    rodar(monkeypatch, str(tmp_path))
    rename_original = Path.rename

    def rename_falhando(self, destino):
        if self.name == "b.pdf":
            raise PermissionError(13, "Permission denied")
        return rename_original(self, destino)

    monkeypatch.setattr(Path, "rename", rename_falhando)
    capsys.readouterr()
    rodar(monkeypatch, str(tmp_path), "--desfazer")

    saida = capsys.readouterr().out
    assert "PULADO: Documentos/b.pdf (não foi possível mover" in saida
    assert (tmp_path / "a.jpg").exists() and (tmp_path / "Documentos" / "b.pdf").exists()
