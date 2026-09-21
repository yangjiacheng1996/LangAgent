"""CLI runner and dispatch orchestration for langagent.

This module provides the main entry point and dispatch logic for the CLI:
- parse_argv(): Parse command-line arguments into CliArgs
- dispatch(): Orchestrate runtime stages based on subcommand
- main(): Top-level entry point with exception handling
"""
import sys
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator
import re


class CliArgs(BaseModel, frozen=True):
    """Parsed CLI arguments (immutable).
    
    This frozen Pydantic model represents validated CLI arguments
    for all 4 subcommands (init, run, eval, doctor).
    """
    
    # Common fields
    subcommand: str = Field(..., description="One of: init, run, eval, doctor")
    agent_dir: str = Field(default=".", description="Path to agent directory")
    cli_args: dict[str, Any] = Field(default_factory=dict, description="Raw CLI args dict")
    
    # Init subcommand
    name: Optional[str] = Field(default=None, description="Agent name for init")
    
    # Run subcommand
    model: Optional[str] = Field(default=None, description="Model name override")
    model_provider: Optional[str] = Field(default=None, description="Model provider override")
    model_base_url: Optional[str] = Field(default=None, description="Model base URL override")
    checkpointer: Optional[str] = Field(default=None, description="Checkpointer type")
    middleware: Optional[str] = Field(default=None, description="Middleware list (comma-separated)")
    max_turns: int = Field(default=30, description="Maximum main loop turns")
    thread_id: Optional[str] = Field(default=None, description="Checkpointer thread ID")
    
    # Eval subcommand
    grader_only: Optional[str] = Field(default=None, description="Filter tasks by grader type")
    task: Optional[str] = Field(default=None, description="Run specific task by ID")
    report_format: str = Field(default="table", description="Report output format")
    
    # Doctor subcommand
    checks: Optional[list[str]] = Field(default=None, description="Checks to run")
    
    @field_validator("subcommand")
    @classmethod
    def validate_subcommand(cls, v: str) -> str:
        """Validate subcommand is one of the 4 allowed values."""
        allowed = {"init", "run", "eval", "doctor"}
        if v not in allowed:
            raise ValueError(f"subcommand must be one of {allowed}, got {v!r}")
        return v
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate agent name matches naming constraints."""
        if v is None:
            return v
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", v):
            raise ValueError(
                f"name must start with letter and contain only letters, digits, "
                f"underscores, and hyphens, got {v!r}"
            )
        return v
    
    @field_validator("max_turns")
    @classmethod
    def validate_max_turns(cls, v: int) -> int:
        """Validate max_turns is positive."""
        if v < 1:
            raise ValueError(f"max_turns must be >= 1, got {v}")
        return v
    
    @field_validator("report_format")
    @classmethod
    def validate_report_format(cls, v: str) -> str:
        """Validate report format is one of the allowed values."""
        allowed = {"json", "yaml", "table"}
        if v not in allowed:
            raise ValueError(f"report_format must be one of {allowed}, got {v!r}")
        return v
    
    @field_validator("grader_only")
    @classmethod
    def validate_grader_only(cls, v: Optional[str]) -> Optional[str]:
        """Validate grader type is one of the allowed values."""
        if v is None:
            return v
        allowed = {"exact_match", "contains", "regex", "llm_judge", "tool_call_match"}
        if v not in allowed:
            raise ValueError(f"grader_only must be one of {allowed}, got {v!r}")
        return v


def parse_argv(argv: list[str]) -> CliArgs:
    """Parse command-line arguments into CliArgs model.
    
    Args:
        argv: Command-line arguments (typically sys.argv[1:])
        
    Returns:
        Validated CliArgs instance
        
    Raises:
        SystemExit: On argparse validation failure (exit code 2)
    """
    from langagent.cli.parser import build_parser, ns_to_cli_args
    
    parser = build_parser()
    ns = parser.parse_args(argv)
    
    # Convert namespace to dict
    raw_args = vars(ns)
    subcommand = raw_args.get("subcommand")
    
    # Build CliArgs based on subcommand
    if subcommand == "init":
        args = CliArgs(
            subcommand="init",
            name=raw_args.get("name"),
            agent_dir=raw_args.get("agent_dir", "."),
            cli_args=ns_to_cli_args(ns)
        )
    else:
        # Fallback for other subcommands (to be implemented)
        args = CliArgs(
            subcommand=subcommand or "init",
            agent_dir=raw_args.get("agent_dir", "."),
            cli_args=ns_to_cli_args(ns)
        )
    
    return args


def dispatch(args: CliArgs) -> int:
    """Dispatch to appropriate subcommand handler.
    
    Args:
        args: Parsed and validated CLI arguments
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    if args.subcommand == "init":
        return _dispatch_init(args)
    elif args.subcommand == "run":
        return _dispatch_run(args)
    elif args.subcommand == "eval":
        return _dispatch_eval(args)
    elif args.subcommand == "doctor":
        return _dispatch_doctor(args)
    else:
        return 2  # Invalid subcommand


def _dispatch_init(args: CliArgs) -> int:
    """Handle init subcommand.
    
    Args:
        args: Parsed CLI arguments with name field
        
    Returns:
        Exit code (0=success, 67=exists, 70=template_failed)
    """
    try:
        # Import F06 RuntimeDirLoader and F09 RuntimeExitHandler
        from langagent.runtime.dir_loader import RuntimeDirLoader
        from langagent.runtime.exit_handler import RuntimeExitHandler
        
        # Get target directory path (parent directory where agent will be created)
        target_dir = args.agent_dir
        
        # Call F06 to write template
        RuntimeDirLoader.write_template(target_dir, args.name)
        
        # Print creation summary
        print(f"✓ Created agent directory: {args.name}")
        print(f"  - instructions.md")
        print(f"  - agent.py")
        print(f"  - pyproject.toml")
        print(f"  - .env.example")
        print(f"  - skills/")
        print(f"  - tools/")
        print(f"  - middleware/")
        
        # Call F09 cleanup with init_only=True per FR-CLI-020
        exit_handler = RuntimeExitHandler()
        exit_code = exit_handler.cleanup(None, None, init_only=True)
        return exit_code
        
    except Exception as e:
        # Check for F06 NameAlreadyExistsError
        if type(e).__name__ == "NameAlreadyExistsError":
            print(f"Error: Directory '{args.name}' already exists", file=sys.stderr)
            return 67  # Exit code per FR-CLI-015
        
        # Check for F06 TemplateLoadFailedError
        if type(e).__name__ == "TemplateLoadFailedError":
            print(f"Error: Failed to load template: {e}", file=sys.stderr)
            return 70  # Exit code per workflow.md
        
        # Generic error
        print(f"Error during init: {e}", file=sys.stderr)
        return 1


def _dispatch_run(args: CliArgs) -> int:
    """Handle run subcommand.
    
    Executes the 6-stage runtime pipeline:
    1. Load agent directory (F06 dir_loader)
    2. Resolve runtime config (F07 config_resolver)
    3. Create chat model and checkpoint (F02, F05)
    4. Merge config with model and checkpoint
    5. Build state graph (F01 state_graph_builder)
    6. Run main loop (F08 main_loop_dispatcher)
    
    Args:
        args: Parsed CLI arguments
        
    Returns:
        Exit code (0=success, 71=agent_not_found, 72=config_error, 
                  73=model_error, 74=runtime_error, 75=token_limit, 
                  76=interrupted, 130=keyboard_interrupt)
    """
    try:
        # Import runtime modules
        from langagent.runtime.dir_loader import RuntimeDirLoader
        from langagent.runtime.config_resolver import RuntimeConfigResolver
        from langagent.runtime import chat_model_factory
        from langagent.runtime import checkpoint_adapter
        from langagent.runtime import state_graph_builder
        from langagent.runtime import main_loop_dispatcher
        from langagent.runtime.exit_handler import RuntimeExitHandler
        from langagent.cli.output_formatter import format_chat_message
        from langchain_core.messages import AIMessage
        
        # Stage 1: Load agent directory
        loaded_agent = RuntimeDirLoader.load(args.agent_dir)
        
        # Stage 2: Resolve runtime config
        config = RuntimeConfigResolver.resolve(args.cli_args, args.agent_dir)
        
        # Stage 3: Create model and checkpoint
        model = chat_model_factory.create(config)
        checkpoint = checkpoint_adapter.create(config)
        
        # Stage 4: Merge config with model and checkpoint
        final_config = config.with_model(model).with_checkpoint(checkpoint)
        
        # Stage 5: Build state graph
        graph = state_graph_builder.build(loaded_agent, final_config)
        
        # Stage 6: Run main loop
        max_turns = args.max_turns if args.max_turns else 30
        final_state = main_loop_dispatcher.run_until_done(
            graph,
            state={"messages": []},  # Initial state will be built by main_loop_dispatcher
            max_turns=max_turns
        )
        
        # Print chat messages to stdout (only AIMessages)
        messages = final_state.get("messages", [])
        for msg in messages:
            if isinstance(msg, AIMessage):
                # Convert message to dict for formatter
                msg_dict = {"content": msg.content}
                formatted = format_chat_message(msg_dict)
                print(formatted, end="")
        
        # Cleanup and return exit code
        exit_handler = RuntimeExitHandler()
        return exit_handler.cleanup(final_state, final_config)
        
    except KeyboardInterrupt:
        # Ctrl-C during run -> return exit code 130
        print("Interrupted", file=sys.stderr)
        return 130
    except Exception as e:
        # Map runtime errors to exit codes per FR-CLI-030
        error_name = type(e).__name__
        
        if error_name == "AgentDirNotFoundError":
            print(f"Error: Agent directory not found: {args.agent_dir}", file=sys.stderr)
            return 66
        elif error_name == "ConfigValidationError":
            print(f"Error: Configuration validation failed: {e}", file=sys.stderr)
            return 72
        elif error_name == "ModelCreationError":
            print(f"Error: Failed to create chat model: {e}", file=sys.stderr)
            return 73
        elif error_name == "TokenLimitExceededError":
            print(f"Error: Token limit exceeded: {e}", file=sys.stderr)
            return 75
        elif error_name == "HitlInterruptedError":
            print(f"Interrupted: {e}", file=sys.stderr)
            return 76
        else:
            # Generic runtime error
            print(f"Error during run: {e}", file=sys.stderr)
            return 74


def _dispatch_eval(args: CliArgs) -> int:
    """Handle eval subcommand.
    
    Executes the 3-stage eval pipeline per FR-CLI-018:
    1. Load agent directory (F06 dir_loader)
    2. Resolve runtime config (F07 config_resolver)
    3. Run eval tasks (F11 eval_runner) and display results
    
    Args:
        args: Parsed CLI arguments with subcommand='eval'
        
    Returns:
        Exit code (0=success, error codes per FR-CLI-027)
    """
    try:
        # Conditional import per FR-CLI-018
        from langagent.eval.runner import run as eval_runner_run
    except ModuleNotFoundError:
        # F11 (Eval System) not yet implemented - return error code
        print("Error: Eval system (F11) not yet implemented", file=sys.stderr)
        return 1
        
    try:
        from langagent.runtime.dir_loader import RuntimeDirLoader
        from langagent.runtime.config_resolver import RuntimeConfigResolver
        from langagent.runtime.exit_handler import RuntimeExitHandler
        from langagent.cli.output_formatter import format_eval_report_stdout
        
        # Stage 1: Load agent directory
        dir_loader = RuntimeDirLoader()
        loaded = dir_loader.load(args.agent_dir)
        
        # Stage 2: Resolve runtime config
        config_resolver = RuntimeConfigResolver()
        config = config_resolver.resolve(args.cli_args, args.agent_dir)
        
        # Stage 3: Construct eval args dict per FR-CLI-025
        eval_args = {
            'cli_args': vars(args),  # Convert CliArgs to dict
            'grader_only': args.cli_args.get('grader_only'),
            'task': args.cli_args.get('task'),
        }
        
        # Run evaluation
        result = eval_runner_run(args.agent_dir, config=config, args=eval_args)
        
        # Format and print report to stdout
        report_output = format_eval_report_stdout(result.eval_report)
        print(report_output)
        
        # Cleanup with eval_report
        exit_handler = RuntimeExitHandler()
        return exit_handler.cleanup(result.final_state, config, eval_report=result.eval_report)
        
    except KeyboardInterrupt:
        print("\nEval interrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        # Map eval errors to exit codes per FR-CLI-027
        error_name = type(e).__name__
        
        if error_name == "EvalsDirMissingError":
            print(f"Error: evals/ directory not found in {args.agent_dir}", file=sys.stderr)
            return 66  # Per workflow.md §langagent eval failure mode
        elif error_name == "EvalTimeoutError":
            print(f"Error: Evaluation timed out: {e}", file=sys.stderr)
            return 70
        elif error_name == "EvalGraderUnknownError":
            print(f"Error: Unknown grader type: {e}", file=sys.stderr)
            return 78
        elif error_name == "AgentDirNotFoundError":
            print(f"Error: Agent directory not found: {args.agent_dir}", file=sys.stderr)
            return 65
        else:
            # Generic eval error
            print(f"Error during eval: {e}", file=sys.stderr)
            return 1


def _dispatch_doctor(args: CliArgs) -> int:
    """Handle doctor subcommand (stub implementation).
    
    TODO: Full implementation per FR-CLI-019:
    1. Load agent directory (F06 dir_loader)
    2. Resolve runtime config (F07 config_resolver)
    3. Build doctor probes (F08 main_loop_dispatcher)
    4. Run doctor checks (F09 exit_handler)
    5. Format and print report
    6. Cleanup with doctor_report
    
    Args:
        args: Parsed CLI arguments with subcommand='doctor'
        
    Returns:
        Exit code (0 for stub, error codes per FR-CLI-027 when implemented)
    """
    # Stub implementation - to be replaced with actual doctor logic
    print("doctor command not yet implemented", file=sys.stderr)
    return 0


def main() -> None:
    """Main entry point for CLI.
    
    Orchestrates parse_argv -> dispatch -> sys.exit flow.
    """
    try:
        args = parse_argv(sys.argv[1:])
        exit_code = dispatch(args)
        sys.exit(exit_code)
    except KeyboardInterrupt:
        # Ctrl-C interrupt -> exit code 130
        sys.exit(130)
    except Exception as e:
        # Unhandled exception -> exit code 1
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
