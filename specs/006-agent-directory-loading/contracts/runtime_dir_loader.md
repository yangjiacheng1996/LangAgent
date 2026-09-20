# RuntimeDirLoader API Contract

**Module**: `langagent.runtime.dir_loader`

**Purpose**: Load and validate agent directories, generate agent templates

## Public API

### RuntimeDirLoader.load()

```python
@staticmethod
def load(agent_dir: str) -> LoadedAgent
```

**Description**: Load and validate an agent directory.

**Parameters**:
- `agent_dir` (str): Path to the agent directory (absolute or relative)

**Returns**: `LoadedAgent` object with validated directory information

**Raises**:
- `AgentDirNotFoundError`: Directory does not exist (exit code 66)
- `AgentDirNotDirectoryError`: Path is not a directory (exit code 66)
- `AgentDirInvalidLayoutError`: Missing mandatory files (exit code 65)
- `InstructionsReadError`: Cannot read instructions.md (exit code 4)

**Example**:
```python
from langagent.runtime.dir_loader import RuntimeDirLoader

loaded_agent = RuntimeDirLoader.load("/path/to/agent")
print(f"Instructions: {loaded_agent.instructions}")
print(f"Tools: {loaded_agent.tool_ids}")
print(f"Skills: {loaded_agent.skill_names}")
```

---

### RuntimeDirLoader.validate_layout()

```python
@staticmethod
def validate_layout(agent_dir: str) -> list[str]
```

**Description**: Validate agent directory structure and check for mandatory files.

**Parameters**:
- `agent_dir` (str): Path to the agent directory

**Returns**: List of missing mandatory files (empty if all present)

**Example**:
```python
missing_files = RuntimeDirLoader.validate_layout("/path/to/agent")
if missing_files:
    print(f"Missing: {', '.join(missing_files)}")
```

---

### RuntimeDirLoader.read_instructions()

```python
@staticmethod
def read_instructions(agent_dir: str) -> str
```

**Description**: Read and validate instructions.md with encoding detection and size limit.

**Parameters**:
- `agent_dir` (str): Path to the agent directory

**Returns**: Content of instructions.md file

**Raises**:
- `InstructionsReadError`: If file cannot be read or exceeds size limit (100KB)

**Features**:
- Auto-detects file encoding (UTF-8, GBK, etc.)
- Enforces 100KB size limit
- Handles empty files gracefully

---

### RuntimeDirLoader.write_template()

```python
@staticmethod
def write_template(target_dir: str, name: str) -> None
```

**Description**: Generate a complete agent directory template.

**Parameters**:
- `target_dir` (str): Parent directory where agent folder will be created
- `name` (str): Name of the agent (used for directory name)

**Behavior**:
- Creates all mandatory files (instructions.md, agent.py, pyproject.toml)
- Creates example files (.env.example, example_skill, example_tool, example_middleware)
- Idempotent: validates existing files and recreates if invalid

**Example**:
```python
RuntimeDirLoader.write_template("/projects", "my-agent")
# Creates /projects/my-agent/ with complete structure
```

---

## LoadedAgent Schema

```python
@dataclass
class LoadedAgent:
    agent_dir: str              # Absolute path to agent directory
    instructions: str           # Content of instructions.md
    tool_ids: list[str]        # List of tool identifiers from tools/
    skill_names: list[str]     # List of skill names from skills/
    metadata: dict[str, Any]   # Contains schema_version="0.2.0"
```

**Note**: LoadedAgent has exactly 5 fields. It does NOT have a `compiled_graph` field per v1.1.0 specification.

---

## Error Codes

| Exception | Exit Code | Description |
|-----------|-----------|-------------|
| AgentDirNotFoundError | 66 | Directory path does not exist |
| AgentDirNotDirectoryError | 66 | Path exists but is not a directory |
| AgentDirInvalidLayoutError | 65 | Missing mandatory files |
| InstructionsReadError | 4 | Cannot read instructions.md (permissions, I/O, size, encoding) |

---

## Mandatory Files

Every valid agent directory must contain:
1. `instructions.md` - Agent behavior instructions
2. `agent.py` - Agent implementation with AgentState
3. `pyproject.toml` - Project dependencies

Optional directories:
- `skills/` - Skill implementations (each with SKILL.md)
- `tools/` - Tool implementations (.py files)
- `middleware/` - Middleware implementations (.py files)
