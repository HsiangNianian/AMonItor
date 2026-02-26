# Examples

`examples/` 提供可配置、可一键运行的本地联调环境：

- 1 个 Go Agent
- 多个 Python SDK 实例（默认 2 个）
- 1 个面板 Demo 客户端

## 文件说明

- `config.json`：示例配置（端口、target_id、动作名称等）
- `config.multi.json`：多实例压力演示配置（默认 5 个 SDK）
- `run_demo.py`：进程编排器（启动/监控/统一退出）
- `run.sh`：一键启动脚本
- `run.multi.sh`：多实例一键启动脚本
- `panel_demo.py`：面板模拟客户端（连接 Agent、发送 action、打印消息）
- `sdk_demo.py`：SDK 示例服务（接 action、发 heartbeat）

## 一键运行

在仓库根目录执行：

```bash
./examples/run.sh
```

或使用 Makefile：

```bash
make demo
```

多实例（5 SDK）演示：

```bash
make demo-multi
```

## 配置方式

编辑 `examples/config.json`：

- `agent.listen_addr`：Agent 监听地址
- `agent.panel_ws`：面板连接地址
- `sdk_instances`：SDK 列表，可扩容为多个实例
- `panel.send_actions_on_connect`：面板连接后是否自动发送 action
- `panel.action_name`：下发动作名称

如需多实例压测，可直接使用 `examples/config.multi.json`。

新增 SDK 实例示例：

```json
{
  "name": "sdk-c",
  "target_id": "demo-target-c",
  "host": "127.0.0.1",
  "port": 8767,
  "heartbeat_interval": 5
}
```

## 交互观测

启动后会在终端看到：

- `[panel] recv ... heartbeat`：SDK 心跳已上行
- `[panel] recv ... action_ack`：控制动作回执已下行

按 `Ctrl + C` 会停止全部示例进程。
