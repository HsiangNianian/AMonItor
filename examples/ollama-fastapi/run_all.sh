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
import json,re,sys
from pathlib import Path

def load_json5(path: str):
  text = Path(path).read_text(encoding='utf-8')
  out = []
  i = 0
  in_str = False
  quote = ''
  escaped = False
  in_line_comment = False
  in_block_comment = False

  while i < len(text):
    ch = text[i]
    nxt = text[i + 1] if i + 1 < len(text) else ''

    if in_line_comment:
      if ch == '\n':
        in_line_comment = False
        out.append(ch)
      i += 1
      continue

    if in_block_comment:
      if ch == '*' and nxt == '/':
        in_block_comment = False
        i += 2
        continue
      i += 1
      continue

    if in_str:
      out.append(ch)
      if escaped:
        escaped = False
      elif ch == '\\':
        escaped = True
      elif ch == quote:
        in_str = False
      i += 1
      continue

    if ch == '/' and nxt == '/':
      in_line_comment = True
      i += 2
      continue

    if ch == '/' and nxt == '*':
      in_block_comment = True
      i += 2
      continue

    if ch in ('"', "'"):
      in_str = True
      quote = ch
      out.append(ch)
      i += 1
      continue

    out.append(ch)
    i += 1

  cleaned = ''.join(out)
  cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
  return json.loads(cleaned)

cfg = load_json5(sys.argv[1])
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
AGENT_LISTEN_ADDR="$(read_cfg server.listen_addr)"
AGENT_PANEL_PATH="$(read_cfg server.panel_path)"
SVC_A_NAME="$(read_cfg services.0.name)"
SVC_A_PORT="$(read_cfg services.0.port)"
SVC_A_CONCURRENCY="$(read_cfg services.0.max_concurrency)"
SVC_B_NAME="$(read_cfg services.1.name)"
SVC_B_PORT="$(read_cfg services.1.port)"
SVC_B_CONCURRENCY="$(read_cfg services.1.max_concurrency)"
PANEL_PORT="$(read_cfg panel.port)"
PANEL_DEFAULT_API_BASE="$(read_cfg panel.defaultApiBase)"
PANEL_DEFAULT_WS="$(/usr/bin/python3 - "$CONFIG_PATH" <<'PY'
import json,re,sys
from pathlib import Path

def load_json5(path: str):
  text = Path(path).read_text(encoding='utf-8')
  out = []
  i = 0
  in_str = False
  quote = ''
  escaped = False
  in_line_comment = False
  in_block_comment = False

  while i < len(text):
    ch = text[i]
    nxt = text[i + 1] if i + 1 < len(text) else ''

    if in_line_comment:
      if ch == '\n':
        in_line_comment = False
        out.append(ch)
      i += 1
      continue

    if in_block_comment:
      if ch == '*' and nxt == '/':
        in_block_comment = False
        i += 2
        continue
      i += 1
      continue

    if in_str:
      out.append(ch)
      if escaped:
        escaped = False
      elif ch == '\\':
        escaped = True
      elif ch == quote:
        in_str = False
      i += 1
      continue

    if ch == '/' and nxt == '/':
      in_line_comment = True
      i += 2
      continue

    if ch == '/' and nxt == '*':
      in_block_comment = True
      i += 2
      continue

    if ch in ('"', "'"):
      in_str = True
      quote = ch
      out.append(ch)
      i += 1
      continue

    out.append(ch)
    i += 1

  cleaned = ''.join(out)
  cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
  return json.loads(cleaned)

cfg = load_json5(sys.argv[1])
server = cfg.get('server', {})
listen_addr = str(server.get('listen_addr', '')).strip()
panel_path = str(server.get('panel_path', '/ws/panel')).strip() or '/ws/panel'

if not listen_addr:
  raise SystemExit('')

if listen_addr.startswith(':'):
  listen_addr = '127.0.0.1' + listen_addr
elif listen_addr.startswith('0.0.0.0:'):
  listen_addr = '127.0.0.1:' + listen_addr.split(':', 1)[1]

if not panel_path.startswith('/'):
  panel_path = '/' + panel_path

print(f"ws://{listen_addr}{panel_path}")
PY
  )"
PANEL_TARGETS_JSON="$(/usr/bin/python3 - "$CONFIG_PATH" <<'PY'
import json,re,sys
from urllib.parse import urlparse
from pathlib import Path

def load_json5(path: str):
  text = Path(path).read_text(encoding='utf-8')
  out = []
  i = 0
  in_str = False
  quote = ''
  escaped = False
  in_line_comment = False
  in_block_comment = False

  while i < len(text):
    ch = text[i]
    nxt = text[i + 1] if i + 1 < len(text) else ''

    if in_line_comment:
      if ch == '\n':
        in_line_comment = False
        out.append(ch)
      i += 1
      continue

    if in_block_comment:
      if ch == '*' and nxt == '/':
        in_block_comment = False
        i += 2
        continue
      i += 1
      continue

    if in_str:
      out.append(ch)
      if escaped:
        escaped = False
      elif ch == '\\':
        escaped = True
      elif ch == quote:
        in_str = False
      i += 1
      continue

    if ch == '/' and nxt == '/':
      in_line_comment = True
      i += 2
      continue

    if ch == '/' and nxt == '*':
      in_block_comment = True
      i += 2
      continue

    if ch in ('"', "'"):
      in_str = True
      quote = ch
      out.append(ch)
      i += 1
      continue

    out.append(ch)
    i += 1

  cleaned = ''.join(out)
  cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
  return json.loads(cleaned)

cfg = load_json5(sys.argv[1])

def ws_to_http_base(raw_url: str) -> str:
  parsed = urlparse(raw_url)
  if not parsed.scheme or not parsed.netloc:
    return ''
  scheme = 'https' if parsed.scheme == 'wss' else 'http'
  return f"{scheme}://{parsed.netloc}"

routes = cfg.get('routes', [])
out = {}
for item in routes:
  if not isinstance(item, dict):
    continue
  target_id = str(item.get('target_id', '')).strip()
  target_url = str(item.get('url', '')).strip()
  if not target_id or not target_url:
    continue
  out[target_id] = {
    "target_id": target_id,
    "target_url": target_url,
    "api_base": ws_to_http_base(target_url)
  }
print(json.dumps(out, ensure_ascii=False))
PY
  )"

export VITE_PANEL_DEFAULT_API_BASE="$PANEL_DEFAULT_API_BASE"
export VITE_PANEL_TARGETS_JSON="$PANEL_TARGETS_JSON"

if [ -z "$PANEL_DEFAULT_WS" ]; then
  echo "config error: server.listen_addr/server.panel_path is required"
  exit 1
fi
export PANEL_DEFAULT_WS
export VITE_PANEL_DEFAULT_WS="$PANEL_DEFAULT_WS"

unset ALL_PROXY all_proxy HTTP_PROXY HTTPS_PROXY http_proxy https_proxy
export NO_PROXY=127.0.0.1,localhost
unset VIRTUAL_ENV

UV_PY_RUN=(uv run --project "$ROOT_DIR/python-sdk" --with httpx)

PIDS=()
cleanup() {
  for pid in "${PIDS[@]:-}"; do
    if kill -0 "$pid" >/dev/null 2>&1; then
      kill "$pid" >/dev/null 2>&1 || true
    fi
  done
}
trap cleanup EXIT INT TERM

echo "[run_all] use python-sdk uv project env"
cd "$EXAMPLE_DIR"

echo "[run_all] start service-a on :$SVC_A_PORT"
OLLAMA_BASE_URL="$OLLAMA_BASE_URL" OLLAMA_MODEL="$OLLAMA_MODEL" MAX_CONCURRENCY="$SVC_A_CONCURRENCY" \
  "${UV_PY_RUN[@]}" uvicorn service_a:app --host 0.0.0.0 --port "$SVC_A_PORT" &
PIDS+=("$!")

echo "[run_all] start service-b on :$SVC_B_PORT"
OLLAMA_BASE_URL="$OLLAMA_BASE_URL" OLLAMA_MODEL="$OLLAMA_MODEL" MAX_CONCURRENCY="$SVC_B_CONCURRENCY" \
  "${UV_PY_RUN[@]}" uvicorn service_b:app --host 0.0.0.0 --port "$SVC_B_PORT" &
PIDS+=("$!")

sleep 1

echo "[run_all] check service health"
if ! curl -fsS "http://127.0.0.1:$SVC_A_PORT/healthz" >/dev/null; then
  echo "service-a health check failed"
  exit 1
fi
if ! curl -fsS "http://127.0.0.1:$SVC_B_PORT/healthz" >/dev/null; then
  echo "service-b health check failed"
  exit 1
fi

echo "[run_all] prepare panel dependencies"
cd "$EXAMPLE_DIR/panel"
rm -rf node_modules
npm install --no-package-lock --legacy-peer-deps --registry=https://registry.npmmirror.com >/dev/null

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
