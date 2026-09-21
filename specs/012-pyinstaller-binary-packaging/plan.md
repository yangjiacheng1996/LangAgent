# Implementation Plan: PyInstaller Binary Packaging and Distribution

**Branch**: `012-pyinstaller-binary-packaging` | **Date**: 2026-09-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/012-pyinstaller-binary-packaging/spec.md`

## Summary

This feature packages LangAgent into a standalone single-file binary executable using PyInstaller, enabling users to run `./langagent` commands without Python installation. It also generates offline wheels packages for internal PyPI mirrors, ensuring completely disconnected deployment. The implementation includes build scripts, PyInstaller configuration, smoke tests, and CI integration with strict quality gates.

**Primary Requirements**:
- Single-file binary (`dist/langagent`) that runs on Linux x86_64 without Python
- Offline wheels directory for `pip install --no-index` in disconnected environments
- Version tracking (embed git commit hash and version number)
- Security: exclude all `.env` files and LangSmith modules
- Quality gates: smoke tests block CI on failure

**Technical Approach**:
- PyInstaller 6.x in onefile mode with explicit hiddenimports/excludes configuration
- `pip-compile --generate-hashes` for reproducible, tamper-proof dependency locks
- Build scripts in `scripts/` directory; test suites in `tests/build/`
- CI pipeline integration with automated smoke tests as release gate

## Technical Context

**Language/Version**: Python 3.11 (per `pyproject.toml` `requires-python`)

**Primary Dependencies**: 
- PyInstaller 6.x (build-time packaging tool)
- pip-tools (for `pip-compile --generate-hashes`)
- LangChain 0.3+ / LangGraph (runtime dependencies to be packaged)
- All 6 LangChain provider packages (openai, anthropic, google_genai, etc.)

**Storage**: N/A (build tooling; no runtime persistence in this feature)

**Testing**: 
- pytest for build process tests (`tests/build/test_build_binary.py`)
- bash scripts for smoke tests (`scripts/smoke_test_binary.sh`)
- Docker-based isolation tests for offline installation validation

**Target Platform**: Linux x86_64 only (v1 scope; macOS/Windows deferred)

**Project Type**: Build/Distribution System (creates CLI tool binary from existing Python codebase)

**Performance Goals**: 
- Build completes in < 10 minutes on standard CI runner (4 CPU, 8GB RAM)
- Binary size < 200MB (target: < 100MB)
- Smoke tests complete in < 5 minutes

**Constraints**: 
- Must exclude all LangSmith modules (Constitutional Article III)
- Must not package user `.env` files or secrets (Constitutional Article X)
- Must support offline installation without internet access (Constitutional Article XI)
- Binary must be self-contained (no system Python dependency)

**Scale/Scope**: 
- Single binary artifact per build
- ~50-80 Python dependencies to package (LangChain ecosystem)
- 4 CLI commands must work post-packaging (init, doctor, run, eval)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Article I - Project Identity ✅
- **Requirement**: Deliver LangAgent as standalone binary executable (Section 2)
- **Compliance**: This feature implements the binary packaging mandate; users run `./langagent` without Python installation

### Article II - Technology Stack ✅
- **Requirement**: Dependencies installable from internal PyPI mirrors without internet (Section 6)
- **Compliance**: `requirements.lock.txt` with SHA256 hashes + wheels directory enable offline installation

### Article III - LangSmith Exclusion ✅
- **Requirement**: Absolutely prohibit LangSmith dependencies (Sections 1-3)
- **Compliance**: PyInstaller spec explicitly excludes 5 LangSmith module paths; smoke tests verify exclusion

### Article X - Security & Privacy ✅
- **Requirement**: Do not package secrets; CI logs must not print keys (Section 5)
- **Compliance**: 
  - PyInstaller spec excludes `.env` files from `datas`
  - Smoke tests verify secrets not in binary via `strings` command
  - CI build logs sanitized (no API key printing)

### Article XI - Packaging & Distribution ✅
- **Requirement**: Implement all 5 mandates (Sections 1-5)
- **Compliance**:
  1. Single-file binary: PyInstaller onefile mode → `dist/langagent`
  2. CLI entry points: `langagent run/init/eval/doctor` all packaged
  3. Reproducible builds: `requirements.lock.txt` with pinned versions + hashes; version + commit hash injection
  4. Offline installation: wheels directory + `pip install --no-index`
  5. Separate upgrade paths: Binary replacement does not touch user agent directories

### Article VIII - TDD ✅
- **Requirement**: Test-driven development; tests before implementation (Sections 1-6)
- **Compliance**: 
  - `tests/build/test_build_binary.py`: Build process validation
  - `tests/build/test_wheels_isolation.py`: Offline installation tests
  - `scripts/smoke_test_binary.sh`: End-to-end CLI validation
  - All tests written before build scripts

### Article XV - Top-Level Design Primacy ✅
- **Requirement**: Reference top-level design artifacts before implementation
- **Compliance**: Spec explicitly references:
  - `harness/top_level_design/workflow.md` - 4 CLI commands behavior
  - `harness/top_level_design/architecture_modules.md#mod-cli-runner` - Entry point at `langagent/__main__.py`

**Gate Status**: ✅ ALL PASS - No violations; proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/012-pyinstaller-binary-packaging/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file (/speckit.plan output)
├── research.md          # Phase 0: PyInstaller best practices, dependency management
├── data-model.md        # Phase 1: Build artifact entities
├── quickstart.md        # Phase 1: Validation commands for binary builds
├── contracts/           # Phase 1: Build script interfaces
│   ├── build-script.md  # Build script CLI contract
│   └── smoke-test.md    # Smoke test output contract
└── tasks.md             # Phase 2: Implementation tasks (/speckit.tasks - NOT created yet)
```

### Source Code (repository root)

```text
# Build Scripts & Configuration
scripts/
├── build_binary.py         # PyInstaller invocation script (Python)
├── build_binary.spec       # PyInstaller configuration (hiddenimports/excludes)
├── build_wheels.sh         # Wheels generation (bash)
└── smoke_test_binary.sh    # Post-build validation (bash)

# Dependency Management
requirements.lock.txt       # Pinned dependencies with SHA256 hashes
wheels/                     # Downloaded .whl files (generated, not in git)

# Build Artifacts
dist/
└── langagent              # Compiled binary (generated, not in git)

# Test Suites
tests/build/
├── test_build_binary.py       # Automated build process tests
├── test_wheels_isolation.py   # Offline installation validation
└── fixtures/                  # Test agent directories

# Main Program Configuration (modified)
pyproject.toml             # Add [project.scripts] and [build-system] sections
```

**Structure Decision**: This feature adds a new `scripts/` directory at repository root for build automation, separate from the main `langagent/` package source. The build system is orthogonal to the 5-layer architecture (primitives/protocol/runtime/cross-cutting/cli) defined in the constitution. Build scripts consume the existing CLI entry point at `langagent/__main__.py` (provided by F10) and package the entire `langagent/` tree into the binary. Tests live in `tests/build/` to clearly separate build-time validation from runtime unit/integration tests.

## Complexity Tracking

> **No violations requiring justification** - Constitution Check shows all gates passing.

This feature aligns with constitutional mandates without introducing architectural complexity. The build system is additive (new `scripts/` directory) and does not modify the existing 5-layer module structure.
