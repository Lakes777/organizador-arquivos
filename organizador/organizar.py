"""Move os arquivos de uma pasta para subpastas por tipo ou por data."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from organizador.categorias import categoria_de

# Arquivos de sistema do Windows: mover o desktop.ini, por exemplo, faz a pasta
# perder o nome e o ícone no Explorer
IGNORADOS = {"desktop.ini", "thumbs.db"}


@dataclass
class Movimento:
    origem: Path
    destino: Path

    @property
    def subpasta(self) -> str:
        """Caminho da pasta de destino relativo à pasta organizada. Ex.: '2026/09'."""
        return self.destino.parent.relative_to(self.origem.parent).as_posix()


def subpasta_de(arquivo: Path, por: str) -> Path:
    """Decide a subpasta: pelo tipo ('Imagens') ou pela data ('2026/09').

    A data usada é a da última modificação, que num arquivo baixado costuma
    ser o dia do download.
    """
    if por == "data":
        modificado = datetime.fromtimestamp(arquivo.stat().st_mtime)
        return Path(f"{modificado:%Y}") / f"{modificado:%m}"
    return Path(categoria_de(arquivo))


def planejar(pasta: Path, por: str = "tipo") -> list[Movimento]:
    """Lista o que seria movido, sem mexer em nada.

    Só olha os arquivos que estão direto na pasta: subpastas (inclusive as
    que o próprio organizador criou), arquivos ocultos e arquivos de sistema
    ficam onde estão.
    """
    movimentos = []
    for item in sorted(pasta.iterdir()):
        if not item.is_file() or item.name.startswith("."):
            continue
        if item.name.lower() in IGNORADOS:
            continue
        destino = pasta / subpasta_de(item, por) / item.name
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
        movimento.destino.parent.mkdir(parents=True, exist_ok=True)
        movimento.origem.rename(movimento.destino)
        movidos.append(movimento)
    return movidos, pulados
