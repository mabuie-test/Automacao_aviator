# Guia para criar uma nova ramificação com todo o projeto

Siga estas etapas para criar uma nova ramificação contendo o estado completo do projeto.

1. Certifique-se de estar na raiz do repositório:
   ```bash
   cd /workspace/Automacao_aviator
   ```
2. Atualize sua cópia local (se aplicável):
   ```bash
   git pull origin main
   ```
3. Crie e troque para a nova ramificação onde deseja manter todo o projeto:
   ```bash
   git checkout -b nova-ramificacao
   ```
4. Verifique se todos os arquivos necessários estão presentes (por exemplo, `aviator_bot/`, `requirements.txt`, `README.md` e `Como_usar_Aviator_Bot.docx`).
5. Adicione e confirme os arquivos, garantindo que nada fique sem versionamento:
   ```bash
   git add .
   git commit -m "Copia do projeto para nova ramificacao"
   ```
6. Envie a ramificação para o repositório remoto:
   ```bash
   git push -u origin nova-ramificacao
   ```

> Dica: se quiser manter a ramificação sempre atualizada com mudanças da linha principal, use `git merge main` ou `git rebase main` periodicamente.
