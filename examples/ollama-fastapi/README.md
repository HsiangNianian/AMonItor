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

1. 在面板输入 WS 地址（默认来自配置）
2. 也可以通过“选择目标服务”下拉自动填充 `target_id/target_url/apiBase`
3. 点击“连接”
4. 右侧实时展示：
   - Token 字符总数
   - 最近请求字符数
   - GPU 利用率
   - 排队数 / 处理中 / 总请求 / 失败请求
5. 在 Action 区域填写动作并发送
6. 在 Prompt 区域输入文本，点击“调用 `/api/generate`”直接触发模型生成
7. 生成结果会显示在“模型输出”，日志会记录本次 `token_chars`

WS 地址示例：

- `ws://127.0.0.1:8011/ws/monitor`
- `ws://127.0.0.1:8012/ws/monitor`

## 配置

编辑 `config.json` 可修改：

- `agent.enabled`：是否启用 Agent 拓扑（仅用于配置语义）
- `agent.panel_ws`：面板连接 Agent 的 WS 地址（例如内网机器）
- `agent.targets`：服务名到目标 `target_url` 映射（给 action 转发使用）
- Ollama 地址与模型
- 两个服务端口
- 并发数
- 面板端口、默认 WS、默认 API Base

当 `agent.enabled=true` 时，`run_all.sh` 会自动把面板默认 WS 覆盖为 `agent.panel_ws`，不需要手动再改 `panel.defaultWs`。

### Agent 在内网其他机器时

如果你的 Agent 二进制部署在别的机器：

1. 将 `panel.defaultWs` 改为 `agent.panel_ws`
2. 面板勾选“通过 Agent 转发”
3. 填写 `target_id` 与 `target_url`（可直接用 `agent.targets` 的映射值）
4. `API Base` 填真实 Python 服务地址（用于 `/api/generate`）

示例：

- `panel.defaultWs = ws://10.0.0.9:8080/ws/panel`
- `actionTargetId = ollama-svc-a`
- `actionTargetUrl = ws://10.0.0.21:8011/ws/monitor`
- `apiBaseUrl = http://10.0.0.21:8011`

## 停止

在启动终端按 `Ctrl + C`，会自动停止全部子进程。
