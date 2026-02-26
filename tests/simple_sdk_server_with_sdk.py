from __future__ import annotations

"""SDK 版最小服务端。

基于 amonitor_sdk.start_server 启动，只保留 action 业务回调。
推荐优先使用本文件进行联调。

最简启动：

python [simple_sdk_server_with_sdk.py](http://_vscodecontentref_/4) --host 127.0.0.1 --port 8013 --service-name ollama-svc-b
TUI 里发送示例：

/send {"msg_id":"m-2001","trace_id":"t-2001","type":"action","target_id":"ollama-svc-b","timestamp":1760000000000,"payload":{"action":"print_message","params":{"message":"hello sdk"}}}
你会在这个 SDK 服务端终端看到：

[SDK] recv action=print_message message=hello sdk
"""

import argparse
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SDK_SRC = PROJECT_ROOT / "python-sdk" / "src"
if str(SDK_SRC) not in sys.path:
    sys.path.insert(0, str(SDK_SRC))

from amonitor_sdk import start_server


async def on_action(action: str, params: dict[str, Any]) -> dict[str, Any]:
    message = ""

    if isinstance(params, dict):
        raw = params.get("message")
        if raw is None and "value" in params:
            raw = params.get("value")
        if raw is not None:
            message = str(raw)

    print(f"[SDK] recv action={action} message={message}")
    return {"ok": True, "message": f"received action={action} message={message}"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple SDK server powered by amonitor-sdk")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8012)
    parser.add_argument("--service-name", default="ollama-svc-b")
    parser.add_argument("--auth-token", default="")
    parser.add_argument("--heartbeat-interval", type=int, default=2)
    args = parser.parse_args()

    start_server(
        host=args.host,
        port=args.port,
        target_id=args.service_name,
        action_handler=on_action,
        auth_token=args.auth_token or None,
        heartbeat_interval=max(1, args.heartbeat_interval),
    )


if __name__ == "__main__":
    main()

