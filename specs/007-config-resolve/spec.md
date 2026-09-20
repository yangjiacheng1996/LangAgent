# Feature Specification: Configuration Resolution (config_resolve Stage)

**Feature Branch**: `007-config-resolve`

**Created**: 2026-09-20

**Status**: Draft

**Input**: User description: "F07 — 配置解析（config_resolve 阶段）"

**Constitutional Alignment**: This specification aligns with Constitution Article XV (Top-Level Design Primacy). All design decisions reference the authoritative artifacts in `harness/top_level_design/`:
- `workflow.md#stage-config_resolve` — Stage 2 inputs, outputs, failure modes, and exit codes
- `architecture_modules.md#mod-runtime-config-resolver` — Module responsibilities, API, and dependency matrix
- `module_schemas.md#schema-runtime-config` — RuntimeConfig 13 fields, priority chain, and frozen constraints
- Constitution Article XII — Configuration priority chain and startup logging
- Constitution Article IV — Model abstraction layer with default `openai-compatible` provider

## Clarifications

### Session 2026-09-20

- Q: 当环境变量 `LANGAGENT_GUARDRAIL_ALLOW_INTERNAL_ENDPOINTS` 的值不是标准布尔值（如 "yes"、"1"、"on"）时，系统应该如何处理？ → A: 宽松解析：接受 "true"/"1"/"yes"/"on" 为 True，"false"/"0"/"no"/"off" 为 False（大小写不敏感），其他值抛出 ValidationError 退出码 78
- Q: 当逗号分隔的列表字段（如 `LANGAGENT_MIDDLEWARE` 或 `LANGAGENT_SKILL_DIRS`）包含空字符串项时（例如 "foo,,bar" 或 "foo, ,bar"），系统应该如何处理？ → A: 过滤空项：自动移除所有空字符串和仅包含空格的项，只保留有效值
- Q: 当 CLI 参数、环境变量和 .env 文件都没有提供 `model_name` 字段，但内置默认值也没有 `model_name` 时，系统应该如何处理？ → A: 要求必填：抛出 RequiredFieldMissingError，退出码 5，强制用户配置 model_name
- Q: 当用户在 .env 文件中为同一个配置项设置了多个值（例如多行 `MODEL_NAME=...`），系统应该如何处理？ → A: 使用最后出现的值：python-dotenv 标准行为，最后一个定义覆盖前面的定义
- Q: 当启动日志需要记录配置源信息时（例如 "model_provider from env" 或 "checkpointer from .env"），日志的详细程度应该如何设置？ → A: 仅记录非默认值来源：只记录从 CLI、env 或 .env 覆盖的字段，使用默认值的字段不单独标注

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Merge Configuration from Multiple Sources (Priority: P1)

A developer runs an agent with configuration provided through CLI arguments, environment variables, and a .env file. The system correctly merges all sources according to the priority chain (CLI > env > .env > defaults) and produces a frozen RuntimeConfig instance.

**Why this priority**: This is the core functionality of the config_resolve stage. Without correct priority merging, users cannot reliably configure their agents. This directly implements Constitution Article XII Section 1.

**Independent Test**: Create test fixtures with conflicting configuration values across all four sources. Call resolve() and verify that the highest-priority value wins for each field. Verify that the priority chain is logged.

**Acceptance Scenarios**:

1. **Given** CLI provides `model_name="gpt-4o"`, env has `MODEL_NAME=claude-3`, and .env has `MODEL_NAME=qwen3-8b`, **When** config is resolved, **Then** RuntimeConfig.model_name equals "gpt-4o"
2. **Given** env provides `MODEL_PROVIDER=anthropic` and .env has `MODEL_PROVIDER=openai`, **When** config is resolved, **Then** RuntimeConfig.model_provider equals "anthropic"
3. **Given** only .env provides `LANGAGENT_CHECKPOINTER=sqlite`, **When** config is resolved, **Then** RuntimeConfig.checkpointer equals "sqlite"
4. **Given** no source provides model_provider, **When** config is resolved, **Then** RuntimeConfig.model_provider equals "openai-compatible" (builtin default)
5. **Given** successful resolution, **When** config is created, **Then** a log entry `la.runtime.config_resolve.ok` is emitted with priority merge details

---

### User Story 2 - Validate Required Fields and Reject Placeholders (Priority: P1)

A developer attempts to run an agent with incomplete configuration (missing required fields or placeholder values like `<your-model-name>`). The system detects the problem, reports which fields are invalid, and exits with a clear error code.

**Why this priority**: Early validation prevents runtime failures with cryptic error messages. Placeholder detection catches common copy-paste mistakes from .env.example files. This ensures users configure their agents properly before execution begins.

**Independent Test**: Create test fixtures with missing required fields (no model_base_url for openai-compatible provider) and placeholder values. Attempt to resolve and verify specific error types and exit codes (5 for missing fields, 78 for placeholders).

**Acceptance Scenarios**:

1. **Given** model_provider is "openai-compatible" but model_base_url is None, **When** config is resolved, **Then** it raises RequiredFieldMissingError listing "model_base_url" and exits with code 5
2. **Given** .env contains `MODEL_NAME=<your-model-name>`, **When** config is resolved, **Then** it raises ConfigPlaceholderError and exits with code 78
3. **Given** .env contains `MODEL_BASE_URL=<your-vllm-endpoint>`, **When** config is resolved, **Then** it raises ConfigPlaceholderError and exits with code 78
4. **Given** model_provider is "unknown", **When** config is resolved, **Then** it raises ValidationError for invalid enum value and exits with code 78
5. **Given** any validation failure, **When** the error occurs, **Then** a log entry `la.runtime.config_resolve.fail` is emitted with error details

---

### User Story 3 - Parse and Validate .env Files (Priority: P1)

A developer places a .env file in the agent directory with configuration values. The system parses the file, handles quotes and comments correctly, and merges the values into the configuration chain.

**Why this priority**: .env files are the standard way to configure agents. Robust parsing handles real-world file formats (quotes, comments, multiline values). This is essential for the "copy agent directory anywhere and it works" promise in Constitution Article V.

**Independent Test**: Create test .env fixtures with various formats (quoted values, comments, blank lines, missing file). Call parse_dotenv() and verify correct parsing or appropriate error handling.

**Acceptance Scenarios**:

1. **Given** .env contains `MODEL_NAME=qwen3-8b`, **When** parsed, **Then** returns `{"MODEL_NAME": "qwen3-8b"}`
2. **Given** .env contains `MODEL_NAME="gpt-4o"` (quoted), **When** parsed, **Then** returns `{"MODEL_NAME": "gpt-4o"}` (quotes removed)
3. **Given** .env contains `# comment\nMODEL_NAME=value`, **When** parsed, **Then** comment is ignored and returns `{"MODEL_NAME": "value"}`
4. **Given** .env file does not exist, **When** parsed, **Then** returns empty dict without raising error
5. **Given** .env contains malformed line `KEY==`, **When** parsed, **Then** raises DotenvMalformedError with exit code 65

---

### User Story 4 - Produce Frozen RuntimeConfig with Metadata (Priority: P2)

The system produces a RuntimeConfig instance with frozen=True, preventing accidental modification. All 13 fields are populated, including metadata about configuration sources (cli_args, env_vars, dotenv_values, builtin_defaults).

**Why this priority**: Immutability prevents bugs from unexpected config changes during runtime. Source metadata enables debugging and audit trails. This implements Constitution Article XII's observability requirements.

**Independent Test**: Call resolve() and verify the returned RuntimeConfig is frozen (assignment raises error), contains all 13 fields, and includes source metadata. Verify with_model() and with_guardrail_policy() methods return new instances.

**Acceptance Scenarios**:

1. **Given** config is resolved successfully, **When** attempting `config.model_provider = "anthropic"`, **Then** raises ValidationError (frozen constraint)
2. **Given** config is resolved successfully, **When** calling config.with_model(fake_model), **Then** returns new RuntimeConfig instance with model field populated and other fields unchanged
3. **Given** config is resolved successfully, **When** inspecting config, **Then** all 13 fields exist (4 source metadata + 4 model + 3 runtime + 1 misc + 1 guardrail)
4. **Given** config is resolved successfully, **When** inspecting config.cli_args, **Then** it contains the exact dict passed to resolve() without mutation
5. **Given** config is resolved successfully, **When** inspecting config.model, **Then** it is None (model instantiation happens in F01 model_adapt stage)

---

### User Story 5 - Enforce Stage Capability Boundaries (Priority: P2)

During the config_resolve stage, the system must prevent operations that belong to other stages (instantiating models, loading agent directories, compiling graphs). If any code attempts these operations, the system immediately detects and blocks them.

**Why this priority**: Stage isolation is a core architectural principle that prevents tangled dependencies and ensures predictable behavior. This enforces the 6-stage pipeline design from workflow.md.

**Independent Test**: Wrap test functions with the stage_guard decorator, attempt blacklisted operations (BaseChatModel.__init__, RuntimeDirLoader.load, chat_model_factory.create), and verify each raises StageCapabilityViolationError with exit code 1.

**Acceptance Scenarios**:

1. **Given** the config_resolve stage is active with stage guards enabled, **When** code attempts to instantiate BaseChatModel, **Then** the monkeypatch system intercepts it and raises StageCapabilityViolationError
2. **Given** the config_resolve stage is active with stage guards enabled, **When** code attempts to call RuntimeDirLoader.load(), **Then** the monkeypatch system intercepts it and raises StageCapabilityViolationError
3. **Given** the config_resolve stage is active with stage guards enabled, **When** code attempts to call chat_model_factory.create(), **Then** the monkeypatch system intercepts it and raises StageCapabilityViolationError
4. **Given** the stage guard decorator wraps a function, **When** the function completes or raises an exception, **Then** all monkeypatches and audit hooks are restored to original state

---

### User Story 6 - Parse List-Based Configuration Fields (Priority: P3)

A developer configures middleware and skill directories using comma-separated environment variables. The system correctly parses these into Python lists.

**Why this priority**: Middleware and skills are common extension points. CSV parsing is standard for environment variables. This enables declarative configuration of agent capabilities.

**Independent Test**: Create test fixtures with CSV environment variables. Call resolve() and verify list fields are correctly parsed and split on commas.

**Acceptance Scenarios**:

1. **Given** env contains `LANGAGENT_MIDDLEWARE=foo,bar,baz`, **When** config is resolved, **Then** RuntimeConfig.middleware_ids equals ["foo", "bar", "baz"]
2. **Given** env contains `LANGAGENT_SKILL_DIRS=/path/one,/path/two`, **When** config is resolved, **Then** RuntimeConfig.skill_dirs equals ["/path/one", "/path/two"]
3. **Given** no source provides middleware_ids, **When** config is resolved, **Then** RuntimeConfig.middleware_ids equals [] (empty list default)

---

### User Story 7 - Emit Startup Logging (Priority: P3)

After successful configuration resolution, the system emits structured startup logs showing LangAgent version, agent directory, model configuration, checkpointer type, and enabled middleware. API keys are never logged.

**Why this priority**: Startup logs enable debugging, auditing, and support. They implement Constitution Article XII Section 2 observability requirements. This is lower priority because the system works without logs, but they significantly improve operational visibility.

**Independent Test**: Call resolve() successfully and verify cross_cutting_logger.emit() is called with appropriate tags and sanitized data (no API keys).

**Acceptance Scenarios**:

1. **Given** config is resolved successfully, **When** resolution completes, **Then** cross_cutting_logger.emit() is called with tag `la.runtime.config_resolve.ok`
2. **Given** env contains `OPENAI_API_KEY=sk-secret`, **When** startup log is emitted, **Then** the log does not contain "sk-secret"
3. **Given** .env contains 10 keys, **When** startup log is emitted, **Then** only tracked configuration fields are logged (not all 10 keys dumped)

---

## Functional Requirements *(mandatory)*

### FR-1: Priority Chain Merging

The system SHALL implement a strict 4-source priority chain for configuration resolution:

1. CLI arguments (highest priority)
2. Environment variables
3. Agent directory .env file
4. Builtin defaults (lowest priority)

For each configuration field, the system SHALL use the value from the highest-priority source that provides a non-None value for that field. The merging process SHALL be logged with explicit notation of which source provided each final value.

**Assumptions**:
- CLI arguments are provided as a Python dict by the cli_runner module
- Environment variables are captured as an os.environ snapshot at the start of resolution
- .env file path is `{agent_dir}/.env`
- Builtin defaults are defined in `langagent/runtime/defaults.py`

**Rationale**: This implements Constitution Article XII Section 1 and workflow.md stage 2 requirements.

---

### FR-2: Required Field Validation

The system SHALL validate that all required configuration fields are present after priority chain merging. Required fields and their validation rules:

- `model_provider`: MUST be one of ["openai", "anthropic", "google", "deepseek", "zhipu", "openai-compatible"]
- `model_name`: MUST be non-None (cannot run agent without specifying a model name). Validation SHALL occur in validate_required_fields() after merge_priority_chain() completes.
- `model_base_url`: MUST be non-None when model_provider is "openai-compatible", "deepseek", or "zhipu"
- `checkpointer`: MUST be one of ["memory", "sqlite", "postgres"]
- `log_level`: MUST be one of ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

If any required field is missing or invalid, the system SHALL raise an appropriate error with exit code 5 (RequiredFieldMissingError) or 78 (ValidationError for invalid enum values).

**Assumptions**:
- OpenAI, Anthropic, and Google providers have builtin base_url values and do not require model_base_url configuration
- model_name is always required - users must explicitly specify which model to use
- Other fields (middleware_ids, skill_dirs) are optional

**Rationale**: Early validation prevents runtime failures. Requiring model_name ensures users make explicit model selection decisions. Provider-specific base_url requirements align with Constitution Article IV.

---

### FR-3: Placeholder Detection

The system SHALL scan all string-typed configuration values after merging. If any value matches the pattern `^<your-.+>$`, the system SHALL raise ConfigPlaceholderError with exit code 78 and a message indicating which field contains a placeholder.

This validation SHALL apply to all string fields including but not limited to: model_name, model_base_url, and any other string-typed configuration.

**Assumptions**:
- Placeholders follow the standardized format `<your-...>` as defined in v0.4.0 m-NEW-7
- Users copy .env.example to .env but forget to replace placeholders
- Non-string fields (integers, lists, bools) cannot contain placeholders

**Rationale**: This catches the common mistake of running agents with unconfigured .env files copied from .env.example templates.

---

### FR-4: Frozen RuntimeConfig Instance

The system SHALL produce a RuntimeConfig instance with Pydantic `frozen=True` constraint. Once created, all fields SHALL be immutable. Any attempt to modify a field directly SHALL raise a ValidationError.

The RuntimeConfig class SHALL provide methods to create modified copies:
- `with_model(model: BaseChatModel) -> RuntimeConfig`: Returns new instance with model field populated
- `with_model_base_url(base_url: str) -> RuntimeConfig`: Returns new instance with model_base_url updated
- `with_guardrail_policy(policy: GuardrailPolicy) -> RuntimeConfig`: Returns new instance with guardrail_policy updated

**Assumptions**:
- Immutability prevents accidental configuration changes during runtime
- Stage-specific modifications (like adding the model instance in F01) require creating new instances
- All 13 fields must be preserved when creating modified copies

**Rationale**: Immutability ensures configuration stability and predictability throughout the agent lifecycle.

---

### FR-5: GuardrailPolicy Resolution

The system SHALL parse guardrail configuration from environment variables and construct a GuardrailPolicy instance. The resolution SHALL:

1. Read environment variables:
   - `LANGAGENT_GUARDRAIL_MODE`: MUST be one of ["all", "smart", "strict"], defaults to "smart"
   - `LANGAGENT_GUARDRAIL_ALLOW_INTERNAL_ENDPOINTS`: boolean (lenient parsing: accept "true"/"1"/"yes"/"on" as True, "false"/"0"/"no"/"off" as False, case-insensitive; other values raise ValidationError with exit code 78), defaults to True
   - `LANGAGENT_INTERNAL_ENDPOINTS`: comma-separated list of glob patterns or CIDR ranges, defaults to empty list

2. Construct a GuardrailPolicy instance with fields: enabled=True, mode, redact_pii=True, allow_internal_endpoints, internal_endpoint_patterns

3. Add the policy to RuntimeConfig.guardrail_policy field (non-None)

**Assumptions**:
- GuardrailPolicy default aligns with internal vLLM deployment (allow_internal_endpoints=True by default)
- enabled and redact_pii fields have no environment variable override in v1 (always True)
- Invalid mode values raise ValidationError with exit code 78
- Boolean parsing is lenient to accommodate common environment variable formats

**Rationale**: This implements Constitution Article X security requirements and enables F04 guardrail evaluation without F04 needing to read environment variables directly. Lenient boolean parsing improves user experience with common environment variable conventions.

---

### FR-6: .env File Parsing

The system SHALL parse .env files using the python-dotenv library. The parser SHALL:

1. Support standard .env syntax: `KEY=VALUE`
2. Handle quoted values: `KEY="VALUE"` (quotes removed)
3. Ignore comments: lines starting with `#`
4. Ignore blank lines and whitespace
5. Return an empty dict if .env file does not exist (not an error)
6. Raise DotenvMalformedError with exit code 65 if parsing fails
7. When duplicate keys exist, use the last occurrence (python-dotenv standard behavior)

**Assumptions**:
- .env files are UTF-8 encoded
- Multiline values are not required for v1
- Only one .env file per agent directory (no chaining or includes)
- Duplicate keys follow python-dotenv convention (last value wins)

**Rationale**: Standard .env parsing enables portable configuration across development and deployment environments. Using python-dotenv's duplicate key behavior ensures consistency with standard tooling.

---

### FR-7: Stage Capability Boundary Enforcement

The system SHALL apply the stage_guard decorator to the resolve() function. The decorator SHALL enforce the following blacklists:

**Monkeypatch blacklist**:
- `BaseChatModel.__init__`
- `RuntimeDirLoader.load`
- `chat_model_factory.create`

**Audit event blacklist**: Empty (config_resolve stage does not read files that trigger audit events)

If any blacklisted operation is attempted, the system SHALL raise StageCapabilityViolationError with exit code 1 and emit `la.runtime.config_resolve.fail` log.

**Assumptions**:
- stage_guard decorator is provided by F06 at `langagent/cross_cutting/stage_guard.py`
- Monkeypatching occurs before function execution and is restored after
- Audit hooks are installed before function execution and removed after

**Rationale**: This enforces the 6-stage pipeline architecture from workflow.md and prevents cross-stage contamination.

---

### FR-8: Configuration Source Metadata

The system SHALL include metadata about configuration sources in the RuntimeConfig instance. The following 4 fields SHALL be populated:

- `cli_args`: dict[str, Any] - exact dict passed to resolve(), unmodified
- `env_vars`: dict[str, str] - snapshot of os.environ at resolution start
- `dotenv_values`: dict[str, str] - parsed .env file contents
- `builtin_defaults`: dict[str, Any] - builtin default values from defaults.py

These metadata fields enable debugging, auditing, and understanding configuration precedence.

**Assumptions**:
- Environment variable snapshot is taken once at the start of resolve() to prevent mid-execution changes
- Input cli_args dict is not mutated (copy if needed)
- Sensitive values (API keys) are stored in metadata but never logged

**Rationale**: Configuration source metadata implements Constitution Article XII observability requirements.

---

### FR-9: Provider-Specific base_url Resolution

The system SHALL map model_base_url configuration keys based on model_provider:

- `openai-compatible` → reads `MODEL_BASE_URL`
- `deepseek` → reads `DEEPSEEK_BASE_URL`
- `zhipu` → reads `ZHIPUAI_BASE_URL`
- `openai`, `anthropic`, `google` → do not read base_url from environment (provider SDK has builtin defaults)

The system SHALL raise RequiredFieldMissingError with exit code 5 if base_url is required but not provided.

**Assumptions**:
- Provider SDK defaults are sufficient for openai, anthropic, and google
- Internal deployments of deepseek and zhipu require explicit base_url configuration
- openai-compatible is the default provider (Constitution Article IV Section 4)

**Rationale**: Provider-specific configuration enables flexible model deployment while maintaining simple configuration for common providers.

---

### FR-10: Startup Logging with Sanitization

The system SHALL emit startup logs via cross_cutting_logger.emit() with tag `la.runtime.config_resolve.ok` after successful configuration resolution. The log SHALL include:

- LangAgent version
- Agent directory path
- model_provider value
- model_name value (if not None)
- checkpointer type
- middleware_ids list
- Configuration source annotations (only for non-default values: indicate whether each field came from CLI, env, or .env)

The system SHALL NOT log:
- API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)
- Full .env file contents (only tracked configuration fields)
- Sensitive credential values
- Source annotations for fields using builtin defaults (to reduce log noise)

**Assumptions**:
- LangAgent version is available from package metadata or __version__
- cross_cutting_logger module provides emit() function
- Log sanitization is enforced at emission time, not in RuntimeConfig itself
- Only non-default configuration values are annotated with their source to highlight user overrides

**Rationale**: Startup logs implement Constitution Article XII Section 2 observability requirements while protecting sensitive data per Constitution Article X. Source annotations only for non-default values reduce log clutter and highlight actual user configuration decisions.

---

### FR-11: List Field CSV Parsing

The system SHALL parse comma-separated values from environment variables for list-typed configuration fields:

- `LANGAGENT_MIDDLEWARE` → RuntimeConfig.middleware_ids: list[str]
- `LANGAGENT_SKILL_DIRS` → RuntimeConfig.skill_dirs: list[str]

Parsing SHALL:
1. Split on comma
2. Strip whitespace from each item
3. Filter out empty strings and whitespace-only items
4. Return empty list if environment variable is not set or empty

**Assumptions**:
- No support for escaped commas or quoted list items in v1
- List items do not contain commas
- Empty strings after split and whitespace trimming are automatically filtered out to handle cases like "foo,,bar" or "foo, ,bar"

**Rationale**: CSV format is standard for environment variable lists and enables declarative configuration of agent capabilities. Automatic filtering of empty items improves robustness against accidental formatting errors.

---

### FR-12: Model Field Initialization

The system SHALL initialize RuntimeConfig.model field to None in the config_resolve stage. Model instantiation SHALL NOT occur in this stage.

The model field SHALL be populated later by F10 dispatch via `config.with_model(chat_model_factory.create(config))` after the model_adapt stage completes.

**Assumptions**:
- BaseChatModel instantiation belongs exclusively to the model_adapt stage (F01)
- RuntimeConfig.model_provider and RuntimeConfig.model_name provide necessary information for later instantiation
- with_model() method creates a new frozen instance with the model field populated

**Rationale**: This enforces stage separation and prevents config_resolve from violating its capability boundaries.

---

## Success Criteria *(mandatory)*

### SC-1: Configuration Priority Chain Correctness

**Metric**: 100% of test cases with overlapping configuration sources produce correct merged values according to the CLI > env > .env > defaults priority chain.

**Verification**: Run test suite with fixtures providing conflicting values across all 4 sources. Assert that each configuration field contains the value from the highest-priority source.

**Target**: All priority chain tests pass without exceptions.

---

### SC-2: Validation Error Detection Rate

**Metric**: 100% of invalid configurations (missing required fields, placeholder values, invalid enum values) are detected and rejected with correct exit codes.

**Verification**: Run test suite with fixtures containing each type of validation error. Assert that appropriate exceptions are raised with correct exit codes (5 for missing fields, 78 for placeholders and invalid enums, 65 for malformed .env).

**Target**: Zero invalid configurations pass through to later stages.

---

### SC-3: Immutability Enforcement

**Metric**: 100% of attempts to modify a frozen RuntimeConfig instance raise ValidationError.

**Verification**: Create a valid RuntimeConfig, attempt to modify each field directly, and verify all attempts raise exceptions. Verify with_model() and related methods create new instances without modifying the original.

**Target**: All immutability tests pass without exceptions.

---

### SC-4: Stage Capability Isolation

**Metric**: 100% of blacklisted operations (model instantiation, directory loading, graph compilation) are blocked during config_resolve stage.

**Verification**: Run test suite with stage_guard enabled, attempt each blacklisted operation, and verify StageCapabilityViolationError is raised with exit code 1.

**Target**: All stage boundary tests pass without exceptions.

---

### SC-5: Startup Logging Completeness

**Metric**: 100% of successful configuration resolutions emit startup logs containing all required fields without sensitive data.

**Verification**: Run resolve() with various configurations, capture emitted logs, and verify presence of required fields (version, agent_dir, model_provider, model_name, checkpointer, middleware_ids) and absence of sensitive data (API keys).

**Target**: All startup logging tests pass without exceptions.

---

## Key Entities *(if applicable)*

### RuntimeConfig

**Description**: Frozen configuration container with 13 fields representing the fully resolved agent runtime configuration.

**Attributes**:
- **Source metadata** (4 fields):
  - cli_args: dict[str, Any]
  - env_vars: dict[str, str]
  - dotenv_values: dict[str, str]
  - builtin_defaults: dict[str, Any]

- **Model configuration** (4 fields):
  - model: BaseChatModel | None (always None from config_resolve stage)
  - model_provider: str
  - model_name: str | None
  - model_base_url: str | None

- **Runtime configuration** (3 fields):
  - checkpointer: str
  - middleware_ids: list[str]
  - skill_dirs: list[str]

- **Miscellaneous** (1 field):
  - log_level: str

- **Guardrail configuration** (1 field):
  - guardrail_policy: GuardrailPolicy | None (non-None from config_resolve stage)

**Relationships**:
- Created by: runtime_config_resolver.resolve()
- Consumed by: F01 model_adapt, F08 main_loop, F10 CLI dispatch
- Modified via: with_model(), with_model_base_url(), with_guardrail_policy() (returns new instances)

**Constraints**:
- Pydantic frozen=True (immutable after creation)
- All 13 fields must be present (no optional fields in the dataclass itself, though some have None as valid values)

---

### GuardrailPolicy

**Description**: Configuration object controlling guardrail behavior for model requests and tool execution.

**Attributes**:
- enabled: bool (always True in v1)
- mode: Literal["all", "smart", "strict"]
- redact_pii: bool (always True in v1)
- allow_internal_endpoints: bool
- internal_endpoint_patterns: list[str] (glob patterns or CIDR ranges)

**Relationships**:
- Created by: runtime_config_resolver.resolve() during guardrail configuration parsing
- Stored in: RuntimeConfig.guardrail_policy
- Consumed by: F04 guardrail evaluation

**Constraints**:
- mode must be one of three literal values
- internal_endpoint_patterns can be empty list

---

## Dependencies *(if applicable)*

### Upstream Dependencies

**F06 (Agent Directory Loading)**:
- Provides: `cross_cutting/stage_guard.py` with `@cross_cutting_stage_guard_decorator`
- Used for: Stage capability boundary enforcement
- Constraint: F07 MUST wait for F06 §七 deliverable completion before starting

**F02 (Cross-Cutting Logger)**:
- Provides: `cross_cutting_logger.emit()` function
- Used for: Emitting `la.runtime.config_resolve.ok` and `la.runtime.config_resolve.fail` log events
- Constraint: F07 MUST NOT implement logging directly, must use F02 logger

### Downstream Dependencies

**F01 (Model Adaptation)**:
- Consumes: RuntimeConfig.model_provider, RuntimeConfig.model_name, RuntimeConfig.model_base_url
- Used for: Instantiating BaseChatModel instances
- Constraint: F01 MUST NOT perform configuration resolution, must accept RuntimeConfig from F07

**F10 (CLI Runner)**:
- Consumes: RuntimeConfig from resolve()
- Used for: Orchestrating the 6-stage pipeline
- Constraint: F10 MUST call resolve() with cli_args dict and agent_dir path

**F04 (Audit & Guardrail System)**:
- Consumes: RuntimeConfig.guardrail_policy
- Used for: Evaluating guardrail rules without reading environment variables directly
- Constraint: F04 MUST NOT read LANGAGENT_GUARDRAIL_* environment variables directly

### External Dependencies

**python-dotenv library**:
- Used for: Parsing .env files
- Version: Specified in pyproject.toml
- Constraint: MUST support standard .env syntax (KEY=VALUE, quotes, comments)

**Pydantic library**:
- Used for: RuntimeConfig frozen dataclass with validation
- Version: Specified in pyproject.toml
- Constraint: MUST support frozen=True and field validators

---

## Out of Scope *(optional)*

The following are explicitly NOT part of this feature:

1. **Model Instantiation**: BaseChatModel instances are created by F01 model_adapt stage, not by config_resolve. F07 only populates model_provider, model_name, and model_base_url fields.

2. **Agent Directory Loading**: LoadedAgent creation is handled by F06 dir_load stage. F07 receives agent_dir as a string path parameter but does not scan or validate the directory structure.

3. **Graph Compilation**: LangGraph StateGraph compilation is handled by F01 graph_compose stage. F07 does not interact with LangGraph.

4. **Skill/Tool/Middleware Loading**: Protocol layer components are loaded by F05 and F06. F07 only stores middleware_ids and skill_dirs as lists of strings, not loaded objects.

5. **Event/Span/Metrics Emission**: F07 only emits log events via cross_cutting_logger. Event bus, span creation, and metrics collection are handled by F02 and F03.

6. **Configuration Schema Evolution**: F07 implements the v0.3.0 RuntimeConfig schema as defined in module_schemas.md. Schema versioning and migration are out of scope for v1.

7. **Multi-Environment Configuration**: F07 only supports one .env file per agent directory. Configuration profiles, environment-specific files, and .env chaining are not supported.

8. **Secret Management Integration**: F07 reads environment variables and .env files as plain text. Integration with secret management systems (HashiCorp Vault, AWS Secrets Manager, etc.) is out of scope.

---

## Assumptions *(optional)*

1. **CLI Arguments Pre-Parsed**: The cli_runner module has already parsed argv into a Python dict before calling resolve(). F07 does not interact with sys.argv or argparse directly.

2. **Single .env File**: Each agent directory has at most one .env file located at `{agent_dir}/.env`. No support for .env.local, .env.production, or other variants.

3. **UTF-8 Encoding**: All .env files are UTF-8 encoded. No automatic encoding detection or conversion.

4. **No Configuration Encryption**: All configuration values (including API keys) are stored as plain text in environment variables and .env files. Encryption is not required for v1.

5. **Synchronous Resolution**: Configuration resolution is synchronous and single-threaded. No concurrent access to os.environ or file system.

6. **Stable Environment**: Environment variables do not change during resolve() execution. A snapshot is taken at the start and used throughout.

7. **No Remote Configuration**: All configuration sources are local (CLI args, env vars, .env file, builtin defaults). No fetching configuration from remote APIs, databases, or cloud services.

8. **Provider SDK Base URLs**: OpenAI, Anthropic, and Google provider SDKs have builtin base_url defaults that work for their public APIs. No configuration is needed unless using proxies or custom endpoints.

9. **Builtin Defaults Complete**: The defaults.py module provides valid default values for all required fields. No configuration source is required to produce a minimal working RuntimeConfig (except API keys which must be provided externally).

---

## Notes *(optional)*

### Design Decisions

**Priority Chain Simplicity**: The 4-source priority chain (CLI > env > .env > defaults) is deliberately simple and non-recursive. No support for merging multiple .env files, no support for .env includes, no support for variable interpolation within .env files. This simplicity makes configuration predictable and debuggable.

**Immutability Trade-offs**: The frozen=True constraint prevents accidental modification but requires creating new instances for stage-specific updates (like adding the model in F01). The with_model() / with_guardrail_policy() methods make this explicit and safe, at the cost of slightly more verbose code.

**Provider-Specific base_url Mapping**: The split between MODEL_BASE_URL, DEEPSEEK_BASE_URL, and ZHIPUAI_BASE_URL enables provider-specific configuration files without cross-contamination. This prevents accidental use of the wrong endpoint when switching providers.

**Placeholder Detection Strictness**: The `^<your-.+>$` regex is deliberately strict to avoid false positives. It only matches exact placeholder format from .env.example templates, not partial matches or other bracket-like syntax.

**GuardrailPolicy Default Values**: The default allow_internal_endpoints=True aligns with the internal vLLM deployment use case (Constitution Article IV Section 4). External deployments can override via environment variables.

### Implementation Notes

**TDD Approach**: All 20+ test cases from §四 must be written before implementation (Red phase). Implementation proceeds test-by-test (Green phase). Refactoring occurs only after tests pass.

**Type Safety**: All functions use strict type annotations. The mypy --strict flag must pass before merge. No use of Any except for scratchpad values and generic dict values.

**Error Messages**: All validation errors must include the field name and the invalid value (sanitized if sensitive). Exit codes must match workflow.md specifications exactly.

**Logging Instrumentation**: Every configuration decision (priority override, default fallback, validation failure) should be logged at DEBUG level. Startup logs at INFO level. Errors at ERROR level with full context.

### Future Enhancements (Not in Scope)

1. **Configuration Validation DSL**: A declarative schema for custom validation rules beyond required/enum checks.

2. **Configuration Profiles**: Support for .env.development, .env.production, etc. with automatic selection based on environment.

3. **Variable Interpolation**: Support for referencing other variables within .env files (e.g., `BASE_URL=${PROTOCOL}://${HOST}:${PORT}`).

4. **Remote Configuration**: Fetching configuration from etcd, Consul, AWS Parameter Store, etc.

5. **Configuration Merging Strategies**: Beyond simple priority override, support for deep merging of nested objects.

6. **Secret Rotation**: Automatic refresh of API keys and credentials without restarting the agent.

7. **Configuration Schema Versioning**: Automatic migration from older RuntimeConfig schema versions to current.

8. **Configuration Validation Levels**: Warn-only mode for non-critical validation failures vs. strict mode that rejects any invalid configuration.
