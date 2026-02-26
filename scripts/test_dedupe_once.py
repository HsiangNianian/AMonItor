import asyncio
import json
import time
import uuid

import websockets


async def wait_ack(ws: websockets.WebSocketClientProtocol, action_msg_id: str, timeout: int = 20) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
        env = json.loads(raw)
        if env.get("type") != "action_ack":
            print("recv", env.get("type"), raw, flush=True)
            continue
        payload = env.get("payload", {})
        print("recv action_ack", raw, flush=True)
        if payload.get("action_msg_id") == action_msg_id:
            return payload
    raise TimeoutError("ack timeout")


async def main() -> None:
    uri = "ws://127.0.0.1:8080/ws/panel"
    msg_id = str(uuid.uuid4())

    first_action = {
        "msg_id": msg_id,
        "trace_id": str(uuid.uuid4()),
        "type": "action",
        "target_id": "demo-target",
        "timestamp": int(time.time() * 1000),
        "payload": {
            "action": "restart",
            "params": {"round": 1},
            "target_url": "ws://127.0.0.1:8765",
        },
    }

    second_action = {
        "msg_id": msg_id,
        "trace_id": str(uuid.uuid4()),
        "type": "action",
        "target_id": "demo-target",
        "timestamp": int(time.time() * 1000),
        "payload": {
            "action": "restart",
            "params": {"round": 2, "expect": "dedupe"},
            "target_url": "ws://127.0.0.1:8765",
        },
    }

    async with websockets.connect(uri) as ws:
        print("send first", msg_id, flush=True)
        await ws.send(json.dumps(first_action, ensure_ascii=False))
        first_ack = await wait_ack(ws, msg_id)
        print("first_ack", json.dumps(first_ack, ensure_ascii=False), flush=True)

        await asyncio.sleep(0.2)

        print("send duplicate", msg_id, flush=True)
        await ws.send(json.dumps(second_action, ensure_ascii=False))
        second_ack = await wait_ack(ws, msg_id)
        print("second_ack", json.dumps(second_ack, ensure_ascii=False), flush=True)

        if "duplicate ignored" in str(second_ack.get("message", "")):
            print("dedupe_ok", flush=True)
        else:
            print("dedupe_unexpected", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
