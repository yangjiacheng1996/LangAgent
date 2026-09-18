# Implementation Plan: F02 Phase 2 - Metrics Collector

**Branch**: `002-metrics-collector-phase2` | **Date**: 2026-09-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-metrics-collector-phase2/spec.md`

**Constitutional Alignment**: 已对齐宪法第 XV 条（顶层设计优先）- 本计划基于 `harness/top_level_design/` 三份 artefact 制定

## Summary

F02 Phase 2 实现 `cross_cutting_metrics_collector` 模块，通过订阅 F03 event bus 的 `tool_call` / `model_response` / `eval_task_started` / `eval_task_done` 事件，自动收集性能指标（latency / token usage / error rate），按时间窗口聚合后产出 `MetricsSnapshot`。

**技术方法**：
- 使用内存列表存储样本（优化追加速度）
- `threading.Lock` 保证线程安全
- 10 分钟滚动窗口去重 event_id（Python set）
- `statistics.quantiles()` 计算百分位延迟
- JSON 配置文件加载模型定价表
- 冻结 dataclass 返回不可变快照

## Technical Context

**Language/Version**: Python 3.11+ (per `pyproject.toml` `requires-python` field)

**Primary Dependencies**: 
- Python stdlib: `threading`, `dataclasses`, `collections`, `statistics`, `datetime`, `json`
- F02 Phase 1: `cross_cutting_logger` (for `emit()` and `EventBusProtocol` interface)
- F03: `protocol_event_bus` (concrete `EventBusProtocol` implementation)

**Storage**: In-memory only (lists for samples, set for event_id deduplication). No disk persistence in this module; F09 `exit_cleanup` writes snapshots to disk.

**Testing**: pytest with mocking for `EventBusProtocol`; thread safety tests with concurrent execution

**Target Platform**: Linux server (same as LangAgent runtime)

**Project Type**: Internal module (part of LangAgent cross_cutting layer, not exposed as public API)

**Performance Goals**: 
- `record_latency()` < 1ms (fire-and-forget, no blocking I/O)
- `snapshot()` < 100ms for 10K samples
- Handle 1000 events/second without dropping samples
- Linear memory growth (no leaks over 24h / 1M samples)

**Constraints**: 
- Thread-safe: concurrent `record_*` and `snapshot()` calls
- No blocking I/O in `record_*` methods
- Use only 4 mandatory `EventBusProtocol` methods (no F03 extensions)
- Percentile calculations within 1% of NumPy reference
- Event deduplication window: 10 minutes (~21MB memory)

**Scale/Scope**: 
- Single agent execution session (not distributed)
- Expected event rate: 10-100 events/second typical, 1000 events/second max
- Deduplication window: 600K event_id entries (10 min × 1000 events/sec)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 宪法对齐检查清单

| 条款 | 对齐状态 | 说明 |
|------|----------|------|
| 第 I 条（项目身份与边界） | ✅ PASS | 本模块不暴露公开 API，仅作为 LangAgent 内部横切层基础设施 |
| 第 II 条（技术栈与依赖范围） | ✅ PASS | 仅依赖 Python stdlib + F02 Phase 1 + F03，无外部第三方库 |
| 第 III 条（LangSmith 剥离原则） | ✅ PASS | 自研指标收集，日志 tag 使用 `la.cross_cutting.metrics.emit` |
| 第 VIII 条（TDD 刚性约束） | ✅ PASS | 18+ 测试用例覆盖所有功能需求，Red-Green-Refactor 流程 |
| 第 IX 条（质量诊断能力矩阵） | ✅ PASS | 实现 Monitoring 子能力，产出 MetricsSnapshot 时序指标 |
| 第 XII 条（配置与可观测契约） | ✅ PASS | 定价表通过环境变量 `LANGAGENT_PRICING_TABLE_PATH` 配置 |
| 第 XIII 条（Hard No） | ✅ PASS | 无硬编码路径（定价表路径可配置）；使用结构化日志（emit） |
| 第 XV 条（顶层设计优先） | ✅ PASS | 已读取三份 artefact；模块设计与 `architecture_modules.md#mod-cross-cutting-metrics-collector` 对齐 |

### 依赖方向校验

| 依赖关系 | 允许状态 | 说明 |
|----------|----------|------|
| `cross_cutting_metrics_collector → cross_cutting_logger` | ✅ ALLOWED | 同层依赖，用于日志发射 |
| `cross_cutting_metrics_collector → protocol_event_bus` | ✅ ALLOWED | 订阅事件（依赖反转，使用 EventBusProtocol 接口） |
| `cross_cutting_metrics_collector → runtime_*` | ❌ FORBIDDEN | 横切层不依赖业务层 |
| `cross_cutting_metrics_collector → cli_*` | ❌ FORBIDDEN | 横切层不依赖 CLI 层 |
| `cross_cutting_metrics_collector → primitives_*` | ❌ FORBIDDEN | 横切层不依赖 primitives 层 |

**GATE RESULT**: ✅ PASS - 无宪法违反，可进入 Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/002-metrics-collector-phase2/
├── plan.md              # This file (/speckit.plan command output)
├── spec.md              # Feature specification (already created)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (if applicable)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
langagent/
├── cross_cutting/
│   ├── logger.py                    # F02 Phase 1 (already implemented)
│   ├── metrics_collector.py         # F02 Phase 2 (this feature)
│   ├── audit_recorder.py            # F04
│   ├── guardrail_middleware.py      # F04
│   └── stage_guard.py               # F06
├── protocol/
│   ├── event_bus.py                 # F03 (already implemented)
│   └── ...
└── primitives/
    └── ...

tests/
├── cross_cutting/
│   ├── test_logger.py               # F02 Phase 1 tests
│   ├── test_metrics_collector.py    # F02 Phase 2 tests (this feature)
│   └── test_event_bus_protocol.py   # F02 Phase 1 protocol contract tests
└── fixtures/
    ├── pricing_table_default.json   # Default model pricing
    └── pricing_table_test.json      # Test pricing for unit tests
```

**Structure Decision**: Single Python project with layered architecture (5 layers: cli / runtime / protocol / cross_cutting / primitives). F02 Phase 2 adds `metrics_collector.py` to existing `langagent/cross_cutting/` directory. Tests follow parallel directory structure in `tests/cross_cutting/`.

## Complexity Tracking

> No Constitution Check violations - this section is empty.

---

## Phase 0: Research & Technical Investigation

### Research Questions

Based on Technical Context and spec clarifications, the following areas require research:

1. **Event Deduplication Window Management**
   - Decision: How to implement a time-based sliding window for event_id deduplication?
   - Options: (a) Store `(event_id, timestamp)` tuples and periodically purge old entries, (b) Use `collections.deque` with maxlen, (c) Use `sortedcontainers.SortedDict` for efficient time-range queries
   - Rationale needed: Balance memory efficiency vs. simplicity vs. thread-safety

2. **Percentile Calculation Method**
   - Decision: Use `statistics.quantiles()` (stdlib) or NumPy?
   - Options: (a) `statistics.quantiles()` (no dependencies), (b) NumPy if available with stdlib fallback, (c) Custom interpolation
   - Rationale needed: Accuracy vs. dependency minimization

3. **Pricing Table Default Location**
   - Decision: Where should the default pricing table file be located?
   - Options: (a) `~/.config/langagent/pricing.json`, (b) `~/.local/share/langagent/pricing.json`, (c) Bundled in package data
   - Rationale needed: Follow XDG Base Directory Specification vs. LangAgent convention

4. **Thread Safety Pattern**
   - Decision: Single lock vs. multiple locks (read-write lock, per-sample-type locks)?
   - Options: (a) Single `threading.Lock` for all operations, (b) `threading.RLock` for reentrant calls, (c) Separate locks for samples vs. deduplication set
   - Rationale needed: Simplicity vs. concurrency performance

### Research Tasks

1. **Event Deduplication Window Management**
   - Research: Python collections best practices for time-based expiry
   - Investigate: `collections.deque` maxlen behavior (FIFO eviction)
   - Benchmark: Memory overhead of `(event_id, timestamp)` tuples vs. set-only approach
   - **Decision**: Use set with periodic purging (simpler, thread-safe with single lock)

2. **Percentile Calculation Method**
   - Research: `statistics.quantiles()` accuracy (PEP 615)
   - Compare: Linear interpolation method (NumPy default) vs. exclusive method
   - Verify: 1% tolerance achievable with stdlib
   - **Decision**: Use `statistics.quantiles()` with `method='exclusive'` for NumPy compatibility

3. **Pricing Table Default Location**
   - Research: Existing LangAgent data directory conventions
   - Check: `~/.local/share/langagent/` already used for logs (per spec.md FR-009 note)
   - Verify: F09 exit_cleanup writes to `~/.local/share/langagent/logs/`
   - **Decision**: Use `~/.local/share/langagent/pricing.json` for consistency with logs directory

4. **Thread Safety Pattern**
   - Research: Python GIL impact on `threading.Lock` contention
   - Investigate: Read-write lock benefits for high-read, low-write workloads
   - Benchmark: Single lock vs. per-type locks for 1000 events/second
   - **Decision**: Single `threading.Lock` (simpler, sufficient for performance goals)

---

## Phase 1: Design & Contracts

### Data Model

See [data-model.md](./data-model.md) for complete entity definitions.

**Summary**:

- **MetricsSnapshot** (frozen dataclass): 9 fields per `module_schemas.md#schema-metrics-snapshot`
  - `window_start`, `window_end`: datetime (UTC)
  - `sample_count`: int
  - `p50_latency_ms`, `p95_latency_ms`, `p99_latency_ms`: Optional[float] (None when no samples)
  - `error_rate`: float (0.0 to 1.0)
  - `token_usage`: dict[str, int] (model_name → total_tokens)
  - `cost_usd`: float

- **LatencySample** (internal dataclass): 4 fields
  - `operation`: str (e.g., "tool_call", "model_call")
  - `latency_ms`: float
  - `timestamp`: datetime (UTC)
  - `event_id`: str (UUID for deduplication)

- **TokenUsageSample** (internal dataclass): 5 fields
  - `model_name`: str
  - `prompt_tokens`: int
  - `completion_tokens`: int
  - `timestamp`: datetime (UTC)
  - `event_id`: str

- **ErrorSample** (internal dataclass): 3 fields
  - `operation`: str
  - `timestamp`: datetime (UTC)
  - `event_id`: str

### Interface Contracts

See [contracts/](./contracts/) for detailed API contracts.

**Public API** (`langagent/cross_cutting/metrics_collector.py`):

```python
def record_latency(operation: str, ms: float) -> None:
    """记录单次操作延迟。线程安全，fire-and-forget（< 1ms）。"""

def record_token_usage(model_name: str, prompt: int, completion: int) -> None:
    """记录 token 消耗。线程安全，fire-and-forget。"""

def record_error(operation: str) -> None:
    """记录错误计数。线程安全，fire-and-forget。"""

def snapshot(window_start: datetime, window_end: datetime) -> MetricsSnapshot:
    """生成时间窗口指标快照。线程安全，返回冻结 dataclass。
    
    Raises:
        ValueError: 当 window_end < window_start 时
    """

def flush() -> None:
    """清空所有累积指标（样本数据 + event_id 去重窗口）。
    
    由 F09 exit_cleanup 调用。线程安全。
    """

def initialize(event_bus: EventBusProtocol, pricing_table_path: str | None = None) -> None:
    """初始化指标收集器，订阅事件总线。
    
    Args:
        event_bus: F03 事件总线实例（实现 EventBusProtocol）
        pricing_table_path: 可选定价表路径（默认 ~/.local/share/langagent/pricing.json）
    """
```

**Event Bus Integration** (via `EventBusProtocol` from F02 Phase 1):

- Subscribe to 4 event types: `tool_call`, `model_response`, `eval_task_started`, `eval_task_done`
- Event payload requirements:
  - All events MUST include `event_id: str` (UUID)
  - `tool_call`: `{"event_id": str, "operation": str, "latency_ms": float, "timestamp": ISO8601}`
  - `model_response`: `{"event_id": str, "model_name": str, "prompt_tokens": int, "completion_tokens": int, "timestamp": ISO8601}`
  - `eval_task_started` / `eval_task_done`: `{"event_id": str, "timestamp": ISO8601}` (latency calculated from delta)

**Pricing Table JSON Schema** (`~/.local/share/langagent/pricing.json`):

```json
{
  "model_name": {
    "prompt": 0.005,      // USD per 1K tokens
    "completion": 0.015   // USD per 1K tokens
  },
  "gpt-4o": {
    "prompt": 0.005,
    "completion": 0.015
  },
  "gpt-4o-mini": {
    "prompt": 0.00015,
    "completion": 0.0006
  },
  "qwen3-8b": {
    "prompt": 0.0,        // Free for internal vLLM
    "completion": 0.0
  }
}
```

### Quickstart Validation Guide

See [quickstart.md](./quickstart.md) for runnable validation scenarios.

**Quick validation steps**:

1. **Basic Metrics Collection**:
   ```python
   from langagent.cross_cutting.metrics_collector import record_latency, snapshot
   from datetime import datetime, timezone
   
   # Record some latencies
   for i in range(100):
       record_latency("test_operation", 10 + i)
   
   # Generate snapshot
   window_start = datetime.now(timezone.utc)
   window_end = datetime.now(timezone.utc)
   snap = snapshot(window_start, window_end)
   
   assert snap.sample_count == 100
   assert snap.p50_latency_ms > 0
   ```

2. **Event Bus Integration**:
   ```python
   from langagent.cross_cutting.metrics_collector import initialize
   from langagent.protocol.event_bus import EventBus
   
   event_bus = EventBus()
   initialize(event_bus, pricing_table_path="/path/to/test_pricing.json")
   
   # Publish test event
   event_bus.publish("tool_call", {
       "event_id": "test-uuid-123",
       "operation": "web_search",
       "latency_ms": 250.0,
       "timestamp": "2026-09-18T10:00:00+00:00"
   })
   
   # Verify automatic recording
   snap = snapshot(window_start, window_end)
   assert snap.sample_count == 1
   ```

3. **Thread Safety**:
   ```python
   import threading
   
   def worker():
       for _ in range(1000):
           record_latency("concurrent_op", 50.0)
   
   threads = [threading.Thread(target=worker) for _ in range(10)]
   for t in threads: t.start()
   for t in threads: t.join()
   
   snap = snapshot(window_start, window_end)
   assert snap.sample_count == 10000  # No lost samples
   ```

---

## Phase 2: Task Breakdown

**Note**: Detailed task breakdown will be generated by `/speckit.tasks` command. This section provides a high-level preview.

### Implementation Tasks (Preview)

1. **Core Data Structures** (TDD Red phase)
   - Define `LatencySample`, `TokenUsageSample`, `ErrorSample` dataclasses
   - Define `MetricsSnapshot` frozen dataclass with Optional[float] percentiles
   - Write failing tests for dataclass immutability

2. **Event Deduplication** (TDD Red-Green-Refactor)
   - Implement event_id set with timestamp tracking
   - Implement 10-minute rolling window purge logic
   - Write tests: duplicate detection, window expiry, thread safety

3. **Sample Recording** (TDD Red-Green-Refactor)
   - Implement `record_latency()` with locking
   - Implement `record_token_usage()` with locking
   - Implement `record_error()` with locking
   - Write tests: basic recording, thread safety, performance (<1ms)

4. **Percentile Calculation** (TDD Red-Green-Refactor)
   - Implement `_calculate_percentiles()` using `statistics.quantiles()`
   - Handle empty sample case (return None)
   - Write tests: p50/p95/p99 accuracy, empty samples, 1% tolerance

5. **Snapshot Generation** (TDD Red-Green-Refactor)
   - Implement `snapshot()` with time window filtering
   - Implement error_rate calculation
   - Implement token_usage aggregation
   - Implement cost_usd calculation with pricing table
   - Write tests: window filtering, aggregation, frozen dataclass

6. **Pricing Table** (TDD Red-Green-Refactor)
   - Implement JSON loading with default path fallback
   - Implement environment variable override (`LANGAGENT_PRICING_TABLE_PATH`)
   - Handle missing models (log warning, contribute 0 to cost)
   - Write tests: file loading, env var, unknown models

7. **Event Bus Integration** (TDD Red-Green-Refactor)
   - Implement `initialize()` with EventBusProtocol subscription
   - Implement event handlers for 4 event types
   - Handle malformed events (missing fields → log warning, skip)
   - Write tests: event subscription, handler invocation, malformed events

8. **Flush Implementation** (TDD Red-Green-Refactor)
   - Implement `flush()` to clear samples and deduplication window
   - Ensure thread safety during flush
   - Write tests: data clearing, concurrent flush, idempotency

---

## Next Steps

1. ✅ **Phase 0 Complete**: Research decisions documented above
2. ✅ **Phase 1 Complete**: Data model and contracts defined (see linked files)
3. ⏭️ **Ready for `/speckit.tasks`**: Detailed TDD task breakdown
4. ⏭️ **Ready for Implementation**: Once tasks generated, proceed with Red-Green-Refactor cycle

---

## References

- **Spec**: [spec.md](./spec.md)
- **Constitution**: `../../.specify/memory/constitution.md`
- **Top-Level Design**:
  - `../../harness/top_level_design/workflow.md` (6 阶段工作流)
  - `../../harness/top_level_design/architecture_modules.md#mod-cross-cutting-metrics-collector`
  - `../../harness/top_level_design/module_schemas.md#schema-metrics-snapshot`
- **Related Features**:
  - F02 Phase 1: `../002-cross-cutting-logger-phase1/` (logger + EventBusProtocol)
  - F03: `../003-protocol-event-bus/` (EventBus implementation)
  - F09: TBD (exit_cleanup will call snapshot() and flush())
