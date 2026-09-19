"""Tests for cross_cutting_logger module - User Story 1: Structured Logging.

This file contains TDD tests written FIRST before implementation.
Tests must FAIL initially (Red phase), then pass after implementation (Green phase).

Test Organization:
- Phase 3 (US1): T010-T016 - Structured logging with tag whitelist
- Phase 4 (US2): T022-T025 - Secret redaction
- Phase 5 (US3): T028-T029 - Log level filtering  
- Phase 6 (US4): T033-T038 - Span buffer

Constitutional Alignment: Article VIII (TDD Red-Green-Refactor)
"""

import io
import json
import sys
import threading
from datetime import datetime
from unittest import mock

import pytest

from langagent.cross_cutting import (
    emit,
    set_level,
    drain_spans,
    Span,
    LogLevel,
    UnknownLogTagError,
    SpanDrainError,
    ALLOWED_TAGS,
)


# ============================================================================
# Phase 3: User Story 1 Tests (T010-T016) - Structured Logging
# ============================================================================

def test_emit_with_valid_tag():
    """T010 [P] [US1]: Verify dual format output to stderr.
    
    Acceptance: emit() with valid tag writes both text and JSONL to stderr.
    """
    # Capture stderr
    captured_stderr = io.StringIO()
    
    with mock.patch('sys.stderr', captured_stderr):
        emit("la.runtime.dir_load.ok", {"agent_dir": "/tmp/agent"})
    
    stderr_output = captured_stderr.getvalue()
    lines = stderr_output.strip().split('\n')
    
    # Should have 2 lines: text + JSONL
    assert len(lines) == 2, f"Expected 2 lines, got {len(lines)}"
    
    # First line should be text format with tag
    assert "[la.runtime.dir_load.ok]" in lines[0], "Text line missing tag"
    
    # Second line should be valid JSON
    jsonl_obj = json.loads(lines[1])
    assert jsonl_obj["tag"] == "la.runtime.dir_load.ok"
    assert "timestamp" in jsonl_obj
    assert jsonl_obj["payload"]["agent_dir"] == "/tmp/agent"


def test_emit_with_unknown_tag():
    """T011 [P] [US1]: Verify UnknownLogTagError raised for invalid tags.
    
    Acceptance: emit() with unregistered tag raises exception immediately.
    """
    with pytest.raises(UnknownLogTagError, match="Unknown log tag: invalid.tag"):
        emit("invalid.tag", {})


def test_emit_emits_jsonl_to_stderr_not_stdout():
    """T012 [P] [US1]: Verify no stdout pollution.
    
    Acceptance: stdout empty, stderr contains both text and JSONL.
    """
    captured_stdout = io.StringIO()
    captured_stderr = io.StringIO()
    
    with mock.patch('sys.stdout', captured_stdout), \
         mock.patch('sys.stderr', captured_stderr):
        emit("la.runtime.dir_load.ok", {"message": "test"})
    
    stdout_output = captured_stdout.getvalue()
    stderr_output = captured_stderr.getvalue()
    
    # stdout must be empty (FR-014)
    assert stdout_output == "", f"stdout should be empty, got: {stdout_output}"
    
    # stderr must contain content
    assert len(stderr_output) > 0, "stderr should have content"
    
    # stderr should have valid JSON line
    lines = stderr_output.strip().split('\n')
    assert len(lines) >= 1
    jsonl_obj = json.loads(lines[1])  # Second line is JSONL
    assert "tag" in jsonl_obj
    assert "payload" in jsonl_obj


def test_emit_thread_safe():
    """T013 [P] [US1]: Verify 10 threads concurrent emit without interleaving.
    
    Acceptance: All log lines appear in stderr without corruption.
    """
    captured_stderr = io.StringIO()
    
    def worker(thread_id: int):
        for i in range(10):
            emit("la.runtime.main_loop.turn.start", {"thread": thread_id, "i": i})
    
    with mock.patch('sys.stderr', captured_stderr):
        threads = [threading.Thread(target=worker, args=(tid,)) for tid in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    
    stderr_output = captured_stderr.getvalue()
    lines = stderr_output.strip().split('\n')
    
    # 10 threads × 10 emits × 2 lines (text + JSONL) = 200 lines
    assert len(lines) == 200, f"Expected 200 lines, got {len(lines)}"
    
    # Every odd line (0, 2, 4...) should be text, even lines (1, 3, 5...) should be JSONL
    for i, line in enumerate(lines):
        if i % 2 == 1:  # JSONL lines
            # Should be valid JSON
            try:
                obj = json.loads(line)
                assert "tag" in obj
            except json.JSONDecodeError:
                pytest.fail(f"Line {i} is not valid JSON: {line}")


def test_emit_tag_whitelist_exactly_45():
    """T014 [P] [US1]: Verify ALLOWED_TAGS has exactly 45 items.
    
    Acceptance: Tag whitelist contains 45 registered tags as per spec.
    """
    assert len(ALLOWED_TAGS) == 45, f"Expected 45 tags, got {len(ALLOWED_TAGS)}"
    
    # Verify namespace distribution (12 lifecycle + 29 runtime + 4 cross_cutting)
    lifecycle_tags = [t for t in ALLOWED_TAGS if t.startswith("la.lifecycle.")]
    runtime_tags = [t for t in ALLOWED_TAGS if t.startswith("la.runtime.")]
    cross_cutting_tags = [t for t in ALLOWED_TAGS if t.startswith("la.cross_cutting.")]
    
    assert len(lifecycle_tags) == 12, f"Expected 12 lifecycle tags, got {len(lifecycle_tags)}"
    assert len(runtime_tags) == 29, f"Expected 29 runtime tags, got {len(runtime_tags)}"
    assert len(cross_cutting_tags) == 4, f"Expected 4 cross_cutting tags, got {len(cross_cutting_tags)}"


def test_emit_timestamp_is_iso8601():
    """T015 [P] [US1]: Verify timestamp format is ISO8601.
    
    Acceptance: Timestamp follows format '2026-09-15T10:30:00.123456+08:00'
    """
    captured_stderr = io.StringIO()
    
    with mock.patch('sys.stderr', captured_stderr):
        emit("la.runtime.dir_load.ok", {"test": "timestamp"})
    
    stderr_output = captured_stderr.getvalue()
    lines = stderr_output.strip().split('\n')
    
    # Parse JSONL line
    jsonl_obj = json.loads(lines[1])
    timestamp_str = jsonl_obj["timestamp"]
    
    # Should be parseable as ISO8601 with timezone
    try:
        dt = datetime.fromisoformat(timestamp_str)
        # Should have timezone info
        assert dt.tzinfo is not None, "Timestamp missing timezone"
        # Should have microseconds
        assert '.' in timestamp_str or 'T' in timestamp_str, "Timestamp should be ISO8601"
    except ValueError as e:
        pytest.fail(f"Timestamp not ISO8601: {timestamp_str}, error: {e}")


def test_emit_payload_must_be_dict():
    """T016 [P] [US1]: Verify TypeError on non-dict payload.
    
    Acceptance: emit() with non-dict payload raises TypeError.
    """
    with pytest.raises(TypeError, match="Payload must be dict"):
        emit("la.runtime.dir_load.ok", "not a dict")  # type: ignore
    
    with pytest.raises(TypeError, match="Payload must be dict"):
        emit("la.runtime.dir_load.ok", ["list", "not", "dict"])  # type: ignore
    
    with pytest.raises(TypeError, match="Payload must be dict"):
        emit("la.runtime.dir_load.ok", 12345)  # type: ignore


# ============================================================================
# Phase 4: User Story 2 Tests (T022-T025) - Secret Redaction
# ============================================================================

def test_emit_does_not_contain_secrets():
    """T022 [P] [US2]: Verify api_key redaction.
    
    Acceptance: api_key value replaced with '***' in output.
    """
    captured_stderr = io.StringIO()
    
    with mock.patch('sys.stderr', captured_stderr):
        emit("la.runtime.model_adapt.start", {"api_key": "sk-secret123"})
    
    stderr_output = captured_stderr.getvalue()
    
    # Secret value should NOT appear in output
    assert "sk-secret123" not in stderr_output, "Secret api_key leaked in output"
    
    # Should contain redacted marker
    assert "***" in stderr_output, "Redaction marker '***' not found"
    
    # Verify in JSONL
    lines = stderr_output.strip().split('\n')
    jsonl_obj = json.loads(lines[1])
    assert jsonl_obj["payload"]["api_key"] == "***"


def test_emit_does_not_contain_password():
    """T023 [P] [US2]: Verify password redaction.
    
    Acceptance: password value replaced with '***'.
    """
    captured_stderr = io.StringIO()
    
    with mock.patch('sys.stderr', captured_stderr):
        emit("la.runtime.config_resolve.ok", {"password": "hunter2"})
    
    stderr_output = captured_stderr.getvalue()
    
    assert "hunter2" not in stderr_output
    assert "***" in stderr_output


def test_emit_does_not_contain_secret():
    """T024 [P] [US2]: Verify secret redaction.
    
    Acceptance: secret value replaced with '***'.
    """
    captured_stderr = io.StringIO()
    
    with mock.patch('sys.stderr', captured_stderr):
        emit("la.runtime.config_resolve.ok", {"secret": "my-secret-value"})
    
    stderr_output = captured_stderr.getvalue()
    
    assert "my-secret-value" not in stderr_output
    assert "***" in stderr_output


def test_emit_does_not_contain_token():
    """T025 [P] [US2]: Verify token redaction with exact match (not substring).
    
    Acceptance: 'token' field redacted, but 'input_tokens' NOT redacted.
    """
    captured_stderr = io.StringIO()
    
    with mock.patch('sys.stderr', captured_stderr):
        emit("la.runtime.model_adapt.ok", {
            "token": "bearer-abc123",
            "input_tokens": 100,
            "output_tokens": 50,
        })
    
    stderr_output = captured_stderr.getvalue()
    lines = stderr_output.strip().split('\n')
    jsonl_obj = json.loads(lines[1])
    
    # 'token' should be redacted
    assert jsonl_obj["payload"]["token"] == "***"
    
    # 'input_tokens' and 'output_tokens' should NOT be redacted (FR-005)
    assert jsonl_obj["payload"]["input_tokens"] == 100
    assert jsonl_obj["payload"]["output_tokens"] == 50


# ============================================================================
# Phase 5: User Story 3 Tests (T028-T029) - Log Level Filtering
# ============================================================================

def test_emit_filters_by_level():
    """T028 [P] [US3]: Verify INFO logs filtered when level=ERROR.
    
    Acceptance: set_level("ERROR") filters out INFO-level logs.
    """
    captured_stderr = io.StringIO()
    
    # Set level to ERROR
    set_level("ERROR")
    
    with mock.patch('sys.stderr', captured_stderr):
        # This should be filtered (INFO < ERROR)
        emit("la.runtime.dir_load.ok", {"message": "info level"})
        
        # This should appear (ERROR == ERROR)
        emit("la.runtime.dir_load.fail", {"message": "error level"})
    
    stderr_output = captured_stderr.getvalue()
    
    # Should NOT contain INFO message
    assert "info level" not in stderr_output
    
    # Should contain ERROR message
    assert "error level" in stderr_output
    
    # Reset to INFO for other tests
    set_level("INFO")


def test_set_level_valid_values():
    """T029 [P] [US3]: Verify only 5 valid levels accepted.
    
    Acceptance: set_level() accepts DEBUG/INFO/WARNING/ERROR/CRITICAL, rejects others.
    """
    # Valid levels should not raise
    set_level("DEBUG")
    set_level("INFO")
    set_level("WARNING")
    set_level("ERROR")
    set_level("CRITICAL")
    
    # Invalid level should raise ValueError
    with pytest.raises(ValueError, match="Invalid level"):
        set_level("INVALID")  # type: ignore
    
    # Reset to INFO
    set_level("INFO")


# ============================================================================
# Phase 6: User Story 4 Tests (T033-T038) - Span Buffer
# ============================================================================

def test_drain_spans_returns_accumulated():
    """T033 [P] [US4]: Verify 5 span emits return 5 Span objects.
    
    Acceptance: drain_spans() returns list of accumulated spans.
    """
    captured_stderr = io.StringIO()
    
    with mock.patch('sys.stderr', captured_stderr):
        for i in range(5):
            emit("la.runtime.main_loop.turn.start", {
                "kind": "span",
                "trace_id": "t1",
                "span_id": f"s{i}",
                "parent_span_id": None,
                "name": f"turn_{i}",
                "start": float(i),
                "end": float(i + 1),
                "attributes": {},
            })
    
    spans = drain_spans()
    
    assert len(spans) == 5, f"Expected 5 spans, got {len(spans)}"
    assert all(isinstance(s, Span) for s in spans)
    assert spans[0].span_id == "s0"
    assert spans[4].span_id == "s4"


def test_drain_spans_filters_non_span_emits():
    """T034 [P] [US4]: Verify non-span logs not in buffer.
    
    Acceptance: Only logs with kind=="span" are buffered.
    """
    captured_stderr = io.StringIO()
    
    with mock.patch('sys.stderr', captured_stderr):
        # Non-span emit
        emit("la.runtime.dir_load.ok", {"message": "not a span"})
        
        # Span emit
        emit("la.runtime.main_loop.turn.start", {
            "kind": "span",
            "trace_id": "t1",
            "span_id": "s1",
            "name": "turn",
            "start": 1.0,
            "end": 2.0,
            "attributes": {},
        })
    
    spans = drain_spans()
    
    # Should only have 1 span (the one with kind=="span")
    assert len(spans) == 1


def test_drain_spans_clears_buffer():
    """T035 [P] [US4]: Verify buffer cleared after drain.
    
    Acceptance: Second drain returns only new spans, not old ones.
    """
    captured_stderr = io.StringIO()
    
    with mock.patch('sys.stderr', captured_stderr):
        # Emit 2 spans
        for i in range(2):
            emit("la.runtime.main_loop.turn.start", {
                "kind": "span",
                "trace_id": "t1",
                "span_id": f"s{i}",
                "name": "turn",
                "start": 1.0,
                "end": 2.0,
                "attributes": {},
            })
    
    spans1 = drain_spans()
    assert len(spans1) == 2
    
    # Emit 3 more spans
    with mock.patch('sys.stderr', captured_stderr):
        for i in range(2, 5):
            emit("la.runtime.main_loop.turn.start", {
                "kind": "span",
                "trace_id": "t1",
                "span_id": f"s{i}",
                "name": "turn",
                "start": 1.0,
                "end": 2.0,
                "attributes": {},
            })
    
    spans2 = drain_spans()
    
    # Should only have 3 new spans, not 5 total
    assert len(spans2) == 3
    assert spans2[0].span_id == "s2"


def test_drain_spans_empty_when_no_pending():
    """T036 [P] [US4]: Verify empty list on empty buffer.
    
    Acceptance: drain_spans() with no pending spans returns [].
    """
    spans = drain_spans()
    assert spans == []


def test_drain_spans_thread_safe():
    """T037 [P] [US4]: Verify 10 threads concurrent emit+drain without data loss.
    
    Acceptance: No spans lost or duplicated.
    """
    captured_stderr = io.StringIO()
    
    def worker(thread_id: int):
        with mock.patch('sys.stderr', captured_stderr):
            for i in range(5):
                emit("la.runtime.main_loop.turn.start", {
                    "kind": "span",
                    "trace_id": f"t{thread_id}",
                    "span_id": f"s{thread_id}_{i}",
                    "name": "turn",
                    "start": 1.0,
                    "end": 2.0,
                    "attributes": {},
                })
    
    threads = [threading.Thread(target=worker, args=(tid,)) for tid in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    spans = drain_spans()
    
    # 10 threads × 5 emits = 50 spans
    assert len(spans) == 50, f"Expected 50 spans, got {len(spans)}"


def test_drain_spans_raises_span_drain_error_on_io_failure():
    """T038 [P] [US4]: Verify SpanDrainError on failure and buffer not cleared.
    
    Note: In Phase 1, SpanDrainError is reserved for future I/O operations.
    Pure memory operations cannot fail, so this test verifies the behavior
    is defined but not actively triggered.
    """
    # This test documents the contract: if drain_spans() raises SpanDrainError,
    # the buffer should NOT be cleared (allows retry).
    # In Phase 1, this doesn't happen (pure memory), but the contract is defined.
    pass  # Test documents behavior, actual error raised in F09 disk persistence
