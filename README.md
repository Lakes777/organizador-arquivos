# 🗂️ Organizador de Arquivos

[![Testes](https://github.com/Lakes777/organizador-arquivos/actions/workflows/testes.yml/badge.svg)](https://github.com/Lakes777/organizador-arquivos/actions/workflows/testes.yml)

Ferramenta de linha de comando que organiza pastas bagunçadas, como a de Downloads, separando os arquivos em subpastas **por tipo** (Imagens, Documentos, Instaladores...) ou **por data** (2026/09). Feita em Python puro.

![Demonstração do organizador](docs/demo.gif)

## Funcionalidades

- **Organiza por tipo** em 10 categorias, reconhecendo mais de 50 extensões (maiúsculas ou minúsculas); o que não for reconhecido vai para `Outros/`
- **Organiza por data** em pastas de ano e mês, pela data de modificação do arquivo
- **Modo simulação** (`--simular`), que mostra o plano completo sem mover nada
- **Nunca sobrescreve arquivos:** nomes repetidos viram `foto (1).jpg`, `foto (2).jpg`..., como no Windows
- **Não mexe no que não deve:** subpastas, arquivos ocultos e arquivos de sistema do Windows (`desktop.ini`, `Thumbs.db`) ficam onde estão

## Instalação

Requer **Python 3.10+**. Não há dependências externas para usar o programa.

```bash
git clone https://github.com/Lakes777/organizador-arquivos.git
cd organizador-arquivos
```

## Como usar

```bash
# Ver o que seria feito, sem mover nada (recomendado na primeira vez)
python -m organizador ~/Downloads --simular

# Organizar por tipo (padrão)
python -m organizador ~/Downloads

# Organizar por ano e mês
python -m organizador ~/Downloads --por data

# Ajuda
python -m organizador --help
```

> **No WSL**, a pasta Downloads do Windows fica em `/mnt/c/Users/<seu-usuário>/Downloads`.

## Testes

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

São 25 testes cobrindo as categorias, o planejamento, a movimentação dos arquivos e a linha de comando. Eles usam pastas temporárias (`tmp_path`) e nunca tocam em arquivos reais. O GitHub Actions roda os testes a cada push, nas versões 3.10 a 3.14 do Python.

## Estrutura do projeto

```
organizador-arquivos/
├── organizador/
│   ├── __main__.py     # linha de comando (argparse)
│   ├── categorias.py   # extensão -> categoria
│   └── organizar.py    # planejar e executar a movimentação
└── tests/              # testes com pytest
```

## Decisões técnicas

- **Planejar separado de executar:** `planejar()` só calcula para onde cada arquivo vai e `executar()` só move. O `--simular` é apenas não chamar o segundo, então a simulação e a execução real sempre batem linha por linha.
- **Nunca apagar nada:** no Linux, mover um arquivo por cima de outro apaga o antigo sem aviso. O nome livre é escolhido no planejamento e, se mesmo assim um arquivo surgir no destino antes da execução (um download terminando, por exemplo), ele é pulado.
- **Arquivos de sistema ignorados:** testando na minha própria pasta Downloads, a simulação mostrou que o `desktop.ini` seria movido. É ele que define o nome e o ícone da pasta no Explorer do Windows, então passou a ser ignorado.
- **Data de modificação para organizar por data:** em arquivos baixados ela costuma ser o dia do download, e mover com `rename()` não a altera, então organizar por tipo antes não estraga as datas.
- **Testes que falham quando devem:** para confirmar que os testes protegem de verdade, introduzi bugs de propósito (remover a proteção contra sobrescrita, esquecer do `desktop.ini`) e verifiquei que a suíte os detecta.

## Próximos passos

- [ ] Encontrar arquivos duplicados comparando o conteúdo (hash), mesmo com nomes diferentes
- [ ] Desfazer a última organização
- [ ] Categorias personalizáveis por um arquivo de configuração
- [ ] Rodar automaticamente em segundo plano, organizando cada novo download
