# Ollama + FastAPI + TS 面板示例

这个示例包含你要求的三部分：

- 两个 FastAPI Python 服务（`service_a.py`、`service_b.py`）
- 服务内部调用 Ollama `qwen3:0.6b` 并暴露 API
- 一个 TypeScript 面板（可填写 WS 地址、发送 action、实时看 token 字符数 / GPU 利用率 / 排队情况）

## 目录

- `service_a.py`：FastAPI 服务 A
- `service_b.py`：FastAPI 服务 B
- `ollama_monitor_app.py`：公共逻辑（Ollama 调用、监控状态、WS 广播）
- `panel/`：TS 前端面板（Vite）
- `config.json`：一键运行配置
- `run_all.sh`：一键启动脚本

## 前置条件

1. 本机已安装并运行 Ollama
2. 模型已拉取：

```bash
ollama pull qwen3:0.6b
```

## 一键启动

在仓库根目录执行：

```bash
bash examples/ollama-fastapi/run_all.sh
```

说明：脚本会直接复用 `python-sdk` 的 `uv` 项目环境运行 Python 服务，不会在 `examples/ollama-fastapi` 目录创建新的虚拟环境。

默认已开启 CORS（支持浏览器 `OPTIONS` 预检）。如果要限制来源，可在启动服务前设置：

```bash
export CORS_ALLOW_ORIGINS=http://127.0.0.1:5174,http://localhost:5174
```

说明：`examples/ollama-fastapi/config.json` 已与 Agent 配置结构对齐，同一份配置可以直接用于 Agent：

```bash
go run ./agent/cmd/agent --config ./examples/ollama-fastapi/config.json
```

启动后可访问：

- 服务 A 文档：`http://127.0.0.1:8011/docs`
- 服务 B 文档：`http://127.0.0.1:8012/docs`
- 面板：`http://127.0.0.1:5174`

## API 示例

### 1) 文本生成（服务 A）

```bash
curl -X POST http://127.0.0.1:8011/api/generate \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"用一句话介绍你自己"}'
```

返回字段包含：

- `text`：模型输出
- `token_chars`：本次输出字符数
- `service_name`、`model`

### 2) 获取指标

```bash
curl http://127.0.0.1:8011/api/metrics
```

关键指标：

- `total_token_chars`
- `gpu_utilization`（无 NVIDIA 环境时为 `-1`）
- `queue_size`
- `in_progress_requests`

### 3) 发送 action

```bash
curl -X POST http://127.0.0.1:8011/api/action \
  -H 'Content-Type: application/json' \
  -d '{"action":"set_max_concurrency","value":2}'
```

支持的 action：

- `reset_metrics`
- `set_max_concurrency`

## 面板交互

1. 在面板输入 Agent WS 地址（默认来自 `server.listen_addr + server.panel_path`）
2. 通过“选择目标服务”下拉自动填充 `target_id/target_url/apiBase`
3. 点击“连接”
4. 右侧实时展示：
   - Token 字符总数
   - 最近请求字符数
   - GPU 利用率
   - 排队数 / 处理中 / 总请求 / 失败请求
5. 在 Action 区域填写动作并发送
6. 在 Prompt 区域输入文本，点击“调用 `/api/generate`”直接触发模型生成
7. 生成结果会显示在“模型输出”，日志会记录本次 `token_chars`

WS 地址示例（面板固定连接 Agent）：

- `ws://127.0.0.1:8080/ws/panel`

## 配置

编辑 `config.json` 可修改：

- `server.listen_addr` 与 `server.panel_path`：Agent 面板入口
- `routes[]`：目标服务路由（`target_id -> url(+auth_token)`）
- `client.upstreams[]`：可选，Agent 主动连接多个上游服务
- Ollama 地址与模型
- 两个服务端口
- 并发数
- 面板端口、默认 API Base

`run_all.sh` 始终使用 `server.listen_addr + server.panel_path` 作为面板默认 WS。

### Agent 在内网其他机器时

如果你的 Agent 二进制部署在别的机器：

1. 配置 `server.listen_addr` 为 Agent 的对外地址，`server.panel_path` 为面板入口路径
2. 填写 `target_id` 与 `target_url`（可直接用 `routes[]` 的映射值）
3. `API Base` 填真实 Python 服务地址（用于 `/api/generate`）

注意：选择目标服务只会自动填写 `target_id/target_url/apiBase`，不会覆盖你已经填写的 Agent `WS` 地址。

示例：

- `server.listen_addr = 10.0.0.9:8080`
- `server.panel_path = /ws/panel`
- `actionTargetId = ollama-svc-a`
- `actionTargetUrl = ws://10.0.0.21:8011/ws/monitor`
- `apiBaseUrl = http://10.0.0.21:8011`

## 停止

在启动终端按 `Ctrl + C`，会自动停止全部子进程。

## 项目根目录启动 Agent

源码运行：

```bash
cd /home/hsiangnianian/GitProject/HsiangNianian/AMonItor
go run ./agent/cmd/agent
```

编译后运行：

```bash
cd /home/hsiangnianian/GitProject/HsiangNianian/AMonItor
go build -o amonitor-agent ./agent/cmd/agent
./amonitor-agent
```
