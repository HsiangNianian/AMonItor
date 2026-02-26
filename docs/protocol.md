# 协议说明（MVP）

统一消息 envelope 字段：
- `msg_id`: 全局唯一消息ID
- `trace_id`: 链路追踪ID
- `type`: 消息类型
- `target_id`: 目标实例
- `timestamp`: UTC毫秒
- `payload`: 业务负载（可变）

消息类型：
- `register`
- `heartbeat`
- `event`
- `action`
- `action_ack`
- `error`

幂等规则：
- Agent 对 `action.msg_id` 去重
- 已处理过的 `msg_id` 不重复执行，返回重复ACK
