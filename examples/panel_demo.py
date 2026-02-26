from __future__ import annotations

import argparse
import asyncio
import json
import time
import uuid
from typing import Any

import websockets


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run panel demo client")
    parser.add_argument("--panel-ws", required=True)
    parser.add_argument("--action-name", default="restart")
    parser.add_argument("--send-actions", action="store_true")
    parser.add_argument("--targets-json", required=True)
    return parser


async def send_initial_actions(
    websocket: Any,
    action_name: str,
    targets: list[dict],
) -> None:
    for target in targets:
        message_id = str(uuid.uuid4())
        envelope = {
            "msg_id": message_id,
            "trace_id": str(uuid.uuid4()),
            "type": "action",
            "target_id": target["target_id"],
            "timestamp": int(time.time() * 1000),
            "payload": {
                "action": action_name,
                "params": {"source": "panel-demo", "sdk": target["name"]},
                "target_url": f"ws://{target['host']}:{target['port']}",
            },
        }
        await websocket.send(json.dumps(envelope, ensure_ascii=False))
        print(f"[panel] action sent target={target['target_id']} msg_id={message_id}", flush=True)


async def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    targets = json.loads(args.targets_json)

    while True:
        try:
            async with websockets.connect(args.panel_ws) as websocket:
                print(f"[panel] connected: {args.panel_ws}", flush=True)
                if args.send_actions:
                    await send_initial_actions(websocket, args.action_name, targets)

                async for message in websocket:
                    print(f"[panel] recv {message}", flush=True)
        except Exception as exc:
            print(f"[panel] reconnect in 2s due to: {exc}", flush=True)
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())
