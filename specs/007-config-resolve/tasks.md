# Tasks: Configuration Resolution (config_resolve Stage)

**Input**: Design documents from `/specs/007-config-resolve/`

**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: Following Constitution Article VIII (TDD mandatory), all test tasks MUST be written and FAIL before implementation tasks.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

All paths relative to repository root:
- Implementation: `langagent/runtime/`
- Tests: `tests/runtime/`
- Fixtures: `tests/fixtures/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure for F07 config_resolve module

- [ ] T001 Create langagent/runtime/exceptions.py with config-specific exception classes (RequiredFieldMissingError, ConfigPlaceholderError, DotenvMalformedError, TypeMismatchError)
- [ ] T002 [P] Create langagent/runtime/defaults.py stub with empty BUILTIN_DEFAULTS dict
- [ ] T003 [P] Create tests/fixtures/ directory for test .env files
- [ ] T004 [P] Extend langagent/runtime/agent_state.py to import Pydantic BaseModel and ConfigDict for RuntimeConfig schema preparation

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 Define RuntimeConfig Pydantic schema with 13 fields and frozen=True in langagent/runtime/agent_state.py
- [ ] T006 [P] Implement with_model() method in RuntimeConfig class that returns new frozen instance with model field populated
- [ ] T007 [P] Implement with_model_base_url() method in RuntimeConfig class that returns new frozen instance with model_base_url updated
- [ ] T008 [P] Implement with_guardrail_policy() method in RuntimeConfig class that returns new frozen instance with guardrail_policy updated
- [ ] T009 Define GuardrailPolicy Pydantic schema with 5 fields (enabled, mode, redact_pii, allow_internal_endpoints, internal_endpoint_patterns) in langagent/runtime/agent_state.py
- [ ] T010 Create RuntimeConfigResolver class skeleton in langagent/runtime/config_resolver.py with resolve() method signature
- [ ] T011 Populate BUILTIN_DEFAULTS dict in langagent/runtime/defaults.py with 7 default values (model_provider="openai-compatible", checkpointer="memory", middleware_ids=[], skill_dirs=[], log_level="INFO", GuardrailPolicy defaults, model_name=None)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Merge Configuration from Multiple Sources (Priority: P1) 🎯 MVP

**Goal**: Implement 4-source priority chain (CLI > env > .env > defaults) that correctly merges configuration and produces frozen RuntimeConfig

**Independent Test**: Create fixtures with conflicting values across all 4 sources, call resolve(), verify highest-priority value wins for each field

### Tests for User Story 1 (TDD - Write First, Must FAIL)

- [ ] T012 [P] [US1] Write test_resolve_cli_overrides_all in tests/runtime/test_config_resolver.py (CLI="gpt-4o" > env="claude-3" > .env="qwen3-8b" → result="gpt-4o") - MUST FAIL initially
- [ ] T013 [P] [US1] Write test_resolve_env_overrides_dotenv in tests/runtime/test_config_resolver.py (CLI absent, env="gpt-4o" > .env="qwen3-8b" → result="gpt-4o") - MUST FAIL initially
- [ ] T014 [P] [US1] Write test_resolve_dotenv_overrides_builtin in tests/runtime/test_config_resolver.py (CLI/env absent, .env="qwen3-8b" > default="openai-compatible" → result="qwen3-8b") - MUST FAIL initially
- [ ] T015 [P] [US1] Write test_resolve_builtin_when_no_source in tests/runtime/test_config_resolver.py (all sources absent → use builtin default) - MUST FAIL initially
- [ ] T016 [P] [US1] Write test_resolve_priority_logged in tests/runtime/test_config_resolver.py (verify cross_cutting_logger.emit called with la.runtime.config_resolve.ok tag and priority merge details) - MUST FAIL initially

### Implementation for User Story 1

- [ ] T017 [US1] Implement parse_dotenv(env_path: str) -> dict[str, str] function in langagent/runtime/config_resolver.py using python-dotenv's dotenv_values(), handle missing file → empty dict
- [ ] T018 [US1] Implement merge_priority_chain(cli_args, env_vars, dotenv_values, builtin_defaults) -> dict[str, Any] function in langagent/runtime/config_resolver.py that applies CLI > env > .env > defaults priority for each field
- [ ] T019 [US1] Implement RuntimeConfigResolver.resolve(cli_args: dict[str, Any], agent_dir: str) -> RuntimeConfig method that: 1) snapshots os.environ, 2) calls parse_dotenv(), 3) calls merge_priority_chain(), 4) constructs RuntimeConfig from merged dict
- [ ] T020 [US1] Add logging to resolve() method: call cross_cutting_logger.emit() with tag="la.runtime.config_resolve.ok" after successful resolution, include priority merge details (non-default value sources only per clarification Q5)
- [ ] T021 [US1] Verify all T012-T016 tests now PASS after implementation

**Checkpoint**: At this point, User Story 1 (priority chain merging) should be fully functional and testable independently

---

## Phase 4: User Story 2 - Validate Required Fields and Reject Placeholders (Priority: P1)

**Goal**: Detect missing required fields and placeholder values, raise appropriate errors with correct exit codes

**Independent Test**: Create fixtures with missing model_base_url and placeholder values, attempt resolve(), verify RequiredFieldMissingError (exit 5) and ConfigPlaceholderError (exit 78)

### Tests for User Story 2 (TDD - Write First, Must FAIL)

- [ ] T022 [P] [US2] Write test_resolve_required_field_missing in tests/runtime/test_config_resolver.py (model_provider absent from all 4 sources → RequiredFieldMissingError exit 5) - MUST FAIL initially
- [ ] T023 [P] [US2] Write test_resolve_required_field_missing_openai_compatible_base_url in tests/runtime/test_config_resolver.py (model_provider="openai-compatible" but model_base_url=None → RequiredFieldMissingError exit 5) - MUST FAIL initially
- [ ] T023b [P] [US2] Write test_resolve_deepseek_base_url_mapping in tests/runtime/test_config_resolver.py (model_provider="deepseek" reads DEEPSEEK_BASE_URL not MODEL_BASE_URL) - MUST FAIL initially
- [ ] T023c [P] [US2] Write test_resolve_zhipu_base_url_mapping in tests/runtime/test_config_resolver.py (model_provider="zhipu" reads ZHIPUAI_BASE_URL not MODEL_BASE_URL) - MUST FAIL initially
- [ ] T024 [P] [US2] Write test_resolve_required_field_missing_model_name in tests/runtime/test_config_resolver.py (model_name=None after merge → RequiredFieldMissingError exit 5 per clarification Q3) - MUST FAIL initially
- [ ] T025 [P] [US2] Write test_resolve_rejects_placeholder_values in tests/runtime/test_config_resolver.py (.env contains MODEL_NAME=<your-model-name> → ConfigPlaceholderError exit 78) - MUST FAIL initially
- [ ] T026 [P] [US2] Write test_resolve_rejects_placeholder_values_all_fields in tests/runtime/test_config_resolver.py (.env contains MODEL_BASE_URL=<your-vllm-endpoint> → ConfigPlaceholderError exit 78) - MUST FAIL initially
- [ ] T027 [P] [US2] Write test_resolve_type_mismatch in tests/runtime/test_config_resolver.py (CLI provides model_provider=123 (int not str) → TypeMismatchError exit 78) - MUST FAIL initially
- [ ] T028 [P] [US2] Write test_resolve_invalid_enum_value in tests/runtime/test_config_resolver.py (model_provider="unknown" → ValidationError exit 78) - MUST FAIL initially

### Implementation for User Story 2

- [ ] T029 [P] [US2] Implement validate_required_fields(merged_config: dict) function in langagent/runtime/config_resolver.py that checks model_provider, model_name, model_base_url (provider-specific), checkpointer, log_level are present and non-None
- [ ] T030 [P] [US2] Implement validate_no_placeholders(merged_config: dict) function in langagent/runtime/config_resolver.py that scans all string values for regex pattern ^<your-.+>$, raise ConfigPlaceholderError if match
- [ ] T031 [US2] Integrate validate_required_fields() call into resolve() method after merge_priority_chain(), raise RequiredFieldMissingError with field name and exit code 5 if validation fails
- [ ] T032 [US2] Integrate validate_no_placeholders() call into resolve() method after validate_required_fields(), raise ConfigPlaceholderError with field name and exit code 78 if validation fails
- [ ] T033 [US2] Add error logging: call cross_cutting_logger.emit() with tag="la.runtime.config_resolve.fail" when any validation error occurs, include error details (sanitized - no secrets)
- [ ] T034 [US2] Verify all T022-T028 tests now PASS after implementation

**Checkpoint**: At this point, User Stories 1 AND 2 (priority chain + validation) should both work independently

---

## Phase 5: User Story 3 - Parse and Validate .env Files (Priority: P1)

**Goal**: Robust .env file parsing with python-dotenv, handle quotes/comments/malformed files correctly

**Independent Test**: Create test .env fixtures with various formats, call parse_dotenv(), verify correct parsing or DotenvMalformedError

### Tests for User Story 3 (TDD - Write First, Must FAIL)

- [ ] T035 [P] [US3] Write test_parse_dotenv_basic in tests/runtime/test_config_resolver.py (KEY=VALUE → {"KEY": "VALUE"}) - MUST FAIL initially
- [ ] T036 [P] [US3] Write test_parse_dotenv_with_quotes in tests/runtime/test_config_resolver.py (KEY="VALUE" → {"KEY": "VALUE"} quotes removed) - MUST FAIL initially
- [ ] T037 [P] [US3] Write test_parse_dotenv_with_comments in tests/runtime/test_config_resolver.py (# comment\nKEY=value → {"KEY": "value"} comment ignored) - MUST FAIL initially
- [ ] T038 [P] [US3] Write test_parse_dotenv_missing_file in tests/runtime/test_config_resolver.py (.env not exist → empty dict, no error) - MUST FAIL initially
- [ ] T039 [P] [US3] Write test_parse_dotenv_malformed in tests/runtime/test_config_resolver.py (KEY== malformed → DotenvMalformedError exit 65) - MUST FAIL initially
- [ ] T040 [P] [US3] Write test_parse_dotenv_duplicate_keys in tests/runtime/test_config_resolver.py (KEY=first\nKEY=second → {"KEY": "second"} last value wins per clarification Q4) - MUST FAIL initially

### Implementation for User Story 3

- [ ] T041 [P] [US3] Create tests/fixtures/.env.test with KEY=VALUE test data for T035
- [ ] T042 [P] [US3] Create tests/fixtures/.env.quoted with KEY="VALUE" test data for T036
- [ ] T043 [P] [US3] Create tests/fixtures/.env.comments with # comment\nKEY=value test data for T037
- [ ] T044 [P] [US3] Create tests/fixtures/.env.malformed with KEY== test data for T039
- [ ] T045 [P] [US3] Create tests/fixtures/.env.duplicates with KEY=first\nKEY=second test data for T040
- [ ] T046 [US3] Enhance parse_dotenv() function to use python-dotenv's dotenv_values(), wrap in try-except to catch parsing errors and raise DotenvMalformedError with exit code 65
- [ ] T047 [US3] Add validation in parse_dotenv() to detect malformed syntax (lines with == or other invalid patterns) before python-dotenv processing
- [ ] T048 [US3] Verify all T035-T040 tests now PASS after implementation

**Checkpoint**: At this point, User Stories 1, 2, AND 3 (.env parsing) should all work independently

---

## Phase 6: User Story 4 - Produce Frozen RuntimeConfig with Metadata (Priority: P2)

**Goal**: RuntimeConfig with frozen=True enforced, with_* methods creating new instances, all 13 fields + 4 source metadata populated

**Independent Test**: Create RuntimeConfig, attempt direct modification (should raise ValidationError), verify with_model() returns new instance

### Tests for User Story 4 (TDD - Write First, Must FAIL)

- [ ] T049 [P] [US4] Write test_resolve_returns_frozen_runtime_config in tests/runtime/test_config_resolver.py (config.model_provider = "anthropic" → ValidationError) - MUST FAIL initially
- [ ] T050 [P] [US4] Write test_resolve_creates_new_instance_on_modify_attempt in tests/runtime/test_config_resolver.py (config.__setattr__ → raises error) - MUST FAIL initially
- [ ] T051 [P] [US4] Write test_resolve_model_field_is_none_by_default in tests/runtime/test_config_resolver.py (config.model is None after resolve) - MUST FAIL initially
- [ ] T052 [P] [US4] Write test_resolve_with_model_returns_new_instance_with_model in tests/runtime/test_config_resolver.py (config2 = config.with_model(fake_model); config.model is None; config2.model is fake_model; config is not config2) - MUST FAIL initially
- [ ] T053 [P] [US4] Write test_resolve_with_model_preserves_other_fields in tests/runtime/test_config_resolver.py (with_model() does not modify other 12 fields) - MUST FAIL initially
- [ ] T054 [P] [US4] Write test_resolve_with_model_base_url in tests/runtime/test_config_resolver.py (with_model_base_url() returns new instance with updated base_url) - MUST FAIL initially
- [ ] T055 [P] [US4] Write test_resolve_cli_args_preserved_unmodified in tests/runtime/test_config_resolver.py (config.cli_args == input cli_args dict, not mutated) - MUST FAIL initially

### Implementation for User Story 4

- [ ] T056 [US4] Add model_config = ConfigDict(frozen=True) to RuntimeConfig class in langagent/runtime/agent_state.py to enforce immutability
- [ ] T057 [US4] Implement with_model() using self.model_copy(update={"model": model}) in RuntimeConfig class
- [ ] T058 [US4] Implement with_model_base_url() using self.model_copy(update={"model_base_url": base_url}) in RuntimeConfig class
- [ ] T059 [US4] Implement with_guardrail_policy() using self.model_copy(update={"guardrail_policy": policy}) in RuntimeConfig class
- [ ] T060 [US4] Update resolve() to populate all 4 source metadata fields (cli_args, env_vars, dotenv_values, builtin_defaults) in RuntimeConfig constructor
- [ ] T061 [US4] Update resolve() to ensure cli_args dict is copied (not mutated) before storing in RuntimeConfig
- [ ] T062 [US4] Verify all T049-T055 tests now PASS after implementation

**Checkpoint**: At this point, User Stories 1-4 (frozen config with metadata) should all work independently

---

## Phase 7: User Story 5 - Enforce Stage Capability Boundaries (Priority: P2)

**Goal**: Apply stage_guard decorator to resolve(), block blacklisted operations (BaseChatModel.__init__, RuntimeDirLoader.load, chat_model_factory.create)

**Independent Test**: Wrap test function with stage_guard, attempt blacklisted operations, verify StageCapabilityViolationError with exit code 1

### Tests for User Story 5 (TDD - Write First, Must FAIL)

- [ ] T063 [P] [US5] Write test_resolve_does_not_instantiate_model in tests/runtime/test_config_resolver.py (monkeypatch BaseChatModel.__init__ → StageCapabilityViolationError exit 1) - MUST FAIL initially
- [ ] T064 [P] [US5] Write test_resolve_does_not_load_agent_dir in tests/runtime/test_config_resolver.py (monkeypatch RuntimeDirLoader.load → StageCapabilityViolationError exit 1) - MUST FAIL initially
- [ ] T065 [P] [US5] Write test_resolve_uses_stage_guard_decorator in tests/runtime/test_config_resolver.py (verify @cross_cutting_stage_guard_decorator applied to resolve() via static inspection) - MUST FAIL initially

### Implementation for User Story 5

- [ ] T066 [US5] Import @cross_cutting_stage_guard_decorator from langagent.cross_cutting.stage_guard in langagent/runtime/config_resolver.py
- [ ] T067 [US5] Apply @cross_cutting_stage_guard_decorator('config_resolve', monkeypatch_blacklist=[BaseChatModel.__init__, RuntimeDirLoader.load, chat_model_factory.create]) to RuntimeConfigResolver.resolve() method
- [ ] T068 [US5] Import BaseChatModel from langagent.primitives.langchain_types for blacklist reference (type-only import)
- [ ] T069 [US5] Import RuntimeDirLoader from langagent.runtime.dir_loader for blacklist type reference only (implementation will be provided by F06; F07 only needs the class reference for monkeypatch blacklist)
- [ ] T070 [US5] Verify all T063-T065 tests now PASS after implementation

**Checkpoint**: At this point, User Stories 1-5 (stage boundary enforcement) should all work independently

---

## Phase 8: User Story 6 - Parse List-Based Configuration Fields (Priority: P3)

**Goal**: Parse comma-separated env vars (LANGAGENT_MIDDLEWARE, LANGAGENT_SKILL_DIRS) into lists, filter empty items per clarification Q2

**Independent Test**: Set env LANGAGENT_MIDDLEWARE=foo,bar,baz, call resolve(), verify RuntimeConfig.middleware_ids == ["foo", "bar", "baz"]

### Tests for User Story 6 (TDD - Write First, Must FAIL)

- [ ] T071 [P] [US6] Write test_resolve_middleware_ids_from_csv in tests/runtime/test_config_resolver.py (env LANGAGENT_MIDDLEWARE=foo,bar,baz → middleware_ids==["foo","bar","baz"]) - MUST FAIL initially
- [ ] T072 [P] [US6] Write test_resolve_skill_dirs_from_csv in tests/runtime/test_config_resolver.py (env LANGAGENT_SKILL_DIRS=/path/one,/path/two → skill_dirs==["/path/one","/path/two"]) - MUST FAIL initially
- [ ] T073 [P] [US6] Write test_resolve_middleware_ids_default_empty in tests/runtime/test_config_resolver.py (no config source provides middleware_ids → middleware_ids==[]) - MUST FAIL initially
- [ ] T074 [P] [US6] Write test_resolve_csv_filters_empty_items in tests/runtime/test_config_resolver.py (env="foo,,bar" or "foo, ,bar" → ["foo","bar"] empty items filtered per clarification Q2) - MUST FAIL initially

### Implementation for User Story 6

- [ ] T075 [P] [US6] Implement parse_csv_list(value: str) -> list[str] function in langagent/runtime/config_resolver.py that splits on comma, strips whitespace, filters empty strings
- [ ] T076 [US6] Update merge_priority_chain() to call parse_csv_list() for LANGAGENT_MIDDLEWARE and LANGAGENT_SKILL_DIRS fields when processing environment variables
- [ ] T077 [US6] Add empty list defaults for middleware_ids and skill_dirs in BUILTIN_DEFAULTS dict in langagent/runtime/defaults.py (already done in T011, verify correct)
- [ ] T078 [US6] Verify all T071-T074 tests now PASS after implementation

**Checkpoint**: At this point, User Stories 1-6 (CSV list parsing) should all work independently

---

## Phase 9: User Story 7 - Emit Startup Logging (Priority: P3)

**Goal**: Emit startup logs with LangAgent version, agent_dir, model config, checkpointer, middleware; sanitize API keys; annotate only non-default value sources per clarification Q5

**Independent Test**: Call resolve() successfully, verify cross_cutting_logger.emit() called with la.runtime.config_resolve.ok tag, required fields present, no API keys logged

### Tests for User Story 7 (TDD - Write First, Must FAIL)

- [ ] T079 [P] [US7] Write test_resolve_emits_startup_log in tests/runtime/test_config_resolver.py (verify cross_cutting_logger.emit called with la.runtime.config_resolve.ok tag) - MUST FAIL initially
- [ ] T080 [P] [US7] Write test_resolve_does_not_log_api_key in tests/runtime/test_config_resolver.py (env OPENAI_API_KEY=sk-secret → log does not contain "sk-secret") - MUST FAIL initially
- [ ] T081 [P] [US7] Write test_resolve_does_not_log_full_dotenv in tests/runtime/test_config_resolver.py (.env has 10 keys → log only contains tracked config fields, not all 10 keys) - MUST FAIL initially
- [ ] T082 [P] [US7] Write test_resolve_startup_log_source_annotations in tests/runtime/test_config_resolver.py (verify source annotations only for non-default values per clarification Q5) - MUST FAIL initially

### Implementation for User Story 7

- [ ] T083 [P] [US7] Implement get_langagent_version() function in langagent/runtime/config_resolver.py that reads from package __version__ or metadata
- [ ] T084 [P] [US7] Implement sanitize_for_logging(config: RuntimeConfig) -> dict function in langagent/runtime/config_resolver.py that removes API key fields (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.) from env_vars metadata
- [ ] T085 [P] [US7] Implement track_config_overrides(cli_args, env_vars, dotenv_values, builtin_defaults) -> dict[str, str] function in langagent/runtime/config_resolver.py that returns {field_name: source_name} mapping only for non-default values per clarification Q5
- [ ] T086 [US7] Update resolve() to call track_config_overrides() during merge_priority_chain() to capture which fields were overridden
- [ ] T087 [US7] Enhance startup log emission in resolve() to include: LangAgent version (from T083), agent_dir, model_provider, model_name (if not None), checkpointer, middleware_ids, source annotations (from T085)
- [ ] T088 [US7] Update startup log emission to call sanitize_for_logging() before logging to ensure no API keys are included
- [ ] T089 [US7] Verify all T079-T082 tests now PASS after implementation

**Checkpoint**: At this point, all 7 user stories should be independently functional

---

## Phase 10: GuardrailPolicy Resolution (Cross-Cutting)

**Purpose**: Parse guardrail env vars (LANGAGENT_GUARDRAIL_MODE, LANGAGENT_GUARDRAIL_ALLOW_INTERNAL_ENDPOINTS, LANGAGENT_INTERNAL_ENDPOINTS) with lenient boolean parsing per clarification Q1

### Tests for GuardrailPolicy Resolution (TDD - Write First, Must FAIL)

- [ ] T090 [P] Write test_resolve_guardrail_policy_defaults in tests/runtime/test_config_resolver.py (no guardrail env vars → GuardrailPolicy with enabled=True, mode="smart", redact_pii=True, allow_internal_endpoints=True, internal_endpoint_patterns=[])
- [ ] T091 [P] Write test_resolve_guardrail_allow_internal_endpoints_lenient_bool in tests/runtime/test_config_resolver.py (env LANGAGENT_GUARDRAIL_ALLOW_INTERNAL_ENDPOINTS="yes" → True; "1" → True; "on" → True; "false" → False; "0" → False; "no" → False; "off" → False; case insensitive per clarification Q1)
- [ ] T092 [P] Write test_resolve_guardrail_allow_internal_endpoints_invalid_bool in tests/runtime/test_config_resolver.py (env LANGAGENT_GUARDRAIL_ALLOW_INTERNAL_ENDPOINTS="maybe" → ValidationError exit 78)
- [ ] T093 [P] Write test_resolve_guardrail_mode_validation in tests/runtime/test_config_resolver.py (env LANGAGENT_GUARDRAIL_MODE="all"|"smart"|"strict" → valid; "unknown" → ValidationError exit 78)
- [ ] T094 [P] Write test_resolve_guardrail_internal_endpoints_csv in tests/runtime/test_config_resolver.py (env LANGAGENT_INTERNAL_ENDPOINTS="*.internal.example.com,10.0.0.0/8" → ["*.internal.example.com", "10.0.0.0/8"])

### Implementation for GuardrailPolicy Resolution

- [ ] T095 [P] Implement parse_bool(value: str) -> bool function in langagent/runtime/config_resolver.py with lenient parsing: accept ["true","1","yes","on"] as True, ["false","0","no","off"] as False (case insensitive), raise ValidationError for other values
- [ ] T096 [P] Implement parse_guardrail_policy(env_vars: dict) -> GuardrailPolicy function in langagent/runtime/config_resolver.py that reads LANGAGENT_GUARDRAIL_MODE, LANGAGENT_GUARDRAIL_ALLOW_INTERNAL_ENDPOINTS (via parse_bool), LANGAGENT_INTERNAL_ENDPOINTS (via parse_csv_list)
- [ ] T097 Add call to parse_guardrail_policy() in resolve() method after merge_priority_chain(), construct GuardrailPolicy instance and populate RuntimeConfig.guardrail_policy field
- [ ] T098 Update BUILTIN_DEFAULTS in langagent/runtime/defaults.py to include default GuardrailPolicy (enabled=True, mode="smart", redact_pii=True, allow_internal_endpoints=True, internal_endpoint_patterns=[])
- [ ] T099 Verify all T090-T094 tests now PASS after implementation

**Checkpoint**: GuardrailPolicy resolution complete with lenient boolean parsing

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements, documentation, and validation

- [ ] T100 [P] Run mypy --strict on langagent/runtime/config_resolver.py and langagent/runtime/agent_state.py, fix all type errors
- [ ] T101 [P] Add docstrings to all public functions in RuntimeConfigResolver class following Google style
- [ ] T102 [P] Add module-level docstring to langagent/runtime/config_resolver.py explaining config_resolve stage purpose and 4-source priority chain
- [ ] T103 [P] Verify all ≥20 test cases from spec §四 are implemented and passing in tests/runtime/test_config_resolver.py
- [ ] T104 [P] Run pytest tests/runtime/ and verify 100% pass rate for all F07 tests
- [ ] T105 [P] Add inline comments explaining priority chain merging logic in merge_priority_chain() function
- [ ] T106 Update langagent/runtime/exceptions.py docstrings to document exit codes (RequiredFieldMissingError=5, ConfigPlaceholderError=78, DotenvMalformedError=65, TypeMismatchError=78)
- [ ] T107 Create test coverage report for langagent/runtime/config_resolver.py and verify ≥90% coverage
- [ ] T108 Integration test: Create end-to-end test that combines all 7 user stories (priority chain + validation + .env parsing + frozen config + stage guard + CSV lists + startup logging) in tests/runtime/test_config_resolver_integration.py
- [ ] T109 Final validation: Run all tests with pytest -v tests/runtime/ and confirm zero failures

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-9)**: All depend on Foundational phase completion
  - User Story 1 (P1): Priority chain merging - NO dependencies on other stories
  - User Story 2 (P1): Validation - Depends on US1 (needs merge_priority_chain)
  - User Story 3 (P1): .env parsing - NO dependencies (parse_dotenv is independent)
  - User Story 4 (P2): Frozen config - Depends on US1 (needs RuntimeConfig construction)
  - User Story 5 (P2): Stage guard - NO dependencies (decorator is orthogonal)
  - User Story 6 (P3): CSV parsing - Depends on US1 (needs merge_priority_chain)
  - User Story 7 (P3): Startup logging - Depends on US1 (needs successful resolve)
- **GuardrailPolicy (Phase 10)**: Depends on Foundational + US1
- **Polish (Phase 11)**: Depends on all user stories being complete

### User Story Dependencies

**Critical Path (must complete in order)**:
1. Foundational (Phase 2) - BLOCKS everything
2. User Story 1 (Phase 3) - Core priority chain merging
3. User Story 2 (Phase 4) - Validation (depends on US1)
4. User Story 4 (Phase 6) - Frozen config (depends on US1)
5. User Story 6 (Phase 8) - CSV parsing (depends on US1)
6. User Story 7 (Phase 9) - Startup logging (depends on US1)

**Parallel Opportunities** (can start after Foundational):
- User Story 3 (Phase 5) - .env parsing is independent, can run in parallel with US1
- User Story 5 (Phase 7) - Stage guard is orthogonal, can run in parallel after Foundational

### Within Each User Story

1. Tests MUST be written first and FAIL
2. Implementation makes tests PASS
3. Verify checkpoint before moving to next story

### Parallel Task Opportunities

- All Setup tasks (T001-T004) marked [P] can run in parallel
- All Foundational tasks (T005-T011) marked [P] can run in parallel within Phase 2
- Test writing within each user story: all [P] test tasks can run in parallel
- After US1 completes: US2, US3, US4, US5, US6, US7 tests can be written in parallel (then implemented sequentially per dependencies)

---

## Parallel Example: User Story 1

```bash
# Write all US1 tests in parallel (T012-T016):
Task T012: "test_resolve_cli_overrides_all"
Task T013: "test_resolve_env_overrides_dotenv"
Task T014: "test_resolve_dotenv_overrides_builtin"
Task T015: "test_resolve_builtin_when_no_source"
Task T016: "test_resolve_priority_logged"

# After tests written and failing, implement sequentially (T017-T021):
Task T017: "parse_dotenv()"
Task T018: "merge_priority_chain()"
Task T019: "RuntimeConfigResolver.resolve()"
Task T020: "logging integration"
Task T021: "verify tests pass"
```

---

## Implementation Strategy

### MVP First (User Stories 1-2 Only)

**Rationale**: Priority chain merging (US1) + validation (US2) are P1 and deliver core value

1. Complete Phase 1: Setup → Foundation files ready
2. Complete Phase 2: Foundational → RuntimeConfig schema + resolver skeleton ready
3. Complete Phase 3: User Story 1 → Priority chain merging works
4. Complete Phase 4: User Story 2 → Validation blocks bad configs
5. **STOP and VALIDATE**: Test US1+US2 independently with all 4 sources and validation
6. Demo/Review if ready

### Incremental Delivery

**After MVP (US1+US2), add stories incrementally**:

1. Add User Story 3: .env parsing → Enhances US1 with robust file handling
2. Add User Story 4: Frozen config → Prevents config mutation bugs
3. Add User Story 5: Stage guard → Enforces architectural boundaries
4. Add User Story 6: CSV parsing → Enables middleware/skill configuration
5. Add User Story 7: Startup logging → Improves observability
6. Add GuardrailPolicy: Enables F04 guardrail evaluation
7. Polish: Documentation, type safety, coverage

Each increment adds value without breaking previous stories.

### Parallel Team Strategy

With multiple developers (after Foundational phase complete):

**Option 1: Story-based parallelism**
- Developer A: User Story 1 (priority chain) + User Story 2 (validation)
- Developer B: User Story 3 (.env parsing) + User Story 6 (CSV parsing)
- Developer C: User Story 4 (frozen config) + User Story 5 (stage guard)
- Coordinate: User Story 7 (logging) integrates after US1 complete

**Option 2: Layer-based parallelism**
- Developer A: All tests for US1-US7 (T012-T094)
- Developer B: US1-US3 implementation (priority chain, validation, .env parsing)
- Developer C: US4-US7 implementation (frozen config, stage guard, CSV, logging)

---

## Notes

- **[P] tasks** = different files, no dependencies, can run in parallel
- **[Story] label** maps task to specific user story for traceability
- **TDD MANDATORY** per Constitution Article VIII: Write tests first, ensure FAIL, then implement
- Each user story should be independently completable and testable
- Stop at any checkpoint to validate story independently
- All tests marked "MUST FAIL initially" enforce TDD Red-Green-Refactor cycle
- Verify tests FAIL before implementation, then PASS after implementation
- Commit after each task or logical group
- Constitution Article XV alignment verified in plan.md

---

## Success Criteria Validation

After Phase 11 completion, verify all spec Success Criteria:

- **SC-1**: Run all priority chain tests (T012-T016) → 100% pass
- **SC-2**: Run all validation tests (T022-T028) → 100% detection rate with correct exit codes
- **SC-3**: Run all immutability tests (T049-T055) → 100% enforcement
- **SC-4**: Run all stage boundary tests (T063-T065) → 100% blocked operations
- **SC-5**: Run all startup logging tests (T079-T082) → 100% completeness, no sensitive data

All 5 success criteria must pass before declaring F07 complete.
