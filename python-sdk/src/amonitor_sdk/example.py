from __future__ import annotations

from typing import Any

from .server import start_server


async def on_action(action: str, params: dict[str, Any]) -> dict[str, Any]:
    if action == "restart":
        return {"ok": True, "message": f"restart accepted with params={params}"}
    return {"ok": False, "message": f"unsupported action: {action}"}


if __name__ == "__main__":
    start_server(host="0.0.0.0", port=8765, target_id="demo-target", action_handler=on_action)
