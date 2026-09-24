"""Decide em qual pasta cada arquivo deve ficar, pela extensão."""

from pathlib import Path

CATEGORIAS: dict[str, set[str]] = {
    "Imagens": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".heic"},
    "Documentos": {".pdf", ".doc", ".docx", ".odt", ".txt", ".md", ".rtf"},
    "Planilhas": {".xls", ".xlsx", ".ods", ".csv"},
    "Apresentações": {".ppt", ".pptx", ".odp"},
    "Vídeos": {".mp4", ".mkv", ".avi", ".mov", ".webm"},
    "Músicas": {".mp3", ".wav", ".flac", ".ogg", ".m4a"},
    "Compactados": {".zip", ".rar", ".7z", ".tar", ".gz"},
    "Instaladores": {".exe", ".msi", ".deb", ".appimage"},
    "Código": {".py", ".js", ".html", ".css", ".json", ".sh"},
}

OUTROS = "Outros"

# Índice invertido (".jpg" -> "Imagens") para achar a categoria sem percorrer tudo
_POR_EXTENSAO = {
    extensao: categoria
    for categoria, extensoes in CATEGORIAS.items()
    for extensao in extensoes
}


def categoria_de(arquivo: Path) -> str:
    """Retorna o nome da pasta de destino. Ex.: 'foto.JPG' -> 'Imagens'."""
    return _POR_EXTENSAO.get(arquivo.suffix.lower(), OUTROS)
