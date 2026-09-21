# Contract: Build Binary Script

**File**: `scripts/build_binary.py`  
**Type**: CLI Tool  
**Purpose**: Invoke PyInstaller to package LangAgent into a single-file binary executable.

---

## Command-Line Interface

### Invocation
```bash
python scripts/build_binary.py [OPTIONS]
```

### Options
- `--clean`: Remove existing `build/` and `dist/` directories before building (default: false)
- `--spec FILE`: Path to PyInstaller spec file (default: `scripts/build_binary.spec`)
- `--version VERSION`: Override version string (default: read from `pyproject.toml`)
- `--commit HASH`: Override commit hash (default: read from `git rev-parse HEAD`)
- `--output-dir DIR`: Output directory for binary (default: `dist/`)

### Exit Codes
- `0`: Build succeeded; binary created at `dist/langagent`
- `1`: Build failed; see error output for details
- `2`: Pre-build validation failed (missing dependencies, invalid spec)
- `3`: Post-build validation failed (binary too large, missing modules)

---

## Input Requirements

### Prerequisites
1. **Python 3.11+** installed and active
2. **PyInstaller 6.x** installed (`pip install pyinstaller>=6.0,<7.0`)
3. **Git** command available (for commit hash extraction)
4. **pyproject.toml** exists at repository root with valid `[project]` section

### File Dependencies
- `scripts/build_binary.spec` - PyInstaller configuration
- `langagent/__main__.py` - Entry point module (must exist and be runnable)
- `pyproject.toml` - Version source

### Environment Variables (Optional)
- `LANGAGENT_VERSION`: Override version (takes precedence over `--version` flag)
- `LANGAGENT_COMMIT`: Override commit hash (takes precedence over `--commit` flag)

---

## Output Guarantees

### Success Case (Exit Code 0)

**Created Files**:
```
dist/
└── langagent          # Single-file executable, Linux x86_64 ELF binary
```

**Binary Properties**:
- File size: < 200MB (target: < 100MB)
- Permissions: Executable (`chmod +x` applied automatically)
- Format: ELF 64-bit LSB executable
- Embedded metadata:
  - Version string from `pyproject.toml`
  - Git commit hash (7-character short form)

**Console Output** (stdout):
```
Building LangAgent binary...
Version: 1.2.3
Commit: a1b2c3d
PyInstaller spec: scripts/build_binary.spec
Entry point: langagent/__main__.py

[PyInstaller output...]

Build completed successfully!
Binary: dist/langagent
Size: 95.3 MB
```

### Failure Case (Exit Code ≠ 0)

**Console Output** (stderr):
```
ERROR: Build failed
Reason: [specific error description]

[Detailed PyInstaller error log]

Missing modules detected:
  - langchain_openai (add to hiddenimports)
  - langgraph.checkpoint.sqlite

Troubleshooting:
  1. Check hiddenimports in scripts/build_binary.spec
  2. Verify all dependencies installed: pip install -r requirements.lock.txt
  3. Run tests: pytest tests/build/test_build_binary.py
```

**Error Categories**:
1. **Import Errors**: PyInstaller cannot find modules → check `hiddenimports`
2. **File Not Found**: Missing entry point or spec file → verify paths
3. **Version Extraction Failed**: Cannot read `pyproject.toml` or git → check file permissions
4. **Post-Build Validation Failed**: Binary size exceeded or modules missing → check excludes list

---

## Validation Steps (Internal)

The script MUST perform these checks before exiting with code 0:

### Pre-Build Validation
1. ✓ PyInstaller installed (`import PyInstaller`)
2. ✓ Spec file exists and is valid Python
3. ✓ Entry point `langagent/__main__.py` exists
4. ✓ `pyproject.toml` parseable and has `project.version`
5. ✓ Git repository detected (or `--commit` provided)

### Post-Build Validation
1. ✓ `dist/langagent` file exists
2. ✓ Binary is executable (has execute permission)
3. ✓ Binary size < 200MB
4. ✓ Binary is valid ELF format (`file dist/langagent` shows "ELF 64-bit")

**Implementation Note**: If any post-build validation fails, the script MUST delete the invalid binary and exit with code 3.

---

## Integration with CI

### GitHub Actions Usage
```yaml
- name: Build binary
  run: python scripts/build_binary.py --clean
  
- name: Check exit code
  if: failure()
  run: |
    echo "Build failed! See logs above."
    exit 1
```

### Expected CI Behavior
- **On success**: CI proceeds to smoke tests
- **On failure**: CI job fails immediately; no artifact uploaded

---

## Error Handling Contract

### Transient Errors (Should Not Occur)
- Disk full during build → Exit code 1, message "Insufficient disk space"
- Permission denied writing to `dist/` → Exit code 1, message "Cannot write to output directory"

### Permanent Errors (Require Code Fix)
- Missing `hiddenimports` → Exit code 1, message lists missing modules
- Spec file syntax error → Exit code 2, message shows Python traceback
- Entry point not found → Exit code 2, message "langagent/__main__.py does not exist"

**Retry Policy**: Build failures due to configuration errors (exit code 1 or 2) SHOULD NOT be retried automatically; human intervention required.

---

## Version Injection Mechanism

### Implementation Requirement
The script MUST inject version and commit hash into the binary so they are:
1. Readable via `strings dist/langagent | grep -E 'v[0-9]+\.[0-9]+\.[0-9]+'`
2. Displayed when running `./dist/langagent --help`

### Injection Method (Reference Implementation)
```python
import os
import subprocess
import tomli

# Read version from pyproject.toml
with open('pyproject.toml', 'rb') as f:
    pyproject = tomli.load(f)
    version = os.getenv('LANGAGENT_VERSION') or pyproject['project']['version']

# Read commit hash
commit = os.getenv('LANGAGENT_COMMIT') or subprocess.check_output(
    ['git', 'rev-parse', '--short=7', 'HEAD'],
    text=True
).strip()

# Write to temporary file for PyInstaller to include
with open('langagent/_build_metadata.py', 'w') as f:
    f.write(f'__version__ = "{version}"\n')
    f.write(f'__commit__ = "{commit}"\n')

# Run PyInstaller (which will package _build_metadata.py)
# ...

# Clean up
os.remove('langagent/_build_metadata.py')
```

---

## Security Requirements

### Secrets Exclusion
The script MUST ensure:
1. `.env` files are NOT included in `datas` section of spec
2. No environment variables containing "KEY" or "SECRET" are logged to stdout
3. Build logs MUST NOT contain API keys (use `***` masking if logging env vars)

### Verification
Post-build check:
```bash
! strings dist/langagent | grep -E '(OPENAI_API_KEY|sk-[a-zA-Z0-9]{32})'
```

If secrets detected → Exit code 3, delete binary, print error.

---

## Performance Requirements

- Build MUST complete within 10 minutes on CI runner (4 CPU, 8GB RAM)
- Build MUST be deterministic (same inputs → same binary size ±1MB variance)
- Build MUST use < 4GB peak memory

---

## Example Usage

### Local Development
```bash
# Clean build with all validations
python scripts/build_binary.py --clean

# Build with custom version (testing)
python scripts/build_binary.py --version 1.2.3-dev

# Build with specific commit (release)
python scripts/build_binary.py --commit abcdef1
```

### CI/CD Pipeline
```bash
# Production build (reads version from pyproject.toml, commit from git)
python scripts/build_binary.py --clean

# If successful, smoke tests run next
bash scripts/smoke_test_binary.sh
```

---

## Contract Compliance Checklist

A compliant implementation MUST:
- [ ] Accept all documented CLI options
- [ ] Exit with documented exit codes
- [ ] Perform all pre-build and post-build validations
- [ ] Inject version and commit hash into binary
- [ ] Exclude secrets from binary
- [ ] Complete within performance limits
- [ ] Produce executable binary < 200MB
- [ ] Output actionable error messages on failure
