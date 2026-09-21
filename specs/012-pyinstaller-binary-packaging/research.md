# Research: PyInstaller Binary Packaging and Distribution

**Feature**: 012-pyinstaller-binary-packaging  
**Date**: 2026-09-21  
**Status**: Phase 0 Complete

## Overview

This document consolidates research findings for packaging LangAgent as a standalone binary using PyInstaller 6.x, generating offline wheels with cryptographic hashes, and implementing build quality gates.

---

## R1: PyInstaller 6.x Configuration for LangChain/LangGraph Projects

### Decision
Use PyInstaller 6.x in **onefile mode** with explicit `hiddenimports` list for LangChain ecosystem packages.

### Rationale
1. **Version Choice**: PyInstaller 6.x has improved hooks for Python 3.11/3.12 and better compatibility with namespace packages (common in `langchain_*` providers)
2. **Onefile Mode**: Produces single executable file as required by Constitutional Article XI, Section 1; simplifies distribution (no `_internal/` directory to manage)
3. **Hiddenimports Strategy**: LangChain's plugin architecture (provider packages like `langchain_openai`) uses dynamic imports that PyInstaller's AST analysis may miss; explicit listing ensures inclusion

### Alternatives Considered
- **PyInstaller 5.x**: Rejected due to known issues with `importlib.metadata` in Python 3.11+ (causes runtime errors with LangChain's version detection)
- **PyOxidizer**: Rejected due to lack of mature support for C extensions (required by `numpy`, `pydantic` in LangChain stack)
- **Nuitka**: Rejected due to compilation time (>30 minutes for large projects) exceeding CI constraints

### Implementation Details
```python
# build_binary.spec key sections
a = Analysis(
    ['langagent/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        # Providers (dynamic imports)
        'langchain_openai', 'langchain_anthropic', 'langchain_google_genai',
        'langchain_community', 'langchain_core', 'langchain_text_splitters',
        # LangGraph
        'langgraph', 'langgraph.checkpoint.sqlite', 'langgraph.checkpoint.postgres',
        # Eval subsystem (F11)
        'langagent.eval.runner', 'langagent.eval.task_loader',
        'langagent.eval.report_aggregator',
        'langagent.eval.graders.exact_match', 'langagent.eval.graders.contains',
        'langagent.eval.graders.regex', 'langagent.eval.graders.llm_judge',
        'langagent.eval.graders.tool_call_match',
        # Core dependencies
        'pydantic', 'pydantic_core',
    ],
    excludes=[
        # LangSmith (Constitutional Article III)
        'langsmith', 'langchain_community.langsmith',
        'langchain.callbacks.langsmith',
        'langchain_core.tracers.langchain', 'langchain_core.tracers.langchain_v1',
        # Size reduction
        'tkinter', 'matplotlib', 'numpy.tests', 'IPython', 'jupyter',
    ],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='langagent',
    onefile=True,  # Single-file mode
    console=True,
)
```

### Validation
- Smoke test imports all provider packages in packaged binary
- Binary size check: < 200MB (excludes reduce from ~300MB baseline)
- Runtime verification: `python -c "import sys; assert 'langsmith' not in sys.modules"`

---

## R2: Reproducible Builds with Cryptographic Hashes

### Decision
Use `pip-compile --generate-hashes` to produce `requirements.lock.txt` with SHA256 hashes for all dependencies (direct + transitive).

### Rationale
1. **Supply Chain Security**: SHA256 hashes prevent dependency tampering (CVE-2013-5123 demonstrated pip's vulnerability to MITM attacks)
2. **Reproducible Builds**: Pinned versions + hashes ensure identical builds across environments (Constitutional Article XI, Section 3)
3. **Offline Installation Verification**: `pip install --require-hashes` enforces hash validation even in disconnected environments

### Alternatives Considered
- **Poetry lock file**: Rejected because Poetry's lock format is not directly usable by `pip download` for wheels generation
- **Version pinning only (no hashes)**: Rejected due to lack of tamper protection; does not satisfy Constitutional Article X security requirements
- **pipenv**: Rejected due to slower dependency resolution and less mature tooling for hash generation

### Implementation Details
```bash
# Generate lock file with hashes
pip-compile \
  --generate-hashes \
  --output-file=requirements.lock.txt \
  pyproject.toml

# Example output format
langchain==0.3.0 \
    --hash=sha256:abc123... \
    --hash=sha256:def456...  # wheel + sdist hashes
langchain-core==0.3.1 \
    --hash=sha256:789ghi...
```

### Validation
- Lock file parsing test: verify all lines match `package==version --hash=sha256:...` format
- Offline install test: Docker container with no internet installs from wheels + lock file
- Hash count: each package has ≥1 hash (wheel or sdist)

---

## R3: Version and Commit Hash Injection

### Decision
Inject version from `pyproject.toml` and commit hash from `git rev-parse HEAD` at build time using PyInstaller's `--version-file` and runtime environment variables.

### Rationale
1. **Troubleshooting**: Users can report exact version + commit for bug triage (Constitutional Article XI, Section 3 requirement)
2. **Automation**: Avoids manual version synchronization between git tags and code
3. **Auditability**: CI builds can correlate binary artifacts with source commits

### Alternatives Considered
- **Manual version updates**: Rejected due to human error risk (version mismatches between releases)
- **importlib.metadata at runtime**: Rejected because PyInstaller's bundled metadata may not be accessible via standard importlib APIs
- **Embedded version.py file**: Considered but `--version-file` is simpler and PyInstaller-native

### Implementation Details
```python
# scripts/build_binary.py
import subprocess
import tomli  # or tomllib in Python 3.11+

# Read version from pyproject.toml
with open('pyproject.toml', 'rb') as f:
    pyproject = tomli.load(f)
    version = pyproject['project']['version']

# Get commit hash
commit = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip()

# Inject into spec via environment or modify spec dynamically
os.environ['LANGAGENT_VERSION'] = version
os.environ['LANGAGENT_COMMIT'] = commit

# In langagent/__init__.py or cli/runner.py
__version__ = os.getenv('LANGAGENT_VERSION', 'dev')
__commit__ = os.getenv('LANGAGENT_COMMIT', 'unknown')

# Display in --help
def show_version():
    print(f"LangAgent v{__version__} (commit {__commit__})")
```

### Validation
- Build test: verify `strings dist/langagent | grep <commit_hash>` finds injected hash
- Runtime test: `./langagent --help` output contains version + commit
- Multiple builds: different commits produce different commit strings

---

## R4: Binary Self-Containment (No System Python Dependency)

### Decision
PyInstaller onefile mode bundles Python interpreter and all dependencies; binary does **not** check or require system Python.

### Rationale
1. **Constitutional Alignment**: Article XI, Section 1 mandates "users run without Python installation"
2. **Portability**: Binary runs on machines with Python 2.x, Python 3.x, or no Python at all
3. **Simplicity**: Eliminates version mismatch errors and user support burden

### Alternatives Considered
- **Check system Python and warn if mismatched**: Rejected because it contradicts "no Python required" promise and adds failure modes
- **Use system Python if available**: Rejected due to unpredictable behavior with different Python versions/packages

### Implementation Details
- PyInstaller onefile mode creates self-extracting archive with embedded Python 3.11 interpreter
- At runtime, binary extracts to `/tmp/_MEI<random>/` and executes
- No `PYTHONPATH` or system site-packages consulted

### Validation
- Docker test: `FROM scratch` base image + glibc → binary runs successfully
- Version independence: binary built with Python 3.11 runs on system with Python 3.9 or no Python

---

## R5: Smoke Test Design Patterns

### Decision
Implement bash-based smoke tests that invoke binary as subprocess and validate output; block CI on any failure.

### Rationale
1. **Fast Feedback**: Smoke tests catch 80% of packaging errors in <5 minutes
2. **Isolation**: Subprocess invocation tests actual binary (not in-process imports)
3. **CI Integration**: Exit code propagation allows simple CI gate (`smoke_test.sh || exit 1`)

### Alternatives Considered
- **Python pytest for smoke tests**: Rejected because requires Python runtime (defeats purpose of testing "no Python needed")
- **Manual testing only**: Rejected due to human error risk and slow iteration
- **Full integration tests**: Rejected for smoke layer (too slow; reserved for regression suite)

### Implementation Details
```bash
#!/bin/bash
# scripts/smoke_test_binary.sh
set -e  # Exit on first failure

BINARY="./dist/langagent"

# Test 1: Binary executes and shows help
echo "Test: --help displays version"
$BINARY --help | grep -q "LangAgent v"

# Test 2: Init creates directory
echo "Test: init command"
$BINARY init /tmp/test-agent
test -f /tmp/test-agent/agent.py

# Test 3: Doctor runs without error
echo "Test: doctor command"
cd /tmp/test-agent && $BINARY doctor

# Test 4: No secrets leaked
echo "Test: secret exclusion"
! strings $BINARY | grep -q "sk-test"

# Test 5: Size constraint
echo "Test: binary size < 200MB"
SIZE=$(stat -c%s "$BINARY")
test $SIZE -lt 209715200

echo "All smoke tests passed!"
```

### Validation
- CI pipeline: smoke tests run after build, before artifact upload
- Failure scenarios: inject deliberate errors (missing module, leaked secret) to verify detection
- Performance: smoke tests complete in <5 minutes

---

## R6: Offline Wheels Generation Strategy

### Decision
Use `pip download -r requirements.lock.txt -d ./wheels/ --platform linux_x86_64 --only-binary=:all:` to pre-download all wheels for target platform.

### Rationale
1. **Offline Installation**: Constitutional Article XI, Section 4 requires no internet on first run
2. **Platform Specificity**: Target Linux x86_64 only (v1 scope); avoid cross-platform wheel conflicts
3. **Binary-Only**: Exclude source distributions (sdist) to prevent build-time compilation requirements

### Alternatives Considered
- **Include sdist as fallback**: Rejected because sdist requires build tools (gcc, etc.) in target environment, violating "offline" constraint
- **Universal wheels only**: Rejected because some dependencies (e.g., `pydantic`) have platform-specific wheels with better performance
- **Manual wheel curation**: Rejected due to maintenance burden and error risk

### Implementation Details
```bash
#!/bin/bash
# scripts/build_wheels.sh
set -e

# Generate lock file (if not exists)
if [ ! -f requirements.lock.txt ]; then
  pip-compile --generate-hashes --output-file=requirements.lock.txt pyproject.toml
fi

# Download wheels for target platform
pip download \
  -r requirements.lock.txt \
  -d ./wheels/ \
  --platform manylinux2014_x86_64 \
  --platform linux_x86_64 \
  --only-binary=:all: \
  --python-version 311

echo "Wheels downloaded to ./wheels/"
ls -lh ./wheels/
```

### Validation
- Isolation test: Docker container with `--network=none` installs from wheels
- Completeness check: `pip install --no-index --find-links=./wheels/ langagent` succeeds
- Platform verification: all wheels match `*manylinux*_x86_64.whl` or `*py3-none-any.whl`

---

## R7: CI Integration and Quality Gates

### Decision
Integrate smoke tests as mandatory CI step after build; block merge/release on failure (exit code ≠ 0).

### Rationale
1. **Shift Left**: Catch packaging errors before distribution (Constitutional Article VIII TDD principle)
2. **No Manual Bottleneck**: Automated gate eliminates human approval delay
3. **Clear Failure Signal**: CI red build prevents bad binary from reaching users

### Alternatives Considered
- **Smoke tests as optional/informational**: Rejected because defeats quality gate purpose
- **Post-release validation**: Rejected due to rollback cost and user impact
- **Manual smoke testing**: Rejected due to inconsistency and slow iteration

### Implementation Details
```yaml
# .github/workflows/build-binary.yml
name: Build Binary

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python 3.11
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install pyinstaller pip-tools
          pip-compile --generate-hashes
      
      - name: Build binary
        run: python scripts/build_binary.py
      
      - name: Run smoke tests
        run: bash scripts/smoke_test_binary.sh
        # ↑ This step MUST pass or workflow fails
      
      - name: Upload binary artifact
        if: success()
        uses: actions/upload-artifact@v3
        with:
          name: langagent-binary
          path: dist/langagent
```

### Validation
- CI test: introduce deliberate smoke test failure → verify workflow fails
- Merge protection: GitHub branch protection requires "Build Binary" check to pass
- Artifact availability: only successful builds upload binary to artifact storage

---

## Research Summary

All clarifications from Technical Context resolved:

| Area | Decision | Key Constraint |
|------|----------|----------------|
| PyInstaller Configuration | v6.x onefile + hiddenimports | LangChain dynamic imports |
| Dependency Security | SHA256 hashes via pip-compile | Supply chain tamper protection |
| Version Tracking | Git commit + pyproject.toml version | Troubleshooting & audit trail |
| Runtime Independence | No system Python check | Constitutional Article XI |
| Quality Gate | Bash smoke tests block CI | Fast failure detection |
| Offline Wheels | Platform-specific binary wheels | Disconnected environments |
| CI Integration | Automated smoke tests mandatory | No human approval bottleneck |

**Next Phase**: Phase 1 - Design data models, define build script contracts, create quickstart validation guide.
