# Agent（Go）

## 启动

```bash
go run ./cmd/agent
```

使用配置文件：

```bash
go run ./cmd/agent --config ./config.example.json
```

命令行覆盖配置：

```bash
go run ./cmd/agent \
  --config ./config.example.json \
  --listen-addr :8088 \
  --panel-path /ws/panel \
  --panel-token panel-secret \
  --sdk-token sdk-secret \
  --route ollama-svc-a=ws://10.0.0.21:8011/ws/monitor \
  --upstream ollama-svc-a=ws://10.0.0.21:8011/ws/monitor \
  --upstream-token ollama-svc-a=sdk-secret
```

## 配置文件

参考 `config.example.json`：

- `server`：Agent 作为 WS 服务端时的配置
  - `enabled`：是否启用服务端模式
  - `listen_addr` 或 `host+port`
  - `panel_path`：面板连接路径（默认 `/ws/panel`）
  - `panel_auth_token`：面板鉴权 Token
  - `default_sdk_auth_token`：Agent 拨号 SDK 时默认 Token
- `store.redis_addr`：可选 Redis
- `routes`：路由表（`target_id -> url + auth_token`）
- `client`：Agent 作为 WS 客户端主动连接多服务
  - `enabled`
  - `reconnect_interval_seconds`
  - `upstreams[]`：多个上游（`target_id/url/auth_token`）

## 环境变量

- `AGENT_LISTEN_ADDR`：监听地址，默认 `:8080`
- `PANEL_AUTH_TOKEN`：面板连接 Token（可选）
- `SDK_AUTH_TOKEN`：Agent 连接 SDK 的 Token（可选）
- `REDIS_ADDR`：Redis 地址（可选，未设置时使用内存存储）

## 面板连接地址

- `ws://<agent-host>:8080/ws/panel`
