# 架构说明

## 组件
1. 监控面板：WS 客户端，连接 Agent
2. Agent：
   - 对面板：WS 服务端
   - 对 SDK：WS 客户端
3. Python SDK：在被监控程序侧开启 WS 服务端

## 数据流
- SDK -> Agent -> 面板：heartbeat / event
- 面板 -> Agent -> SDK：action
- SDK -> Agent -> 面板：action_ack

## 多实例与状态
MVP 使用 Redis 存储：
- 路由表：`target_id -> sdk_url`
- 幂等表：`msg_id`
- ACK 状态：`msg_id -> status`

## 安全
- 链路 TLS
- 双链路 Token 鉴权
