from __future__ import annotations

"""手写协议版最小服务端。

说明：这个文件不依赖 python-sdk，直接用 FastAPI + WebSocket 实现协议处理，
用于对照理解协议细节。若只想快速接入，优先使用 simple_sdk_server_with_sdk.py。
"""

import argparse
import json
import time
from typing import Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect


def _extract_action_and_message(envelope: dict[str, Any]) -> tuple[str, str]:
    payload = envelope.get("payload")
    action = ""
    message = ""

    if isinstance(payload, dict):
        action = str(payload.get("action", ""))
        params = payload.get("params")
        if isinstance(params, dict):
            raw_message = params.get("message")
            if raw_message is None and "value" in params:
                raw_message = params.get("value")
            if raw_message is not None:
                message = str(raw_message)
        elif params is not None:
            message = str(params)

    if not action:
        action = str(envelope.get("action", ""))

    if not message:
        raw_message = envelope.get("message")
        if raw_message is None:
            raw_message = envelope.get("value")
        if raw_message is not None:
            message = str(raw_message)

    return action, message


def create_app(service_name: str) -> FastAPI:
    app = FastAPI(title=f"Simple Python SDK Server - {service_name}")

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "service": service_name}

    @app.websocket("/ws/monitor")
    async def ws_monitor(websocket: WebSocket) -> None:
        await websocket.accept()
        print(f"[SDK] panel/agent connected -> {service_name}")

        try:
            while True:
                text = await websocket.receive_text()
                try:
                    envelope = json.loads(text)
                except json.JSONDecodeError:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "target_id": service_name,
                            "timestamp": int(time.time() * 1000),
                            "payload": {"message": "invalid json"},
                        }
                    )
                    continue

                envelope_type = str(envelope.get("type", ""))
                if envelope_type != "action":
                    print(f"[SDK] ignore non-action: type={envelope_type}")
                    continue

                msg_id = str(envelope.get("msg_id", ""))
                action, message = _extract_action_and_message(envelope)
                print(
                    f"[SDK] recv action target={service_name} msg_id={msg_id} action={action} message={message}"
                )

                await websocket.send_json(
                    {
                        "type": "action_ack",
                        "target_id": service_name,
                        "timestamp": int(time.time() * 1000),
                        "payload": {
                            "action_msg_id": msg_id,
                            "success": True,
                            "message": f"received action={action} message={message}",
                        },
                    }
                )
        except WebSocketDisconnect:
            print(f"[SDK] disconnected -> {service_name}")

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Very simple Python SDK server for AMonitor")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8013)
    parser.add_argument("--service-name", default="ollama-svc-b")
    args = parser.parse_args()

    app = create_app(args.service_name)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
