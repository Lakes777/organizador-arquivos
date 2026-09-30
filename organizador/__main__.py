"""Interface de linha de comando: python -m organizador <pasta>."""

import argparse
from pathlib import Path

from organizador.duplicados import (
    PASTA_DUPLICADOS,
    GrupoDeDuplicados,
    encontrar_duplicados,
    espaco_liberado,
    planejar_duplicados,
    tamanho_legivel,
)
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


def mostrar_duplicados(pasta: Path, grupos: list[GrupoDeDuplicados]) -> None:
    """Mostra cada grupo de iguais sem mover nada."""
    print("MODO SIMULAÇÃO: nenhum arquivo será movido.\n")
    for grupo in grupos:
        print(f"{tamanho_legivel(grupo.tamanho)} cada")
        print(f"  fica:   {grupo.fica.relative_to(pasta).as_posix()}")
        for copia in grupo.copias:
            print(f"  cópia:  {copia.relative_to(pasta).as_posix()}")
        print()
    copias = sum(len(g.copias) for g in grupos)
    print(
        f"{len(grupos)} grupo(s), {copias} cópia(s). "
        f"Espaço que seria liberado: {tamanho_legivel(espaco_liberado(grupos))}."
    )
    print(f"Para mover as cópias para {PASTA_DUPLICADOS}/, rode o mesmo comando sem --simular.")


def separar_duplicados(pasta: Path, simular_apenas: bool) -> None:
    """--duplicados: acha arquivos iguais e move as cópias para Duplicados/."""
    grupos = encontrar_duplicados(pasta)
    if not grupos:
        print("Nenhum arquivo duplicado.")
        return
    if simular_apenas:
        mostrar_duplicados(pasta, grupos)
        return

    tamanhos = {copia: g.tamanho for g in grupos for copia in g.copias}
    movidos, pulados = executar(planejar_duplicados(pasta, grupos))
    for movimento in movidos:
        print(f"{movimento.origem.relative_to(pasta).as_posix()}  ->  {movimento.destino.relative_to(pasta).as_posix()}")
    for movimento in pulados:
        print(f"PULADO: {movimento.origem.relative_to(pasta).as_posix()} (surgiu um arquivo com o mesmo nome no destino)")
    liberado = sum(tamanhos[m.origem] for m in movidos)
    print(f"\n{len(movidos)} cópia(s) movida(s) para {PASTA_DUPLICADOS}/ ({tamanho_legivel(liberado)}).")
    if pulados:
        print(f"{len(pulados)} pulada(s). Rode de novo para separá-las.")
    print(f"Nada foi apagado: confira a pasta {PASTA_DUPLICADOS}/ e, se estiver tudo certo, apague-a para liberar o espaço.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="organizador",
        description="Separa os arquivos de uma pasta em subpastas por tipo ou por data.",
    )
    parser.add_argument("pasta", type=pasta_existente, help="ex.: ~/Downloads")
    parser.add_argument(
        "--por",
        choices=["tipo", "data"],
        default=None,  # None = não digitado, para recusar junto com --duplicados
        help="tipo: Imagens/, Documentos/... | data: 2026/09/... (padrão: tipo)",
    )
    parser.add_argument(
        "-s",
        "--simular",
        action="store_true",
        help="só mostra o que seria feito, sem mover nada",
    )
    parser.add_argument(
        "--duplicados",
        action="store_true",
        help="acha arquivos iguais (pelo conteúdo) e move as cópias para Duplicados/",
    )
    args = parser.parse_args()

    if args.duplicados:
        if args.por:
            parser.error("--duplicados não combina com --por")
        separar_duplicados(args.pasta, args.simular)
        return

    movimentos = planejar(args.pasta, args.por or "tipo")
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
