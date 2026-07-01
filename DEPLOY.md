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

## Troubleshooting

**Build falha:** verifique se o `Dockerfile` está na raiz do projeto.

**Erro de autenticação Supabase:** confira se `SUPABASE_URL` e `SUPABASE_KEY` estão corretos (sem espaços extras).

**Dashboard não carrega:** no Railway, veja os logs em **Deployments** > **View Logs**.

**Porta não funciona:** Railway injeta `PORT` automaticamente — não configure manualmente.
