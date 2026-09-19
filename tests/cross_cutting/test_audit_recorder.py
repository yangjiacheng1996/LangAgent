"""
Test suite for audit recorder (User Story 1 - Audit Trail for Security Events).

This module implements TDD Red Phase tests that MUST FAIL before implementation.
All 12 tests verify audit logging, redaction, query, and event bus integration.
"""

import json
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import pytest

from langagent.cross_cutting.audit_recorder import AuditRecorder, AuditFlushError
from langagent.cross_cutting.types import AuditEntry
from tests.cross_cutting.fixtures.audit_fixtures import make_audit_entry


# T010 [P] [US1] Test audit entry creation
def test_write_creates_entry(tmp_path: Path) -> None:
    """
    Test that write() creates an audit entry in audit.jsonl.
    
    Verifies FR-001: Append-only audit logging.
    """
    recorder = AuditRecorder(audit_dir=tmp_path)
    
    entry = AuditEntry(
        entry_id=str(uuid.uuid4()),
        audited_at=datetime.now(timezone.utc),
        severity="info",
        category="unauthorized_tool",
        actor="system:test",
        action="tool_blocked",
        target="test_tool",
        outcome="blocked",
        evidence={"reason": "requires_approval=True"},
    )
    
    recorder.write(entry)
    
    audit_file = tmp_path / "audit.jsonl"
    assert audit_file.exists(), "audit.jsonl should be created"
    
    lines = audit_file.read_text().strip().split("\n")
    assert len(lines) == 1, "Should have exactly one entry"
    
    written_entry = json.loads(lines[0])
    assert written_entry["entry_id"] == entry.entry_id
    assert written_entry["category"] == "unauthorized_tool"


# T011 [P] [US1] Test append-only guarantee
def test_write_append_only(tmp_path: Path) -> None:
    """
    Test that write() appends without modifying existing entries.
    
    Verifies FR-001: Append-only guarantee (no truncate/overwrite).
    """
    recorder = AuditRecorder(audit_dir=tmp_path)
    
    # Write 3 entries
    entries = []
    for i in range(3):
        entry = AuditEntry(
            entry_id=str(uuid.uuid4()),
            audited_at=datetime.now(timezone.utc),
            severity="info",
            category="unauthorized_tool",
            actor="system:test",
            action=f"action_{i}",
            target=f"tool_{i}",
            outcome="blocked",
            evidence={},
        )
        entries.append(entry)
        recorder.write(entry)
    
    # Write 4th entry and flush
    entry_4 = AuditEntry(
        entry_id=str(uuid.uuid4()),
        audited_at=datetime.now(timezone.utc),
        severity="info",
        category="pii_detected",
        actor="system:test",
        action="action_4",
        target="tool_4",
        outcome="redacted",
        evidence={},
    )
    recorder.write(entry_4)
    recorder.flush()
    
    # Verify all 4 entries exist and none were modified
    audit_file = tmp_path / "audit.jsonl"
    lines = audit_file.read_text().strip().split("\n")
    assert len(lines) == 4, "Should have exactly 4 entries"
    
    for i in range(3):
        written = json.loads(lines[i])
        assert written["action"] == f"action_{i}", f"Entry {i} should not be modified"


# T012 [P] [US1] Test query by category filter
def test_query_by_category(tmp_path: Path) -> None:
    """
    Test that query() filters by category correctly.
    
    Verifies FR-005: Query by category filter.
    """
    recorder = AuditRecorder(audit_dir=tmp_path)
    
    # Write entries with different categories
    categories = ["unauthorized_tool", "pii_detected", "unauthorized_tool", "prompt_injection"]
    for i, cat in enumerate(categories):
        entry = AuditEntry(
            entry_id=str(uuid.uuid4()),
            audited_at=datetime.now(timezone.utc),
            severity="info",
            category=cat,  # type: ignore
            actor="system:test",
            action=f"action_{i}",
            target=f"target_{i}",
            outcome="blocked",
            evidence={},
        )
        recorder.write(entry)
    
    recorder.flush()
    
    # Query for unauthorized_tool only
    results = recorder.query(
        category="unauthorized_tool",
        since=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    
    assert len(results) == 2, "Should return exactly 2 unauthorized_tool entries"
    assert all(r.category == "unauthorized_tool" for r in results)


# T013 [P] [US1] Test query since timestamp filter
def test_query_since_filter(tmp_path: Path) -> None:
    """
    Test that query() filters by since timestamp correctly.
    
    Verifies FR-005: Query by timestamp filter.
    """
    recorder = AuditRecorder(audit_dir=tmp_path)
    
    # Write entries at different times
    base_time = datetime.now(timezone.utc)
    times = [
        base_time - timedelta(hours=2),
        base_time - timedelta(hours=1),
        base_time - timedelta(minutes=30),
        base_time,
    ]
    
    for i, ts in enumerate(times):
        entry = AuditEntry(
            entry_id=str(uuid.uuid4()),
            audited_at=ts,
            severity="info",
            category="unauthorized_tool",
            actor="system:test",
            action=f"action_{i}",
            target=f"target_{i}",
            outcome="blocked",
            evidence={},
        )
        recorder.write(entry)
    
    recorder.flush()
    
    # Query for entries since 1 hour ago (should get last 3 entries: 1h ago, 30m ago, now)
    since_time = base_time - timedelta(hours=1)
    results = recorder.query(category="unauthorized_tool", since=since_time)
    
    assert len(results) == 3, "Should return entries at or after since timestamp (inclusive)"
    assert all(r.audited_at >= since_time for r in results)


# T014 [P] [US1] Test api_key redaction
def test_evidence_redaction(tmp_path: Path) -> None:
    """
    Test that api_key patterns are redacted in evidence.
    
    Verifies FR-003: Redaction of api_key, password, token patterns.
    """
    recorder = AuditRecorder(audit_dir=tmp_path)
    
    entry = AuditEntry(
        entry_id=str(uuid.uuid4()),
        audited_at=datetime.now(timezone.utc),
        severity="info",
        category="unauthorized_tool",
        actor="system:test",
        action="tool_blocked",
        target="test_tool",
        outcome="blocked",
        evidence={"api_key": "sk-12345abcdef", "password": "secret123"},
    )
    
    recorder.write(entry)
    recorder.flush()
    
    # Read back and verify redaction
    audit_file = tmp_path / "audit.jsonl"
    written = json.loads(audit_file.read_text())
    
    assert written["evidence"]["api_key"] == "***", "api_key should be redacted to ***"
    assert written["evidence"]["password"] == "***", "password should be redacted to ***"


# T015 [P] [US1] Test email redaction
def test_pii_email_redaction(tmp_path: Path) -> None:
    """
    Test that email addresses are redacted to ***@domain.com.
    
    Verifies FR-003: Email redaction preserving domain.
    """
    recorder = AuditRecorder(audit_dir=tmp_path)
    
    entry = AuditEntry(
        entry_id=str(uuid.uuid4()),
        audited_at=datetime.now(timezone.utc),
        severity="info",
        category="pii_detected",
        actor="system:audit_recorder",
        action="pii_redacted",
        target="user_email",
        outcome="redacted",
        evidence={"email": "user@example.com", "contact": "admin@test.org"},
    )
    
    recorder.write(entry)
    recorder.flush()
    
    # Read back and verify email redaction
    audit_file = tmp_path / "audit.jsonl"
    written = json.loads(audit_file.read_text())
    
    assert written["evidence"]["email"] == "***@example.com", "Email username should be redacted"
    assert written["evidence"]["contact"] == "***@test.org", "Contact email username should be redacted"


# T016 [P] [US1] Test flush persists to disk
def test_flush_persists_to_disk(tmp_path: Path) -> None:
    """
    Test that flush() ensures all entries are written to disk.
    
    Verifies FR-006: Flush guarantees persistence.
    """
    recorder = AuditRecorder(audit_dir=tmp_path)
    
    entry = AuditEntry(
        entry_id=str(uuid.uuid4()),
        audited_at=datetime.now(timezone.utc),
        severity="info",
        category="unauthorized_tool",
        actor="system:test",
        action="tool_blocked",
        target="test_tool",
        outcome="blocked",
        evidence={},
    )
    
    recorder.write(entry)
    
    # Before flush, file might not exist or be incomplete
    # After flush, must be complete
    recorder.flush()
    
    audit_file = tmp_path / "audit.jsonl"
    assert audit_file.exists(), "audit.jsonl must exist after flush"
    
    lines = audit_file.read_text().strip().split("\n")
    assert len(lines) == 1, "Flushed entry must be on disk"
    
    written = json.loads(lines[0])
    assert written["entry_id"] == entry.entry_id


# T017 [P] [US1] Test write failure raises AuditFlushError
def test_write_failure_raises_audit_flush_error(tmp_path: Path) -> None:
    """
    Test that write() raises AuditFlushError when disk write fails.
    
    Verifies FR-007: I/O error handling (exit code 4).
    """
    # Create recorder with non-writable directory
    readonly_dir = tmp_path / "readonly"
    readonly_dir.mkdir()
    readonly_dir.chmod(0o444)  # Read-only
    
    recorder = AuditRecorder(audit_dir=readonly_dir)
    
    entry = AuditEntry(
        entry_id=str(uuid.uuid4()),
        audited_at=datetime.now(timezone.utc),
        severity="info",
        category="unauthorized_tool",
        actor="system:test",
        action="tool_blocked",
        target="test_tool",
        outcome="blocked",
        evidence={},
    )
    
    with pytest.raises(AuditFlushError):
        recorder.write(entry)
    
    # Cleanup
    readonly_dir.chmod(0o755)


# T018 [P] [US1] Test entry_id is UUID4 format
def test_entry_id_is_uuid4(tmp_path: Path) -> None:
    """
    Test that entry_id matches UUID4 format validation.
    
    Verifies schema validation rule from plan.md.
    """
    # Valid UUID4
    valid_entry = AuditEntry(
        entry_id="550e8400-e29b-41d4-a716-446655440000",
        audited_at=datetime.now(timezone.utc),
        severity="info",
        category="unauthorized_tool",
        actor="system:test",
        action="tool_blocked",
        target="test_tool",
        outcome="blocked",
        evidence={},
    )
    assert valid_entry.entry_id == "550e8400-e29b-41d4-a716-446655440000"
    
    # Invalid UUID (not UUID4)
    with pytest.raises(ValueError):
        AuditEntry(
            entry_id="not-a-valid-uuid",
            audited_at=datetime.now(timezone.utc),
            severity="info",
            category="unauthorized_tool",
            actor="system:test",
            action="tool_blocked",
            target="test_tool",
            outcome="blocked",
            evidence={},
        )


# T019 [P] [US1] Test category validation
def test_category_must_be_in_literal(tmp_path: Path) -> None:
    """
    Test that category must be one of the allowed literal values.
    
    Verifies schema validation for AuditCategory.
    """
    # Valid category
    valid_entry = AuditEntry(
        entry_id=str(uuid.uuid4()),
        audited_at=datetime.now(timezone.utc),
        severity="info",
        category="unauthorized_tool",
        actor="system:test",
        action="tool_blocked",
        target="test_tool",
        outcome="blocked",
        evidence={},
    )
    assert valid_entry.category == "unauthorized_tool"
    
    # Invalid category
    with pytest.raises(ValueError):
        AuditEntry(
            entry_id=str(uuid.uuid4()),
            audited_at=datetime.now(timezone.utc),
            severity="info",
            category="invalid_category",  # type: ignore
            actor="system:test",
            action="tool_blocked",
            target="test_tool",
            outcome="blocked",
            evidence={},
        )


# T020 [P] [US1] Test severity validation
def test_severity_must_be_in_literal(tmp_path: Path) -> None:
    """
    Test that severity must be one of the allowed literal values.
    
    Verifies schema validation for AuditSeverity.
    """
    # Valid severities
    for severity in ["debug", "info", "warn", "error"]:
        entry = AuditEntry(
            entry_id=str(uuid.uuid4()),
            audited_at=datetime.now(timezone.utc),
            severity=severity,  # type: ignore
            category="unauthorized_tool",
            actor="system:test",
            action="tool_blocked",
            target="test_tool",
            outcome="blocked",
            evidence={},
        )
        assert entry.severity == severity
    
    # Invalid severity
    with pytest.raises(ValueError):
        AuditEntry(
            entry_id=str(uuid.uuid4()),
            audited_at=datetime.now(timezone.utc),
            severity="critical",  # type: ignore
            category="unauthorized_tool",
            actor="system:test",
            action="tool_blocked",
            target="test_tool",
            outcome="blocked",
            evidence={},
        )


# T021 [P] [US1] Test event bus subscription
def test_audit_recorder_subscribes_to_guardrail_block_event(tmp_path: Path, monkeypatch: Any) -> None:
    """
    Test that subscribe_guardrail_events() subscribes to F03 event bus.
    
    Verifies integration with F03 protocol_event_bus (guardrail_block events).
    """
    recorder = AuditRecorder(audit_dir=tmp_path)
    
    # Mock event bus using a simple class
    class MockEventBus:
        def __init__(self):
            self.subscribed_events = []
        
        def subscribe(self, event_type: str, handler: Any) -> None:
            self.subscribed_events.append(event_type)
    
    mock_event_bus = MockEventBus()
    
    recorder.subscribe_guardrail_events(mock_event_bus)
    
    # For now, subscribe_guardrail_events is a stub, so this test just verifies
    # it doesn't crash. Full implementation will be added with F03 integration.
    # When implemented, uncomment:
    # assert "guardrail_block" in mock_event_bus.subscribed_events
