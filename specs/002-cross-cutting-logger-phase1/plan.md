# Implementation Plan: Cross-Cutting Logger + EventBusProtocol (F02 Phase 1)

**Branch**: `002-cross-cutting-logger-phase1` | **Date**: 2026-09-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-cross-cutting-logger-phase1/spec.md`

## Summary

Implement cross_cutting_logger module providing structured logging with tag whitelist validation, automatic secret redaction, and EventBusProtocol interface definition. This is F02 Phase 1 - foundation for LangAgent's observability system (all 9 features F01, F03-F11 depend on this capability).

**Technical Approach** (from research.md):
- **Thread-safety**: Python `threading.Lock` for stderr writes and span buffer operations
- **Tag validation**: Module-level `frozenset` with 46 pre-registered tags (O(1) lookup)
- **Secret redaction**: Deep recursive traversal with exact field name matching (`api_key`, `password`, `secret`, `token`)
- **Dual-format output**: Text format (human-readable) + JSONL format (machine-parseable) both to stderr
- **Span buffering**: In-memory list with atomic drain-and-clear for F09 exit_cleanup integration
- **EventBusProtocol**: Structural subtyping via `typing.Protocol` (4 required methods for F03 contract)

## Technical Context

**Language/Version**: Python 3.11+ (per `pyproject.toml` `requires-python` field)

**Primary Dependencies**: Python standard library only
- `threading` - Lock for concurrency safety
- `datetime` - ISO8601 timestamp generation
- `json` - JSONL format serialization
- `dataclasses` - Span dataclass (7 fields)
- `typing` - Protocol, Literal, Callable for type safety

**Storage**: In-memory span buffer (no disk I/O in F02 Phase 1; F09 handles persistence)

**Testing**: pytest with coverage requirements
- 28 unit/integration tests across 5 user stories
- Performance benchmark: <5ms per emit() call (SC-004)
- Concurrency stress test: 10,000 concurrent emits from 100 threads (SC-007)

**Target Platform**: Linux server (primary), cross-platform compatible (no OS-specific syscalls)

**Project Type**: Internal library module (part of LangAgent CLI tool, not published as separate package)

**Performance Goals**:
- **Latency**: <5ms per emit() call measured with 1000 sequential emissions
- **Throughput**: Handle 10,000 concurrent emit() calls from 100 threads without deadlock
- **Overhead**: Lock contention <1% (measured at ~0.5μs per acquire/release)

**Constraints**:
- **Thread-safe**: All public APIs (`emit`, `set_level`, `drain_spans`) must be reentrant
- **Fire-and-forget**: I/O failures in emit() must not raise exceptions to caller
- **No external dependencies**: stdlib only (aligns with Constitution Article II)
- **Immutability**: `ALLOWED_TAGS` frozenset, `Span` dataclass frozen
- **Performance**: json.dumps() + 2 stderr writes < 5ms total

**Scale/Scope**:
- Single module file: `langagent/cross_cutting/logger.py` (~170 LOC per research.md estimate)
- 28 tests across 2 test files + 4 validation scripts
- 46-item tag whitelist organized into 4 namespaces
- 5 user stories (US1-US5) with independent test criteria

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

### Alignment with Constitution Articles

✅ **第 I 条 (项目身份与边界)**: F02 is internal module, not exposing SDK. Logger used only within `langagent/` codebase.

✅ **第 II 条 (技术栈与依赖范围)**: Uses Python stdlib only. No LangChain/LangGraph dependencies in F02 (pure infrastructure layer per architecture_modules.md).

✅ **第 III 条 (LangSmith 剥离原则)**: No LangSmith dependencies. Self-contained observability implementation.

✅ **第 VIII 条 (开发方法论 - TDD 刚性约束)**:
- All 62 tasks follow Red-Green-Refactor cycle
- Tests written FIRST (explicitly marked in tasks.md with checkpoints)
- Each user story has "Run tests - all X tests must FAIL" checkpoint before implementation
- No implementation tasks before corresponding test tasks

✅ **第 XIII 条 (禁止项 - Hard No)**:
- No `print` statements - use structured `emit()` to stderr only (FR-014)
- No hardcoded API keys - automatic redaction for 4 sensitive field names (FR-004)
- No absolute paths - all paths project-relative (`langagent/cross_cutting/`)
- TDD enforced - see Article VIII alignment above

✅ **第 XV 条 (Top-Level Design Primacy)**:
- spec.md:L9-12 explicitly references 3 top-level design artifacts:
  - `harness/top_level_design/workflow.md` - 46 log tags + exit codes
  - `harness/top_level_design/architecture_modules.md` - cross_cutting layer constraints
  - `harness/top_level_design/module_schemas.md` - Span (7 fields), Trace, MetricsSnapshot schemas
- All design decisions traceable to these artifacts

### Gate Status

**✅ PASS** - No constitution violations. No complexity tracking needed (single module, no architectural deviations).

## Project Structure

### Documentation (this feature)

```text
specs/002-cross-cutting-logger-phase1/
├── spec.md              # Feature specification (user stories, FRs, SCs)
├── plan.md              # This file (implementation plan)
├── research.md          # Phase 0 output (technical decisions & rationale)
├── tasks.md             # Phase 2 output (62 tasks across 8 phases)
└── checklists/
    └── requirements.md  # Spec quality validation checklist
```

### Source Code (repository root)

```text
langagent/
└── cross_cutting/
    ├── __init__.py          # Public API exports (8 symbols):
    │                        # emit, set_level, drain_spans,
    │                        # EventBusProtocol, Span, LogLevel,
    │                        # UnknownLogTagError, SpanDrainError
    └── logger.py            # Core implementation (~170 LOC):
                             # - ALLOWED_TAGS frozenset (46 items)
                             # - _redact() recursive function
                             # - emit() dual-format output
                             # - set_level() validation
                             # - drain_spans() atomic operation
                             # - EventBusProtocol interface (4 methods)
                             # - Span dataclass (7 fields)
                             # - 2 custom exceptions

tests/
├── cross_cutting/
│   ├── test_logger.py              # 22 unit tests (logger + redaction + level + drain_spans)
│   ├── test_event_bus_protocol.py  # 5 protocol contract tests
│   ├── benchmark_logger.py         # Performance tests (SC-004: <5ms per emit)
│   ├── stress_test_logger.py       # Concurrency tests (SC-007: 10k concurrent emits)
│   └── validate_tags.py            # Tag whitelist validator (SC-006: exactly 46 tags)
└── fixtures/
    └── log_tags_whitelist.json     # 46 tags reference (4 namespaces)
```

**Structure Decision**: Single project (Option 1 from template) - `langagent/` is existing monorepo structure per repository layout. cross_cutting layer sits between primitives and protocol layers per architecture_modules.md dependency matrix.

**Key Files**:
- **logger.py**: Single module contains all implementation (logging + EventBusProtocol interface). Consolidation rationale: logger and EventBusProtocol are both "passive interfaces" (callers push to them, no reverse dependencies), and both are cross_cutting concerns (review.md v0.5.0 design trade-off).
- **__init__.py**: Exports 8 public symbols for import by F01/F03-F11 features.
- **test_logger.py**: 22 tests covering 4 user stories (US1-US4: structured logging, redaction, level filtering, span buffer).
- **test_event_bus_protocol.py**: 5 tests for US5 (EventBusProtocol interface contract).

## Complexity Tracking

> **No violations** - This section intentionally empty per Constitution Check gate status.

---

## Phase 0: Research (Complete)

**Status**: ✅ Complete - see `research.md`

**Key Decisions** (summary):

1. **Thread-Safe Logging**: `threading.Lock` chosen over queue-based async (simpler, <5ms target met)
2. **Secret Redaction**: Exact field name matching with `frozenset` (O(1) lookup, prevents `input_tokens` false positives)
3. **Dual-Format Output**: Two `sys.stderr.write()` calls per emit (text first, then JSONL)
4. **Tag Whitelist**: Module-level `ALLOWED_TAGS: frozenset[str]` with 46 pre-registered tags
5. **ISO8601 Timestamps**: `datetime.now(timezone.utc).astimezone().isoformat()` for local time + UTC offset
6. **EventBusProtocol**: `typing.Protocol` with 4 required methods (structural subtyping, no inheritance)
7. **Span Buffer**: In-memory list with failure-safe drain (buffer NOT cleared on exception, allows retry)
8. **Log Level Filtering**: Stdlib-aligned numeric levels (DEBUG=10, INFO=20, WARNING=30, ERROR=40, CRITICAL=50)

**Alternatives Considered**: See research.md sections 1-8 for full rationale and rejected alternatives.

---

## Phase 1: Design & Contracts (Partial)

**Status**: ⚠️ Partial - data-model.md, contracts/, quickstart.md skipped per project type

### Data Model

F02 Phase 1 defines 4 key types (all in `langagent/cross_cutting/logger.py`):

**1. Span** (dataclass, frozen)
```python
@dataclass(frozen=True)
class Span:
    trace_id: str
    span_id: str
    parent_span_id: str | None
    name: str
    start: float  # Unix timestamp (seconds since epoch)
    end: float    # Unix timestamp
    attributes: dict[str, Any]
```

**2. LogLevel** (Literal type)
```python
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
```

**3. EventBusProtocol** (Protocol interface)
```python
class EventBusProtocol(Protocol):
    def publish(self, event_type: str, payload: dict[str, Any]) -> None: ...
    def subscribe(self, event_type: str, callback: Callable[[dict[str, Any]], None]) -> str: ...
    def unsubscribe(self, subscription_id: str) -> None: ...
    def flush(self) -> None: ...
```

**4. Custom Exceptions**
```python
class UnknownLogTagError(ValueError): ...
class SpanDrainError(RuntimeError): ...
```

**Rationale for no separate data-model.md**: F02 is infrastructure layer with 4 simple types (no complex relationships, state transitions, or validation rules beyond type hints). Type definitions colocated in logger.py per architecture_modules.md single-module constraint.

### Interface Contracts

**Contract Type**: Internal library module API (not web service, CLI, or parser)

**Public API** (8 symbols exported via `__init__.py`):

1. **emit(tag: str, payload: dict[str, Any]) -> None**
   - Validates `tag` in `ALLOWED_TAGS` (raises `UnknownLogTagError` if not)
   - Validates `payload` is dict (raises `TypeError` if not)
   - Redacts sensitive fields (`api_key`, `password`, `secret`, `token`)
   - Writes dual-format (text + JSONL) to stderr atomically under lock
   - Fire-and-forget semantics (I/O errors logged, not raised)

2. **set_level(level: LogLevel) -> None**
   - Validates `level` in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
   - Raises `ValueError` if invalid
   - Updates global `_current_level` numeric value

3. **drain_spans() -> list[Span]**
   - Returns accumulated Span objects from `_span_buffer`
   - Clears buffer atomically under lock
   - Failure-safe: buffer NOT cleared if exception raised (allows retry)

4. **EventBusProtocol** (Protocol class for type hints only)
5. **Span** (dataclass for span construction)
6. **LogLevel** (Literal type for `set_level()` type hints)
7. **UnknownLogTagError** (exception for invalid tags)
8. **SpanDrainError** (exception for drain failures)

**Contract Consumers**:
- F01 (primitives layer) - may log primitive operations
- F03 (protocol_event_bus) - implements EventBusProtocol interface
- F04 (audit + guardrail) - emits `la.cross_cutting.*` tags
- F05-F11 (runtime/cli layers) - emit logs for 6 stages + eval/doctor workflows

**Rationale for no contracts/ directory**: F02 is internal module with Python type hints as contract. No external interface formats (REST endpoints, CLI schemas, gRPC protos) to document.

### Quickstart Validation

**Quickstart scenarios** integrated into tasks.md Phase 8 (Polish) rather than separate quickstart.md:

**Scenario 1: Basic Logging** (US1 validation)
```bash
# Prerequisites: Phase 1-3 tasks complete (T001-T021)
cd /home/ctyun/workspace/github/LangAgent
python3 -c "
from langagent.cross_cutting import emit
emit('la.runtime.dir_load.ok', {'agent_dir': '/tmp/test'})
" 2>&1 | head -2
# Expected: 2 lines to stderr (text + JSONL), 0 lines to stdout
```

**Scenario 2: Secret Redaction** (US2 validation)
```bash
# Prerequisites: Phase 4 tasks complete (T022-T027)
python3 -c "
from langagent.cross_cutting import emit
emit('la.runtime.model_adapt.start', {'api_key': 'sk-secret123'})
" 2>&1 | grep -o 'sk-secret123' | wc -l
# Expected: 0 (secret fully redacted to ***)
```

**Scenario 3: Span Draining** (US4 validation)
```bash
# Prerequisites: Phase 6 tasks complete (T033-T043)
python3 -c "
from langagent.cross_cutting import emit, drain_spans
emit('la.runtime.main_loop.turn.start', {'kind': 'span', 'trace_id': 't1', 'span_id': 's1', 'name': 'turn', 'start': 1.0, 'end': 2.0, 'attributes': {}})
spans = drain_spans()
assert len(spans) == 1
print('✓ Span buffer works')
"
# Expected: ✓ Span buffer works
```

**Scenario 4: Full Test Suite** (all US1-US5 validation)
```bash
# Prerequisites: All phases complete (T001-T062)
pytest tests/cross_cutting/ -v --tb=short
# Expected: 28 passed in <2s (per SC-001, SC-002)

mypy --strict langagent/cross_cutting/logger.py
# Expected: Success: no issues found (per SC-003)
```

**Rationale for no quickstart.md**: Validation scenarios are atomic Python snippets (not multi-service setup). Integrated into tasks.md checkpoints for immediate validation after each user story phase. Full validation covered by pytest suite (T057).

---

## Implementation Notes

**Development Order** (from tasks.md):
1. Phase 1: Setup (T001-T004) - 4 tasks, ~5 min
2. Phase 2: Foundational (T005-T009) - 5 tasks, ~15 min, **BLOCKS all user stories**
3. Phase 3: US1 Structured Logging (T010-T021) - 12 tasks, ~2 hours (7 tests + 5 impl)
4. Phase 4: US2 Secret Redaction (T022-T027) - 6 tasks, ~45 min (4 tests + 2 impl)
5. Phase 5: US3 Log Level Filtering (T028-T032) - 5 tasks, ~30 min (2 tests + 3 impl)
6. Phase 6: US4 Span Buffer (T033-T043) - 11 tasks, ~1.5 hours (6 tests + 5 impl)
7. Phase 7: US5 EventBusProtocol (T044-T054) - 11 tasks, ~1 hour (5 tests + 6 impl)
8. Phase 8: Polish (T055-T062) - 8 tasks, ~1 hour

**Total Estimated Effort**: ~8-10 hours for single developer (TDD cycle: write test → fail → implement → pass → refactor)

**MVP Scope** (from tasks.md): Phases 1-4 (27 tasks) delivers secure structured logging ready for F03-F11 consumption.

**Parallel Opportunities**:
- Phase 2 Foundational: T006-T009 can run in parallel (different type definitions)
- US1 Tests: T010-T016 can be written in parallel (7 independent test functions)
- US1 + US5: US5 EventBusProtocol can be implemented in parallel with US1-4 (pure interface, no logger dependencies)
- Phase 8 Polish: T055-T059 can run in parallel (different files)

**Dependencies**:
- US2 depends on US1 (needs `emit()` function)
- US3 depends on US1 (extends `emit()` logic)
- US4 depends on US1 (extends `emit()` logic)
- US5 independent (pure type definition)

---

## Success Validation

**Before declaring F02 Phase 1 complete, verify** (from spec.md Success Criteria):

- [ ] SC-001: All 28 tests pass (pytest tests/cross_cutting/ shows 28 passed)
- [ ] SC-002: drain_spans 6 tests pass (subset of SC-001)
- [ ] SC-003: mypy --strict langagent/cross_cutting/logger.py shows 0 errors
- [ ] SC-004: benchmark_logger.py reports <5ms per emit() call
- [ ] SC-005: All 4 redaction tests pass (no secrets in stderr)
- [ ] SC-006: validate_tags.py confirms exactly 46 tags in ALLOWED_TAGS
- [ ] SC-007: stress_test_logger.py completes 10k concurrent emits without deadlock
- [ ] SC-008: test_event_bus_protocol.py mypy test passes

**Integration Readiness** (for F03-F11 consumption):

- [ ] `from langagent.cross_cutting import emit, set_level, drain_spans` works
- [ ] `from langagent.cross_cutting import EventBusProtocol` imports for F03 type hints
- [ ] All 46 tags from workflow.md present in whitelist (validated by T061)
- [ ] Thread-safety verified by stress test (10k concurrent emits)
- [ ] No external dependencies (stdlib only)

---

**Version**: 1.0 | **Author**: OpenCode AI | **Last Updated**: 2026-09-18
