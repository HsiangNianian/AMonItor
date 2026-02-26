from __future__ import annotations

import asyncio
import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=1)
    system: str | None = None
    options: dict[str, Any] | None = None


class ActionRequest(BaseModel):
    action: str
    value: Any | None = None


@dataclass
class RuntimeState:
    service_name: str
    model: str
    ollama_base_url: str
    max_concurrency: int = 1

    pending_requests: int = 0
    in_progress_requests: int = 0
    total_requests: int = 0
    failed_requests: int = 0

    total_token_chars: int = 0
    last_request_token_chars: int = 0

    gpu_utilization: int = -1
    updated_at_ms: int = 0

    clients: set[WebSocket] = field(default_factory=set)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    semaphore: asyncio.Semaphore = field(default_factory=lambda: asyncio.Semaphore(1))

    def snapshot(self) -> dict[str, Any]:
        return {
            "service_name": self.service_name,
            "model": self.model,
            "queue_size": self.pending_requests,
            "in_progress_requests": self.in_progress_requests,
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "total_token_chars": self.total_token_chars,
            "last_request_token_chars": self.last_request_token_chars,
            "gpu_utilization": self.gpu_utilization,
            "max_concurrency": self.max_concurrency,
            "updated_at_ms": self.updated_at_ms,
        }


def read_gpu_utilization_sync() -> int:
    try:
        output = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            timeout=1,
        ).strip()
        if not output:
            return -1
        first_line = output.splitlines()[0].strip()
        return int(first_line)
    except Exception:
        return -1


async def safe_broadcast(state: RuntimeState, message: dict[str, Any]) -> None:
    if not state.clients:
        return

    disconnected: list[WebSocket] = []
    for client in list(state.clients):
        try:
            await client.send_json(message)
        except Exception:
            disconnected.append(client)

    for client in disconnected:
        state.clients.discard(client)


async def broadcast_metrics(state: RuntimeState) -> None:
    await safe_broadcast(state, {"type": "metrics", "payload": state.snapshot()})


async def apply_action(state: RuntimeState, action: str, value: Any) -> dict[str, Any]:
    async with state.lock:
        if action == "reset_metrics":
            state.pending_requests = 0
            state.in_progress_requests = 0
            state.total_requests = 0
            state.failed_requests = 0
            state.total_token_chars = 0
            state.last_request_token_chars = 0
            state.updated_at_ms = int(time.time() * 1000)
            result = {"ok": True, "message": "metrics reset"}
        elif action == "set_max_concurrency":
            try:
                new_value = int(value)
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"invalid value: {exc}") from exc
            if new_value < 1:
                raise HTTPException(status_code=400, detail="max_concurrency must be >= 1")
            state.max_concurrency = new_value
            state.semaphore = asyncio.Semaphore(new_value)
            state.updated_at_ms = int(time.time() * 1000)
            result = {"ok": True, "message": f"max_concurrency set to {new_value}"}
        else:
            raise HTTPException(status_code=400, detail=f"unsupported action: {action}")

    await safe_broadcast(state, {"type": "ack", "payload": {"action": action, **result}})
    await broadcast_metrics(state)
    return result


async def request_ollama_stream(
    state: RuntimeState,
    prompt: str,
    system: str | None,
    options: dict[str, Any] | None,
) -> tuple[str, int]:
    payload: dict[str, Any] = {
        "model": state.model,
        "prompt": prompt,
        "stream": True,
    }
    if system:
        payload["system"] = system
    if options:
        payload["options"] = options

    full_text: list[str] = []
    token_chars = 0

    async with httpx.AsyncClient(timeout=None) as client:
        url = f"{state.ollama_base_url.rstrip('/')}/api/generate"
        async with client.stream("POST", url, json=payload) as response:
            if response.status_code >= 400:
                body = await response.aread()
                raise HTTPException(status_code=502, detail=f"ollama error: {body.decode(errors='ignore')}")

            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                token = item.get("response", "")
                if token:
                    full_text.append(token)
                    token_chars += len(token)

    return "".join(full_text), token_chars


def create_app(service_name: str) -> FastAPI:
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    model = os.getenv("OLLAMA_MODEL", "qwen3:0.6b")
    max_concurrency = int(os.getenv("MAX_CONCURRENCY", "1"))

    state = RuntimeState(
        service_name=service_name,
        model=model,
        ollama_base_url=ollama_base_url,
        max_concurrency=max(1, max_concurrency),
    )
    state.semaphore = asyncio.Semaphore(state.max_concurrency)

    app = FastAPI(title=f"AMonitor Ollama Service - {service_name}")

    stop_event = asyncio.Event()

    @app.on_event("startup")
    async def on_startup() -> None:
        async def gpu_loop() -> None:
            while not stop_event.is_set():
                gpu = await asyncio.to_thread(read_gpu_utilization_sync)
                async with state.lock:
                    state.gpu_utilization = gpu
                    state.updated_at_ms = int(time.time() * 1000)
                await broadcast_metrics(state)
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=2)
                except asyncio.TimeoutError:
                    pass

        app.state.gpu_task = asyncio.create_task(gpu_loop())

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        stop_event.set()
        task = getattr(app.state, "gpu_task", None)
        if task:
            await task

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/metrics")
    async def metrics() -> dict[str, Any]:
        async with state.lock:
            return state.snapshot()

    @app.post("/api/action")
    async def action(request: ActionRequest) -> dict[str, Any]:
        return await apply_action(state, request.action, request.value)

    @app.post("/api/generate")
    async def generate(request: GenerateRequest) -> dict[str, Any]:
        async with state.lock:
            state.pending_requests += 1
            state.updated_at_ms = int(time.time() * 1000)
        await broadcast_metrics(state)

        await state.semaphore.acquire()
        try:
            async with state.lock:
                state.pending_requests = max(0, state.pending_requests - 1)
                state.in_progress_requests += 1
                state.updated_at_ms = int(time.time() * 1000)
            await broadcast_metrics(state)

            text, token_chars = await request_ollama_stream(
                state=state,
                prompt=request.prompt,
                system=request.system,
                options=request.options,
            )

            async with state.lock:
                state.total_requests += 1
                state.total_token_chars += token_chars
                state.last_request_token_chars = token_chars
                state.updated_at_ms = int(time.time() * 1000)

            await broadcast_metrics(state)
            return {
                "service_name": state.service_name,
                "model": state.model,
                "text": text,
                "token_chars": token_chars,
            }
        except HTTPException:
            async with state.lock:
                state.failed_requests += 1
                state.updated_at_ms = int(time.time() * 1000)
            await broadcast_metrics(state)
            raise
        except Exception as exc:
            async with state.lock:
                state.failed_requests += 1
                state.updated_at_ms = int(time.time() * 1000)
            await broadcast_metrics(state)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        finally:
            async with state.lock:
                state.in_progress_requests = max(0, state.in_progress_requests - 1)
                state.updated_at_ms = int(time.time() * 1000)
            state.semaphore.release()
            await broadcast_metrics(state)

    @app.websocket("/ws/monitor")
    async def ws_monitor(websocket: WebSocket) -> None:
        await websocket.accept()
        state.clients.add(websocket)
        await websocket.send_json({"type": "welcome", "payload": state.snapshot()})
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                except json.JSONDecodeError:
                    await websocket.send_json({"type": "error", "payload": {"message": "invalid json"}})
                    continue

                if message.get("type") == "action":
                    action_name = str(message.get("action", ""))
                    action_value = message.get("value")
                    try:
                        result = await apply_action(state, action_name, action_value)
                        await websocket.send_json(
                            {
                                "type": "ack",
                                "payload": {
                                    "action": action_name,
                                    **result,
                                },
                            }
                        )
                    except HTTPException as exc:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "payload": {
                                    "message": exc.detail,
                                },
                            }
                        )
        except WebSocketDisconnect:
            state.clients.discard(websocket)
        except Exception:
            state.clients.discard(websocket)

    return app
