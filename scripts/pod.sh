#!/usr/bin/env bash
# Liga/desliga o pod no RunPod (GPU só cobra enquanto ligado).
# uso: scripts/pod.sh start|stop|status
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -f .env ]; then set -a; . ./.env; set +a; fi

: "${RUNPOD_API_KEY:?defina RUNPOD_API_KEY no .env}"
: "${RUNPOD_POD_ID:?defina RUNPOD_POD_ID no .env}"

API="https://rest.runpod.io/v1/pods/$RUNPOD_POD_ID"
AUTH="Authorization: Bearer $RUNPOD_API_KEY"

case "${1:-status}" in
  start)  curl -fsS -X POST -H "$AUTH" "$API/start" >/dev/null && echo "pod ligando (os modelos levam ~1 min pra carregar)" ;;
  stop)   curl -fsS -X POST -H "$AUTH" "$API/stop"  >/dev/null && echo "pod desligado" ;;
  status) curl -fsS -H "$AUTH" "$API" | python3 -c '
import json, sys
p = json.load(sys.stdin)
for k in ("name", "desiredStatus", "costPerHr", "gpu", "lastStatusChange"):
    if p.get(k) is not None:
        print(f"{k:>16}: {p[k]}")
' ;;
  *) echo "uso: $0 start|stop|status" >&2; exit 1 ;;
esac
