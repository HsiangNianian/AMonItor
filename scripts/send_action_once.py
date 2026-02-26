import asyncio
import json
import time
import uuid

import websockets


async def main() -> None:
    uri = "ws://127.0.0.1:8080/ws/panel"
    async with websockets.connect(uri) as ws:
        msg_id = str(uuid.uuid4())
        action = {
            "msg_id": msg_id,
            "trace_id": str(uuid.uuid4()),
            "type": "action",
            "target_id": "demo-target",
            "timestamp": int(time.time() * 1000),
            "payload": {
                "action": "restart",
                "params": {"from": "send-action-once"},
                "target_url": "ws://127.0.0.1:8765",
            },
        }
        await ws.send(json.dumps(action, ensure_ascii=False))
        print("sent", msg_id, flush=True)

        deadline = time.time() + 20
        while time.time() < deadline:
            raw = await asyncio.wait_for(ws.recv(), timeout=20)
            env = json.loads(raw)
            print("recv", env.get("type"), raw, flush=True)
            if env.get("type") != "action_ack":
                continue
            payload = env.get("payload", {})
            if payload.get("action_msg_id") == msg_id:
                print("ack_matched", json.dumps(payload, ensure_ascii=False), flush=True)
                return

        print("ack_timeout", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
