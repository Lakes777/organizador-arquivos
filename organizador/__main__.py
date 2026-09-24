"""Interface de linha de comando: python -m organizador <pasta>."""

import argparse
from pathlib import Path

from organizador.organizar import executar, planejar


def pasta_existente(texto: str) -> Path:
    """Converte o texto digitado em Path, recusando o que não for uma pasta."""
    pasta = Path(texto).expanduser()
    if not pasta.is_dir():
        raise argparse.ArgumentTypeError(f"pasta não encontrada: {texto}")
    return pasta


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="organizador",
        description="Separa os arquivos de uma pasta em subpastas por tipo.",
    )
    parser.add_argument("pasta", type=pasta_existente, help="ex.: ~/Downloads")
    args = parser.parse_args()

    movimentos = planejar(args.pasta)
    if not movimentos:
        print("Nada para organizar.")
        return

    movidos, pulados = executar(movimentos)
    for movimento in movidos:
        print(f"{movimento.origem.name}  ->  {movimento.destino.parent.name}/")
    for movimento in pulados:
        print(f"PULADO: {movimento.origem.name} (já existe em {movimento.destino.parent.name}/)")
    print(f"\n{len(movidos)} arquivo(s) movido(s), {len(pulados)} pulado(s).")


if __name__ == "__main__":
    main()
