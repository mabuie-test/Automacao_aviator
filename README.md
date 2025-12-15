# Aviator Bot (Python + armazenamento local)

Reescrita em Python do bot de previsões para o jogo Aviator. A nova versão
armazena os multiplicadores em um arquivo JSON local (sem MySQL), usa um modelo
de Random Forest para prever o próximo ponto de cashout com base em janelas
temporais e responde em tempo real ao navegador já aberto. A GUI embutida
(Opera/Chromium) conecta direto no link fornecido, captura automaticamente o
endpoint final do jogo após redirecionamentos, guarda credenciais para reuso e
dispara o bot sem precisar do terminal. O painel de status agora recebe todos os
logs (incluindo a odd prevista de colapso da próxima rodada). O navegador
controlado é aberto pelo próprio bot ao iniciar, sem dependência de variáveis de
ambiente ou sessões externas (o anexo a um debug remoto continua disponível de
forma opcional). O guia de uso está em texto puro em
`docs/Como_usar_Aviator_Bot.md`, eliminando o arquivo DOCX para evitar binários
em PRs.

## Requisitos
- Python 3.11+
- Navegador Chromium-based (Opera/Chrome/Edge) e o driver do Selenium (o
  Selenium 4 baixa/gerencia automaticamente). Se preferir reutilizar uma sessão
  já logada, habilite o modo "usar navegador já aberto" na GUI e informe
  host/porta de depuração.
- Para a GUI: `PyQt5` + `PyQtWebEngine` (já listados em `requirements.txt`)

Instale as dependências Python:

```bash
pip install -r requirements.txt
```

Toda a configuração agora é feita pela própria GUI e armazenada em
`~/.aviator_bot/settings.json` (endpoint, credenciais opcionais, seletores,
parâmetros de risco e o caminho do arquivo de dados). O arquivo é sobrescrito a
cada ajuste feito na interface e também pode ser editado manualmente em texto.

## Como usar (GUI com browser embutido)
1. Rode a GUI para carregar o browser embutido e preencher credenciais/seletores. A GUI
   persiste tudo em `~/.aviator_bot/settings.json` (login/senha, endpoint do jogo, seletores
   e caminho do arquivo de dados JSON) para reutilizar depois. Se preferir uma área de login
   maior que o painel embutido, use o botão **Abrir navegador em janela grande** para abrir
   um WebView dedicado com 1400x900 pixels:
   ```bash
   python -m aviator_bot.gui
   ```
2. Clique em **Iniciar bot**. O Selenium abrirá automaticamente uma janela do navegador
   apontando para o link informado. Use essa janela ou o WebView dedicado para fazer login
   manualmente; o bot espera o seletor de prontidão ficar clicável e cumpre o aquecimento
   mínimo de 120s antes de liberar auto-bet.
3. Clique em **Testar conexões** para validar o arquivo de dados local (criado/regravado em
   `DATA_PATH`) e, se você optou por reutilizar uma sessão existente, o host/porta de depuração.
   O resultado aparece no painel de status.
4. Os logs com odds previstas, stake sugerida e ajustes de endpoint aparecem no painel inferior.
   As configurações podem ser editadas diretamente na GUI a qualquer momento; cada alteração é
   salva no JSON.

## Como usar (CLI tradicional)
1. Ajuste as configurações via GUI ou editando `~/.aviator_bot/settings.json`.
2. Rode o bot (o loop agora reage assim que um novo round encerra, sem
   polling manual). Por padrão ele passa os primeiros minutos apenas
   observando/coletando dados antes de habilitar apostas automáticas. O
   aquecimento sempre será de no mínimo 120 segundos, mesmo que um valor menor
   seja informado. Se preferir reaproveitar uma sessão já logada, habilite
   `attach_to_existing` na GUI antes de rodar o comando:
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
valores via Selenium. As previsões são logadas no console e, se `auto_bet` estiver
habilitado no JSON/GUI, o bot envia os cliques de aposta/cashout conforme a estratégia de
risco embutida.

## Como funciona (visão geral)
1. **Carregamento de configuração** (`aviator_bot/config.py`): carrega valores
   padrão e um JSON local com credenciais, endpoint, seletores e parâmetros de
   risco. Toda edição é feita via GUI e gravada no arquivo, dispensando variáveis
   de ambiente.
2. **Persistência local** (`aviator_bot/db.py`): garante o arquivo JSON
   `multipliers`, grava cada novo multiplicador observado e oferece consultas
   para treinar e alimentar o modelo de previsão.
3. **Scraping em tempo real** (`aviator_bot/scraper.py`): abre uma janela de navegador
   controlada automaticamente (ou anexa a uma já aberta, se configurado), carrega o link
   fornecido, captura o endpoint final após redirecionamentos e observa o valor de cashout
   ao fim de cada rodada. Em caso de erro ou timeout, ressincroniza o iframe automaticamente.
4. **Modelo de previsão** (`aviator_bot/model.py`): treina um Random Forest
   usando janelas temporais de multiplicadores e prevê o próximo valor esperado.
5. **Gestão de risco e execução** (`aviator_bot/strategy.py` e
   `aviator_bot/runner.py`): calcula aposta sugerida combinando confiança do
   modelo com leitura de tendência recente (`STREAK_WINDOW`). A estratégia agora
   é autoajustável: aplica freios quando há alta volatilidade ou sequência de
   busts e libera stake/cashout mais agressivos quando a tendência é positiva e
   estável. Quando `auto_bet` está ativo, o runner envia cliques nos
   campos/botões configurados para apostar e fazer cashout, sempre após cumprir
   a janela de aquecimento `WARMUP_SECONDS` e somente depois que o jogo estiver
   logado (o bot espera o formulário ficar clicável). A GUI embute o browser e
   inicia o loop em thread separada usando as credenciais persistidas.

## Estrutura
- `aviator_bot/config.py`: gerenciamento de configurações e persistência em JSON local.
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
