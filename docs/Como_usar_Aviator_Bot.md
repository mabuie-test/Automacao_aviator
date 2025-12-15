# Guia rápido: Aviator Bot (GUI + CLI)

Este guia substitui o antigo arquivo DOCX e está totalmente em texto para
facilitar revisões de PR e compartilhamento. Ele resume como preparar o ambiente,
usar a GUI com navegador embutido, rodar via CLI, além de dicas de estratégia e
armazenamento de credenciais.

## Pré-requisitos
- Python 3.11+
- Navegador baseado em Chromium (Opera/Chrome/Edge) aberto com
  `--remote-debugging-port` para reaproveitar a sessão autenticada
- Dependências Python listadas em `requirements.txt` (`PyQt5` e `PyQtWebEngine`
  já incluídas para o navegador embutido)

Instalação das dependências:
```bash
pip install -r requirements.txt
```

## Configuração (variáveis de ambiente principais)
Configure o endpoint, armazenamento local e parâmetros de risco/automação antes de iniciar:
```bash
export AVIATOR_URL="https://1whpc.com/casino/play/aviator"
export CHROME_DEBUG_HOST=127.0.0.1
export CHROME_DEBUG_PORT=9222
export CHROME_BINARY="C:/Program Files/Opera/opera.exe"
export DATA_PATH="~/.aviator_bot/multipliers.json"
export PLATFORM_USER="seu_login"             # opcional: preenche login automaticamente
export PLATFORM_PASSWORD="sua_senha"         # opcional: preenche senha
export AUTO_BET=true
export BASE_BET=2
export MAX_BET=20
export CONFIDENCE_FLOOR=0.4
export STREAK_WINDOW=10
export BET_INPUT_SELECTOR="input[type='number']"
export BET_BUTTON_SELECTOR="button.place-bet"
export CASHOUT_BUTTON_SELECTOR="button.cashout"
export WARMUP_SECONDS=180        # mínimo de 120s sempre aplicado
export SESSION_READY_SELECTOR="input[type='number']"
export SESSION_READY_TIMEOUT=90
```

## Usando a GUI com navegador embutido
1. Abra o Opera (ou outro Chromium) com depuração remota:
   ```bash
   "C:/Program Files/Opera/opera.exe" --remote-debugging-port=9222 --user-data-dir="%USERPROFILE%/opera-aviator"
   ```
2. Inicie a GUI e preencha login/senha (opcionais), endpoint do jogo, seletores e caminho do arquivo de dados JSON:
   ```bash
   python -m aviator_bot.gui
   ```
3. Faça login manualmente no navegador embutido; o bot só continua quando o
   seletor de prontidão (`SESSION_READY_SELECTOR`) ficar clicável e o
   aquecimento mínimo (>=120s) for cumprido.
4. Clique em **Testar conexões** para validar o arquivo local e sessão de depuração antes
   de iniciar.
5. Clique em **Iniciar bot**. O loop roda em segundo plano, salva
   multiplicadores no JSON local, ajusta aposta/cashout com base em confiança do
   modelo, tendência recente e freios de volatilidade, captura o endpoint final
   da janela e reusa as credenciais/endpoint persistidos em `~/.aviator_bot/settings.json`.

## Usando via CLI
1. Abra o navegador com depuração remota (mesmo comando do passo 1 acima) e
   faça login manualmente.
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
- Defina `AUTO_BET=false` para rodar somente em modo observação/log, mantendo a
  coleta e previsões sem clicar.
- Os seletores de input/botões podem ser ajustados via variáveis de ambiente ou
  na própria GUI.

## Armazenamento de credenciais e endpoint
- A GUI salva as informações em `~/.aviator_bot/settings.json` de forma local.
- Você pode editar ou remover esse arquivo manualmente para limpar dados.
- O runner também consome essas configurações quando a GUI as persiste.

## Solução para o erro "Binary files are not supported"
O arquivo DOCX anterior foi substituído por este guia em Markdown para evitar
binários no repositório. Isso elimina o aviso ao criar PRs e facilita revisões.
