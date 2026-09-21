# Tasks: PyInstaller Binary Packaging and Distribution

**Input**: Design documents from `/specs/012-pyinstaller-binary-packaging/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: This feature follows TDD (Constitutional Article VIII) - all tests are written BEFORE implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

All paths relative to repository root:
- Build scripts: `scripts/`
- Test suites: `tests/build/`
- Binary output: `dist/`
- Wheels output: `wheels/`
- Lock file: `requirements.lock.txt`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and directory structure for build system

- [ ] T001 Create `scripts/` directory for build automation scripts
- [ ] T002 Create `tests/build/` directory for build process tests
- [ ] T003 Create `tests/build/fixtures/` directory for test agent directories
- [ ] T004 Add `dist/` and `build/` to `.gitignore`
- [ ] T005 Add `wheels/` to `.gitignore`
- [ ] T006 Update `pyproject.toml` to add `[project.scripts]` section with entry point `langagent = "langagent.cli.runner:main"`
- [ ] T007 Update `pyproject.toml` to add `[build-system]` section with setuptools configuration

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core build infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T008 Generate initial `requirements.lock.txt` using `pip-compile --generate-hashes --output-file=requirements.lock.txt pyproject.toml`
- [ ] T009 [P] Create PyInstaller spec template at `scripts/build_binary.spec` with basic structure (entry_point, onefile=True)
- [ ] T010 [P] Add hiddenimports to `scripts/build_binary.spec` for LangChain providers (langchain_openai, langchain_anthropic, langchain_google_genai)
- [ ] T011 [P] Add hiddenimports to `scripts/build_binary.spec` for LangGraph modules (langgraph, langgraph.checkpoint.sqlite, langgraph.checkpoint.postgres)
- [ ] T012 [P] Add hiddenimports to `scripts/build_binary.spec` for LangChain core (langchain_core, langchain_core.runnables, langchain_core.messages, langchain_core.tools)
- [ ] T013 [P] Add hiddenimports to `scripts/build_binary.spec` for F11 eval subsystem (langagent.eval.runner, langagent.eval.task_loader, langagent.eval.report_aggregator, all grader modules)
- [ ] T014 [P] Add hiddenimports to `scripts/build_binary.spec` for base dependencies (pydantic, pydantic_core, langchain_text_splitters)
- [ ] T015 [P] Add excludes to `scripts/build_binary.spec` for LangSmith modules (langsmith, langchain_community.langsmith, langchain.callbacks.langsmith, langchain_core.tracers.langchain, langchain_core.tracers.langchain_v1)
- [ ] T016 [P] Add excludes to `scripts/build_binary.spec` for size reduction (tkinter, matplotlib, numpy.tests, IPython, jupyter)
- [ ] T017 Ensure `scripts/build_binary.spec` datas section is empty (no .env files packaged)

**Checkpoint**: Foundation ready - PyInstaller spec configured; user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Offline Binary Distribution (Priority: P1) 🎯 MVP

**Goal**: Build single-file binary that runs on Linux x86_64 without Python; users can execute `./langagent --help`, `init`, `doctor`, and `run` commands.

**Independent Test**: Copy binary to clean Docker container (no Python), run `langagent init`, `langagent doctor`, `langagent run --help`. Binary executes successfully.

### Tests for User Story 1 (TDD - Write FIRST)

> **RED**: Write these tests FIRST, ensure they FAIL before implementation

- [ ] T018 [P] [US1] Create test fixture: minimal agent directory in `tests/build/fixtures/minimal-agent/` with agent.py, instructions.md, pyproject.toml
- [ ] T019 [P] [US1] Write test `test_build_binary_runs_on_clean_env` in `tests/build/test_build_binary.py` (verifies build succeeds in Docker ubuntu:26.04 without Python pre-installed)
- [ ] T020 [P] [US1] Write test `test_build_binary_size_under_200mb` in `tests/build/test_build_binary.py` (verifies binary < 200MB via stat)
- [ ] T021 [P] [US1] Write test `test_build_binary_includes_all_providers` in `tests/build/test_build_binary.py` (imports all 6 LangChain providers from binary)
- [ ] T022 [P] [US1] Write test `test_build_binary_includes_eval_runner` in `tests/build/test_build_binary.py` (imports F11 eval.runner from binary)
- [ ] T023 [P] [US1] Create smoke test script `scripts/smoke_test_binary.sh` framework and implement first 5 basic tests (T1-T5: version, init, doctor, run --help, eval --help); remaining 5 security tests (T6-T10) will be implemented in US4
- [ ] T024 [US1] Run all tests - verify they FAIL (no implementation exists yet)

### Implementation for User Story 1

- [ ] T025 [US1] Implement `scripts/build_binary.py` main entry point with CLI arg parsing (--clean, --spec, --version, --commit, --output-dir)
- [ ] T026 [US1] Implement pre-build validation in `scripts/build_binary.py` (check PyInstaller installed, spec file exists, entry point exists, pyproject.toml readable, git available)
- [ ] T027 [US1] Implement version injection in `scripts/build_binary.py` (read pyproject.toml version, run `git rev-parse HEAD`, write to langagent/_build_metadata.py; fallback to LANGAGENT_COMMIT env var if git unavailable, use "unknown-commit" if both absent)
- [ ] T028 [US1] Implement PyInstaller invocation in `scripts/build_binary.py` (call PyInstaller.__main__.run() with spec file)
- [ ] T029 [US1] Implement post-build validation in `scripts/build_binary.py` (verify dist/langagent exists, is executable, size < 200MB, is ELF binary)
- [ ] T030 [US1] Implement error handling in `scripts/build_binary.py` (exit code 1 for build failure with full PyInstaller log, exit code 2 for pre-build failure, exit code 3 for post-build failure)
- [ ] T031 [US1] Implement cleanup in `scripts/build_binary.py` (remove langagent/_build_metadata.py after build, delete invalid binary on post-build failure)
- [ ] T032 [US1] Make `scripts/smoke_test_binary.sh` executable (chmod +x)
- [ ] T033 [US1] Implement T1 in `scripts/smoke_test_binary.sh` (test binary version display)
- [ ] T034 [US1] Implement T2 in `scripts/smoke_test_binary.sh` (test init command functionality)
- [ ] T035 [US1] Implement T3 in `scripts/smoke_test_binary.sh` (test doctor command execution)
- [ ] T036 [US1] Implement T4 in `scripts/smoke_test_binary.sh` (test run command help)
- [ ] T037 [US1] Implement T5 in `scripts/smoke_test_binary.sh` (test eval command help)
- [ ] T038 [US1] Add structured output formatting to `scripts/smoke_test_binary.sh` (pass/fail per test, summary at end)
- [ ] T039 [US1] Add cleanup trap to `scripts/smoke_test_binary.sh` (rm -rf test directories on exit)
- [ ] T040 [US1] Run `pytest tests/build/test_build_binary.py` - verify all tests PASS (GREEN)
- [ ] T041 [US1] Run `bash scripts/smoke_test_binary.sh` - verify all 5 tests PASS (T1-T5)
- [ ] T042 [US1] Manual validation: copy dist/langagent to clean Docker container (ubuntu:26.04 without Python), run `./langagent --help`, verify version displayed

**Checkpoint**: At this point, User Story 1 (basic binary build + smoke tests) is fully functional and testable independently

---

## Phase 4: User Story 2 - Pre-Packaged Dependency Wheels (Priority: P1)

**Goal**: Generate offline wheels directory for disconnected deployment; operations teams can `pip install --no-index --find-links=./wheels/ langagent`.

**Independent Test**: Create Docker container with `--network=none`, install from wheels/, verify all imports succeed.

### Tests for User Story 2 (TDD - Write FIRST)

> **RED**: Write these tests FIRST, ensure they FAIL before implementation

- [ ] T043 [P] [US2] Write test `test_pip_install_no_index_succeeds` in `tests/build/test_wheels_isolation.py` (Docker container, pip install from wheels)
- [ ] T044 [P] [US2] Write test `test_wheels_lockfile_pinned` in `tests/build/test_wheels_isolation.py` (verify all deps in requirements.lock.txt have ==X.Y.Z format)
- [ ] T045 [P] [US2] Write test `test_wheels_no_extra_network` in `tests/build/test_wheels_isolation.py` (Docker --network=none, pip install succeeds)
- [ ] T046 [P] [US2] Write test `test_wheels_sha256_hashes_present` in `tests/build/test_wheels_isolation.py` (verify each dep in lock file has ≥1 --hash=sha256: line)
- [ ] T047 [US2] Run all tests - verify they FAIL (no implementation exists yet)

### Implementation for User Story 2

- [ ] T048 [US2] Create `scripts/build_wheels.sh` with shebang and set -e
- [ ] T049 [US2] Implement lock file check in `scripts/build_wheels.sh` (if requirements.lock.txt missing, run pip-compile --generate-hashes)
- [ ] T050 [US2] Implement wheels download in `scripts/build_wheels.sh` (pip download -r requirements.lock.txt -d ./wheels/ --platform manylinux2014_x86_64 --only-binary=:all: --python-version 311)
- [ ] T051 [US2] Add output summary to `scripts/build_wheels.sh` (echo "Wheels downloaded to ./wheels/", ls -lh wheels/)
- [ ] T052 [US2] Make `scripts/build_wheels.sh` executable (chmod +x)
- [ ] T053 [US2] Update `requirements.lock.txt` if needed (regenerate with pip-compile --generate-hashes to ensure all transitive deps included)
- [ ] T054 [US2] Run `bash scripts/build_wheels.sh` - verify wheels/ directory created with 50-80 .whl files
- [ ] T055 [US2] Run `pytest tests/build/test_wheels_isolation.py` - verify all tests PASS (GREEN)
- [ ] T056 [US2] Manual validation: Docker container with --network=none, pip install from wheels/, verify imports work

**Checkpoint**: At this point, User Stories 1 AND 2 (binary + offline wheels) both work independently

---

## Phase 5: User Story 3 - Reproducible Builds with Version Tracking (Priority: P2)

**Goal**: Binary embeds version from pyproject.toml and git commit hash; users can run `./langagent --help` to see "LangAgent v1.2.3 (commit a1b2c3d)".

**Independent Test**: Run build script, check `./langagent --help` contains version + commit; run `strings dist/langagent | grep <commit>` finds embedded hash.

### Tests for User Story 3 (TDD - Write FIRST)

> **RED**: Write these tests FIRST, ensure they FAIL before implementation

- [ ] T057 [P] [US3] Write test `test_binary_version_embedded` in `tests/build/test_build_binary.py` (verify strings dist/langagent contains version pattern)
- [ ] T058 [P] [US3] Write test `test_binary_commit_hash_embedded` in `tests/build/test_build_binary.py` (verify strings dist/langagent contains commit hash)
- [ ] T059 [P] [US3] Write test `test_version_displayed_in_help` in `tests/build/test_build_binary.py` (run ./dist/langagent --help, verify output contains version + commit)
- [ ] T060 [US3] Run all tests - verify they FAIL (version injection not implemented yet)

### Implementation for User Story 3

- [ ] T061 [US3] Enhance version injection in `scripts/build_binary.py` (ensure _build_metadata.py is created with __version__ and __commit__)
- [ ] T062 [US3] Update CLI runner (if needed) to read _build_metadata.py and display in --help output (format: "LangAgent v{version} (commit {commit})")
- [ ] T062.1 [US3] Modify F10 CLI runner in `langagent/cli/runner.py` to import `_build_metadata.py` and display version in --help output (format: "LangAgent v{__version__} (commit {__commit__})")
- [ ] T063 [US3] Update `scripts/build_binary.py` to support --version and --commit CLI overrides (for testing/CI)
- [ ] T064 [US3] Add environment variable support in `scripts/build_binary.py` (LANGAGENT_VERSION, LANGAGENT_COMMIT override CLI args)
- [ ] T065 [US3] Run `pytest tests/build/test_build_binary.py -k version` - verify version tests PASS (GREEN)
- [ ] T066 [US3] Build binary twice from different commits, verify commit hashes differ in output

**Checkpoint**: At this point, User Stories 1, 2, AND 3 all work independently (binary + wheels + version tracking)

---

## Phase 6: User Story 4 - Automated Build Quality Checks (Priority: P2)

**Goal**: Smoke tests validate binary post-build; CI blocks on any failure. Tests verify: no secrets leaked, LangSmith excluded, size < 200MB, all providers importable.

**Independent Test**: Run smoke test script against built binary, verify all 10 tests pass; introduce deliberate failure (remove eval module), verify test detects it.

### Tests for User Story 4 (TDD - Write FIRST)

> **RED**: Write these tests FIRST, ensure they FAIL before implementation

- [ ] T067 [P] [US4] Write test `test_dotenv_excluded_from_binary` in `tests/build/test_build_binary.py` (create fixture with .env containing sk-test, build, verify strings finds nothing)
- [ ] T068 [P] [US4] Write test `test_build_binary_excludes_langsmith` in `tests/build/test_build_binary.py` (verify langsmith not in sys.modules at runtime)
- [ ] T069 [P] [US4] Write test `test_smoke_test_detects_failures` in `tests/build/test_build_binary.py` (intentionally break binary, verify smoke test exits 1)
- [ ] T070 [US4] Run all tests - verify they FAIL (smoke test checks not fully implemented)

### Implementation for User Story 4

- [ ] T071 [US4] Implement T6 in `scripts/smoke_test_binary.sh` (test secret exclusion via strings | grep)
- [ ] T072 [US4] Implement T7 in `scripts/smoke_test_binary.sh` (test LangSmith module exclusion via sys.modules check)
- [ ] T073 [US4] Implement T8 in `scripts/smoke_test_binary.sh` (test binary size constraint via stat)
- [ ] T074 [US4] Implement T9 in `scripts/smoke_test_binary.sh` (test provider import validation)
- [ ] T075 [US4] Implement T10 in `scripts/smoke_test_binary.sh` (test eval subsystem import validation)
- [ ] T076 [US4] Enhance error messages in `scripts/smoke_test_binary.sh` (actionable debugging hints for each failure)
- [ ] T077 [US4] Add exit code handling to `scripts/smoke_test_binary.sh` (exit 1 on any test failure, exit 0 only if all pass)
- [ ] T078 [US4] Add --stop-on-failure option to `scripts/smoke_test_binary.sh` (exit immediately on first failure if flag set)
- [ ] T079 [US4] Run `bash scripts/smoke_test_binary.sh` - verify all 10 tests (T1-T10) PASS
- [ ] T080 [US4] Run `pytest tests/build/test_build_binary.py -k exclusion` - verify security tests PASS (GREEN)
- [ ] T081 [US4] Test failure detection: remove eval module from hiddenimports, rebuild, run smoke tests, verify exit 1

**Checkpoint**: At this point, all quality gates (smoke tests T1-T10) are operational and block bad builds

---

## Phase 7: User Story 5 - Upgrade Without Overwriting User Content (Priority: P3)

**Goal**: Binary upgrade preserves user agent directories; custom instructions.md, tools/, skills/ remain unchanged.

**Independent Test**: Create agent directory with custom content, replace binary with new version, run `langagent doctor`, verify all custom files unchanged.

### Tests for User Story 5 (TDD - Write FIRST)

> **RED**: Write these tests FIRST, ensure they FAIL before implementation

- [ ] T082 [P] [US5] Write test `test_binary_upgrade_preserves_agent_dir` in `tests/build/test_build_binary.py` (create agent with custom instructions.md, upgrade binary, verify content unchanged)
- [ ] T083 [P] [US5] Write test `test_binary_upgrade_preserves_user_config` in `tests/build/test_build_binary.py` (create ~/.local/share/langagent/logs/, upgrade, verify logs preserved)
- [ ] T084 [P] [US5] Write test `test_user_agent_pyproject_excluded_from_binary` in `tests/build/test_build_binary.py` (create agent with pyproject.toml, verify strings dist/langagent does not contain agent deps)
- [ ] T085 [US5] Run all tests - verify they PASS (this is validation of existing behavior, not new implementation)

### Implementation for User Story 5

> **Note**: This user story validates existing separation between binary and agent directories. No new implementation required if tests pass.

- [ ] T086 [US5] Document upgrade procedure in quickstart.md (step-by-step: replace dist/langagent, verify agent dirs untouched)
- [ ] T087 [US5] Add comment to `scripts/build_binary.spec` datas section explaining why user agent dirs are excluded
- [ ] T088 [US5] Run `pytest tests/build/test_build_binary.py -k upgrade` - verify upgrade safety tests PASS (GREEN)
- [ ] T089 [US5] Manual validation: create agent, build v1 binary, edit agent files, build v2 binary, run v2, verify edits preserved

**Checkpoint**: All user stories (US1-US5) are now independently functional and tested

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: CI integration, documentation, and final validation

- [ ] T090 [P] Create `.github/workflows/build-binary.yml` CI workflow (on push/PR: setup Python 3.11, install deps, run build_binary.py, run smoke tests, upload artifact on success)
- [ ] T090.1 [P] Add CI log sanitization check in `.github/workflows/build-binary.yml` (grep build logs for secret patterns like 'sk-', 'key_', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY'; fail workflow if found)
- [ ] T091 [P] Add smoke test as mandatory CI step in workflow (bash scripts/smoke_test_binary.sh; workflow fails if exit code ≠ 0)
- [ ] T092 [P] Add build artifact upload step in workflow (uses: actions/upload-artifact@v3, only if all tests pass)
- [ ] T093 [P] Update root README.md with "Building from Source" section (link to quickstart.md)
- [ ] T094 [P] Add troubleshooting guide to quickstart.md (common errors: ModuleNotFoundError → check hiddenimports; size > 200MB → check excludes)
- [ ] T095 Verify all 6 quickstart.md validation scenarios work end-to-end (Scenario 1-6)
- [ ] T096 Run full test suite: `pytest tests/build/ -v` - verify all tests PASS
- [ ] T097 Run CI simulation locally: generate lock → download wheels → build binary → smoke tests → all succeed
- [ ] T098 Final manual validation: copy binary to fresh ubuntu:26.04 container (no Python), run all 4 CLI commands (init, doctor, run --help, eval --help)
- [ ] T099 Update CHANGELOG.md (if exists) with F12 feature summary
- [ ] T100 Code review: verify all Constitutional requirements met (Articles I, II, III, X, XI, VIII, XV)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - US1 (P1): Binary build → foundational for US2-US5
  - US2 (P1): Wheels generation → can run parallel with US1 after foundational
  - US3 (P2): Version tracking → depends on US1 (enhances binary)
  - US4 (P2): Quality gates → depends on US1 (validates binary)
  - US5 (P3): Upgrade safety → validates US1 behavior (no new code)
- **Polish (Phase 8)**: Depends on all user stories being complete

### Recommended Execution Order

**For MVP (minimum viable product)**:
1. Phase 1 (Setup) → Phase 2 (Foundational) → Phase 3 (US1) → **STOP and VALIDATE**

**For full feature**:
1. Phase 1 (Setup)
2. Phase 2 (Foundational) ← **CRITICAL CHECKPOINT**
3. Phase 3 (US1 - Binary) + Phase 4 (US2 - Wheels) ← can parallelize
4. Phase 5 (US3 - Version tracking) ← enhances US1
5. Phase 6 (US4 - Quality gates) ← validates US1
6. Phase 7 (US5 - Upgrade safety) ← validates existing behavior
7. Phase 8 (Polish) ← CI + docs

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD)
- Tests in parallel where marked [P]
- Implementation follows tests
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 1 (Setup)**: T001-T007 all parallel (different files)

**Phase 2 (Foundational)**: T009-T016 parallel (different sections of spec file)

**Phase 3 (US1 Tests)**: T018-T022 parallel (different test files/functions)

**Phase 4 (US2 Tests)**: T043-T046 parallel (different test functions)

**Phase 5 (US3 Tests)**: T057-T059 parallel (different test functions)

**Phase 6 (US4 Tests)**: T067-T069 parallel (different test functions)

**Phase 7 (US5 Tests)**: T082-T084 parallel (different test functions)

**Phase 8 (Polish)**: T090-T094 parallel (different files: CI workflow, README, docs)

**Multiple developers scenario**:
- After Phase 2: Dev A → US1, Dev B → US2, Dev C → US3-US5 (sequential but can start early)

---

## Parallel Example: User Story 1

```bash
# Phase 3: Launch all US1 tests together (T018-T022):
Task: "Create test fixture in tests/build/fixtures/minimal-agent/"
Task: "Write test_build_binary_runs_on_clean_env in tests/build/test_build_binary.py"
Task: "Write test_build_binary_size_under_200mb in tests/build/test_build_binary.py"
Task: "Write test_build_binary_includes_all_providers in tests/build/test_build_binary.py"
Task: "Write test_build_binary_includes_eval_runner in tests/build/test_build_binary.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T007)
2. Complete Phase 2: Foundational (T008-T017) ← **CRITICAL - blocks all stories**
3. Complete Phase 3: User Story 1 (T018-T042)
4. **STOP and VALIDATE**: Run quickstart.md Scenario 1 (Clean Build → Smoke Test)
5. Demo binary in clean Docker container

**MVP Delivered**: Single-file binary that runs without Python on Linux x86_64

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → **MVP Release**
3. Add User Story 2 → Test independently → Offline capability added
4. Add User Story 3 → Test independently → Version tracking added
5. Add User Story 4 → Test independently → Quality gates automated
6. Add User Story 5 → Validate → Upgrade safety confirmed
7. Polish (CI + docs) → **Full Release**

### Parallel Team Strategy

With 3 developers:

1. All devs: Complete Setup + Foundational together (1-2 days)
2. After Foundational complete:
   - Developer A: User Story 1 (binary build) - **critical path**
   - Developer B: User Story 2 (wheels) - parallel with A
   - Developer C: Start US3-US5 tests (can write tests before A finishes)
3. Integration point: US3-US4 need US1 binary to test against
4. All devs: Polish phase together

---

## Notes

- [P] tasks = different files, no dependencies within phase
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- TDD is mandatory per Constitutional Article VIII: Write tests FIRST (RED), implement (GREEN), refactor
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Binary size target is < 100MB (hard limit 200MB)
- All smoke tests (T1-T10) must pass before CI allows merge/release
- Version + commit hash injection is automatic (no manual sync)

---

## Task Count Summary

- **Phase 1 (Setup)**: 7 tasks
- **Phase 2 (Foundational)**: 10 tasks
- **Phase 3 (US1 - Binary)**: 25 tasks (7 tests + 18 implementation)
- **Phase 4 (US2 - Wheels)**: 14 tasks (5 tests + 9 implementation)
- **Phase 5 (US3 - Version)**: 11 tasks (4 tests + 7 implementation) ← **+1 task (T062.1)**
- **Phase 6 (US4 - Quality)**: 15 tasks (4 tests + 11 implementation)
- **Phase 7 (US5 - Upgrade)**: 8 tasks (4 tests + 4 validation)
- **Phase 8 (Polish)**: 12 tasks ← **+1 task (T090.1)**

**Total**: 102 tasks ← **Updated from 100 (added T062.1, T090.1)**

**Test tasks**: 28 (27%)
**Implementation tasks**: 63 (62%)
**Infrastructure tasks**: 11 (11%)

**Parallel opportunities**: ~35 tasks marked [P] can run concurrently
