# Quickstart: Binary Build Validation

**Feature**: 012-pyinstaller-binary-packaging  
**Purpose**: Runnable validation scenarios proving the binary packaging system works end-to-end  
**Date**: 2026-09-21

---

## Prerequisites

Before running validation scenarios, ensure:

1. **Development Environment**:
   - Python 3.11+ installed
   - Git repository cloned
   - Working directory is repository root

2. **Dependencies Installed**:
   ```bash
   pip install pyinstaller>=6.0,<7.0 pip-tools pytest
   ```

3. **Source Code Ready**:
   - F10 (CLI runner) implemented at `langagent/__main__.py`
   - F11 (eval subsystem) implemented under `langagent/eval/`
   - `pyproject.toml` has valid `[project]` section with version

---

## Validation Scenario 1: Clean Build → Smoke Test (5-10 minutes)

**Goal**: Build binary from scratch and validate all CLI commands work.

### Step 1: Generate Dependency Lock File
```bash
# Generate requirements.lock.txt with SHA256 hashes
pip-compile --generate-hashes --output-file=requirements.lock.txt pyproject.toml

# Verify lock file format
head -5 requirements.lock.txt
# Expected: Lines like "langchain==0.3.0 --hash=sha256:abc123..."
```

**Expected Outcome**: 
- File `requirements.lock.txt` created
- All lines match format: `package==version --hash=sha256:...`
- No version ranges (no `>=`, `~=`)

### Step 2: Download Offline Wheels
```bash
# Generate wheels directory
bash scripts/build_wheels.sh

# Verify wheels downloaded
ls -lh wheels/ | head -10
```

**Expected Outcome**:
- Directory `wheels/` contains 50-80 `.whl` files
- File sizes reasonable (langchain ~2MB, numpy ~20MB, etc.)
- All wheels match platform: `*manylinux*_x86_64.whl` or `*py3-none-any.whl`

### Step 3: Build Binary
```bash
# Run build script
python scripts/build_binary.py --clean

# Check output
ls -lh dist/
file dist/langagent
```

**Expected Outcome**:
- Binary created at `dist/langagent`
- Size: 80-150 MB (under 200MB limit)
- File type: `ELF 64-bit LSB executable, x86-64`
- Build completes in < 10 minutes

### Step 4: Run Smoke Tests
```bash
# Execute all smoke tests
bash scripts/smoke_test_binary.sh

# Check exit code
echo $?  # Should be 0
```

**Expected Outcome**:
```
Running LangAgent Binary Smoke Tests
Binary: dist/langagent (95.3 MB)

[PASS] T1: Binary version display
[PASS] T2: Init command functionality
[PASS] T3: Doctor command execution
[PASS] T4: Run command help
[PASS] T5: Eval command help
[PASS] T6: Secret exclusion verification
[PASS] T7: LangSmith module exclusion
[PASS] T8: Binary size constraint
[PASS] T9: Provider import validation
[PASS] T10: Eval subsystem import validation

Result: ALL TESTS PASSED (10/10)
```

### Step 5: Manual Binary Invocation
```bash
# Test help output
./dist/langagent --help

# Test init command
./dist/langagent init /tmp/test-agent

# Test doctor command
cd /tmp/test-agent && ../dist/langagent doctor
```

**Expected Outcome**:
- `--help` shows version like "LangAgent v1.2.3 (commit a1b2c3d)"
- `init` creates `/tmp/test-agent/` with `agent.py`, `instructions.md`, etc.
- `doctor` runs diagnostic checks without crashing

---

## Validation Scenario 2: Offline Installation Test (Docker, 10-15 minutes)

**Goal**: Prove binary and wheels work in completely disconnected environment.

### Step 1: Build Test Docker Image
```bash
# Create Dockerfile for offline test
cat > Dockerfile.offline-test <<'EOF'
FROM python:3.11-slim

# Install only base system tools (no pip packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels and lock file
COPY wheels/ /wheels/
COPY requirements.lock.txt /requirements.lock.txt

# Disable network access (simulate air-gapped environment)
RUN echo "127.0.0.1 pypi.org pypi.python.org files.pythonhosted.org" >> /etc/hosts

WORKDIR /app
CMD ["/bin/bash"]
EOF

# Build image
docker build -f Dockerfile.offline-test -t langagent-offline-test .
```

### Step 2: Test Offline Pip Install
```bash
# Run container with network disabled
docker run --rm --network=none langagent-offline-test bash -c "
  pip install --no-index --find-links=/wheels/ langagent && \
  python -c 'import langchain; import langgraph; print(\"Success: All imports work\")' \
"
```

**Expected Outcome**:
```
Looking in links: /wheels
Processing ./wheels/langagent-1.2.3-py3-none-any.whl
...
Successfully installed langagent-1.2.3 langchain-0.3.0 ...
Success: All imports work
```

### Step 3: Test Binary in Clean Container
```bash
# Copy binary to container and run
docker run --rm -v $(pwd)/dist:/dist langagent-offline-test bash -c "
  /dist/langagent --help && \
  /dist/langagent init /tmp/agent && \
  /dist/langagent doctor \
"
```

**Expected Outcome**:
- `--help` shows version without error
- `init` creates directory structure
- `doctor` runs (may show warnings about missing `.env`, but no crashes)

---

## Validation Scenario 3: Security Validation (5 minutes)

**Goal**: Verify no secrets or prohibited modules leaked into binary.

### Step 1: Create Test Agent with Secrets
```bash
# Create agent directory with .env file
./dist/langagent init /tmp/secret-agent
echo "OPENAI_API_KEY=sk-test1234567890abcdef" > /tmp/secret-agent/.env
```

### Step 2: Attempt to Build Binary from Secret-Containing Repo
```bash
# Note: This is a negative test - we verify secrets are NOT packaged
# The build script should already exclude .env, but let's verify

# Search binary for secret strings
strings dist/langagent | grep -E "(OPENAI_API_KEY|sk-test1234567890)"
echo "Exit code: $?"  # Should be 1 (not found)
```

**Expected Outcome**:
```
Exit code: 1
```
(No output from grep means secrets not found)

### Step 3: Verify LangSmith Exclusion
```bash
# Check binary does not contain LangSmith modules
strings dist/langagent | grep -i langsmith
echo "Exit code: $?"  # Should be 1 (not found)

# Verify at runtime
./dist/langagent -c "import sys; print('langsmith' in sys.modules)"
# Expected output: False
```

**Expected Outcome**:
```
Exit code: 1
False
```

### Step 4: Check Excluded Packages (Size Reduction)
```bash
# Verify tkinter excluded
./dist/langagent -c "import tkinter" 2>&1 | grep "No module named"
# Should show error (tkinter excluded)

# Verify matplotlib excluded
./dist/langagent -c "import matplotlib" 2>&1 | grep "No module named"
# Should show error (matplotlib excluded)
```

**Expected Outcome**:
Both imports fail with `ModuleNotFoundError` (packages successfully excluded for size reduction).

---

## Validation Scenario 4: Version Tracking (2 minutes)

**Goal**: Verify version and commit hash injection works correctly.

### Step 1: Check Embedded Metadata
```bash
# Extract version from binary
strings dist/langagent | grep -E "LangAgent v[0-9]+\.[0-9]+\.[0-9]+"

# Extract commit hash
strings dist/langagent | grep -E "commit [a-f0-9]{7}"
```

**Expected Outcome**:
```
LangAgent v1.2.3
commit a1b2c3d
```

### Step 2: Verify Runtime Display
```bash
# Check --help output
./dist/langagent --help | grep -E "v[0-9]+\.[0-9]+\.[0-9]+"
./dist/langagent --help | grep -E "commit [a-f0-9]{7}"
```

**Expected Outcome**:
Help text includes both version and commit, e.g.:
```
LangAgent v1.2.3 (commit a1b2c3d)
...
```

### Step 3: Build from Different Commits
```bash
# Current build
COMMIT1=$(git rev-parse --short HEAD)
python scripts/build_binary.py
strings dist/langagent | grep "commit"

# Different commit (checkout older commit)
git checkout HEAD~1
COMMIT2=$(git rev-parse --short HEAD)
python scripts/build_binary.py
strings dist/langagent | grep "commit"

# Verify they differ
test "$COMMIT1" != "$COMMIT2" && echo "Commit tracking works!"
```

**Expected Outcome**:
Two builds from different commits show different commit hashes in binary.

---

## Validation Scenario 5: CI Pipeline Simulation (15 minutes)

**Goal**: Simulate full CI workflow locally before pushing to remote CI.

### Step 1: Clean Workspace
```bash
# Remove all build artifacts
rm -rf dist/ build/ wheels/
git status  # Should show clean working tree
```

### Step 2: Run Full Build + Test Pipeline
```bash
# Simulate CI steps
set -e  # Exit on any failure

echo "Step 1: Generate lock file..."
pip-compile --generate-hashes --output-file=requirements.lock.txt pyproject.toml

echo "Step 2: Download wheels..."
bash scripts/build_wheels.sh

echo "Step 3: Build binary..."
python scripts/build_binary.py --clean

echo "Step 4: Run smoke tests..."
bash scripts/smoke_test_binary.sh

echo "Step 5: Run build process tests..."
pytest tests/build/test_build_binary.py -v

echo "Step 6: Run isolation tests..."
pytest tests/build/test_wheels_isolation.py -v

echo "CI pipeline simulation complete!"
```

**Expected Outcome**:
All steps pass; script exits with code 0; output shows:
```
CI pipeline simulation complete!
```

### Step 3: Simulate Failure Scenario
```bash
# Intentionally break smoke test (remove eval module from hiddenimports)
sed -i '/langagent.eval.runner/d' scripts/build_binary.spec

# Rebuild
python scripts/build_binary.py --clean

# Run smoke tests (should fail)
bash scripts/smoke_test_binary.sh
echo "Exit code: $?"  # Should be 1 (failure)
```

**Expected Outcome**:
```
[FAIL] T10: Eval subsystem import validation
  ModuleNotFoundError: No module named 'langagent.eval.runner'
Exit code: 1
```

### Step 4: Restore Working Config
```bash
# Restore spec file
git checkout scripts/build_binary.spec

# Verify fix
python scripts/build_binary.py --clean
bash scripts/smoke_test_binary.sh  # Should pass now
```

---

## Validation Scenario 6: Binary Portability (5 minutes)

**Goal**: Verify binary runs on different Linux distributions without Python.

### Step 1: Test on Ubuntu (Python not installed)
```bash
# Run in Ubuntu container WITHOUT Python
docker run --rm -v $(pwd)/dist:/dist ubuntu:22.04 bash -c "
  # Verify Python not available
  ! which python3 && echo 'Python not installed (as expected)' && \
  # Run binary
  /dist/langagent --help
"
```

**Expected Outcome**:
```
Python not installed (as expected)
LangAgent v1.2.3 (commit a1b2c3d)
...
```

### Step 2: Test on Alpine (Different libc)
```bash
# Note: Alpine uses musl libc; binary built on glibc may not work
# This is expected to FAIL (v1 targets glibc only)

docker run --rm -v $(pwd)/dist:/dist alpine:3.18 sh -c "
  /dist/langagent --help
"
```

**Expected Outcome**:
```
Error: /lib64/libc.so.6: version GLIBC_2.34 not found
```
(This failure is acceptable; v1 targets Linux glibc x86_64 only)

---

## Success Criteria Summary

| Scenario | Pass Criteria | Time |
|----------|---------------|------|
| 1: Clean Build → Smoke Test | All 10 smoke tests pass | 5-10 min |
| 2: Offline Installation | Pip install + imports work in `--network=none` | 10-15 min |
| 3: Security Validation | No secrets/LangSmith in binary | 5 min |
| 4: Version Tracking | Commit hash changes per build | 2 min |
| 5: CI Simulation | Full pipeline passes locally | 15 min |
| 6: Binary Portability | Runs on Ubuntu without Python | 5 min |

**Total Validation Time**: ~45 minutes (can be parallelized)

---

## Troubleshooting

### Problem: Build fails with "ModuleNotFoundError"
**Solution**: Add missing module to `hiddenimports` in `scripts/build_binary.spec`

### Problem: Binary size exceeds 200MB
**Solution**: 
1. Check `excludes` list includes tkinter, matplotlib, numpy.tests
2. Verify LangSmith modules excluded
3. Run `pyinstaller --clean` to remove cached files

### Problem: Smoke test T6 fails (secrets detected)
**Solution**: 
1. Verify `.env` NOT in `datas` section of spec
2. Clean build directory: `rm -rf build/ dist/`
3. Rebuild with `--clean` flag

### Problem: Offline install fails in Docker
**Solution**:
1. Verify `requirements.lock.txt` includes ALL transitive dependencies
2. Check wheels directory has files for all locked packages
3. Regenerate wheels: `bash scripts/build_wheels.sh`

---

## Next Steps

After all validation scenarios pass:
1. **Commit changes**: `git add scripts/ requirements.lock.txt`
2. **Push to CI**: `git push origin 012-pyinstaller-binary-packaging`
3. **Monitor CI build**: Verify GitHub Actions completes successfully
4. **Create release**: Tag commit and upload binary artifact

For detailed implementation tasks, see **[tasks.md](./tasks.md)** (generated by `/speckit.tasks`).
