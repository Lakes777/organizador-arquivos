"""Interface de linha de comando: python -m organizador <pasta>."""

import argparse
import shlex
import sys
from pathlib import Path

from organizador import historico
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


def mover_e_registrar(
    pasta: Path, movimentos: list[Movimento]
) -> tuple[list[Movimento], list[Movimento], str | None]:
    """Move os arquivos e grava a rodada no histórico, para poder desfazer.

    Retorna (movidos, pulados, aviso); o aviso diz se o histórico não pôde ser gravado.
    """
    pastas_criadas = historico.pastas_novas(pasta, movimentos)
    movidos, pulados = executar(movimentos)
    try:
        historico.registrar(pasta, movidos, pastas_criadas)
    except OSError as erro:  # ex.: pasta sem permissão de escrita
        aviso = f"AVISO: não foi possível gravar o histórico ({erro}); esta mudança não poderá ser desfeita."
        return movidos, pulados, aviso
    return movidos, pulados, None


def dica_de_desfazer(pasta: Path, movidos: list[Movimento], aviso: str | None) -> None:
    if aviso:
        print(aviso)
    elif movidos:
        # shlex.quote põe aspas se o caminho tiver espaço, para o comando funcionar colado
        print(f"Para desfazer: python -m organizador {shlex.quote(str(pasta))} --desfazer")


def desfazer(pasta: Path, simulando: bool) -> None:
    """Desfaz (ou só mostra) a última organização feita nesta pasta."""
    resultado = historico.desfazer(pasta, simular=simulando)
    if resultado is None:
        print("Nada para desfazer nesta pasta.")
        return

    def relativo(caminho: Path) -> str:
        return caminho.relative_to(pasta).as_posix()

    if simulando:
        print(f"MODO SIMULAÇÃO: nada será desfeito (organização de {resultado.rodada.data.replace('T', ' ')}).\n")
    for movimento in resultado.voltaram:
        print(f"{relativo(movimento.destino)}  ->  {relativo(movimento.origem)}")
    for movimento, motivo in resultado.pulados:
        print(f"PULADO: {relativo(movimento.destino)} ({motivo})")

    if simulando:
        print(f"\n{len(resultado.voltaram)} arquivo(s) voltaria(m) para o lugar original.")
        if resultado.rodada.pastas_criadas:
            pastas = ", ".join(f"{relativo(p)}/" for p in resultado.rodada.pastas_criadas)
            print(f"Pastas criadas nessa organização (removidas se ficarem vazias): {pastas}")
        print("Para desfazer de verdade, rode o mesmo comando sem --simular.")
        return

    print(f"\n{len(resultado.voltaram)} arquivo(s) voltou(aram) para o lugar original.")
    if resultado.pastas_removidas:
        pastas = ", ".join(f"{relativo(p)}/" for p in resultado.pastas_removidas)
        print(f"Pasta(s) vazia(s) removida(s): {pastas}")
    if resultado.pulados:
        print(
            f"{len(resultado.pulados)} pulado(s): ficaram onde estão. "
            "Essa organização saiu do histórico mesmo assim."
        )


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
    ilegiveis: list[Path] = []
    grupos = encontrar_duplicados(pasta, ilegiveis)
    for arquivo in ilegiveis:
        print(f"NÃO LIDO: {arquivo.relative_to(pasta).as_posix()} (aberto em outro programa ou sem permissão; ficou de fora)")
    if not grupos:
        print("Nenhum arquivo duplicado.")
        return
    if simular_apenas:
        mostrar_duplicados(pasta, grupos)
        return

    tamanhos = {copia: g.tamanho for g in grupos for copia in g.copias}
    movidos, pulados, aviso = mover_e_registrar(pasta, planejar_duplicados(pasta, grupos))
    for movimento in movidos:
        print(f"{movimento.origem.relative_to(pasta).as_posix()}  ->  {movimento.destino.relative_to(pasta).as_posix()}")
    for movimento in pulados:
        print(f"PULADO: {movimento.origem.relative_to(pasta).as_posix()} (surgiu um arquivo com o mesmo nome no destino)")
    liberado = sum(tamanhos[m.origem] for m in movidos)
    print(f"\n{len(movidos)} cópia(s) movida(s) para {PASTA_DUPLICADOS}/ ({tamanho_legivel(liberado)}).")
    if pulados:
        print(f"{len(pulados)} pulada(s). Rode de novo para separá-las.")
    print(f"Nada foi apagado: confira a pasta {PASTA_DUPLICADOS}/ e, se estiver tudo certo, apague-a para liberar o espaço.")
    dica_de_desfazer(pasta, movidos, aviso)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="organizador",
        description="Separa os arquivos de uma pasta em subpastas por tipo ou por data.",
    )
    parser.add_argument("pasta", type=pasta_existente, help="ex.: ~/Downloads")
    parser.add_argument(
        "--por",
        choices=["tipo", "data"],
        default=None,  # None em vez de "tipo" para saber se o usuário digitou --por
        help="tipo: Imagens/, Documentos/... | data: 2026/09/... (padrão: tipo)",
    )
    parser.add_argument(
        "-s",
        "--simular",
        action="store_true",
        help="só mostra o que seria feito, sem mover nada",
    )
    parser.add_argument(
        "--desfazer",
        action="store_true",
        help="desfaz a última organização (ou separação de duplicados) desta pasta; pode repetir",
    )
    parser.add_argument(
        "--duplicados",
        action="store_true",
        help="acha arquivos iguais (pelo conteúdo) e move as cópias para Duplicados/",
    )
    args = parser.parse_args()

    if args.desfazer and args.duplicados:
        parser.error("use --desfazer sozinho: ele desfaz a última mudança, inclusive a dos duplicados")
    if args.desfazer and args.por:
        parser.error("--desfazer não combina com --por: ele desfaz o que foi feito, seja por tipo ou por data")
    if args.duplicados and args.por:
        parser.error("--duplicados não combina com --por")

    # Confere o histórico antes de mover qualquer coisa: se ele estiver
    # corrompido, mover agora criaria uma rodada impossível de desfazer
    try:
        historico.carregar(args.pasta)
    except historico.HistoricoInvalido as erro:
        sys.exit(f"Erro no histórico: {erro}\nConfira ou apague o arquivo {historico.ARQUIVO} dessa pasta.")

    if args.desfazer:
        desfazer(args.pasta, args.simular)
        return
    if args.duplicados:
        separar_duplicados(args.pasta, args.simular)
        return

    movimentos = planejar(args.pasta, args.por or "tipo")
    if not movimentos:
        print("Nada para organizar.")
        return

    if args.simular:
        simular(movimentos)
        return

    movidos, pulados, aviso = mover_e_registrar(args.pasta, movimentos)
    for movimento in movidos:
        print(descrever(movimento))
    for movimento in pulados:
        print(f"PULADO: {movimento.origem.name} (surgiu um arquivo com o mesmo nome em {movimento.subpasta}/)")
    print(f"\n{len(movidos)} arquivo(s) movido(s){contar_renomeados(movidos)}.")
    if pulados:
        print(f"{len(pulados)} pulado(s). Rode de novo para organizá-los.")
    dica_de_desfazer(args.pasta, movidos, aviso)


if __name__ == "__main__":
    main()
