"""Guarda o que cada organização moveu, para poder desfazer depois.

O histórico fica num arquivo oculto dentro da própria pasta organizada
(.organizador-historico.json). Como o nome começa com ".", o planejar()
nunca tenta organizá-lo. Os caminhos são guardados relativos à pasta: se o
usuário mover ou renomear a pasta inteira, o histórico continua valendo.
"""

import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path, PurePosixPath

from organizador.organizar import Movimento

ARQUIVO = ".organizador-historico.json"
VERSAO = 1
# Só as últimas rodadas: dá para desfazer várias vezes sem o arquivo crescer para sempre
LIMITE_RODADAS = 20


class HistoricoInvalido(Exception):
    """O arquivo de histórico existe, mas não dá para confiar no que tem nele."""


@dataclass
class Rodada:
    """Uma execução do organizador: o que foi movido e quais pastas ela criou."""

    data: str
    movimentos: list[Movimento]
    pastas_criadas: list[Path]


@dataclass
class Desfeito:
    """Resultado de desfazer uma rodada."""

    rodada: Rodada
    voltaram: list[Movimento] = field(default_factory=list)
    pulados: list[tuple[Movimento, str]] = field(default_factory=list)
    pastas_removidas: list[Path] = field(default_factory=list)


def caminho_do_historico(pasta: Path) -> Path:
    return pasta / ARQUIVO


def pastas_novas(pasta: Path, movimentos: list[Movimento]) -> list[Path]:
    """Pastas que o executar() vai precisar criar. Chame ANTES de executar.

    Depois de mover já não dá para saber se a pasta 'Imagens' existia antes
    ou foi criada agora, e desfazer só pode apagar as que ele mesmo criou.
    """
    novas = set()
    for movimento in movimentos:
        atual = movimento.destino.parent
        while atual != pasta and pasta in atual.parents and not atual.exists():
            novas.add(atual)
            atual = atual.parent
    return sorted(novas)


def _relativo(pasta: Path, caminho: Path) -> str:
    return caminho.relative_to(pasta).as_posix()


def _absoluto(pasta: Path, texto: object) -> Path:
    """Converte um caminho do JSON de volta, recusando o que sairia da pasta.

    Sem essa checagem, um histórico editado com '../' ou '/etc/...' faria o
    desfazer mover arquivos fora da pasta organizada.
    """
    if not isinstance(texto, str) or not texto:
        raise HistoricoInvalido("caminho vazio ou que não é texto")
    relativo = PurePosixPath(texto)
    if relativo.is_absolute() or ".." in relativo.parts:
        raise HistoricoInvalido(f"caminho fora da pasta: {texto}")
    return pasta.joinpath(*relativo.parts)


def _ler_bruto(pasta: Path) -> dict:
    """Lê e confere o JSON. Sem arquivo, devolve um histórico vazio."""
    arquivo = caminho_do_historico(pasta)
    if not arquivo.exists():
        return {"versao": VERSAO, "rodadas": []}
    try:
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as erro:
        raise HistoricoInvalido(f"não foi possível ler {arquivo}: {erro}") from erro
    if not isinstance(dados, dict) or dados.get("versao") != VERSAO:
        raise HistoricoInvalido(f"{arquivo} tem um formato ou versão desconhecida")
    if not isinstance(dados.get("rodadas"), list):
        raise HistoricoInvalido(f"{arquivo} não tem a lista de rodadas")
    return dados


def _rodada_do_json(pasta: Path, bruta: object) -> Rodada:
    try:
        movimentos = [
            Movimento(origem=_absoluto(pasta, m["origem"]), destino=_absoluto(pasta, m["destino"]))
            for m in bruta["movimentos"]
        ]
        pastas = [_absoluto(pasta, p) for p in bruta["pastas_criadas"]]
        return Rodada(data=str(bruta["data"]), movimentos=movimentos, pastas_criadas=pastas)
    except (KeyError, TypeError) as erro:
        raise HistoricoInvalido(f"rodada com formato inesperado no histórico: {erro}") from erro


def carregar(pasta: Path) -> list[Rodada]:
    """Todas as rodadas guardadas, da mais antiga para a mais recente.

    Confere o arquivo inteiro de uma vez, assim um erro aparece antes de
    qualquer arquivo ser movido.
    """
    return [_rodada_do_json(pasta, bruta) for bruta in _ler_bruto(pasta)["rodadas"]]


def _gravar(pasta: Path, rodadas: list[dict]) -> None:
    """Grava num temporário e troca de uma vez com os.replace.

    Se o programa cair no meio da escrita, o histórico antigo continua
    inteiro, em vez de ficar um JSON pela metade.
    """
    arquivo = caminho_do_historico(pasta)
    if not rodadas:
        arquivo.unlink(missing_ok=True)  # nada mais para desfazer: não deixa lixo na pasta
        return
    conteudo = json.dumps({"versao": VERSAO, "rodadas": rodadas}, ensure_ascii=False, indent=2)
    # O temporário começa com "." para o planejar() também ignorá-lo
    descritor, temporario = tempfile.mkstemp(dir=pasta, prefix=".organizador-historico-", suffix=".tmp")
    try:
        with os.fdopen(descritor, "w", encoding="utf-8") as saida:
            saida.write(conteudo)
        os.replace(temporario, arquivo)
    except BaseException:
        Path(temporario).unlink(missing_ok=True)
        raise


def registrar(pasta: Path, movidos: list[Movimento], pastas_criadas: list[Path]) -> None:
    """Empilha uma rodada no histórico. Serve para qualquer operação que mova
    arquivos com Movimento/executar (organizar, duplicados...).

    `pastas_criadas` vem do pastas_novas(), chamado antes de executar.
    """
    if not movidos:
        return
    dados = _ler_bruto(pasta)
    carregar(pasta)  # confere as rodadas antigas antes de reescrever o arquivo
    # Uma pasta prevista pode não ter sido criada se todos os arquivos dela foram pulados
    criadas = [p for p in pastas_criadas if p.is_dir()]
    dados["rodadas"].append(
        {
            "data": datetime.now().isoformat(timespec="seconds"),
            "movimentos": [
                {"origem": _relativo(pasta, m.origem), "destino": _relativo(pasta, m.destino)}
                for m in movidos
            ],
            "pastas_criadas": [_relativo(pasta, p) for p in criadas],
        }
    )
    _gravar(pasta, dados["rodadas"][-LIMITE_RODADAS:])


def motivo_para_pular(movimento: Movimento) -> str | None:
    """Por que um arquivo não pode voltar ao lugar (None se pode)."""
    if not movimento.destino.is_file():
        return "não está mais lá: foi apagado, movido ou renomeado"
    if movimento.origem.exists() or movimento.origem.is_symlink():
        return f"já existe outro arquivo chamado {movimento.origem.name} no lugar original"
    return None


def desfazer(pasta: Path, simular: bool = False) -> Desfeito | None:
    """Desfaz a rodada mais recente. Retorna None se não há nada para desfazer.

    Nunca apaga nem sobrescreve arquivo: só move de volta e remove as pastas
    que a própria rodada criou, se ficaram vazias. Na simulação, só diz o que
    aconteceria. A rodada sai do histórico mesmo com arquivos pulados, senão
    um único arquivo apagado travaria o desfazer das rodadas anteriores.
    """
    rodadas = carregar(pasta)
    if not rodadas:
        return None
    resultado = Desfeito(rodada=rodadas[-1])

    # Ordem inversa: o último a ser movido é o primeiro a voltar
    for movimento in reversed(resultado.rodada.movimentos):
        motivo = motivo_para_pular(movimento)
        if motivo:
            resultado.pulados.append((movimento, motivo))
            continue
        if not simular:
            movimento.origem.parent.mkdir(parents=True, exist_ok=True)
            movimento.destino.rename(movimento.origem)
        resultado.voltaram.append(movimento)

    if simular:
        return resultado

    # Das mais fundas para as mais rasas: '2026/09' antes de '2026'
    for criada in sorted(resultado.rodada.pastas_criadas, key=lambda p: len(p.parts), reverse=True):
        try:
            criada.rmdir()  # rmdir só funciona em pasta vazia: o que o usuário pôs lá fica
        except OSError:
            continue
        resultado.pastas_removidas.append(criada)

    _gravar(pasta, _ler_bruto(pasta)["rodadas"][:-1])
    return resultado
