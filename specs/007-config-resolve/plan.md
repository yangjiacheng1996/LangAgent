# Implementation Plan: Configuration Resolution (config_resolve Stage)

**Branch**: `007-config-resolve` | **Date**: 2026-09-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-config-resolve/spec.md`

## Summary

Implement the config_resolve stage (stage 2 of 6) that merges configuration from 4 sources (CLI > env > .env > defaults) following strict priority chain rules, validates all required fields, detects placeholder values, and produces a frozen RuntimeConfig instance with 13 fields. The system enforces stage capability boundaries, parses .env files with python-dotenv, handles GuardrailPolicy resolution with lenient boolean parsing, filters empty items from CSV lists, requires model_name as mandatory, and emits sanitized startup logs showing only non-default value sources.

## Technical Context

**Language/Version**: Python 3.11+ (per Constitution Article II Section 5, aligned with pyproject.toml requires-python)

**Primary Dependencies**: 
- Pydantic v2.x (frozen dataclass with validation for RuntimeConfig)
- python-dotenv (standard .env file parsing)
- LangChain types (BaseChatModel, re-exported via primitives layer per Constitution Article IV Section 1)

**Storage**: N/A (configuration resolution is in-memory only; no persistence at this stage)

**Testing**: pytest with strict TDD (Red-Green-Refactor per Constitution Article VIII)
- Unit tests: ≥20 test cases covering priority chain, validation, parsing, freezing
- Integration tests: End-to-end config resolution with all 4 sources
- Fixtures: Test .env files, mock cli_args dicts, environment variable snapshots

**Target Platform**: Linux server (primary), cross-platform compatible (Constitution Article I Section 3 - local product)

**Project Type**: CLI tool component (runtime layer module within LangAgent binary)

**Performance Goals**: 
- Config resolution must complete in <100ms (negligible startup overhead)
- Memory footprint <10MB for typical configuration (13 fields + metadata)
- Zero network I/O (all configuration sources are local per Constitution Article XII Section 1)

**Constraints**: 
- MUST NOT instantiate BaseChatModel (stage boundary violation per workflow.md)
- MUST NOT load agent directory (dir_load is stage 1, config_resolve is stage 2)
- MUST NOT read LangSmith environment variables (Constitution Article III Section 2)
- MUST use stage_guard decorator from F06 cross_cutting/stage_guard.py
- MUST emit logs via F02 cross_cutting_logger (no direct logging)

**Scale/Scope**: 
- 13 RuntimeConfig fields (4 source metadata + 4 model + 3 runtime + 1 misc + 1 guardrail)
- 6 model providers (openai, anthropic, google, deepseek, zhipu, openai-compatible)
- 4 configuration sources (CLI, env, .env, defaults)
- 5 exit codes (0=success, 1=stage violation, 5=missing required, 65=malformed .env, 78=validation error)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Article I (Project Identity)
✅ **PASS**: F07 is a runtime layer component, not a separate SDK or framework. No public API exposure outside LangAgent binary.

### Article II (Technical Stack)
✅ **PASS**: Uses Pydantic (standard Python validation), python-dotenv (standard .env parsing). No new LangChain/LangGraph dependencies added. LangChain types accessed via primitives layer only.

### Article III (LangSmith Isolation)
✅ **PASS**: F07 explicitly excludes LANGSMITH_* environment variables from priority chain (spec FR-1 assumptions). No LangSmith imports or API calls.

### Article IV (Model Abstraction)
✅ **PASS**: F07 sets RuntimeConfig.model to None; model instantiation delegated to F01 model_adapt stage. Default model_provider="openai-compatible" per Constitution Article IV Section 4.

### Article VIII (TDD)
✅ **PASS**: Spec defines ≥20 test cases covering all priority chain scenarios, validation rules, .env parsing, freezing constraints. Red-Green-Refactor mandatory per spec section §四 Implementation Notes.

### Article XII (Configuration Contract)
✅ **PASS**: F07 directly implements Article XII Section 1 (4-source priority chain) and Section 2 (startup logging with sanitization). Priority chain merging logged explicitly per spec FR-1.

### Article XIII (Hard No)
✅ **PASS**: No API keys hardcoded, no external network calls, no LangSmith dependencies, no direct provider SDK calls, no print statements (uses structured logger).

### Article XV (Top-Level Design Primacy)
✅ **PASS**: Spec explicitly references workflow.md#stage-config_resolve, architecture_modules.md#mod-runtime-config-resolver, module_schemas.md#schema-runtime-config. All design decisions traced to top-level artifacts.

**Result**: All gates pass. No complexity tracking violations. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/007-config-resolve/
├── spec.md              # Feature specification with clarifications
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
langagent/
├── runtime/
│   ├── config_resolver.py          # RuntimeConfigResolver class (NEW - F07)
│   ├── defaults.py                 # Builtin default values (NEW - F07)
│   ├── exceptions.py               # Config-specific exceptions (EXTEND - F07)
│   └── agent_state.py              # RuntimeConfig schema (EXTEND - F07 adds with_* methods)
├── cross_cutting/
│   ├── logger.py                   # cross_cutting_logger.emit() (EXISTS - F02)
│   └── stage_guard.py              # @cross_cutting_stage_guard_decorator (EXISTS - F06)
└── primitives/
    └── langchain_types.py          # BaseChatModel re-export (EXISTS - F01)

tests/
├── runtime/
│   └── test_config_resolver.py     # ≥20 unit tests covering all validation, parsing, and merging (NEW - F07)
└── fixtures/
    ├── .env.test                   # Test .env files (NEW - F07)
    ├── .env.malformed              # Malformed .env test (NEW - F07)
    └── .env.placeholders           # Placeholder detection test (NEW - F07)
```

**Structure Decision**: F07 creates new modules in `langagent/runtime/` (config_resolver.py, defaults.py) and extends existing RuntimeConfig schema in agent_state.py with with_model(), with_model_base_url(), with_guardrail_policy() methods. Test fixtures in tests/fixtures/ follow existing project convention. No new top-level directories required.

## Complexity Tracking

> **No violations detected. This section intentionally left empty per gate check results.**

---

## Phase 0: Research & Unknowns Resolution

### Research Tasks

#### R1: Pydantic Frozen Dataclass Best Practices
**Question**: How to implement immutable Pydantic models with frozen=True while providing with_* methods for controlled field updates?

**Decision**: Use Pydantic BaseModel with `model_config = ConfigDict(frozen=True)` and implement with_* methods using `model_copy(update={...})` to create new instances.

**Rationale**: 
- Pydantic v2 ConfigDict provides frozen constraint enforcement
- model_copy() is the recommended way to create modified frozen instances
- Preserves all 13 fields while updating specific fields
- Type-safe and validates updated values

**Alternatives Considered**:
- dataclasses.dataclass(frozen=True): Rejected - less validation than Pydantic
- Manual __setattr__ override: Rejected - Pydantic handles this automatically
- Copy constructor pattern: Rejected - model_copy() is more idiomatic

**References**:
- Pydantic v2 docs: Frozen models and validation
- module_schemas.md#schema-runtime-config: frozen=True requirement

---

#### R2: python-dotenv Duplicate Key Handling
**Question**: How does python-dotenv handle duplicate keys in .env files? Does it match spec clarification (last value wins)?

**Decision**: python-dotenv default behavior is last-value-wins, which matches spec clarification Session 2026-09-20 Q4.

**Rationale**:
- python-dotenv load_dotenv() uses dict update semantics
- Later definitions overwrite earlier ones in same file
- No configuration needed - library default matches requirement

**Alternatives Considered**:
- Custom parser: Rejected - python-dotenv handles this correctly
- First-value-wins: Rejected - conflicts with library default and user expectation
- Error on duplicate: Rejected - too strict for real-world .env files

**References**:
- python-dotenv documentation: dotenv_values() behavior
- Spec FR-6 updated with duplicate key handling rule

---

#### R3: Boolean Parsing Strategies for Environment Variables
**Question**: What's the industry-standard approach for lenient boolean parsing in environment variables?

**Decision**: Implement case-insensitive parsing accepting ["true", "1", "yes", "on"] as True and ["false", "0", "no", "off"] as False, raise ValidationError for other values.

**Rationale**:
- Matches common conventions across platforms (systemd, docker-compose, shell scripts)
- User-friendly for developers familiar with multiple ecosystems
- Clear error messages for invalid values prevent silent failures

**Alternatives Considered**:
- Python bool("string"): Rejected - all non-empty strings are True (misleading)
- Strict "true"/"false" only: Rejected - too inflexible per clarification Session 2026-09-20 Q1
- Accept any value: Rejected - creates ambiguity and silent bugs

**Implementation**:
```python
def parse_bool(value: str) -> bool:
    """Parse boolean from environment variable with lenient matching."""
    normalized = value.strip().lower()
    if normalized in ("true", "1", "yes", "on"):
        return True
    if normalized in ("false", "0", "no", "off"):
        return False
    raise ValidationError(f"Invalid boolean value: {value}")
```

---

#### R4: CSV List Parsing with Empty Item Filtering
**Question**: How to robustly parse comma-separated lists while filtering empty items as specified in clarification Session 2026-09-20 Q2?

**Decision**: Split on comma, strip whitespace from each item, filter empty strings and whitespace-only items using list comprehension with str.strip() and bool check.

**Rationale**:
- Handles accidental double commas ("foo,,bar")
- Handles trailing/leading whitespace ("foo, , bar")
- Simple implementation with clear semantics
- Zero-cost abstraction - no regex needed

**Implementation**:
```python
def parse_csv_list(value: str) -> list[str]:
    """Parse comma-separated list, filtering empty items."""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]
```

**Alternatives Considered**:
- Regex-based splitting: Rejected - overkill for simple comma separation
- Keep empty items: Rejected - spec clarification explicitly requires filtering
- Error on empty items: Rejected - too strict, user-unfriendly

---

#### R5: Stage Guard Integration Pattern
**Question**: How to integrate F06 stage_guard decorator with config_resolve stage while maintaining clean separation?

**Decision**: Import @cross_cutting_stage_guard_decorator from langagent.cross_cutting.stage_guard and apply to RuntimeConfigResolver.resolve() with monkeypatch_blacklist=[BaseChatModel.__init__, RuntimeDirLoader.load, chat_model_factory.create].

**Rationale**:
- F06 provides stage_guard as cross-feature reusable utility per spec §3.5
- Decorator pattern keeps stage boundary enforcement orthogonal to business logic
- Monkeypatch blacklist matches spec FR-7 exactly

**Alternatives Considered**:
- Manual boundary checks: Rejected - duplicates F06 logic, breaks DRY
- Runtime reflection: Rejected - stage_guard already uses monkeypatch + audit hooks
- Skip boundary enforcement: Rejected - violates workflow.md stage separation

**References**:
- F06 spec §3.4: stage_guard implementation at cross_cutting/stage_guard.py
- Spec FR-7: Stage Capability Boundary Enforcement

---

#### R6: model_name Required Field Enforcement
**Question**: How to enforce model_name as required field while maintaining backwards compatibility with existing defaults.py?

**Decision**: Remove model_name from defaults.py (set to None), add validation in resolve() that raises RequiredFieldMissingError if model_name is None after priority chain merging.

**Rationale**:
- Spec clarification Session 2026-09-20 Q3: "要求必填，强制用户配置 model_name"
- Explicit > implicit - users must consciously choose their model
- Prevents accidental runs with wrong/missing model

**Implementation**:
```python
# In resolve()
if config.model_name is None:
    raise RequiredFieldMissingError(
        field="model_name",
        message="model_name is required - cannot run agent without specifying a model"
    )
```

**Alternatives Considered**:
- Provider-specific defaults: Rejected - creates hidden coupling between provider and model
- Allow None: Rejected - spec clarification explicitly requires this field
- Use empty string as sentinel: Rejected - None is more idiomatic for "not set"

---

#### R7: Startup Logging Source Annotation Strategy
**Question**: How to implement "only log non-default value sources" as specified in clarification Session 2026-09-20 Q5?

**Decision**: Track which fields were overridden during priority chain merging, include source annotation (CLI/env/.env) only for overridden fields in startup log, omit annotation for fields using builtin defaults.

**Rationale**:
- Reduces log noise - defaults are expected, overrides are notable
- Highlights actual user configuration decisions
- Maintains full information in RuntimeConfig metadata fields for debugging

**Implementation**:
```python
# Track overrides during merge
overrides = {}  # field_name -> source_name mapping
for field in ["model_provider", "model_name", ...]:
    if cli_args.get(field) is not None:
        overrides[field] = "CLI"
    elif env_vars.get(field.upper()) is not None:
        overrides[field] = "env"
    elif dotenv_values.get(field.upper()) is not None:
        overrides[field] = ".env"
    # else: using default, no annotation

# In startup log
log_data = {
    "model_provider": config.model_provider,
    "model_provider_source": overrides.get("model_provider"),  # None if default
    ...
}
```

**Alternatives Considered**:
- Log all sources: Rejected - too verbose per clarification
- Log only critical fields: Rejected - spec FR-10 lists specific fields to log
- Skip source annotation entirely: Rejected - loses valuable debugging info

---

### Research Summary

All technical unknowns resolved. Key decisions:
1. Pydantic frozen models with model_copy() for with_* methods
2. python-dotenv default behavior (last-value-wins) matches spec
3. Lenient boolean parsing with 4 true values + 4 false values
4. CSV parsing with strip() + filter() for empty item removal
5. stage_guard decorator integration via F06 cross_cutting module
6. model_name required field with explicit validation
7. Source annotation only for non-default values in startup log

No blocking issues. Ready for Phase 1 design.

---

## Phase 1: Design & Contracts

See generated artifacts:
- [data-model.md](./data-model.md) - RuntimeConfig 13 fields, GuardrailPolicy, validation rules
- [contracts/](./contracts/) - RuntimeConfigResolver public API contract
- [quickstart.md](./quickstart.md) - Validation scenarios and test commands

---

## Implementation Phases (from /speckit.tasks)

**Note**: Task decomposition is handled by `/speckit.tasks` command, not by this plan. The tasks.md file will break down implementation into:
- Phase 2.1: Core priority chain merging
- Phase 2.2: Validation and placeholder detection
- Phase 2.3: .env parsing with python-dotenv
- Phase 2.4: Frozen RuntimeConfig with with_* methods
- Phase 2.5: GuardrailPolicy resolution
- Phase 2.6: Startup logging with sanitization
- Phase 2.7: Integration with stage_guard

---

## Success Criteria (from spec)

1. **SC-1: Configuration Priority Chain Correctness** - 100% of test cases with overlapping configuration sources produce correct merged values
2. **SC-2: Validation Error Detection Rate** - 100% of invalid configurations detected with correct exit codes
3. **SC-3: Immutability Enforcement** - 100% of attempts to modify frozen RuntimeConfig raise ValidationError
4. **SC-4: Stage Capability Isolation** - 100% of blacklisted operations blocked during config_resolve stage
5. **SC-5: Startup Logging Completeness** - 100% of successful resolutions emit startup logs with required fields, no sensitive data

---

## Dependencies

### Upstream (Must Complete Before F07)
- F06: Provides cross_cutting/stage_guard.py with @cross_cutting_stage_guard_decorator
- F02: Provides cross_cutting_logger.emit() for la.runtime.config_resolve.ok/.fail logs

### Downstream (Depends on F07)
- F01: Consumes RuntimeConfig.model_provider/model_name/model_base_url for model instantiation
- F10: Calls resolve() with cli_args dict and agent_dir path
- F04: Reads RuntimeConfig.guardrail_policy for evaluation

### External Libraries
- Pydantic ≥2.0: Frozen dataclass validation
- python-dotenv: Standard .env file parsing

---

## Risk Mitigation

### Risk 1: Stage Guard Decorator Not Available
**Likelihood**: Low (F06 is upstream dependency, must complete first)
**Impact**: High (cannot enforce stage boundaries without it)
**Mitigation**: Block F07 implementation until F06 §七 deliverable (stage_guard.py) is complete and tested

### Risk 2: python-dotenv Behavior Mismatch
**Likelihood**: Low (well-established library with stable behavior)
**Impact**: Medium (incorrect .env parsing could break priority chain)
**Mitigation**: Comprehensive test coverage for .env parsing (spec test cases 4.2.1-4.2.5), validate against python-dotenv documentation

### Risk 3: Pydantic Frozen Model Performance
**Likelihood**: Low (Pydantic is production-grade)
**Impact**: Low (config resolution is one-time operation at startup)
**Mitigation**: Benchmark config resolution time <100ms, profile with typical 13-field config

### Risk 4: model_name Required Field Breaking Existing Agents
**Likelihood**: Medium (clarification changed from optional to required)
**Impact**: Medium (existing agents without model_name will fail)
**Mitigation**: Clear error message with guidance, update F06 init templates to include model_name in .env.example

---

## Open Questions

None. All clarifications resolved in spec Session 2026-09-20.

---

## Next Steps

1. Run `/speckit.tasks` to generate tasks.md with detailed implementation breakdown
2. Implement Phase 2.1-2.7 following TDD (Red-Green-Refactor)
3. Run mypy --strict for type safety validation
4. Execute ≥20 test cases from spec §四
5. Integration test with F06 stage_guard and F02 logger
6. Update F06 init templates to include model_name in .env.example

**Ready for task generation.** All gates pass, all research complete, all design artifacts generated.
