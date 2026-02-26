from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Footer, Header, Input, RichLog
from websockets.asyncio.client import connect as ws_connect
from websockets.exceptions import ConnectionClosed


@dataclass
class ConnectionState:
    url: str | None = None
    connected: bool = False


class AgentTUIPanel(App[None]):
    TITLE = "AMonitor TUI Panel"
    SUB_TITLE = "Textual WebSocket Panel"

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+l", "clear_log", "Clear Log"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._ws = None
        self._recv_task: asyncio.Task[None] | None = None
        self._state = ConnectionState()

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield RichLog(id="log", wrap=True, markup=False, highlight=True)
            yield Input(
                placeholder="输入命令：/connect ws://127.0.0.1:8080/ws/panel | /disconnect | /chat 你好 | /send {\"type\":\"ping\"}",
                id="command",
            )
        yield Footer()

    def on_mount(self) -> None:
        self._log_info("TUI 已启动。可用命令：/connect /disconnect /chat /send")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        raw = event.value.strip()
        event.input.value = ""
        if not raw:
            return

        await self._handle_command(raw)

    def action_clear_log(self) -> None:
        log = self.query_one("#log", RichLog)
        log.clear()

    async def on_unmount(self) -> None:
        await self._disconnect()

    async def _handle_command(self, raw: str) -> None:
        if raw.startswith("/connect"):
            await self._cmd_connect(raw)
            return

        if raw == "/disconnect":
            await self._disconnect()
            return

        if raw.startswith("/chat"):
            await self._cmd_chat(raw)
            return

        if raw.startswith("/send"):
            await self._cmd_send(raw)
            return

        self._log_error(f"未知命令: {raw}")

    async def _cmd_connect(self, raw: str) -> None:
        parts = raw.split(maxsplit=1)
        if len(parts) != 2 or not parts[1].strip():
            self._log_error("用法: /connect ws://host:port/ws/panel")
            return

        url = parts[1].strip()
        await self._connect(url)

    async def _cmd_chat(self, raw: str) -> None:
        message = raw[len("/chat") :].strip()
        if not message:
            self._log_error("用法: /chat 你的消息")
            return

        payload = {
            "msg_id": str(uuid.uuid4()),
            "trace_id": str(uuid.uuid4()),
            "type": "chat",
            "timestamp": int(time.time() * 1000),
            "payload": {
                "message": message,
            },
        }
        await self._send_json(payload)

    async def _cmd_send(self, raw: str) -> None:
        body = raw[len("/send") :].strip()
        if not body:
            self._log_error("用法: /send {\"type\":\"action\",...}")
            return

        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            self._log_error(f"JSON 解析失败: {exc}")
            return

        compact = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        await self._send_text(compact)

    async def _connect(self, url: str) -> None:
        await self._disconnect()
        try:
            self._ws = await ws_connect(url)
        except Exception as exc:
            self._log_error(f"连接失败: {url} ({exc})")
            return

        self._state.url = url
        self._state.connected = True
        self._log_info(f"已连接: {url}")
        self._recv_task = asyncio.create_task(self._recv_loop())

    async def _disconnect(self) -> None:
        if self._recv_task:
            self._recv_task.cancel()
            try:
                await self._recv_task
            except asyncio.CancelledError:
                pass
            self._recv_task = None

        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None

        if self._state.connected:
            self._log_info("连接已断开")

        self._state = ConnectionState()

    async def _recv_loop(self) -> None:
        try:
            while self._ws is not None:
                message = await self._ws.recv()
                self._log_recv(message)
        except ConnectionClosed as exc:
            self._log_warn(f"连接关闭: code={exc.code} reason={exc.reason}")
        except asyncio.CancelledError:
            return
        except Exception as exc:
            self._log_error(f"接收异常: {exc}")
        finally:
            await self._disconnect()

    async def _send_json(self, payload: dict) -> None:
        compact = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        await self._send_text(compact)

    async def _send_text(self, body: str) -> None:
        if self._ws is None or not self._state.connected:
            self._log_error("尚未连接，请先执行 /connect")
            return

        try:
            await self._ws.send(body)
            self._log_send(body)
        except Exception as exc:
            self._log_error(f"发送失败: {exc}")

    def _log_info(self, message: str) -> None:
        self.query_one("#log", RichLog).write(f"[{self._now()}] [INFO] {message}")

    def _log_warn(self, message: str) -> None:
        self.query_one("#log", RichLog).write(f"[{self._now()}] [WARN] {message}")

    def _log_error(self, message: str) -> None:
        self.query_one("#log", RichLog).write(f"[{self._now()}] [ERROR] {message}")

    def _log_send(self, body: str) -> None:
        self.query_one("#log", RichLog).write(f"[{self._now()}] [SEND] {body}")

    def _log_recv(self, body: str) -> None:
        self.query_one("#log", RichLog).write(f"[{self._now()}] [RECV] {body}")

    @staticmethod
    def _now() -> str:
        return time.strftime("%H:%M:%S")


def main() -> None:
    AgentTUIPanel().run()


if __name__ == "__main__":
    main()
