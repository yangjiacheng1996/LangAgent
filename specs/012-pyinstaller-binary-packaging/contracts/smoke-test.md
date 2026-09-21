# Contract: Smoke Test Script

**File**: `scripts/smoke_test_binary.sh`  
**Type**: Bash Script  
**Purpose**: Validate packaged binary functionality via end-to-end subprocess invocation.

---

## Command-Line Interface

### Invocation
```bash
bash scripts/smoke_test_binary.sh [OPTIONS]
```

### Options
- `--binary PATH`: Path to binary to test (default: `dist/langagent`)
- `--verbose`: Print detailed output for each test (default: false)
- `--stop-on-failure`: Exit immediately on first failure (default: true)
- `--test-dir DIR`: Temporary directory for test artifacts (default: `/tmp/langagent-smoke-tests`)

### Exit Codes
- `0`: All smoke tests passed
- `1`: One or more smoke tests failed
- `2`: Binary not found or not executable
- `3`: Pre-test setup failed (cannot create test directory, etc.)

---

## Input Requirements

### Prerequisites
1. **Binary artifact** exists at specified path (default: `dist/langagent`)
2. **Write access** to test directory (default: `/tmp`)
3. **Shell utilities** available: `grep`, `stat`, `strings`, `file`

### Environment Variables (Optional)
- `BINARY_PATH`: Override default binary path
- `SMOKE_TEST_VERBOSE`: Set to "1" for verbose output

---

## Test Suite Definition

### T1: Binary Version Display
**Purpose**: Verify version and commit hash are embedded and displayed.

**Command**:
```bash
$BINARY --help
```

**Success Criteria**:
- Exit code: 0
- Output contains: `LangAgent v` followed by semver pattern (e.g., "v1.2.3")
- Output contains: `commit` followed by 7-character hash (e.g., "commit a1b2c3d")

**Failure Output**:
```
FAIL: Binary version display
  Expected: "LangAgent v[0-9]+\.[0-9]+\.[0-9]+ (commit [a-f0-9]{7})"
  Actual: [captured output]
```

---

### T2: Init Command Functionality
**Purpose**: Verify `langagent init` creates agent directory structure.

**Command**:
```bash
$BINARY init $TEST_DIR/demo-agent
```

**Success Criteria**:
- Exit code: 0
- Directory created: `$TEST_DIR/demo-agent/`
- Files exist:
  - `agent.py`
  - `instructions.md`
  - `pyproject.toml`
  - `.env` (or `.env.example`)
- Directories exist:
  - `tools/`
  - `skills/`
  - `middleware/`

**Failure Output**:
```
FAIL: Init command functionality
  Missing files: agent.py, instructions.md
  Created directory: /tmp/langagent-smoke-tests/demo-agent
  Contents: [ls output]
```

---

### T3: Doctor Command Execution
**Purpose**: Verify `langagent doctor` runs diagnostic checks.

**Command**:
```bash
cd $TEST_DIR/demo-agent && $BINARY doctor
```

**Success Criteria**:
- Exit code: 0 or 1 (may warn about missing .env, but should not crash)
- Output contains at least one diagnostic message
- No Python tracebacks in output

**Failure Output**:
```
FAIL: Doctor command execution
  Exit code: 139 (segfault)
  Output: [captured stderr]
```

---

### T4: Run Command Help
**Purpose**: Verify `langagent run --help` displays usage information.

**Command**:
```bash
$BINARY run --help
```

**Success Criteria**:
- Exit code: 0
- Output contains: "usage:" or "Usage:"
- Output mentions: `--max-turns` or similar CLI options

**Failure Output**:
```
FAIL: Run command help
  Exit code: 2
  Output: [captured output]
```

---

### T5: Eval Command Help
**Purpose**: Verify `langagent eval --help` displays usage information.

**Command**:
```bash
$BINARY eval --help
```

**Success Criteria**:
- Exit code: 0
- Output contains: "usage:" or "Usage:"
- Output mentions: evaluation-related options

**Failure Output**:
```
FAIL: Eval command help
  Exit code: 127 (command not found)
  Possible cause: F11 eval subsystem not packaged
```

---

### T6: Secret Exclusion Verification
**Purpose**: Verify no secrets leaked into binary.

**Command**:
```bash
strings $BINARY | grep -E '(OPENAI_API_KEY|ANTHROPIC_API_KEY|sk-[a-zA-Z0-9]{20,}|key_[a-zA-Z0-9]{20,})'
```

**Success Criteria**:
- Exit code: 1 (grep found no matches)
- No output

**Failure Output**:
```
FAIL: Secret exclusion verification
  Found secrets in binary:
    OPENAI_API_KEY=sk-test1234567890
  Use: strings dist/langagent | grep -E '(OPENAI_API_KEY|sk-)' to debug
```

---

### T7: LangSmith Module Exclusion
**Purpose**: Verify LangSmith modules are not packaged.

**Command**:
```bash
$BINARY -c "import sys; sys.exit(0 if 'langsmith' not in sys.modules else 1)" 2>/dev/null
```

**Success Criteria**:
- Exit code: 0 (langsmith not in sys.modules)

**Failure Output**:
```
FAIL: LangSmith module exclusion
  langsmith module found in binary
  Violates Constitutional Article III
  Check excludes list in scripts/build_binary.spec
```

---

### T8: Binary Size Constraint
**Purpose**: Verify binary size is under 200MB.

**Command**:
```bash
stat -c%s $BINARY
```

**Success Criteria**:
- Output value < 209715200 (200MB in bytes)

**Failure Output**:
```
FAIL: Binary size constraint
  Expected: < 200 MB
  Actual: 235 MB
  Exceeds limit by: 35 MB
  Suggestions:
    - Check excludes list (tkinter, matplotlib, numpy.tests)
    - Review hiddenimports for over-inclusion
```

---

### T9: Provider Import Validation
**Purpose**: Verify all 6 LangChain provider packages are importable.

**Command**:
```bash
$BINARY -c "
import langchain_openai
import langchain_anthropic
import langchain_google_genai
import langchain_community
import langchain_core
print('All providers imported successfully')
"
```

**Success Criteria**:
- Exit code: 0
- Output contains: "All providers imported successfully"

**Failure Output**:
```
FAIL: Provider import validation
  ModuleNotFoundError: No module named 'langchain_anthropic'
  Missing provider: langchain_anthropic
  Add to hiddenimports in scripts/build_binary.spec
```

---

### T10: Eval Subsystem Import Validation
**Purpose**: Verify F11 eval modules are packaged.

**Command**:
```bash
$BINARY -c "
from langagent.eval.runner import run
from langagent.eval.graders.exact_match import grade
print('Eval subsystem loaded')
"
```

**Success Criteria**:
- Exit code: 0
- Output contains: "Eval subsystem loaded"

**Failure Output**:
```
FAIL: Eval subsystem import validation
  ModuleNotFoundError: No module named 'langagent.eval.runner'
  F11 eval modules not packaged
  Verify hiddenimports includes langagent.eval.* modules
```

---

## Output Format

### Success Case (All Tests Pass)
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
[PASS] T8: Binary size constraint (95 MB < 200 MB)
[PASS] T9: Provider import validation
[PASS] T10: Eval subsystem import validation

========================================
Result: ALL TESTS PASSED (10/10)
Duration: 4.2 seconds
========================================
```

### Failure Case (One or More Tests Fail)
```
Running LangAgent Binary Smoke Tests
Binary: dist/langagent (235.7 MB)

[PASS] T1: Binary version display
[PASS] T2: Init command functionality
[FAIL] T3: Doctor command execution
  Exit code: 1
  Error: ModuleNotFoundError: No module named 'langchain_core.runnables'
[PASS] T4: Run command help
[PASS] T5: Eval command help
[PASS] T6: Secret exclusion verification
[PASS] T7: LangSmith module exclusion
[FAIL] T8: Binary size constraint (235 MB > 200 MB)
[PASS] T9: Provider import validation
[PASS] T10: Eval subsystem import validation

========================================
Result: TESTS FAILED (8/10 passed)
Duration: 3.8 seconds

Failed Tests:
  - T3: Doctor command execution
  - T8: Binary size constraint

See above for details.
========================================
```

---

## Integration with CI

### GitHub Actions Usage
```yaml
- name: Run smoke tests
  run: bash scripts/smoke_test_binary.sh --binary dist/langagent
  
- name: Upload smoke test results
  if: failure()
  uses: actions/upload-artifact@v3
  with:
    name: smoke-test-failure-logs
    path: /tmp/langagent-smoke-tests/
```

### CI Behavior
- **All tests pass**: CI proceeds to artifact upload
- **Any test fails**: CI job fails; no artifact uploaded (per Clarification Q5)

---

## Performance Requirements

- Smoke tests MUST complete within 5 minutes
- Each individual test SHOULD complete within 30 seconds
- Test directory cleanup MUST occur even if tests fail

---

## Error Handling Contract

### Pre-Test Failures (Exit Code 2-3)
- Binary not found → Exit 2, message "Binary not found: dist/langagent"
- Binary not executable → Exit 2, message "Binary not executable (chmod +x required?)"
- Cannot create test directory → Exit 3, message "Permission denied: /tmp"

### Test Failures (Exit Code 1)
- Any test fails → Exit 1 after running all tests (unless `--stop-on-failure`)
- Output shows which tests failed and provides actionable debugging hints

**Non-Transient Failures**: All test failures indicate build/packaging issues requiring code/config changes; DO NOT retry automatically.

---

## Cleanup Behavior

The script MUST clean up test artifacts:
```bash
# At script exit (trap)
rm -rf $TEST_DIR/demo-agent
rm -f /tmp/langagent-test-*.log
```

Even if tests fail or script is interrupted (SIGINT), cleanup MUST run.

---

## Contract Compliance Checklist

A compliant implementation MUST:
- [ ] Run all 10 tests (T1-T10)
- [ ] Exit with documented exit codes
- [ ] Produce structured output (pass/fail per test)
- [ ] Provide actionable failure messages
- [ ] Complete within 5 minutes
- [ ] Clean up test artifacts on exit
- [ ] Block CI on any test failure (exit code 1)
- [ ] Validate all Constitutional requirements (Articles III, X)
