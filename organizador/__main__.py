"""Interface de linha de comando: python -m organizador <pasta>."""

import argparse
from pathlib import Path

from organizador.organizar import Movimento, executar, planejar


def pasta_existente(texto: str) -> Path:
    """Converte o texto digitado em Path, recusando o que não for uma pasta."""
    pasta = Path(texto).expanduser()
    if not pasta.is_dir():
        raise argparse.ArgumentTypeError(f"pasta não encontrada: {texto}")
    return pasta


def descrever(movimento: Movimento) -> str:
    """Ex.: 'foto.jpg  ->  Imagens/' ou 'print.png  ->  Imagens/print (1).png'."""
    destino = f"{movimento.subpasta}/"
    if movimento.renomeado:
        destino += movimento.destino.name
    return f"{movimento.origem.name}  ->  {destino}"


def contar_renomeados(movimentos: list[Movimento]) -> str:
    renomeados = sum(m.renomeado for m in movimentos)
    return f" ({renomeados} renomeado(s) por já existir um arquivo com o mesmo nome)" if renomeados else ""


def simular(movimentos: list[Movimento]) -> None:
    """Mostra o plano sem mover nada."""
    print("MODO SIMULAÇÃO: nenhum arquivo será movido.\n")
    for movimento in movimentos:
        print(descrever(movimento))
    print(f"\n{len(movimentos)} arquivo(s) seria(m) movido(s){contar_renomeados(movimentos)}.")
    print("Para organizar de verdade, rode o mesmo comando sem --simular.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="organizador",
        description="Separa os arquivos de uma pasta em subpastas por tipo ou por data.",
    )
    parser.add_argument("pasta", type=pasta_existente, help="ex.: ~/Downloads")
    parser.add_argument(
        "--por",
        choices=["tipo", "data"],
        default="tipo",
        help="tipo: Imagens/, Documentos/... | data: 2026/09/... (padrão: tipo)",
    )
    parser.add_argument(
        "-s",
        "--simular",
        action="store_true",
        help="só mostra o que seria feito, sem mover nada",
    )
    args = parser.parse_args()

    movimentos = planejar(args.pasta, args.por)
    if not movimentos:
        print("Nada para organizar.")
        return

    if args.simular:
        simular(movimentos)
        return

    movidos, pulados = executar(movimentos)
    for movimento in movidos:
        print(descrever(movimento))
    for movimento in pulados:
        print(f"PULADO: {movimento.origem.name} (surgiu um arquivo com o mesmo nome em {movimento.subpasta}/)")
    print(f"\n{len(movidos)} arquivo(s) movido(s){contar_renomeados(movidos)}.")
    if pulados:
        print(f"{len(pulados)} pulado(s). Rode de novo para organizá-los.")

if __name__ == "__main__":
    main()
