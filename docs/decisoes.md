# Decisões

## Ollama em vez de vLLM

O objetivo é rodar no RunPod **exatamente** o que vai rodar no PC de 16–32 GB.

- **Ollama**: modelos quantizados (GGUF) que cabem em GPU de consumidor, troca
  de modelo sob demanda numa GPU só, mesmo comando no RunPod e em casa.
- **vLLM**: mais throughput com muitos usuários simultâneos, mas prende um
  modelo por GPU, prefere pesos maiores (FP16/AWQ) e pede mais VRAM pro mesmo
  modelo. Faz sentido pra servir um modelo fixo pra muita gente, que não é o caso.

Se um dia precisar de vLLM pra um modelo específico, ele também expõe API
OpenAI: vira só mais um `api_base` no `gateway/config.yaml`.

## Gateway LiteLLM separado do pod

- O pod liga e desliga (custo); o gateway fica sempre no ar com URL fixa.
- Apps usam nomes estáveis (`geral`, `codigo`) e uma chave só; trocar o modelo
  ou o backend (RunPod → PC local → outro provedor) é editar um YAML.
- Fallback automático pra um modelo menor quando o maior falha.
- Próximo passo possível: chaves por app e controle de gasto (LiteLLM com
  Postgres; dá pra usar um Supabase).

## Caddy na frente do Ollama

O Ollama não tem autenticação. A URL de proxy do RunPod é pública, então sem
isso qualquer um que achasse a URL usaria sua GPU. O Caddy exige
`Authorization: Bearer $POD_TOKEN` e deixa só `/health` aberto. O Ollama escuta
apenas em `127.0.0.1`.

## Um modelo carregado por vez

`OLLAMA_MAX_LOADED_MODELS=1` e `OLLAMA_NUM_PARALLEL=1` simulam um PC com uma
GPU. Os números do `benchmark.py` ficam comparáveis com o que você vai ter em casa.
