# Catálogo de modelos

Tamanhos são do download padrão do Ollama (quantização Q4_K_M ou MXFP4).
Na VRAM some ~1–4 GB de contexto (KV cache) por cima. Regra de bolso:
**arquivo + 2 GB ≤ VRAM** cabe confortável com 16k de contexto.

| Nome no gateway | Tag Ollama | Tamanho | Bom pra | 16 | 24 | 32 |
|---|---|---|---|:-:|:-:|:-:|
| `qwen3-14b` | `qwen3:14b` | ~9 GB | geral, PT-BR, tool calling | ✅ | ✅ | ✅ |
| `gemma3-12b` | `gemma3:12b` | ~8 GB | geral + imagens | ✅ | ✅ | ✅ |
| `qwen2.5-coder-14b` | `qwen2.5-coder:14b` | ~9 GB | código | ✅ | ✅ | ✅ |
| `gpt-oss-20b` | `gpt-oss:20b` | ~14 GB | raciocínio, MoE rápido | ✅ | ✅ | ✅ |
| `devstral-24b` | `devstral:24b` | ~14 GB | agente de código | ⚠️ | ✅ | ✅ |
| `mistral-small-24b` | `mistral-small3.2:24b` | ~15 GB | geral + imagens | ⚠️ | ✅ | ✅ |
| `gemma3-27b` | `gemma3:27b` | ~17 GB | geral + imagens | ❌ | ✅ | ✅ |
| `qwen3-30b` | `qwen3:30b` | ~19 GB | geral, MoE (3B ativos), muito rápido | ❌ | ✅ | ✅ |
| `qwen3-coder-30b` | `qwen3-coder:30b` | ~19 GB | código / agentes, MoE | ❌ | ✅ | ✅ |
| `qwen3-32b` | `qwen3:32b` | ~20 GB | denso, mais "pensante" | ❌ | ⚠️ | ✅ |

✅ cabe folgado · ⚠️ cabe com pouco contexto · ❌ não cabe na GPU (o Ollama
joga parte pra CPU e fica muito lento)

## Famílias mais novas

Em 2026 saíram gerações novas (ex.: Qwen 3.6 35B-A3B, Gemma 4 31B) que guias
recomendam pra 24–32 GB. As tags acima são as que eu tinha certeza que existem.
Antes de adotar uma nova, confira a tag exata em https://ollama.com/library,
adicione no perfil e no `gateway/config.yaml` e compare no `benchmark.py`.

## Adicionar um modelo

1. `pod/perfis/<perfil>.txt` → uma linha com a tag do Ollama.
2. `gateway/config.yaml` → um bloco em `model_list`:
   ```yaml
   - model_name: nome-amigavel
     litellm_params: { model: openai/<tag-ollama>, api_base: os.environ/POD_URL, api_key: os.environ/POD_TOKEN }
   ```
3. Reinicie o pod (baixa o modelo) e faça redeploy do gateway.

Pra testar uma tag sem mexer em nada: variável `MODELOS_EXTRA="tag1 tag2"` no pod.
