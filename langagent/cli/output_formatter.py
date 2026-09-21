"""CLI output formatting for langagent reports and messages.

This module provides formatting functions for:
- Chat messages (stdout, no la.* tags)
- Eval reports (compact table, detailed file version)
- Doctor reports (check status, overall conclusion)
- ANSI color support with TTY detection
- Sensitive field sanitization
"""
import sys
from dataclasses import dataclass
from typing import Any


# ANSI color codes
ANSI_COLORS = {
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "bold": "\033[1m",
    "reset": "\033[0m",
}


def is_tty() -> bool:
    """Check if stdout is a TTY.
    
    Returns:
        True if stdout is a terminal, False otherwise
    """
    try:
        return sys.stdout.isatty()
    except (AttributeError, ValueError):
        return False


def colorize(text: str, color: str) -> str:
    """Apply ANSI color codes to text if TTY is detected.
    
    Args:
        text: Text to colorize
        color: Color name ('red', 'green', 'yellow', 'blue', 'bold')
        
    Returns:
        Colored text if TTY, plain text otherwise
    """
    if not is_tty():
        return text
    
    color_code = ANSI_COLORS.get(color, "")
    reset_code = ANSI_COLORS["reset"]
    
    if color_code:
        return f"{color_code}{text}{reset_code}"
    return text


def sanitize_sensitive_fields(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively sanitize sensitive fields in a dictionary.
    
    Replaces values of keys matching sensitive patterns with "***".
    Sensitive patterns: api_key, api-key, token, password, secret, auth
    (case-insensitive)
    
    Args:
        data: Dictionary to sanitize
        
    Returns:
        New dictionary with sensitive values replaced
    """
    # Sensitive field patterns (case-insensitive)
    sensitive_patterns = {
        "api_key", "api-key", "token", "password", "secret", "auth"
    }
    
    def is_sensitive(key: str) -> bool:
        """Check if a key matches sensitive patterns."""
        key_lower = key.lower().replace("_", "-")
        return key_lower in sensitive_patterns
    
    def sanitize_value(value: Any) -> Any:
        """Recursively sanitize a value."""
        if isinstance(value, dict):
            return {k: sanitize_value(v) if not is_sensitive(k) else "***" 
                    for k, v in value.items()}
        elif isinstance(value, list):
            return [sanitize_value(item) for item in value]
        else:
            return value
    
    return sanitize_value(data)


def truncate_payload(payload: str, max_length: int = 1024) -> str:
    """Truncate long payloads to prevent log spam.
    
    Args:
        payload: String to truncate
        max_length: Maximum length before truncation (default: 1024)
        
    Returns:
        Original string if <= max_length, else first 200 chars + "..."
    """
    if len(payload) <= max_length:
        return payload
    
    return payload[:200] + "..."


@dataclass
class FormatterContext:
    """Output formatting context with TTY detection."""
    
    is_tty: bool
    enable_color: bool
    terminal_width: int
    
    @classmethod
    def detect(cls) -> "FormatterContext":
        """Detect current terminal context."""
        is_tty = sys.stdout.isatty() if hasattr(sys.stdout, 'isatty') else False
        return cls(
            is_tty=is_tty,
            enable_color=is_tty,
            terminal_width=80  # Default, can be enhanced with shutil.get_terminal_size()
        )


def format_chat_message(message_dict: dict[str, Any]) -> str:
    """Format a chat message for stdout display.
    
    Args:
        message_dict: AIMessage.to_dict() result with 'content' field
        
    Returns:
        Formatted string like "[assistant] <content>\\n"
    """
    content = message_dict.get("content", "")
    tool_calls = message_dict.get("tool_calls", [])
    
    # Truncate long content
    content = truncate_payload(content)
    
    # If there are tool calls, format them
    if tool_calls:
        tool_parts = []
        for tool_call in tool_calls:
            name = tool_call.get("name", "unknown")
            args = tool_call.get("args", {})
            
            # Sanitize sensitive fields in args
            args = sanitize_sensitive_fields(args)
            
            # Format args as key=value pairs
            args_str = ", ".join(f"{k}={v}" for k, v in args.items())
            # Truncate long args
            args_str = truncate_payload(args_str, max_length=200)
            tool_parts.append(f"{name}({args_str})")
        
        tool_str = ", ".join(tool_parts)
        if content:
            return f"[assistant] {content} (tool_call: {tool_str})\n"
        else:
            return f"[assistant] (tool_call: {tool_str})\n"
    
    return f"[assistant] {content}\n"


def format_eval_report_stdout(eval_report: Any) -> str:
    """Format eval report for stdout (compact table).
    
    Args:
        eval_report: EvalReport from F11
        
    Returns:
        Multi-line string with compact ASCII table
    """
    lines = []
    
    # Header
    lines.append("Task ID       | Status | Latency | Grader")
    lines.append("--------------|--------|---------|------------------")
    
    # Task rows
    tasks = getattr(eval_report, 'tasks', [])
    for task in tasks:
        task_id = getattr(task, 'task_id', 'unknown')
        status = getattr(task, 'status', 'UNKNOWN')
        latency_ms = getattr(task, 'latency_ms', 0)
        grader = getattr(task, 'grader', 'unknown')
        
        # Apply color to status
        if status == "PASS":
            status_colored = colorize(status, "green")
        elif status == "FAIL":
            status_colored = colorize(status, "red")
        else:
            status_colored = status
        
        # Format row with fixed widths (color codes don't affect display width)
        lines.append(f"{task_id:<13} | {status_colored:<6} | {latency_ms:>4}ms  | {grader}")
    
    # Pass rate summary
    pass_rate = getattr(eval_report, 'pass_rate', 0.0)
    lines.append("")
    
    # Color the pass rate based on value
    pass_rate_str = f"{pass_rate * 100:.2f}%"
    if pass_rate >= 0.8:
        pass_rate_colored = colorize(pass_rate_str, "green")
    elif pass_rate >= 0.5:
        pass_rate_colored = colorize(pass_rate_str, "yellow")
    else:
        pass_rate_colored = colorize(pass_rate_str, "red")
    
    lines.append(f"Overall Pass Rate: {pass_rate_colored}")
    
    return "\n".join(lines) + "\n"


def format_eval_report(eval_report: Any, report_format: str = "table") -> str:
    """Format eval report for file persistence (detailed version).
    
    Args:
        eval_report: EvalReport from F11
        report_format: One of 'json', 'yaml', 'table'
        
    Returns:
        Multi-line string with detailed report
    """
    if report_format == "json":
        import json
        # Convert eval_report to dict for JSON serialization
        tasks = getattr(eval_report, 'tasks', [])
        report_dict = {
            'tasks': [
                {
                    'task_id': getattr(t, 'task_id', ''),
                    'status': getattr(t, 'status', ''),
                    'latency_ms': getattr(t, 'latency_ms', 0),
                    'grader': getattr(t, 'grader', '')
                }
                for t in tasks
            ],
            'pass_rate': getattr(eval_report, 'pass_rate', 0.0)
        }
        return json.dumps(report_dict, indent=2) + "\n"
    
    elif report_format == "yaml":
        # Simple YAML formatting without external dependency
        lines = ["tasks:"]
        tasks = getattr(eval_report, 'tasks', [])
        for task in tasks:
            lines.append(f"  - task_id: {getattr(task, 'task_id', '')}")
            lines.append(f"    status: {getattr(task, 'status', '')}")
            lines.append(f"    latency_ms: {getattr(task, 'latency_ms', 0)}")
            lines.append(f"    grader: {getattr(task, 'grader', '')}")
        lines.append(f"pass_rate: {getattr(eval_report, 'pass_rate', 0.0)}")
        return "\n".join(lines) + "\n"
    
    else:  # table format (more detailed than stdout version)
        lines = []
        lines.append("=" * 80)
        lines.append("EVAL REPORT - DETAILED")
        lines.append("=" * 80)
        lines.append("")
        
        tasks = getattr(eval_report, 'tasks', [])
        for task in tasks:
            task_id = getattr(task, 'task_id', 'unknown')
            status = getattr(task, 'status', 'UNKNOWN')
            latency_ms = getattr(task, 'latency_ms', 0)
            grader = getattr(task, 'grader', 'unknown')
            
            lines.append(f"Task: {task_id}")
            lines.append(f"  Status: {status}")
            lines.append(f"  Latency: {latency_ms}ms")
            lines.append(f"  Grader: {grader}")
            lines.append("")
        
        pass_rate = getattr(eval_report, 'pass_rate', 0.0)
        lines.append(f"Overall Pass Rate: {pass_rate * 100:.2f}%")
        lines.append("=" * 80)
        
        return "\n".join(lines) + "\n"


def format_doctor_report_stdout(doctor_report: Any) -> str:
    """Format doctor report for stdout (compact check list).
    
    Args:
        doctor_report: DoctorReport from F09
        
    Returns:
        Multi-line string with check status lines
    """
    lines = []
    lines.append("Doctor Check Results:")
    lines.append("")
    
    checks = getattr(doctor_report, 'checks', [])
    for check in checks:
        check_name = getattr(check, 'name', 'unknown')
        passed = getattr(check, 'passed', False)
        message = getattr(check, 'message', '')
        
        if passed:
            status_line = colorize(f"✓ {check_name}: ok", "green")
            lines.append(status_line)
        else:
            status_line = colorize(f"✗ {check_name}: error", "red")
            if message:
                lines.append(f"{status_line} - {message}")
            else:
                lines.append(status_line)
    
    lines.append("")
    overall = getattr(doctor_report, 'overall', 'unknown')
    if overall == 'ok':
        overall_line = colorize("Overall: ✓ All checks passed", "green")
        lines.append(overall_line)
    else:
        overall_line = colorize("Overall: ✗ Some checks failed", "red")
        lines.append(overall_line)
    
    return "\n".join(lines) + "\n"


def format_doctor_report(doctor_report: Any) -> str:
    """Format doctor report for file persistence (detailed version).
    
    Args:
        doctor_report: DoctorReport from F09
        
    Returns:
        Multi-line string with detailed report and recommendations
    """
    lines = []
    lines.append("=" * 80)
    lines.append("DOCTOR REPORT - DETAILED")
    lines.append("=" * 80)
    lines.append("")
    
    checks = getattr(doctor_report, 'checks', [])
    for check in checks:
        check_name = getattr(check, 'name', 'unknown')
        passed = getattr(check, 'passed', False)
        message = getattr(check, 'message', '')
        details = getattr(check, 'details', '')
        
        lines.append(f"Check: {check_name}")
        lines.append(f"  Status: {'PASS' if passed else 'FAIL'}")
        if message:
            lines.append(f"  Message: {message}")
        if details:
            lines.append(f"  Details: {details}")
        lines.append("")
    
    overall = getattr(doctor_report, 'overall', 'unknown')
    lines.append(f"Overall Status: {overall.upper()}")
    lines.append("")
    
    # Add runtime config snapshot if available
    runtime = getattr(doctor_report, 'runtime', None)
    if runtime:
        lines.append("Runtime Configuration Snapshot:")
        lines.append(f"  Model: {getattr(runtime, 'model', 'N/A')}")
        lines.append(f"  Checkpointer: {getattr(runtime, 'checkpointer', 'N/A')}")
        lines.append("")
    
    lines.append("=" * 80)
    
    return "\n".join(lines) + "\n"
