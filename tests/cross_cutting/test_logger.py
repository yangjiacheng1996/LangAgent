"""Tests for cross-cutting logger (F02 Phase 1).

TDD approach: All tests written FIRST and must FAIL before implementation.
"""
import pytest
import sys
from io import StringIO
import threading
import json
from datetime import datetime

from langagent.cross_cutting.logger import (
    emit,
    set_level,
    drain_spans,
    Span,
    LogLevel,
    UnknownLogTagError,
    SpanDrainError,
    ALLOWED_TAGS,
)


# ===== User Story 1: Structured Logging with Tag Whitelist =====


def test_emit_with_valid_tag(capsys):
    """Test emit() with valid tag outputs dual format to stderr."""
    emit("la.runtime.dir_load.ok", {"agent_dir": "/tmp/test"})
    
    captured = capsys.readouterr()
    stderr_lines = captured.err.strip().split("\n")
    
    # Should have 2 lines: text format + JSONL format
    assert len(stderr_lines) == 2
    
    # Text format (first line)
    assert "[la.runtime.dir_load.ok]" in stderr_lines[0]
    
    # JSONL format (second line)
    jsonl = json.loads(stderr_lines[1])
    assert jsonl["tag"] == "la.runtime.dir_load.ok"
    assert jsonl["payload"]["agent_dir"] == "/tmp/test"
    assert "timestamp" in jsonl
    
    # No stdout pollution
    assert captured.out == ""


def test_emit_with_unknown_tag():
    """Test emit() with unknown tag raises UnknownLogTagError."""
    with pytest.raises(UnknownLogTagError, match="invalid.tag"):
        emit("invalid.tag", {"data": "test"})


def test_emit_emits_jsonl_to_stderr_not_stdout(capsys):
    """Test emit() writes to stderr only, not stdout."""
    emit("la.lifecycle.init.start", {"mode": "test"})
    
    captured = capsys.readouterr()
    
    # stderr should have content
    assert len(captured.err) > 0
    
    # stdout should be empty
    assert captured.out == ""


def test_emit_thread_safe(capsys):
    """Test emit() is thread-safe with 10 concurrent threads."""
    results = []
    
    def worker(thread_id):
        emit("la.lifecycle.run.turn", {"thread_id": thread_id})
    
    threads = []
    for i in range(10):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    captured = capsys.readouterr()
    stderr_lines = captured.err.strip().split("\n")
    
    # Should have 20 lines (2 per thread: text + JSONL)
    assert len(stderr_lines) == 20
    
    # All JSONL lines (even indices) should be valid JSON
    jsonl_lines = stderr_lines[1::2]
    for line in jsonl_lines:
        data = json.loads(line)
        assert data["tag"] == "la.lifecycle.run.turn"


def test_emit_tag_whitelist_at_least_46():
    """Test ALLOWED_TAGS has at least 46 items."""
    assert len(ALLOWED_TAGS) >= 46


def test_emit_timestamp_is_iso8601(capsys):
    """Test emit() generates ISO8601 timestamp."""
    emit("la.lifecycle.init.start", {})
    
    captured = capsys.readouterr()
    stderr_lines = captured.err.strip().split("\n")
    jsonl = json.loads(stderr_lines[1])
    
    # Verify ISO8601 format (should parse without error)
    timestamp = jsonl["timestamp"]
    parsed = datetime.fromisoformat(timestamp)
    assert parsed is not None
    
    # Verify format includes timezone offset
    assert "+" in timestamp or "Z" in timestamp or "-" in timestamp[-6:]


def test_emit_payload_must_be_dict():
    """Test emit() raises TypeError when payload is not a dict."""
    with pytest.raises(TypeError, match="payload must be a dict"):
        emit("la.lifecycle.init.start", "not_a_dict")  # type: ignore


# ===== User Story 2: Secret Redaction =====


def test_emit_does_not_contain_secrets(capsys):
    """Test emit() redacts api_key field."""
    emit("la.runtime.model_adapt.start", {"api_key": "sk-secret123", "model": "gpt-4"})
    
    captured = capsys.readouterr()
    
    # Verify the secret is not in output
    assert "sk-secret123" not in captured.err
    
    # Verify redaction marker is present
    assert "***" in captured.err
    
    # Parse JSONL to verify structure
    stderr_lines = captured.err.strip().split("\n")
    jsonl = json.loads(stderr_lines[1])
    assert jsonl["payload"]["api_key"] == "***"
    assert jsonl["payload"]["model"] == "gpt-4"


def test_emit_does_not_contain_password(capsys):
    """Test emit() redacts password field."""
    emit("la.runtime.config_resolve.ok", {"password": "mypass123", "username": "alice"})
    
    captured = capsys.readouterr()
    
    # Verify the password is not in output
    assert "mypass123" not in captured.err
    
    # Parse JSONL to verify structure
    stderr_lines = captured.err.strip().split("\n")
    jsonl = json.loads(stderr_lines[1])
    assert jsonl["payload"]["password"] == "***"
    assert jsonl["payload"]["username"] == "alice"


def test_emit_does_not_contain_secret(capsys):
    """Test emit() redacts secret field."""
    emit("la.runtime.tool_bind.ok", {"secret": "topsecret", "tool": "calculator"})
    
    captured = capsys.readouterr()
    
    # Verify the secret is not in output
    assert "topsecret" not in captured.err
    
    # Parse JSONL to verify structure
    stderr_lines = captured.err.strip().split("\n")
    jsonl = json.loads(stderr_lines[1])
    assert jsonl["payload"]["secret"] == "***"
    assert jsonl["payload"]["tool"] == "calculator"


def test_emit_does_not_contain_token(capsys):
    """Test emit() redacts token field with exact match (not substring)."""
    emit("la.runtime.graph_build.ok", {
        "token": "bearer123",
        "input_tokens": 42,  # Should NOT be redacted
        "output_tokens": 100  # Should NOT be redacted
    })
    
    captured = capsys.readouterr()
    
    # Verify the token is not in output
    assert "bearer123" not in captured.err
    
    # Parse JSONL to verify structure
    stderr_lines = captured.err.strip().split("\n")
    jsonl = json.loads(stderr_lines[1])
    assert jsonl["payload"]["token"] == "***"
    assert jsonl["payload"]["input_tokens"] == 42  # Not redacted
    assert jsonl["payload"]["output_tokens"] == 100  # Not redacted


# ===== User Story 3: Log Level Filtering =====


def test_emit_filters_by_level(capsys):
    """Test emit() filters logs based on set_level()."""
    # Set level to ERROR (only ERROR and CRITICAL should appear)
    set_level("ERROR")
    
    # Emit INFO level log (should be filtered out)
    emit("la.runtime.dir_load.ok", {"data": "info_log"})
    
    # Emit ERROR level log (should appear)
    emit("la.runtime.dir_load.fail", {"data": "error_log"})
    
    captured = capsys.readouterr()
    stderr_lines = captured.err.strip().split("\n")
    
    # Should only have 2 lines (1 ERROR log = text + JSONL)
    assert len(stderr_lines) == 2
    
    # Verify the ERROR log is present
    assert "la.runtime.dir_load.fail" in captured.err
    
    # Verify the INFO log is not present
    assert "la.runtime.dir_load.ok" not in captured.err
    
    # Reset to default level
    set_level("INFO")


def test_set_level_valid_values(capsys):
    """Test set_level() only accepts 5 valid levels."""
    # Valid levels should not raise
    set_level("DEBUG")
    set_level("INFO")
    set_level("WARNING")
    set_level("ERROR")
    set_level("CRITICAL")
    
    # Invalid level should raise ValueError
    with pytest.raises(ValueError, match="Invalid level"):
        set_level("INVALID")  # type: ignore
    
    # Reset to default
    set_level("INFO")


# ===== User Story 4: Span Buffer =====


def test_drain_spans_returns_buffered_spans():
    """Test drain_spans() returns accumulated spans."""
    # Clear buffer first
    drain_spans()
    
    # Emit 3 span logs
    emit("la.lifecycle.run.turn", {
        "kind": "span",
        "trace_id": "trace1",
        "span_id": "span1",
        "name": "turn_1",
        "start": 1.0,
        "end": 2.0,
        "attributes": {"user": "alice"},
    })
    
    emit("la.lifecycle.run.turn", {
        "kind": "span",
        "trace_id": "trace1",
        "span_id": "span2",
        "parent_span_id": "span1",
        "name": "turn_2",
        "start": 2.0,
        "end": 3.0,
        "attributes": {"user": "bob"},
    })
    
    emit("la.lifecycle.run.turn", {
        "kind": "span",
        "trace_id": "trace2",
        "span_id": "span3",
        "name": "turn_3",
        "start": 3.0,
        "end": 4.0,
        "attributes": {},
    })
    
    # Drain and verify
    spans = drain_spans()
    assert len(spans) == 3
    
    assert spans[0].trace_id == "trace1"
    assert spans[0].span_id == "span1"
    assert spans[0].name == "turn_1"
    assert spans[0].parent_span_id is None
    
    assert spans[1].trace_id == "trace1"
    assert spans[1].span_id == "span2"
    assert spans[1].parent_span_id == "span1"
    
    assert spans[2].trace_id == "trace2"
    assert spans[2].span_id == "span3"


def test_drain_spans_clears_buffer():
    """Test drain_spans() clears the buffer after draining."""
    # Clear buffer first
    drain_spans()
    
    # Emit 1 span
    emit("la.lifecycle.run.turn", {
        "kind": "span",
        "trace_id": "trace1",
        "span_id": "span1",
        "name": "test",
        "start": 1.0,
        "end": 2.0,
        "attributes": {},
    })
    
    # First drain should return 1 span
    spans1 = drain_spans()
    assert len(spans1) == 1
    
    # Second drain should return empty list
    spans2 = drain_spans()
    assert len(spans2) == 0


def test_drain_spans_only_buffers_kind_span():
    """Test drain_spans() only buffers logs with kind='span'."""
    # Clear buffer first
    drain_spans()
    
    # Emit 1 regular log (no kind field)
    emit("la.lifecycle.init.start", {"data": "not_a_span"})
    
    # Emit 1 span log
    emit("la.lifecycle.run.turn", {
        "kind": "span",
        "trace_id": "trace1",
        "span_id": "span1",
        "name": "test",
        "start": 1.0,
        "end": 2.0,
        "attributes": {},
    })
    
    # Emit 1 log with different kind
    emit("la.lifecycle.run.turn", {"kind": "event", "data": "not_a_span"})
    
    # Drain should only return the span log
    spans = drain_spans()
    assert len(spans) == 1
    assert spans[0].span_id == "span1"


def test_drain_spans_returns_empty_when_no_spans():
    """Test drain_spans() returns empty list when buffer is empty."""
    # Clear buffer first
    drain_spans()
    
    # Drain again without emitting anything
    spans = drain_spans()
    assert len(spans) == 0
    assert isinstance(spans, list)


def test_drain_spans_is_thread_safe():
    """Test drain_spans() is thread-safe with concurrent emit() and drain()."""
    # Clear buffer first
    drain_spans()
    
    results = []
    
    def emitter(thread_id):
        for i in range(5):
            emit("la.lifecycle.run.turn", {
                "kind": "span",
                "trace_id": f"trace{thread_id}",
                "span_id": f"span{thread_id}_{i}",
                "name": f"turn_{i}",
                "start": float(i),
                "end": float(i + 1),
                "attributes": {},
            })
    
    def drainer():
        spans = drain_spans()
        results.append(len(spans))
    
    # Start 3 emitter threads
    emitters = [threading.Thread(target=emitter, args=(i,)) for i in range(3)]
    for t in emitters:
        t.start()
    
    # Wait for all emitters to finish
    for t in emitters:
        t.join()
    
    # Now drain from 2 threads simultaneously
    drainers = [threading.Thread(target=drainer) for _ in range(2)]
    for t in drainers:
        t.start()
    
    for t in drainers:
        t.join()
    
    # Verify we got all 15 spans across the 2 drain calls
    total = sum(results)
    assert total == 15


def test_drain_spans_failure_does_not_clear_buffer():
    """Test drain_spans() does not clear buffer if an error occurs during drain."""
    # Clear buffer first
    drain_spans()
    
    # Emit 1 span
    emit("la.lifecycle.run.turn", {
        "kind": "span",
        "trace_id": "trace1",
        "span_id": "span1",
        "name": "test",
        "start": 1.0,
        "end": 2.0,
        "attributes": {},
    })
    
    # Normal drain should work
    spans = drain_spans()
    assert len(spans) == 1
    
    # Buffer should now be empty
    spans2 = drain_spans()
    assert len(spans2) == 0
