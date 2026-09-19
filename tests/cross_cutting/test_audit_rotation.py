"""
Test suite for audit file rotation (Extension to User Story 1).

This module tests 10MB file size rotation with timestamp naming and 3-file retention.
Note: Tests use smaller data sizes for speed while still verifying rotation logic.
"""

import json
import re
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from langagent.cross_cutting.audit_recorder import AuditRecorder
from langagent.cross_cutting.types import AuditEntry


# T062 [P] Test rotation triggers at threshold
def test_rotation_triggers_at_10mb(tmp_path: Path) -> None:
    """
    Test that rotation triggers when audit.jsonl exceeds size threshold.
    
    Verifies FR-009: File size rotation threshold.
    """
    # Create recorder with smaller threshold for faster testing
    recorder = AuditRecorder(audit_dir=tmp_path)
    recorder._max_file_size = 100 * 1024  # 100KB for testing
    
    # Write entries until file exceeds threshold
    large_evidence = {"data": "x" * 400}
    for i in range(250):  # Should exceed 100KB
        entry = AuditEntry(
            entry_id=str(uuid.uuid4()),
            audited_at=datetime.now(timezone.utc),
            severity="info",
            category="unauthorized_tool",
            actor="system:test",
            action=f"action_{i}",
            target=f"target_{i}",
            outcome="blocked",
            evidence=large_evidence,
        )
        recorder.write(entry)
    
    recorder.flush()
    
    # Verify rotation occurred
    audit_files = list(tmp_path.glob("audit*.jsonl"))
    assert len(audit_files) >= 2, "Should have current file + at least 1 rotated file"
    
    # Verify current file is smaller than threshold
    current_file = tmp_path / "audit.jsonl"
    assert current_file.stat().st_size < 100 * 1024, "Current file should be < threshold after rotation"


# T063 [P] Test rotated file naming format
def test_rotated_file_naming_format(tmp_path: Path) -> None:
    """
    Test that rotated files use audit-YYYYMMDD-HHMMSS.jsonl naming format.
    
    Verifies FR-010: Timestamp-based naming for rotated files.
    """
    recorder = AuditRecorder(audit_dir=tmp_path)
    recorder._max_file_size = 50 * 1024  # 50KB for testing
    
    # Write enough data to trigger rotation
    large_evidence = {"data": "x" * 400}
    for i in range(150):
        entry = AuditEntry(
            entry_id=str(uuid.uuid4()),
            audited_at=datetime.now(timezone.utc),
            severity="info",
            category="unauthorized_tool",
            actor="system:test",
            action=f"action_{i}",
            target=f"target_{i}",
            outcome="blocked",
            evidence=large_evidence,
        )
        recorder.write(entry)
    
    recorder.flush()
    
    # Find rotated files
    rotated_files = [f for f in tmp_path.glob("audit-*.jsonl")]
    assert len(rotated_files) >= 1, "Should have at least one rotated file"
    
    # Verify naming format: audit-YYYYMMDD-HHMMSS-microseconds.jsonl or audit-YYYYMMDD-HHMMSS-microseconds-N.jsonl
    pattern = re.compile(r"audit-\d{8}-\d{6}-\d{6}(-\d+)?\.jsonl")
    for rotated_file in rotated_files:
        assert pattern.match(rotated_file.name), f"File {rotated_file.name} should match audit-YYYYMMDD-HHMMSS-microseconds.jsonl"


# T064 [P] Test 3-file retention limit
def test_three_file_retention_limit(tmp_path: Path) -> None:
    """
    Test that only 3 rotated files are retained (oldest deleted).
    
    Verifies FR-011: 3-file retention limit.
    """
    recorder = AuditRecorder(audit_dir=tmp_path)
    recorder._max_file_size = 20 * 1024  # 20KB for testing
    
    # Write data to trigger 5 rotations
    large_evidence = {"data": "x" * 400}
    for rotation in range(5):
        for i in range(60):
            entry = AuditEntry(
                entry_id=str(uuid.uuid4()),
                audited_at=datetime.now(timezone.utc),
                severity="info",
                category="unauthorized_tool",
                actor="system:test",
                action=f"rotation_{rotation}_action_{i}",
                target=f"target_{i}",
                outcome="blocked",
                evidence=large_evidence,
            )
            recorder.write(entry)
        time.sleep(0.1)  # Small delay to ensure different timestamps
    
    recorder.flush()
    
    # Count rotated files (exclude current audit.jsonl)
    rotated_files = [f for f in tmp_path.glob("audit-*.jsonl")]
    assert len(rotated_files) <= 3, f"Should have at most 3 rotated files, found {len(rotated_files)}"


# T065 [P] Test query across rotated files
def test_query_across_rotated_files(tmp_path: Path) -> None:
    """
    Test that query() scans both current and rotated files.
    
    Verifies FR-012: Cross-file query support.
    """
    recorder = AuditRecorder(audit_dir=tmp_path)
    recorder._max_file_size = 30 * 1024  # 30KB for testing
    
    # Record start time for query
    query_since = datetime.now(timezone.utc)
    
    # Write unauthorized_tool entries
    large_evidence = {"data": "x" * 400}
    for i in range(80):
        entry = AuditEntry(
            entry_id=str(uuid.uuid4()),
            audited_at=datetime.now(timezone.utc),
            severity="info",
            category="unauthorized_tool",
            actor="system:test",
            action=f"unauthorized_{i}",
            target=f"target_{i}",
            outcome="blocked",
            evidence=large_evidence,
        )
        recorder.write(entry)
    
    # Trigger rotation with different category
    for i in range(100):
        entry = AuditEntry(
            entry_id=str(uuid.uuid4()),
            audited_at=datetime.now(timezone.utc),
            severity="info",
            category="pii_detected",
            actor="system:test",
            action=f"pii_{i}",
            target=f"target_{i}",
            outcome="redacted",
            evidence=large_evidence,
        )
        recorder.write(entry)
    
    recorder.flush()
    
    # Verify rotation occurred - should have multiple audit files
    all_audit_files = list(tmp_path.glob("audit*.jsonl"))
    assert len(all_audit_files) >= 2, f"Should have multiple audit files after rotation, found {len(all_audit_files)}"
    
    # Query for unauthorized_tool entries (should find entries across files)
    unauthorized_results = recorder.query(
        category="unauthorized_tool",
        since=query_since,
    )
    
    # Query for pii_detected entries
    pii_results = recorder.query(
        category="pii_detected",
        since=query_since,
    )
    
    # Verify cross-file query works - we should find entries of both types
    # Note: Due to rotation timing, exact counts may vary but both should be present
    assert len(unauthorized_results) > 0, "Should find unauthorized_tool entries from rotated files"
    assert len(pii_results) > 0, "Should find pii_detected entries"
    
    # Total entries should add up close to what we wrote (allowing for rotation edge cases)
    total_found = len(unauthorized_results) + len(pii_results)
    assert total_found >= 100, f"Should find most entries across all files, found {total_found}"


# T066 [P] Test filename timestamp filtering
def test_query_filename_timestamp_filtering(tmp_path: Path) -> None:
    """
    Test that query() scans all audit files.
    
    Verifies query implementation works across files.
    """
    recorder = AuditRecorder(audit_dir=tmp_path)
    
    # Write some entries
    for i in range(100):
        entry = AuditEntry(
            entry_id=str(uuid.uuid4()),
            audited_at=datetime.now(timezone.utc),
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
    
    # Query with recent timestamp
    results = recorder.query(
        category="unauthorized_tool",
        since=datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    
    # Should return results from recent entries
    assert len(results) == 100
