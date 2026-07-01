# Safe Trading — Deploy Railway + Supabase

Deploy gratuito do dashboard para rodar 24/7 na nuvem.

---

## Pré-requisitos

- Conta no [GitHub](https://github.com)
- Conta no [Railway](https://railway.app) (gratuito — 500h/mês)
- Conta no [Supabase](https://supabase.com) (gratuito — 500MB)

---

## Passo 1 — Criar banco de dados no Supabase

1. Acesse [supabase.com](https://supabase.com) e crie um novo projeto
2. Aguarde o projeto inicializar (1-2 minutos)
3. Vá em **SQL Editor** > **New Query**
4. Cole o conteúdo do arquivo `supabase_schema.sql` e clique em **Run**
5. Vá em **Settings** > **API** e copie:
   - **Project URL** (algo como `https://abc123.supabase.co`)
   - **anon public key** (string longa começando com `eyJ...`)

---

## Passo 2 — Publicar o código no GitHub

```bash
# No terminal, dentro da pasta do projeto:
git init
git add .
git commit -m "Safe Trading Dashboard — deploy inicial"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/safe-trading.git
git push -u origin main
```

> Substitua `SEU_USUARIO` pelo seu usuário do GitHub.
> Crie o repositório no GitHub antes (pode ser privado).

---

## Passo 3 — Criar projeto no Railway

1. Acesse [railway.app](https://railway.app) e faça login com GitHub
2. Clique em **New Project** > **Deploy from GitHub Repo**
3. Selecione o repositório `safe-trading`
4. Railway vai detectar o `Dockerfile` automaticamente e iniciar o build

---

## Passo 4 — Configurar variáveis de ambiente no Railway

No painel do Railway, vá em **Variables** e adicione:

| Variável | Valor |
|---|---|
| `SUPABASE_URL` | URL copiada no Passo 1 |
| `SUPABASE_KEY` | Chave anon copiada no Passo 1 |
| `DASHBOARD_USER` | `andre` (ou outro usuário) |
| `DASHBOARD_PASSWORD` | Escolha uma senha forte |

> `PORT` não precisa ser configurado — Railway injeta automaticamente.

---

## Passo 5 — Acessar o dashboard

1. No Railway, vá em **Settings** > **Networking** > **Generate Domain**
2. Clique no domínio gerado (algo como `safe-trading-production.up.railway.app`)
3. O navegador vai pedir usuário e senha (os que você configurou acima)

---

## Atualizações futuras

Para atualizar o dashboard após mudanças no código:

```bash
git add .
git commit -m "Descrição da mudança"
git push
```

Railway detecta o push e faz redeploy automaticamente.

---

## Scheduler interno

O dashboard roda um job interno a cada **4 horas** que:
- Busca as últimas velas BTC/USDT da Binance
- Recalcula EMA/RSI e verifica sinais de entrada/saída
- Atualiza o paper trading e sincroniza com o Supabase

Não é necessário configurar nada — roda automaticamente com o app.

---

---

## Freqtrade no Railway (segundo serviço)

O Freqtrade roda como um **serviço separado** no Railway, usando a imagem Docker oficial.
O dashboard Dash consome a API REST do Freqtrade via variável `FREQTRADE_URL`.

### Passo 1 — Criar segundo serviço no Railway

1. No painel do Railway, clique em **New** > **Docker Image**
2. Imagem: `freqtradeorg/freqtrade:stable`
3. Nome do serviço: `freqtrade`

### Passo 2 — Configurar variáveis de ambiente do Freqtrade

No serviço `freqtrade`, em **Variables**:

| Variável | Valor |
|---|---|
| `FREQTRADE__DRY_RUN` | `true` |
| `FREQTRADE__DRY_RUN_WALLET` | `1000` |
| `FREQTRADE__API_SERVER__ENABLED` | `true` |
| `FREQTRADE__API_SERVER__USERNAME` | `freqtrade` |
| `FREQTRADE__API_SERVER__PASSWORD` | `safetrading123` |
| `FREQTRADE__API_SERVER__JWT_SECRET_KEY` | `safe-trading-2026` |

### Passo 3 — Montar config.json e estratégias

O Freqtrade no Railway precisa dos arquivos de estratégia. Opções:

**Opção A (recomendada):** criar repositório separado `safe-trading-freqtrade` contendo:
```
config.json
strategies/
    EMAClassica.py
    EMAComFiltro.py
user_data/
    data/
    logs/
```
E deployar via **GitHub Repo** em vez de Docker Image.

**Opção B:** usar Volume do Railway para montar os arquivos.

### Passo 4 — Conectar o Dashboard ao Freqtrade

No serviço do **dashboard** (Dash), adicionar variável:

| Variável | Valor |
|---|---|
| `FREQTRADE_URL` | URL interna do serviço Railway (ex.: `http://freqtrade.railway.internal:8081`) |

O Railway fornece DNS interno entre serviços do mesmo projeto.
Se usar domínio público: `https://freqtrade-production.up.railway.app`

### Comando de inicialização do Freqtrade no Railway

```
trade --logfile /freqtrade/user_data/logs/freqtrade.log --config /freqtrade/config.json --strategy EMAClassica
```

### Rodar localmente (desenvolvimento)

```bash
cd freqtrade
docker-compose up -d

# Ver logs
docker-compose logs -f

# Testar API
curl -u freqtrade:safetrading123 http://localhost:8081/api/v1/ping

# Parar
docker-compose down
```

### Mudar estratégia ativa (S1 → S2)

Edite `freqtrade/docker-compose.yml` e troque `--strategy EMAClassica` por `--strategy EMAComFiltro`.
Reinicie: `docker-compose down && docker-compose up -d`

---

## Troubleshooting

**Build falha:** verifique se o `Dockerfile` está na raiz do projeto.

**Erro de autenticação Supabase:** confira se `SUPABASE_URL` e `SUPABASE_KEY` estão corretos (sem espaços extras).

**Dashboard não carrega:** no Railway, veja os logs em **Deployments** > **View Logs**.

**Porta não funciona:** Railway injeta `PORT` automaticamente — não configure manualmente.
