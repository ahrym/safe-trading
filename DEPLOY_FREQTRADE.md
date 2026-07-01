# Deploy Freqtrade no Railway

## Passo a passo

1. No Railway, no mesmo projeto do dashboard, clique em **"+ New Service"**
2. Escolha **"GitHub Repo"** → selecione `ahrym/safe-trading`
3. Em **"Root Directory"**, coloque: `freqtrade`
4. O Railway vai detectar o Dockerfile automaticamente
5. Em **"Variables"**, não é necessário adicionar nada — tudo está no `config.json`
6. Clique em **Deploy** → aguarde o build (pode levar alguns minutos)

## Após o deploy do Freqtrade

1. Copie o URL interno do serviço Freqtrade (Railway mostra em **"Networking" → "Private Networking"**)
   - Exemplo: `freqtrade.railway.internal:8081`
2. No serviço do **Dashboard**, adicione a variável de ambiente:
   - `FREQTRADE_URL` = `http://freqtrade.railway.internal:8081`
3. Clique em **Redeploy** no Dashboard

## Verificar se funcionou

No dashboard, abra a aba **"Freqtrade Live"** — deve mostrar status, capital e trades.

## Credenciais da API Freqtrade

As credenciais estão definidas em `freqtrade/config.json` (variáveis `api_server.username` e `api_server.password`).
Para produção real, mova-as para variáveis de ambiente no Railway e referencie via `${FREQTRADE_API_USER}` / `${FREQTRADE_API_PASSWORD}`.

- Endpoint de status: `GET /api/v1/status` (com Basic Auth)
- Ping (requer auth): `GET /api/v1/ping`
