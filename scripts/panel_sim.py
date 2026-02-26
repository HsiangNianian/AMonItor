import asyncio
import json
import time
import uuid

import websockets

AGENT_WS = "ws://127.0.0.1:8080/ws/panel"
TARGET_URL = "ws://127.0.0.1:8765"


async def main() -> None:
    while True:
        try:
            async with websockets.connect(AGENT_WS) as ws:
                print("[panel] connected", flush=True)
                action = {
                    "msg_id": str(uuid.uuid4()),
                    "trace_id": str(uuid.uuid4()),
                    "type": "action",
                    "target_id": "demo-target",
                    "timestamp": int(time.time() * 1000),
                    "payload": {
                        "action": "restart",
                        "params": {"from": "panel-simulator"},
                        "target_url": TARGET_URL,
                    },
                }
                await ws.send(json.dumps(action, ensure_ascii=False))
                print(f"[panel] action sent {action['msg_id']}", flush=True)
                async for message in ws:
                    print(f"[panel] recv {message}", flush=True)
        except Exception as exc:
            print(f"[panel] reconnecting after error: {exc}", flush=True)
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())
