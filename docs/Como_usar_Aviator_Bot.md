# Guia rápido: Aviator Bot (GUI + CLI)

Este guia substitui o antigo arquivo DOCX e está totalmente em texto para
facilitar revisões de PR e compartilhamento. Ele resume como preparar o ambiente,
usar a GUI com navegador embutido, rodar via CLI, além de dicas de estratégia e
armazenamento de credenciais.

## Pré-requisitos
- Python 3.11+
- Navegador baseado em Chromium (Opera/Chrome/Edge) com driver compatível
  (o Selenium 4 baixa/gerencia automaticamente). Se quiser anexar a uma sessão
  já aberta, marque essa opção na GUI e informe host/porta de depuração.
- Dependências Python listadas em `requirements.txt` (`PyQt5` e `PyQtWebEngine`
  já incluídas para o navegador embutido)

Instalação das dependências:
```bash
pip install -r requirements.txt
```

## Configuração (GUI ou arquivo JSON)
Todos os ajustes são feitos na própria interface do bot e gravados em
`~/.aviator_bot/settings.json` (endpoint, credenciais opcionais, seletores,
parâmetros de risco e caminho do arquivo de dados). Você pode editar esse
arquivo manualmente em texto simples se preferir.

## Usando a GUI com navegador embutido
1. Inicie a GUI e preencha login/senha (opcionais), endpoint do jogo, seletores e caminho do arquivo de dados JSON:
   ```bash
   python -m aviator_bot.gui
   ```
2. Clique em **Iniciar bot**. O Selenium abre automaticamente uma janela do
   navegador apontando para o link informado. Faça login manualmente nessa
   janela (ou no navegador embutido); o bot só continua quando o seletor de
   prontidão ficar clicável e o aquecimento mínimo (>=120s) for cumprido.
3. Clique em **Testar conexões** para validar o arquivo local e, se você optou
   por anexar a uma sessão existente, o host/porta de depuração antes de iniciar.
4. O loop roda em segundo plano, salva multiplicadores no JSON local, ajusta
   aposta/cashout com base em confiança do modelo, tendência recente e freios de
   volatilidade, captura o endpoint final da janela e reusa as
   credenciais/endpoint persistidos em `~/.aviator_bot/settings.json`.

## Usando via CLI
1. Ajuste configurações via GUI ou editando `~/.aviator_bot/settings.json`.
2. Execute o runner (modo coleta/treino + automação):
   ```bash
   python -m aviator_bot.runner --seed-data Main/traindata.txt Main/traindata1.txt --time-steps 12 --warmup-seconds 180
   ```
3. Para apenas validar dependências, rode o modo de checagem e saia:
   ```bash
   python -m aviator_bot.runner --check-only
   ```

## Estratégia e segurança
- Sempre há pelo menos 120s de aquecimento antes de liberar apostas automáticas.
- A gestão de risco usa confiança do modelo, viés de tendência (`STREAK_WINDOW`)
  e freios de volatilidade/busts para limitar exposição.
- Defina `auto_bet=false` no `settings.json` para rodar somente em modo observação/log, mantendo a
  coleta e previsões sem clicar.
- Os seletores de input/botões podem ser ajustados direto na GUI (ou no
  `settings.json`).

## Armazenamento de credenciais e endpoint
- A GUI salva as informações em `~/.aviator_bot/settings.json` de forma local.
- Você pode editar ou remover esse arquivo manualmente para limpar dados.
- O runner também consome essas configurações quando a GUI as persiste.

## Solução para o erro "Binary files are not supported"
O arquivo DOCX anterior foi substituído por este guia em Markdown para evitar
binários no repositório. Isso elimina o aviso ao criar PRs e facilita revisões.
