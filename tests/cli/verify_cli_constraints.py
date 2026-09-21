"""Static verification of CLI module import constraints.

This script uses AST parsing to verify that CLI modules do not import
from prohibited modules, ensuring proper layer separation:

Constraints:
- langagent/cli/*.py MUST NOT import from langagent.primitives.chat_model_factory
- langagent/cli/*.py MUST NOT import from langagent.primitives.checkpoint_adapter
- langagent/cli/*.py MUST NOT import from langagent.cross_cutting.logger

Rationale:
- CLI layer should delegate to runtime layer, not primitives layer
- CLI layer uses print() for output, not centralized logger
"""
import ast
import sys
from pathlib import Path
from typing import Set, List, Tuple


def get_imports(filepath: Path) -> Set[str]:
    """Extract all import module names from a Python file.
    
    Args:
        filepath: Path to Python file
        
    Returns:
        Set of module names imported (e.g., {'langagent.primitives.chat_model_factory'})
    """
    with open(filepath, 'r') as f:
        tree = ast.parse(f.read(), filename=str(filepath))
    
    imports = set()
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
    
    return imports


def check_cli_constraints(cli_dir: Path) -> List[Tuple[Path, str]]:
    """Check all CLI modules for prohibited imports.
    
    Args:
        cli_dir: Path to langagent/cli/ directory
        
    Returns:
        List of (filepath, violation_message) tuples for violations found
    """
    prohibited_imports = {
        'langagent.primitives.chat_model_factory',
        'langagent.primitives.checkpoint_adapter',
        'langagent.cross_cutting.logger',
    }
    
    violations = []
    
    # Scan all Python files in cli/
    for py_file in cli_dir.glob('*.py'):
        if py_file.name == '__init__.py':
            continue
        
        imports = get_imports(py_file)
        
        # Check for prohibited imports
        for imp in imports:
            if imp in prohibited_imports:
                violation = (py_file, f"Prohibited import: {imp}")
                violations.append(violation)
    
    return violations


def main() -> int:
    """Run static verification and report results.
    
    Returns:
        Exit code (0=success, 1=violations found)
    """
    # Find CLI directory
    repo_root = Path(__file__).parent.parent.parent
    cli_dir = repo_root / 'langagent' / 'cli'
    
    if not cli_dir.exists():
        print(f"Error: CLI directory not found: {cli_dir}", file=sys.stderr)
        return 1
    
    # Check constraints
    violations = check_cli_constraints(cli_dir)
    
    if violations:
        print("❌ CLI Import Constraint Violations Found:", file=sys.stderr)
        print("", file=sys.stderr)
        for filepath, message in violations:
            print(f"  {filepath.name}: {message}", file=sys.stderr)
        print("", file=sys.stderr)
        print("CLI modules must not import from:", file=sys.stderr)
        print("  - langagent.primitives.chat_model_factory", file=sys.stderr)
        print("  - langagent.primitives.checkpoint_adapter", file=sys.stderr)
        print("  - langagent.cross_cutting.logger", file=sys.stderr)
        return 1
    
    print("✅ All CLI modules pass import constraint checks")
    return 0


if __name__ == '__main__':
    sys.exit(main())
