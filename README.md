# Quartel das IAs locais

Modelos open source rodando em GPU alugada (RunPod) hoje, e no meu PC amanhã,
atrás de **uma URL e uma chave**, com API compatível com OpenAI.

A regra do quartel: **só entra modelo que caiba numa GPU de 16 a 32 GB**. Assim
tudo que funciona aqui vai funcionar igual quando o PC chegar.

```
 apps / scripts / Claude Code / Open WebUI ...
              │   (API OpenAI, chave sk-...)
              ▼
 ┌──────────────────────────┐        ┌───────────────────────────────┐
 │ gateway/ (LiteLLM)       │ Bearer │ pod/ (RunPod ou PC local)     │
 │ Railway ou docker local  │───────▶│ Caddy :8080 (checa o token)   │
 │ apelidos, fallback,      │ token  │   └▶ Ollama 127.0.0.1:11434   │
 │ chave mestra             │        │        modelos em /workspace  │
 └──────────────────────────┘        └───────────────────────────────┘
        sempre ligado, barato           GPU por hora: liga/desliga
```

## Estrutura

| Pasta | O que é |
|---|---|
| `pod/` | Imagem da GPU: Ollama + Caddy (autenticação) + perfis de modelos por VRAM |
| `pod/perfis/` | `16gb.txt`, `24gb.txt`, `32gb.txt`, `dev.txt`: quais modelos baixar |
| `gateway/` | LiteLLM: roteia nomes (`geral`, `codigo`, `qwen3-14b`...) pro pod |
| `scripts/` | `pod.sh` (liga/desliga RunPod), `testar.sh`, `benchmark.py` |
| `docs/` | [RunPod passo a passo](docs/runpod.md), [catálogo de modelos](docs/modelos.md), [decisões](docs/decisoes.md) |

## Começo rápido (local, sem GPU)

Testa o encanamento todo com um modelo minúsculo em CPU:

```bash
cp .env.example .env          # preencha LITELLM_MASTER_KEY e POD_TOKEN
docker compose up --build     # PERFIL=dev por padrão
scripts/testar.sh teste
```

## Usando de verdade (RunPod)

1. Siga [docs/runpod.md](docs/runpod.md) pra criar o pod (uma vez só).
2. `scripts/pod.sh start`: liga a GPU.
3. Aponte qualquer cliente OpenAI pro gateway:

```python
from openai import OpenAI
cliente = OpenAI(base_url="https://<seu-gateway>/v1", api_key="sk-...")
cliente.chat.completions.create(model="geral", messages=[{"role": "user", "content": "oi"}])
```

4. `scripts/pod.sh stop`: **desliga quando parar de usar** (GPU cobra por hora).

## Nomes de modelo

- **Por função** (recomendado nos apps): `geral`, `codigo`, `visao`, `rapido`.
  Troque o modelo por trás em `gateway/config.yaml` → `model_group_alias`.
- **Por nome**: `qwen3-14b`, `gpt-oss-20b`, `qwen3-coder-30b`... veja [docs/modelos.md](docs/modelos.md).

## Escolher a GPU do PC futuro

Suba o pod num perfil, rode `python3 scripts/benchmark.py` e anote os tok/s.
Repita em 16, 24 e 32 GB. A tabela resultante responde "vale pagar pela 5090?".

---

O projeto anterior deste repo (Safe Trading) está arquivado na branch
[`arquivo-safe-trading`](../../tree/arquivo-safe-trading).
