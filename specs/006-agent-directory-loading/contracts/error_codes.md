# Error Codes Mapping

## Overview

LangAgent uses Unix-style exit codes to communicate error conditions. This document maps exception types to their corresponding exit codes.

## Error Code Table

| Exit Code | Exception | Module | Description | Recovery |
|-----------|-----------|--------|-------------|----------|
| 1 | `StageCapabilityViolationError` | cross_cutting.stage_guard | Stage boundary violation | Review stage restrictions, remove blocked operations |
| 4 | `InstructionsReadError` | runtime.dir_loader | Cannot read instructions.md | Check file permissions, encoding, size (100KB limit) |
| 65 | `AgentDirInvalidLayoutError` | runtime.dir_loader | Missing mandatory files | Add missing files: instructions.md, agent.py, pyproject.toml |
| 66 | `AgentDirNotFoundError` | runtime.dir_loader | Directory does not exist | Verify path, create directory with `langagent init` |
| 66 | `AgentDirNotDirectoryError` | runtime.dir_loader | Path is not a directory | Provide directory path, not file path |

---

## Exit Code Categories

### Standard Unix Exit Codes (0-2)

- **0**: Success
- **1**: General error (StageCapabilityViolationError)
- **2**: Misuse of shell command (not used in LangAgent)

### BSD Exit Codes (64-78)

LangAgent uses BSD sysexits.h conventions:

- **64**: `EX_USAGE` - Command line usage error
- **65**: `EX_DATAERR` - Data format error (AgentDirInvalidLayoutError)
- **66**: `EX_NOINPUT` - Input file/directory not found (AgentDirNotFoundError, AgentDirNotDirectoryError)
- **4**: Custom error for I/O and permission issues (InstructionsReadError)

---

## Exception Details

### StageCapabilityViolationError (Exit Code 1)

**Trigger**: Operation blocked by stage guard decorator

**Common Causes**:
- Attempting to instantiate `BaseChatModel` during `dir_load`
- Attempting to compile `StateGraph` during `config_load`
- Reading .env files during `dir_load`

**Example**:
```python
# This raises StageCapabilityViolationError during dir_load
model = BaseChatModel()  # Blocked!
```

**Recovery**: Remove the blocked operation or move it to appropriate stage.

---

### InstructionsReadError (Exit Code 4)

**Trigger**: Cannot read instructions.md file

**Common Causes**:
- Permission denied (chmod 000)
- File exceeds 100KB size limit
- Encoding detection failure
- I/O error (disk failure, network mount)

**Example**:
```bash
# These cause InstructionsReadError
chmod 000 my-agent/instructions.md  # Permission denied
truncate -s 200K my-agent/instructions.md  # Size limit exceeded
```

**Recovery**: Fix permissions, reduce file size, check encoding, verify disk access.

---

### AgentDirInvalidLayoutError (Exit Code 65)

**Trigger**: Agent directory missing mandatory files

**Mandatory Files**:
1. `instructions.md`
2. `agent.py`
3. `pyproject.toml`

**Example**:
```python
# Missing instructions.md raises AgentDirInvalidLayoutError
RuntimeDirLoader.load("/incomplete/agent")
```

**Recovery**: Add missing files or regenerate with `langagent init`.

---

### AgentDirNotFoundError (Exit Code 66)

**Trigger**: Specified directory path does not exist

**Example**:
```python
RuntimeDirLoader.load("/nonexistent/path")
# Raises AgentDirNotFoundError
```

**Recovery**: Verify path, create directory with `langagent init <name>`.

---

### AgentDirNotDirectoryError (Exit Code 66)

**Trigger**: Path exists but is a file, not a directory

**Example**:
```python
RuntimeDirLoader.load("/path/to/file.md")
# Raises AgentDirNotDirectoryError
```

**Recovery**: Provide directory path instead of file path.

---

## Error Handling Best Practices

### 1. Catch Specific Exceptions

```python
try:
    loaded_agent = RuntimeDirLoader.load(agent_dir)
except AgentDirNotFoundError:
    print(f"Directory not found: {agent_dir}")
    sys.exit(66)
except AgentDirInvalidLayoutError as e:
    print(f"Missing files: {', '.join(e.missing_files)}")
    sys.exit(65)
except InstructionsReadError as e:
    print(f"Cannot read instructions: {e}")
    sys.exit(4)
```

### 2. Provide Actionable Error Messages

```python
except AgentDirInvalidLayoutError as e:
    print(f"Invalid agent directory: missing {len(e.missing_files)} files")
    print(f"Missing: {', '.join(e.missing_files)}")
    print(f"Run: langagent init {agent_name}")
    sys.exit(65)
```

### 3. Log Before Exit

```python
except StageCapabilityViolationError as e:
    logger.error(f"Stage violation: {e.stage_name} attempted {e.operation} on {e.target}")
    sys.exit(1)
```

---

## Testing Error Conditions

```python
# Test exit code 66
with pytest.raises(AgentDirNotFoundError):
    RuntimeDirLoader.load("/nonexistent")

# Test exit code 65
with pytest.raises(AgentDirInvalidLayoutError) as exc_info:
    RuntimeDirLoader.load("/broken/agent")
assert "instructions.md" in exc_info.value.missing_files

# Test exit code 4
with pytest.raises(InstructionsReadError):
    RuntimeDirLoader.read_instructions("/agent/with/huge/file")
```
