# AMonitor Python SDK

## 使用 uv
```bash
uv sync
uv run python -m amonitor_sdk.example
```

## 最小示例
```python
from amonitor_sdk.server import start_server

async def on_action(action: str, params: dict):
    if action == "restart":
        return {"ok": True, "message": "restarted"}
    return {"ok": False, "message": "unknown action"}

start_server(host="0.0.0.0", port=8765, target_id="server-a", action_handler=on_action)
```
