# Agent（Go）

## 启动
```bash
go run ./cmd/agent
```

## 环境变量
- `AGENT_LISTEN_ADDR`：监听地址，默认 `:8080`
- `PANEL_AUTH_TOKEN`：面板连接 Token（可选）
- `SDK_AUTH_TOKEN`：Agent 连接 SDK 的 Token（可选）
- `REDIS_ADDR`：Redis 地址（可选，未设置时使用内存存储）

## 面板连接地址
- `ws://<agent-host>:8080/ws/panel`
