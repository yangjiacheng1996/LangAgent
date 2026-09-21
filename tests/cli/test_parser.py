"""Tests for CLI argument parser (cli_parser module).

Test coverage:
- T010: argparse init subcommand accepts name positional arg
- T011: argparse init rejects invalid name with exit code 2
- T057-T061: Additional parser tests (Phase 7)
"""
import pytest
import argparse
from langagent.cli.parser import build_parser, ns_to_cli_args
from langagent.cli.runner import parse_argv


class TestParserInit:
    """Tests for 'init' subcommand argument parsing."""
    
    def test_parse_init_name(self):
        """T010: argparse init subcommand accepts name positional arg."""
        parser = build_parser()
        args = parser.parse_args(["init", "myagent"])
        
        assert args.subcommand == "init"
        assert args.name == "myagent"
    
    def test_parse_init_name_invalid(self):
        """T011: argparse init rejects invalid name (123invalid) with exit code 2."""
        parser = build_parser()
        
        # argparse raises SystemExit(2) on validation failure
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["init", "123invalid"])
        
        assert exc_info.value.code == 2


class TestParserRun:
    """Tests for 'run' subcommand argument parsing."""
    
    def test_parse_run_with_agent_dir(self):
        """T021: argparse run subcommand accepts optional agent_dir positional."""
        parser = build_parser()
        args = parser.parse_args(["run", "/path/to/agent"])
        
        assert args.subcommand == "run"
        assert args.agent_dir == "/path/to/agent"
    
    def test_parse_run_defaults_to_cwd(self):
        """T021: argparse run defaults agent_dir to current directory."""
        parser = build_parser()
        args = parser.parse_args(["run"])
        
        assert args.subcommand == "run"
        assert args.agent_dir == "."
    
    def test_parse_run_with_overrides(self):
        """T022: argparse run accepts --model, --model-provider, --checkpointer flags."""
        parser = build_parser()
        args = parser.parse_args([
            "run", 
            "--model", "gpt-4o",
            "--model-provider", "openai",
            "--checkpointer", "sqlite"
        ])
        
        assert args.subcommand == "run"
        assert args.model == "gpt-4o"
        assert args.model_provider == "openai"
        assert args.checkpointer == "sqlite"
    
    def test_parse_run_with_max_turns(self):
        """T022: argparse run accepts --max-turns flag."""
        parser = build_parser()
        args = parser.parse_args(["run", "--max-turns", "5"])
        
        assert args.subcommand == "run"
        assert args.max_turns == 5
    
    def test_parse_run_negative_max_turns(self):
        """T060a: argparse accepts negative --max-turns (validation happens at runtime)."""
        parser = build_parser()
        args = parser.parse_args(["run", "--max-turns", "-1"])
        
        # argparse type=int accepts negative values
        # Runtime validation should reject this later
        assert args.max_turns == -1


class TestParserEval:
    """Tests for 'eval' subcommand argument parsing."""
    
    def test_parse_eval_with_grader_only(self):
        """T035: argparse eval accepts --grader-only, --task, --report-format flags."""
        parser = build_parser()
        args = parser.parse_args([
            "eval",
            "--grader-only", "llm_judge",
            "--task", "user_greeting",
            "--report-format", "json"
        ])
        
        assert args.subcommand == "eval"
        assert args.grader_only == "llm_judge"
        assert args.task == "user_greeting"
        assert args.report_format == "json"
    
    def test_parse_eval_defaults(self):
        """T035: argparse eval has correct defaults."""
        parser = build_parser()
        args = parser.parse_args(["eval"])
        
        assert args.subcommand == "eval"
        assert args.agent_dir == "."
        assert args.grader_only is None
        assert args.task is None
        assert args.report_format == "table"


class TestParserDoctor:
    """Tests for 'doctor' subcommand argument parsing."""
    
    def test_parse_doctor_with_checks(self):
        """T047: argparse doctor accepts --checks flag (comma-separated list)."""
        parser = build_parser()
        args = parser.parse_args([
            "doctor",
            "--checks", "model,checkpointer"
        ])
        
        assert args.subcommand == "doctor"
        assert args.checks == "model,checkpointer"
    
    def test_parse_doctor_checks_comma_separated(self):
        """T060b: argparse accepts --checks as comma-separated list."""
        parser = build_parser()
        args = parser.parse_args(["doctor", "--checks", "model,checkpointer,skills,instructions"])
        
        assert args.subcommand == "doctor"
        assert args.checks == "model,checkpointer,skills,instructions"
    
    def test_parse_doctor_defaults(self):
        """T047: argparse doctor defaults to all checks."""
        parser = build_parser()
        args = parser.parse_args(["doctor"])
        
        assert args.subcommand == "doctor"
        assert args.agent_dir == "."
        assert args.checks is None  # None means run all checks


class TestParserGeneral:
    """General parser tests."""
    
    def test_build_parser_has_4_subcommands(self):
        """T057: build_parser has exactly 4 subcommands (no version/tui/serve/clean)."""
        parser = build_parser()
        subparsers_actions = [
            action for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        ]
        
        assert len(subparsers_actions) == 1
        subparser_map = subparsers_actions[0].choices
        assert set(subparser_map.keys()) == {"init", "run", "eval", "doctor"}
    
    def test_build_parser_no_extra_subcommands(self):
        """T058: build_parser does not include extra subcommands."""
        parser = build_parser()
        subparsers_actions = [
            action for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        ]
        
        subparser_map = subparsers_actions[0].choices
        assert "version" not in subparser_map
        assert "tui" not in subparser_map
        assert "serve" not in subparser_map
        assert "clean" not in subparser_map
    
    def test_unknown_flag_returns_exit_code_2(self):
        """T060: unknown CLI flag returns exit code 2 (argparse error)."""
        parser = build_parser()
        
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["run", "--unknown-flag"])
        
        assert exc_info.value.code == 2


class TestNsToCliArgs:
    """Tests for ns_to_cli_args() helper function."""
    
    def test_ns_to_cli_args_returns_dict(self):
        """T059: ns_to_cli_args() converts Namespace to dict."""
        parser = build_parser()
        ns = parser.parse_args(["run", "--model", "gpt-4o", "--max-turns", "5"])
        
        result = ns_to_cli_args(ns)
        
        assert isinstance(result, dict)
        assert result["subcommand"] == "run"
        assert result["model"] == "gpt-4o"
        assert result["max_turns"] == 5


class TestParseEval:
    """Phase 5: Tests for eval subcommand parser (T035)."""
    
    def test_parse_eval_with_grader_only(self):
        """T035: argparse eval accepts --grader-only, --task, --report-format flags."""
        argv = [
            "eval",
            "my_agent",
            "--grader-only", "exact_match",
            "--task", "task1",
            "--report-format", "json"
        ]
        
        args = parse_argv(argv)
        
        assert args.subcommand == "eval"
        assert args.agent_dir == "my_agent"
        assert args.cli_args["grader_only"] == "exact_match"
        assert args.cli_args["task"] == "task1"
        assert args.cli_args["report_format"] == "json"
    
    def test_parse_eval_defaults(self):
        """T035: eval subcommand uses defaults when flags not provided."""
        argv = ["eval"]
        
        args = parse_argv(argv)
        
        assert args.subcommand == "eval"
        assert args.agent_dir == "."
        assert args.cli_args.get("grader_only") is None
        assert args.cli_args.get("task") is None
        assert args.cli_args["report_format"] == "table"
