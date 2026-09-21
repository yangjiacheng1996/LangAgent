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
    subcommand: str = Field(..., description="One of: init, run, eval, doctor, chat, version")
    agent_dir: str = Field(default=".", description="Path to agent directory")
    cli_args: dict[str, Any] = Field(default_factory=dict, description="Raw CLI args dict")
    
    # Init subcommand
    name: Optional[str] = Field(default=None, description="Agent name for init")
    
    # Run subcommand
    user: Optional[str] = Field(default=None, description="User prompt for run command")
    model: Optional[str] = Field(default=None, description="Model name override")
    model_provider: Optional[str] = Field(default=None, description="Model provider override")
    model_base_url: Optional[str] = Field(default=None, description="Model base URL override")
    checkpointer: Optional[str] = Field(default=None, description="Checkpointer type")
    middleware: Optional[str] = Field(default=None, description="Middleware list (comma-separated)")
    max_turns: int = Field(default=30, description="Maximum main loop turns")
    thread_id: Optional[str] = Field(default=None, description="Checkpointer thread ID")
    
    # Chat subcommand
    session_id: Optional[str] = Field(default=None, description="Chat session ID for persistence")
    
    # Eval subcommand
    grader_only: Optional[str] = Field(default=None, description="Filter tasks by grader type")
    task: Optional[str] = Field(default=None, description="Run specific task by ID")
    report_format: str = Field(default="table", description="Report output format")
    
    # Doctor subcommand
    checks: Optional[list[str]] = Field(default=None, description="Checks to run")
    
    @field_validator("subcommand")
    @classmethod
    def validate_subcommand(cls, v: str) -> str:
        """Validate subcommand is one of the 6 allowed values."""
        allowed = {"init", "run", "eval", "doctor", "chat", "version"}
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
    elif subcommand == "run":
        args = CliArgs(
            subcommand="run",
            agent_dir=raw_args.get("agent_dir", "."),
            user=raw_args.get("user"),
            model=raw_args.get("model"),
            model_provider=raw_args.get("model_provider"),
            model_base_url=raw_args.get("model_base_url"),
            checkpointer=raw_args.get("checkpointer"),
            middleware=raw_args.get("middleware"),
            max_turns=raw_args.get("max_turns", 30),
            thread_id=raw_args.get("thread_id"),
            cli_args=ns_to_cli_args(ns)
        )
    elif subcommand == "eval":
        args = CliArgs(
            subcommand="eval",
            agent_dir=raw_args.get("agent_dir", "."),
            grader_only=raw_args.get("grader_only"),
            task=raw_args.get("task"),
            report_format=raw_args.get("report_format", "table"),
            cli_args=ns_to_cli_args(ns)
        )
    elif subcommand == "doctor":
        args = CliArgs(
            subcommand="doctor",
            agent_dir=raw_args.get("agent_dir", "."),
            checks=raw_args.get("checks"),
            cli_args=ns_to_cli_args(ns)
        )
    elif subcommand == "chat":
        args = CliArgs(
            subcommand="chat",
            agent_dir=raw_args.get("agent_dir", "."),
            session_id=raw_args.get("session_id"),
            model=raw_args.get("model"),
            model_provider=raw_args.get("model_provider"),
            model_base_url=raw_args.get("model_base_url"),
            cli_args=ns_to_cli_args(ns)
        )
    elif subcommand == "version":
        args = CliArgs(
            subcommand="version",
            cli_args=ns_to_cli_args(ns)
        )
    else:
        # Fallback
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
    elif args.subcommand == "chat":
        return _dispatch_chat(args)
    elif args.subcommand == "version":
        return _dispatch_version(args)
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
    
    User input handling:
    - If --user is provided, use that as initial message
    - Otherwise, read from stdin (supporting echo "prompt" | langagent run)
    
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
        from langagent.primitives import checkpoint_adapter
        from langagent.primitives import state_graph_builder
        from langagent.runtime import main_loop_dispatcher
        from langagent.runtime.exit_handler import RuntimeExitHandler
        from langagent.cli.output_formatter import format_chat_message
        from langchain_core.messages import AIMessage, HumanMessage
        
        # Get user input from --user parameter or stdin
        user_input = None
        if args.user:
            # Use --user parameter
            user_input = args.user
        elif not sys.stdin.isatty():
            # Read from stdin (pipe or redirect)
            user_input = sys.stdin.read().strip()
        
        if not user_input:
            print("Error: No user input provided. Use --user parameter or pipe input via stdin.", file=sys.stderr)
            print("Examples:", file=sys.stderr)
            print("  langagent run --user '你好'", file=sys.stderr)
            print("  echo '你好' | langagent run", file=sys.stderr)
            return 2
        
        # Stage 1: Load agent directory
        loaded_agent = RuntimeDirLoader.load(args.agent_dir)
        
        # Stage 2: Resolve runtime config
        resolver = RuntimeConfigResolver()
        config = resolver.resolve(args.cli_args, args.agent_dir)
        
        # Stage 3: Create model and checkpoint
        model = chat_model_factory.create(config)
        checkpoint = checkpoint_adapter.create(config)
        
        # Stage 4: Merge config with model and checkpoint
        final_config = config.with_model(model).with_checkpoint(checkpoint)
        
        # Stage 5: Build state graph
        graph = state_graph_builder.build(loaded_agent, final_config, checkpoint)
        
        # Stage 6: Run main loop with initial user message
        max_turns = args.max_turns if args.max_turns else 30
        thread_id = args.thread_id if args.thread_id else "run_" + str(hash(user_input))[:8]
        initial_message = HumanMessage(content=user_input)
        final_state = main_loop_dispatcher.run_until_done(
            graph,
            state={"messages": [initial_message]},
            max_turns=max_turns,
            thread_id=thread_id
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
    
    Executes the evaluation pipeline:
    1. Run eval tasks (F11 eval_runner)
    2. Display results
    
    Args:
        args: Parsed CLI arguments with subcommand='eval'
        
    Returns:
        Exit code (0=all pass, >0=failures or errors)
    """
    try:
        # Import eval runner
        from langagent.eval.runner import run as eval_runner_run
        from langagent.cross_cutting.logger import emit
        
        # Emit start log
        emit("la.lifecycle.eval.start", {"agent_dir": args.agent_dir})
        
        # Run evaluation with filters
        result = eval_runner_run(
            agent_dir=args.agent_dir,
            grader_only=args.grader_only,
            task_id=args.task
        )
        
        # Format and print report summary
        report = result.eval_report
        print(f"\n{'='*60}")
        print(f"Eval Report: {args.agent_dir}")
        print(f"{'='*60}")
        print(f"Tasks run: {len(report.task_results)}")
        print(f"Pass rate: {report.pass_rate*100:.1f}% ({sum(1 for t in report.task_results if t['passed'])}/{len(report.task_results)})")
        
        if report.task_results:
            print(f"P50 latency: {report.p50_latency_ms:.1f}ms")
            print(f"P95 latency: {report.p95_latency_ms:.1f}ms")
        
        print(f"\nDetails:")
        for task in report.task_results:
            status = "✓ PASS" if task['passed'] else "✗ FAIL"
            print(f"  [{status}] {task['task_id']} ({task['latency_ms']:.0f}ms)")
            if task['error_message']:
                print(f"    Error: {task['error_message']}")
        
        print(f"{'='*60}\n")
        
        # Emit summary log
        emit("la.lifecycle.eval.summary", {
            "pass_rate": report.pass_rate,
            "total_tasks": len(report.task_results),
            "passed": sum(1 for t in report.task_results if t['passed']),
            "failed": sum(1 for t in report.task_results if not t['passed'])
        })
        
        return result.exit_code
        
    except KeyboardInterrupt:
        print("\nEval interrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        # Map eval errors to exit codes
        error_name = type(e).__name__
        
        if "NotFound" in error_name or "Missing" in error_name:
            print(f"Error: {e}", file=sys.stderr)
            return 66
        elif "Timeout" in error_name:
            print(f"Error: {e}", file=sys.stderr)
            return 70
        elif "Unknown" in error_name or "Grader" in error_name:
            print(f"Error: {e}", file=sys.stderr)
            return 78
        else:
            print(f"Error during eval: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
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


def _dispatch_chat(args: CliArgs) -> int:
    """Handle chat subcommand - interactive REPL with agent.
    
    Implements an interactive chat session with:
    - Persistent conversation history via session_id
    - Slash commands: /picture, /quit, /help
    - Real-time streaming of agent responses
    
    Args:
        args: Parsed CLI arguments with subcommand='chat'
        
    Returns:
        Exit code (0=success, 130=interrupted, 1=error)
    """
    try:
        # Import runtime modules
        from langagent.runtime.dir_loader import RuntimeDirLoader
        from langagent.runtime.config_resolver import RuntimeConfigResolver
        from langagent.runtime import chat_model_factory
        from langagent.primitives import checkpoint_adapter
        from langagent.primitives import state_graph_builder
        from langagent.runtime import main_loop_dispatcher
        from langagent.runtime.exit_handler import RuntimeExitHandler
        from langchain_core.messages import HumanMessage, AIMessage
        from langagent.cross_cutting import logger
        import base64
        import uuid
        import warnings
        import os
        
        # Enable silent mode for chat - suppress all logging output
        logger.set_silent_mode(True)
        
        # Suppress langchain warnings
        warnings.filterwarnings('ignore')
        os.environ['PYTHONWARNINGS'] = 'ignore'
        
        # Import readline for better input handling (arrow keys, history, etc.)
        try:
            import readline
            # Enable tab completion and history
            readline.parse_and_bind('tab: complete')
            readline.parse_and_bind('set editing-mode emacs')
        except ImportError:
            # readline not available on this platform (e.g., Windows)
            pass
        
        # Initialize session with thread_id
        session_id = args.session_id or str(uuid.uuid4())
        thread_id = session_id  # Use session_id as thread_id for checkpointer
        
        # Setup runtime (stages 1-5)
        loaded_agent = RuntimeDirLoader.load(args.agent_dir)
        resolver = RuntimeConfigResolver()
        config = resolver.resolve(args.cli_args, args.agent_dir)
        model = chat_model_factory.create(config)
        checkpoint = checkpoint_adapter.create(config)
        final_config = config.with_model(model).with_checkpoint(checkpoint)
        graph = state_graph_builder.build(loaded_agent, final_config, checkpoint)
        
        # Load existing conversation history from checkpointer if session exists
        messages = []
        try:
            # Try to get existing state from checkpointer
            existing_state = graph.get_state(config={"configurable": {"thread_id": thread_id}})
            if existing_state and existing_state.values.get("messages"):
                messages = list(existing_state.values["messages"])
                print(f"Loaded {len(messages)} messages from session: {session_id}")
        except Exception:
            # Session doesn't exist yet, start fresh
            pass
        
        # Print welcome message
        print(f"LangAgent Chat Session: {session_id}")
        print("Type your message and press Enter. Use /quit to exit, /help for commands.")
        print("-" * 60)
        
        # REPL loop
        while True:
            try:
                # Read user input
                user_input = input("\nYou: ").strip()
                
                if not user_input:
                    continue
                
                # Handle slash commands
                if user_input.startswith("/"):
                    command_parts = user_input.split(maxsplit=1)
                    command = command_parts[0].lower()
                    
                    if command == "/quit":
                        print("Goodbye!")
                        break
                    elif command == "/help":
                        print("\nAvailable commands:")
                        print("  /picture <path>  - Load image and send to agent")
                        print("  /quit            - Exit chat session")
                        print("  /help            - Show this help message")
                        continue
                    elif command == "/picture":
                        if len(command_parts) < 2:
                            print("Usage: /picture <path>")
                            continue
                        
                        image_path = command_parts[1]
                        try:
                            with open(image_path, "rb") as f:
                                image_data = base64.b64encode(f.read()).decode()
                            
                            # Create message with image
                            message = HumanMessage(
                                content=[
                                    {"type": "text", "text": "Please analyze this image:"},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                                ]
                            )
                            messages.append(message)
                            print(f"Image loaded: {image_path}")
                        except Exception as e:
                            print(f"Error loading image: {e}")
                            continue
                    else:
                        print(f"Unknown command: {command}. Type /help for available commands.")
                        continue
                else:
                    # Regular text message
                    messages.append(HumanMessage(content=user_input))
                
                # Run agent with current messages
                final_state = main_loop_dispatcher.run_until_done(
                    graph,
                    state={"messages": messages},
                    max_turns=30,
                    thread_id=thread_id
                )
                
                # Extract and display agent response
                updated_messages = final_state.get("messages", [])
                messages = updated_messages  # Update conversation history
                
                # Find and print the last AI message
                for msg in reversed(updated_messages):
                    if isinstance(msg, AIMessage):
                        print(f"\nAgent: {msg.content}")
                        break
                
            except KeyboardInterrupt:
                print("\n\nChat interrupted. Type /quit to exit or continue chatting.")
                continue
            except EOFError:
                print("\nGoodbye!")
                break
        
        # Cleanup
        exit_handler = RuntimeExitHandler()
        return exit_handler.cleanup({"messages": messages}, final_config)
        
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error during chat: {e}", file=sys.stderr)
        return 1


def _dispatch_version(args: CliArgs) -> int:
    """Handle version subcommand.
    
    Displays LangAgent version information including:
    - Version number
    - Git commit hash
    - Build metadata
    
    Args:
        args: Parsed CLI arguments with subcommand='version'
        
    Returns:
        Exit code (0=success)
    """
    try:
        # Try to import build metadata
        try:
            from langagent._build_metadata import __version__, __commit__
            print(f"LangAgent v{__version__}")
            print(f"Commit: {__commit__}")
        except ImportError:
            # Development mode - read from pyproject.toml
            try:
                import tomllib
                from pathlib import Path
                pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
                if pyproject_path.exists():
                    with open(pyproject_path, "rb") as f:
                        pyproject = tomllib.load(f)
                        version = pyproject.get("project", {}).get("version", "dev")
                        print(f"LangAgent v{version} (development mode)")
                else:
                    print("LangAgent (version unknown)")
            except Exception:
                print("LangAgent (version unknown)")
        
        return 0
        
    except Exception as e:
        print(f"Error retrieving version: {e}", file=sys.stderr)
        return 1


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
