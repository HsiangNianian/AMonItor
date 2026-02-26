# 部署说明（MVP）

## Agent
1. 配置环境变量：`PANEL_AUTH_TOKEN`、`SDK_AUTH_TOKEN`、`REDIS_ADDR`
2. 启动二进制：`./amonitor-agent`

## Python SDK
1. 在被监控程序侧启动 SDK WS 服务
2. Agent 通过 `target_url` 连接该服务并发送 action

## 验证
- 面板连接 `ws://agent/ws/panel`
- SDK 发送 `heartbeat/event`
- 面板下发 `action`，收到 `action_ack`
