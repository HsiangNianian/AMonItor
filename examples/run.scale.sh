#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COUNT="${SDK_COUNT:-10}"
START_PORT="${SDK_START_PORT:-8901}"
HEARTBEAT_INTERVAL="${SDK_HEARTBEAT_INTERVAL:-5}"
ACTION_NAME="${ACTION_NAME:-restart}"
AGENT_LISTEN_ADDR="${AGENT_LISTEN_ADDR:-127.0.0.1:8080}"
PANEL_WS="${PANEL_WS:-ws://127.0.0.1:8080/ws/panel}"
TMP_CONFIG="$ROOT_DIR/examples/.generated.scale.config.json"

cd "$ROOT_DIR/python-sdk"
uv sync

env -u ALL_PROXY -u all_proxy -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy NO_PROXY=127.0.0.1,localhost \
  uv run python ../examples/gen_scale_config.py \
    --output "$TMP_CONFIG" \
    --count "$COUNT" \
    --start-port "$START_PORT" \
    --heartbeat-interval "$HEARTBEAT_INTERVAL" \
    --action-name "$ACTION_NAME" \
    --agent-listen-addr "$AGENT_LISTEN_ADDR" \
    --panel-ws "$PANEL_WS"

env -u ALL_PROXY -u all_proxy -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy NO_PROXY=127.0.0.1,localhost \
  uv run python ../examples/run_demo.py --config "$TMP_CONFIG"
