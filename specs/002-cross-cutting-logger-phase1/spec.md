# Feature Specification: Cross-Cutting Logger + EventBusProtocol (F02 Phase 1)

**Feature Branch**: `002-cross-cutting-logger-phase1`

**Created**: 2026-09-18

**Status**: Draft

**Constitutional Alignment**: This specification adheres to Constitution Article XV (Top-Level Design Primacy) and has been derived from the following top-level design artifacts:
- `harness/top_level_design/workflow.md` - Log tags, exit codes, and 6-stage workflow
- `harness/top_level_design/architecture_modules.md` - Module dependencies and layer constraints
- `harness/top_level_design/module_schemas.md` - Span, Trace, and MetricsSnapshot schemas

**Input**: User description: "F02 Phase 1 — Implement cross_cutting_logger module with structured logging (emit/set_level/drain_spans), EventBusProtocol interface definition, 45-item log tag whitelist (not 46), redaction, and thread-safety"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Structured Logging with Tag Whitelist (Priority: P1)

As a LangAgent runtime developer, I need to emit structured logs with validated tags so that all observability events are consistently formatted and easily parseable by monitoring tools.

**Why this priority**: This is the foundation of LangAgent's observability system. Without structured logging, no other feature (metrics, audit, tracing) can function properly. All 9 features (F01, F03-F11) depend on this capability.

**Independent Test**: Can be fully tested by calling `emit()` with valid/invalid tags and verifying stderr output contains both human-readable text and JSONL format with proper tag validation.

**Acceptance Scenarios**:

1. **Given** logger is initialized, **When** developer calls `emit("la.runtime.dir_load.ok", {"agent_dir": "/tmp/agent"})`, **Then** stderr contains both text line `[la.runtime.dir_load.ok]` and JSONL line with `tag`, `timestamp`, `payload` fields
2. **Given** logger is initialized, **When** developer calls `emit("invalid.tag", {})`, **Then** system raises `UnknownLogTagError` immediately
3. **Given** logger is initialized with 45-item whitelist, **When** developer calls `emit()` with any of the 45 registered tags, **Then** emission succeeds without validation error
4. **Given** logger is initialized, **When** 10 threads concurrently call `emit()`, **Then** all log lines appear in stderr without interleaving or corruption

---

### User Story 2 - Secret Redaction (Priority: P1)

As a security-conscious developer, I need automatic redaction of sensitive fields so that API keys and secrets are never exposed in log files or stderr output.

**Why this priority**: Security requirement - leaking secrets in logs is a critical vulnerability. Must be implemented atomically with logging to prevent any window of exposure.

**Independent Test**: Can be fully tested by calling `emit()` with payloads containing `api_key`, `password`, `secret`, or `token` fields and verifying output shows `***` instead of actual values.

**Acceptance Scenarios**:

1. **Given** logger is initialized, **When** developer calls `emit("la.runtime.model_adapt.start", {"api_key": "sk-xxx"})`, **Then** stderr output contains `"api_key": "***"` not `"sk-xxx"`
2. **Given** logger is initialized, **When** payload contains nested dict `{"model": {"token": "abc123"}}`, **Then** output shows `"token": "***"` (deep traversal)
3. **Given** logger is initialized, **When** payload contains `{"input_tokens": 100, "output_tokens": 50}`, **Then** output shows actual values (not redacted, exact field name match only)

---

### User Story 3 - Log Level Filtering (Priority: P2)

As a production operator, I need to adjust log verbosity at runtime so that I can reduce noise during normal operation and increase detail during debugging.

**Why this priority**: Operational requirement - excessive logging can overwhelm stderr and impact performance. Can be implemented after basic logging works.

**Independent Test**: Can be fully tested by calling `set_level("ERROR")` and then emitting INFO-level logs, verifying they don't appear in output.

**Acceptance Scenarios**:

1. **Given** logger is set to `ERROR` level, **When** developer calls `emit("la.runtime.dir_load.ok", ...)` (INFO level), **Then** no output appears in stderr
2. **Given** logger is set to `DEBUG` level, **When** developer emits logs at any level, **Then** all logs appear in stderr
3. **Given** logger is initialized, **When** developer calls `set_level("INVALID")`, **Then** system raises exception with clear error message

---

### User Story 4 - Span Buffer for Tracing (Priority: P2)

As a runtime developer implementing cleanup (F09), I need to retrieve accumulated span logs so that I can persist them to disk in `logs/<run-id>.jsonl` during exit_cleanup phase.

**Why this priority**: Required for F09 integration but not blocking for basic logging. Spans are a specialized subset of logs with `"kind": "span"` in payload.

**Independent Test**: Can be fully tested by emitting multiple logs with `{"kind": "span", ...}` fields, calling `drain_spans()`, and verifying returned list contains exactly those span logs with buffer cleared afterward.

**Acceptance Scenarios**:

1. **Given** logger has received 5 span emits, **When** developer calls `drain_spans()`, **Then** returns list of 5 Span objects and buffer is cleared
2. **Given** logger has received 3 span emits and 2 non-span emits, **When** developer calls `drain_spans()`, **Then** returns list of 3 Span objects only
3. **Given** empty span buffer, **When** developer calls `drain_spans()`, **Then** returns empty list without error
4. **Given** 10 threads concurrently emit spans and drain, **When** operations complete, **Then** no spans are lost or duplicated

---

### User Story 5 - EventBusProtocol Interface Definition (Priority: P3)

As a protocol layer developer implementing F03, I need a well-defined EventBusProtocol interface so that I can implement event bus with guaranteed contract compatibility.

**Why this priority**: Interface definition has no runtime behavior - it's a type contract. Can be finalized last since F03 implementation happens in Phase 2/Batch 3.

**Independent Test**: Can be fully tested by creating a mock class implementing EventBusProtocol and verifying mypy --strict type checking passes for all 4 required methods (publish/subscribe/unsubscribe/flush).

**Acceptance Scenarios**:

1. **Given** EventBusProtocol is defined in logger.py, **When** F03 developer creates `class EventBus(EventBusProtocol)`, **Then** mypy validates all 4 methods are present with correct signatures
2. **Given** EventBusProtocol is defined, **When** F02 metrics_collector (Phase 2) consumes the protocol, **Then** type hints allow `event_bus.subscribe("model_response", callback)` calls

---

### Edge Cases

- What happens when `emit()` is called with a payload that is not a dict? **Must raise TypeError immediately**
- What happens when logger fails to write to stderr (e.g., pipe broken)? **Must not raise exception to caller; log failure once to stderr with `logger_emit_failed` tag (fire-and-forget semantics)**
- What happens when `drain_spans()` is called during concurrent span emissions? **Must use locks to ensure thread-safety; no spans lost**
- What happens when payload contains 1000+ nested dicts with secrets? **Redaction must handle arbitrary depth without stack overflow**
- What happens when tag whitelist is accidentally modified at runtime? **Whitelist must be frozenset; any modification attempt fails**

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST emit structured logs to stderr in dual format (human-readable text + JSONL) simultaneously
- **FR-002**: System MUST validate all log tags against a whitelist of at least 45 registered tags before emission
- **FR-003**: System MUST raise `UnknownLogTagError` when `emit()` is called with an unregistered tag
- **FR-004**: System MUST redact exact field names `api_key`, `password`, `secret`, `token` by replacing values with `***`
- **FR-005**: System MUST NOT redact fields like `input_tokens`, `output_tokens`, `total_tokens` (substring match must not trigger redaction)
- **FR-006**: System MUST traverse nested dicts and lists recursively during redaction
- **FR-007**: System MUST filter log emissions based on configured level (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- **FR-008**: System MUST accept only the 5 standard log levels; reject invalid levels with exception
- **FR-009**: System MUST accumulate logs with `payload.kind == "span"` in an internal buffer
- **FR-010**: System MUST return accumulated spans as `list[Span]` when `drain_spans()` is called and clear the buffer atomically
- **FR-011**: System MUST NOT clear span buffer when `drain_spans()` fails (allows caller retry)
- **FR-012**: System MUST be thread-safe for concurrent `emit()` and `drain_spans()` calls (use locks)
- **FR-013**: System MUST include ISO8601 timestamp in JSONL output (format: `2026-09-15T10:30:00.123456+08:00`)
- **FR-014**: System MUST NOT write logs to stdout (stdout reserved for user-facing dialogue per workflow.md)
- **FR-015**: System MUST define `EventBusProtocol` as a Protocol class with 4 required methods: `publish`, `subscribe`, `unsubscribe`, `flush`
- **FR-016**: System MUST NOT implement EventBus (implementation is F03's responsibility)
- **FR-017**: System MUST NOT raise exceptions from `emit()` on I/O failure (fire-and-forget semantics)
- **FR-018**: System MUST store whitelist as `ALLOWED_TAGS: frozenset[str]` at module level
- **FR-019**: System MUST define Span dataclass with 7 fields: trace_id, span_id, parent_span_id, name, start, end, attributes
- **FR-020**: System MUST validate payload is dict type before processing; raise TypeError otherwise

### Key Entities *(include if feature involves data)*

- **Span**: Represents a single trace span with timing information (7 fields per module_schemas.md)
- **LogTag**: String identifier from 45-item whitelist organized into 3 namespaces (la.lifecycle.* - 12 tags, la.runtime.* - 29 tags, la.cross_cutting.* - 4 tags)
- **EventBusProtocol**: Protocol interface defining the contract for event bus implementations (4 required methods)
- **LogLevel**: Enum or Literal type with 5 values (DEBUG, INFO, WARNING, ERROR, CRITICAL)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 28 test cases defined in tasks.md pass (19 tests in test_logger.py: 7 US1 + 4 US2 + 2 US3 + 6 US4; 5 EventBusProtocol tests in test_event_bus_protocol.py; 4 validation scripts in Phase 8)
- **SC-002**: All 6 test cases in section 4.1b (drain_spans tests) pass
- **SC-003**: mypy --strict type checking passes with zero errors for logger.py and EventBusProtocol
- **SC-004**: Logging overhead is under 20ms per emit() call (measured with 1000 sequential emissions, includes all operations from function entry to exit)
- **SC-005**: No secrets appear in stderr when test payload contains all 4 sensitive field names
- **SC-006**: At least 45 tags are registered in ALLOWED_TAGS whitelist (matches workflow.md log tag table: 12 lifecycle.* + 29 runtime.* + 4 cross_cutting.* = 45 tags total)
- **SC-007**: Logger can handle 10,000 concurrent emit() calls from 100 threads without deadlock or data race
- **SC-008**: EventBusProtocol definition allows F03 to implement EventBus with full type safety

## Assumptions

- Logs are primarily consumed by automated monitoring tools, not human operators (JSONL format prioritized equally with text)
- stderr capacity is unlimited (no buffering overflow expected in practice)
- Thread-safety is required because F08 main_loop may spawn concurrent tool executions
- Redaction performance is acceptable even with 1000+ nested objects (rare in practice)
- F03 event bus implementation will happen in Phase 2/Batch 3; EventBusProtocol interface alone is sufficient for Phase 1
- All 45 log tags are pre-determined from workflow.md and architecture_modules.md (no runtime registration needed)
- Span buffer growth is bounded by single run duration (F09 drains at exit, no rotation needed)
- ISO8601 timezone is system local time (not forcing UTC)
- ANSI color codes in text format are optional (can be disabled via env var in future, not Phase 1 scope)
