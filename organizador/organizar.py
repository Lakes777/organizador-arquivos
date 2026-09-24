"""Move os arquivos de uma pasta para subpastas por categoria."""

from dataclasses import dataclass
from pathlib import Path

from organizador.categorias import categoria_de


@dataclass
class Movimento:
    origem: Path
    destino: Path


def planejar(pasta: Path) -> list[Movimento]:
    """Lista o que seria movido, sem mexer em nada.

    Só olha os arquivos que estão direto na pasta: subpastas (inclusive as
    que o próprio organizador criou) e arquivos ocultos ficam onde estão.
    """
    movimentos = []
    for item in sorted(pasta.iterdir()):
        if not item.is_file() or item.name.startswith("."):
            continue
        destino = pasta / categoria_de(item) / item.name
        movimentos.append(Movimento(origem=item, destino=destino))
    return movimentos


def executar(movimentos: list[Movimento]) -> tuple[list[Movimento], list[Movimento]]:
    """Move os arquivos. Retorna (movidos, pulados).

    Se já existir um arquivo com o mesmo nome no destino, ele é pulado:
    no Linux, mover por cima de um arquivo apaga o antigo sem avisar.
    """
    movidos, pulados = [], []
    for movimento in movimentos:
        if movimento.destino.exists():
            pulados.append(movimento)
            continue
        movimento.destino.parent.mkdir(exist_ok=True)
        movimento.origem.rename(movimento.destino)
        movidos.append(movimento)
    return movidos, pulados
