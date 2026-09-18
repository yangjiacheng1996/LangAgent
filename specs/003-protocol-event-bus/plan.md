# Implementation Plan: F03 Protocol Event Bus

**Branch**: `003-protocol-event-bus` | **Date**: 2026-09-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-protocol-event-bus/spec.md`

**Aligned with Constitution Article XV**: This plan references the top-level design artifacts and maintains alignment with the constitution as specified in spec.md.

## Summary

F03 implements a publish/subscribe event bus for cross-module communication in LangAgent's protocol layer. The event bus provides synchronous and asynchronous event publication, error isolation, thread-safe operations, graceful shutdown via `flush()`, and event drainage for persistence. This infrastructure enables loose coupling between runtime modules (publishers) and cross-cutting modules (subscribers) while maintaining system reliability.

**Technical Approach**: Implement an in-memory event bus using Python's `threading.Lock` for thread safety, `asyncio.gather(return_exceptions=True)` for async handler isolation, and a FIFO subscription registry for deterministic handler execution order. The bus accumulates all events in an internal buffer for later JSONL persistence by F09 exit handler.

## Technical Context

**Language/Version**: Python 3.11+ (per `pyproject.toml` `requires-python` field from constitution Article II.5)

**Primary Dependencies**: 
- `langchain-core` (for Event schema compatibility with LangChain message types)
- F02 `cross_cutting_logger` (provides `emit()` interface and `EventBusProtocol` definition)
- Python standard library: `threading`, `asyncio`, `uuid`, `datetime`, `dataclasses`

**Storage**: In-memory event buffer (list); JSONL persistence handled by F09 (not F03 responsibility)

**Testing**: pytest with `pytest-asyncio` for async handler tests; thread concurrency tests using `threading.Barrier`

**Target Platform**: Linux server (primary); cross-platform Python (secondary)

**Project Type**: Internal library module (protocol layer of agent runtime system)

**Performance Goals**: 
- <10ms event publication latency for 3 subscribers
- 1,000 events/second throughput without memory leak
- Zero handler exception propagation to caller (100% isolation)

**Constraints**: 
- Thread-safe without GIL assumptions
- No external service dependencies (self-contained)
- Event buffer unbounded for v1 (<10,000 events per run typical)
- FIFO handler execution order guarantee

**Scale/Scope**: 
- 13+ event types in whitelist (tool_call, model_response, guardrail_block, etc.)
- ~10-50 subscribers per event type typical
- ~280 lines of code estimated for core EventBus class

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Article I (Project Identity) ✅
- **Compliance**: Event bus is internal infrastructure, not exposed as SDK
- **Verification**: Module in `langagent/protocol/event_bus.py`, not published externally

### Article II (Tech Stack) ✅
- **Compliance**: Uses LangChain primitives (Event schema compatible with LangChain message types)
- **Verification**: No new third-party dependencies; uses `langchain-core` already in project

### Article III (LangSmith Decoupling) ✅
- **Compliance**: Zero LangSmith dependencies; self-contained pub/sub implementation
- **Verification**: No `from langsmith import`, no LangSmith environment variables

### Article VIII (TDD Mandate) ✅
- **Compliance**: ≥24 test cases specified in feature prompt before implementation
- **Verification**: Test-first development required per spec.md §4.1 test catalog

### Article XIII (Hard No) ✅
- **Compliance**: No hardcoded paths, no external network calls, structured logging via F02
- **Verification**: Event bus uses F02 logger interface, no `print()` statements

### Article XV (Top-Level Design Primacy) ✅
- **Compliance**: Spec references workflow.md, architecture_modules.md, module_schemas.md
- **Verification**: `protocol_event_bus` module defined in architecture_modules.md#mod-protocol-event-bus

**Overall Status**: ✅ All gates pass. No violations to justify.

## Project Structure

### Documentation (this feature)

```text
specs/003-protocol-event-bus/
├── plan.md              # This file (/speckit.plan output)
├── spec.md              # Feature specification (already exists)
├── research.md          # Phase 0 output (clarification resolutions)
├── data-model.md        # Phase 1 output (entity definitions)
├── quickstart.md        # Phase 1 output (validation guide)
├── contracts/           # Phase 1 output (EventBus API contract)
│   └── event_bus_api.md
├── checklists/
│   └── requirements.md  # Spec quality checklist (already exists)
└── tasks.md             # Phase 2 output (/speckit.tasks - NOT created yet)
```

### Source Code (repository root)

```text
langagent/
├── protocol/
│   ├── __init__.py
│   ├── event_bus.py          # F03: EventBus class + SubscriptionToken
│   └── event_types.py        # F03: ALLOWED_EVENT_TYPES constant (≥13 types)
│
├── cross_cutting/
│   └── logger.py             # F02: emit() + EventBusProtocol (dependency)
│
└── primitives/
    └── langchain_types.py    # F10: Event schema re-export (dependency)

tests/
├── protocol/
│   ├── test_event_bus.py                    # F03: ≥24 core tests
│   └── test_event_integration_with_metrics.py  # F03: ≥3 integration tests
│
└── conftest.py                               # Shared fixtures
```

**Structure Decision**: Single project structure with clear layer separation (protocol/cross_cutting/primitives). F03 lives in `langagent/protocol/` per architecture_modules.md. Tests mirror source structure under `tests/protocol/`.

## Complexity Tracking

> **No violations to track** - Constitution Check passed all gates.

---

# Phase 0: Outline & Research

## Research Tasks

Based on Technical Context, the following areas need investigation:

1. **Thread Safety Patterns**: Best practices for `threading.Lock` usage in pub/sub systems
2. **Async Handler Patterns**: `asyncio.gather(return_exceptions=True)` error handling patterns
3. **Flush Timeout Implementation**: Strategies for waiting on pending handlers with timeout
4. **Event ID Generation**: UUID v4 collision probability and alternatives
5. **Subscription Token Design**: Opaque handle patterns for unsubscribe

## Research Findings → research.md

Let me generate the research document:
