import json
from unittest.mock import Mock
from langagent.cli.output_formatter import (
    format_eval_report_stdout,
    format_eval_report,
    format_doctor_report_stdout,
    format_doctor_report,
    format_chat_message,
)


class TestFormatEvalReport:
    """Phase 5: Tests for eval report formatting (T038)."""
    
    def test_format_eval_report_stdout_compact(self):
        """T038: format_eval_report_stdout() returns compact ASCII table."""
        # Mock EvalReport structure
        mock_report = Mock()
        mock_report.tasks = [
            Mock(task_id="task1", status="PASS", latency_ms=123, grader="exact_match"),
            Mock(task_id="task2", status="FAIL", latency_ms=456, grader="contains"),
            Mock(task_id="task3", status="PASS", latency_ms=789, grader="llm_judge"),
        ]
        mock_report.pass_rate = 0.6667
        
        result = format_eval_report_stdout(mock_report)
        
        # Verify table structure
        assert "task1" in result
        assert "task2" in result
        assert "task3" in result
        assert "PASS" in result
        assert "FAIL" in result
        assert "123" in result
        assert "456" in result
        assert "789" in result
        assert "exact_match" in result
        assert "contains" in result
        assert "llm_judge" in result
        # Verify pass rate
        assert "66.67%" in result or "67%" in result


class TestPhase9OutputFormatterCore:
    """Phase 9: Core output formatter tests (T067-T073)."""
    
    def test_format_eval_report_json(self):
        """T067: format_eval_report() with report_format='json' outputs valid JSON."""
        mock_report = Mock()
        mock_report.tasks = [
            Mock(task_id="task1", status="PASS", latency_ms=100, grader="exact_match"),
            Mock(task_id="task2", status="FAIL", latency_ms=200, grader="contains"),
        ]
        mock_report.pass_rate = 0.5
        
        result = format_eval_report(mock_report, report_format="json")
        
        # Verify valid JSON
        parsed = json.loads(result)
        assert "tasks" in parsed
        assert len(parsed["tasks"]) == 2
        assert parsed["tasks"][0]["task_id"] == "task1"
        assert parsed["tasks"][0]["status"] == "PASS"
        assert parsed["tasks"][1]["task_id"] == "task2"
        assert parsed["pass_rate"] == 0.5
    
    def test_format_eval_report_table(self):
        """T068: format_eval_report() with report_format='table' outputs ASCII table."""
        mock_report = Mock()
        mock_report.tasks = [
            Mock(task_id="task1", status="PASS", latency_ms=100, grader="exact_match"),
        ]
        mock_report.pass_rate = 1.0
        
        result = format_eval_report(mock_report, report_format="table")
        
        # Verify table format with headers
        assert "EVAL REPORT" in result
        assert "task1" in result
        assert "PASS" in result
        assert "100" in result
        assert "exact_match" in result
        assert "100.00%" in result
        assert "=" in result  # Table borders
    
    def test_format_doctor_report(self):
        """T069: format_doctor_report() outputs check status and overall conclusion."""
        mock_report = Mock()
        mock_report.checks = [
            Mock(name="config_valid", passed=True, message="", details=""),
            Mock(name="dependencies_ok", passed=False, message="missing package", details="install foo"),
        ]
        mock_report.overall = "error"
        mock_report.runtime = Mock(model="gpt-4", checkpointer="sqlite")
        
        result = format_doctor_report(mock_report)
        
        # Verify detailed format
        assert "DOCTOR REPORT" in result
        assert "config_valid" in result
        assert "PASS" in result
        assert "dependencies_ok" in result
        assert "FAIL" in result
        assert "missing package" in result
        assert "install foo" in result
        assert "ERROR" in result.upper()
        assert "Runtime Configuration" in result
        assert "gpt-4" in result
        assert "sqlite" in result
    
    def test_format_chat_message_handles_tool_calls(self):
        """T070: format_chat_message() handles tool_calls field."""
        message_dict = {
            "content": "",
            "tool_calls": [
                {"name": "search", "args": {"query": "python"}}
            ]
        }
        
        result = format_chat_message(message_dict)
        
        # Should format tool calls
        assert "[assistant]" in result
        assert "tool_call" in result or "search" in result
    
    def test_format_chat_message_handles_empty_content(self):
        """T071: format_chat_message() handles empty content gracefully."""
        message_dict = {"content": ""}
        
        result = format_chat_message(message_dict)
        
        # Should not crash, should return valid format
        assert "[assistant]" in result
        assert result.endswith("\n")
    
    def test_format_chat_message_returns_assistant_line(self):
        """T072: format_chat_message() returns [assistant] line for AI messages."""
        message_dict = {"content": "Hello, how can I help?"}
        
        result = format_chat_message(message_dict)
        
        # Verify format
        assert result.startswith("[assistant]")
        assert "Hello, how can I help?" in result
        assert result.endswith("\n")


class TestPhase10ANSIColor:
    """Phase 10: ANSI color support with TTY detection (T074-T079)."""
    
    def test_format_disables_color_when_no_tty(self, monkeypatch):
        """T074: ANSI color disabled when stdout not a TTY."""
        import sys
        from langagent.cli.output_formatter import is_tty, colorize
        
        # Mock sys.stdout.isatty() to return False
        class FakeStdout:
            def isatty(self):
                return False
        
        monkeypatch.setattr(sys, 'stdout', FakeStdout())
        
        # Verify is_tty() returns False
        assert is_tty() is False
        
        # Verify colorize() returns plain text when not TTY
        result = colorize("error text", "red")
        assert result == "error text"
        assert "\033[" not in result  # No ANSI codes
    
    def test_format_enables_color_when_tty(self, monkeypatch):
        """T075: ANSI color enabled when stdout is a TTY."""
        import sys
        from langagent.cli.output_formatter import is_tty, colorize
        
        # Mock sys.stdout.isatty() to return True
        class FakeStdout:
            def isatty(self):
                return True
            def fileno(self):
                return 1
        
        monkeypatch.setattr(sys, 'stdout', FakeStdout())
        
        # Verify is_tty() returns True
        assert is_tty() is True
        
        # Verify colorize() returns ANSI codes when TTY
        result = colorize("success text", "green")
        assert "\033[" in result  # Contains ANSI codes
        assert "success text" in result


class TestPhase11Security:
    """Phase 11: Security - payload truncation and sensitive field sanitization (T080-T086)."""
    
    def test_format_truncates_long_payload(self):
        """T080: payload >1KB truncated to exactly 203 chars (200 + '...')."""
        from langagent.cli.output_formatter import truncate_payload
        
        # Create a 1025 byte payload
        long_payload = "x" * 1025
        
        result = truncate_payload(long_payload)
        
        # Should be exactly 203 characters (200 + "...")
        assert len(result) == 203
        assert result.endswith("...")
        assert result[:200] == "x" * 200
    
    def test_format_never_logs_secrets(self):
        """T081: sensitive fields replaced with '***'."""
        from langagent.cli.output_formatter import sanitize_sensitive_fields
        
        # Test all 6 sensitive field patterns
        sensitive_data = {
            "api_key": "secret123",
            "API_KEY": "secret456",
            "api-key": "secret789",
            "token": "bearer_token",
            "password": "mypassword",
            "secret": "mysecret",
            "auth": "authtoken",
            "normal_field": "normal_value",
        }
        
        result = sanitize_sensitive_fields(sensitive_data)
        
        # All sensitive fields should be replaced with "***"
        assert result["api_key"] == "***"
        assert result["API_KEY"] == "***"
        assert result["api-key"] == "***"
        assert result["token"] == "***"
        assert result["password"] == "***"
        assert result["secret"] == "***"
        assert result["auth"] == "***"
        # Normal fields should remain unchanged
        assert result["normal_field"] == "normal_value"
    
    def test_format_sanitizes_nested_fields(self):
        """T081: sanitize_sensitive_fields() handles nested dicts."""
        from langagent.cli.output_formatter import sanitize_sensitive_fields
        
        nested_data = {
            "config": {
                "api_key": "secret123",
                "database": {
                    "password": "dbpass",
                    "host": "localhost"
                }
            },
            "user": "john"
        }
        
        result = sanitize_sensitive_fields(nested_data)
        
        # Nested sensitive fields should be sanitized
        assert result["config"]["api_key"] == "***"
        assert result["config"]["database"]["password"] == "***"
        # Non-sensitive fields should remain
        assert result["config"]["database"]["host"] == "localhost"
        assert result["user"] == "john"
    
    def test_format_eval_report_stdout_does_not_print_secrets(self):
        """T082: eval report stdout does not print raw token values."""
        from langagent.cli.output_formatter import format_eval_report_stdout
        
        # Create report with sensitive data in task details
        mock_report = Mock()
        mock_report.tasks = [
            Mock(
                task_id="task1",
                status="PASS",
                latency_ms=100,
                grader="exact_match",
                details={"api_key": "secret123"}
            ),
        ]
        mock_report.pass_rate = 1.0
        
        result = format_eval_report_stdout(mock_report)
        
        # Should not contain the raw secret
        assert "secret123" not in result
    
    def test_format_chat_message_sanitizes_tool_calls(self):
        """T085: format_chat_message() sanitizes tool_calls before output."""
        from langagent.cli.output_formatter import format_chat_message
        
        # Chat message with tool_calls containing sensitive data
        message_dict = {
            "content": "Calling API...",
            "tool_calls": [
                {
                    "name": "fetch_data",
                    "args": {
                        "api_key": "secret123",
                        "endpoint": "/users"
                    }
                }
            ]
        }
        
        result = format_chat_message(message_dict)
        
        # Should not contain the raw secret
        assert "secret123" not in result
        # Should contain sanitized version
        assert "***" in result
    
    def test_format_chat_message_truncates_long_content(self):
        """T086: format_chat_message() truncates content >1KB."""
        from langagent.cli.output_formatter import format_chat_message
        
        # Chat message with very long content (2KB)
        message_dict = {
            "content": "x" * 2048,
            "tool_calls": []
        }
        
        result = format_chat_message(message_dict)
        
        # Should be truncated
        assert len(result) < 2048 + 100  # Some overhead for formatting
        assert "..." in result  # Truncation indicator


class TestPhase13ArchitectureConstraints:
    """Phase 13: Verify CLI output formatter does not violate architecture constraints."""
    
    def test_dispatch_cli_does_not_import_logger(self):
        """T092: CLI output_formatter does not import cross_cutting.logger (FR-CLI-023)."""
        import ast
        from pathlib import Path
        
        # Read the output_formatter.py source code
        formatter_path = Path(__file__).parent.parent.parent / "langagent" / "cli" / "output_formatter.py"
        source = formatter_path.read_text()
        
        # Parse AST
        tree = ast.parse(source)
        
        # Check all import statements
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("langagent.cross_cutting.logger"), \
                        f"CLI output_formatter imports {alias.name} which violates FR-CLI-023"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    assert not node.module.startswith("langagent.cross_cutting.logger"), \
                        f"CLI output_formatter imports from {node.module} which violates FR-CLI-023"
