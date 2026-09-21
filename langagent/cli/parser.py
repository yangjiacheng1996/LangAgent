"""CLI argument parsing for langagent.

This module provides argparse-based CLI parsing for the 4 core subcommands:
- init: Initialize new agent directory
- run: Run agent with configuration overrides
- eval: Evaluate agent quality with evals/
- doctor: Diagnose agent configuration issues
"""
import argparse
from typing import Any


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser with 4 subcommands.
    
    Returns:
        ArgumentParser configured with init/run/eval/doctor subcommands
    """
    # Get version info from build metadata if available
    version_str = "dev"
    try:
        from langagent._build_metadata import __version__, __commit__
        version_str = f"{__version__} (commit {__commit__})"
    except ImportError:
        # Development mode - no build metadata
        try:
            import tomllib
            from pathlib import Path
            pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
            if pyproject_path.exists():
                with open(pyproject_path, "rb") as f:
                    pyproject = tomllib.load(f)
                    version_str = pyproject.get("project", {}).get("version", "dev")
        except Exception:
            pass
    
    parser = argparse.ArgumentParser(
        prog="langagent",
        description=f"LangAgent v{version_str}\n\nConstitutional LLM Agent Framework - Build, run, and evaluate LLM agents with governance constraints",
        epilog="Exit codes: 0=success, 1=generic error, 2=invalid args, 64=config error, 65=missing resource, "
               "66=missing evals dir, 67=name conflict, 70=internal error, 78=grader error, 130=keyboard interrupt",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="subcommand", required=True)
    
    # Validate name format using a custom type function
    def validate_agent_name(value: str) -> str:
        import re
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", value):
            raise argparse.ArgumentTypeError(
                f"name must start with letter and contain only letters, digits, "
                f"underscores, and hyphens, got {value!r}"
            )
        return value
    
    # Subcommand: init
    parser_init = subparsers.add_parser(
        "init",
        help="Initialize a new agent directory with template structure",
        description="Create a new agent directory with minimal template (constitution.md, agent.py). "
                    "Exit codes: 0=success, 67=directory already exists, 70=template load failed"
    )
    parser_init.add_argument(
        "name",
        type=validate_agent_name,
        help="Agent name (must start with letter, contain only alphanumeric, underscore, or hyphen)"
    )
    
    # Subcommand: run
    parser_run = subparsers.add_parser(
        "run",
        help="Run agent with optional configuration overrides",
        description="Execute agent with CLI overrides for model, checkpointer, and middleware. "
                    "Reads stdin for user input, prints chat messages to stdout. "
                    "Exit codes: 0=success, 1=agent error, 64=invalid config, 65=agent dir not found, 130=interrupted"
    )
    parser_run.add_argument(
        "agent_dir",
        nargs="?",
        default=".",
        help="Path to agent directory (default: current directory)"
    )
    parser_run.add_argument(
        "--user",
        type=str,
        help="User prompt to send to the agent (alternative to stdin)"
    )
    parser_run.add_argument(
        "--model",
        type=str,
        help="Override model name (e.g., gpt-4o, claude-3-5-sonnet-20241022)"
    )
    parser_run.add_argument(
        "--model-provider",
        type=str,
        help="Override model provider (openai, anthropic, vllm, etc.)"
    )
    parser_run.add_argument(
        "--model-base-url",
        type=str,
        help="Override model API base URL (for local or custom endpoints)"
    )
    parser_run.add_argument(
        "--checkpointer",
        type=str,
        help="Override checkpointer type (sqlite, memory, redis, etc.)"
    )
    parser_run.add_argument(
        "--middleware",
        type=str,
        help="Override middleware (comma-separated list, e.g., 'logger,validator')"
    )
    parser_run.add_argument(
        "--max-turns",
        type=int,
        default=30,
        help="Maximum conversation turns before termination (default: 30)"
    )
    parser_run.add_argument(
        "--thread-id",
        type=str,
        help="Checkpointer thread ID for conversation persistence"
    )
    
    # Subcommand: eval
    parser_eval = subparsers.add_parser(
        "eval",
        help="Evaluate agent quality using tasks in evals/ directory",
        description="Run evaluation tasks against agent, compute pass rate and latency metrics. "
                    "Requires evals/ directory with task definitions. "
                    "Exit codes: 0=success, 1=eval failure, 66=evals dir missing, 70=timeout, 78=grader error"
    )
    parser_eval.add_argument(
        "agent_dir",
        nargs="?",
        default=".",
        help="Path to agent directory (default: current directory)"
    )
    parser_eval.add_argument(
        "--grader-only",
        type=str,
        choices=["exact_match", "contains", "regex", "llm_judge", "tool_call_match"],
        help="Filter evaluation tasks to specific grader type only"
    )
    parser_eval.add_argument(
        "--task",
        type=str,
        help="Run only the specified task_id (e.g., 'greeting_test')"
    )
    parser_eval.add_argument(
        "--report-format",
        type=str,
        choices=["json", "yaml", "table"],
        default="table",
        help="Output format for evaluation report (default: table)"
    )
    
    # Subcommand: doctor
    parser_doctor = subparsers.add_parser(
        "doctor",
        help="Diagnose agent configuration issues and validate setup",
        description="Run health checks on agent configuration (model, checkpointer, skills, instructions). "
                    "Reports pass/fail status for each check. "
                    "Exit codes: 0=all checks pass, 1=one or more checks fail, 65=agent dir not found"
    )
    parser_doctor.add_argument(
        "agent_dir",
        nargs="?",
        default=".",
        help="Path to agent directory (default: current directory)"
    )
    parser_doctor.add_argument(
        "--checks",
        type=str,
        help="Run specific checks only (comma-separated: model,checkpointer,skills,instructions). Default: all checks"
    )
    
    # Subcommand: chat
    parser_chat = subparsers.add_parser(
        "chat",
        help="Start an interactive chat session with the agent",
        description="Launch an interactive REPL for conversing with the agent. "
                    "Supports slash commands: /picture <path> to load images, /quit to exit. "
                    "Exit codes: 0=success, 130=interrupted, 1=error"
    )
    parser_chat.add_argument(
        "agent_dir",
        nargs="?",
        default=".",
        help="Path to agent directory (default: current directory)"
    )
    parser_chat.add_argument(
        "--session-id",
        type=str,
        help="Session ID for conversation persistence (creates new session if not provided)"
    )
    parser_chat.add_argument(
        "--model",
        type=str,
        help="Override model name"
    )
    parser_chat.add_argument(
        "--model-provider",
        type=str,
        help="Override model provider"
    )
    parser_chat.add_argument(
        "--model-base-url",
        type=str,
        help="Override model API base URL"
    )
    
    # Subcommand: version
    parser_version = subparsers.add_parser(
        "version",
        help="Display LangAgent version information",
        description="Show version, commit hash, and build metadata. "
                    "Exit codes: 0=success"
    )
    
    return parser


def ns_to_cli_args(ns: argparse.Namespace) -> dict[str, Any]:
    """Convert argparse Namespace to CLI args dict.
    
    Args:
        ns: Parsed argparse Namespace
        
    Returns:
        Dictionary compatible with RuntimeConfig.cli_args
    """
    # Stub implementation - to be completed in Phase 7
    return vars(ns)
