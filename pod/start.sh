#!/usr/bin/env bash
# Sobe Ollama + Caddy e baixa os modelos do perfil escolhido (PERFIL=16gb|24gb|32gb|dev).
set -euo pipefail

: "${POD_TOKEN:?defina POD_TOKEN (o mesmo valor que o gateway usa)}"

# No RunPod, /workspace é o volume persistente: modelos sobrevivem a stop/start.
if [ -z "${OLLAMA_MODELS:-}" ]; then
  if [ -d /workspace ]; then
    export OLLAMA_MODELS=/workspace/ollama/models
  else
    export OLLAMA_MODELS=/root/.ollama/models
  fi
fi
mkdir -p "$OLLAMA_MODELS"

ARQUIVO_PERFIL="/opt/quartel/perfis/${PERFIL}.txt"
if [ ! -f "$ARQUIVO_PERFIL" ]; then
  echo "[quartel] perfil '$PERFIL' não existe. Opções:" $(ls /opt/quartel/perfis | sed 's/\.txt$//') >&2
  exit 1
fi

echo "[quartel] perfil=$PERFIL modelos_em=$OLLAMA_MODELS"

ollama serve &
OLLAMA_PID=$!

until ollama list >/dev/null 2>&1; do sleep 1; done
echo "[quartel] ollama no ar"

caddy run --config /etc/caddy/Caddyfile --adapter caddyfile &
CADDY_PID=$!

# Baixa em segundo plano pra API já responder; modelos já baixados são pulados rápido.
(
  MODELOS=$(sed 's/#.*//' "$ARQUIVO_PERFIL" | xargs)
  for m in $MODELOS ${MODELOS_EXTRA:-}; do
    echo "[quartel] pull $m"
    ollama pull "$m" >/dev/null || echo "[quartel] FALHOU pull $m" >&2
  done
  echo "[quartel] modelos prontos:"
  ollama list
) &

# Se o Ollama ou o Caddy cair, o container cai junto (e o RunPod reinicia).
wait -n "$OLLAMA_PID" "$CADDY_PID"
exit $?
