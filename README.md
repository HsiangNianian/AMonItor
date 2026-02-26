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

## 快速开始
1. 阅读计划：`PLAN.md`
2. 查看架构：`docs/architecture.md`
3. 查看协议：`docs/protocol.md`
4. 运行构建：`make build-agent`

## 当前状态
仓库已完成 MVP 基础骨架，后续按 `PLAN.md` 持续迭代。
