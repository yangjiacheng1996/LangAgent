#!/bin/bash
#
# Smoke Test Script for LangAgent Binary
#
# Contract: scripts/smoke_test_binary.sh
# Purpose: Validate packaged binary functionality via end-to-end subprocess invocation
#
# Exit codes:
#   0 - All tests passed
#   1 - One or more tests failed
#   2 - Binary not found or not executable
#   3 - Pre-test setup failed

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

BINARY_PATH="${1:-dist/langagent}"
TEST_DIR="${TEST_DIR:-/tmp/langagent-smoke-tests}"
VERBOSE="${SMOKE_TEST_VERBOSE:-0}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# ============================================================================
# Helper Functions
# ============================================================================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_test_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((TESTS_PASSED++))
}

log_test_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    echo -e "  $2"
    ((TESTS_FAILED++))
}

cleanup() {
    if [ -d "$TEST_DIR" ]; then
        rm -rf "$TEST_DIR"
    fi
}

# ============================================================================
# Pre-Test Validation
# ============================================================================

echo "Running LangAgent Binary Smoke Tests"
echo "Binary: $BINARY_PATH"

# Check binary exists
if [ ! -f "$BINARY_PATH" ]; then
    log_error "Binary not found: $BINARY_PATH"
    exit 2
fi

# Check binary is executable
if [ ! -x "$BINARY_PATH" ]; then
    log_error "Binary not executable: $BINARY_PATH"
    log_error "Run: chmod +x $BINARY_PATH"
    exit 2
fi

# Display binary size
BINARY_SIZE=$(stat -c%s "$BINARY_PATH" 2>/dev/null || stat -f%z "$BINARY_PATH" 2>/dev/null || echo "unknown")
if [ "$BINARY_SIZE" != "unknown" ]; then
    BINARY_SIZE_MB=$((BINARY_SIZE / 1024 / 1024))
    echo "Size: ${BINARY_SIZE_MB} MB"
fi

# Create test directory
if ! mkdir -p "$TEST_DIR"; then
    log_error "Cannot create test directory: $TEST_DIR"
    exit 3
fi

# Register cleanup trap
trap cleanup EXIT

echo ""

# ============================================================================
# Test Suite
# ============================================================================

# T1: Binary Version Display
# ============================================================================
((TESTS_RUN++))
if $BINARY_PATH --help 2>&1 | grep -qE "(LangAgent|version|v[0-9]+\.[0-9]+\.[0-9]+)"; then
    VERSION_OUTPUT=$($BINARY_PATH --help 2>&1 | grep -E "(LangAgent|version)" | head -1 || echo "")
    log_test_pass "T1: Binary version display - $VERSION_OUTPUT"
else
    log_test_fail "T1: Binary version display" \
        "Expected version in --help output"
fi

# T2: Init Command Functionality
# ============================================================================
((TESTS_RUN++))
DEMO_AGENT="$TEST_DIR/demo-agent"
if $BINARY_PATH init "$DEMO_AGENT" >/dev/null 2>&1; then
    if [ -f "$DEMO_AGENT/agent.py" ] && [ -f "$DEMO_AGENT/instructions.md" ]; then
        log_test_pass "T2: Init command functionality"
    else
        log_test_fail "T2: Init command functionality" \
            "agent.py or instructions.md not created"
    fi
else
    log_test_fail "T2: Init command functionality" \
        "init command failed"
fi

# T3: Doctor Command Execution
# ============================================================================
((TESTS_RUN++))
if [ -d "$DEMO_AGENT" ]; then
    cd "$DEMO_AGENT"
    if $BINARY_PATH doctor >/dev/null 2>&1; then
        log_test_pass "T3: Doctor command execution"
    else
        # Doctor may exit with 1 if issues found, but shouldn't crash
        DOCTOR_EXIT=$?
        if [ $DOCTOR_EXIT -eq 1 ]; then
            log_test_pass "T3: Doctor command execution (with warnings)"
        else
            log_test_fail "T3: Doctor command execution" \
                "Doctor crashed with exit code $DOCTOR_EXIT"
        fi
    fi
    cd - >/dev/null
else
    log_test_fail "T3: Doctor command execution" \
        "Demo agent directory not created"
fi

# T4: Run Command Help
# ============================================================================
((TESTS_RUN++))
if $BINARY_PATH run --help >/dev/null 2>&1; then
    log_test_pass "T4: Run command help"
else
    # Some CLI frameworks exit with 2 for --help
    RUN_HELP_EXIT=$?
    if [ $RUN_HELP_EXIT -eq 2 ]; then
        log_test_pass "T4: Run command help"
    else
        log_test_fail "T4: Run command help" \
            "run --help failed with exit code $RUN_HELP_EXIT"
    fi
fi

# T5: Eval Command Help
# ============================================================================
((TESTS_RUN++))
if $BINARY_PATH eval --help >/dev/null 2>&1; then
    log_test_pass "T5: Eval command help"
else
    EVAL_HELP_EXIT=$?
    if [ $EVAL_HELP_EXIT -eq 2 ]; then
        log_test_pass "T5: Eval command help"
    else
        log_test_fail "T5: Eval command help" \
            "eval --help failed with exit code $EVAL_HELP_EXIT"
    fi
fi

# T6: Secret Exclusion Verification
# ============================================================================
((TESTS_RUN++))
if strings "$BINARY_PATH" | grep -qE '(OPENAI_API_KEY|ANTHROPIC_API_KEY|sk-[a-zA-Z0-9]{20,}|key_[a-zA-Z0-9]{20,})'; then
    FOUND_SECRETS=$(strings "$BINARY_PATH" | grep -E '(OPENAI_API_KEY|ANTHROPIC_API_KEY|sk-)' | head -3)
    log_test_fail "T6: Secret exclusion verification" \
        "Found secrets in binary: $FOUND_SECRETS"
else
    log_test_pass "T6: Secret exclusion verification"
fi

# T7: LangSmith Module Exclusion
# ============================================================================
((TESTS_RUN++))
if $BINARY_PATH -c "import sys; sys.exit(0 if 'langsmith' not in sys.modules else 1)" 2>/dev/null; then
    log_test_pass "T7: LangSmith module exclusion"
else
    log_test_fail "T7: LangSmith module exclusion" \
        "langsmith module found in binary (violates Constitutional Article III)"
fi

# T8: Binary Size Constraint
# ============================================================================
((TESTS_RUN++))
MAX_SIZE=$((200 * 1024 * 1024))  # 200MB in bytes
if [ "$BINARY_SIZE" != "unknown" ] && [ "$BINARY_SIZE" -lt "$MAX_SIZE" ]; then
    log_test_pass "T8: Binary size constraint (${BINARY_SIZE_MB} MB < 200 MB)"
else
    if [ "$BINARY_SIZE" = "unknown" ]; then
        log_test_fail "T8: Binary size constraint" \
            "Could not determine binary size"
    else
        EXCESS_MB=$(( (BINARY_SIZE - MAX_SIZE) / 1024 / 1024 ))
        log_test_fail "T8: Binary size constraint" \
            "Binary ${BINARY_SIZE_MB} MB exceeds 200 MB limit by ${EXCESS_MB} MB"
    fi
fi

# T9: Provider Import Validation
# ============================================================================
((TESTS_RUN++))
IMPORT_TEST=$(cat <<'EOF'
import sys
try:
    import langchain_openai
    import langchain_anthropic
    import langchain_google_genai
    import langchain_community
    import langchain_core
    print("SUCCESS")
except ImportError as e:
    print(f"FAIL: {e}")
    sys.exit(1)
EOF
)

if $BINARY_PATH -c "$IMPORT_TEST" 2>&1 | grep -q "SUCCESS"; then
    log_test_pass "T9: Provider import validation"
else
    IMPORT_ERROR=$($BINARY_PATH -c "$IMPORT_TEST" 2>&1 | grep "FAIL" || echo "Unknown error")
    log_test_fail "T9: Provider import validation" \
        "$IMPORT_ERROR"
fi

# T10: Eval Subsystem Import Validation
# ============================================================================
((TESTS_RUN++))
EVAL_TEST=$(cat <<'EOF'
import sys
try:
    from langagent.eval.runner import run_evaluations
    from langagent.eval.task_loader import load_tasks
    from langagent.eval.graders.exact_match import ExactMatchGrader
    print("SUCCESS")
except ImportError as e:
    print(f"FAIL: {e}")
    sys.exit(1)
EOF
)

if $BINARY_PATH -c "$EVAL_TEST" 2>&1 | grep -q "SUCCESS"; then
    log_test_pass "T10: Eval subsystem import validation"
else
    EVAL_ERROR=$($BINARY_PATH -c "$EVAL_TEST" 2>&1 | grep "FAIL" || echo "Unknown error")
    log_test_fail "T10: Eval subsystem import validation" \
        "$EVAL_ERROR"
fi

# ============================================================================
# Test Summary
# ============================================================================

echo ""
echo "========================================"
if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}Result: ALL TESTS PASSED (${TESTS_PASSED}/${TESTS_RUN})${NC}"
    echo "========================================"
    exit 0
else
    echo -e "${RED}Result: TESTS FAILED (${TESTS_PASSED}/${TESTS_RUN} passed)${NC}"
    echo ""
    echo "Failed tests: $TESTS_FAILED"
    echo "========================================"
    exit 1
fi
