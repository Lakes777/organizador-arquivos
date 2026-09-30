"""Acha arquivos com o mesmo conteúdo e separa as cópias em Duplicados/.

Nada é apagado: as cópias só são movidas, para o usuário conferir antes.
"""

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from organizador.categorias import CATEGORIAS, OUTROS
from organizador.organizar import IGNORADOS, Movimento, nome_livre

PASTA_DUPLICADOS = "Duplicados"

# Subpastas da raiz em que a busca entra: as que o próprio organizador cria
# (Imagens/, Outros/... e 2026/ no --por data). Uma pasta qualquer, como um
# jogo ou projeto extraído de um .zip, pode ter arquivos repetidos de
# propósito (DLLs, LICENSE), e tirar um deles quebraria o programa.
PASTAS_DO_ORGANIZADOR = {nome.lower() for nome in [*CATEGORIAS, OUTROS]}
ANO = re.compile(r"^\d{4}$")

# Lê 1 MiB por vez: um vídeo de 4 GB não precisa caber inteiro na memória
TAMANHO_DO_PEDACO = 1024 * 1024

# Nomes que indicam cópia: 'foto (1).jpg' (Windows e nome_livre) ou
# 'foto - Copia.jpg' / 'foto - Cópia (2).jpg' (Windows em português)
SUFIXO_DE_COPIA = re.compile(r"( \(\d+\)| - (copia|cópia|copy)( \(\d+\))?)$", re.IGNORECASE)


@dataclass
class GrupoDeDuplicados:
    """Arquivos com o mesmo conteúdo: um fica, os outros são cópias."""

    tamanho: int
    fica: Path
    copias: list[Path]

    @property
    def espaco_liberado(self) -> int:
        return self.tamanho * len(self.copias)


def espaco_liberado(grupos: list[GrupoDeDuplicados]) -> int:
    """Quantos bytes sobram se todas as cópias forem apagadas."""
    return sum(grupo.espaco_liberado for grupo in grupos)


def tamanho_legivel(tamanho: int) -> str:
    """Ex.: 512 -> '512 bytes', 3565158 -> '3,4 MB' (vírgula, como no Brasil)."""
    if tamanho < 1024:
        return f"{tamanho} bytes"
    valor = float(tamanho)
    for unidade in ["KB", "MB", "GB", "TB"]:
        valor /= 1024
        if valor < 1024 or unidade == "TB":
            break
    return f"{valor:.1f} {unidade}".replace(".", ",")


def entra_na_busca(subpasta_da_raiz: Path) -> bool:
    """Imagens/, Outros/, 2026/... sim; Duplicados/ e pastas do usuário, não.

    Sem diferenciar maiúsculas: no Windows, 'duplicados' e 'Duplicados' são a
    mesma pasta.
    """
    nome = subpasta_da_raiz.name
    return nome.lower() in PASTAS_DO_ORGANIZADOR or ANO.match(nome) is not None


def listar_arquivos(
    pasta: Path, raiz: Path | None = None, ilegiveis: list[Path] | None = None
) -> list[Path]:
    """Os arquivos da raiz e das subpastas que o organizador cria.

    Pula ocultos, links simbólicos (o arquivo de verdade está em outro lugar),
    arquivos de sistema, pastas do usuário e a Duplicados/ (senão a segunda
    rodada acharia as cópias que a primeira já separou). Uma pasta que não
    abre é anotada em ilegiveis e pulada.
    """
    raiz = raiz or pasta
    arquivos = []
    try:
        itens = sorted(pasta.iterdir())
    except OSError:
        if ilegiveis is not None:
            ilegiveis.append(pasta)
        return []
    for item in itens:
        if item.name.startswith(".") or item.is_symlink():
            continue
        if item.is_dir():
            if pasta == raiz and not entra_na_busca(item):
                continue
            arquivos.extend(listar_arquivos(item, raiz, ilegiveis))
        elif item.is_file() and item.name.lower() not in IGNORADOS:
            arquivos.append(item)
    return arquivos


def hash_do_arquivo(arquivo: Path) -> str:
    """SHA-256 do conteúdo, lido em pedaços. Mesmo hash = mesmo conteúdo."""
    sha = hashlib.sha256()
    with arquivo.open("rb") as f:
        while pedaco := f.read(TAMANHO_DO_PEDACO):
            sha.update(pedaco)
    return sha.hexdigest()


def parece_copia(arquivo: Path) -> bool:
    """'foto (1).jpg' e 'foto - Cópia.jpg' parecem cópia; 'foto.jpg' não."""
    # normaliza o acento: 'ó' pode vir como um caractere só ou como 'o' + acento
    nome = unicodedata.normalize("NFC", arquivo.stem)
    return SUFIXO_DE_COPIA.search(nome) is not None


def escolher_quem_fica(iguais: list[Path]) -> Path:
    """O original provável: sem sufixo de cópia, depois o mais antigo, depois
    o primeiro em ordem alfabética (para o resultado não variar entre rodadas)."""
    return min(iguais, key=lambda a: (parece_copia(a), a.stat().st_mtime, a.as_posix()))


def encontrar_duplicados(pasta: Path, ilegiveis: list[Path] | None = None) -> list[GrupoDeDuplicados]:
    """Procura arquivos iguais pelo conteúdo, sem mexer em nada.

    Calcular o hash lê o arquivo inteiro, então primeiro agrupa pelo tamanho
    (que é de graça): arquivos de tamanhos diferentes não podem ser iguais.
    Um arquivo que não abre (aberto em outro programa no Windows, sem
    permissão) fica de fora em vez de parar a busca; se a lista ilegiveis
    for passada, ele é anotado nela.
    """
    def anotar(arquivo: Path) -> None:
        if ilegiveis is not None:
            ilegiveis.append(arquivo)

    por_tamanho: dict[int, list[Path]] = {}
    for arquivo in listar_arquivos(pasta, ilegiveis=ilegiveis):
        try:  # um download terminando pode renomear o arquivo durante a busca
            tamanho = arquivo.stat().st_size
        except OSError:
            anotar(arquivo)
            continue
        if tamanho > 0:  # vazios seriam todos "iguais" entre si
            por_tamanho.setdefault(tamanho, []).append(arquivo)

    grupos = []
    for tamanho, candidatos in sorted(por_tamanho.items()):
        if len(candidatos) < 2:
            continue
        por_hash: dict[str, list[Path]] = {}
        for arquivo in candidatos:
            try:
                hash_ = hash_do_arquivo(arquivo)
            except OSError:
                anotar(arquivo)
                continue
            por_hash.setdefault(hash_, []).append(arquivo)
        for iguais in por_hash.values():
            if len(iguais) < 2:
                continue
            try:
                fica = escolher_quem_fica(iguais)
            except OSError:  # algum deles sumiu depois do hash
                continue
            copias = [a for a in iguais if a != fica]
            grupos.append(GrupoDeDuplicados(tamanho=tamanho, fica=fica, copias=copias))
    return sorted(grupos, key=lambda g: g.fica.as_posix())


def planejar_duplicados(pasta: Path, grupos: list[GrupoDeDuplicados]) -> list[Movimento]:
    """Planeja mover cada cópia para Duplicados/<caminho original>.

    Guardar o caminho (ex.: Duplicados/Imagens/foto (1).jpg) mostra de onde
    a cópia veio, caso o usuário queira devolvê-la.
    """
    movimentos = []
    for grupo in grupos:
        for copia in grupo.copias:
            destino = nome_livre(pasta / PASTA_DUPLICADOS / copia.relative_to(pasta))
            movimentos.append(Movimento(origem=copia, destino=destino))
    return movimentos
