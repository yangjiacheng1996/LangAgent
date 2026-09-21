"""Agent directory loading and template generation.

This module implements the RuntimeDirLoader class for loading existing agent
directories and generating new agent templates via the dir_load stage.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any


# Exception classes for error handling
class AgentDirNotFoundError(Exception):
    """Raised when the specified agent directory does not exist."""
    pass


class AgentDirNotDirectoryError(Exception):
    """Raised when the specified path is not a directory."""
    pass


class AgentDirInvalidLayoutError(Exception):
    """Raised when the agent directory is missing mandatory files."""
    
    def __init__(self, missing_files: list[str]):
        self.missing_files = missing_files
        message = f"Invalid agent directory layout. Missing files: {', '.join(missing_files)}"
        super().__init__(message)


class InstructionsReadError(Exception):
    """Raised when instructions.md cannot be read (permissions, I/O, size, encoding)."""
    pass


@dataclass
class LoadedAgent:
    """Represents a loaded agent directory with validated structure.
    
    This is the return type of RuntimeDirLoader.load() and contains all
    information needed for subsequent pipeline stages.
    
    Attributes:
        agent_dir: Absolute path to the agent directory
        instructions: Content of instructions.md file
        tool_ids: List of tool identifiers found in tools/ directory
        skill_names: List of skill names found in skills/ directory
        metadata: Dictionary containing schema_version and other metadata
    """
    agent_dir: str
    instructions: str
    tool_ids: list[str]
    skill_names: list[str]
    metadata: dict[str, Any]


class RuntimeDirLoader:
    """Load and validate agent directories, generate agent templates.
    
    This class implements the dir_load stage of the LangAgent pipeline,
    providing functionality to load existing agent directories and create
    new ones from templates.
    """
    
    @staticmethod
    def load(agent_dir: str) -> LoadedAgent:
        """Load and validate an agent directory.
        
        Args:
            agent_dir: Path to the agent directory (absolute or relative)
            
        Returns:
            LoadedAgent object with validated directory information
            
        Raises:
            AgentDirNotFoundError: Directory does not exist (exit code 66)
            AgentDirNotDirectoryError: Path is not a directory (exit code 66)
            AgentDirInvalidLayoutError: Missing mandatory files (exit code 65)
            InstructionsReadError: Cannot read instructions.md (exit code 4)
        """
        # Convert to absolute path
        dir_path = Path(agent_dir).resolve()
        
        # Check directory existence
        if not dir_path.exists():
            raise AgentDirNotFoundError(f"Agent directory not found: {agent_dir}")
        
        # Check if it's a directory
        if not dir_path.is_dir():
            raise AgentDirNotDirectoryError(f"Path is not a directory: {agent_dir}")
        
        # Validate layout
        missing_files = RuntimeDirLoader.validate_layout(str(dir_path))
        if missing_files:
            raise AgentDirInvalidLayoutError(missing_files)
        
        # Read instructions
        try:
            instructions = RuntimeDirLoader.read_instructions(str(dir_path))
        except Exception as e:
            raise InstructionsReadError(f"Failed to read instructions.md: {e}")
        
        # Scan tools and skills
        tool_ids = scan_tools(str(dir_path))
        skill_names = scan_skills(str(dir_path))
        
        # Create LoadedAgent
        loaded_agent = LoadedAgent(
            agent_dir=str(dir_path),
            instructions=instructions,
            tool_ids=tool_ids,
            skill_names=skill_names,
            metadata={'schema_version': '0.2.0'}
        )
        
        # Emit success log
        # TODO: Implement logging in future PR
        # log('la.runtime.dir_load.ok', {'agent_dir': str(dir_path)})
        
        return loaded_agent
    
    @staticmethod
    def validate_layout(agent_dir: str) -> list[str]:
        """Validate agent directory structure and check for mandatory files.
        
        Args:
            agent_dir: Path to the agent directory
            
        Returns:
            List of missing mandatory files (empty if all present)
        """
        dir_path = Path(agent_dir)
        mandatory_files = ['instructions.md', 'agent.py', 'pyproject.toml']
        missing_files = []
        
        for filename in mandatory_files:
            file_path = dir_path / filename
            if not file_path.exists():
                missing_files.append(filename)
        
        return missing_files
    
    @staticmethod
    def read_instructions(agent_dir: str) -> str:
        """Read and validate instructions.md with encoding detection and size limit.
        
        Args:
            agent_dir: Path to the agent directory
            
        Returns:
            Content of instructions.md file
            
        Raises:
            InstructionsReadError: If file cannot be read or exceeds size limit
        """
        import charset_normalizer
        
        instructions_path = Path(agent_dir) / 'instructions.md'
        
        # Check file size (100KB limit per FR-039)
        try:
            file_size = instructions_path.stat().st_size
            if file_size > 100 * 1024:  # 100KB
                raise InstructionsReadError(
                    f"instructions.md exceeds 100KB limit (actual: {file_size} bytes)"
                )
            
            # Handle empty file (FR-040)
            if file_size == 0:
                return ""
            
            # Read file with encoding detection (FR-041)
            raw_bytes = instructions_path.read_bytes()
            detected = charset_normalizer.from_bytes(raw_bytes).best()
            
            if detected is None:
                # Fallback to UTF-8
                return raw_bytes.decode('utf-8', errors='replace')
            
            return str(detected)
            
        except PermissionError as e:
            raise InstructionsReadError(f"Permission denied reading instructions.md: {e}")
        except OSError as e:
            raise InstructionsReadError(f"I/O error reading instructions.md: {e}")
    
    @staticmethod
    def write_template(target_dir: str, name: str) -> None:
        """Generate a complete agent directory template.
        
        Creates all mandatory and example files for a new agent directory,
        with idempotent behavior (validate and recreate if invalid).
        
        Args:
            target_dir: Parent directory where agent folder will be created
            name: Name of the agent (used for directory name)
        """
        # TODO: Emit la.lifecycle.init.start log (FR-011)
        # Log emission will be implemented when logging infrastructure exists
        
        agent_dir = Path(target_dir) / name
        agent_dir.mkdir(parents=True, exist_ok=True)
        
        # Create/validate mandatory files (idempotent behavior per FR-043, FR-044)
        
        # 1. instructions.md
        instructions_path = agent_dir / "instructions.md"
        if instructions_path.exists():
            content = instructions_path.read_text()
            if not validate_instructions(content):
                instructions_path.unlink()
                instructions_path.write_text(create_instructions())
        else:
            instructions_path.write_text(create_instructions())
        
        # 2. agent.py
        agent_py_path = agent_dir / "agent.py"
        if agent_py_path.exists():
            content = agent_py_path.read_text()
            if not validate_agent_py(content):
                agent_py_path.unlink()
                agent_py_path.write_text(create_agent_py())
        else:
            agent_py_path.write_text(create_agent_py())
        
        # 3. pyproject.toml
        pyproject_path = agent_dir / "pyproject.toml"
        if pyproject_path.exists():
            content = pyproject_path.read_text()
            if not validate_pyproject_toml(content):
                pyproject_path.unlink()
                pyproject_path.write_text(create_pyproject_toml(name))
        else:
            pyproject_path.write_text(create_pyproject_toml(name))
        
        # 4. .env.example
        env_example_path = agent_dir / ".env.example"
        if env_example_path.exists():
            content = env_example_path.read_text()
            if not validate_env_example(content):
                env_example_path.unlink()
                env_example_path.write_text(create_env_example())
        else:
            env_example_path.write_text(create_env_example())
        
        # Create v1 reserved directories
        (agent_dir / "skills").mkdir(exist_ok=True)
        (agent_dir / "tools").mkdir(exist_ok=True)
        (agent_dir / "middleware").mkdir(exist_ok=True)
        (agent_dir / "evals").mkdir(exist_ok=True)
        
        # Create example skill
        example_skill_dir = agent_dir / "skills" / "example_skill"
        example_skill_dir.mkdir(exist_ok=True)
        (example_skill_dir / "SKILL.md").write_text(create_example_skill())
        
        # Create example tool
        (agent_dir / "tools" / "example_tool.py").write_text(create_example_tool())
        
        # Create example middleware
        (agent_dir / "middleware" / "example_middleware.py").write_text(create_example_middleware())


# Helper functions for scanning tools and skills
def scan_tools(agent_dir: str) -> list[str]:
    """Scan tools/ directory and return list of tool identifiers.
    
    Args:
        agent_dir: Path to the agent directory
        
    Returns:
        List of tool IDs (empty if tools/ directory doesn't exist)
    """
    tools_dir = Path(agent_dir) / 'tools'
    
    if not tools_dir.exists() or not tools_dir.is_dir():
        return []
    
    tool_ids = []
    for item in tools_dir.iterdir():
        if item.is_file() and item.suffix == '.py' and item.stem != '__init__':
            tool_ids.append(item.stem)
    
    return sorted(tool_ids)


def scan_skills(agent_dir: str) -> list[str]:
    """Scan skills/ directory and return list of skill names.
    
    Args:
        agent_dir: Path to the agent directory
        
    Returns:
        List of skill names (empty if skills/ directory doesn't exist)
    """
    skills_dir = Path(agent_dir) / 'skills'
    
    if not skills_dir.exists() or not skills_dir.is_dir():
        return []
    
    skill_names = []
    for item in skills_dir.iterdir():
        if item.is_dir():
            # Check for SKILL.md file (FR-042)
            skill_md = item / 'SKILL.md'
            if skill_md.exists():
                skill_names.append(item.name)
    
    return sorted(skill_names)


# Helper functions for template generation
def create_instructions(content: str = "") -> str:
    """Create instructions.md content.
    
    Args:
        content: Optional custom content (if empty, uses default template)
        
    Returns:
        Markdown content for instructions.md
    """
    if content:
        return content
    
    return """You are a helpful AI assistant designed to assist users with their tasks.

## Core Capabilities

- Answer questions clearly and concisely
- Help with problem-solving and analysis
- Provide explanations and guidance when needed

## Communication Style

Be direct, professional, and focused on delivering value to the user.
"""


def validate_instructions(content: str) -> bool:
    """Validate instructions.md content.
    
    Args:
        content: Content to validate
        
    Returns:
        True if valid, False otherwise
    """
    # Must be non-empty and contain typical instruction markers
    if len(content.strip()) == 0:
        return False
    
    # If content looks like placeholder/invalid, reject it
    if content.strip() in ["INVALID CONTENT", "TODO", "PLACEHOLDER"]:
        return False
    
    return True


def create_agent_py() -> str:
    """Create agent.py with AgentState template.
    
    Returns:
        Python code with AgentState TypedDict and 5 fields
    """
    return '''"""Agent implementation with state management."""

from typing import TypedDict
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """Agent state with 5 required fields per Constitution Article VI.
    
    Attributes:
        messages: List of conversation messages
        todos: List of pending tasks
        files: Dictionary mapping file paths to content
        context: Dictionary for contextual information
        scratchpad: Temporary working memory for the agent
    """
    messages: list[BaseMessage]
    todos: list[str]
    files: dict[str, str]
    context: dict[str, str]
    scratchpad: str


def create_graph():
    """Create and configure the agent graph.
    
    This function will be implemented to define the agent's
    processing workflow using LangGraph.
    """
    # TODO: Implement graph creation logic
    pass
'''


def validate_agent_py(content: str) -> bool:
    """Validate agent.py with AST parse check.
    
    Args:
        content: Python code to validate
        
    Returns:
        True if valid Python syntax, False otherwise
    """
    import ast
    
    try:
        ast.parse(content)
        return True
    except SyntaxError:
        return False


def create_pyproject_toml(agent_name: str) -> str:
    """Create pyproject.toml content.
    
    Args:
        agent_name: Name of the agent
        
    Returns:
        TOML content for pyproject.toml
    """
    return f"""[project]
name = "{agent_name}"
version = "0.1.0"
description = "LangAgent AI agent"
requires-python = ">=3.10"
dependencies = [
    "langchain-core>=0.2.0",
    "langchain-openai>=0.1.0",
    "langgraph>=0.1.0",
    "pydantic>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
]
"""


def validate_pyproject_toml(content: str) -> bool:
    """Validate pyproject.toml with TOML parse check.
    
    Args:
        content: TOML content to validate
        
    Returns:
        True if valid TOML, False otherwise
    """
    try:
        import tomllib as toml_parser
    except ImportError:
        import tomli as toml_parser  # type: ignore
    
    try:
        toml_parser.loads(content)
        return True
    except Exception:
        return False


def create_env_example() -> str:
    """Create .env.example with placeholders.
    
    Returns:
        Environment variable template with angle bracket placeholders
    """
    return """# LangAgent Configuration
# Copy this file to .env and fill in your actual values

# Model Provider Configuration
MODEL_PROVIDER=<PROVIDER_NAME>
MODEL_NAME=<MODEL_NAME>
MODEL_BASE_URL=<API_BASE_URL>

# API Keys
OPENAI_API_KEY=<YOUR_OPENAI_API_KEY>
ANTHROPIC_API_KEY=<YOUR_ANTHROPIC_API_KEY>
GOOGLE_API_KEY=<YOUR_GOOGLE_API_KEY>

# Optional: Logging and monitoring
LOG_LEVEL=<INFO|DEBUG|WARNING|ERROR>
"""


def validate_env_example(content: str) -> bool:
    """Validate .env.example placeholder regex check.
    
    Args:
        content: .env.example content to validate
        
    Returns:
        True if valid (has placeholders, no localhost), False otherwise
    """
    import re
    
    # Check for localhost or internal IPs
    if any(pattern in content.lower() for pattern in ['localhost', '127.0.0.1', '192.168.', '10.0.']):
        return False
    
    # Check for angle bracket placeholders
    placeholders = re.findall(r'<[A-Z_]+>', content)
    return len(placeholders) > 0


def create_example_skill() -> str:
    """Create example skill content.
    
    Returns:
        Example SKILL.md content
    """
    return """# Example Skill

This is an example skill demonstrating the skill structure.

## Purpose

Skills extend the agent's capabilities with specialized workflows.

## Usage

Add your skill implementation in this directory.
"""


def create_example_tool() -> str:
    """Create example tool content.
    
    Returns:
        Example tool Python code
    """
    return '''"""Example tool for the agent."""

from typing import Any


def example_function(input_data: str) -> str:
    """Example function that processes input.
    
    Args:
        input_data: Input string to process
        
    Returns:
        Processed result
    """
    return f"Processed: {input_data}"
'''


def create_example_middleware() -> str:
    """Create example middleware content.
    
    Returns:
        Example middleware Python code
    """
    return '''"""Example middleware for the agent."""

from typing import Any, Callable


def example_middleware(next_handler: Callable) -> Callable:
    """Example middleware that wraps request handling.
    
    Args:
        next_handler: The next handler in the chain
        
    Returns:
        Wrapped handler function
    """
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Pre-processing
        print("Before processing")
        
        # Call next handler
        result = next_handler(*args, **kwargs)
        
        # Post-processing
        print("After processing")
        
        return result
    
    return wrapper
'''
