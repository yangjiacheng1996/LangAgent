# Feature Specification: PyInstaller Binary Packaging and Distribution

**Feature Branch**: `012-pyinstaller-binary-packaging`

**Created**: 2026-09-21

**Status**: Draft

**Constitutional Alignment**: This specification aligns with Article XV (Top-Level Design Primacy) by referencing the top-level design artifacts and constitutional constraints. See alignment checklist in section "Constitutional Alignment Checklist" below.

## Constitutional Alignment Checklist

This feature implements the core requirements of the following constitutional articles:

- **Article I (Project Identity)**: Delivers LangAgent as a standalone binary executable (Article I, Section 2) - users run `./langagent` without Python installation
- **Article II (Technology Stack)**: Ensures all dependencies can be installed from internal PyPI mirrors without internet access (Article II, Section 6)
- **Article III (LangSmith Exclusion)**: Explicitly excludes all LangSmith-related modules from the binary build (Article III, Sections 1-3)
- **Article X (Security & Privacy)**: Does not package user `.env` files or secrets; CI logs must not print keys (Article X, Section 5)
- **Article XI (Packaging & Distribution)**: Implements all 5 mandates - single-file binary, CLI entry points, reproducible builds, offline installation, separate upgrade paths (Article XI, Sections 1-5)

**Top-Level Design Artifacts Referenced**:
1. `harness/top_level_design/workflow.md` - All 4 CLI commands must work post-packaging
2. `harness/top_level_design/architecture_modules.md#mod-cli-runner` - CLI entry point at `langagent/__main__.py`

## Clarifications

### Session 2026-09-21

- Q: 当 PyInstaller 构建失败时，系统应该如何处理？ → A: 立即失败，输出完整的 PyInstaller 错误日志和缺失模块清单，退出码非零
- Q: `requirements.lock.txt` 应该包含哪些依赖的哈希值？ → A: 包含所有依赖（直接+传递）的 SHA256 哈希值，使用 `pip-compile --generate-hashes` 生成
- Q: 当二进制在运行时检测到 Python 版本不匹配（例如系统 Python 3.9，但二进制编译时用的 3.11）时，应该如何处理？ → A: 二进制完全独立运行，不检测系统 Python 版本（PyInstaller onefile 模式自包含）
- Q: 当用户的智能体目录（agent directory）缺失必需文件（如 `agent.py` 或 `instructions.md`）时，`langagent run` 应该提供什么级别的诊断信息？ → A: 列出缺失文件 + 提供修复建议（如 "运行 `langagent doctor` 检查" 或 "参考文档 URL"）
- Q: `scripts/smoke_test_binary.sh` 冒烟测试失败时，CI 流水线应该采取什么行动？ → A: 阻断 CI 流水线，标记构建失败，不生成发布产物（严格门禁）

## User Scenarios & Testing

### User Story 1 - Offline Binary Distribution (Priority: P1)

Enterprise users receive a single `langagent` binary file and deploy it on internal servers without Python or internet access. They can immediately run `./langagent init my-agent` and start building agents.

**Why this priority**: This is the core value proposition - making LangAgent truly "ready-to-run" without environment setup. Without this, users must install Python, manage dependencies, and deal with version conflicts.

**Independent Test**: Can be fully tested by copying the binary to a clean Docker container (ubuntu:26.04 with no Python), running `langagent init`, `langagent doctor`, and `langagent run --max-turns 1`. Delivers immediate usability without any setup.

**Acceptance Scenarios**:

1. **Given** a Linux x86_64 machine with no Python installed (e.g., Docker ubuntu:26.04 base image), **When** user downloads and runs `./langagent --help`, **Then** the help text displays with version number and commit hash
2. **Given** the binary is placed in `/opt/tools/`, **When** user runs `/opt/tools/langagent init /tmp/demo-agent`, **Then** a complete agent directory structure is created with all template files
3. **Given** an agent directory with valid `.env`, **When** user runs `./langagent run /tmp/demo-agent --max-turns 1`, **Then** the agent executes one loop iteration and exits successfully
4. **Given** a disconnected network environment, **When** user runs any `langagent` command, **Then** no network requests are made and all functionality works

---

### User Story 2 - Pre-Packaged Dependency Wheels (Priority: P1)

Operations teams receive a `wheels/` directory containing all LangChain, LangGraph, and provider dependencies as `.whl` files. They can install these into an internal PyPI mirror before deploying LangAgent.

**Why this priority**: Ensures offline operation per Constitutional Article XI, Section 4. Without pre-packaged wheels, first run would require internet access, violating the offline constraint.

**Independent Test**: Can be fully tested by creating a Docker container with no internet, installing from `wheels/` directory using `pip install --no-index --find-links=./wheels/ langagent`, and verifying all imports succeed. Delivers offline installation capability.

**Acceptance Scenarios**:

1. **Given** the `wheels/` directory and a `requirements.lock.txt` file, **When** operations runs `pip install --no-index --find-links=./wheels/ langagent` in a disconnected environment, **Then** all dependencies install successfully
2. **Given** a fresh internal PyPI mirror, **When** operations uploads all `.whl` files from `wheels/`, **Then** subsequent `pip install langagent` commands from that mirror succeed without internet
3. **Given** the binary is built, **When** inspecting `requirements.lock.txt`, **Then** every dependency has an exact pinned version (format `package==X.Y.Z`)

---

### User Story 3 - Reproducible Builds with Version Tracking (Priority: P2)

Development teams build the binary using `scripts/build_binary.py`, and the resulting executable automatically embeds the version number and git commit hash. Users can verify which version they're running.

**Why this priority**: Enables troubleshooting and version tracking in production. Teams can correlate bug reports with specific builds. Not P1 because basic functionality works without version info.

**Independent Test**: Can be fully tested by running the build script, checking the output binary with `./langagent --help` contains version + commit hash, and verifying `strings dist/langagent | grep <commit>` finds the hash. Delivers build traceability.

**Acceptance Scenarios**:

1. **Given** the repository at commit `a1b2c3d`, **When** running `python scripts/build_binary.py`, **Then** the output binary contains "commit a1b2c3d" in its help text
2. **Given** `pyproject.toml` defines version "1.2.3", **When** the binary is built, **Then** running `./langagent --help` displays "LangAgent v1.2.3"
3. **Given** two builds from different commits, **When** comparing version output, **Then** each binary reports its unique commit hash

---

### User Story 4 - Automated Build Quality Checks (Priority: P2)

CI systems run `scripts/smoke_test_binary.sh` after each build to verify all CLI commands work, no secrets leak, and LangSmith modules are excluded. Build failures are caught before distribution.

**Why this priority**: Prevents distribution of broken binaries. Not P1 because manual testing can catch these issues initially; automation is for scaling and confidence.

**Independent Test**: Can be fully tested by running the smoke test script against a built binary, verifying it checks `init`, `doctor`, `run --help`, `eval --help`, size limits, and secret exclusion. Delivers automated quality gates.

**Acceptance Scenarios**:

1. **Given** a freshly built binary, **When** running `scripts/smoke_test_binary.sh`, **Then** all test cases pass (init, doctor, run --help, eval --help, size < 200MB, no env leaks)
2. **Given** a binary with a test `.env` file containing `OPENAI_API_KEY=sk-test`, **When** running `strings dist/langagent | grep "sk-test"`, **Then** no matches are found
3. **Given** a build that accidentally includes LangSmith, **When** smoke tests run, **Then** the test fails with a clear error message about prohibited dependencies

---

### User Story 5 - Upgrade Without Overwriting User Content (Priority: P3)

Users replace their old `langagent` binary with a new version. Their existing agent directories remain unchanged - custom `instructions.md`, `skills/`, `tools/`, and `middleware/` are preserved.

**Why this priority**: Ensures upgrade safety per Constitutional Article XI, Section 5. P3 because v1 doesn't require an automated upgrade command; manual replacement is acceptable.

**Independent Test**: Can be fully tested by creating an agent directory with custom content, replacing the binary with a new version, running `langagent doctor`, and verifying all custom files remain unchanged. Delivers safe upgrade path.

**Acceptance Scenarios**:

1. **Given** an agent directory with user-edited `instructions.md`, **When** replacing the `langagent` binary with a newer version, **Then** the `instructions.md` content is unchanged
2. **Given** `~/.local/share/langagent/logs/` contains execution logs, **When** upgrading the binary, **Then** all historical logs are preserved
3. **Given** an agent directory with custom tools in `tools/*.py`, **When** running the new binary, **Then** the custom tools are still loaded and functional

---

### Edge Cases

- What happens when PyInstaller build fails due to configuration errors or missing modules?
  - **Behavior**: Build script immediately exits with non-zero code, outputs complete PyInstaller error log and missing module diagnostics
  - **Rationale**: Fast failure aligns with TDD principles; configuration issues won't self-resolve through retries
  
- What happens when PyInstaller's static analysis misses a dynamically imported module (e.g., provider package)?
  - **Mitigation**: Use explicit `hiddenimports` list in `.spec` file for all LangChain providers and deep submodules
  - **Detection**: Smoke tests must import all 6 providers + core modules after build
  
- What happens when the binary size exceeds 200MB due to included dependencies?
  - **Mitigation**: Explicit `excludes` list removes tkinter, matplotlib, numpy.tests, and all LangSmith modules
  - **Detection**: Automated test fails if `stat -c %s dist/langagent` > 200MB
  
- What happens when a user's agent directory has a `pyproject.toml` with conflicting dependencies?
  - **Expected behavior**: User agent `pyproject.toml` is NOT packaged into the binary (PyInstaller only scans main program); user dependencies are installed separately in their environment
  - **Detection**: Test verifies `strings dist/langagent` does not contain content from user agent's `pyproject.toml`
  
- What happens when building on a machine that has `.env` files with real secrets?
  - **Mitigation**: PyInstaller spec explicitly excludes `.env` files from all data collection
  - **Detection**: Test runs `strings dist/langagent | grep "sk-"` and fails if secrets are found; CI grep validation before release

- What happens when running the binary on a platform other than Linux x86_64?
  - **Expected behavior**: Binary fails with clear error message; v1 only supports Linux x86_64 per Constitutional Article XI risk statement
  - **Out of scope**: Cross-platform builds are not required for v1

- What happens when the binary runs on a system with different Python versions or no Python installed?
  - **Behavior**: Binary operates completely independently; does not detect or require system Python (PyInstaller onefile mode is self-contained)
  - **Rationale**: Aligns with Constitutional Article XI, Section 1 "users run without Python installation"

- What happens when building in a non-git environment (e.g., clean Docker container without .git/)?
  - **Behavior**: Build script attempts `git rev-parse HEAD`; if git command fails, falls back to `LANGAGENT_COMMIT` environment variable; if both absent, uses "unknown-commit" placeholder
  - **Rationale**: Enables CI/CD pipelines that build from archives or non-git contexts while maintaining traceability when possible

- What happens when user runs `langagent run` on an incomplete agent directory (missing `agent.py` or `instructions.md`)?
  - **Behavior**: Command lists all missing required files and provides remediation guidance (e.g., "Run `langagent doctor`" or documentation link)
  - **Rationale**: Balances Constitutional Article V, Section 2 requirement to report missing files with good UX for troubleshooting

## Requirements

### Functional Requirements

#### Build System

- **FR-001**: System MUST provide `scripts/build_binary.py` that invokes PyInstaller to create a single-file executable from `langagent/__main__.py`; on build failure, script MUST immediately exit with non-zero code and output complete PyInstaller error log including missing module list
- **FR-002**: System MUST provide `scripts/build_binary.spec` with PyInstaller configuration including hiddenimports, excludes, and datas sections
- **FR-003**: System MUST provide `scripts/build_wheels.sh` that exports `requirements.lock.txt` and downloads all wheels to `./wheels/`
- **FR-004**: System MUST inject version number from `pyproject.toml` and commit hash from `git rev-parse HEAD` into the binary at build time; if git is unavailable (e.g., non-git Docker build environment), MUST fallback to `LANGAGENT_COMMIT` environment variable, or use "unknown-commit" placeholder if both absent
- **FR-005**: System MUST produce a binary named `langagent` in `dist/` directory that is executable without Python installation

#### PyInstaller Configuration

- **FR-006**: PyInstaller spec MUST include in `hiddenimports` all 6 LangChain provider packages: `langchain_openai`, `langchain_anthropic`, `langchain_google_genai`, `langchain_community`, `langchain_groq`, `langchain_cohere` (and their submodules)
- **FR-007**: PyInstaller spec MUST include in `hiddenimports` all LangGraph checkpoint modules: `langgraph.checkpoint.sqlite`, `langgraph.checkpoint.postgres`
- **FR-008**: PyInstaller spec MUST include in `hiddenimports` core LangChain modules: `langchain_core`, `langchain_core.runnables`, `langchain_core.messages`, `langchain_core.tools`
- **FR-009**: PyInstaller spec MUST include in `hiddenimports` all eval subsystem modules: `langagent.eval.runner`, `langagent.eval.task_loader`, `langagent.eval.report_aggregator`, and all grader modules
- **FR-010**: PyInstaller spec MUST exclude from the binary all LangSmith-related modules: `langsmith`, `langchain_community.langsmith`, `langchain.callbacks.langsmith`, `langchain_core.tracers.langchain`, `langchain_core.tracers.langchain_v1`
- **FR-011**: PyInstaller spec MUST exclude size-bloating packages not used at runtime: `tkinter`, `matplotlib`, `numpy.tests`
- **FR-012**: PyInstaller spec MUST NOT include `.env` files in `datas` section

#### Dependency Management

- **FR-013**: System MUST provide `requirements.lock.txt` with all dependencies (direct and transitive) pinned to exact versions using `==X.Y.Z` format and SHA256 hashes (generated via `pip-compile --generate-hashes`)
- **FR-014**: `requirements.lock.txt` MUST lock PyInstaller version to `6.x` series for compatibility with LangChain/LangGraph
- **FR-015**: System MUST support installation via `pip install --no-index --find-links=./wheels/ langagent` in disconnected environments
- **FR-016**: Main program `pyproject.toml` MUST define `[project.scripts]` entry: `langagent = "langagent.cli.runner:main"`
- **FR-017**: Main program `pyproject.toml` MUST define `[build-system]` section with build backend configuration

#### Runtime Behavior

- **FR-018**: Binary MUST display version and commit hash when run with `--help` (format: "LangAgent vX.Y.Z (commit abcdef)"); binary operates independently without detecting or requiring system Python installation (PyInstaller onefile mode is fully self-contained)
- **FR-019**: Binary MUST successfully execute `langagent init <dir>` and create agent directory structure; when required files are missing from an agent directory (e.g., `agent.py`, `instructions.md`), MUST list missing files and provide actionable remediation suggestions (e.g., "Run `langagent doctor` to diagnose" or documentation URL)
- **FR-020**: Binary MUST successfully execute `langagent doctor` and display all diagnostic checks
- **FR-021**: Binary MUST successfully execute `langagent run --help` and display complete usage information
- **FR-022**: Binary MUST successfully execute `langagent eval --help` and display complete usage information
- **FR-023**: Binary MUST be able to import and instantiate all 6 LangChain provider models at runtime (without calling external APIs)
- **FR-024**: Binary MUST NOT expose or load LangSmith modules at runtime (verified by checking `sys.modules`)

#### Security & Privacy

- **FR-025**: Build process MUST NOT include any `.env` files in the binary artifact
- **FR-026**: Build process MUST NOT include user agent directory `pyproject.toml` files in the binary
- **FR-027**: CI build logs MUST NOT print API keys, even if present in environment variables
- **FR-028**: Binary artifact MUST NOT contain secret strings searchable via `strings` command

#### Testing & Validation

- **FR-029**: System MUST provide `scripts/smoke_test_binary.sh` that validates binary functionality via subprocess execution; on any test failure, CI pipeline MUST block and mark build as failed without generating release artifacts
- **FR-030**: System MUST provide `tests/build/test_build_binary.py` with automated tests for build process
- **FR-031**: System MUST provide `tests/build/test_wheels_isolation.py` with automated tests for offline installation
- **FR-032**: Build validation MUST include size check ensuring binary is under 200MB
- **FR-033**: Build validation MUST verify all eval subsystem modules are importable from the binary

### Key Entities

- **Binary Artifact**: The compiled `dist/langagent` executable file
  - Attributes: size (bytes), version string, commit hash, build timestamp
  - Relationships: Contains all LangAgent Python modules, excludes user agent directories

- **Wheels Package**: The `wheels/` directory containing `.whl` files
  - Attributes: wheel filename, package name, version, Python compatibility
  - Relationships: Corresponds to entries in `requirements.lock.txt`

- **Build Configuration**: The `scripts/build_binary.spec` PyInstaller spec file
  - Attributes: hiddenimports list, excludes list, datas list, binary name
  - Relationships: Controls what goes into Binary Artifact

- **Requirements Lock**: The `requirements.lock.txt` dependency manifest
  - Attributes: package name, exact version, SHA256 hashes (all direct and transitive dependencies)
  - Relationships: Drives Wheels Package generation, ensures reproducible builds and supply chain security

- **Main Program Metadata**: The root `pyproject.toml`
  - Attributes: version number, CLI entry points, build system config
  - Relationships: Packaged into Binary Artifact; distinct from user agent `pyproject.toml`

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can download a single `langagent` binary, place it on a machine without Python, and successfully run `langagent init` within 30 seconds
- **SC-002**: Binary size remains under 200MB (target: under 100MB) after packaging all required dependencies
- **SC-003**: Installation from `wheels/` directory succeeds in a disconnected Docker container within 5 minutes
- **SC-004**: All 4 CLI commands (init, doctor, run, eval) execute successfully in the packaged binary as verified by smoke tests
- **SC-005**: 100% of smoke tests pass before any binary is marked for distribution; any smoke test failure blocks CI pipeline and prevents artifact generation
- **SC-006**: Zero secrets or API keys are discoverable in the binary via `strings` command after building from a repository with test `.env` files
- **SC-007**: PyInstaller build completes within 10 minutes on a standard CI runner (4 CPU, 8GB RAM)
- **SC-008**: Upgraded binary preserves 100% of user-created files in existing agent directories (instructions, skills, tools, middleware)

## Assumptions

- **Platform**: v1 targets Linux x86_64 only; macOS and Windows support are deferred (Article XI, Section 9, Risk 3)
- **Python Version**: Build environment has Python 3.11 as specified in `pyproject.toml` `requires-python`
- **Git Availability**: Build scripts assume `git` command is available to extract commit hash
- **Build Environment**: CI runners have sufficient disk space (> 2GB free) and memory (> 4GB) for PyInstaller compilation
- **PyInstaller Version**: Using PyInstaller 6.x which has confirmed compatibility with LangChain 0.3+ and LangGraph
- **User Agent Separation**: User agent directories are created post-binary-distribution via `langagent init`; they are not bundled into the binary
- **F10 Dependency**: F10 (CLI runner with `langagent/__main__.py` entry point) is already implemented and tested
- **F11 Dependency**: F11 (eval subsystem) is already implemented; its modules will be auto-discovered by PyInstaller AST analysis and/or included via hiddenimports
- **Network-Free Operation**: Once installed, no LangAgent functionality requires internet access except user-initiated model API calls
- **Internal PyPI Mirror**: Enterprise deployment environments have an internal PyPI mirror where wheels can be uploaded
