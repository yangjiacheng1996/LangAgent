# Feature Specification: F03 — Protocol Event Bus

**Feature Branch**: `003-protocol-event-bus`

**Created**: 2026-09-18

**Status**: Draft

**Input**: User description: "F03 — Protocol 层 Event 总线（protocol_event_bus）"

**Aligned with Constitution Article XV**: This specification has been created after reading the three mandatory top-level design artifacts:
1. `harness/top_level_design/workflow.md` (stage-main_loop event requirements)
2. `harness/top_level_design/architecture_modules.md` (mod-protocol-event-bus module definition)
3. `harness/top_level_design/module_schemas.md` (schema-event definition)

**Alignment Checklist**:
- Article I (Project Identity): Event bus is internal infrastructure, not SDK
- Article II (Tech Stack): Built on LangChain/LangGraph primitives
- Article III (LangSmith Decoupling): No LangSmith dependencies; self-contained event system
- Article IV (Model Abstraction): No direct model dependencies; consumes events from model interactions
- Article V (Agent Directory Contract): Supports agent lifecycle events
- Article VI (Agent Loop): Publishes tool_call/model_response events during main_loop
- Article VII (Middleware): Event bus integrates with middleware pipeline
- Article IX (Quality Diagnostics): Event bus is the Tracing/Monitoring foundation
- Article XIII (Hard No): No LangSmith, no hardcoded paths, TDD required

## Clarifications

### Session 2026-09-18

- Q: 当多个订阅者同时订阅同一个事件类型时，它们的执行顺序是否有保证？ → A: 按注册顺序执行（先注册先执行）
- Q: 当 flush() 超时时，那些尚未完成的 handler 会发生什么？ → A: 继续在后台运行直到完成
- Q: 如果事件的 event_id 生成出现重复（虽然概率很低），系统应该如何处理？ → A: 允许重复（依赖 UUID 的低碰撞概率）
- Q: 当调用 publish_async() 且多个 async handler 并发执行时，如果其中一个 handler 抛出异常，其他 handler 是否应该继续执行？ → A: 继续执行其他 handler（错误隔离）
- Q: 当 drain_events() 返回事件列表后，如果后续的 JSONL 文件写入失败，调用者是否有机会重新获取这些事件？ → A: drain 成功返回后，调用者负责保留事件列表并处理写入失败的重试

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Event Publication and Subscription (Priority: P1)

The runtime modules (F05, F08, F04) publish events during agent execution. Cross-cutting modules (F02 metrics_collector) subscribe to these events to collect observability data without creating tight coupling between layers.

**Why this priority**: Core event bus functionality - all other features depend on reliable pub/sub

**Independent Test**: Can be fully tested by publishing a single event and verifying subscriber receives it, demonstrating the foundational pub/sub mechanism works

**Acceptance Scenarios**:

1. **Given** a subscriber registered for `tool_call` events, **When** a `tool_call` event is published, **Then** the subscriber handler is invoked exactly once with the event
2. **Given** no subscribers for `model_response` events, **When** a `model_response` event is published, **Then** no error occurs and execution continues
3. **Given** three subscribers for the same event type, **When** that event is published, **Then** all three handlers are invoked in registration order (FIFO)

---

### User Story 2 - Error Isolation (Priority: P1)

When a subscriber handler throws an exception, other subscribers continue to receive events. The system logs the error but maintains stability.

**Why this priority**: Critical for system reliability - one faulty subscriber must not break the entire event pipeline

**Independent Test**: Can be tested by registering two handlers where one throws an exception, verifying the second handler still executes

**Acceptance Scenarios**:

1. **Given** two subscribers where handler A throws an exception, **When** an event is published, **Then** handler B still receives and processes the event
2. **Given** a handler that throws an exception, **When** an event is published, **Then** an `event_handler_error` log is emitted with error details
3. **Given** a handler that fails, **When** subsequent events are published, **Then** the same handler continues to be invoked (no permanent blacklisting)

---

### User Story 3 - Async Handler Support (Priority: P2)

Subscribers can register async handlers for long-running operations (e.g., writing to external systems). The event bus properly awaits async handlers.

**Why this priority**: Needed for real-world integrations but not blocking basic functionality

**Independent Test**: Can be tested by registering an async handler that performs an awaitable operation and verifying completion

**Acceptance Scenarios**:

1. **Given** an async handler registered for an event type, **When** an event is published via `publish_async()`, **Then** the async handler is properly awaited
2. **Given** multiple async handlers, **When** an event is published, **Then** all handlers run concurrently via `asyncio.gather` with error isolation (return_exceptions=True)
3. **Given** a mix of sync and async handlers, **When** `publish_async()` is called, **Then** sync handlers are wrapped as coroutines and all execute
4. **Given** one async handler throws an exception, **When** multiple async handlers are executing, **Then** other handlers continue to completion

---

### User Story 4 - Graceful Shutdown (Priority: P2)

During exit_cleanup stage, the system calls `flush()` to ensure all pending event handlers complete before writing final reports.

**Why this priority**: Important for data integrity but can be implemented after core pub/sub works

**Independent Test**: Can be tested by publishing events with slow handlers and verifying `flush()` blocks until completion

**Acceptance Scenarios**:

1. **Given** pending event handlers running, **When** `flush(timeout=5.0)` is called, **Then** the call blocks until all handlers complete or timeout occurs
2. **Given** handlers complete within timeout, **When** `flush()` returns, **Then** all handlers have finished execution
3. **Given** handlers exceed timeout, **When** `flush()` times out, **Then** an `event_handler_error` log is emitted but no exception is thrown

---

### User Story 5 - Event Drainage for Persistence (Priority: P2)

The exit handler collects all accumulated events via `drain_events()` to write them to the JSONL log file. This provides a complete audit trail.

**Why this priority**: Required for F09 cleanup integration but depends on core event bus first

**Independent Test**: Can be tested by publishing events and verifying `drain_events()` returns them all and clears the buffer

**Acceptance Scenarios**:

1. **Given** 5 events have been published, **When** `drain_events()` is called, **Then** all 5 events are returned in order
2. **Given** events have been drained once, **When** 3 new events are published and `drain_events()` is called again, **Then** only the 3 new events are returned
3. **Given** no events in buffer, **When** `drain_events()` is called, **Then** an empty list is returned without error

---

### Edge Cases

- What happens when `publish()` is called with an unregistered event type? → Throws `UnknownEventTypeError` with exit code 78
- How does the system handle concurrent publish from multiple threads? → Uses `threading.Lock` to protect subscriber list and event buffer
- What if `drain_events()` is called during active event publishing? → Thread-safe lock ensures either operation completes atomically
- What happens if event payload contains non-JSON-serializable objects (e.g., `BaseMessage`)? → Caller must use `langchain_core.messages.message_to_dict` before constructing Event
- What if `flush()` is called when no handlers are pending? → Returns immediately without blocking
- What if `unsubscribe()` is called multiple times with the same token? → Idempotent operation, no error thrown
- What if `flush()` timeout expires with handlers still running? → Handlers continue in background until completion; `event_handler_error` log emitted but no exception thrown
- What if duplicate `event_id` values are generated? → Allowed; UUID v4 collision probability is negligible (~10^-18); events distinguishable by other fields (emitted_at, source)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST implement a publish/subscribe event bus where modules can publish events without knowing subscribers
- **FR-002**: System MUST support synchronous event publication via `publish(event: Event)` that invokes all subscribers in registration order (FIFO) before returning
- **FR-003**: System MUST support asynchronous event handlers via `publish_async(event: Event)` that properly awaits async functions using `asyncio.gather(return_exceptions=True)` for error isolation
- **FR-004**: System MUST isolate handler exceptions so one failing subscriber does not prevent other subscribers from executing
- **FR-005**: System MUST log handler exceptions using the `la.cross_cutting.event_handler_error` tag via F02 logger interface
- **FR-006**: System MUST maintain an internal error counter for handler failures (not exposed in MetricsSnapshot, internal diagnostic only)
- **FR-007**: System MUST be thread-safe using `threading.RLock` to protect subscriber list and event buffer from race conditions
- **FR-008**: System MUST enforce an event type whitelist containing at least 13 registered types (tool_call, tool_result, model_response, guardrail_block, skill_loaded, skill_load_failed, tool_registered, graph_composed, eval_task_started, eval_task_done, audit_written, metrics_snapshot, event_handler_error)
- **FR-009**: System MUST throw `UnknownEventTypeError` when attempting to publish an event type not in the whitelist
- **FR-010**: System MUST provide `subscribe(event_type, handler)` that returns a `SubscriptionToken` for later unsubscription
- **FR-011**: System MUST provide `unsubscribe(token)` that removes the handler and is idempotent (can be called multiple times safely)
- **FR-012**: System MUST provide `flush(timeout: float = 5.0)` that blocks until all pending handlers complete or timeout occurs
- **FR-013**: System MUST emit `event_handler_error` log (not throw exception) when `flush()` timeout expires with incomplete handlers
- **FR-014**: System MUST maintain internal `_event_buffer: list[Event]` protected by threading.Lock for event accumulation
- **FR-015**: System MUST provide `drain_events() -> list[Event]` that returns all accumulated events and clears the buffer atomically
- **FR-016**: System MUST throw `EventDrainError` (exit code 4) only if drain operation itself fails due to IO error; once events are returned to caller, the caller is responsible for persistence and retry
- **FR-017**: System MUST ensure `drain_events()` is not reentrant - second call returns empty list if no events published since last drain
- **FR-018**: System MUST support concurrent publish operations from multiple threads without data loss or corruption
- **FR-019**: System MUST allow subscribe/unsubscribe calls during event publication without causing runtime errors
- **FR-020**: Event payload MUST be JSON-serializable dict (LangChain types like BaseMessage must be pre-converted using message_to_dict)

### Key Entities

- **Event**: 6-field immutable data structure (event_id, event_type, emitted_at, source, payload, trace_id) representing a single system occurrence
- **SubscriptionToken**: Opaque handle returned by subscribe() used to unsubscribe a specific handler
- **EventBus**: Central registry managing subscribers and dispatching events to registered handlers
- **EventHandler**: Callable function `(Event) -> None` or async function `async (Event) -> None` that processes events
- **EventBuffer**: Internal list accumulating all published events for later drainage by F09 exit handler

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Event publication latency (time from publish call to all handlers invoked) remains under 10ms for 3 subscribers on single event
- **SC-002**: System successfully publishes and delivers 1,000 events per second without event loss or memory leak
- **SC-003**: Handler exception isolation verified - 100% of remaining handlers execute even when one handler fails in 100% of test cases
- **SC-004**: Thread safety verified - 10 concurrent threads publishing 100 events each results in exactly 1,000 events in buffer with no corruption
- **SC-005**: Flush operation completes within timeout for 95% of test cases with handlers completing in under 5 seconds
- **SC-006**: Drain operation successfully retrieves all accumulated events in 100% of non-failure cases
- **SC-007**: Whitelist enforcement blocks 100% of unregistered event types with appropriate error message
- **SC-008**: Zero unhandled exceptions reach the publish caller from subscriber handler failures

## Assumptions

- F02 cross_cutting_logger module is already implemented and provides the `emit()` interface that F03 will use for logging
- F02 provides the `EventBusProtocol` interface definition that F03's `EventBus` class must implement
- Event publishers (F05, F08, F04, F09, F11) will properly convert LangChain message objects to dicts before creating Events
- The 13 initial event types in the whitelist are sufficient for the first batch of features (F02-F11)
- Module importing F03 will catch `UnknownEventTypeError` and `EventDrainError` and map them to appropriate exit codes
- F09 exit_cleanup handler will call `flush()` before `drain_events()` to ensure all handlers complete before event persistence
- No circular import issues exist between F03 protocol_event_bus and F02 cross_cutting_logger (F03 imports logger, logger doesn't import event_bus)
- Async event handlers are only used with `publish_async()` - calling `publish()` with async handlers is not supported
- Event buffer does not need size limits for v1 (unbounded growth acceptable for single agent run lifetime)
- System has sufficient memory to hold all events in buffer until drain (typical runs produce < 10,000 events)
