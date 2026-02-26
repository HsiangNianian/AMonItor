# AMonitor Python SDK

## 目标

Python SDK 运行在被监控进程一侧，提供：

- 启动 WS 服务端，接收 Agent 下发的 `action`
- 周期发送 `heartbeat`
- 向 Agent 发送 `event`
- 返回 `action_ack`

## 安装与运行（uv）

```bash
uv sync
uv run python -m amonitor_sdk.example
```

## 最小示例

```python
from amonitor_sdk.server import start_server

async def on_action(action: str, params: dict):
    if action == "restart":
        return {"ok": True, "message": "restarted"}
    return {"ok": False, "message": "unknown action"}

start_server(host="0.0.0.0", port=8765, target_id="server-a", action_handler=on_action)
```

## 交互说明

1. Agent 连接 SDK WS 地址。
2. SDK 启动后按间隔发送 `heartbeat`。
3. SDK 收到 `action` 后执行 `action_handler`。
4. SDK 将执行结果封装为 `action_ack` 返回。

## 开发规范（Python）

### 代码风格

- Python 版本：`>=3.11`
- 强制类型注解，公开 API 需要完整函数签名。
- 不使用单字母变量名（循环计数器除外）。
- 异步代码优先使用 `async/await`，避免阻塞调用。

### 项目结构

- `src/amonitor_sdk/server.py`：服务端与消息处理主逻辑
- `src/amonitor_sdk/models.py`：协议模型
- `src/amonitor_sdk/example.py`：最小可运行示例

### 依赖与命令

- 新增依赖后执行 `uv sync`
- 运行检查：`uv run --with dev ruff check src`
- 本地 smoke：`uv run python -c "import amonitor_sdk"`

### 测试与验收

- 单模块测试：`cd .. && make test`
- 幂等验收：`cd .. && RUN_E2E=1 make test`

### 协议约束

- 必须携带 `msg_id`、`type`、`timestamp`
- `payload` 保持业务透传，SDK 不做业务字段裁剪
- `action_ack.payload.action_msg_id` 必须等于原 action 的 `msg_id`
