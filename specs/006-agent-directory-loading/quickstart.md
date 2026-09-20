# Quickstart: Agent Directory Loading (dir_load Stage)

This guide provides validation scenarios for the agent directory loading feature.

## Prerequisites

- Python 3.10+
- LangAgent installed
- Virtual environment activated

## Scenario 1: Generate and Load Template

**Purpose**: Verify template generation and directory loading work end-to-end

```bash
# Create a new agent from template
cd /tmp
python -c "
from langagent.runtime.dir_loader import RuntimeDirLoader
RuntimeDirLoader.write_template('.', 'demo-agent')
"

# Verify structure
ls -la demo-agent/
# Expected output:
# instructions.md
# agent.py
# pyproject.toml
# .env.example
# skills/
# tools/
# middleware/

# Load the generated agent
python -c "
from langagent.runtime.dir_loader import RuntimeDirLoader
loaded = RuntimeDirLoader.load('demo-agent')
print(f'Agent loaded: {loaded.agent_dir}')
print(f'Instructions length: {len(loaded.instructions)}')
print(f'Tools: {loaded.tool_ids}')
print(f'Skills: {loaded.skill_names}')
"

# Expected output:
# Agent loaded: /tmp/demo-agent
# Instructions length: >0
# Tools: ['example_tool']
# Skills: ['example_skill']
```

**Success Criteria** (SC-001, SC-003):
- Template generation completes in <5 seconds
- Directory loading completes in <100ms
- All mandatory and example files exist
- LoadedAgent has 5 fields (no compiled_graph)

---

## Scenario 2: Load Minimal Agent

**Purpose**: Verify minimal agent support (only 3 mandatory files)

```bash
# Create minimal agent
mkdir -p /tmp/minimal-agent
cat > /tmp/minimal-agent/instructions.md << 'EOF'
You are a minimal test agent.
EOF

cat > /tmp/minimal-agent/agent.py << 'EOF'
from typing import TypedDict
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    messages: list[BaseMessage]
    todos: list[str]
    files: dict[str, str]
    context: dict[str, str]
    scratchpad: str
EOF

cat > /tmp/minimal-agent/pyproject.toml << 'EOF'
[project]
name = "minimal-agent"
version = "0.1.0"
EOF

# Load minimal agent
python -c "
from langagent.runtime.dir_loader import RuntimeDirLoader
loaded = RuntimeDirLoader.load('/tmp/minimal-agent')
print(f'Tool IDs: {loaded.tool_ids}')
print(f'Skill names: {loaded.skill_names}')
assert loaded.tool_ids == []
assert loaded.skill_names == []
print('✓ Minimal agent loaded successfully')
"
```

**Success Criteria** (SC-008):
- Minimal agent with only 3 files loads successfully
- Empty tool_ids and skill_names lists returned

---

## Scenario 3: Stage Guard Violation Detection

**Purpose**: Verify stage boundary enforcement prevents cross-stage operations

```python
# test_stage_guard.py
from langagent.cross_cutting.stage_guard import (
    cross_cutting_stage_guard_decorator,
    StageCapabilityViolationError
)

class MockModel:
    def __init__(self):
        self.initialized = True

@cross_cutting_stage_guard_decorator(
    'dir_load',
    monkeypatch_blacklist=[MockModel]
)
def test_no_model_instantiation():
    # This should raise StageCapabilityViolationError
    model = MockModel()
    return model

try:
    test_no_model_instantiation()
    print("✗ FAILED: Should have raised StageCapabilityViolationError")
except StageCapabilityViolationError as e:
    print(f"✓ PASSED: Stage guard blocked operation")
    print(f"  Stage: {e.stage_name}")
    print(f"  Target: {e.target}")
    print(f"  Operation: {e.operation}")
```

**Success Criteria** (SC-006, SC-009):
- Stage guard overhead <10ms
- Blocked operations raise StageCapabilityViolationError with exit code 1
- Error message includes stage_name, target, operation

---

## Scenario 4: Idempotent Template Generation

**Purpose**: Verify write_template validates and recreates invalid files

```bash
# Create agent
python -c "
from langagent.runtime.dir_loader import RuntimeDirLoader
RuntimeDirLoader.write_template('/tmp', 'test-agent')
"

# Corrupt instructions.md
echo "INVALID CONTENT" > /tmp/test-agent/instructions.md

# Regenerate (should detect and fix)
python -c "
from langagent.runtime.dir_loader import RuntimeDirLoader
RuntimeDirLoader.write_template('/tmp', 'test-agent')
"

# Verify recreation
python -c "
content = open('/tmp/test-agent/instructions.md').read()
assert 'INVALID CONTENT' not in content
assert len(content) > 0
print('✓ Idempotent regeneration successful')
"
```

**Success Criteria** (SC-007):
- Invalid files detected via validation functions
- Corrupted files deleted and recreated
- No hardcoded paths in generated templates (portability)

---

## Error Validation

### Test 1: Missing Directory

```python
from langagent.runtime.dir_loader import RuntimeDirLoader, AgentDirNotFoundError

try:
    RuntimeDirLoader.load("/nonexistent/path")
except AgentDirNotFoundError as e:
    print(f"✓ Exit code 66: {e}")
```

### Test 2: Missing Mandatory Files

```python
from langagent.runtime.dir_loader import RuntimeDirLoader, AgentDirInvalidLayoutError

try:
    RuntimeDirLoader.load("/path/to/broken/agent")
except AgentDirInvalidLayoutError as e:
    print(f"✓ Exit code 65: Missing files: {e.missing_files}")
```

### Test 3: Instructions Read Error

```python
from langagent.runtime.dir_loader import RuntimeDirLoader, InstructionsReadError
import os

# Create agent with unreadable instructions
os.makedirs("/tmp/broken/agent", exist_ok=True)
open("/tmp/broken/agent/instructions.md", "w").close()
os.chmod("/tmp/broken/agent/instructions.md", 0o000)

try:
    RuntimeDirLoader.read_instructions("/tmp/broken/agent")
except InstructionsReadError as e:
    print(f"✓ Exit code 4: {e}")
finally:
    os.chmod("/tmp/broken/agent/instructions.md", 0o644)
```

---

## Performance Benchmarks

```python
import time
from langagent.runtime.dir_loader import RuntimeDirLoader

# Benchmark template generation
start = time.time()
RuntimeDirLoader.write_template("/tmp", "perf-test")
duration = time.time() - start
print(f"Template generation: {duration*1000:.2f}ms (target: <5000ms)")
assert duration < 5.0, "SC-001 failed"

# Benchmark directory loading
start = time.time()
loaded = RuntimeDirLoader.load("/tmp/perf-test")
duration = time.time() - start
print(f"Directory loading: {duration*1000:.2f}ms (target: <100ms)")
assert duration < 0.1, "SC-003 failed"

# Benchmark stage guard overhead
@cross_cutting_stage_guard_decorator('test_stage')
def guarded_function():
    pass

start = time.time()
for _ in range(100):
    guarded_function()
duration = time.time() - start
avg_overhead = (duration / 100) * 1000
print(f"Stage guard overhead: {avg_overhead:.2f}ms (target: <10ms)")
assert avg_overhead < 10.0, "SC-006 failed"
```

---

## References

- [RuntimeDirLoader API](./contracts/runtime_dir_loader.md)
- [Stage Guard Decorator](./contracts/stage_guard_decorator.md)
- [Error Codes](./contracts/error_codes.md)
- [Data Model](./data-model.md)
