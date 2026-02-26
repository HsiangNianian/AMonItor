#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
EXAMPLE_DIR="$ROOT_DIR/examples/ollama-fastapi"
CONFIG_PATH="${1:-$EXAMPLE_DIR/config.json}"

if [ ! -f "$CONFIG_PATH" ]; then
  echo "config not found: $CONFIG_PATH"
  exit 1
fi

read_cfg() {
  /usr/bin/python3 - "$CONFIG_PATH" "$1" <<'PY'
import json,sys
from pathlib import Path
cfg = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
key = sys.argv[2]
obj = cfg
for part in key.split('.'):
    if part.isdigit():
        obj = obj[int(part)]
    else:
        obj = obj[part]
print(obj)
PY
}

OLLAMA_BASE_URL="$(read_cfg ollama.base_url)"
OLLAMA_MODEL="$(read_cfg ollama.model)"
AGENT_ENABLED="$(read_cfg agent.enabled)"
AGENT_PANEL_WS="$(read_cfg agent.panel_ws)"
SVC_A_NAME="$(read_cfg services.0.name)"
SVC_A_PORT="$(read_cfg services.0.port)"
SVC_A_CONCURRENCY="$(read_cfg services.0.max_concurrency)"
SVC_B_NAME="$(read_cfg services.1.name)"
SVC_B_PORT="$(read_cfg services.1.port)"
SVC_B_CONCURRENCY="$(read_cfg services.1.max_concurrency)"
PANEL_PORT="$(read_cfg panel.port)"
PANEL_DEFAULT_WS="$(read_cfg panel.defaultWs)"
PANEL_DEFAULT_API_BASE="$(read_cfg panel.defaultApiBase)"
PANEL_TARGETS_JSON="$(/usr/bin/python3 - "$CONFIG_PATH" <<'PY'
import json,sys
from pathlib import Path
cfg = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
targets = cfg.get('agent', {}).get('targets', {})
out = {}
for key, value in targets.items():
  if isinstance(value, str):
    out[key] = {"target_id": key, "target_url": value}
  elif isinstance(value, dict):
    out[key] = {
      "target_id": key,
      "target_url": value.get('ws', ''),
      "api_base": value.get('api_base', '')
    }
print(json.dumps(out, ensure_ascii=False))
PY
  )"

export PANEL_DEFAULT_WS
export VITE_PANEL_DEFAULT_WS="$PANEL_DEFAULT_WS"
export VITE_PANEL_DEFAULT_API_BASE="$PANEL_DEFAULT_API_BASE"
export VITE_PANEL_TARGETS_JSON="$PANEL_TARGETS_JSON"

if [ "$AGENT_ENABLED" = "True" ] || [ "$AGENT_ENABLED" = "true" ]; then
  if [ -n "$AGENT_PANEL_WS" ]; then
    PANEL_DEFAULT_WS="$AGENT_PANEL_WS"
    export PANEL_DEFAULT_WS
    export VITE_PANEL_DEFAULT_WS="$PANEL_DEFAULT_WS"
  fi
fi

unset ALL_PROXY all_proxy HTTP_PROXY HTTPS_PROXY http_proxy https_proxy
export NO_PROXY=127.0.0.1,localhost

PIDS=()
cleanup() {
  for pid in "${PIDS[@]:-}"; do
    if kill -0 "$pid" >/dev/null 2>&1; then
      kill "$pid" >/dev/null 2>&1 || true
    fi
  done
}
trap cleanup EXIT INT TERM

echo "[run_all] prepare python dependencies"
cd "$EXAMPLE_DIR"
uv sync

echo "[run_all] start service-a on :$SVC_A_PORT"
OLLAMA_BASE_URL="$OLLAMA_BASE_URL" OLLAMA_MODEL="$OLLAMA_MODEL" MAX_CONCURRENCY="$SVC_A_CONCURRENCY" \
  uv run uvicorn service_a:app --host 0.0.0.0 --port "$SVC_A_PORT" &
PIDS+=("$!")

echo "[run_all] start service-b on :$SVC_B_PORT"
OLLAMA_BASE_URL="$OLLAMA_BASE_URL" OLLAMA_MODEL="$OLLAMA_MODEL" MAX_CONCURRENCY="$SVC_B_CONCURRENCY" \
  uv run uvicorn service_b:app --host 0.0.0.0 --port "$SVC_B_PORT" &
PIDS+=("$!")

sleep 1

echo "[run_all] prepare panel dependencies"
cd "$EXAMPLE_DIR/panel"
npm install --no-package-lock --registry=https://registry.npmmirror.com >/dev/null

echo "[run_all] panel default ws: $PANEL_DEFAULT_WS"
echo "[run_all] panel default api: $PANEL_DEFAULT_API_BASE"
echo "[run_all] start panel on :$PANEL_PORT"
npm run dev -- --host 0.0.0.0 --port "$PANEL_PORT" &
PIDS+=("$!")

echo "[run_all] done"
echo "  - service-a: http://127.0.0.1:$SVC_A_PORT/docs"
echo "  - service-b: http://127.0.0.1:$SVC_B_PORT/docs"
echo "  - panel:     http://127.0.0.1:$PANEL_PORT"

echo "Press Ctrl+C to stop all services"
wait
