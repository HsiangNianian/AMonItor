# AMonitor

AMonitor 是一个 Monorepo 监控系统，包含：

- Go Agent（二进制中台）
- Python SDK（被监控程序侧）
- 协议定义（Protobuf）

## 仓库结构

- `agent/` Go Agent
- `python-sdk/` Python SDK (`uv`)
- `proto/` 协议定义
- `docs/` 设计与使用文档
- `scripts/` 构建与工具脚本
- `tests/e2e/` 端到端联调说明

## 运行环境

- Go >= 1.23
- Python >= 3.11
- `uv`（Python 依赖与构建管理）
- 可选：Redis（多实例路由/幂等状态）

## 快速使用

1. 启动 Agent

```bash
cd agent
go run ./cmd/agent
```

2. 启动 Python SDK 示例服务

```bash
cd python-sdk
uv sync
uv run python -m amonitor_sdk.example
```

3. 启动面板模拟客户端（会自动下发 action 并打印回包）

```bash
cd python-sdk
uv run python ../scripts/panel_sim.py
```

4. 一次性发送 action 并等待 ACK

```bash
cd python-sdk
uv run python ../scripts/send_action_once.py
```

5. 验证幂等（同一 `msg_id` 发送两次）

```bash
cd python-sdk
uv run python ../scripts/test_dedupe_once.py
```

## 交互过程

### 链路 A：监控数据上行

1. SDK 在被监控服务侧启动 WS 服务端。
2. Agent 作为客户端连接 SDK。
3. SDK 周期发送 `heartbeat`/`event` 给 Agent。
4. Agent 原样转发到监控面板连接。

### 链路 B：控制指令下行

1. 面板作为客户端连接 Agent（`/ws/panel`）。
2. 面板发送 `action`（含 `msg_id` 和 `target_url`/`target_id`）。
3. Agent 路由到目标 SDK，SDK 执行动作并返回 `action_ack`。
4. Agent 将 `action_ack` 回传给面板。

### 幂等行为

- Agent 对 `action.msg_id` 做去重。
- 相同 `msg_id` 第二次到达时，不重复执行动作，直接返回 `duplicate ignored`。

## 构建与测试

```bash
make lint
make test
make build-agent
make build-sdk
```

启用端到端幂等测试（需要 Agent/SDK 已运行）：

```bash
RUN_E2E=1 make test
```

## 一键示例（Agent + 多 SDK + 面板）

```bash
make demo
make demo-multi
make demo-stress
SDK_COUNT=20 make demo-scale
```

或直接运行：

```bash
./examples/run.sh
./examples/run.multi.sh
./examples/run.stress.sh
./examples/run.scale.sh
```

配置文件在 `examples/config.json`，多实例演示使用 `examples/config.multi.json`，压力演示使用 `examples/config.stress.json`。

## 文档索引

- 架构说明：[docs/architecture.md](docs/architecture.md)
- 协议说明：[docs/protocol.md](docs/protocol.md)
- 发布说明：[docs/release.md](docs/release.md)
- 部署说明：[docs/deploy.md](docs/deploy.md)
- Ubuntu 从零部署：[docs/ubuntu-from-scratch.md](docs/ubuntu-from-scratch.md)
- SDK 规范：[python-sdk/README.md](python-sdk/README.md)
- 示例说明：[examples/README.md](examples/README.md)

## 当前状态

仓库已完成 MVP 基础骨架，后续按 `PLAN.md` 持续迭代。
