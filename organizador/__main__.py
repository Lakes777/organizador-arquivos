"""Interface de linha de comando: python -m organizador <pasta>."""

import argparse
import shlex
import sys
from pathlib import Path

from organizador import historico
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
        help="desfaz a última organização feita nesta pasta (pode repetir)",
    )
    args = parser.parse_args()

    if args.desfazer and args.por:
        parser.error("--desfazer não combina com --por: ele desfaz o que foi feito, seja por tipo ou por data")

    # Confere o histórico antes de mover qualquer coisa: se ele estiver
    # corrompido, organizar agora criaria uma rodada impossível de desfazer
    try:
        historico.carregar(args.pasta)
    except historico.HistoricoInvalido as erro:
        sys.exit(f"Erro no histórico: {erro}\nConfira ou apague o arquivo {historico.ARQUIVO} dessa pasta.")

    if args.desfazer:
        desfazer(args.pasta, args.simular)
        return

    movimentos = planejar(args.pasta, args.por or "tipo")
    if not movimentos:
        print("Nada para organizar.")
        return

    if args.simular:
        simular(movimentos)
        return

    pastas_criadas = historico.pastas_novas(args.pasta, movimentos)
    movidos, pulados = executar(movimentos)
    aviso = None
    try:
        historico.registrar(args.pasta, movidos, pastas_criadas)
    except OSError as erro:  # ex.: pasta sem permissão de escrita
        aviso = f"AVISO: não foi possível gravar o histórico ({erro}); esta organização não poderá ser desfeita."
    for movimento in movidos:
        print(descrever(movimento))
    for movimento in pulados:
        print(f"PULADO: {movimento.origem.name} (surgiu um arquivo com o mesmo nome em {movimento.subpasta}/)")
    print(f"\n{len(movidos)} arquivo(s) movido(s){contar_renomeados(movidos)}.")
    if pulados:
        print(f"{len(pulados)} pulado(s). Rode de novo para organizá-los.")
    if aviso:
        print(aviso)
    elif movidos:
        # shlex.quote põe aspas se o caminho tiver espaço, para o comando funcionar colado
        print(f"Para desfazer: python -m organizador {shlex.quote(str(args.pasta))} --desfazer")

if __name__ == "__main__":
    main()
