# E2E 最小联调

## 1. 启动 Agent
```bash
cd agent
go run ./cmd/agent
```

## 2. 启动 SDK 服务
```bash
cd python-sdk
uv sync
uv run python -m amonitor_sdk.example
```

## 3. 连接面板
- 连接 `ws://127.0.0.1:8080/ws/panel`
- 发送 `action` 消息，payload 中提供 `target_url`（例如 `ws://127.0.0.1:8765`）

## 4. 预期结果
- 面板收到 SDK 的 `heartbeat`
- action 被 SDK 处理后回传 `action_ack`
