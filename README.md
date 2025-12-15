# Aviator Bot (Python + armazenamento local)

Reescrita em Python do bot de previsões para o jogo Aviator. A nova versão
armazena os multiplicadores em um arquivo JSON local (sem MySQL), usa um modelo
de Random Forest para prever o próximo ponto de cashout com base em janelas
temporais e responde em tempo real ao navegador já aberto. A GUI embutida
(Opera/Chromium) conecta direto no link fornecido, captura automaticamente o
endpoint final do jogo após redirecionamentos, guarda credenciais para reuso e
dispara o bot sem precisar do terminal. O painel de status agora recebe todos os
logs (incluindo a odd prevista de colapso da próxima rodada). O guia de uso está
em texto puro em `docs/Como_usar_Aviator_Bot.md`, eliminando o arquivo DOCX para
evitar binários em PRs.

## Requisitos
- Python 3.11+
- Navegador Chromium-based (Opera/Chrome/Edge) aberto com `--remote-debugging-port`
  para que o bot reutilize a sessão autenticada
- Para a GUI: `PyQt5` + `PyQtWebEngine` (já listados em `requirements.txt`)

Instale as dependências Python:

```bash
pip install -r requirements.txt
```

Configure as variáveis de ambiente para o endpoint, armazenamento local e (opcionalmente)
para o modo de autoaposta e estratégia:

```bash
export AVIATOR_URL="https://1whpc.com/casino/play/aviator"
export CHROME_DEBUG_HOST=127.0.0.1     # host do debug remoto (Opera/Chrome/Edge)
export CHROME_DEBUG_PORT=9222          # porta do debug remoto
export CHROME_BINARY="C:/Program Files/Opera/opera.exe"  # binário do Opera (opcional)
export DATA_PATH="~/.aviator_bot/multipliers.json"        # arquivo JSON regravável
export PLATFORM_USER="seu_login"                         # opcional: preenche o login
export PLATFORM_PASSWORD="sua_senha"                     # opcional: preenche a senha
export AUTO_BET=true               # habilita cliques automáticos
export BASE_BET=2                  # valor inicial sugerido
export MAX_BET=20                  # teto de exposição
export CONFIDENCE_FLOOR=0.4        # confiança mínima para apostar
export STREAK_WINDOW=10            # janela para medir tendência e ajustar stake/cashout
export BET_INPUT_SELECTOR="input[type='number']"   # seletores customizáveis
export BET_BUTTON_SELECTOR="button.place-bet"
export CASHOUT_BUTTON_SELECTOR="button.cashout"
export WARMUP_SECONDS=180           # janela inicial só de observação/coleta (mínimo 120s)
export SESSION_READY_SELECTOR="input[type='number']" # usa este elemento para confirmar login
export SESSION_READY_TIMEOUT=90     # tempo máximo esperando você logar manualmente
```

## Como usar (GUI com browser embutido)
1. Inicie o Opera (ou outro Chromium) com depuração remota, por exemplo:
   ```bash
   "C:/Program Files/Opera/opera.exe" --remote-debugging-port=9222 --user-data-dir="%USERPROFILE%/opera-aviator"
   ```
2. Rode a GUI para carregar o browser embutido e preencher credenciais/seletores. A GUI
   persiste tudo em `~/.aviator_bot/settings.json` (login/senha, endpoint do jogo, seletores
   e caminho do arquivo de dados JSON) para reutilizar depois:
   ```bash
   python -m aviator_bot.gui
   ```
3. Use o navegador embutido para logar manualmente na plataforma. O bot só começa após
   detectar o seletor de prontidão configurado e cumprir o aquecimento mínimo de 120s
   (ou mais, se definido).
4. Clique em **Testar conexões** para validar o arquivo de dados local (criado/regravado em
   `DATA_PATH`) e a sessão de depuração do Opera/Chrome antes de iniciar. O resultado aparece
   no painel de status.
5. Clique em **Iniciar bot** na GUI. O loop de coleta/predição roda em uma thread separada,
   grava multiplicadores no JSON local, calcula stake/cashout automaticamente, ajusta o
   endpoint final detectado no navegador e respeita as travas de risco/volatilidade. Os logs
   aparecem no painel inferior.

## Como usar (CLI tradicional)
1. Inicie o Opera com depuração remota (ou outro navegador compatível), por exemplo:
   ```bash
   "C:/Program Files/Opera/opera.exe" --remote-debugging-port=9222 --user-data-dir="%USERPROFILE%/opera-aviator"
   ```
2. Faça login manualmente no site do jogo na janela aberta.
3. Certifique-se de que o arquivo local indicado em `DATA_PATH` é gravável e que
   o navegador aberto com depuração remota está logado no jogo.
4. Rode o bot (o loop agora reage assim que um novo round encerra, sem
   polling manual). Por padrão ele passa os primeiros minutos apenas
   observando/coletando dados antes de habilitar apostas automáticas. O
   aquecimento sempre será de no mínimo 120 segundos, mesmo que um valor menor
   seja informado. Se estiver no Windows com o Opera aberto, aponte o binário e
   o host/porta de depuração via `CHROME_BINARY`/`CHROME_DEBUG_HOST` para o
   driver reutilizar essa sessão:
   ```bash
   python -m aviator_bot.runner --seed-data Main/traindata.txt Main/traindata1.txt --time-steps 12 --warmup-seconds 180
   ```

Se quiser apenas testar as dependências sem rodar o loop, use o modo de verificação e
encerre após o diagnóstico:

```bash
python -m aviator_bot.runner --check-only
```

O comando acima cria o arquivo JSON de multipliers (caso não exista),
pré-carrega multiplicadores dos arquivos de treino e passa a coletar novos
valores via Selenium. As previsões são logadas no console e, se `AUTO_BET` for
`true`, o bot envia os cliques de aposta/cashout conforme a estratégia de risco
embutida.

## Como funciona (visão geral)
1. **Carregamento de configuração** (`aviator_bot/config.py`): lê variáveis de
   ambiente, normaliza tipos (bool/float/int), valida limites de risco e agora
   persiste/recupera um JSON local com credenciais e endpoint do jogo.
2. **Persistência local** (`aviator_bot/db.py`): garante o arquivo JSON
   `multipliers`, grava cada novo multiplicador observado e oferece consultas
   para treinar e alimentar o modelo de previsão.
3. **Scraping em tempo real** (`aviator_bot/scraper.py`): conecta ao Opera/Chrome já
   aberto via depuração remota, abre o link fornecido, captura o endpoint final após
   redirecionamentos e observa o valor de cashout ao fim de cada rodada. Em caso de
   erro ou timeout, ressincroniza o iframe automaticamente.
4. **Modelo de previsão** (`aviator_bot/model.py`): treina um Random Forest
   usando janelas temporais de multiplicadores e prevê o próximo valor esperado.
5. **Gestão de risco e execução** (`aviator_bot/strategy.py` e
   `aviator_bot/runner.py`): calcula aposta sugerida combinando confiança do
   modelo com leitura de tendência recente (`STREAK_WINDOW`). A estratégia agora
   é autoajustável: aplica freios quando há alta volatilidade ou sequência de
   busts e libera stake/cashout mais agressivos quando a tendência é positiva e
   estável. Quando `AUTO_BET` está ativo, o runner envia cliques nos
   campos/botões configurados para apostar e fazer cashout, sempre após cumprir
   a janela de aquecimento `WARMUP_SECONDS` e somente depois que o jogo estiver
   logado (o bot espera o formulário ficar clicável). A GUI embute o browser e
   inicia o loop em thread separada usando as credenciais persistidas.

## Estrutura
- `aviator_bot/config.py`: gerenciamento de configurações, variáveis de ambiente
  e persistência em JSON local.
- `aviator_bot/db.py`: operações com o arquivo JSON de multiplicadores.
- `aviator_bot/model.py`: modelo de previsão usando Random Forest.
- `aviator_bot/scraper.py`: scraper Selenium que lê os multiplicadores na página.
- `aviator_bot/runner.py`: orquestração de scraping, persistência e previsões.
- `aviator_bot/gui.py`: GUI PyQt5 com navegador embutido, armazenamento de
  credenciais/endpoint e disparo do loop do bot.

A pasta `Main/` mantém os arquivos originais em C# como referência dos
seletores e dados históricos.

## Criar nova ramificação

Para manter uma cópia completa do projeto em uma ramificação separada, siga o
guia em `docs/BRANCHING.md`. Ele mostra como criar a branch (ex.: `nova-ramificacao`),
confirmar todos os arquivos (código Python, GUI embutida, modelo de estratégia,
requirements e o guia em Markdown) e enviar para o remoto.
