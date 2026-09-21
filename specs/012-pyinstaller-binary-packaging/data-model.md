# Data Model: PyInstaller Binary Packaging and Distribution

**Feature**: 012-pyinstaller-binary-packaging  
**Date**: 2026-09-21  
**Status**: Phase 1

## Overview

This document defines the key entities and their relationships in the binary packaging and distribution system. These entities represent build artifacts, configuration files, and validation states managed by the build scripts.

---

## Entity Definitions

### E1: Binary Artifact

**Description**: The compiled single-file executable produced by PyInstaller.

**Attributes**:
- `path` (string): Filesystem path to the binary (e.g., `dist/langagent`)
- `size_bytes` (integer): File size in bytes
- `version` (string): Embedded version string from `pyproject.toml` (e.g., "1.2.3")
- `commit_hash` (string): Git commit hash injected at build time (e.g., "a1b2c3d")
- `build_timestamp` (datetime): When the binary was created
- `platform` (string): Target platform identifier (e.g., "linux_x86_64")
- `python_version` (string): Python version used for build (e.g., "3.11")

**Relationships**:
- **Produced by**: Build Configuration (E3)
- **Contains**: All packages listed in Requirements Lock (E4)
- **Excludes**: User agent directories, `.env` files, LangSmith modules
- **Validated by**: Smoke Test Results (E6)

**Validation Rules**:
- Size MUST be < 200MB (target: < 100MB)
- MUST be executable (`chmod +x` not required after build)
- MUST NOT contain secret strings (verified by `strings` command)
- MUST NOT load LangSmith modules at runtime

**State Transitions**:
```
[Not Exists] --build--> [Built] --smoke-test--> [Validated] --distribute--> [Released]
                           |
                           +--build-failure--> [Failed]
                           |
                           +--smoke-test-failure--> [Invalid]
```

---

### E2: Wheels Package

**Description**: Directory containing pre-downloaded `.whl` files for offline installation.

**Attributes**:
- `directory_path` (string): Path to wheels directory (e.g., `./wheels/`)
- `wheel_files` (list[WheelFile]): Collection of individual wheel files
- `total_size_bytes` (integer): Sum of all wheel file sizes
- `platform` (string): Target platform for wheels (e.g., "manylinux2014_x86_64")
- `python_version` (string): Python version compatibility (e.g., "311")

**WheelFile Sub-Entity**:
- `filename` (string): Wheel filename (e.g., `langchain-0.3.0-py3-none-any.whl`)
- `package_name` (string): Extracted package name (e.g., "langchain")
- `version` (string): Package version (e.g., "0.3.0")
- `size_bytes` (integer): File size
- `sha256_hash` (string): SHA256 checksum (from lock file)

**Relationships**:
- **Generated from**: Requirements Lock (E4)
- **Used by**: Offline installation process (`pip install --no-index`)
- **Corresponds to**: Each entry in Requirements Lock

**Validation Rules**:
- All packages in Requirements Lock MUST have corresponding wheel file
- Each wheel filename MUST match pattern `*-py3-none-any.whl` or `*manylinux*_x86_64.whl`
- SHA256 of each wheel MUST match hash in Requirements Lock
- Directory MUST be self-sufficient (no missing transitive dependencies)

---

### E3: Build Configuration

**Description**: PyInstaller `.spec` file defining what gets packaged into the binary.

**Attributes**:
- `spec_path` (string): Path to spec file (e.g., `scripts/build_binary.spec`)
- `entry_point` (string): Main module path (e.g., `langagent/__main__.py`)
- `hiddenimports` (list[string]): Modules to force-include (see R1 in research.md)
- `excludes` (list[string]): Modules to force-exclude (LangSmith, tkinter, etc.)
- `datas` (list[tuple]): Data files to include (currently empty for this feature)
- `onefile` (boolean): Single-file mode flag (always `true`)
- `console` (boolean): Console application flag (always `true` for CLI)

**Relationships**:
- **Controls**: Binary Artifact (E1) contents
- **References**: Requirements Lock (E4) implicitly via Python imports
- **Validated by**: Build Process Tests (E5)

**Validation Rules**:
- `hiddenimports` MUST include all 6 LangChain provider packages
- `excludes` MUST include all 5 LangSmith module paths
- `datas` MUST NOT include `.env` files
- `entry_point` MUST exist and be executable Python file

**Constitutional Alignment**:
- Excludes list enforces Article III (LangSmith exclusion)
- Datas exclusions enforce Article X (no secrets in binary)

---

### E4: Requirements Lock

**Description**: Locked dependency manifest with pinned versions and cryptographic hashes.

**Attributes**:
- `file_path` (string): Path to lock file (e.g., `requirements.lock.txt`)
- `dependencies` (list[LockedDependency]): All pinned packages
- `hash_algorithm` (string): Hash type used (always "sha256")
- `generation_tool` (string): Tool that created lock file (e.g., "pip-compile 7.x")
- `python_version` (string): Target Python version (e.g., "3.11")

**LockedDependency Sub-Entity**:
- `package_name` (string): Package name (e.g., "langchain")
- `version` (string): Exact version (e.g., "0.3.0")
- `hashes` (list[string]): SHA256 hashes for all distribution formats (wheel + sdist)
- `direct_dependency` (boolean): Is this a direct dependency or transitive?

**Relationships**:
- **Drives**: Wheels Package (E2) generation
- **Consumed by**: Binary Artifact (E1) build process
- **Validates**: Supply chain integrity (tamper detection)

**Validation Rules**:
- Every line MUST match format: `package==version --hash=sha256:...`
- Each package MUST have ≥1 hash
- No version ranges allowed (no `>=`, `~=`, `^`)
- PyInstaller MUST be locked to `6.x` series

**Regeneration Triggers**:
- `pyproject.toml` dependencies change
- Upstream package updates (manual decision)
- Security vulnerability patches

---

### E5: Build Process Tests

**Description**: Automated test suite validating the build process.

**Attributes**:
- `test_file_path` (string): Path to test module (e.g., `tests/build/test_build_binary.py`)
- `test_cases` (list[TestCase]): Individual test scenarios
- `framework` (string): Testing framework (e.g., "pytest")

**TestCase Sub-Entity**:
- `name` (string): Test function name (e.g., `test_build_binary_size_under_200mb`)
- `category` (enum): Test type - "build_process", "security", "isolation", "smoke"
- `expected_outcome` (enum): "pass" or "fail"
- `failure_action` (enum): "block_ci", "warn", "informational"

**Key Test Cases** (from FR-029 to FR-033):
1. `test_build_binary_runs_on_clean_env`: Build succeeds in fresh Docker container
2. `test_build_binary_size_under_200mb`: Binary size constraint
3. `test_build_binary_excludes_langsmith`: LangSmith not in `sys.modules`
4. `test_build_binary_includes_all_providers`: All 6 providers importable
5. `test_build_binary_includes_eval_runner`: F11 eval modules present
6. `test_pip_install_no_index_succeeds`: Offline installation works
7. `test_wheels_lockfile_pinned`: All deps have exact versions
8. `test_dotenv_excluded_from_binary`: No secrets in binary
9. `test_binary_version_embedded`: Version + commit hash present

**Relationships**:
- **Validates**: Build Configuration (E3)
- **Validates**: Binary Artifact (E1)
- **Validates**: Wheels Package (E2)
- **Blocks**: CI pipeline on failure

**Validation Rules**:
- ALL tests MUST pass before binary is marked for distribution
- Test failures MUST produce actionable error messages
- Tests MUST be runnable in CI environment (no manual steps)

---

### E6: Smoke Test Results

**Description**: Output from end-to-end smoke test validation.

**Attributes**:
- `script_path` (string): Path to smoke test script (e.g., `scripts/smoke_test_binary.sh`)
- `execution_time_seconds` (float): How long tests took to run
- `test_results` (list[SmokeTestResult]): Individual test outcomes
- `overall_status` (enum): "pass" or "fail"
- `binary_under_test` (string): Path to tested binary

**SmokeTestResult Sub-Entity**:
- `test_name` (string): Human-readable test description (e.g., "Test: --help displays version")
- `command` (string): Shell command executed (e.g., `./dist/langagent --help`)
- `exit_code` (integer): Command exit code
- `output` (string): Captured stdout/stderr
- `passed` (boolean): Whether test passed

**Key Smoke Tests** (from FR-029):
1. Binary shows version/commit in `--help`
2. `langagent init /tmp/demo` creates directory
3. `langagent doctor` runs without error
4. `langagent run --help` shows usage
5. `langagent eval --help` shows usage
6. `strings` command finds no secrets
7. Binary size < 200MB

**Relationships**:
- **Validates**: Binary Artifact (E1)
- **Triggered by**: CI pipeline after build
- **Blocks**: Artifact upload on failure

**Validation Rules**:
- ALL smoke tests MUST pass (no partial success)
- Smoke tests MUST complete in < 5 minutes
- Exit code MUST be 0 for pass, non-zero for fail

---

### E7: Main Program Metadata

**Description**: Configuration and metadata in root `pyproject.toml` (distinct from user agent `pyproject.toml`).

**Attributes**:
- `file_path` (string): Always at repository root `./pyproject.toml`
- `version` (string): Project version (e.g., "1.2.3")
- `python_requires` (string): Python version constraint (e.g., ">=3.11")
- `cli_entry_points` (dict[string, string]): CLI command mappings
- `build_system` (dict): Build backend configuration

**Key Sections**:
```toml
[project]
name = "langagent"
version = "1.2.3"
requires-python = ">=3.11"

[project.scripts]
langagent = "langagent.cli.runner:main"

[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"
```

**Relationships**:
- **Consumed by**: Build Configuration (E3) for version injection
- **Consumed by**: Requirements Lock (E4) generation
- **Packaged into**: Binary Artifact (E1) metadata
- **Distinct from**: User agent directory `pyproject.toml` (not packaged)

**Validation Rules**:
- `[project.scripts]` MUST define `langagent` entry point
- Version MUST follow semver (major.minor.patch)
- Version MUST match git tag (if building from tagged commit)
- MUST NOT contain user agent dependencies

---

## Entity Relationship Diagram

```
┌─────────────────────────┐
│ Main Program Metadata   │
│ (E7: pyproject.toml)    │
└───────────┬─────────────┘
            │ provides version
            ▼
┌─────────────────────────┐         ┌──────────────────────┐
│ Requirements Lock       │────────>│ Wheels Package       │
│ (E4: requirements.lock) │generates│ (E2: ./wheels/)      │
└───────────┬─────────────┘         └──────────────────────┘
            │ pins dependencies
            ▼
┌─────────────────────────┐         ┌──────────────────────┐
│ Build Configuration     │────────>│ Binary Artifact      │
│ (E3: build_binary.spec) │produces │ (E1: dist/langagent) │
└───────────┬─────────────┘         └──────────┬───────────┘
            │ validates                        │
            ▼                                  │
┌─────────────────────────┐                   │
│ Build Process Tests     │                   │ validates
│ (E5: test_build_*.py)   │                   │
└─────────────────────────┘                   ▼
                                   ┌──────────────────────┐
                                   │ Smoke Test Results   │
                                   │ (E6: smoke_test.sh)  │
                                   └──────────────────────┘
```

---

## Validation Workflow State Machine

```
┌─────────────────────────────────────────────────────────────────┐
│ Build Workflow                                                  │
└─────────────────────────────────────────────────────────────────┘

[Start] --> [Generate Lock File (E4)]
                    |
                    | pip-compile
                    v
            [Lock File Valid?] --No--> [Report Error & Exit]
                    |
                    | Yes
                    v
            [Download Wheels (E2)]
                    |
                    | pip download
                    v
            [Wheels Complete?] --No--> [Report Missing & Exit]
                    |
                    | Yes
                    v
            [Build Binary (E1)]
                    |
                    | PyInstaller
                    v
            [Build Success?] --No--> [Output Error Log & Exit]
                    |
                    | Yes
                    v
            [Run Build Tests (E5)]
                    |
                    v
            [All Tests Pass?] --No--> [Block CI & Exit]
                    |
                    | Yes
                    v
            [Run Smoke Tests (E6)]
                    |
                    v
            [All Smoke Pass?] --No--> [Block CI & Exit]
                    |
                    | Yes
                    v
            [Upload Artifact]
                    |
                    v
                [End]
```

---

## Data Persistence

### Files in Git (Version Controlled)
- `scripts/build_binary.py` - Build script
- `scripts/build_binary.spec` - Build configuration (E3)
- `scripts/build_wheels.sh` - Wheels generation script
- `scripts/smoke_test_binary.sh` - Smoke test script (E6 definition)
- `requirements.lock.txt` - Locked dependencies (E4)
- `pyproject.toml` - Main program metadata (E7)
- `tests/build/test_build_binary.py` - Build tests (E5)

### Files NOT in Git (Build Artifacts)
- `dist/langagent` - Binary artifact (E1)
- `wheels/*.whl` - Wheel files (E2)
- `build/` - PyInstaller intermediate files
- `.pytest_cache/` - Test execution cache

### CI Artifacts (Ephemeral)
- Binary uploaded to GitHub Actions artifacts
- Test reports (JUnit XML, coverage)
- Build logs

---

## Data Validation Summary

| Entity | Key Constraint | Enforcement |
|--------|----------------|-------------|
| E1: Binary Artifact | < 200MB, no secrets, no LangSmith | Smoke tests |
| E2: Wheels Package | SHA256 matches lock file | Isolation tests |
| E3: Build Configuration | Correct hiddenimports/excludes | Build tests |
| E4: Requirements Lock | All deps pinned with hashes | Lock file parser test |
| E5: Build Process Tests | All tests pass | CI gate |
| E6: Smoke Test Results | Exit code 0 (all pass) | CI gate |
| E7: Main Program Metadata | Valid semver version | Pyproject validator |

**Next Document**: [contracts/](./contracts/) - Build script interface definitions
