# F01 Primitives Layer — Quickstart Validation Guide

**Feature**: F01 — Primitives Layer Encapsulation  
**Date**: 2026-09-17  
**Status**: Phase 1 Design

This document provides runnable validation scenarios that prove F01 works end-to-end. These scenarios map directly to the 5 prioritized user stories in spec.md.

---

## Prerequisites

### Environment Setup

1. **Python Version**: ≥3.10 (verify: `python --version`)
2. **Install Project**: `pip install -e .` from repository root
3. **Environment Variables**: Set API keys for providers you want to test:
   ```bash
   export OPENAI_API_KEY="sk-..."
   export ANTHROPIC_API_KEY="sk-ant-..."
   export GOOGLE_API_KEY="..."
   export DEEPSEEK_API_KEY="..."
   export ZHIPUAI_API_KEY="..."
   ```
4. **Optional: Local vLLM**: For baseline tests, start vLLM at `http://10.0.0.5:8000/v1` with Qwen3.8-27B model

### Test Data

All test fixtures are in `tests/fixtures/`:
- `openai_compatible_local/` - Local vLLM endpoint config
- `fake_models.py` - FakeChatModel for tests that don't need real LLM calls
- `test_agent_dirs/` - Sample agent directories with middleware/tools

---

## Scenario 1: Model Provider Abstraction (P1)

**User Story**: Instantiate any of 6 supported LLM backends based on runtime configuration.

**Success Criteria** (SC-001): All 6 providers return working BaseChatModel instances within 5 seconds.

### Test Commands

```bash
# Test all 6 providers
pytest tests/primitives/test_chat_model_factory.py::test_create_openai_default -v
pytest tests/primitives/test_chat_model_factory.py::test_create_anthropic_default -v
pytest tests/primitives/test_chat_model_factory.py::test_create_google_default -v
pytest tests/primitives/test_chat_model_factory.py::test_create_deepseek_default -v
pytest tests/primitives/test_chat_model_factory.py::test_create_zhipu_default -v
pytest tests/primitives/test_chat_model_factory.py::test_create_openai_compatible_local -v

# Run all model factory tests
pytest tests/primitives/test_chat_model_factory.py -v
```

### Expected Outcomes

1. Each test completes in <5s (includes endpoint probe)
2. All tests return `BaseChatModel` instances
3. OpenAI/Anthropic/Google tests use official LangChain classes
4. DeepSeek/Zhipu/OpenAI-compatible tests use `ChatOpenAI` with custom `base_url`
5. Log tags emitted: `la.runtime.model_adapt.start`, `la.runtime.model_adapt.endpoint_probe`, `la.runtime.model_adapt.ok`

### Error Cases

```bash
# Test unsupported provider
pytest tests/primitives/test_chat_model_factory.py::test_create_unsupported_provider -v
# Expected: ProviderUnsupportedError, exit code 78

# Test missing API key
pytest tests/primitives/test_chat_model_factory.py::test_create_missing_api_key -v
# Expected: AuthFailedError, exit code 78

# Test endpoint unreachable
pytest tests/primitives/test_chat_model_factory.py::test_create_endpoint_unreachable -v
# Expected: EndpointUnreachableError, exit code 70 (strict enforcement per clarification Q1)
```

### Manual Verification

```bash
# Invoke model to verify it works end-to-end
python -c "
from langagent.primitives.chat_model_factory import create
from langagent.runtime.config import RuntimeConfig
from langagent.primitives.langchain_types import HumanMessage

config = RuntimeConfig(model_provider='openai', model_name='gpt-4', model_base_url=None)
model = create(config)
response = model.invoke([HumanMessage(content='Hello')])
print(response.content)
"
# Expected: Model returns a valid response
```

---

## Scenario 2: State Graph Compilation (P1)

**User Story**: Compile a LangGraph StateGraph with tools, middleware, and checkpointing.

**Success Criteria** (SC-002): Minimal agent compiles in <500ms; SC-006: All 9 log tags emitted.

### Test Commands

```bash
# Test minimal graph (0 tools, 0 middleware)
pytest tests/primitives/test_state_graph_builder.py::test_build_minimal_agent_state -v

# Test with tools
pytest tests/primitives/test_state_graph_builder.py::test_build_with_one_tool -v

# Test with middleware
pytest tests/primitives/test_state_graph_builder.py::test_build_with_one_middleware -v

# Test with guardrail middleware
pytest tests/primitives/test_state_graph_builder.py::test_build_with_guardrail_middleware -v

# Run all graph builder tests
pytest tests/primitives/test_state_graph_builder.py -v
```

### Expected Outcomes

1. Minimal graph compiles in <500ms
2. Graph with 1 tool binds successfully
3. Graph with 1 user middleware loads from `agent_dir/middleware/`
4. Graph with guardrail middleware calls `build_middleware(policy)` (mocked in tests)
5. All 9 log tags emitted:
   - `la.runtime.graph_compose.start`
   - `la.runtime.graph_compose.middleware_bind` (per middleware)
   - `la.runtime.graph_compose.tool_bind` (per tool)
   - `la.runtime.graph_compose.ok`
6. `sys.modules` cleaned up: no `langagent_dynamic_middleware_*` entries after build

### Error Cases

```bash
# Test middleware syntax error
pytest tests/primitives/test_state_graph_builder.py::test_build_middleware_syntax_error -v
# Expected: GraphCompileError with file path and syntax details (clarification Q3)

# Test tool binding error
pytest tests/primitives/test_state_graph_builder.py::test_build_tool_binding_error -v
# Expected: ToolBindingError, exit code 70
```

### Manual Verification

```bash
# Build and invoke graph
python -c "
from langagent.primitives.state_graph_builder import build
from langagent.primitives.checkpoint_adapter import create as create_checkpoint
from langagent.protocol.loaded_agent import LoadedAgent
from langagent.runtime.config import RuntimeConfig
from langagent.primitives.langchain_types import HumanMessage
from pathlib import Path

loaded = LoadedAgent(
    agent_dir=Path('tests/fixtures/test_agent_dirs/minimal'),
    instructions='You are a helpful assistant',
    tool_ids=[],
    skill_names=[],
    metadata={}
)

config = RuntimeConfig(
    model_provider='openai',
    model_name='gpt-4',
    checkpointer='memory',
    middleware_ids=[],
    guardrail_policy=None
)

checkpoint = create_checkpoint(config)
graph = build(loaded, config, checkpoint)

result = graph.invoke({'messages': [HumanMessage('Test message')]})
print(f'State updated: {len(result[\"messages\"])} messages')
"
# Expected: Graph invokes successfully, state contains messages
```

---

## Scenario 3: Checkpoint Adapter (P2)

**User Story**: Instantiate the correct checkpointer (memory, sqlite, postgres) and properly close it.

**Success Criteria** (SC-004): All 3 types create/close without resource leaks.

### Test Commands

```bash
# Test all 3 checkpointer types
pytest tests/primitives/test_checkpoint_adapter.py::test_create_memory -v
pytest tests/primitives/test_checkpoint_adapter.py::test_create_sqlite_in_tmp -v
pytest tests/primitives/test_checkpoint_adapter.py::test_create_postgres_url -v

# Test close operations
pytest tests/primitives/test_checkpoint_adapter.py::test_close_memory_no_op -v
pytest tests/primitives/test_checkpoint_adapter.py::test_close_sqlite_releases_lock -v
pytest tests/primitives/test_checkpoint_adapter.py::test_close_postgres_closes_pool -v

# Run all checkpoint tests
pytest tests/primitives/test_checkpoint_adapter.py -v
```

### Expected Outcomes

1. Memory checkpointer creates instantly
2. SQLite checkpointer creates with integrity check (clarification Q2)
3. Postgres checkpointer creates with 3-retry mechanism (clarification Q5)
4. Close operations release resources (verify via file descriptor count)
5. No resource leaks detected

### Error Cases

```bash
# Test SQLite corruption repair
pytest tests/primitives/test_checkpoint_adapter.py::test_create_sqlite_corrupted_db -v
# Expected: Successful repair via dump/restore (research.md Decision 5)

# Test SQLite unrepairable
pytest tests/primitives/test_checkpoint_adapter.py::test_create_sqlite_unrepairable_db -v
# Expected: GraphCompileError, no backup file created (clarification Q2)

# Test Postgres retry exhausted
pytest tests/primitives/test_checkpoint_adapter.py::test_create_postgres_retry_exhausted -v
# Expected: GraphCompileError after 3 retries with 1s intervals (clarification Q5)

# Test unsupported checkpointer
pytest tests/primitives/test_checkpoint_adapter.py::test_create_unsupported_checkpointer -v
# Expected: CheckpointTypeUnsupportedError, exit code 78
```

### Manual Verification

```bash
# Test checkpoint persistence roundtrip
python -c "
from langagent.primitives.checkpoint_adapter import create, close
from langagent.runtime.config import RuntimeConfig
import tempfile

# SQLite roundtrip
with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
    db_path = f.name

config = RuntimeConfig(checkpointer='sqlite', checkpoint_sqlite_path=db_path)
checkpoint = create(config)
# ... persist state via graph.invoke() ...
close(checkpoint)

# Reopen and verify state persisted
checkpoint2 = create(config)
# ... verify state restored ...
close(checkpoint2)
print('SQLite checkpoint roundtrip successful')
"
```

---

## Scenario 4: LangChain Types Re-Export (P2)

**User Story**: Import LangChain/LangGraph types through primitives layer re-export module.

**Success Criteria** (SC-005): 100% of imports go through re-export module (static analysis).

### Test Commands

```bash
# Test re-export identity
pytest tests/primitives/test_langchain_types.py::test_import_messages -v
pytest tests/primitives/test_langchain_types.py::test_import_models -v
pytest tests/primitives/test_langchain_types.py::test_import_tools -v
pytest tests/primitives/test_langchain_types.py::test_import_graph -v
pytest tests/primitives/test_langchain_types.py::test_import_checkpoint -v

# Static analysis tests
pytest tests/primitives/test_langchain_types.py::test_no_direct_langchain_imports_runtime -v
pytest tests/primitives/test_langchain_types.py::test_no_direct_langchain_imports_cross_cutting -v
pytest tests/primitives/test_langchain_types.py::test_no_direct_langchain_imports_protocol -v
pytest tests/primitives/test_langchain_types.py::test_no_direct_langchain_imports_cli -v

# Run all langchain_types tests
pytest tests/primitives/test_langchain_types.py -v
```

### Expected Outcomes

1. All re-exported types are identical to LangChain originals (object identity check)
2. Static analysis finds 0 direct langchain imports outside primitives layer
3. 100% architectural boundary enforcement (SC-005)

### Manual Verification

```bash
# Grep for direct langchain imports (should find 0 matches outside primitives/)
grep -r "from langchain" langagent/runtime/ langagent/cross_cutting/ langagent/protocol/ langagent/cli/

# Expected: No matches (or only in comments)
```

---

## Scenario 5: Stage Logging Integration (P3)

**User Story**: Primitives layer emits structured log tags at key points in model_adapt and graph_compose stages.

**Success Criteria** (SC-006): All 9 tags emitted; SC-007: Stage guards prevent blacklist violations.

### Test Commands

```bash
# Test model_adapt log tags (4 tags)
pytest tests/primitives/test_chat_model_factory.py::test_create_emits_start_tag -v
pytest tests/primitives/test_chat_model_factory.py::test_create_emits_endpoint_probe_tag -v
pytest tests/primitives/test_chat_model_factory.py::test_create_emits_ok_tag -v
pytest tests/primitives/test_chat_model_factory.py::test_create_emits_fail_tag -v

# Test graph_compose log tags (5 tags)
pytest tests/primitives/test_state_graph_builder.py::test_build_emits_start_tag -v
pytest tests/primitives/test_state_graph_builder.py::test_build_emits_middleware_bind_tag -v
pytest tests/primitives/test_state_graph_builder.py::test_build_emits_tool_bind_tag -v
pytest tests/primitives/test_state_graph_builder.py::test_build_emits_ok_tag -v
pytest tests/primitives/test_state_graph_builder.py::test_build_emits_fail_tag -v

# Test stage guard decorators
pytest tests/primitives/test_stage_guard_integration.py::test_model_adapt_stage_guard -v
pytest tests/primitives/test_stage_guard_integration.py::test_graph_compose_stage_guard -v
```

### Expected Outcomes

1. All 9 log tags emitted with appropriate payloads
2. Tags registered in F02's `ALLOWED_TAGS` whitelist (≥46 items)
3. Stage guard decorators prevent 100% of blacklist violations (SC-007):
   - `model_adapt` blocks: `RuntimeDirLoader.load`, `RuntimeConfigResolver.resolve`
   - `graph_compose` blocks: `BaseChatModel.__init__`, `chat_model_factory.create`, `RuntimeDirLoader.load`

### Manual Verification

```bash
# Run with real logger to see tag emissions
pytest tests/integration/test_primitives_integration.py -v -s

# Expected log output:
# [DEBUG] la.runtime.model_adapt.start {"provider": "openai", ...}
# [DEBUG] la.runtime.model_adapt.endpoint_probe {"url": "...", ...}
# [INFO] la.runtime.model_adapt.ok {"duration_ms": 234, ...}
# [DEBUG] la.runtime.graph_compose.start {...}
# [DEBUG] la.runtime.graph_compose.middleware_bind {"id": "rate_limiter", ...}
# [DEBUG] la.runtime.graph_compose.tool_bind {"tool_id": "calculator", ...}
# [INFO] la.runtime.graph_compose.ok {"duration_ms": 456, ...}
```

---

## Integration Test: End-to-End

**Scenario**: Full workflow from config → model → graph → invoke → checkpoint → resume.

### Test Command

```bash
pytest tests/integration/test_primitives_integration.py::test_full_workflow -v
```

### Expected Workflow

1. F07 produces `RuntimeConfig` (mocked in test)
2. F06 produces `LoadedAgent` (mocked in test)
3. F01 `chat_model_factory.create(config)` → `BaseChatModel`
4. F10 `config.with_model(model)` → New frozen `RuntimeConfig`
5. F01 `checkpoint_adapter.create(config)` → `BaseCheckpointSaver`
6. F01 `state_graph_builder.build(loaded, config, checkpoint)` → `CompiledStateGraph`
7. F08 `graph.invoke(input, config)` → Agent execution, state updated
8. Checkpoint persists state
9. Resume from checkpoint → State restored
10. All 9 log tags emitted
11. F09 `checkpoint_adapter.close(checkpoint)` → Resources released

### Expected Outcomes

- Full workflow completes in <10s (SC-010: local vLLM ReAct turn)
- State persists across sessions (for sqlite/postgres)
- No resource leaks
- All constitutional constraints satisfied

---

## Performance Validation

### Success Criteria Checklist

- [ ] SC-001: All 6 providers instantiate in <5s (with endpoint probe)
- [ ] SC-002: Minimal graph compiles in <500ms
- [ ] SC-003: 10 concurrent middleware registrations (stress test, optional)
- [ ] SC-004: Checkpoint create/close without resource leaks
- [ ] SC-005: 100% re-export module usage (static analysis)
- [ ] SC-006: All 9 log tags emitted
- [ ] SC-007: Stage guards prevent 100% of blacklist violations
- [ ] SC-008: Reducers handle edge cases without exceptions
- [ ] SC-009: Provider switching (openai → openai-compatible → anthropic) with zero code changes
- [ ] SC-010: Local vLLM completes basic ReAct turn in <10s

### Performance Benchmarks

```bash
# Run performance benchmarks
pytest tests/primitives/test_performance.py -v

# Expected:
# test_model_instantiation_latency: <5s per provider
# test_graph_compilation_latency: <500ms for minimal agent
# test_checkpoint_create_latency: <100ms (memory/sqlite), <500ms (postgres)
# test_middleware_loading_latency: <50ms per middleware
# test_reducer_execution_latency: <1ms per field update
```

---

## Static Analysis

### Architectural Boundary Enforcement

```bash
# Verify no direct langchain imports outside primitives/
grep -r "from langchain" langagent/runtime/ langagent/cross_cutting/ langagent/protocol/ langagent/cli/

# Expected: 0 matches

# Verify no hardcoded API keys/URLs (宪法第 XIII 条)
grep -r "sk-[a-zA-Z0-9]" langagent/primitives/

# Expected: 0 matches (only in tests/fixtures/)

# Verify no localhost hardcoding (review.md M-1)
grep -r "localhost\|127.0.0.1" langagent/primitives/*.py

# Expected: 0 matches in source files
```

---

## Cleanup

After running all tests:

```bash
# Clean up test artifacts
rm -rf /tmp/langagent_test_*
rm -rf tests/fixtures/test_agent_dirs/*/middleware/__pycache__

# Verify no lingering sys.modules pollution
python -c "
import sys
middleware_modules = [k for k in sys.modules if 'langagent_dynamic_middleware' in k]
assert len(middleware_modules) == 0, f'Leaked modules: {middleware_modules}'
print('✓ No sys.modules pollution')
"
```

---

## Troubleshooting

### Common Issues

**Issue**: `EndpointUnreachableError` when testing local vLLM  
**Solution**: Ensure vLLM is running at `http://10.0.0.5:8000/v1`. Tests skip gracefully if unreachable.

**Issue**: `AuthFailedError` for provider tests  
**Solution**: Set corresponding API key environment variable (`OPENAI_API_KEY`, etc.)

**Issue**: `GraphCompileError: SQLite corruption`  
**Solution**: Delete corrupted test database: `rm /tmp/test_checkpoint.db`

**Issue**: Middleware syntax error in tests  
**Solution**: Check `tests/fixtures/test_agent_dirs/*/middleware/*.py` for valid Python syntax

**Issue**: Stage guard violation  
**Solution**: Verify test doesn't attempt blacklisted operations (see FR-045/FR-046 monkeypatch_blacklist)

---

## Next Steps

After validating all scenarios:

1. **Mark Phase 1 Complete**: All quickstart scenarios pass
2. **Run `/speckit.tasks`**: Generate `tasks.md` with TDD task breakdown
3. **Begin Implementation**: Red-Green-Refactor cycle per 宪法第 VIII 条

---

This quickstart guide validates that F01 meets all 47 functional requirements, 10 success criteria, and constitutional constraints before proceeding to implementation.
