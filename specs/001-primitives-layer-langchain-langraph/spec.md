# Feature Specification: F01 — Primitives Layer Encapsulation (LangChain / LangGraph Interface)

**Feature Branch**: `001-primitives-layer-langchain-langraph`

**Created**: 2026-09-17

**Status**: Draft

**Constitutional Alignment**: This specification aligns with Constitution Article XV (Top-Level Design Primacy). See alignment checklist in §Assumptions below.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Model Provider Abstraction (Priority: P1)

As a LangAgent developer, I need to instantiate any of 6 supported LLM backends (OpenAI, Anthropic, Google, DeepSeek, Zhipu, OpenAI-compatible) based on runtime configuration, so that users can switch between cloud providers and local vLLM deployments without code changes.

**Why this priority**: This is the foundational capability required by Constitution Article IV (Model Abstraction Layer). Without this, LangAgent cannot fulfill its core promise of provider independence and local-first deployment.

**Independent Test**: Can be fully tested by providing a `RuntimeConfig` with different `model_provider` values and verifying that each returns a working `BaseChatModel` instance that can successfully invoke a test prompt.

**Acceptance Scenarios**:

1. **Given** a `RuntimeConfig` with `model_provider="openai"` and valid `OPENAI_API_KEY` env var, **When** `chat_model_factory.create(config)` is called, **Then** it returns a `ChatOpenAI` instance with `model_name` matching the config
2. **Given** a `RuntimeConfig` with `model_provider="openai-compatible"` and `model_base_url="http://10.0.0.5:8000/v1"`, **When** `create()` is called, **Then** it returns a `ChatOpenAI` instance configured with the custom base URL for local vLLM
3. **Given** a `RuntimeConfig` with `model_provider="anthropic"` and valid API key, **When** `create()` is called, **Then** it returns a `ChatAnthropic` instance
4. **Given** a `RuntimeConfig` with `model_provider="unknown"`, **When** `create()` is called, **Then** it raises `ProviderUnsupportedError` with exit code 78
5. **Given** a frozen `RuntimeConfig` instance, **When** `create()` is called, **Then** the config instance ID remains unchanged (immutability preserved)
6. **Given** a `RuntimeConfig` with `model_provider="openai-compatible"` and `model_base_url="http://localhost:8000/v1"`, **When** `create()` is called, **Then** it raises `RequiredFieldMissingError` with exit code 5 and error message indicating hardcoded localhost is forbidden

---

### User Story 2 - State Graph Compilation (Priority: P1)

As a LangAgent developer, I need to compile a LangGraph `StateGraph` from agent specifications (tools, middleware, state schema) into a runnable `CompiledStateGraph`, so that the ReAct agent loop can execute with proper state management and checkpointing.

**Why this priority**: This is the second half of the model_adapt/graph_compose pipeline (stages 3-4 in workflow.md). Without graph compilation, LangAgent cannot execute any agent logic. This is equally critical to P1 as model instantiation.

**Independent Test**: Can be fully tested by providing a `LoadedAgent` with tool IDs and middleware specs, a `RuntimeConfig` with checkpointer config, and an explicit checkpoint instance, then verifying the returned `CompiledStateGraph` can be invoked with a test message and produces a valid state update.

**Acceptance Scenarios**:

1. **Given** a minimal `AgentState` with only `messages` field and a memory checkpointer, **When** `state_graph_builder.build(loaded, config, checkpoint)` is called, **Then** it returns a `CompiledStateGraph` that can invoke a test message and maintain conversation history
2. **Given** a `LoadedAgent` with `tool_ids` containing one tool, **When** `build()` is called, **Then** the compiled graph includes a tools node and can execute tool calls
3. **Given** a `RuntimeConfig` with `middleware_ids` containing one middleware spec, **When** `build()` is called, **Then** the middleware hooks are registered and trigger during graph execution
4. **Given** 10 middleware modules with different priorities, **When** `state_graph_builder.build()` loads all middleware concurrently, **Then** all 10 middleware are registered in correct priority order without conflicts
5. **Given** consecutive state updates with new `todos` entries, **When** the graph reducer processes them, **Then** the `todos` field merges according to the `replace_with_merge` reducer (not blind overwrite)
6. **Given** an invalid state schema (e.g., wrong type for `messages`), **When** `build()` is called, **Then** it raises `GraphCompileError` with exit code 70

---

### User Story 3 - Checkpoint Adapter (Priority: P2)

As a LangAgent developer, I need to instantiate the correct checkpointer (memory, sqlite, postgres) based on configuration and properly close it during cleanup, so that agent state can be persisted and resumed across sessions.

**Why this priority**: While checkpoint support is required for production deployments (Constitution Article VI, section 5), the basic in-memory checkpointer can satisfy MVP requirements for P1/P2 user stories. Persistent checkpoint backends are enhancement features.

**Independent Test**: Can be fully tested by calling `checkpoint_adapter.create(config)` with different `checkpointer` values and verifying the returned instance matches the expected type, then confirming `close()` properly releases resources.

**Acceptance Scenarios**:

1. **Given** a `RuntimeConfig` with `checkpointer="memory"`, **When** `checkpoint_adapter.create(config)` is called, **Then** it returns a `MemorySaver` instance
2. **Given** a `RuntimeConfig` with `checkpointer="sqlite"` and a temp file path, **When** `create()` is called, **Then** it returns a `SqliteSaver` that can persist and retrieve state
3. **Given** a `RuntimeConfig` with `checkpointer="postgres"` and a DSN, **When** `create()` is called with mocked postgres connection, **Then** it returns a `PostgresSaver` instance
4. **Given** a `SqliteSaver` instance, **When** `checkpoint_adapter.close(saver)` is called, **Then** the file lock is released and connection is closed
5. **Given** a `RuntimeConfig` with `checkpointer="redis"` (unsupported), **When** `create()` is called, **Then** it raises `CheckpointTypeUnsupportedError` with exit code 78

---

### User Story 4 - LangChain Types Re-Export (Priority: P2)

As a LangAgent developer working in runtime/cross_cutting/cli layers, I need to import LangChain/LangGraph types through the primitives layer's re-export module, so that the primitives layer remains the single point of contact with LangChain/LangGraph (enforcing Constitution Article II architectural boundary).

**Why this priority**: This enforces the architectural principle that only primitives layer imports langchain/langgraph directly. While critical for maintainability, it's a supporting capability rather than user-facing functionality.

**Independent Test**: Can be fully tested by importing common types from `langagent.primitives.langchain_types` and verifying they're identical to the LangChain originals, plus static analysis confirming no direct langchain imports exist outside primitives layer.

**Acceptance Scenarios**:

1. **Given** the primitives layer module `langchain_types.py`, **When** importing `add_messages, BaseMessage, AgentMiddleware, StateGraph`, **Then** all imports succeed and types match LangChain originals
2. **Given** a grep search of runtime/cross_cutting/cli layer modules, **When** searching for `from langchain` or `from langgraph`, **Then** no matches are found (all imports go through primitives re-export)
3. **Given** the `state_graph_builder.build()` implementation, **When** it needs to construct a `StateGraph`, **Then** it imports from `langagent.primitives.langchain_types` not directly from `langgraph.graph`

---

### User Story 5 - Stage Logging Integration (Priority: P3)

As a LangAgent developer, I need the primitives layer to emit structured log tags at key points in model_adapt and graph_compose stages, so that observability tooling can track stage progression and diagnose failures.

**Why this priority**: While logging is required by workflow.md (9 tags for stages 3-4), it's supplementary to core functionality. The system can function without logging, making this lower priority than actual model/graph creation.

**Independent Test**: Can be fully tested by mocking the `cross_cutting_logger.emit()` function and verifying the correct tags are emitted at entry/exit/error points during `create()` and `build()` calls.

**Acceptance Scenarios**:

1. **Given** a successful call to `chat_model_factory.create()`, **When** execution completes, **Then** logs show `la.runtime.model_adapt.start`, `la.runtime.model_adapt.endpoint_probe`, and `la.runtime.model_adapt.ok` tags with appropriate payloads
2. **Given** a `ProviderUnsupportedError` during `create()`, **When** the error is caught, **Then** a `la.runtime.model_adapt.fail` log is emitted with `error_type` and `error_message` in payload
3. **Given** a successful call to `state_graph_builder.build()`, **When** middleware and tools are bound, **Then** logs show `la.runtime.graph_compose.middleware_bind` and `la.runtime.graph_compose.tool_bind` tags
4. **Given** all 9 stage tags emitted by primitives layer, **When** checking against F02's `ALLOWED_TAGS` whitelist, **Then** all tags are present (validation: no `UnknownLogTagError`)

---

### Edge Cases

- What happens when `model_base_url` contains `localhost` or `127.0.0.1` literals? → Reject with `RequiredFieldMissingError` per review.md M-1 (no hardcoded localhost)
- What happens when multiple middleware have the same `priority` value? → Sort by name alphabetically as tiebreaker
- What happens when `LoadedAgent.tool_ids` references a tool that doesn't exist in tool_registry? → Raise `ToolBindingError` with specific tool_id in message, exit code 70
- What happens when checkpointer connection fails mid-build? → Raise `GraphCompileError` with inner exception details, exit code 70
- What happens when `state_graph_builder.build()` is called with `guardrail_policy=None`? → Skip system guardrail middleware instantiation (guardrail_policy=None is valid per RuntimeConfig schema; system guardrail middleware instantiation is skipped when None; F07 typically provides policy but None is acceptable for minimal agent configurations)
- What happens when `sys.modules` already contains `langagent_dynamic_middleware_<name>` from a previous load? → Pop the old entry before `spec_from_file_location` to avoid silent cache hit with stale module
- What happens when a reducer function (e.g., `replace_with_merge`) receives `current=None` and `update=None`? → Return empty container appropriate to field type (empty list for todos, empty dict for files)
- What happens when reducer encounters unexpected data types (e.g., string instead of list for `todos`)? → Attempt type conversion first (e.g., wrap string in list), log error via `cross_cutting_logger.emit` if conversion fails, then return current state
- What happens when endpoint probe succeeds but actual model initialization fails? → Emit both `endpoint_probe` (success) and `model_adapt.fail` tags; final exit code 70
- What happens when endpoint_probe fails? → Immediately fail and raise `EndpointUnreachableError` (exit code 70); no degradation to warnings allowed
- What happens when sqlite database file is corrupted? → Attempt repair using `PRAGMA integrity_check`; if repair fails, raise `GraphCompileError` (exit code 70); no backup file creation
- What happens when middleware Python file has syntax errors? → Immediately fail and raise `GraphCompileError` with specific file path and syntax error details; no partial loading
- What happens when postgres checkpointer encounters network interruption? → Retry up to 3 times with 1-second intervals; raise exception only after all retries exhausted

---

## Requirements *(mandatory)*

### Functional Requirements

**Model Instantiation (chat_model_factory)**

- **FR-001**: System MUST support instantiation of 6 model providers: `openai`, `anthropic`, `google`, `deepseek`, `zhipu`, `openai-compatible`
- **FR-002**: System MUST read API keys from environment variables (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `DEEPSEEK_API_KEY`, `ZHIPUAI_API_KEY`) without hardcoding
- **FR-003**: System MUST read `model_base_url` from `RuntimeConfig.model_base_url` for providers that require it (deepseek, zhipu, openai-compatible)
- **FR-004a**: System MUST reject model_base_url values containing literal strings "localhost", "127.0.0.1", or RFC1918 private address blocks: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 when model_provider is "openai-compatible". Validation logic MUST reject URLs containing:
  - Literal "10." followed by any digits
  - Literal "172." followed by 16-31 (inclusive) as second octet
  - Literal "192.168." followed by any digits
  - Regex reference pattern: `\b(10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|192\.168\.)`
  - Rejection MUST raise RequiredFieldMissingError with exit code 5 and error message "Hardcoded localhost/private IPs forbidden in model_base_url per review.md M-1"
- **FR-005**: System MUST raise `ProviderUnsupportedError` (exit code 78) when `model_provider` is not in the 6 supported values
- **FR-006**: System MUST raise `AuthFailedError` (exit code 78) when required API key environment variable is missing
- **FR-007**: System MUST raise `EndpointUnreachableError` (exit code 70) when `model_base_url` cannot be reached during endpoint probe; no degradation to warnings is allowed (strict quality enforcement)
- **FR-008**: System MUST raise `RequiredFieldMissingError` (exit code 5) when `model_base_url` is None for providers that require it (openai-compatible, deepseek, zhipu)
- **FR-008a**: Endpoint probe mechanism MUST follow these rules:
  - For openai-compatible/deepseek/zhipu: Send **unauthenticated** HTTP GET request to {model_base_url}/models endpoint with 5-second timeout (no API key or auth headers in probe request)
  - For openai/anthropic/google: Skip probe (rely on provider SDK's built-in connection validation)
  - Acceptable HTTP responses: 200 (success), 401/403 (auth required but endpoint reachable - probe succeeds, proceed with authenticated model init)
  - Failure conditions triggering EndpointUnreachableError: timeout, connection refused, DNS resolution failure, 404, 5xx errors
  - Probe MUST complete before model instantiation; failure MUST prevent model object creation
- **FR-009**: System MUST preserve `RuntimeConfig` immutability (frozen=True) during and after model creation
- **FR-010**: System MUST return a `BaseChatModel` instance without modifying the input `RuntimeConfig` (reconstruction via `with_model()` is F10's responsibility per review.md S-1)

**State Graph Compilation (state_graph_builder)**

- **FR-011**: System MUST compile a `StateGraph` with `AgentState` TypedDict containing exactly 5 fields: (1) `messages`, (2) `todos`, (3) `files`, (4) `context`, (5) `scratchpad`
- **FR-012**: System MUST inject reducers for each AgentState field: `add_messages` (for messages), `replace_with_merge` (for todos/scratchpad), `merge_dict` (for files), `overwrite_or_merge` (for context)
- **FR-013**: System MUST load reducer functions from `langagent.primitives.state_reducers` module (not inline in state_graph_builder)
- **FR-014**: System MUST accept an explicit `checkpoint` parameter (BaseCheckpointSaver instance) rather than creating one internally
- **FR-014a**: System MUST validate checkpoint parameter before graph compilation: 
  - Check checkpoint instance is not None
  - Check checkpoint is an instance of BaseCheckpointSaver
  - Attempt to call checkpoint setup/validation method (if available in BaseCheckpointSaver protocol); if no such method exists, validation passes after instance checks
  - Assume caller ensures checkpoint is open/ready (F01 does not check closed state)
  - Raise GraphCompileError (exit code 70) with message "Invalid checkpoint: {reason}" if validation fails
  - Validation MUST occur before any middleware loading or tool binding
- **FR-015**: System MUST load middleware from `agent_dir/middleware/<name>.py` using `importlib.util.spec_from_file_location` with namespace `langagent_dynamic_middleware_{name}`
- **FR-016**: System MUST clean up `sys.modules` entries with prefix `langagent_dynamic_middleware_` after build() completes
- **FR-017**: System MUST parse `MIDDLEWARE_SPEC` module-level constant from each middleware module; if any middleware file has syntax errors, system MUST immediately fail with `GraphCompileError` including specific file path and error details (no partial loading). Error message format: "Middleware '{name}' at {path}: SyntaxError: {details}" (example: "Middleware 'rate_limiter' at /path/to/agent/middleware/rate_limiter.py: SyntaxError: invalid syntax (line 42)"). Line number extraction: use SyntaxError.lineno attribute or parse from exception traceback if lineno is None.
- **FR-018**: System MUST validate MiddlewareSpec.hook_points contains only the following 7 valid hook names (exhaustive list, hardcoded): "on_chat_model_start", "on_chat_model_end", "on_chat_model_stream", "on_tool_start", "on_tool_end", "on_chain_start", "on_chain_end". Any hook name not in this list MUST be rejected with GraphCompileError. This list is frozen for the current LangGraph version locked in pyproject.toml; future LangGraph upgrades may expand this list as part of normal dependency update process
- **FR-019**: System MUST instantiate system guardrail middleware by calling `cross_cutting_guardrail_middleware.build_middleware(policy=RuntimeConfig.guardrail_policy)` when policy is not None
- **FR-020**: System MUST inject both user middleware (from agent_dir) and system guardrail middleware into the graph in priority order (ascending)
- **FR-021**: System MUST raise `GraphCompileError` (exit code 70) when LangGraph compilation fails
- **FR-022**: System MUST raise `ToolBindingError` (exit code 70) when tool binding to model fails
- **FR-023**: System MUST return a `CompiledStateGraph` instance (not `StateGraph`)
- **FR-024**: System MUST support concurrent registration of at least 10 middleware instances without race conditions or priority conflicts

**Checkpoint Management (checkpoint_adapter)**

- **FR-025**: System MUST support 3 checkpointer types: `memory`, `sqlite`, `postgres`
- **FR-026**: System MUST return a `MemorySaver` instance when `checkpointer="memory"`
- **FR-027**: System MUST return a `SqliteSaver` instance when `checkpointer="sqlite"` with path from config; if database file is corrupted, system MUST attempt repair using `PRAGMA integrity_check` before failing
- **FR-028**: System MUST return a `PostgresSaver` instance when `checkpointer="postgres"` with DSN from config; system MUST implement retry mechanism (3 attempts, 1-second intervals) for network interruptions **during initial connection in create() only**; subsequent checkpoint read/write operation failures propagate immediately without retry
- **FR-029**: System MUST raise `CheckpointTypeUnsupportedError` (exit code 78) when checkpointer type is not in the 3 supported values
- **FR-030**: System MUST provide a `close(saver)` function that properly closes sqlite/postgres connections
- **FR-031**: System MUST allow `close()` on `MemorySaver` to complete without error (no-op)

**LangChain Types Re-Export (langchain_types)**

- **FR-032**: System MUST re-export exactly the following types from langagent.primitives.langchain_types module:
  - From langchain_core.messages: `add_messages` (reducer function), `BaseMessage`, `HumanMessage`, `AIMessage`, `SystemMessage`, `ToolMessage`
  - From langchain_core.language_models: `BaseChatModel`
  - From langchain_core.tools: `BaseTool`, `tool` (decorator)
  - From langgraph.graph: `StateGraph`, `CompiledStateGraph`
  - From langgraph.checkpoint: `BaseCheckpointSaver`
  - From langgraph.constants: `interrupt` (control flow function)
  - From langgraph.prebuilt: `Runtime` (context object for middleware hook injection)
- **FR-033**: All re-exports MUST preserve original type signatures without wrapper functions
- **FR-034**: System MUST provide all re-exports from `langagent.primitives.langchain_types` module
- **FR-035**: Runtime/cross_cutting/cli layers MUST NOT contain direct imports from `langchain` or `langgraph` packages

**State Reducers (state_reducers)**

- **FR-036**: System MUST implement 3 custom reducer functions (replace_with_merge, merge_dict, overwrite_or_merge) in langagent.primitives.state_reducers module with complete type signatures:
  - `from typing import Any, Literal`
  - `def replace_with_merge(current: list[dict[str, Any]] | None, update: list[dict[str, Any]] | None) -> list[dict[str, Any]]`
  - `def merge_dict(current: dict[str, dict[str, Any]] | None, update: dict[str, dict[str, Any]] | None) -> dict[str, dict[str, Any]]`
  - `def overwrite_or_merge(current: dict[str, Any] | None, update: dict[str, Any] | None, *, mode: Literal['overwrite', 'merge_with_prior'] = 'merge_with_prior') -> dict[str, Any]`
  - Edge case behavior: When both current and update are None, return empty container (empty list for replace_with_merge, empty dict for merge_dict/overwrite_or_merge) - never return None
  - Inner dict structures use `dict[str, Any]` to tolerate LLM output variations per FR-042
  - System MUST also re-export 1 LangGraph built-in reducer (add_messages) for AgentState field definitions
- **FR-037**: All reducer functions MUST be pure functions (no side effects, no global state mutation)
- **FR-038**: All reducer functions MUST return new objects rather than mutating input parameters
- **FR-039**: System MUST implement `replace_with_merge` to handle None inputs by returning empty list
- **FR-040**: System MUST implement `merge_dict` to merge dicts by key, with update values overriding current values
- **FR-041**: System MUST implement `overwrite_or_merge` with a `mode` parameter supporting 'overwrite' and 'merge_with_prior'
- **FR-042**: Reducer functions MUST NOT raise exceptions; when encountering unexpected data types (e.g., string instead of list for `todos`), system MUST attempt type conversion first, then degrade gracefully by returning current state if conversion fails; log errors via `cross_cutting_logger.emit` for debugging

**Stage Logging Integration**

- **FR-043**: System MUST emit 4 log tags during model_adapt stage: `start`, `endpoint_probe`, `ok`, `fail`
- **FR-044**: System MUST emit 5 log tags during graph_compose stage: `start`, `middleware_bind`, `tool_bind`, `ok`, `fail`
- **FR-045**: System MUST call `cross_cutting_logger.emit(tag, payload)` for all log emissions
- **FR-046**: All 9 emitted tags MUST be registered in F02's `ALLOWED_TAGS` whitelist (≥46 items). Validation: coordinate with F02 to add tags before F01 Phase 5 (User Story 5) implementation; T073 is explicit coordination task

**Stage Guard Decorator Application**

- **FR-047**: System MUST apply `@cross_cutting_stage_guard_decorator('model_adapt', monkeypatch_blacklist=[RuntimeDirLoader.load, RuntimeConfigResolver.resolve])` to `chat_model_factory.create()` entry point
- **FR-048**: System MUST apply `@cross_cutting_stage_guard_decorator('graph_compose', monkeypatch_blacklist=[BaseChatModel.__init__, chat_model_factory.create, RuntimeDirLoader.load])` to `state_graph_builder.build()` entry point
- **FR-049**: Stage guard decorator MUST raise `StageCapabilityViolationError` when blacklisted operations are attempted
- **FR-051**: System MUST complete middleware registration for 10 concurrent instances within 500ms total (50ms per middleware). This is the performance requirement for FR-024's concurrent registration capability. "Registration" is defined as the following steps for each middleware:
  - File loading via importlib.util.spec_from_file_location()
  - MIDDLEWARE_SPEC constant parsing and MiddlewareSpec validation
  - Middleware function instantiation (if MIDDLEWARE_SPEC includes factory pattern)
  - Priority sorting across all loaded middleware
  - Hook binding to LangGraph Runtime context
  - Note: Measurement scope EXCLUDES actual hook execution during graph invocation (that is runtime overhead, not registration cost)
  - Measurement methodology: Timer starts AFTER all test fixtures (agent directory, middleware files) are loaded into memory; timer stops AFTER the last middleware's hook binding completes. Fixture I/O time is excluded from the 500ms budget to ensure measurement reflects F01 code performance, not filesystem variance.
  - Task T043 implements this requirement with explicit measurement methodology

### Key Entities *(include if feature involves data)*

- **BaseChatModel**: LangChain's abstract model interface; produced by chat_model_factory; consumed by graph_compose stage
- **CompiledStateGraph**: LangGraph's executable graph; produced by state_graph_builder; consumed by F08 main_loop dispatcher
- **BaseCheckpointSaver**: LangGraph's state persistence interface; produced by checkpoint_adapter; consumed by state_graph_builder as parameter. **Ownership note**: F01's checkpoint_adapter creates instances; state_graph_builder validates readiness before use (FR-014a). Caller (F10 runtime layer) is responsible for passing valid checkpoint instance.
- **AgentState**: TypedDict with 5 fields (messages, todos, files, context, scratchpad); defines graph state schema; consumed by StateGraph compilation
- **LoadedAgent**: Pydantic model (schema v0.2.0) containing loaded agent metadata; produced by F06 dir_load stage; consumed by state_graph_builder. **Schema fields (5 total)**:
  1. `agent_dir: Path` - Absolute path to agent directory root
  2. `tool_ids: list[str]` - List of tool identifiers loaded from tools/ subdirectory
  3. `skill_names: list[str]` - List of skill names loaded from skills/ subdirectory
  4. `instructions: str` - Content of instructions.md file (system prompt)
  5. `middleware_specs: list[dict]` - Raw middleware metadata dicts parsed from middleware/*.py files
  
  **Historical Note**: `compiled_graph` field was removed in review.md v1.1.0; LoadedAgent now has exactly 5 fields (not 6)
- **MiddlewareSpec**: Pydantic model describing middleware metadata (id, priority, hook_points); **ownership**: F01 owns the Pydantic model definition; agent developers provide `MIDDLEWARE_SPEC` constants in middleware/*.py files which F01 parses; parsed from agent_dir/middleware/*.py; translated to AgentMiddleware instances
- **RuntimeConfig**: Frozen Pydantic model containing configuration snapshot; immutable input to all factory methods; produced by F07 config_resolve stage

---

## Clarifications

### Session 2026-09-17

- Q: 当 `endpoint_probe` 测试失败但开发者希望继续使用该模型时，系统应该如何处理？ → A: 选项 A - 立即失败并抛出 `EndpointUnreachableError`。连接可以重试，但不能降级。模型必须严格要求质量，如果连模型都连不上，不应该继续运行智能体。
- Q: 当 sqlite checkpointer 的数据库文件路径指向一个已存在但损坏的数据库文件时，系统应该如何处理？ → A: 尝试使用 sqlite 的 `PRAGMA integrity_check` 修复损坏的数据库，修复失败则抛出 `GraphCompileError`。不创建备份文件，用户需要为人为损坏承担后果。
- Q: 当 `state_graph_builder.build()` 加载多个 middleware 时，如果其中某个 middleware 的 Python 文件存在语法错误，系统应该如何处理？ → A: 选项 A - 立即失败并抛出 `GraphCompileError`，错误信息中包含具体的 middleware 文件路径和语法错误详情。因为 middleware 是智能体内部代码，语法错误意味着智能体整体失败。
- Q: 当 `reducer` 函数（如 `replace_with_merge`）在处理状态更新时遇到意外的数据类型（例如 `todos` 字段收到字符串而不是列表），系统应该如何处理？ → A: 选项 B - 尝试类型转换（如将字符串包装成列表），转换失败则记录错误日志并返回 `current` 状态。因为有的大模型智力低下，确实会把 todo 变成字符串或输出残缺/非法的 JSON。
- Q: 当 postgres checkpointer 在执行状态保存时遇到网络瞬时中断（例如持续 1-2 秒的网络抖动），系统应该如何处理？ → A: 选项 B - 实现有限次重试机制（3 次，每次间隔 1 秒），重试失败后抛出异常。网络瞬时抖动在生产环境中很常见，有限重试能提高容错能力。

### Session 2026-09-17 (Amendment)

- Q: LangGraph的中间件机制使用Runtime context而非传统的AgentMiddleware，这是否符合宪法第VII条"遵循LangChain middleware协议"的要求？ → A: Runtime context是LangGraph官方推荐的中间件注入模式，LangGraph是LangChain生态的官方工作流编排工具，其Runtime context机制属于LangChain middleware协议的演进形式。宪法第VII条的"LangChain middleware协议"涵盖LangGraph Runtime context模式。结论：使用Runtime context符合宪法要求。

### Session 2026-09-17 (Terminology Standardization)

- Q: What is the canonical term for LangGraph's middleware injection mechanism? → A: Use "LangGraph Runtime context" when referring to the `langgraph.prebuilt.Runtime` type; use "Runtime context pattern" when describing the architectural pattern; never use bare "Runtime" without "context" suffix to avoid confusion with runtime layer. In all requirements and task descriptions, always use full type name "RuntimeConfig" (not abbreviated "config") for clarity and traceability.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: System can instantiate all 6 model providers and successfully invoke a test prompt within 5 seconds on any provider (cloud or local vLLM)
- **SC-002**: State graph compilation completes for a minimal agent (0 tools, 0 middleware) in under 500ms on commodity hardware
- **SC-003**: System supports at least 10 concurrent middleware registrations without performance degradation or priority conflicts, completing within 500ms (measured from post-fixture-load to hook-binding-complete per FR-051 methodology)
- **SC-004**: Checkpointer creation and closure for all 3 types (memory, sqlite, postgres) completes without resource leaks (verified by file descriptor count)
- **SC-005**: 100% of primitives layer imports of LangChain/LangGraph types go through re-export module (verified by static analysis grep test)
- **SC-006**: All 9 stage log tags (4 model_adapt + 5 graph_compose) appear in F02 whitelist and emit successfully during golden path execution
- **SC-007**: Stage guard decorators prevent 100% of attempted blacklist violations (e.g., model_adapt calling RuntimeDirLoader.load) by raising StageCapabilityViolationError
- **SC-008**: Reducer functions handle edge cases (None inputs, empty collections) without raising exceptions in 100% of test scenarios
- **SC-009**: System can switch between providers (openai → openai-compatible → anthropic) by changing only RuntimeConfig fields, with zero code changes
- **SC-010**: Local vLLM Qwen3.8-27B deployment serves as default model and can complete a basic ReAct turn (question → tool call → answer) in under 10 seconds
- **SC-011**: System rejects 100% of model_base_url values containing literal strings "localhost", "127.0.0.1", or RFC1918 private IP address patterns (10.x.x.x, 172.16-31.x.x, 192.168.x.x) when model_provider is "openai-compatible", raising RequiredFieldMissingError with exit code 5 and error message "Hardcoded localhost/private IPs forbidden in model_base_url per review.md M-1"

---

## Assumptions

### Constitutional Alignment Checklist (Article XV Compliance)

This specification aligns with Constitution v1.1.0 as follows:

**Article I (Project Identity)**: F01 implements internal factory abstractions; does not expose SDK or public API. Aligns fully.

**Article II (Technology Stack)**: F01 is the sole point of contact with LangChain/LangGraph. Uses `langchain_openai`, `langchain_anthropic`, `langchain_google_genai`, `langgraph`, `langgraph-checkpoint-sqlite`, `langgraph-checkpoint-postgres`. Does not add dependencies outside this approved list. Aligns fully.

**Article III (LangSmith Removal)**: F01 does not import `langsmith`, does not read `LANGSMITH_API_KEY` or `LANGCHAIN_TRACING_V2` env vars. Aligns fully.

**Article IV (Model Abstraction)**: F01 is the primary implementer of this article. Supports 6 providers with equal priority. Does not hardcode `model_name` or `base_url`. Local OpenAI-compatible (vLLM Qwen3.8-27B) is baseline model for tests. Aligns fully.

**Article V (Agent Directory Contract)**: F01 consumes but does not own agent directory loading (F06 responsibility). Loads middleware from `middleware/` subdirectory using importlib. Aligns fully.

**Article VI (Agent Loop & State)**: F01 implements AgentState with 5 required fields. Uses custom reducers (not bare MessagesState). StateGraph compilation respects LangGraph checkpointer protocol. Aligns fully.

**Article VII (Middleware & Tools)**: F01 implements middleware loading protocol using LangGraph Runtime context pattern (official LangGraph middleware mechanism). Runtime context injection via langgraph.prebuilt.Runtime aligns with LangChain ecosystem middleware conventions. Tools are consumed via LoadedAgent.tool_ids (tool loading is F05 responsibility). Aligns fully.

**Article VIII (TDD)**: This spec defines 56+ test tasks across 5 user stories (US1: 13 tests, US2: 12 tests, US3: 9 tests, US4: 8 tests, US5: 11 tests) plus integration and performance benchmarks. Red-Green-Refactor cycle will be enforced. Tests will not mock LangGraph behavior (real graph execution required). Aligns fully.

**Article IX (Quality Diagnostics)**: F01 emits 9 tracing tags for model_adapt/graph_compose stages. Does not implement full observability stack (F02/F03 responsibility). Aligns with tracing requirements.

**Article X (Security & Privacy)**: F01 does not transmit data externally. Does not hardcode API keys. Reads keys from env only. Guardrail middleware instantiation defers logic to F04. Aligns fully.

**Article XI (Packaging)**: F01 is a library module, not a CLI entry point. Packaging is F12 responsibility. No alignment constraints.

**Article XII (Configuration)**: F01 consumes frozen RuntimeConfig produced by F07's priority chain. Does not parse .env directly. Does not mutate config (returns new instances via with_* methods). Aligns fully.

**Article XIII (Hard No)**: F01 does not depend on LangSmith. Does not hardcode API keys, model names, or base URLs. Does not call provider SDKs directly (only via LangChain abstraction). Does not use print/console.log (uses structured logger). Does not write TDD after implementation. Aligns fully.

**Article XV (Top-Level Design Primacy)**: This spec was created after reading workflow.md (stages 3-4), architecture_modules.md (primitives layer modules), and module_schemas.md (RuntimeConfig, AgentState, LoadedAgent schemas). Alignment checklist provided in this section. Aligns fully.

### Technical Assumptions

- **Assumption 1**: Python version ≥3.10 (specified in pyproject.toml `requires-python` field)
- **Assumption 2**: LangChain/LangGraph versions locked in pyproject.toml; no runtime version detection needed
- **Assumption 3**: Local vLLM deployment at `http://10.0.0.5:8000/v1` is available in test environment (tests skip if unreachable)
- **Assumption 4**: Environment variables for API keys are set by user or .env file before model instantiation
- **Assumption 5**: F06 cross_cutting_stage_guard module exists and provides `@stage_guard_decorator` before F01 implementation starts
- **Assumption 6**: F04 cross_cutting_guardrail_middleware.build_middleware stub (Protocol) exists before F01 implementation (F06 creates stub, F04 Phase 1 fills implementation)
- **Assumption 7**: F02 cross_cutting_logger.emit() interface exists with ≥46-item ALLOWED_TAGS whitelist before F01 starts emitting logs
- **Assumption 8**: F05 protocol_tool_registry provides BaseTool instances via LoadedAgent.tool_ids during graph_compose (or tests use fake tools)
- **Assumption 9**: All middleware modules in agent_dir/middleware/ are well-formed Python with valid MIDDLEWARE_SPEC constant (malformed modules raise ImportError handled by caller)
- **Assumption 10**: Checkpointer DSN/paths in RuntimeConfig are validated by F07 before reaching F01 (F01 assumes well-formed inputs)

### Test Fixtures

**Test Agent Directory Structure** (for integration tests):

- `tests/fixtures/test_agent_dirs/minimal/`: Empty agent directory (0 tools, 0 middleware) for US2 minimal graph test - MUST have instructions.md and agent.yaml per Constitution Article V
- `tests/fixtures/test_agent_dirs/with_middleware/`: Contains `middleware/rate_limiter.py` with valid MIDDLEWARE_SPEC - MUST have instructions.md and agent.yaml
- `tests/fixtures/test_agent_dirs/with_tools/`: Contains `tools/calculator.py` with @tool decorator - MUST have instructions.md and agent.yaml
- All 3 fixture directories referenced in tasks.md T004 must be created during Phase 1 Setup

### Scope Boundaries

- **In scope**: Model instantiation, graph compilation, checkpoint adapter, type re-exports, reducer functions, stage logging, stage guard application
- **Out of scope**: CLI argument parsing (F10), agent directory scanning (F06), RuntimeConfig priority chain merging (F07), tool loading (F05), main loop execution (F08), exit cleanup (F09), evaluation runner (F11), packaging (F12)
- **Deferred to later features**: Actual guardrail logic (F04 Phase 1), full event bus implementation (F07), metrics collection (F08), audit recording (F04)

### Performance Expectations

- Model instantiation: <5s per provider (includes endpoint probe)
- Graph compilation: <500ms for minimal agent (0 tools, 0 middleware)
- Checkpoint creation: <100ms for memory/sqlite, <500ms for postgres (connection pool warmup)
- Middleware loading: <50ms per middleware module (importlib overhead)
- Reducer execution: <1ms per field update (pure Python dict/list operations)

### Dependency Graph

```
F01 depends on:
  - F02 Phase 1 (cross_cutting_logger.emit interface + ALLOWED_TAGS ≥46 whitelist)
  - F06 (cross_cutting_stage_guard decorator + StageCapabilityViolationError)
  - F04 stub (cross_cutting_guardrail_middleware.build_middleware Protocol; actual implementation in F04 Phase 1)

F01 is depended on by:
  - F10 (cli_runner / runtime_main_loop_dispatcher calls create/build/checkpoint_adapter.create)
  - F05 (protocol_tool_registry imports BaseTool via primitives re-export)
  - F03 (runtime_config_resolver references BaseChatModel type annotation)
  - F08 (runtime_main_loop_dispatcher invokes CompiledStateGraph)
  - F09 (runtime_exit_handler calls checkpoint_adapter.close)
```

### Hard Constraints from Top-Level Design

**From workflow.md**:
- Stage 3 (model_adapt) MUST emit 4 tags: start, endpoint_probe, ok, fail
- Stage 4 (graph_compose) MUST emit 5 tags: start, middleware_bind, tool_bind, ok, fail
- Exit codes: 78 for unsupported provider/checkpointer, 70 for graph compile/tool binding errors, 5 for required field missing, 1 for stage capability violation

**From architecture_modules.md**:
- Primitives layer MUST be the only layer importing langchain/langgraph directly
- 3 hard-exception unidirectional edges: primitives_chat_model_factory → cross_cutting_logger, primitives_state_graph_builder → cross_cutting_logger, primitives_state_graph_builder → cross_cutting_guardrail_middleware
- Primitives layer MUST NOT depend on runtime/cli/protocol layers (except cross_cutting as allowed exceptions)
- 5 modules: chat_model_factory, state_graph_builder, checkpoint_adapter, langchain_types, state_reducers

**From module_schemas.md**:
- AgentState MUST have 5 fields with specific reducers (messages: add_messages, todos: replace_with_merge, files: merge_dict, context: overwrite_or_merge, scratchpad: replace_with_merge)
- RuntimeConfig MUST be frozen (immutability via Pydantic frozen=True)
- LoadedAgent schema v0.2.0 has 5 fields (no compiled_graph; that field was removed in review.md v1.1.0)
- MiddlewareSpec owned by F01 (not F05)

### Risk Mitigation

- **Risk**: LangChain provider SDK breaking changes → **Mitigation**: Lock LangChain versions in pyproject.toml; version matrix tests in CI
- **Risk**: Local vLLM unavailable in test environment → **Mitigation**: Tests skip with pytest.mark.skipif when endpoint unreachable
- **Risk**: Middleware importlib namespace collision → **Mitigation**: Use unique namespace `langagent_dynamic_middleware_{name}` and clean sys.modules after each load
- **Risk**: F04 guardrail_middleware not ready when F01 starts → **Mitigation**: F06 creates Protocol stub in first batch; F01 tests mock the interface
- **Risk**: Reducer function edge case raises exception → **Mitigation**: FR-040 requires graceful degradation; all reducers return current state on error rather than propagating exceptions
