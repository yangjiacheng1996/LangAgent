# Feature Specification: Cross-Cutting Audit and Guardrail System

**Feature Branch**: `004-audit-guardrail-system`

**Created**: 2026-09-19

**Status**: Draft

**Constitutional Alignment**: This specification aligns with Article XV (Top-Level Design Primacy) and has been derived from the mandatory design artifacts in `harness/top_level_design/`. See alignment checklist at end of document.

**Input**: User description: F04 — 横切层审计与护栏（cross_cutting_audit_recorder + cross_cutting_guardrail_middleware）

## Clarifications

### Session 2026-09-19

- Q: 审计日志的保留期限和轮转策略是什么？ → A: 按大小轮转（每个文件最大 10MB，保留最近 3 个文件）
- Q: 当审计文件达到轮转阈值（10MB）时，旧文件的命名规则是什么？ → A: 基于时间戳命名（例如 `audit-20260919-143022.jsonl`）
- Q: `query()` 函数是否需要支持跨多个轮转文件查询历史审计记录？ → A: 支持跨文件查询（扫描当前文件 + 所有归档文件，按时间戳过滤）
- Q: prompt injection 检测触发后的默认行为是什么？ → A: 写审计日志 + 在消息中添加 untrusted 标记（继续执行但标记风险）
- Q: `AuditEntry` 中的 `actor` 字段应该填充什么值？ → A: 系统级标识符（例如 `system:guardrail_middleware` 或 `system:audit_recorder`）

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Audit Trail for Security Events (Priority: P1)

As a security administrator, when tools are blocked by guardrails, PII is detected, or unauthorized actions are attempted, I need a permanent, tamper-proof audit log so I can review security incidents and demonstrate compliance.

**Why this priority**: Audit logging is the foundation for all other security features. Without audit trails, guardrail blocks are invisible and compliance cannot be demonstrated. This is the core security capability required by Article X (Security & Privacy).

**Independent Test**: Create an agent that attempts to call a tool marked `requires_approval=True`, verify that the guardrail blocks the call and writes an `AuditEntry` with category `unauthorized_tool` to `~/.local/share/langagent/audit.jsonl`. The audit file must exist, contain exactly one JSON line, and persist after the agent exits.

**Acceptance Scenarios**:

1. **Given** an agent attempts to call a tool marked `requires_approval=True`, **When** the guardrail middleware blocks it, **Then** an audit entry is written with `category=unauthorized_tool`, `severity=info`, and the tool name in `target`
2. **Given** the audit file contains 3 entries, **When** I write a 4th entry and call `flush()`, **Then** the file contains exactly 4 lines and no prior entries are modified (append-only guarantee)
3. **Given** an audit entry contains sensitive data like `api_key=sk-12345`, **When** the entry is written to disk, **Then** the file contains `api_key=***` instead of the actual key
4. **Given** an audit entry contains an email address `user@example.com`, **When** written to disk, **Then** the file contains `***@example.com`
5. **Given** I query for entries with `category=unauthorized_tool` since yesterday, **When** the query executes, **Then** I receive only entries matching that category created after the specified timestamp

---

### User Story 2 - Three-Level Guardrail Modes (Priority: P1)

As an agent operator, I need to configure guardrail strictness via environment variables (all/smart/strict modes) so I can balance security with usability based on my deployment context without modifying code.

**Why this priority**: Guardrail mode selection is the primary security control mechanism. Article X mandates "tool permission minimization" and this is how operators enforce it. Without modes, security is either too lax (no approval) or too strict (blocks everything).

**Independent Test**: Set `LANGAGENT_GUARDRAIL_MODE=strict` in environment, load an agent with any tools, attempt to call a tool. Verify that the guardrail blocks all tool calls regardless of `requires_approval` annotation and writes audit entries with `severity=warn`.

**Acceptance Scenarios**:

1. **Given** guardrail mode is `strict`, **When** any tool is called (regardless of `requires_approval` value), **Then** the call is blocked with `GuardrailDecision(allow=False, interrupt=True, reason="strict mode: deny all tools")`
2. **Given** guardrail mode is `all`, **When** any tool is called, **Then** an interrupt is triggered requiring human approval before execution
3. **Given** guardrail mode is `smart` (default) and a tool has `requires_approval=True`, **When** that tool is called, **Then** an interrupt is triggered
4. **Given** guardrail mode is `smart` and a tool has `requires_approval=False`, **When** that tool is called, **Then** execution proceeds without interrupt
5. **Given** guardrail policy is `enabled=False`, **When** any tool is called, **Then** all tools are allowed without evaluation

---

### User Story 3 - Internal Endpoint Allowlisting (Priority: P2)

As an enterprise user running a local vLLM model, I need the guardrail to distinguish internal endpoints (10.0.0.0/8, *.internal.company.com) from public endpoints so that local model calls are not blocked while external API calls require approval.

**Why this priority**: Article IV mandates that "local models must be viable as defaults" and Article X requires "no external data transmission". This feature allows local deployments to run smoothly while still protecting against unintended external calls.

**Independent Test**: Configure `LANGAGENT_GUARDRAIL_MODE=smart`, `LANGAGENT_GUARDRAIL_ALLOW_INTERNAL_ENDPOINTS=true`, and `LANGAGENT_INTERNAL_ENDPOINTS=10.0.0.0/8`. Create a tool that calls `http://10.0.0.5:8000/v1` with `requires_approval=False`. Verify that the guardrail returns `GuardrailDecision(allow=True, is_internal_endpoint=True)`.

**Acceptance Scenarios**:

1. **Given** internal endpoint patterns include `10.0.0.0/8`, **When** evaluating endpoint `http://10.0.0.5:8000/v1`, **Then** `is_internal()` returns `True`
2. **Given** internal endpoint patterns include `*.internal.example.com`, **When** evaluating endpoint `http://llm.internal.example.com`, **Then** `is_internal()` returns `True`
3. **Given** no pattern matches endpoint `http://api.openai.com`, **When** evaluating this public endpoint, **Then** `is_internal()` returns `False`
4. **Given** smart mode with `requires_approval=False` and internal endpoint, **When** tool is called, **Then** execution is allowed
5. **Given** smart mode with `requires_approval=False` and public endpoint, **When** tool is called, **Then** interrupt is triggered with reason "public endpoint requires approval"

---

### User Story 4 - PII Redaction in Tool Outputs (Priority: P2)

As a compliance officer, I need tool outputs containing PII (emails, phone numbers, API keys) to be automatically redacted before being logged or persisted so that we meet data privacy requirements.

**Why this priority**: Article X mandates PII handling interfaces. While advanced PII detection is deferred to enterprise version, basic pattern matching for emails/phones/keys is essential for v1 compliance baseline.

**Independent Test**: Configure `GuardrailPolicy(redact_pii=True)`, execute a tool that returns content containing "Contact user@example.com or call +1-555-0100". Verify that the middleware's `after_tools` hook redacts the output to "Contact ***@example.com or call ***".

**Acceptance Scenarios**:

1. **Given** `GuardrailPolicy(redact_pii=True)`, **When** tool output contains an email address, **Then** the email is replaced with `***@domain.com` before being added to state
2. **Given** `GuardrailPolicy(redact_pii=True)`, **When** tool output contains a phone number pattern, **Then** the number is replaced with `***`
3. **Given** `GuardrailPolicy(redact_pii=False)`, **When** tool output contains PII, **Then** no redaction occurs
4. **Given** audit entry evidence contains `password=secret123`, **When** written to disk, **Then** the value is replaced with `***`

---

### User Story 5 - Prompt Injection Detection (Priority: P3)

As a security engineer, I need the middleware to detect and flag prompt injection patterns in tool outputs and retrieved content so that malicious instructions from external sources cannot hijack the agent's behavior.

**Why this priority**: Article X.3 requires prompt injection defense. This is P3 because it's a detection/alerting capability (writes audit entries and marks content as untrusted) rather than a hard block, and the heuristics are basic in v1.

**Independent Test**: Configure middleware, send a message containing "忽略以上指令" (ignore previous instructions) through the `wrap_model_call` hook. Verify that the middleware writes an audit entry with `category=prompt_injection, severity=warn` AND marks the content as untrusted (does NOT block execution).

**Acceptance Scenarios**:

1. **Given** a message contains the pattern "忽略以上指令", **When** processed by `wrap_model_call`, **Then** an audit entry with `category=prompt_injection, severity=warn` is written AND content is annotated as untrusted (execution continues)
2. **Given** tool output contains injection patterns, **When** processed by middleware, **Then** the content is marked with untrusted annotation AND audit entry is written (execution continues)
3. **Given** normal user input without injection patterns, **When** processed, **Then** no injection alerts are generated and no untrusted annotations are added

---

### Edge Cases

- What happens when the audit file directory doesn't exist? (Must auto-create `~/.local/share/langagent/`)
- What happens when disk is full during audit write? (Must raise `AuditFlushError` with exit code 4)
- What happens when `LANGAGENT_GUARDRAIL_MODE` has invalid value like "medium"? (Must log warning and default to "smart")
- What happens when internal endpoint patterns contain invalid CIDR notation? (Must log error and skip that pattern)
- What happens when a tool throws an exception during execution? (Middleware must not swallow it, let LangGraph handle)
- What happens when `RuntimeConfig.guardrail_policy` is `None`? (Must default to `GuardrailPolicy(enabled=True, mode="smart")`)
- What happens when querying audit entries with `since` timestamp in the future? (Returns empty list)
- What happens when audit.jsonl contains malformed JSON lines? (Query should skip invalid lines and log warning, not crash)
- What happens when current audit.jsonl reaches 10MB? (Must rotate to `audit-YYYYMMDD-HHMMSS.jsonl`, create new `audit.jsonl`, delete oldest file if more than 3 files exist)
- What happens when query spans multiple rotated files? (Must scan all files matching `audit*.jsonl` pattern, filter by filename timestamp based on `since` parameter for performance)
- What happens when prompt injection pattern is detected? (Must write `AuditEntry(category=prompt_injection, severity=warn)` AND annotate message content as untrusted; do NOT block execution in v1)

## Requirements *(mandatory)*

### Functional Requirements

#### Audit Recorder

- **FR-001**: System MUST write audit entries to `~/.local/share/langagent/audit.jsonl` in append-only mode
- **FR-002**: Each `AuditEntry` MUST contain 9 fields: `entry_id` (UUID4), `audited_at` (ISO 8601 timestamp), `severity` (Literal["debug", "info", "warn", "error"]), `category` (Literal["unauthorized_tool", "pii_detected", "prompt_injection"]), `actor` (system-level identifier string, e.g., "system:guardrail_middleware"), `action` (string), `target` (string), `outcome` (string), `evidence` (dict)
- **FR-003**: Audit recorder MUST redact sensitive patterns before writing to disk: `api_key`, `password`, `token`, email addresses (pattern: `\S+@\S+\.\S+`), phone numbers (pattern: `\+?\d[\d\s\-\(\)]{7,}\d`)
- **FR-004**: `write()` MUST raise `AuditFlushError` if disk write fails, with exit code 4
- **FR-005**: `query(category: str, since: datetime)` MUST return `list[AuditEntry]` filtered by exact category match and `audited_at >= since`
- **FR-006**: `flush()` MUST ensure all buffered entries are persisted to disk before returning
- **FR-007**: Audit recorder MUST subscribe to event bus `guardrail_block` events and automatically write audit entries
- **FR-008**: Audit file directory MUST be auto-created if it doesn't exist (with proper permissions)
- **FR-009**: When `audit.jsonl` reaches 10MB, system MUST rotate it to `audit-YYYYMMDD-HHMMSS.jsonl` (timestamp at rotation time), create new empty `audit.jsonl`, and delete oldest file if more than 3 total files exist
- **FR-010**: `query()` MUST scan current `audit.jsonl` AND all rotated files matching `audit-*.jsonl` pattern, filtering by filename timestamp to optimize performance (only scan files within `since` time range)

#### Guardrail Middleware

- **FR-011**: Middleware MUST implement LangChain `AgentMiddleware` protocol with three hooks: `before_tools`, `after_tools`, `wrap_model_call`
- **FR-012**: `build_middleware(policy: GuardrailPolicy)` MUST return an `AgentMiddleware` instance
- **FR-013**: `evaluate(tool_spec: ToolSpec, config: RuntimeConfig)` MUST return `GuardrailDecision` based on three-level mode rules:
  - `strict` mode: deny all tools (`allow=False, interrupt=True`)
  - `all` mode: all tools require approval (`allow=False, interrupt=True`)
  - `smart` mode with `requires_approval=True`: require approval (`allow=False, interrupt=True`)
  - `smart` mode with `requires_approval=False`: allow (`allow=True, interrupt=False`)
- **FR-014**: `is_internal(endpoint: str, patterns: list[str])` MUST return `True` if endpoint hostname matches any CIDR block or glob pattern
- **FR-015**: In `smart` mode with `allow_internal_endpoints=True`, if tool endpoint matches internal patterns, MUST allow without interrupt (set `is_internal_endpoint=True`)
- **FR-016**: In `smart` mode with `allow_internal_endpoints=True`, if tool endpoint is public, MUST interrupt with reason "public endpoint requires approval"
- **FR-017**: `before_tools` hook MUST call `evaluate()` for each tool call, and raise `InterruptException` if `decision.interrupt=True`
- **FR-018**: When guardrail blocks a tool in `strict` or `all` mode, MUST write `AuditEntry(category=unauthorized_tool, severity=warn)`
- **FR-019**: When guardrail blocks a tool in `smart` mode due to `requires_approval=True`, MUST write `AuditEntry(category=unauthorized_tool, severity=info)`
- **FR-020**: `after_tools` hook MUST redact PII from tool results if `policy.redact_pii=True`
- **FR-021**: `wrap_model_call` hook MUST detect prompt injection patterns (heuristic: "忽略以上指令", "ignore previous instructions") and when detected: write `AuditEntry(category=prompt_injection, severity=warn)` AND mark message content with untrusted annotation
- **FR-022**: Middleware MUST NOT swallow exceptions raised by tools or model calls, allowing LangGraph to handle them
- **FR-023**: When `policy.enabled=False`, middleware MUST allow all operations without evaluation

#### Schema & Types

- **FR-024**: `GuardrailMode` MUST be `Literal["all", "smart", "strict"]`
- **FR-025**: `GuardrailPolicy` MUST have fields: `enabled: bool`, `mode: GuardrailMode`, `redact_pii: bool`, `allow_internal_endpoints: bool`, `internal_endpoint_patterns: list[str]`
- **FR-026**: `GuardrailDecision` MUST have fields: `allow: bool`, `interrupt: bool`, `redact: bool`, `reason: str`, `is_internal_endpoint: bool | None`
- **FR-027**: All schemas MUST be Pydantic models with full type annotations passing `mypy --strict`

### Key Entities

- **AuditEntry**: Immutable record of a security event with timestamp, severity, category, actor, action, target, outcome, and evidence. Persisted as JSONL.
- **GuardrailPolicy**: Configuration object controlling guardrail behavior (mode, PII redaction, internal endpoints). Injected via `RuntimeConfig.guardrail_policy`.
- **GuardrailDecision**: Result of evaluating whether a tool call should be allowed, interrupted, or modified. Contains reasoning for audit trail.
- **GuardrailMiddleware**: LangChain `AgentMiddleware` implementation that hooks into LangGraph execution at three points (before tools, after tools, wrap model call).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: When a tool marked `requires_approval=True` is called in smart mode, the guardrail blocks execution and human approval is required within 1 second of detection
- **SC-002**: Audit entries are written to disk within 100ms of the security event occurring, ensuring near-real-time audit trail
- **SC-003**: 100% of sensitive patterns (api_key, password, token, emails, phone numbers) are redacted before being written to audit.jsonl, verified by scanning the file contents
- **SC-004**: Guardrail mode can be changed via environment variable and takes effect on next agent startup without code modification
- **SC-005**: Internal endpoint detection correctly classifies 100% of test cases (internal IPs, internal hostnames, public IPs) based on CIDR and glob patterns
- **SC-006**: Audit query performance returns results in under 50ms for files containing up to 10,000 entries
- **SC-007**: Zero audit entries are lost when agent exits normally (flush completes successfully)
- **SC-008**: When disk write fails, the agent terminates with exit code 4 and logs the error, preventing silent audit loss

## Assumptions

- F01 (primitives layer) already provides `AgentMiddleware` type re-exported from LangChain via `primitives_langchain_types`
- F02 (cross_cutting_logger) is available for emitting structured logs with tag `la.cross_cutting.audit.write`
- F03 (protocol_event_bus) is available for subscribing to `guardrail_block` events
- F07 (runtime config) will add `RuntimeConfig.guardrail_policy: GuardrailPolicy | None` field and populate it from environment variables `LANGAGENT_GUARDRAIL_MODE`, `LANGAGENT_GUARDRAIL_ALLOW_INTERNAL_ENDPOINTS`, `LANGAGENT_INTERNAL_ENDPOINTS`
- F05 (protocol_tool_registry) already defines `ToolSpec` schema with `requires_approval: bool` field
- LangGraph `interrupt()` mechanism is the standard way to trigger HITL approval (F08 will handle `GraphInterrupt` exceptions)
- Audit files are stored per-user (no multi-tenancy in v1), so `~/.local/share/langagent/` is the appropriate location
- PII detection uses heuristic regex patterns (email, phone) rather than NLP models; advanced detection is deferred to enterprise version
- Prompt injection detection uses simple pattern matching; ML-based detection is out of scope for v1
- CIDR notation parsing uses Python's `ipaddress` module; glob matching uses `fnmatch` module
- `AuditEntry.actor` field uses system-level identifiers (e.g., "system:guardrail_middleware", "system:audit_recorder") rather than user identifiers, as v1 focuses on system-level security events; user-level audit (tracking which human user triggered an action) is deferred to F13 (IdentitySpec) in future releases

---

## Constitutional Alignment Checklist

This specification aligns with the LangAgent Constitution (v1.1.0) as follows:

### Article I (Project Identity & Boundaries)
- ✅ F04 is internal infrastructure, not exposed as SDK
- ✅ No user-facing API; guardrails are configured via `.env` files in agent directory

### Article II (Tech Stack & Dependencies)
- ✅ Uses LangChain `AgentMiddleware` protocol (core dependency)
- ✅ No new third-party dependencies (uses stdlib: `ipaddress`, `fnmatch`, `uuid`, `datetime`, `json`)

### Article IV (Model Abstraction Layer)
- ✅ Internal endpoint detection supports local vLLM models (Article IV.4: "local models must be viable as defaults")
- ✅ Guardrail distinguishes internal vs external endpoints to allow local model usage

### Article VII (Middleware & Tool Rules)
- ✅ Implements LangChain middleware protocol
- ✅ Middleware injected at graph build time (F10 responsibility), not scattered in business nodes
- ✅ Cross-cutting concerns (audit, guardrails) handled via middleware hooks

### Article X (Security & Privacy)
- ✅ X.1: No external data transmission (all PII/injection detection is local heuristic)
- ✅ X.2: Tool permission minimization (three-level guardrail modes with `smart` as default)
- ✅ X.3: Prompt injection defense (detection via `wrap_model_call` hook)
- ✅ X.4: PII interfaces provided (redaction in audit + tool outputs)
- ✅ X.5: Secrets not logged (redaction of api_key/password/token patterns)

### Article XIII (Hard No Items)
- ✅ No LangSmith dependencies
- ✅ No hardcoded API keys or paths
- ✅ TDD approach mandated in design
- ✅ No external network calls for guardrail evaluation
- ✅ Structured logging (via F02), not print statements

### Article XV (Top-Level Design Primacy)
- ✅ Read `harness/top_level_design/workflow.md` for `guardrail_block` event flow
- ✅ Read `harness/top_level_design/architecture_modules.md` for module responsibilities and dependency direction
- ✅ Read `harness/top_level_design/module_schemas.md` for `AuditEntry`, `GuardrailPolicy`, `GuardrailDecision` schemas
- ✅ Cross_cutting layer depends only on: primitives (types), cross_cutting_logger (F02), protocol_event_bus (F03)
- ✅ Cross_cutting does NOT depend on: runtime, cli, protocol_skill_loader, protocol_tool_registry

### Deviations
None. This specification fully conforms to the constitution and top-level design artifacts.
