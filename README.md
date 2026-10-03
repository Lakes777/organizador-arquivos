# Tidy

[![Testes](https://github.com/Lakes777/organizador-arquivos/actions/workflows/testes.yml/badge.svg)](https://github.com/Lakes777/organizador-arquivos/actions/workflows/testes.yml)

**Tidy · organizador de arquivos.** Ferramenta de linha de comando que organiza pastas bagunçadas, como a de Downloads, separando os arquivos em subpastas **por tipo** (Imagens, Documentos, Instaladores...) ou **por data** (2026/09). Feita em Python puro.

![Demonstração do Tidy no terminal: simular, organizar por tipo e por data](docs/demo.gif)

## Funcionalidades

- **Organiza por tipo** em 10 categorias, reconhecendo mais de 50 extensões (maiúsculas ou minúsculas); o que não for reconhecido vai para `Outros/`
- **Organiza por data** em pastas de ano e mês, pela data de modificação do arquivo
- **Modo simulação** (`--simular`), que mostra o plano completo sem mover nada
- **Nunca sobrescreve arquivos:** nomes repetidos viram `foto (1).jpg`, `foto (2).jpg`..., como no Windows
- **Acha arquivos duplicados** (`--duplicados`) pelo conteúdo, mesmo com nomes diferentes, na pasta e nas subpastas que o organizador cria (`Imagens/`, `2026/`...), e mostra quanto espaço dá para liberar. As cópias são movidas para `Duplicados/`, nunca apagadas; fica o original provável (sem " (1)" ou "- Cópia" no nome, depois o mais antigo)
- **Desfaz** (`--desfazer`) a última organização ou separação de duplicados, devolvendo cada arquivo ao lugar e removendo as pastas que ela criou e ficaram vazias. Guarda as últimas 20, então dá para desfazer várias vezes
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

# Achar arquivos iguais (só mostrar; sem --simular, move as cópias para Duplicados/)
python -m organizador ~/Downloads --duplicados --simular

# Desfazer a última mudança (organização ou duplicados)
python -m organizador ~/Downloads --desfazer --simular   # mostra o que voltaria
python -m organizador ~/Downloads --desfazer

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

São 83 testes cobrindo as categorias, o planejamento, a movimentação dos arquivos, os duplicados, o histórico e o desfazer, e a linha de comando. Eles usam pastas temporárias (`tmp_path`) e nunca tocam em arquivos reais. O GitHub Actions roda os testes a cada push, nas versões 3.10 a 3.14 do Python.

## Estrutura do projeto

```
organizador-arquivos/
├── organizador/
│   ├── __main__.py     # linha de comando (argparse)
│   ├── categorias.py   # extensão -> categoria
│   ├── duplicados.py   # arquivos iguais pelo conteúdo (SHA-256)
│   ├── historico.py    # o que foi movido, para desfazer
│   └── organizar.py    # planejar e executar a movimentação
└── tests/              # testes com pytest
```

## Decisões técnicas

- **Planejar separado de executar:** `planejar()` só calcula para onde cada arquivo vai e `executar()` só move. O `--simular` é apenas não chamar o segundo, então a simulação e a execução real sempre batem linha por linha.
- **Nunca apagar nada:** no Linux, mover um arquivo por cima de outro apaga o antigo sem aviso. O nome livre é escolhido no planejamento e, se mesmo assim um arquivo surgir no destino antes da execução (um download terminando, por exemplo), ele é pulado.
- **Arquivos de sistema ignorados:** testando na minha própria pasta Downloads, a simulação mostrou que o `desktop.ini` seria movido. É ele que define o nome e o ícone da pasta no Explorer do Windows, então passou a ser ignorado.
- **Data de modificação para organizar por data:** em arquivos baixados ela costuma ser o dia do download, e mover com `rename()` não a altera, então organizar por tipo antes não estraga as datas.
- **Duplicados sem ler tudo:** calcular o hash lê o arquivo inteiro, então os arquivos são agrupados primeiro pelo tamanho (que é de graça) e só os de tamanho repetido têm o SHA-256 calculado, lendo 1 MiB por vez para um vídeo grande não ocupar a memória. Um arquivo que não abre (em uso por outro programa no Windows) fica de fora e aparece na saída, em vez de parar a busca.
- **Histórico dentro da pasta:** cada mudança é gravada em `.organizador-historico.json`, oculto (e por isso ignorado pela organização), com caminhos relativos: se a pasta for renomeada, o desfazer continua valendo. O arquivo é gravado num temporário e trocado com `os.replace`, então uma queda no meio não deixa um JSON pela metade. Um histórico corrompido ou com caminhos para fora da pasta (`..`) é recusado antes de mover qualquer coisa.
- **Duplicados só nas pastas do organizador:** uma pasta qualquer dentro da Downloads (um jogo ou projeto extraído de um `.zip`) pode ter arquivos repetidos de propósito, como DLLs e `LICENSE`; tirar um deles quebraria o programa. Por isso a busca olha só a raiz e as pastas que o próprio organizador cria. `Duplicados/` é comparada sem diferenciar maiúsculas, porque no Windows `duplicados` é a mesma pasta.
- **Arquivo em uso não interrompe nada:** no Windows, um PDF aberto no leitor não pode ser movido. Esse arquivo é pulado com o motivo e os outros continuam; se o programa parasse no meio, os já movidos ficariam fora do histórico e não daria para desfazer. Foi um revisor (outro agente) que achou esse caso, e há testes que simulam o erro.
- **Desfazer também nunca sobrescreve:** se o lugar original já tem outro arquivo, ou se o arquivo não está mais onde foi posto, ele é pulado e aparece na saída. Pastas só são removidas se foram criadas por aquela rodada e ficaram vazias.
- **Feito com subagentes:** o `--duplicados` e o `--desfazer` foram escritos ao mesmo tempo por dois subagentes do Claude Code, cada um num `git worktree` separado; depois as duas branches foram juntadas (resolvendo o conflito na linha de comando) e ligadas, para os duplicados também poderem ser desfeitos.
- **Testes que falham quando devem:** para confirmar que os testes protegem de verdade, introduzi bugs de propósito (remover a proteção contra sobrescrita, esquecer do `desktop.ini`) e verifiquei que a suíte os detecta.

## Próximos passos

- [x] Encontrar arquivos duplicados comparando o conteúdo (hash), mesmo com nomes diferentes
- [x] Desfazer a última organização
- [ ] Categorias personalizáveis por um arquivo de configuração
- [ ] Rodar automaticamente em segundo plano, organizando cada novo download
