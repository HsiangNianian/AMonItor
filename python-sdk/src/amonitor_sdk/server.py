from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosed

ActionHandler = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]


class SDKServer:
    def __init__(
        self,
        host: str,
        port: int,
        target_id: str,
        action_handler: ActionHandler,
        auth_token: str | None = None,
        heartbeat_interval: int = 10,
    ) -> None:
        self.host = host
        self.port = port
        self.target_id = target_id
        self.action_handler = action_handler
        self.auth_token = auth_token
        self.heartbeat_interval = heartbeat_interval
        self._connections: set[Any] = set()

    async def run(self) -> None:
        async with websockets.serve(self._handler, self.host, self.port):
            await asyncio.Future()

    async def _handler(self, websocket: Any) -> None:
        if self.auth_token:
            auth = websocket.request.headers.get("Authorization", "")
            if auth != f"Bearer {self.auth_token}":
                await websocket.close(code=4401, reason="unauthorized")
                return

        self._connections.add(websocket)
        hb_task = asyncio.create_task(self._heartbeat_loop(websocket))
        try:
            async for message in websocket:
                await self._on_message(websocket, message)
        except ConnectionClosed:
            return
        finally:
            hb_task.cancel()
            self._connections.discard(websocket)

    async def _heartbeat_loop(self, websocket: Any) -> None:
        while True:
            envelope = {
                "msg_id": str(uuid.uuid4()),
                "type": "heartbeat",
                "target_id": self.target_id,
                "timestamp": int(time.time() * 1000),
                "payload": {"target_id": self.target_id, "status": "up"},
            }
            await websocket.send(json.dumps(envelope, ensure_ascii=False))
            await asyncio.sleep(self.heartbeat_interval)

    async def _on_message(self, websocket: Any, message: str) -> None:
        envelope = json.loads(message)
        msg_type = envelope.get("type")
        if msg_type != "action":
            return

        payload = envelope.get("payload", {})
        action = payload.get("action", "")
        params = payload.get("params", {})

        result = await self.action_handler(action, params)
        ack = {
            "msg_id": str(uuid.uuid4()),
            "type": "action_ack",
            "target_id": self.target_id,
            "timestamp": int(time.time() * 1000),
            "payload": {
                "action_msg_id": envelope.get("msg_id", ""),
                "success": bool(result.get("ok", False)),
                "message": str(result.get("message", "")),
            },
        }
        await websocket.send(json.dumps(ack, ensure_ascii=False))

    async def emit_event(self, event_name: str, data: dict[str, Any]) -> None:
        if not self._connections:
            return
        envelope = {
            "msg_id": str(uuid.uuid4()),
            "type": "event",
            "target_id": self.target_id,
            "timestamp": int(time.time() * 1000),
            "payload": {
                "target_id": self.target_id,
                "event_name": event_name,
                "data": data,
            },
        }
        raw = json.dumps(envelope, ensure_ascii=False)
        await asyncio.gather(*(ws.send(raw) for ws in self._connections), return_exceptions=True)


def start_server(
    host: str,
    port: int,
    target_id: str,
    action_handler: ActionHandler,
    auth_token: str | None = None,
    heartbeat_interval: int = 10,
) -> None:
    server = SDKServer(
        host=host,
        port=port,
        target_id=target_id,
        action_handler=action_handler,
        auth_token=auth_token,
        heartbeat_interval=heartbeat_interval,
    )
    asyncio.run(server.run())
