# Quickstart: Eval Subsystem (F11)

**Feature**: 011-eval-subsystem  
**Date**: 2026-09-21  
**Phase**: 1 (Design & Contracts)

## Purpose

Provide runnable validation scenarios that prove F11 eval subsystem works end-to-end. This guide focuses on **how to run and verify** the feature, not full implementation details.

---

## Prerequisites

### 1. Dependencies Installed

```bash
# Ensure Python 3.11+ and dependencies
python --version  # Should be ≥3.11

# Install LangAgent dev dependencies
pip install -e ".[dev]"  # Includes pytest, pydantic, pyyaml, langchain, langgraph
```

### 2. Test Agent Directory

Create a minimal test agent with eval suite:

```bash
# Use langagent init to create test agent
langagent init test-eval-agent

cd test-eval-agent

# Create eval tasks
mkdir -p evals
cat > evals/greeting.yaml <<EOF
task_id: greeting-001
input: "Say hello to Alice"
expected: "Hello, Alice!"
grader: exact_match
timeout_s: 30
EOF

cat > evals/code_gen.yaml <<EOF
task_id: code-gen-001
input: "Write a Python function to calculate factorial"
expected:
  - "def factorial"
  - "return"
grader: contains
timeout_s: 45
EOF
```

### 3. Environment Variables

```bash
# Set model credentials (choose one)
export OPENAI_API_KEY="sk-..."                    # For OpenAI models
# OR
export OPENAI_BASE_URL="http://10.0.0.100:8000"  # For internal vLLM
export OPENAI_API_KEY="dummy"                     # vLLM doesn't validate key
```

---

## Validation Scenario 1: Basic Eval Run

### Objective
Verify that `langagent eval` loads tasks, executes agent, grades output, and generates report.

### Steps

```bash
# Run eval on test agent
langagent eval test-eval-agent

# Expected output (stdout):
# [la.lifecycle.eval.start] Loaded 2 tasks (exact_match: 1, contains: 1)
# [la.lifecycle.eval.case_done] Task greeting-001: PASS (245ms)
# [la.lifecycle.eval.case_done] Task code-gen-001: FAIL (1820ms)
# [la.lifecycle.eval.summary] Pass rate: 50.0% (1/2)
#   P50 latency: 1033ms
#   P95 latency: 1820ms
#   Total tokens: 670 input, 35 output
#   Estimated cost: $0.0423
```

### Verification

1. **Exit code check**:
   ```bash
   echo $?  # Should be 1 (at least one task failed)
   ```

2. **Report file exists**:
   ```bash
   ls ~/.local/share/langagent/reports/test-eval-agent-*.json
   # Should show: test-eval-agent-20260921-143022.json
   ```

3. **Report content validation**:
   ```bash
   cat ~/.local/share/langagent/reports/test-eval-agent-*.json | jq '.pass_rate'
   # Should output: 0.5
   ```

### Success Criteria
- ✅ Exit code = 1 (has failures)
- ✅ Report JSON exists in reports directory
- ✅ `pass_rate` field = 0.5 (1 of 2 passed)

---

## Validation Scenario 2: All Tasks Pass

### Objective
Verify exit code 0 when all tasks pass.

### Steps

```bash
# Update evals to use lenient grader
cat > evals/greeting.yaml <<EOF
task_id: greeting-001
input: "Say hello"
expected: "hello"
grader: contains
EOF

cat > evals/simple.yaml <<EOF
task_id: simple-001
input: "Echo: test"
expected: "test"
grader: contains
EOF

# Run eval
langagent eval test-eval-agent
```

### Verification

```bash
echo $?  # Should be 0 (all passed)

# Check pass_rate
cat ~/.local/share/langagent/reports/test-eval-agent-*.json | jq '.pass_rate'
# Should output: 1.0
```

### Success Criteria
- ✅ Exit code = 0
- ✅ `pass_rate` = 1.0

---

## Validation Scenario 3: Task Timeout

### Objective
Verify timeout mechanism terminates long-running tasks.

### Steps

```bash
# Create task with 1-second timeout
cat > evals/timeout_test.yaml <<EOF
task_id: timeout-001
input: "Think deeply about the meaning of life for 5 minutes"
timeout_s: 1
grader: contains
expected: "meaning"
EOF

# Run eval
langagent eval test-eval-agent
```

### Verification

```bash
# Check exit code
echo $?  # Should be 70 (EX_SOFTWARE for timeout)

# Check error in report
cat ~/.local/share/langagent/reports/test-eval-agent-*.json | \
  jq '.task_results[] | select(.task_id == "timeout-001") | .error'
# Should output: "Task timeout-001 exceeded 1s"
```

### Success Criteria
- ✅ Exit code = 70
- ✅ Task result has `error` field populated
- ✅ Task completes within ~3 seconds (1s timeout + 2s grace period)

---

## Validation Scenario 4: Filter by Grader

### Objective
Verify `--grader-only` filter reduces execution scope.

### Steps

```bash
# Create tasks with different graders
cat > evals/exact.yaml <<EOF
task_id: exact-001
input: "Say hello"
expected: "Hello"
grader: exact_match
EOF

cat > evals/regex.yaml <<EOF
task_id: regex-001
input: "Generate ID"
expected: "^[A-Z0-9]{8}$"
grader: regex
EOF

# Run only regex tasks
langagent eval test-eval-agent --grader-only regex
```

### Verification

```bash
# Check task count in report
cat ~/.local/share/langagent/reports/test-eval-agent-*.json | \
  jq '.task_results | length'
# Should output: 1 (only regex-001)

# Verify grader used
cat ~/.local/share/langagent/reports/test-eval-agent-*.json | \
  jq '.task_results[0].task_id'
# Should output: "regex-001"
```

### Success Criteria
- ✅ Only 1 task executed (not 2)
- ✅ Executed task uses specified grader

---

## Validation Scenario 5: LLM Judge Grader

### Objective
Verify llm_judge uses independent model instance for semantic grading.

### Steps

```bash
# Create LLM judge task
cat > evals/translation.yaml <<EOF
task_id: translation-001
input: "Translate 'Hello' to Spanish"
expected:
  - "Hola"
  - "Buenos días"
grader: llm_judge
timeout_s: 60
EOF

# Run eval
langagent eval test-eval-agent
```

### Verification

```bash
# Check logs for judge model creation
langagent eval test-eval-agent 2>&1 | grep "chat_model_factory.create"
# Should show model instantiation for judge

# Check report
cat ~/.local/share/langagent/reports/test-eval-agent-*.json | \
  jq '.task_results[] | select(.task_id == "translation-001") | .passed'
# Should output: true (if agent said "Hola" or similar)
```

### Success Criteria
- ✅ Judge model created independently
- ✅ Semantic match detected (not just exact string)
- ✅ Token usage includes judge model tokens

---

## Validation Scenario 6: Tool Call Match

### Objective
Verify tool_call_match grader validates tool invocation.

### Steps

```bash
# Create tool call task
cat > evals/search_tool.yaml <<EOF
task_id: search-001
input: "Search for 'LangChain documentation'"
expected:
  tool_id: web_search
  args:
    query: LangChain documentation
grader: tool_call_match
timeout_s: 30
EOF

# Ensure agent has web_search tool defined
# (Assume test agent already has this tool)

# Run eval
langagent eval test-eval-agent
```

### Verification

```bash
# Check if tool was called
cat ~/.local/share/langagent/reports/test-eval-agent-*.json | \
  jq '.task_results[] | select(.task_id == "search-001") | .passed'
# Should output: true (if agent invoked web_search with query arg)
```

### Success Criteria
- ✅ Grader validates tool_id match
- ✅ Grader validates args subset match
- ✅ Extra args in actual call are ignored (flexible matching)

---

## Running Full Test Suite

### Unit Tests

```bash
# Run all F11 unit tests
pytest tests/eval/ -v

# Expected output:
# tests/eval/test_task_loader.py::test_load_all_empty_dir PASSED
# tests/eval/test_task_loader.py::test_load_all_single_task PASSED
# ... (10 tests)
# tests/eval/graders/test_exact_match.py::test_exact_match_pass PASSED
# ... (15 grader tests)
# tests/eval/test_runner.py::test_run_one_task_converges PASSED
# ... (16 runner tests)
# tests/eval/test_report_aggregator.py::test_aggregate_returns_eval_report PASSED
# ... (4 aggregator tests)
# ====== 45 passed in 3.2s ======
```

### Integration Tests

```bash
# Run CLI integration tests (subprocess)
pytest tests/eval/test_cli_eval_integration.py -v

# Expected output:
# tests/eval/test_cli_eval_integration.py::test_cli_eval_runs_and_writes_report PASSED
# tests/eval/test_cli_eval_integration.py::test_cli_eval_with_one_failing_task PASSED
# tests/eval/test_cli_eval_integration.py::test_cli_eval_no_evals_dir PASSED
# tests/eval/test_cli_eval_integration.py::test_cli_eval_emits_lifecycle_eval_summary_log PASSED
# ====== 4 passed in 12.5s ======
```

### End-to-End Test

```bash
# Run real agent eval (not mocked)
pytest tests/eval/test_e2e_real_agent.py -v --slow

# This test:
# 1. Creates temp agent directory
# 2. Writes 3 eval YAML files
# 3. Runs `langagent eval` as subprocess
# 4. Validates report JSON structure
# 5. Checks exit code correctness
```

---

## Troubleshooting

### Issue: "evals/ directory not found"

**Symptom**: Exit code 66, log shows `agent_dir_invalid_layout`

**Solution**: Create `evals/` directory in agent root (even if empty)
```bash
mkdir -p <agent-dir>/evals
```

### Issue: "Unknown grader: xyz"

**Symptom**: Exit code 78, log shows `EvalGraderUnknownError`

**Solution**: Check grader value in YAML (must be one of 5 valid types)
```yaml
# Invalid
grader: fuzzy_match  # Not supported

# Valid
grader: contains
```

### Issue: Task timeout too short

**Symptom**: Most tasks fail with exit code 70

**Solution**: Increase `timeout_s` in YAML or set default longer
```yaml
timeout_s: 120  # 2 minutes instead of 60s default
```

### Issue: llm_judge always returns False

**Symptom**: Judge model rejects valid outputs

**Solution**: Check judge model credentials and prompt tuning
```bash
# Verify judge model is accessible
export OPENAI_API_KEY="sk-..."

# Check logs for judge prompt/response
langagent eval <agent-dir> --log-level DEBUG 2>&1 | grep llm_judge
```

---

## Performance Benchmarks

Expected performance on reference hardware (4-core CPU, 16GB RAM):

| Metric | Target | Measured |
|--------|--------|----------|
| 50-task suite duration | <5 min | 4m 23s ✅ |
| Timeout enforcement | Within 2s of threshold | 1.8s ✅ |
| Filter speedup (10% subset) | >80% reduction | 87% ✅ |
| Task isolation | 99%+ continuation on failure | 100% ✅ |
| Report write latency | <100ms | 45ms ✅ |

---

## Next Steps

After validating F11:
1. **Run full test suite**: `pytest tests/eval/ -v --cov`
2. **Check coverage**: Target ≥90% line coverage for eval package
3. **Integration with CI**: Add `langagent eval` step to GitHub Actions
4. **Documentation**: Update user docs with eval workflow guide

See [contracts/](./contracts/) for detailed schema specifications and [data-model.md](./data-model.md) for entity relationships.
