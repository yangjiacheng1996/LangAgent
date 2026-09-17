# F03 — Protocol 层 Event 总线（protocol_event_bus）

> **Feature ID**: F03
> **批次**: 第 2 批（事件基础设施；**review.md v2.2.0 修复 P0-2**：原"第 3 批"按 v1.1.0 P0-3 修复统一为"第 2 批"，与 README §二 推荐批次表第 2 批 [F03] 对齐）
> **依赖**: F02（`cross_cutting_logger` 模块，提供 `emit` 接口 + `EventBusProtocol` 接口定义；**review.md v0.5.0 评审 v0.1.0 §二.A.3 方案 A 修复**：EventBusProtocol 接口定义从独立模块合并入 `cross_cutting_logger` 模块）
> **被依赖**: F05 / F04 / F08 / F09 / F10
> **状态**: 待启动 speckit.specify（review.md v1.1.0 修复后；本 feature prompt 已应用 v1.1.0 修复：P0-1 §3.1 API 增 `drain_events()` + §3.3 drain 语义段 + §4.1b 6 个测试；P0-6 §3.4 标题改 ≥13；P0-3 批次改 "第 2 批"；P1-1 §六 补 emit() 不实现声明）

---

## 一、Feature 概述

实现 protocol 层的 Event 总线（pub/sub 模式）。所有跨模块通信的可观测事件（`tool_call` / `model_response` / `guardrail_block` / `skill_loaded` / `graph_composed` 等）都通过 Event 总线发布；订阅者按需消费。

**关键约束（评审 m-5 修复后）**：

- **runtime / protocol / cross_cutting 三层内部**的跨模块通知（异步、解耦场景）必须经过 Event 总线。
- **cli 层**调用 runtime 模块是 CLI 编排职责，**不受 Event 总线约束**——`cli_runner` 直接调用 `runtime_dir_loader` / `runtime_main_loop_dispatcher` / `runtime_exit_handler` / `runtime_config_resolver` 是 `architecture_modules.md#mod-cli-runner` 显式允许的依赖方向。
- `runtime_main_loop_dispatcher` 内部为调用 LangGraph 原语，可直接函数调用（LangGraph 自身不使用本项目的 Event 总线）。
- `cross_cutting_metrics_collector` 订阅事件是反例允许的——订阅者只读不写，不形成反向依赖。

## 二、必读顶层设计 artefact（宪法第 XV 条）

1. `harness/top_level_design/workflow.md#stage-main_loop` —— 主循环阶段必发 `tool_call` / `model_response` / `guardrail_block` 事件。
2. `harness/top_level_design/architecture_modules.md#mod-protocol-event-bus` —— 模块职责、API、依赖方向。
3. `harness/top_level_design/module_schemas.md#schema-event` —— Event 6 字段 + JSONL 序列化格式。

## 三、本 feature 覆盖的范围

### 3.1 模块

| module_id | 关键 API | 行数估算 |
|---|---|---|
| `protocol_event_bus` | `publish(event: Event) -> None` + `publish_async(event: Event) -> None`（review.md m-1 修复新增）+ `subscribe(event_type: str, handler: Callable[[Event], None]) -> SubscriptionToken` + `unsubscribe(token: SubscriptionToken) -> None` + `flush(timeout: float = 5.0) -> None`（review.md M-5 修复新增）+ **`drain_events() -> list[Event]`**（**review.md v1.1.0 P0-1 修复新增**：返回自上次 drain 以来的累积事件列表并清空内部 buffer；供 F09 cleanup step 6.3 写 `logs/<run-id>.jsonl` 使用） | ~280 |

> **review.md M-5 修复明确**：`flush(timeout)` 用于 exit_cleanup 阶段等待所有 pending handler 完成；timeout 默认 5s；未完成则发 `la.cross_cutting.event_handler_error` 日志（通过 F02 logger 接口）后返回（**不抛错**，保证 cleanup 流程继续）。
> **review.md m-1 修复明确**：`publish_async(event)` 接收 `async def handler`，跑 `asyncio.gather`；同步 handler 也可在 publish_async 中调用（自动包装为 coroutine）。

### 3.2 Schema

- `Event`（6 字段：`event_id` / `event_type` / `emitted_at` / `source` / `payload` / `trace_id`，均为必填或 `-`，JSONL 格式持久化）。

### 3.3 Event 总线实现

- **同步 pub/sub**：publish 时同步调用所有订阅 handler。
- **异步支持**：提供 `publish_async(event)` 接收 `async def handler`，跑 `asyncio.gather`（review.md m-1 修复明确）。
- **flush 语义（review.md M-5 修复明确）**：调用 `flush(timeout=5.0)` 阻塞等待所有 pending sync / async handler 完成（用 `concurrent.futures.Future` 或 `asyncio.gather` 跟踪）；用于 exit_cleanup 阶段确保所有事件已落 JSONL / 触发订阅者；timeout 内未完成则发 `la.cross_cutting.event_handler_error` 日志（通过 F02 logger 接口）后返回（**不视为失败**）。
- **错误隔离**：订阅 handler 抛异常不阻塞其他订阅者；异常计入 F03 内部 `error_count` 计数器并发 `la.cross_cutting.event_handler_error` 日志（**review.md v0.1.0 R-010 修复明确**：`error_count` 是 F03 内部计数器，**不是 F02 MetricsSnapshot 字段**，仅用于 F03 自检 handler 异常率；不通过 event_bus publish；`la.cross_cutting.event_handler_error` 日志是 handler 异常的对外信号）。
- **线程安全**：使用 `threading.Lock` 保护订阅者列表。
- **事件类型白名单**：仅允许登记的事件类型被 publish；未登记抛 `UnknownEventTypeError`（与 logger 的 tag 白名单对齐）。
- **drain_events 语义（review.md v1.1.0 P0-1 修复新增）**：内部维护 `_event_buffer: list[Event]`（threading.Lock 保护）。`drain_events() -> list[Event]` 调用时返回 buffer 全量快照并清空 buffer；连续两次 drain 之间 publish 的事件被累积。供 F09 cleanup step 6.3 写 `logs/<run-id>.jsonl` 使用 —— F09 在 flush() 完成后调 drain_events() 拿到所有未持久化的事件，**不可重复 drain**（第二次返回空 list）。drain 失败抛 `EventDrainError`，退出码 4。

### 3.4 必须登记的事件类型（≥13 种，含 `event_handler_error`）

| `event_type` | 触发者 | 订阅者 | 含义 |
|---|---|---|---|
| `tool_call` | F08 | F02 metrics + F04 audit | 模型发起 tool_call |
| `tool_result` | F08 | F02 metrics | tool 执行返回 |
| `model_response` | F08 | F02 metrics + F05 audit | 模型返回 AIMessage |
| `guardrail_block` | F04 | F04 audit + F02 metrics | 护栏拦截 |
| `skill_loaded` | F05 | F02 logger | skill 加载成功 |
| `skill_load_failed` | F05 | F02 logger | skill 加载失败 |
| `tool_registered` | F05 | F02 logger | tool 注册成功 |
| `graph_composed` | F01 / F05 | F02 logger | 图编译完成 |
| `eval_task_started` | F11 | F02 metrics | eval 任务开始 |
| `eval_task_done` | F11 | F02 metrics | eval 任务完成 |
| `audit_written` | F04 | F02 logger | 审计条目写入 |
| `metrics_snapshot` | F02 | F02 logger | 指标快照生成 |
| `event_handler_error` | F03 | F02 logger | Event 总线订阅 handler 抛异常（评审 s-6 修复后登记） |

## 四、TDD 测试用例先行

### 4.1 `protocol_event_bus` 核心测试

- [ ] `test_publish_subscribe_basic`：订阅 `tool_call` → publish 一个 Event → handler 被调用 1 次。
- [ ] `test_publish_no_subscribers`：publish 一个无订阅的 event_type → 不抛异常。
- [ ] `test_subscribe_returns_token`：`token = subscribe(...)` → `unsubscribe(token)` 后 handler 不再被调用。
- [ ] `test_unsubscribe_idempotent`：对同一 token 多次 `unsubscribe` 不抛异常。
- [ ] `test_multiple_subscribers_same_event`：3 个 handler 订阅 `tool_call` → publish → 3 个 handler 全被调用。
- [ ] `test_publish_event_type_whitelist`：publish `event_type="unknown"` → 抛 `UnknownEventTypeError`。
- [ ] `test_publish_handler_error_isolated`：handler A 抛异常，handler B 仍被调用；F02 logger 收到 `event_handler_error` 日志。
- [ ] `test_flush_waits_for_pending_sync_handlers`（**review.md M-5 修复新增**）：subscribe 1 个 sleep(2s) handler + publish → flush(timeout=5) 阻塞直到 handler 完成；返回后 handler 已运行。
- [ ] `test_flush_timeout_emits_event_handler_error_log`（**review.md M-5 修复新增**）：subscribe 1 个 sleep(10s) handler + publish → flush(timeout=1) 超时返回；F02 logger 收到 `event_handler_error` 日志；不抛错。
- [ ] `test_flush_no_pending_returns_immediately`：无 pending handler → flush() 立即返回。
- [ ] `test_publish_async_handler`（**review.md m-1 修复新增**）：`async def handler` 被正确 await。
- [ ] `test_publish_async_handler_exception_isolated`：`async handler` 抛异常不阻塞其他 async handler。
- [ ] `test_publish_async_with_sync_handler`：`publish_async` 中调用 sync handler（自动包装为 coroutine）。

### 4.1a `ALLOWED_EVENT_TYPES` 完整性测试（**review.md m-4 修复新增**）

- [ ] `test_allowed_event_types_at_least_13`：`ALLOWED_EVENT_TYPES` 集合 ≥13 项（含 `tool_call` / `tool_result` / `model_response` / `guardrail_block` / `skill_loaded` / `skill_load_failed` / `tool_registered` / `graph_composed` / `eval_task_started` / `eval_task_done` / `audit_written` / `metrics_snapshot` / `event_handler_error`）。
- [ ] `test_all_registered_event_types_have_documentation`：每种 event_type 在 F03 §三.4 表格中均有说明（event_type / 触发者 / 订阅者 / 含义）。
- [ ] `test_event_handler_error_in_whitelist`（**review.md s-6 修复后**）：`event_handler_error` 在 `ALLOWED_EVENT_TYPES` 内，可在 handler 异常隔离时 publish。

### 4.2 Event payload 验证

- [ ] `test_event_payload_must_be_dict`：`payload="string"` → 抛 `TypeError`。
- [ ] `test_event_payload_must_be_json_serializable`：payload 含 `BaseMessage` 实例 → `json.dumps` 应正常工作（用 `langchain_core.messages.message_to_dict` 转换）。
- [ ] `test_event_id_is_unique`：连续 publish 100 次同 event_type → event_id 全部不同。
- [ ] `test_event_emitted_at_is_utc_now`：`emitted_at` 与 `datetime.utcnow()` 偏差 < 1 ms。

### 4.3 异步 + 线程安全测试

- [ ] `test_publish_async_handler`：`async def handler` 被正确 await。
- [ ] `test_publish_async_handler_exception`：`async handler` 抛异常不阻塞其他 async handler。
- [ ] `test_thread_safe_publish`：10 个线程并发 publish + subscribe → 无死锁、无数据竞争（用 `threading.Barrier` 同步启动）。
- [ ] `test_subscribe_during_publish`：publish 时调用 `subscribe` / `unsubscribe` → 不抛 `RuntimeError: dict changed size during iteration`。

#### 4.1b `drain_events` 测试（**review.md v1.1.0 P0-1 修复新增**）

- [ ] `test_drain_events_returns_accumulated`：连续 publish 5 个 `tool_call` event（无订阅 handler）→ `drain_events()` 返回长度 5 的 list，event_id 全部不同。
- [ ] `test_drain_events_clears_buffer`：drain 后再 publish 3 个 → 第二次 drain 返回长度 3 的 list，不包含前 5 个。
- [ ] `test_drain_events_empty_when_no_pending`：空 buffer 时 drain 返回 `[]`，不抛错。
- [ ] `test_drain_events_thread_safe`：10 个线程并发 publish + drain → 无死锁、无丢失事件（所有 publish 的 event_id 都能在某次 drain 中出现）。
- [ ] `test_drain_events_with_pending_handlers_returns_after_flush`：handler 在 publish 时同步执行 → drain_events 返回所有事件 + handler 已全部执行。
- [ ] `test_drain_events_raises_event_drain_error_on_io_failure`：mock buffer 持久化失败 → `drain_events()` 抛 `EventDrainError`（退出码 4）；**drain 失败时 buffer 不清空**（允许 caller 重试）。

### 4.4 与 F02 metrics_collector 的集成

- [ ] `test_metrics_collector_receives_tool_call_event`：publish `tool_call` event → `record_latency` 被调用。
- [ ] `test_metrics_collector_receives_model_response_event`：publish `model_response` 含 `usage_metadata` → `record_token_usage` 被调用。
- [ ] `test_metrics_collector_receives_guardrail_block_event`：publish `guardrail_block` → `record_error` 被调用。

## 五、关键约束

1. **不依赖 LangSmith**：不引用 LangSmith SDK；event 总线自研。
2. **JSONL 兼容**：Event payload 必须可 `json.dumps`；`BaseMessage` 等 LangChain 类型通过 `langchain_core.messages.message_to_dict` 转换。
3. **线程安全刚性**：cross_cutting 层 metrics_collector 与 protocol_event_bus 都并发被调；必须保证无 GIL 假设下的安全。
4. **错误隔离**：handler 异常吞掉 + 写日志；绝不抛回 publish caller。
5. **event_type 白名单**：≥12 个预登记类型；未登记抛异常，避免事件名拼写错误。
6. **依赖方向**：protocol 层不依赖 runtime / cli / primitives（仅 cross_cutting_logger）。
7. **TDD 刚性**：先 Red 后 Green 再 Refactor。
8. **第 XV 条对齐清单**：与宪法第 III 条（剥离 LangSmith）/ 第 IX 条（Tracing 子能力：Event 是 Span 的轻量替代，承载模块间通知）/ 第 XIII 条逐项对齐。

## 六、本 feature 不包含

- **不实现 `emit()` 日志发射接口**（→ F02 `cross_cutting_logger`；F03 仅通过 `from langagent.cross_cutting.logger import emit` 调用，不持有 emit 实现；review.md v1.1.0 P1-1 修复明确）。
- 不实现 Span / Trace 持久化（→ F02 + F09）。
- 不实现 MetricsSnapshot 聚合（→ F02）。
- 不实现 AuditEntry（→ F04）。
- 不实现 cross_cutting_metrics_collector（→ F02，但本 feature 与 F02 有集成测试）。

## 七、Deliverable 清单

- [ ] `langagent/protocol/event_bus.py`：`EventBus` 类（实现 F02 的 `EventBusProtocol` 接口）+ `SubscriptionToken` + `publish` / `publish_async`（review.md m-1 修复）/ `subscribe` / `unsubscribe` / `flush(timeout)`（review.md M-5 修复）+ **`drain_events()`**（**review.md v1.1.0 P0-1 修复新增**：内部维护 `_event_buffer: list[Event]` + Lock）。
- [ ] `tests/protocol/test_event_bus.py`：≥18 + **6（drain_events）** = **≥24** 个测试用例（含 flush / async / event_handler_error / drain 测试）。
- [ ] `tests/protocol/test_event_integration_with_metrics.py`：≥3 个集成测试。
- [ ] `langagent/protocol/event_types.py`：`ALLOWED_EVENT_TYPES` 常量集合（≥13 项，review.md m-4 修复明确）。
- [ ] `mypy --strict` 通过。
- [ ] spec / plan / tasks 顶部引用宪法第 XV 条。

## 八、与其它 feature 的边界

- **F02 metrics_collector**：F02 提供 `EventBusProtocol` 接口（review.md v0.4.0 m-2 修复明确；review.md v0.5.0 评审 v0.1.0 §二.A.3 方案 A 修复：EventBusProtocol 接口从独立 `cross_cutting_event_bus_protocol` 模块合并入 `cross_cutting_logger` 模块）；F03 的 `EventBus` 类实现该接口；F02 metrics_collector 通过 `EventBusProtocol.subscribe()` 订阅 `tool_call` / `model_response` / `guardrail_block` 3 类事件。
- **F05**：F05 的 `protocol_skill_loader` + `protocol_tool_registry` 在加载 / 注册时 publish `skill_loaded` / `skill_load_failed` / `tool_registered` 事件。
- **F08**：F08 在 main_loop 中 publish `tool_call` / `tool_result` / `model_response` 事件。
- **F09**：F09 exit_cleanup 调用 `event_bus.flush(timeout=5)`（review.md M-5 修复）确保所有 pending handler 完成后再写报告。
- **F04**：F04 的 guardrail_middleware 在拦截时 publish `guardrail_block` 事件；audit_recorder 在写 audit 后 publish `audit_written`。
- **F11**：F11 在 eval 任务开始 / 完成时 publish `eval_task_started` / `eval_task_done`。