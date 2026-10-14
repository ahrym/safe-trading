# RunPod: passo a passo

Você faz isso uma vez só. Depois é só `scripts/pod.sh start` / `stop`.

## 0. Gerar segredos

```bash
openssl rand -hex 32   # → POD_TOKEN
echo "sk-$(openssl rand -hex 24)"   # → LITELLM_MASTER_KEY
```

Guarde os dois no `.env` (local) e nas variáveis do Railway (gateway).

## 1. Imagem do pod

O workflow `.github/workflows/pod-image.yml` constrói `pod/` e publica em
`ghcr.io/ahrym/safe-trading/pod:latest` a cada push na `main` que mexa em `pod/`
(ou manualmente em *Actions → imagem-do-pod → Run workflow*).

O pacote no GHCR nasce **privado**. Escolha um:
- **Mais simples:** GitHub → seu perfil → *Packages* → `safe-trading/pod` →
  *Package settings* → *Change visibility* → Public. (A imagem não tem segredo
  nenhum; tokens entram por variável de ambiente.)
- **Privado:** no RunPod, *Settings → Container Registry Auth*, adicione
  `ghcr.io` com seu usuário e um PAT com `read:packages`.

## 2. Armazenamento dos modelos

Modelos pesam 10–20 GB cada. Duas opções:

| | Volume do pod (Community Cloud) | Network Volume (Secure Cloud) |
|---|---|---|
| Preço/hora da GPU | mais barato | ~2x |
| Modelos persistem | sim, mas presos àquela máquina | sim, em qualquer GPU do datacenter |
| Trocar 16→24→32 GB | baixa tudo de novo | reaproveita |
| Ao ligar de novo | pode não ter GPU livre naquela máquina | pega qualquer GPU livre |

**Sugestão:** comece no Community com volume de ~100 GB pra testar. Se ficar
chato (GPU indisponível ao religar, ou querer comparar GPUs), migre pra Network
Volume de ~150 GB. Os dois são montados em `/workspace`, então o pod funciona igual.

## 3. Template

RunPod → *Templates → New Template*:

| Campo | Valor |
|---|---|
| Container Image | `ghcr.io/ahrym/safe-trading/pod:latest` |
| Container Disk | 20 GB |
| Volume Disk / Mount Path | 100 GB em `/workspace` (se não usar Network Volume) |
| Expose HTTP Ports | `8080` |
| Env `POD_TOKEN` | o token do passo 0 (use *Secrets* do RunPod se preferir) |
| Env `PERFIL` | `16gb`, `24gb` ou `32gb` |

## 4. Escolher a GPU

| Perfil | GPUs no RunPod | Simula no PC |
|---|---|---|
| `16gb` | RTX A4000 (16 GB), RTX 4000 Ada (20 GB) | RTX 4060 Ti 16G / 4070 Ti Super / 5070 Ti / 5080 |
| `24gb` | RTX 4090, RTX 3090, L4, A5000 | RTX 3090 / 4090 |
| `32gb` | RTX 5090 | RTX 5090 |

Preços mudam e o Community custa ~metade do Secure. Em 2026 as referências
são ~US$ 0,34/h a 4090 e ~US$ 0,69/h a 5090 (Community); confira em
runpod.io/pricing.

## 5. Primeiro boot

*Deploy* com o template. Nos logs do pod você vê:

```
[quartel] perfil=24gb modelos_em=/workspace/ollama/models
[quartel] ollama no ar
[quartel] pull qwen3:30b
...
[quartel] modelos prontos:
```

O primeiro boot demora (download dos modelos). Os próximos são rápidos.

A URL do pod é `https://<POD_ID>-8080.proxy.runpod.net`. Teste:

```bash
curl https://<POD_ID>-8080.proxy.runpod.net/health                       # ok
curl -H "Authorization: Bearer $POD_TOKEN" https://<POD_ID>-8080.proxy.runpod.net/api/tags
```

## 6. Ligar o gateway no pod

No Railway (novo serviço deste repo, *Root Directory* = `gateway`), variáveis:

```
LITELLM_MASTER_KEY=sk-...
POD_TOKEN=...
POD_URL=https://<POD_ID>-8080.proxy.runpod.net/v1
PORT=4000
```

O `POD_ID` não muda ao parar/ligar o mesmo pod, então isso é configurado uma vez.
Se você apagar e recriar o pod, atualize `POD_URL`.

## 7. Liga/desliga pelo terminal

Preencha `RUNPOD_API_KEY` e `RUNPOD_POD_ID` no `.env`:

```bash
scripts/pod.sh start
scripts/pod.sh status
scripts/pod.sh stop
```

## Pegadinhas

- **Proxy HTTP do RunPod corta requisições sem resposta em ~100 s.** Respostas
  longas sem streaming podem cair. Use `stream: true` nos clientes (Open WebUI,
  SDKs etc. já usam). Se incomodar, exponha a porta como TCP e use o IP público.
- **Primeira chamada a cada modelo** carrega ele na VRAM: 10–60 s. O pod mantém
  1 modelo carregado por vez (como um PC), então alternar modelos tem esse custo.
- **Pod parado não cobra GPU**, mas o volume cobra armazenamento.
- Trocar de perfil: mude `PERFIL` no pod e reinicie. Os modelos antigos ficam no
  volume. Pra apagar algum, use o terminal web do pod: `ollama rm <modelo>`.
