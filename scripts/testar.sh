#!/usr/bin/env bash
# Teste rápido do gateway: lista modelos e manda uma pergunta.
# uso: scripts/testar.sh [modelo]      (padrão: rapido)
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -f .env ]; then set -a; . ./.env; set +a; fi

GATEWAY_URL="${GATEWAY_URL:-http://localhost:4000}"
: "${LITELLM_MASTER_KEY:?defina LITELLM_MASTER_KEY no .env}"
MODELO="${1:-rapido}"
AUTH="Authorization: Bearer $LITELLM_MASTER_KEY"

echo "== modelos em $GATEWAY_URL"
curl -fsS -H "$AUTH" "$GATEWAY_URL/v1/models" \
  | python3 -c 'import json,sys; print("  " + "\n  ".join(m["id"] for m in json.load(sys.stdin)["data"]))'

echo "== $MODELO responde:"
curl -fsS -H "$AUTH" -H "Content-Type: application/json" "$GATEWAY_URL/v1/chat/completions" \
  -d "{\"model\": \"$MODELO\", \"messages\": [{\"role\": \"user\", \"content\": \"Em uma frase: quem é você?\"}]}" \
  | python3 -c 'import json,sys; print("  " + json.load(sys.stdin)["choices"][0]["message"]["content"].strip())'
