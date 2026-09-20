# Quickstart: Exit Cleanup & Doctor Self-Check Validation

**Feature**: F09 Exit Cleanup & Doctor Self-Check  
**Created**: 2026-09-20  
**Related**: [spec.md](./spec.md), [plan.md](./plan.md), [data-model.md](./data-model.md)

## Overview

This quickstart provides runnable validation scenarios that prove F09 works end-to-end. Each scenario includes prerequisites, setup commands, test/run commands, and expected outcomes. These scenarios validate the 5 user stories and critical edge cases from the spec.

**Prerequisites**:
- Python 3.11+ installed
- Repository cloned and dependencies installed (`pip install -e .`)
- Test agent directory created (`langagent init test-agent`)

---

## Scenario 1: Doctor Check with Invalid Model Endpoint

**Validates**: User Story 2 (Doctor Self-Check Reporting), FR-011, SC-004

**Objective**: Verify that `langagent doctor` detects unreachable model endpoint and writes DoctorReport with status="error" for check_model.

### Setup

```bash
# Create test agent directory
cd /tmp
langagent init test-agent
cd test-agent

# Configure invalid model endpoint in .env
cat > .env << 'EOF'
MODEL_PROVIDER=openai-compatible
MODEL_BASE_URL=http://invalid-endpoint.local:8000/v1
MODEL_NAME=invalid-model
EOF
```

### Run

```bash
langagent doctor
```

### Expected Output

```
Running doctor checks...
[✗] model: error - Connection timeout to http://invalid-endpoint.local:8000/v1
[✓] checkpointer: ok - MemorySaver initialized successfully
[✓] skills: ok - No skills configured
[✓] instructions: ok - Instructions valid (142 characters)

Overall status: ERROR

Report written to: ~/.local/share/langagent/reports/doctor-2026-09-20T14:30:22.json
```

### Verify Report

```bash
# Check report file exists
ls -lh ~/.local/share/langagent/reports/doctor-*.json

# Verify JSON structure
cat ~/.local/share/langagent/reports/doctor-*.json | jq '.'
```

**Expected JSON** (partial):
```json
{
  "report_id": "550e8400-e29b-41d4-a716-446655440000",
  "generated_at": "2026-09-20T14:30:22Z",
  "checks": [
    {
      "check_name": "model",
      "status": "error",
      "detail": "Connection timeout to http://invalid-endpoint.local:8000/v1"
    },
    {
      "check_name": "checkpointer",
      "status": "ok",
      "detail": "MemorySaver initialized successfully"
    },
    {
      "check_name": "skills",
      "status": "ok",
      "detail": "No skills configured"
    },
    {
      "check_name": "instructions",
      "status": "ok",
      "detail": "Instructions valid (142 characters)"
    }
  ],
  "overall": "error",
  "agent_dir": "/tmp/test-agent",
  "runtime": {
    "schema_version": "v0.2.0",
    "model_provider": "openai-compatible",
    "model_name": "invalid-model",
    "model_base_url": "http://invalid-endpoint.local:8000/v1",
    "checkpointer": "memory",
    "middleware_ids": [],
    "skill_dirs": [],
    "log_level": "INFO",
    "guardrail_allow_internal_endpoints": true
  }
}
```

### Success Criteria

- ✅ Doctor command completes without crashing
- ✅ Report file created at expected path
- ✅ `checks[0].status == "error"` (model check failed)
- ✅ `overall == "error"`
- ✅ `runtime.model` field does NOT exist (excluded from snapshot)
- ✅ Exit code is non-zero (model check error)

---

## Scenario 2: Cleanup Continues After Audit Flush Failure

**Validates**: User Story 4 (Continue-on-Failure), FR-003, SC-002

**Objective**: Verify that cleanup continues after audit_recorder.flush() fails, and returns exit code 4 (I/O error).

### Setup

```python
# Create test script: test_continue_on_failure.py
import sys
sys.path.insert(0, '/path/to/langagent')

from langagent.runtime.exit_handler import RuntimeExitHandler
from langagent.runtime.agent_state import AgentState
from langagent.runtime.config import RuntimeConfig
from unittest.mock import Mock, patch

# Mock F04 audit_recorder to raise exception
def mock_audit_flush():
    from langagent.cross_cutting.audit_recorder import AuditFlushError
    raise AuditFlushError("Disk full: cannot write audit.jsonl")

# Mock other dependencies
with patch('langagent.cross_cutting.audit_recorder.flush', side_effect=mock_audit_flush):
    with patch('langagent.protocol.event_bus.flush'):
        with patch('langagent.cross_cutting.metrics_collector.flush'):
            with patch('langagent.primitives.checkpoint_adapter.close'):
                with patch('langagent.cross_cutting.metrics_collector.snapshot'):
                    with patch('langagent.cross_cutting.logger.drain_spans', return_value=[]):
                        with patch('langagent.protocol.event_bus.drain_events', return_value=[]):
                            
                            # Create minimal state and config
                            state = AgentState(messages=[], todos=[], files={}, context={}, scratchpad={})
                            config = RuntimeConfig(
                                model_provider="openai",
                                checkpointer="memory",
                                middleware_ids=[],
                                skill_dirs=[]
                            )
                            
                            # Run cleanup
                            handler = RuntimeExitHandler()
                            exit_code = handler.cleanup(state, config)
                            
                            print(f"Exit code: {exit_code}")
                            print("Expected: 4 (I/O error from audit flush failure)")
                            print(f"Result: {'PASS' if exit_code == 4 else 'FAIL'}")
                            
                            # Verify other steps still executed
                            # (check mock call counts)
```

### Run

```bash
python test_continue_on_failure.py
```

### Expected Output

```
Exit code: 4
Expected: 4 (I/O error from audit flush failure)
Result: PASS
```

### Success Criteria

- ✅ Cleanup does not crash (exception caught and recorded)
- ✅ Exit code == 4 (I/O error has priority over other failures)
- ✅ Subsequent steps (checkpointer.close, snapshot, write_reports) were attempted
- ✅ `la.runtime.exit_cleanup.fail` log emitted
- ✅ Final exit code returned to caller

---

## Scenario 3: Init-Only Cleanup Mode Performance

**Validates**: User Story 5 (Init-Only Cleanup Mode), FR-021, SC-008

**Objective**: Verify that cleanup(init_only=True) skips steps 1-8, emits lifecycle.init.end log, and completes in < 100ms.

### Setup

```python
# Create test script: test_init_only_cleanup.py
import sys
import time
sys.path.insert(0, '/path/to/langagent')

from langagent.runtime.exit_handler import RuntimeExitHandler

# Run cleanup in init-only mode
handler = RuntimeExitHandler()

start_time = time.perf_counter()
exit_code = handler.cleanup(state=None, config=None, init_only=True)
duration_ms = (time.perf_counter() - start_time) * 1000

print(f"Exit code: {exit_code}")
print(f"Duration: {duration_ms:.2f} ms")
print(f"Performance: {'PASS' if duration_ms < 100 else 'FAIL'} (target: < 100ms)")
```

### Run

```bash
python test_init_only_cleanup.py
```

### Expected Output

```
Exit code: 0
Duration: 12.34 ms
Performance: PASS (target: < 100ms)
```

### Verify Logs

```bash
# Check that la.lifecycle.init.end was emitted
tail -f ~/.local/share/langagent/logs/langagent.log | grep "la.lifecycle.init.end"
```

**Expected Log**:
```
2026-09-20T14:30:22Z [INFO] la.lifecycle.init.end agent_init_completed
```

### Success Criteria

- ✅ Exit code == 0 (success)
- ✅ Duration < 100ms
- ✅ `la.lifecycle.init.end` log emitted
- ✅ `la.runtime.exit_cleanup.ok` log emitted
- ✅ No exceptions raised
- ✅ Steps 1-8 skipped (event_bus.flush, metrics.flush, audit.flush, checkpointer.close, snapshot, drain_spans, drain_events, write_reports)

---

## Scenario 4: Report Routing Priority (Eval > Doctor)

**Validates**: Edge case (eval_report and doctor_report both provided), FR-017

**Objective**: Verify that when both eval_report and doctor_report are provided to cleanup(), eval_report takes precedence.

### Setup

```python
# Create test script: test_report_routing.py
import sys
from datetime import datetime
sys.path.insert(0, '/path/to/langagent')

from langagent.runtime.exit_handler import RuntimeExitHandler
from langagent.runtime.agent_state import AgentState
from langagent.runtime.config import RuntimeConfig
from langagent.eval.report_aggregator import EvalReport
from langagent.runtime.doctor_check import DoctorReport, DoctorCheckResult
from langagent.runtime.config_snapshot import RuntimeConfigSnapshot

# Create both reports
eval_report = EvalReport(
    report_id="eval-550e8400",
    generated_at=datetime.utcnow(),
    agent_dir="/tmp/test-agent",
    task_results=[{"task_id": "t1", "passed": True}],
    pass_rate=1.0,
    p50_latency_ms=123.4,
    p95_latency_ms=456.7,
    token_usage={"gpt-4o": 1000},
    cost_usd=0.05
)

doctor_report = DoctorReport(
    report_id="doctor-660e9500",
    generated_at=datetime.utcnow(),
    checks=[
        DoctorCheckResult(check_name="model", status="ok", detail="OK"),
        DoctorCheckResult(check_name="checkpointer", status="ok", detail="OK"),
        DoctorCheckResult(check_name="skills", status="ok", detail="OK"),
        DoctorCheckResult(check_name="instructions", status="ok", detail="OK")
    ],
    overall="ok",
    agent_dir="/tmp/test-agent",
    runtime=RuntimeConfigSnapshot(
        model_provider="openai",
        checkpointer="memory",
        middleware_ids=[],
        skill_dirs=[]
    )
)

# Run cleanup with both reports
state = AgentState(messages=[], todos=[], files={}, context={}, scratchpad={})
config = RuntimeConfig(model_provider="openai", checkpointer="memory", middleware_ids=[], skill_dirs=[])

handler = RuntimeExitHandler()
exit_code = handler.cleanup(state, config, eval_report=eval_report, doctor_report=doctor_report)

print(f"Exit code: {exit_code}")
print("Check that only EvalReport was written (not DoctorReport)")
```

### Run

```bash
python test_report_routing.py
ls -lh ~/.local/share/langagent/reports/
```

### Expected Output

```
Exit code: 0
Check that only EvalReport was written (not DoctorReport)

# File listing shows:
-rw-r--r-- 1 user user 1.2K Sep 20 14:30 test-agent-2026-09-20T14:30:22.json
# (no doctor-*.json file created)
```

### Success Criteria

- ✅ Exit code == 0
- ✅ EvalReport file created: `test-agent-<timestamp>.json`
- ✅ DoctorReport file NOT created (routing priority respected)
- ✅ EvalReport contains expected fields (pass_rate, p50_latency_ms, token_usage)

---

## Scenario 5: Zero-Valued MetricsSnapshot Fallback

**Validates**: Edge case (metrics_collector.snapshot() fails), FR-005

**Objective**: Verify that when metrics_collector.snapshot() fails, cleanup writes zero-valued MetricsSnapshot and returns exit code 70.

### Setup

```python
# Create test script: test_zero_metrics_fallback.py
import sys
sys.path.insert(0, '/path/to/langagent')

from langagent.runtime.exit_handler import RuntimeExitHandler
from langagent.runtime.agent_state import AgentState
from langagent.runtime.config import RuntimeConfig
from unittest.mock import Mock, patch

# Mock metrics_collector.snapshot() to raise exception
def mock_snapshot_failure():
    raise RuntimeError("MetricsCollector internal error")

with patch('langagent.cross_cutting.metrics_collector.snapshot', side_effect=mock_snapshot_failure):
    with patch('langagent.protocol.event_bus.flush'):
        with patch('langagent.cross_cutting.metrics_collector.flush'):
            with patch('langagent.cross_cutting.audit_recorder.flush'):
                with patch('langagent.primitives.checkpoint_adapter.close'):
                    with patch('langagent.cross_cutting.logger.drain_spans', return_value=[]):
                        with patch('langagent.protocol.event_bus.drain_events', return_value=[]):
                            
                            state = AgentState(messages=[], todos=[], files={}, context={}, scratchpad={})
                            config = RuntimeConfig(
                                model_provider="openai",
                                checkpointer="memory",
                                middleware_ids=[],
                                skill_dirs=[]
                            )
                            
                            handler = RuntimeExitHandler()
                            exit_code = handler.cleanup(state, config)
                            
                            print(f"Exit code: {exit_code}")
                            print("Expected: 70 (EX_SOFTWARE from snapshot failure)")
                            print(f"Result: {'PASS' if exit_code == 70 else 'FAIL'}")
```

### Run

```bash
python test_zero_metrics_fallback.py
```

### Expected Output

```
Exit code: 70
Expected: 70 (EX_SOFTWARE from snapshot failure)
Result: PASS
```

### Verify Report

```bash
# Check that report was still written with zero-valued fields
cat ~/.local/share/langagent/reports/*.json | jq '.token_usage, .latency_ms, .cost_usd'
```

**Expected**:
```json
{}
[]
0.0
```

### Success Criteria

- ✅ Exit code == 70 (EX_SOFTWARE)
- ✅ Report file created (write_reports did not skip)
- ✅ MetricsSnapshot contains zero values:
  - `token_usage == {}`
  - `latency_ms == []`
  - `cost_usd == 0.0`
  - `turn_count == 0`

---

## End-to-End Integration Test

**Validates**: All 5 user stories together

### Setup

```bash
# Create test agent with valid configuration
cd /tmp
langagent init integration-test-agent
cd integration-test-agent

# Configure valid OpenAI endpoint (requires API key)
cat > .env << 'EOF'
MODEL_PROVIDER=openai
MODEL_NAME=gpt-4o-mini
OPENAI_API_KEY=sk-...
EOF

# Add sample skill with valid frontmatter
mkdir -p skills/sample_skill
cat > skills/sample_skill/SKILL.md << 'EOF'
---
name: sample_skill
version: 1.0.0
description: Sample skill for testing
---

This is a sample skill.
EOF
```

### Run Full Workflow

```bash
# 1. Run doctor checks (should pass)
langagent doctor
echo "Doctor exit code: $?"

# 2. Run agent (triggers cleanup)
echo "Hello, test agent" | langagent run
echo "Run exit code: $?"

# 3. Verify reports written
ls -lh ~/.local/share/langagent/reports/
ls -lh ~/.local/share/langagent/logs/
```

### Expected Output

```
# Doctor output
[✓] model: ok - Connected to OpenAI gpt-4o-mini
[✓] checkpointer: ok - MemorySaver initialized
[✓] skills: ok - Found 1 skill: sample_skill
[✓] instructions: ok - Instructions valid (142 characters)
Overall status: OK
Doctor exit code: 0

# Run output
> Hello, test agent
< Hello! How can I help you today?
Run exit code: 0

# File listing
reports/
  doctor-2026-09-20T14:30:22.json
  integration-test-agent-2026-09-20T14:31:45.json

logs/
  550e8400-e29b-41d4-a716-446655440000.jsonl
```

### Verify JSONL Format

```bash
# Check spans are grep-able (one per line)
grep -c '"span_id"' ~/.local/share/langagent/logs/*.jsonl
# Output: 5 (example count)

# Check 7 required fields present
head -1 ~/.local/share/langagent/logs/*.jsonl | jq 'keys'
# Output: ["attributes", "end", "name", "parent_span_id", "span_id", "start", "trace_id"]
```

### Success Criteria

- ✅ Doctor checks pass with valid configuration
- ✅ Agent run completes successfully
- ✅ DoctorReport written with overall="ok"
- ✅ MetricsSnapshot written after run
- ✅ Span JSONL file created with 7 fields per line
- ✅ All exit codes == 0
- ✅ No resource leaks (checkpointer connections closed)

---

## Troubleshooting

### Issue: Doctor checks timeout

**Symptom**: `langagent doctor` hangs for > 30 seconds

**Cause**: Model endpoint unreachable, no timeout configured

**Fix**: Set shorter timeout in probe functions (5s default)

### Issue: Report file permission denied

**Symptom**: `PermissionError: [Errno 13] Permission denied: '~/.local/share/langagent/reports/doctor-*.json'`

**Cause**: `~/.local/share/langagent/` directory does not exist or has wrong permissions

**Fix**:
```bash
mkdir -p ~/.local/share/langagent/reports
mkdir -p ~/.local/share/langagent/logs
chmod 755 ~/.local/share/langagent
```

### Issue: Init-only cleanup takes > 100ms

**Symptom**: Performance test fails (duration > 100ms)

**Cause**: Slow imports (event_bus, metrics_collector loaded even when skipped)

**Fix**: Profile import time with `python -X importtime`, lazy-load heavy modules

### Issue: JSONL corruption (multi-line records)

**Symptom**: `grep` returns incorrect counts, `jq` fails to parse

**Cause**: Missing file lock during concurrent writes

**Fix**: Verify `fcntl.flock()` is applied before append operations (see research.md §2)

---

## Next Steps

After validating these 5 scenarios:

1. Run full test suite: `pytest tests/runtime/test_exit_handler.py -v`
2. Check test coverage: `pytest --cov=langagent.runtime.exit_handler --cov-report=html`
3. Profile init-only performance: `python -m cProfile -o cleanup.prof test_init_only_cleanup.py`
4. Verify no resource leaks: `lsof -p $(pgrep langagent)` before/after cleanup
5. Review logs for unexpected warnings: `grep -E "WARN|ERROR" ~/.local/share/langagent/logs/langagent.log`

**Ready for Phase 2**: Once all scenarios pass, proceed to `/speckit.tasks` for task breakdown and TDD implementation.
