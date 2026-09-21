"""PyInstaller entry point for langagent CLI.

This module serves as the entry point for the langagent binary.
It imports and delegates to the CLI runner's main() function.
"""
import sys


def _main() -> None:
    """Entry point that imports and calls cli_runner.main()."""
    from langagent.cli.runner import main
    
    exit_code = main()
    sys.exit(exit_code)


if __name__ == "__main__":
    _main()
