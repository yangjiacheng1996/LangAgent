# Feature Specification: F02 Phase 2 - Metrics Collector

**Feature Branch**: `002-metrics-collector-phase2`

**Created**: 2026-09-18

**Updated**: 2026-09-19 (Removed tool side effects per feature prompt update)

**Status**: Draft

**Input**: User description: "F02 Phase 2 - cross_cutting_metrics_collector 实现。在 F03 event bus 完成后回填，订阅 protocol_event_bus 的 tool_call / model_response / eval_task_started / eval_task_done 事件，聚合 latency / token usage / error_rate / cost_usd，产出 MetricsSnapshot。工具侧面效应（tool side effects）已从系统中移除。"

**Constitutional References**: 
- 宪法第 XV 条：顶层设计优先（必读 `harness/top_level_design/` 三份 artefact）
- 宪法第 III 条：LangSmith 剥离原则（日志 tag 必须 `la.` 前缀）
- 宪法第 IX 条：Tracing + Monitoring（本 feature 实现 Monitoring 部分）
- 宪法第 XII 条：可观测契约
- 宪法第 XIII 条：Hard No（不写绝对路径/内网 IP）

**Top-Level Design References**:
1. `harness/top_level_design/workflow.md` - 6 阶段工作流与日志标签定义
2. `harness/top_level_design/architecture_modules.md#mod-cross-cutting-metrics-collector` - 模块职责与依赖
3. `harness/top_level_design/module_schemas.md#schema-metrics-snapshot` - MetricsSnapshot 9 字段定义

## Clarifications

### Session 2026-09-18

- Q: 当同一个事件因重试逻辑被发布两次时，指标收集器应该如何处理？ → A: 要求事件必须携带唯一 event_id，系统内部维护去重窗口（最近 10 分钟的 event_id 集合），重复事件直接丢弃。使用 Python set() 进行去重。
- Q: 去重窗口应该保留多长时间的 event_id 历史记录？ → A: 保留最近 10 分钟的 event_id（平衡去重效果与内存占用，约 21MB）
- Q: 当 `snapshot()` 被调用但没有任何样本数据时，百分位延迟字段（p50/p95/p99）应该返回什么值？ → A: 返回 None（表示"无数据"，需要调用方显式检查）
- Q: 模型定价表应该如何配置和加载？ → A: JSON 配置文件，路径通过环境变量或参数指定，提供合理的内置默认值
- Q: 当事件缺少必需字段（如 `latency_ms` 或 `token_usage`）时，除了记录警告日志外，是否需要发出专门的指标来追踪这类异常？ → A: 仅记录警告日志到 stderr（通过 F02 Phase 1 logger），不增加额外指标

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic Metrics Collection During Agent Execution (Priority: P1)

As a LangAgent user running an agent, the system automatically collects performance metrics (latency, token usage, error rate) in the background without requiring any explicit configuration, so I can analyze agent performance after execution completes.

**Why this priority**: This is the core value proposition - transparent, zero-config observability for all agent runs.

**Independent Test**: Can be fully tested by running any agent with tool calls and model interactions, then calling `snapshot()` to verify metrics were collected. Delivers immediate value for performance analysis.

**Acceptance Scenarios**:

1. **Given** an agent makes 5 tool calls during execution, **When** I call `metrics_collector.snapshot()`, **Then** I see 5 latency samples recorded with operation type "tool_call"
2. **Given** an agent makes 3 model calls with different token counts, **When** I call `snapshot()`, **Then** I see aggregated token_usage with correct prompt/completion token totals per model
3. **Given** an agent run completes without errors, **When** I check the snapshot, **Then** error_rate is 0.0
4. **Given** an agent encounters 2 errors during 10 operations, **When** I check the snapshot, **Then** error_rate is 0.2

---

### User Story 2 - Time-Window Metrics Snapshots (Priority: P2)

As a developer analyzing agent performance, I can request metrics snapshots for specific time windows (e.g., "last 5 minutes of this run") to understand performance trends within a single execution, so I can identify bottlenecks in specific phases.

**Why this priority**: Enables fine-grained analysis but not required for basic observability.

**Independent Test**: Can be tested by recording metrics over a 60-second period, then requesting snapshots for `[0:30]` and `[30:60]` windows and verifying they contain only events from their respective windows.

**Acceptance Scenarios**:

1. **Given** metrics recorded over 60 seconds, **When** I request `snapshot(window_start=T0, window_end=T0+30s)`, **Then** I receive only samples from the first 30 seconds
2. **Given** metrics collected across multiple agent turns, **When** I request non-overlapping time windows, **Then** each snapshot contains distinct, non-overlapping samples

---

### User Story 3 - Cost Estimation from Token Usage (Priority: P2)

As a developer monitoring agent costs, the metrics collector automatically calculates `cost_usd` based on token usage and model pricing, so I can understand the financial impact of agent runs without manual calculation.

**Why this priority**: Important for production deployments but not critical for initial development/testing.

**Independent Test**: Can be tested by providing a mock pricing table, recording token usage for known models, and verifying `cost_usd` matches expected calculation (prompt_tokens × prompt_price + completion_tokens × completion_price).

**Acceptance Scenarios**:

1. **Given** a pricing table with `{"gpt-4o": {"prompt": 0.005, "completion": 0.015}}` per 1K tokens, **When** agent uses 1000 prompt + 500 completion tokens, **Then** `cost_usd = (1000 × 0.005 + 500 × 0.015) / 1000 = 0.0125`
2. **Given** multiple models used in one run, **When** I check the snapshot, **Then** `cost_usd` is the sum of costs across all models

---

### User Story 4 - Percentile Latency Reporting (Priority: P1)

As a performance engineer, I can see p50/p95/p99 latency metrics to understand both typical and worst-case performance, so I can identify outliers and set SLOs appropriately.

**Why this priority**: Essential for performance analysis - median alone is insufficient.

**Independent Test**: Can be tested by recording 100 latency samples with known distribution, then verifying p50/p95/p99 match expected percentile values.

**Acceptance Scenarios**:

1. **Given** 100 latency samples uniformly distributed from 10ms to 110ms, **When** I call `snapshot()`, **Then** p50 ≈ 60ms, p95 ≈ 105ms, p99 ≈ 109ms
2. **Given** no samples recorded, **When** I call `snapshot()`, **Then** all percentile fields (p50_latency_ms, p95_latency_ms, p99_latency_ms) are None

---

### User Story 5 - Event Bus Integration (Priority: P1)

As the metrics collector module, I subscribe to the event bus at initialization and automatically record metrics when `tool_call`, `model_response`, `eval_task_started`, or `eval_task_done` events are published, so metrics collection happens transparently without explicit instrumentation in business logic.

**Why this priority**: This is the architectural foundation - without event bus integration, no automatic collection is possible.

**Independent Test**: Can be tested by mocking the event bus, publishing known events, and verifying metrics_collector's internal state reflects those events (e.g., latency samples added, token counts incremented).

**Acceptance Scenarios**:

1. **Given** metrics_collector subscribed to event bus, **When** a `tool_call` event is published with `{"operation": "web_search", "latency_ms": 250}`, **Then** `record_latency("web_search", 250)` is automatically called
2. **Given** a `model_response` event is published with token usage metadata, **When** I check internal state, **Then** `record_token_usage()` was called with correct model/token counts
3. **Given** event bus publishes `eval_task_started`, **When** later `eval_task_done` is published, **Then** elapsed time between events is recorded as eval task latency

---

### Edge Cases

- What happens when `snapshot()` is called with `window_end < window_start`? (Must raise ValueError)
- How does the system handle events with missing `latency_ms` or `token_usage` fields? (Must log warning via F02 Phase 1 logger and skip, not crash; no additional metrics tracked for malformed events in v1)
- What if the same event is published twice due to retry logic? (System maintains a 10-minute rolling window of event_id in a set; duplicate event_id within window is discarded silently)
- How are metrics handled when model_name is unknown (not in pricing table)? (Must record tokens but set cost_usd contribution to 0.0, log warning)
- What happens if `flush()` is called while events are being processed? (Must use thread-safe locks to ensure no data loss; flush() clears both sample data and event_id deduplication window)
- How does `snapshot()` behave if called concurrently from multiple threads? (Must return consistent view, use locks)
- What happens when no samples exist? (Percentile fields p50/p95/p99 return None; sample_count=0, error_rate=0.0, token_usage={}, cost_usd=0.0)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST subscribe to `protocol_event_bus` on initialization and register handlers for `tool_call`, `model_response`, `eval_task_started`, `eval_task_done` events. All events MUST include a unique `event_id` field for deduplication. System maintains a 10-minute rolling window of processed event_id values in a set; events with duplicate event_id within the window are silently discarded.
- **FR-002**: System MUST provide `record_latency(operation: str, ms: float) -> None` API to record operation latencies
- **FR-003**: System MUST provide `record_token_usage(model_name: str, prompt: int, completion: int) -> None` API to record token consumption per model
- **FR-004**: System MUST provide `record_error(operation: str) -> None` API to increment error counters
- **FR-005**: System MUST provide `flush() -> None` API to clear all accumulated metrics (used by F09 exit_cleanup). Flush MUST clear both sample data and the event_id deduplication window.
- **FR-006**: System MUST provide `snapshot(window_start: datetime, window_end: datetime) -> MetricsSnapshot` API to generate time-windowed metrics summary
- **FR-007**: MetricsSnapshot MUST include 9 fields: `window_start`, `window_end`, `sample_count`, `p50_latency_ms`, `p95_latency_ms`, `p99_latency_ms`, `error_rate`, `token_usage`, `cost_usd`. Percentile fields use type `Optional[float]` and return None when no samples exist.
- **FR-008**: System MUST calculate `p50_latency_ms`, `p95_latency_ms`, `p99_latency_ms` from all latency samples within the time window. When no samples exist, all three fields return None.
- **FR-009**: System MUST calculate `error_rate` as `error_count / (error_count + success_count)` within the time window
- **FR-010**: System MUST aggregate `token_usage` as `dict[model_name, total_tokens]` across all models used
- **FR-011**: System MUST calculate `cost_usd` by multiplying token counts by per-model pricing from a configurable JSON pricing table (path specified via environment variable or initialization parameter with built-in default fallback)
- **FR-012**: System MUST emit `la.cross_cutting.metrics.emit` log tag when `snapshot()` is called (via F02 Phase 1 logger)
- **FR-013**: System MUST be thread-safe - concurrent `record_*` calls and `snapshot()` calls must not corrupt internal state
- **FR-014**: System MUST filter samples by timestamp - only samples where `window_start <= sample.timestamp < window_end` are included in snapshot
- **FR-015**: System MUST return a frozen (immutable) MetricsSnapshot dataclass to prevent accidental mutation by callers
- **FR-016**: When an event is missing required fields (`latency_ms`, `token_usage`, or `event_id`), system MUST log a warning via F02 Phase 1 logger and skip the event without crashing. No additional metrics are tracked for malformed events in v1.

### Key Entities *(include if feature involves data)*

- **MetricsSnapshot**: Time-windowed summary of performance metrics. Contains 9 fields per `module_schemas.md#schema-metrics-snapshot`:
  - `window_start: datetime` - Start of measurement window
  - `window_end: datetime` - End of measurement window
  - `sample_count: int` - Total number of operations measured
  - `p50_latency_ms: Optional[float]` - Median latency (None when no samples exist)
  - `p95_latency_ms: Optional[float]` - 95th percentile latency (None when no samples exist)
  - `p99_latency_ms: Optional[float]` - 99th percentile latency (None when no samples exist)
  - `error_rate: float` - Ratio of failed operations (0.0 to 1.0)
  - `token_usage: dict[str, int]` - Total tokens per model
  - `cost_usd: float` - Estimated cost in USD

- **LatencySample**: Internal representation of a single operation's latency measurement. Includes:
  - `operation: str` - Operation type (e.g., "model_call", "tool_call")
  - `latency_ms: float` - Duration in milliseconds
  - `timestamp: datetime` - When the operation completed
  - `event_id: str` - Unique identifier for deduplication

- **TokenUsageSample**: Internal representation of token consumption for a model call. Includes:
  - `model_name: str` - Model identifier (e.g., "gpt-4o", "qwen3-8b")
  - `prompt_tokens: int` - Input tokens
  - `completion_tokens: int` - Output tokens
  - `timestamp: datetime` - When the call completed
  - `event_id: str` - Unique identifier for deduplication

- **ErrorSample**: Internal representation of an error occurrence. Includes:
  - `operation: str` - Operation that failed
  - `timestamp: datetime` - When the error occurred
  - `event_id: str` - Unique identifier for deduplication

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Metrics collector subscribes to event bus within 100ms of initialization
- **SC-002**: `record_latency()` call completes in under 1ms (fire-and-forget, no blocking I/O)
- **SC-003**: `snapshot()` for a 1-hour window with 10,000 samples completes in under 100ms
- **SC-004**: 10 threads concurrently calling `record_*` methods for 1 minute produces no data corruption (all samples accounted for)
- **SC-005**: Percentile calculations (p50/p95/p99) match reference implementation (e.g., NumPy) within 1% error for sample sizes > 100
- **SC-006**: `cost_usd` calculation matches manual calculation within $0.001 USD for any given snapshot
- **SC-007**: System handles 1000 events/second from event bus without dropping samples or blocking event publishers
- **SC-008**: Memory usage grows linearly with sample count (no memory leaks over 24-hour run collecting 1M samples)

## Assumptions

- Event bus (F03) is already implemented and provides `EventBusProtocol` interface defined in F02 Phase 1 (`cross_cutting/logger.py`)
- Event payloads for `tool_call` / `model_response` follow the schema defined in `module_schemas.md#schema-event` and MUST include a unique `event_id` field (e.g., UUID string)
- Model pricing table is provided as a JSON configuration file with path specified via environment variable (e.g., `LANGAGENT_PRICING_TABLE_PATH`) or initialization parameter, with built-in default prices for common models (gpt-4o, gpt-4o-mini, qwen3-8b)
- Default pricing table format: `{"model_name": {"prompt": price_per_1k_tokens, "completion": price_per_1k_tokens}}`
- Metrics are stored in memory only - no disk persistence in this module (F09 exit_cleanup handles writing snapshots to disk)
- All timestamps use UTC timezone to avoid ambiguity
- Percentile calculation uses linear interpolation method (consistent with NumPy's default)
- `flush()` is called exactly once at the end of agent execution (by F09) - not designed for repeated flush-and-continue patterns
- Token usage metadata is present in `model_response` events (provided by F08 main_loop wrapping LangChain responses)
- Unknown models (not in pricing table) are accepted but contribute 0.0 to `cost_usd` - this is logged as a warning
- Event deduplication window (10 minutes) is sufficient to catch all retry scenarios; expired event_id entries are automatically removed from the deduplication set to prevent unbounded memory growth

## Dependencies

### Module Import Dependencies (from architecture_modules.md)
- **F02 Phase 1** (`cross_cutting_logger`): For `emit()` to log `la.cross_cutting.metrics.emit` tag and for `EventBusProtocol` interface definition
- **F03** (`protocol_event_bus`): Concrete implementation of `EventBusProtocol` to subscribe to events

### Runtime Call Dependencies
- None - this module is passively invoked via event bus subscriptions and explicit API calls from F09

### Initialization Responsibility
- **F06** (`runtime_startup`): MUST call `metrics_collector.initialize(event_bus, pricing_table_path)` during agent startup to subscribe to event bus. The initialization should occur after F03 event bus is ready but before any agent execution begins (i.e., in the "startup" phase per workflow.md).

### Dependents (Who Calls This Module)
- **F06** (`runtime_startup`): Calls `initialize()` during startup to subscribe to event bus
- **F09** (`runtime_exit_handler`): Calls `snapshot()` to generate final metrics before exit, calls `flush()` during cleanup
- **F03** (`protocol_event_bus`): Publishes events that trigger metrics recording
- **F08** (`runtime_main_loop_dispatcher`): Indirectly triggers metrics collection via events published to F03

## Out of Scope (Not Part of This Feature)

- Disk persistence of metrics snapshots (handled by F09 exit_cleanup)
- Real-time metrics dashboard or HTTP metrics endpoint (future v2 feature)
- Distributed metrics aggregation across multiple agent processes (single-process only in v1)
- Custom metric types beyond latency/tokens/errors (extensibility deferred to v2)
- Alerting or threshold-based notifications (future feature)
- Metrics retention policies or automatic cleanup of old samples (samples cleared only on `flush()`)
- Integration with external observability systems (Prometheus, Grafana, etc.) - future feature

## Technical Constraints

1. **Thread Safety**: All public APIs (`record_*`, `snapshot()`, `flush()`) MUST use locks to protect internal data structures
2. **No Blocking I/O**: `record_*` methods MUST NOT perform disk I/O, network calls, or other blocking operations
3. **Event Bus Protocol**: MUST use only the 4 mandatory methods of `EventBusProtocol` (`publish`, `subscribe`, `unsubscribe`, `flush`) - no dependency on F03-specific extensions like `publish_async` or `drain_events`
4. **Log Tag Whitelist**: `la.cross_cutting.metrics.emit` MUST be registered in F02 Phase 1's `ALLOWED_TAGS` (already part of 45-tag contract)
5. **No Hard-Coded Paths**: Pricing table path (if loaded from file) MUST be configurable, not hard-coded (宪法第 XIII 条)
6. **Type Safety**: All public APIs MUST pass `mypy --strict` with no type: ignore comments
7. **Immutability**: MetricsSnapshot MUST be a frozen dataclass to prevent mutation after creation

## Test Coverage Requirements (from F02 Feature Prompt §四.2)

Minimum 11 test cases covering:

1. `test_record_latency_increments_sample_count` - Verify 100 calls → `snapshot().sample_count == 100`
2. `test_snapshot_p50_latency` - Verify p50 ≈ 60ms for uniform 10-110ms distribution
3. `test_snapshot_p95_latency` - Verify p95 ≈ 100ms for same distribution
4. `test_snapshot_p99_latency` - Verify p99 ≈ 110ms for same distribution
5. `test_snapshot_error_rate` - Verify 5 errors in 100 operations → error_rate == 0.05
6. `test_snapshot_token_usage_by_model` - Verify per-model token aggregation
7. `test_snapshot_cost_usd` - Verify cost calculation with mock pricing table
8. `test_snapshot_window_filter` - Verify samples outside `[window_start, window_end]` excluded
9. `test_snapshot_returns_frozen_dataclass` - Verify immutability
10. `test_subscribe_to_event_bus` - Verify `model_response` event → `record_token_usage()` auto-called
11. `test_subscribe_to_event_bus_tool_call` - Verify `tool_call` event → `record_latency()` auto-called

Additional required tests (from clarification decisions):
- `test_event_deduplication_within_window` - Publish same event_id twice within 10 minutes → only first is recorded
- `test_event_deduplication_window_expiry` - Event_id older than 10 minutes can be reused
- `test_empty_snapshot_returns_none_percentiles` - No samples → p50/p95/p99 all return None, sample_count=0
- `test_pricing_table_from_json_file` - Load pricing from JSON config file at specified path
- `test_pricing_table_default_fallback` - When path not specified, use built-in default prices
- `test_malformed_event_missing_latency` - Event without `latency_ms` → log warning, skip event, no crash
- `test_malformed_event_missing_event_id` - Event without `event_id` → log warning, skip event, no crash
- Thread safety (concurrent `record_*` calls)
- Window validation (`window_end < window_start` → ValueError)
- Unknown model in pricing table (logs warning, contributes 0 to cost)

## Notes for Implementation

- Use `threading.Lock` for thread safety (simpler than asyncio for this use case)
- Store samples in memory as lists - optimize for append speed, not query speed (snapshots are infrequent)
- Use `dataclasses.dataclass(frozen=True)` for MetricsSnapshot
- Percentile calculation: use `statistics.quantiles()` (Python 3.8+) or NumPy if available. Return None for p50/p95/p99 when sample list is empty.
- Event handler functions registered with event bus should be thin wrappers that call `record_*` methods
- Consider using `collections.defaultdict(int)` for per-model token counting to avoid KeyError checks
- Mock `EventBusProtocol` in unit tests - do not depend on F03 concrete implementation during TDD phase
- F09 integration test (after F09 complete): verify `snapshot()` output is written to `~/.local/share/langagent/logs/<run-id>_metrics.json`
- **Event deduplication**: Use a set to store event_id values. Maintain a sliding 10-minute window by storing tuples `(event_id, timestamp)` and periodically purging entries older than 10 minutes. Alternative: use `collections.deque` with maxlen based on expected event rate.
- **Pricing table loading**: Default path should be `~/.local/share/langagent/pricing.json` or fallback to internal default dict. Environment variable `LANGAGENT_PRICING_TABLE_PATH` overrides default. JSON schema: `{"model_name": {"prompt": float, "completion": float}}` where prices are per 1K tokens.
- **Type hints**: Use `Optional[float]` for p50/p95/p99 fields in MetricsSnapshot dataclass to enable mypy strict mode validation.
