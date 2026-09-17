# Tasks: F01 — Primitives Layer Encapsulation (LangChain / LangGraph Interface)

**Input**: Design documents from `/specs/001-primitives-layer-langchain-langraph/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: This feature follows TDD per Constitution Article VIII. All test tasks MUST be written and FAIL before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Project structure (from plan.md):
- Source: `langagent/primitives/` (F01 owns this subtree)
- Tests: `tests/primitives/` (mirrors source structure)
- Fixtures: `tests/fixtures/` (test data and fake implementations)
- Integration: `tests/integration/` (end-to-end tests)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure for primitives layer

- [ ] T001 Create primitives layer directory structure: `langagent/primitives/` with `__init__.py`
- [ ] T002 Create test directory structure: `tests/primitives/` with `__init__.py`
- [ ] T003 [P] Create test fixtures directory: `tests/fixtures/` with subdirs `openai_compatible_local/`, `fake_models.py`
- [ ] T004 [P] Create test agent directories per spec §Test Fixtures: `tests/fixtures/test_agent_dirs/minimal/`, `tests/fixtures/test_agent_dirs/with_middleware/`, `tests/fixtures/test_agent_dirs/with_tools/` (all MUST have instructions.md and agent.yaml per Constitution Article V)
- [ ] T005 [P] Add LangChain/LangGraph dependencies to pyproject.toml: `langchain-core`, `langchain-openai`, `langchain-anthropic`, `langchain-google-genai`, `langgraph`, `langgraph-checkpoint-sqlite`, `langgraph-checkpoint-postgres`
- [ ] T006 [P] Create primitives exceptions module in langagent/primitives/exceptions.py with 7 exception types (ProviderUnsupportedError, AuthFailedError, EndpointUnreachableError, RequiredFieldMissingError, GraphCompileError, ToolBindingError, CheckpointTypeUnsupportedError) with exit codes per data-model.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T007 Create state reducers module skeleton in langagent/primitives/state_reducers.py with function stubs for replace_with_merge, merge_dict, overwrite_or_merge (no implementation yet, returns empty containers)
- [ ] T008 [P] Create LangChain types re-export module in langagent/primitives/langchain_types.py re-exporting all types from FR-032: add_messages, BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage, BaseChatModel, BaseTool, tool, StateGraph, CompiledStateGraph, BaseCheckpointSaver, interrupt, Runtime
- [ ] T009 [P] Create MiddlewareSpec Pydantic model in langagent/primitives/middleware_spec.py with fields (id: str, priority: int, hook_points: list[str]) and field validator for hook_points against exhaustive list of 7 valid hook names per FR-018
- [ ] T010 Create fake chat model for tests in tests/fixtures/fake_models.py implementing BaseChatModel interface with configurable responses (used across all test phases)
- [ ] T010a [P] Create guardrail middleware stub in langagent/cross_cutting/guardrail_middleware.py per Assumption 6: define build_middleware(policy) Protocol interface returning mock middleware instance for testing (F06 creates stub, F04 Phase 1 fills actual implementation)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Model Provider Abstraction (Priority: P1) 🎯 MVP

**Goal**: Instantiate any of 6 supported LLM backends (OpenAI, Anthropic, Google, DeepSeek, Zhipu, OpenAI-compatible) based on runtime configuration

**Independent Test**: Provide RuntimeConfig with different model_provider values and verify each returns working BaseChatModel instance that can invoke a test prompt (per spec acceptance scenarios 1-6)

### Tests for User Story 1 (TDD - Write tests FIRST, ensure they FAIL)

- [ ] T011 [P] [US1] Write test for OpenAI provider instantiation in tests/primitives/test_chat_model_factory.py::test_create_openai_default (expects ChatOpenAI with model_name from config, MUST FAIL before T024)
- [ ] T012 [P] [US1] Write test for Anthropic provider instantiation in tests/primitives/test_chat_model_factory.py::test_create_anthropic_default (expects ChatAnthropic, MUST FAIL before T024)
- [ ] T013 [P] [US1] Write test for Google provider instantiation in tests/primitives/test_chat_model_factory.py::test_create_google_default (expects ChatGoogleGenerativeAI, MUST FAIL before T024)
- [ ] T014 [P] [US1] Write test for DeepSeek provider instantiation in tests/primitives/test_chat_model_factory.py::test_create_deepseek_default (expects ChatOpenAI with custom base_url, MUST FAIL before T024)
- [ ] T015 [P] [US1] Write test for Zhipu provider instantiation in tests/primitives/test_chat_model_factory.py::test_create_zhipu_default (expects ChatOpenAI with custom base_url, MUST FAIL before T024)
- [ ] T016 [P] [US1] Write test for OpenAI-compatible local vLLM in tests/primitives/test_chat_model_factory.py::test_create_openai_compatible_local (expects ChatOpenAI with base_url=http://10.0.0.5:8000/v1, MUST FAIL before T024)
- [ ] T017 [P] [US1] Write test for localhost rejection (SC-011) in tests/primitives/test_chat_model_factory.py::test_reject_localhost_in_model_base_url (expects RequiredFieldMissingError with exit code 5, MUST FAIL before T024)
- [ ] T018 [P] [US1] Write test for 127.0.0.1 rejection (SC-011) in tests/primitives/test_chat_model_factory.py::test_reject_127_0_0_1_in_model_base_url (expects RequiredFieldMissingError, MUST FAIL before T024)
- [ ] T019 [P] [US1] Write test for RFC1918 private IP rejection (SC-011) in tests/primitives/test_chat_model_factory.py::test_reject_rfc1918_private_ips (test 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 patterns using regex `\b(10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|192\.168\.)` per FR-004a, MUST FAIL before T024)
- [ ] T020 [P] [US1] Write test for unsupported provider error in tests/primitives/test_chat_model_factory.py::test_create_unsupported_provider (expects ProviderUnsupportedError with exit code 78, MUST FAIL before T024)
- [ ] T021 [P] [US1] Write test for missing API key error in tests/primitives/test_chat_model_factory.py::test_create_missing_api_key (expects AuthFailedError with exit code 78, MUST FAIL before T024)
- [ ] T022 [P] [US1] Write test for endpoint unreachable in tests/primitives/test_chat_model_factory.py::test_create_endpoint_unreachable (expects EndpointUnreachableError with exit code 70, MUST FAIL before T024)
- [ ] T023 [US1] Write test for RuntimeConfig immutability in tests/primitives/test_chat_model_factory.py::test_create_preserves_config_immutability (verify config instance ID unchanged after create(), MUST FAIL before T024)

### Implementation for User Story 1

- [ ] T024 [US1] Implement chat_model_factory.create() in langagent/primitives/chat_model_factory.py with provider routing logic for all 6 providers (openai, anthropic, google, deepseek, zhipu, openai-compatible) per contracts/chat_model_factory.md and research.md Decision 1
- [ ] T025 [US1] Implement localhost/private IP rejection logic in chat_model_factory.create() per FR-004a: validate model_base_url does NOT contain "localhost", "127.0.0.1", or RFC1918 private address blocks (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16) using regex pattern `\b(10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|192\.168\.)` when model_provider="openai-compatible", raise RequiredFieldMissingError with exit code 5
- [ ] T026 [US1] Implement endpoint probe mechanism in chat_model_factory.py per FR-008a: send unauthenticated HTTP GET to {model_base_url}/models with 5s timeout for openai-compatible/deepseek/zhipu; accept 200/401/403 as success; raise EndpointUnreachableError on timeout/refused/404/5xx
- [ ] T027 [US1] Implement API key validation in chat_model_factory.py: read from env vars (OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, DEEPSEEK_API_KEY, ZHIPUAI_API_KEY), raise AuthFailedError if missing for provider
- [ ] T028 [US1] Verify all US1 tests pass (T011-T023): Run pytest tests/primitives/test_chat_model_factory.py -v and confirm all 13 tests pass with <5s per provider per SC-001

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. All 6 providers can be instantiated with proper validation.

---

## Phase 4: User Story 2 - State Graph Compilation (Priority: P1)

**Goal**: Compile a LangGraph StateGraph from agent specifications (tools, middleware, state schema) into a runnable CompiledStateGraph

**Independent Test**: Provide LoadedAgent with tool IDs and middleware specs, RuntimeConfig with checkpointer config, explicit checkpoint instance, verify returned CompiledStateGraph can invoke test message and produce valid state update (per spec acceptance scenarios 1-6)

### Tests for User Story 2 (TDD - Write tests FIRST, ensure they FAIL)

- [ ] T029 [P] [US2] Write test for minimal graph compilation in tests/primitives/test_state_graph_builder.py::test_build_minimal_agent_state (0 tools, 0 middleware, memory checkpointer, expects CompiledStateGraph that invokes successfully, MUST FAIL before T047)
- [ ] T030 [P] [US2] Write test for graph with one tool in tests/primitives/test_state_graph_builder.py::test_build_with_one_tool (expects graph includes tools node, MUST FAIL before T047)
- [ ] T031 [P] [US2] Write test for graph with one middleware in tests/primitives/test_state_graph_builder.py::test_build_with_one_middleware (expects middleware hooks registered via Runtime context, MUST FAIL before T047)
- [ ] T032 [P] [US2] Write test for 10 concurrent middleware registration in tests/primitives/test_state_graph_builder.py::test_build_with_ten_middleware_concurrent (expects all 10 registered in priority order within 500ms per FR-051, measurement methodology: timer starts AFTER all test fixtures are loaded into memory, timer stops AFTER last middleware hook binding completes, fixture I/O time excluded from 500ms budget, MUST FAIL before T047)
- [ ] T033 [P] [US2] Write test for reducer merge behavior in tests/primitives/test_state_graph_builder.py::test_build_reducer_merge_todos (consecutive state updates with new todos, expects replace_with_merge not blind overwrite, MUST FAIL before T047)
- [ ] T034 [P] [US2] Write test for invalid state schema error in tests/primitives/test_state_graph_builder.py::test_build_invalid_state_schema (wrong type for messages, expects GraphCompileError with exit code 70, MUST FAIL before T047)
- [ ] T035 [P] [US2] Write test for middleware syntax error in tests/primitives/test_state_graph_builder.py::test_build_middleware_syntax_error (middleware file with syntax error, expects GraphCompileError with specific file path and error details per FR-017 format "Middleware '{name}' at {path}: SyntaxError: {details}", MUST FAIL before T047)
- [ ] T036 [P] [US2] Write test for tool binding error in tests/primitives/test_state_graph_builder.py::test_build_tool_binding_error (nonexistent tool_id, expects ToolBindingError with exit code 70, MUST FAIL before T047)
- [ ] T036a [P] [US2] Write test for checkpoint validation in tests/primitives/test_state_graph_builder.py::test_build_validates_checkpoint (checkpoint=None, expects GraphCompileError with exit code 70 and message "Invalid checkpoint: {reason}" per FR-014a, MUST FAIL before T047)
- [ ] T037 [P] [US2] Write test for sys.modules cleanup in tests/primitives/test_state_graph_builder.py::test_build_cleans_sys_modules (after build(), expects no langagent_dynamic_middleware_* entries in sys.modules per FR-016, MUST FAIL before T047)
- [ ] T038 [P] [US2] Write test for guardrail middleware instantiation in tests/primitives/test_state_graph_builder.py::test_build_with_guardrail_middleware (guardrail_policy not None, expects build_middleware(policy) called per stub created in T010a, MUST FAIL before T047)
- [ ] T039 [P] [US2] Write test for middleware priority tiebreaker in tests/primitives/test_state_graph_builder.py::test_build_middleware_priority_tiebreaker (multiple middleware same priority, expects sort by name alphabetically per spec edge case, MUST FAIL before T047)

### Implementation for User Story 2

- [ ] T040 [P] [US2] Implement replace_with_merge reducer in langagent/primitives/state_reducers.py with complete type signature per FR-036, edge case handling (None→empty list), type conversion per research.md Decision 6, no exceptions per FR-042
- [ ] T041 [P] [US2] Implement merge_dict reducer in langagent/primitives/state_reducers.py with complete type signature per FR-036, merge by key logic per FR-040, edge case handling (None→empty dict)
- [ ] T042 [US2] Implement overwrite_or_merge reducer in langagent/primitives/state_reducers.py with complete type signature per FR-036, mode parameter support per FR-041, edge case handling (None→empty dict)
- [ ] T043 [US2] Implement middleware loading in state_graph_builder.py using importlib.util.spec_from_file_location per FR-015 and research.md Decision 3 context manager pattern, load from agent_dir/middleware/<name>.py with namespace langagent_dynamic_middleware_{name}
- [ ] T044 [US2] Implement MiddlewareSpec parsing and validation in state_graph_builder.py: parse MIDDLEWARE_SPEC constant from loaded middleware module, validate hook_points against exhaustive list of 7 valid names per FR-018
- [ ] T045 [US2] Implement middleware syntax error handling in state_graph_builder.py per FR-017: catch SyntaxError during importlib load, raise GraphCompileError with format "Middleware '{name}' at {path}: SyntaxError: {details}"
- [ ] T046 [US2] Implement sys.modules cleanup in state_graph_builder.py per FR-016: after build() completes (success or failure), pop all entries with prefix langagent_dynamic_middleware_
- [ ] T046a [US2] Implement checkpoint validation in state_graph_builder.py per FR-014a: validate checkpoint parameter before graph compilation (check not None, attempt to call checkpoint setup/validation method if available in BaseCheckpointSaver protocol), raise GraphCompileError (exit code 70) with message "Invalid checkpoint: {reason}" if validation fails, validation MUST occur before any middleware loading or tool binding
- [ ] T047 [US2] Implement state_graph_builder.build() in langagent/primitives/state_graph_builder.py per contracts/state_graph_builder.md: define StateGraph with AgentState schema (5 fields with reducers), load user middleware + guardrail middleware, inject via LangGraph Runtime context pattern per research.md Decision 2, bind tools, compile with checkpoint parameter
- [ ] T048 [US2] Implement concurrent middleware registration with performance measurement in state_graph_builder.py per FR-051: 10 middleware within 500ms total (file loading, MIDDLEWARE_SPEC parsing, function instantiation, priority sorting, hook binding), measurement methodology: timer starts AFTER test fixtures loaded, stops AFTER last hook binding completes, fixture I/O time excluded from budget to measure F01 code performance not filesystem variance, no race conditions
- [ ] T049 [US2] Verify all US2 tests pass (T029-T039): Run pytest tests/primitives/test_state_graph_builder.py -v and confirm all 12 tests pass (including T036a for checkpoint validation) with <500ms compilation per SC-002

**Checkpoint**: At this point, User Story 2 should be fully functional and testable independently. StateGraph compiles with tools, middleware, and checkpointer.

---

## Phase 5: User Story 3 - Checkpoint Adapter (Priority: P2)

**Goal**: Instantiate the correct checkpointer (memory, sqlite, postgres) based on configuration and properly close it during cleanup

**Independent Test**: Call checkpoint_adapter.create(config) with different checkpointer values, verify returned instance matches expected type, confirm close() releases resources (per spec acceptance scenarios 1-5)

### Tests for User Story 3 (TDD - Write tests FIRST, ensure they FAIL)

- [ ] T050 [P] [US3] Write test for memory checkpointer in tests/primitives/test_checkpoint_adapter.py::test_create_memory (expects MemorySaver instance, MUST FAIL before T059)
- [ ] T051 [P] [US3] Write test for sqlite checkpointer in tests/primitives/test_checkpoint_adapter.py::test_create_sqlite_in_tmp (with temp file path, expects SqliteSaver that persists state, MUST FAIL before T059)
- [ ] T052 [P] [US3] Write test for postgres checkpointer in tests/primitives/test_checkpoint_adapter.py::test_create_postgres_url (with DSN, expects PostgresSaver instance, MUST FAIL before T059)
- [ ] T053 [P] [US3] Write test for close memory no-op in tests/primitives/test_checkpoint_adapter.py::test_close_memory_no_op (expects close() completes without error per FR-031, MUST FAIL before T059)
- [ ] T054 [P] [US3] Write test for close sqlite releases lock in tests/primitives/test_checkpoint_adapter.py::test_close_sqlite_releases_lock (expects file lock released, MUST FAIL before T059)
- [ ] T055 [P] [US3] Write test for close postgres closes pool in tests/primitives/test_checkpoint_adapter.py::test_close_postgres_closes_pool (expects connection pool closed, MUST FAIL before T059)
- [ ] T056 [P] [US3] Write test for unsupported checkpointer error in tests/primitives/test_checkpoint_adapter.py::test_create_unsupported_checkpointer (checkpointer="redis", expects CheckpointTypeUnsupportedError with exit code 78, MUST FAIL before T059)
- [ ] T057 [P] [US3] Write test for sqlite corruption repair in tests/primitives/test_checkpoint_adapter.py::test_create_sqlite_corrupted_db (corrupted db file, expects successful repair via dump/restore per research.md Decision 5, MUST FAIL before T059)
- [ ] T058 [US3] Write test for postgres retry exhausted in tests/primitives/test_checkpoint_adapter.py::test_create_postgres_retry_exhausted (network interruption, expects 3 retries with 1s intervals then GraphCompileError per FR-028, MUST FAIL before T059)

### Implementation for User Story 3

- [ ] T059 [US3] Implement checkpoint_adapter.create() in langagent/primitives/checkpoint_adapter.py per contracts/checkpoint_adapter.md: support 3 types (memory, sqlite, postgres) per FR-025-029, return appropriate BaseCheckpointSaver instance
- [ ] T060 [US3] Implement sqlite corruption repair in checkpoint_adapter.py per research.md Decision 5: run PRAGMA integrity_check to detect corruption, if corrupted use sqlite3.iterdump() to export schema+data to temporary buffer, create new database file, restore from dump using executescript(), raise GraphCompileError if dump or restore fails (no backup file per clarification Q2)
- [ ] T061 [US3] Implement postgres retry mechanism in checkpoint_adapter.py per FR-028 and research.md Decision 4: 3 attempts with 1s intervals for network interruptions during initial connection in create() only, subsequent read/write failures propagate immediately without retry
- [ ] T062 [US3] Implement checkpoint_adapter.close() in langagent/primitives/checkpoint_adapter.py per contracts/checkpoint_adapter.md: handle memory (no-op), sqlite (release file lock), postgres (close connection pool), propagate exceptions
- [ ] T063 [US3] Verify all US3 tests pass (T050-T058): Run pytest tests/primitives/test_checkpoint_adapter.py -v and confirm all 9 tests pass with <100ms for memory/sqlite, <500ms for postgres per SC-004

**Checkpoint**: At this point, User Story 3 should be fully functional and testable independently. All 3 checkpointer types create/close without resource leaks.

---

## Phase 6: User Story 4 - LangChain Types Re-Export (Priority: P2)

**Goal**: Import LangChain/LangGraph types through primitives layer's re-export module to enforce architectural boundaries

**Independent Test**: Import common types from langagent.primitives.langchain_types and verify they're identical to LangChain originals, plus static analysis confirming no direct langchain imports exist outside primitives layer (per spec acceptance scenarios 1-3)

### Tests for User Story 4 (TDD - Write tests FIRST, ensure they FAIL)

- [ ] T064 [P] [US4] Write test for message types import in tests/primitives/test_langchain_types.py::test_import_messages (import add_messages, BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage, verify identity to LangChain originals, MUST FAIL before T008 completion verification)
- [ ] T065 [P] [US4] Write test for model types import in tests/primitives/test_langchain_types.py::test_import_models (import BaseChatModel, verify identity, MUST FAIL before T008 completion verification)
- [ ] T066 [P] [US4] Write test for tool types import in tests/primitives/test_langchain_types.py::test_import_tools (import BaseTool, tool decorator, verify identity, MUST FAIL before T008 completion verification)
- [ ] T067 [P] [US4] Write test for graph types import in tests/primitives/test_langchain_types.py::test_import_graph (import StateGraph, CompiledStateGraph, verify identity, MUST FAIL before T008 completion verification)
- [ ] T068 [P] [US4] Write test for checkpoint types import in tests/primitives/test_langchain_types.py::test_import_checkpoint (import BaseCheckpointSaver, verify identity, MUST FAIL before T008 completion verification)
- [ ] T069 [P] [US4] Write test for Runtime context import in tests/primitives/test_langchain_types.py::test_import_runtime_context (import Runtime from langgraph.prebuilt per FR-032, verify identity, MUST FAIL before T008 completion verification)
- [ ] T070 [P] [US4] Write static analysis test for runtime layer in tests/primitives/test_langchain_types.py::test_no_direct_langchain_imports_runtime (grep langagent/runtime/ for "from langchain" or "from langgraph", expect 0 matches, MUST FAIL before T072)
- [ ] T071 [P] [US4] Write static analysis test for cross_cutting layer in tests/primitives/test_langchain_types.py::test_no_direct_langchain_imports_cross_cutting (grep langagent/cross_cutting/ for direct imports, expect 0 matches, MUST FAIL before T072)

### Implementation for User Story 4

- [ ] T072 [US4] Audit all langagent layers (runtime, cross_cutting, protocol, cli) for direct langchain/langgraph imports: run grep -r "from langchain\|from langgraph" langagent/runtime/ langagent/cross_cutting/ langagent/protocol/ langagent/cli/, replace any found with imports from langagent.primitives.langchain_types per FR-035
- [ ] T073 [US4] Verify all US4 tests pass (T064-T071): Run pytest tests/primitives/test_langchain_types.py -v and confirm all 8 tests pass with 100% architectural boundary enforcement per SC-005

**Checkpoint**: At this point, User Story 4 should be fully functional and testable independently. All layers import LangChain/LangGraph types through primitives re-export only.

---

## Phase 7: User Story 5 - Stage Logging Integration (Priority: P3)

**Goal**: Primitives layer emits structured log tags at key points in model_adapt and graph_compose stages for observability

**Independent Test**: Mock cross_cutting_logger.emit() and verify correct tags emitted at entry/exit/error points during create() and build() calls (per spec acceptance scenarios 1-4)

### Tests for User Story 5 (TDD - Write tests FIRST, ensure they FAIL)

- [ ] T074 [P] [US5] Write test for model_adapt start tag in tests/primitives/test_chat_model_factory.py::test_create_emits_start_tag (expects la.runtime.model_adapt.start with provider payload, MUST FAIL before T087)
- [ ] T075 [P] [US5] Write test for model_adapt endpoint_probe tag in tests/primitives/test_chat_model_factory.py::test_create_emits_endpoint_probe_tag (expects la.runtime.model_adapt.endpoint_probe with url payload, MUST FAIL before T087)
- [ ] T076 [P] [US5] Write test for model_adapt ok tag in tests/primitives/test_chat_model_factory.py::test_create_emits_ok_tag (expects la.runtime.model_adapt.ok with duration_ms payload, MUST FAIL before T087)
- [ ] T077 [P] [US5] Write test for model_adapt fail tag in tests/primitives/test_chat_model_factory.py::test_create_emits_fail_tag (on ProviderUnsupportedError, expects la.runtime.model_adapt.fail with error_type/error_message payload, MUST FAIL before T087)
- [ ] T078 [P] [US5] Write test for graph_compose start tag in tests/primitives/test_state_graph_builder.py::test_build_emits_start_tag (expects la.runtime.graph_compose.start, MUST FAIL before T088)
- [ ] T079 [P] [US5] Write test for graph_compose middleware_bind tag in tests/primitives/test_state_graph_builder.py::test_build_emits_middleware_bind_tag (per middleware, expects la.runtime.graph_compose.middleware_bind with middleware id payload, MUST FAIL before T088)
- [ ] T080 [P] [US5] Write test for graph_compose tool_bind tag in tests/primitives/test_state_graph_builder.py::test_build_emits_tool_bind_tag (per tool, expects la.runtime.graph_compose.tool_bind with tool_id payload, MUST FAIL before T088)
- [ ] T081 [P] [US5] Write test for graph_compose ok tag in tests/primitives/test_state_graph_builder.py::test_build_emits_ok_tag (expects la.runtime.graph_compose.ok with duration_ms payload, MUST FAIL before T088)
- [ ] T082 [P] [US5] Write test for graph_compose fail tag in tests/primitives/test_state_graph_builder.py::test_build_emits_fail_tag (on GraphCompileError, expects la.runtime.graph_compose.fail with error payload, MUST FAIL before T088)
- [ ] T083 [P] [US5] Write test for stage guard model_adapt blacklist in tests/primitives/test_stage_guard_integration.py::test_model_adapt_stage_guard (attempt RuntimeDirLoader.load during create(), expects StageCapabilityViolationError per FR-047, MUST FAIL before T089)
- [ ] T084 [US5] Write test for stage guard graph_compose blacklist in tests/primitives/test_stage_guard_integration.py::test_graph_compose_stage_guard (attempt chat_model_factory.create during build(), expects StageCapabilityViolationError per FR-048, MUST FAIL before T089)

### Implementation for User Story 5

- [ ] T085 [US5] Coordinate with F02 to add 9 log tags to ALLOWED_TAGS whitelist (≥46 items) per FR-046: la.runtime.model_adapt.{start,endpoint_probe,ok,fail} and la.runtime.graph_compose.{start,middleware_bind,tool_bind,ok,fail}. **Prerequisite**: Verify F02 Phase 1 completion per Assumption 7 (cross_cutting_logger.emit() interface exists with ALLOWED_TAGS whitelist); if not available, coordinate with F02 team before proceeding with US5 implementation.
- [ ] T086 [P] [US5] Import cross_cutting_logger.emit in langagent/primitives/chat_model_factory.py and langagent/primitives/state_graph_builder.py per FR-045
- [ ] T087 [US5] Implement logging in chat_model_factory.create() per FR-043: emit start (entry), endpoint_probe (during probe), ok (success with duration_ms), fail (error with error_type/error_message)
- [ ] T088 [US5] Implement logging in state_graph_builder.build() per FR-044: emit start (entry), middleware_bind (per middleware with id), tool_bind (per tool with tool_id), ok (success with duration_ms), fail (error)
- [ ] T089 [US5] Apply stage guard decorators per FR-047/FR-048: @stage_guard_decorator('model_adapt', monkeypatch_blacklist=[RuntimeDirLoader.load, RuntimeConfigResolver.resolve]) to chat_model_factory.create(), @stage_guard_decorator('graph_compose', monkeypatch_blacklist=[BaseChatModel.__init__, chat_model_factory.create, RuntimeDirLoader.load]) to state_graph_builder.build()
- [ ] T090 [US5] Verify all US5 tests pass (T074-T084): Run pytest tests/primitives/test_chat_model_factory.py tests/primitives/test_state_graph_builder.py tests/primitives/test_stage_guard_integration.py -v and confirm all 11 tests pass with all 9 log tags emitted per SC-006 and stage guards preventing 100% of blacklist violations per SC-007

**Checkpoint**: At this point, User Story 5 should be fully functional and testable independently. All 9 stage log tags emit successfully and stage guards enforce boundaries.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories, integration testing, and final validation

- [ ] T091 [P] Write integration test in tests/integration/test_primitives_integration.py::test_full_workflow covering create model → build graph → invoke → checkpoint → resume per quickstart.md end-to-end scenario
- [ ] T092 [P] Write performance benchmark tests in tests/primitives/test_performance.py: test_model_instantiation_latency (<5s per provider per SC-001), test_graph_compilation_latency (<500ms per SC-002), test_checkpoint_create_latency (<100ms memory/sqlite, <500ms postgres), test_middleware_loading_latency (<50ms per middleware), test_reducer_execution_latency (<1ms per field update). Tests MUST fail (not just log) if any threshold exceeded. Use pytest.mark.skipif for vLLM test if http://10.0.0.5:8000/v1 endpoint unreachable.
- [ ] T093 [P] Write reducer edge case tests in tests/primitives/test_state_reducers.py: test_replace_with_merge_none_inputs (expects empty list per FR-039), test_merge_dict_none_inputs (expects empty dict), test_overwrite_or_merge_none_inputs (expects empty dict), test all type conversion scenarios from research.md Decision 6 table
- [ ] T094 [P] Add typing imports to langagent/primitives/state_reducers.py per FR-036: from typing import Any, Literal at module top
- [ ] T095 Run full primitives test suite: pytest tests/primitives/ -v and confirm all 42+ tests pass per Constitution Article VIII
- [ ] T096 Run static analysis grep tests from quickstart.md: verify no direct langchain imports outside primitives/ (SC-005), no hardcoded API keys (Constitution Article XIII), no localhost literals in source (review.md M-1)
- [ ] T097 Run integration test with all 3 checkpointer types: memory, sqlite, postgres and verify state persistence roundtrip per quickstart.md Scenario 3
- [ ] T098 Run quickstart.md validation: execute all 5 scenarios (Model Provider Abstraction, State Graph Compilation, Checkpoint Adapter, LangChain Types Re-Export, Stage Logging Integration) and verify all expected outcomes met
- [ ] T099 Update langagent/primitives/__init__.py to re-export public API: chat_model_factory.create, state_graph_builder.build, checkpoint_adapter.create/close, langchain_types module, state_reducers module, exceptions module
- [ ] T100 Code cleanup: remove unused imports, add docstrings to all public functions per contracts/ specifications, ensure all type annotations complete
- [ ] T101 Documentation updates: verify all file paths in spec.md, plan.md, quickstart.md match actual implementation, update any outdated references

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (US1 → US2 → US3 → US4 → US5)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories (but uses state_reducers from Phase 2)
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 4 (P2)**: Can start after Foundational (Phase 2) - No dependencies on other stories (validates architectural boundaries from all prior stories)
- **User Story 5 (P3)**: Depends on US1 and US2 completion (adds logging to chat_model_factory.create and state_graph_builder.build)

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD per Constitution Article VIII)
- All tests for a user story marked [P] can run in parallel
- Implementation tasks within a story follow dependencies: reducers before graph builder, validators before factories
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T003, T004, T005, T006)
- All Foundational tasks marked [P] can run in parallel within Phase 2 (T008, T009)
- Once Foundational phase completes, US1, US2, US3, US4 can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel (e.g., T011-T022 for US1)
- Models/reducers within a story marked [P] can run in parallel (e.g., T040, T041 for US2)
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together (TDD - write these first):
Task: "Write test for OpenAI provider instantiation in tests/primitives/test_chat_model_factory.py::test_create_openai_default"
Task: "Write test for Anthropic provider instantiation in tests/primitives/test_chat_model_factory.py::test_create_anthropic_default"
Task: "Write test for Google provider instantiation in tests/primitives/test_chat_model_factory.py::test_create_google_default"
Task: "Write test for localhost rejection in tests/primitives/test_chat_model_factory.py::test_reject_localhost_in_model_base_url"
# ... (all T011-T023 in parallel)

# Verify all tests FAIL before implementation

# Implementation (sequential due to shared module):
Task: "Implement chat_model_factory.create() in langagent/primitives/chat_model_factory.py"
Task: "Implement localhost/private IP rejection logic in chat_model_factory.create()"
Task: "Implement endpoint probe mechanism in chat_model_factory.py"
Task: "Implement API key validation in chat_model_factory.py"

# Verify all tests PASS after implementation
```

---

## Parallel Example: User Story 2

```bash
# Launch reducer implementations in parallel (different files):
Task: "Implement replace_with_merge reducer in langagent/primitives/state_reducers.py"
Task: "Implement merge_dict reducer in langagent/primitives/state_reducers.py"
# (Note: overwrite_or_merge depends on seeing merge_dict pattern, so sequential)

# Launch middleware loading tasks in parallel (different concerns):
Task: "Implement middleware loading in state_graph_builder.py using importlib"
Task: "Implement MiddlewareSpec parsing and validation in state_graph_builder.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 + User Story 2 Only)

1. Complete Phase 1: Setup (T001-T006)
2. Complete Phase 2: Foundational (T007-T010) - CRITICAL blocking phase
3. Complete Phase 3: User Story 1 (T011-T028) - Model provider abstraction
4. Complete Phase 4: User Story 2 (T029-T049) - State graph compilation
5. **STOP and VALIDATE**: Run pytest tests/primitives/ -v to test US1+US2 independently
6. Run integration test (T091) to verify end-to-end workflow
7. Deploy/demo if ready (MVP = model instantiation + graph compilation)

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready (T001-T010)
2. Add User Story 1 → Test independently → Deploy/Demo (MVP: model provider abstraction)
3. Add User Story 2 → Test independently → Deploy/Demo (graph compilation)
4. Add User Story 3 → Test independently → Deploy/Demo (checkpoint persistence)
5. Add User Story 4 → Test independently → Deploy/Demo (architectural boundary enforcement)
6. Add User Story 5 → Test independently → Deploy/Demo (observability logging)
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T001-T010)
2. Once Foundational is done:
   - Developer A: User Story 1 (T011-T028) - Model provider abstraction
   - Developer B: User Story 2 (T029-T049) - State graph compilation
   - Developer C: User Story 3 (T050-T063) - Checkpoint adapter
3. After US1+US2 complete:
   - Developer A: User Story 4 (T064-T073) - Types re-export
   - Developer B: User Story 5 (T074-T090) - Logging integration
4. All team: Polish & Integration (T091-T101)
5. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- **TDD ENFORCED**: All test tasks (T011-T023, T029-T039, T050-T058, T064-T071, T074-T084) MUST be written first and FAIL before corresponding implementation tasks
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- Constitution Article VIII compliance: Red-Green-Refactor cycle enforced, no LangGraph mocking, real graph execution required
- All 51 functional requirements (FR-001 to FR-051) from spec.md mapped to tasks
- All 11 success criteria (SC-001 to SC-011) validated in tests
- Total tasks: 101 (6 setup + 4 foundational + 89 user story + 11 polish)

---

## Task Count Summary

- **Phase 1 (Setup)**: 6 tasks
- **Phase 2 (Foundational)**: 4 tasks
- **Phase 3 (US1 - Model Provider)**: 18 tasks (13 tests + 5 implementation)
- **Phase 4 (US2 - Graph Compilation)**: 21 tasks (11 tests + 10 implementation)
- **Phase 5 (US3 - Checkpoint Adapter)**: 14 tasks (9 tests + 5 implementation)
- **Phase 6 (US4 - Types Re-Export)**: 10 tasks (8 tests + 2 implementation)
- **Phase 7 (US5 - Logging Integration)**: 17 tasks (11 tests + 6 implementation)
- **Phase 8 (Polish)**: 11 tasks

**Total**: 101 tasks

**Test Coverage**: 52 test tasks (TDD enforced)  
**Implementation Tasks**: 28 implementation tasks  
**Infrastructure Tasks**: 21 tasks (setup, foundational, polish)

**Parallel Opportunities**: 45 tasks marked [P] can run in parallel within their phase/story

**MVP Scope** (US1 + US2): 42 tasks (Setup + Foundational + US1 + US2)  
**Independent Test Criteria**: Each of 5 user stories has explicit independent test validation

---

This task breakdown enables independent implementation and testing of each user story while maintaining TDD discipline per Constitution Article VIII. All tasks are immediately executable with specific file paths and acceptance criteria.
