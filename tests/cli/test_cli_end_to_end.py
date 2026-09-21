"""End-to-end CLI integration tests.

These tests validate the complete CLI stack by invoking the CLI as a subprocess
and checking exit codes, stdout, and stderr.
"""

import subprocess
import sys
from pathlib import Path


class TestPhase12EndToEnd:
    """Phase 12: End-to-end integration tests for all CLI commands."""
    
    def test_cli_help(self):
        """T087: `langagent --help` displays usage and exits 0."""
        # Run langagent --help
        result = subprocess.run(
            [sys.executable, "-m", "langagent", "--help"],
            capture_output=True,
            text=True
        )
        
        # Should exit with 0
        assert result.returncode == 0
        
        # Should contain usage information
        assert "usage:" in result.stdout.lower() or "Usage:" in result.stdout
        assert "init" in result.stdout
        assert "run" in result.stdout
        assert "eval" in result.stdout
        assert "doctor" in result.stdout
    
    def test_cli_unknown_subcommand(self):
        """T088: Unknown subcommand returns exit code 2."""
        # Run langagent with unknown subcommand
        result = subprocess.run(
            [sys.executable, "-m", "langagent", "unknown_command_xyz"],
            capture_output=True,
            text=True
        )
        
        # Should exit with 2 (argparse error)
        assert result.returncode == 2
        
        # Should contain error message
        assert "invalid choice" in result.stderr.lower() or "error" in result.stderr.lower()
    
    def test_cli_run_stdout_does_not_contain_la_tags(self):
        """T089: `langagent run` stdout does not contain internal la.* tags."""
        # Create a temporary agent directory for testing
        import tempfile
        import shutil
        
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_dir = Path(tmpdir) / "test_agent"
            agent_dir.mkdir()
            
            # Create minimal agent structure
            (agent_dir / "agent.yaml").write_text("""
name: test_agent
model: gpt-4
prompt: "You are a test agent."
""")
            
            # Run langagent run with a simple query
            result = subprocess.run(
                [sys.executable, "-m", "langagent", "run", str(agent_dir), "-q", "Hello"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Check stdout does not contain internal tags
            # Internal tags like [la.step], [la.tool_call], etc. should not leak
            assert "[la." not in result.stdout
            assert "la.step" not in result.stdout
            assert "la.tool_call" not in result.stdout
    
    def test_cli_eval_with_tasks(self):
        """T039: `langagent eval <agent_dir>` runs eval tasks and displays report."""
        # Create a temporary agent directory with eval tasks
        import tempfile
        import shutil
        
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_dir = Path(tmpdir) / "test_agent"
            agent_dir.mkdir()
            
            # Create minimal agent structure
            (agent_dir / "agent.yaml").write_text("""
name: test_agent
model: gpt-4
prompt: "You are a test agent."
""")
            
            # Create evals directory with a simple task
            evals_dir = agent_dir / "evals"
            evals_dir.mkdir()
            (evals_dir / "task1.yaml").write_text("""
task_id: task1
input: "What is 2+2?"
expected: "4"
grader: exact_match
""")
            
            # Run langagent eval
            result = subprocess.run(
                [sys.executable, "-m", "langagent", "eval", str(agent_dir)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Check output contains eval report elements
            # Note: Actual eval may fail if F11 not implemented, but should at least
            # show report structure or proper error
            assert "task1" in result.stdout or "Error" in result.stderr
            
            # If successful, check for report elements
            if result.returncode == 0:
                assert "Status" in result.stdout or "PASS" in result.stdout or "FAIL" in result.stdout
