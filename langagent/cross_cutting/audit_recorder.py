"""
Audit recorder for security events.

Provides append-only JSONL logging with rotation for audit trail per
Constitution Article X (Security & Privacy).
"""

import fcntl
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langagent.cross_cutting.types import AuditEntry


class AuditFlushError(Exception):
    """
    Raised when audit write/flush fails.
    
    Exit code 4 (I/O error) per Constitution Article X.5 - audit failures
    must be visible and prevent agent execution from proceeding silently.
    """
    pass


class AuditRecorder:
    """
    Singleton audit recorder for security events. Thread-safe.
    
    Provides append-only JSONL logging with automatic redaction of PII
    and sensitive data (api_key, password, token, emails) per Constitution
    Article X (Security & Privacy).
    """
    
    def __init__(self, audit_dir: Path = Path.home() / ".local/share/langagent"):
        """
        Initialize recorder with audit directory.
        
        Args:
            audit_dir: Directory for audit.jsonl files (default: ~/.local/share/langagent/)
        
        Raises:
            PermissionError: If audit_dir is not writable
        """
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.audit_file = self.audit_dir / "audit.jsonl"
        self._buffer: list[AuditEntry] = []
        self._max_file_size = 10 * 1024 * 1024  # 10MB
        self._max_rotated_files = 3
        
        # Verify directory is writable
        if not self.audit_dir.exists() or not self.audit_dir.is_dir():
            raise PermissionError(f"Audit directory does not exist or is not a directory: {audit_dir}")
    
    def _redact_secrets(self, text: str) -> str:
        """
        Redact api_key, password, token patterns to ***.
        
        Pattern: (api_key|password|token)["']?\\s*[:=]\\s*["']?([^"'\\s,}]+)
        Replace group 2 with ***
        """
        pattern = r'(api_key|password|token)["\']?\s*[:=]\s*["\']?([^"\'\\s,}]+)'
        return re.sub(pattern, r'\1=***', text, flags=re.IGNORECASE)
    
    def _redact_email(self, text: str) -> str:
        """
        Redact email username to ***@domain.com.
        
        Pattern: ([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})
        Replace group 1 with ***
        """
        pattern = r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        return re.sub(pattern, r'***@\2', text)
    
    def _redact_phone(self, text: str) -> str:
        """
        Redact phone numbers to ***.
        
        Pattern: \\+?\\d[\\d\\s\\-\\(\\)]{7,}\\d
        Replace entire match with ***
        """
        pattern = r'\+?\d[\d\s\-\(\)]{7,}\d'
        return re.sub(pattern, '***', text)
    
    def _redact_evidence(self, evidence: dict[str, Any]) -> dict[str, Any]:
        """
        Apply redaction to evidence dictionary.
        
        Redacts api_key, password, token fields to ***.
        Redacts email addresses to ***@domain.com.
        Redacts phone numbers to ***.
        """
        redacted = {}
        for key, value in evidence.items():
            # Direct secret keys
            if key.lower() in {"api_key", "password", "token"}:
                redacted[key] = "***"
            elif isinstance(value, str):
                # Apply pattern-based redaction
                redacted_value = self._redact_secrets(value)
                redacted_value = self._redact_email(redacted_value)
                redacted_value = self._redact_phone(redacted_value)
                redacted[key] = redacted_value
            else:
                redacted[key] = value
        return redacted
    
    def _get_file_size(self) -> int:
        """Get current audit file size in bytes."""
        if not self.audit_file.exists():
            return 0
        return self.audit_file.stat().st_size
    
    def _rotate_file(self) -> None:
        """
        Rotate audit.jsonl to audit-YYYYMMDD-HHMMSS-microseconds.jsonl.
        Creates new audit.jsonl and cleans up old rotated files.
        """
        if not self.audit_file.exists():
            return
        
        # Generate timestamp-based filename with microseconds for uniqueness
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        rotated_name = f"audit-{timestamp}.jsonl"
        rotated_path = self.audit_dir / rotated_name
        
        # Ensure unique filename (in case of race conditions)
        counter = 0
        while rotated_path.exists():
            counter += 1
            rotated_name = f"audit-{timestamp}-{counter}.jsonl"
            rotated_path = self.audit_dir / rotated_name
        
        # Rename current file to rotated file
        self.audit_file.rename(rotated_path)
        
        # Clean up old rotated files
        self._cleanup_old_files()
    
    def _cleanup_old_files(self) -> None:
        """Delete oldest rotated files if count exceeds max_rotated_files."""
        rotated_files = sorted(self.audit_dir.glob("audit-*.jsonl"))
        
        # Keep only the most recent N files
        if len(rotated_files) > self._max_rotated_files:
            files_to_delete = rotated_files[: len(rotated_files) - self._max_rotated_files]
            for old_file in files_to_delete:
                old_file.unlink()
    
    def write(self, entry: AuditEntry) -> None:
        """
        Write audit entry to audit.jsonl (append-only). Auto-rotates if file exceeds 10MB.
        
        Args:
            entry: AuditEntry to persist
        
        Raises:
            AuditFlushError: If disk write fails (exit code 4)
        
        Side Effects:
            - Writes JSONL line to audit.jsonl
            - Applies redaction to evidence field
            - Triggers rotation if file > 10MB
            - Publishes audit.write event to event bus (future: F03 integration)
        """
        try:
            # Check if rotation is needed before writing
            if self._get_file_size() >= self._max_file_size:
                self._rotate_file()
            
            # Convert to dict with mode='json' to serialize datetime to ISO format
            entry_dict = entry.model_dump(mode='json')
            entry_dict["evidence"] = self._redact_evidence(entry.evidence)
            
            # Append to file with file lock
            with open(self.audit_file, "a", encoding="utf-8") as f:
                # Acquire exclusive lock for thread safety
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    f.write(json.dumps(entry_dict) + "\n")
                    f.flush()
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
        except (OSError, IOError) as e:
            raise AuditFlushError(f"Failed to write audit entry: {e}") from e
    
    def query(self, category: str, since: datetime) -> list[AuditEntry]:
        """
        Query audit entries across all rotated files.
        
        Args:
            category: Exact category match (one of "unauthorized_tool", "pii_detected", "prompt_injection")
            since: Minimum audited_at timestamp (inclusive)
        
        Returns:
            List of AuditEntry objects matching filters, sorted by audited_at ascending
        
        Performance:
            - Pre-filters files by filename timestamp
            - Scans matching files line-by-line
            - Target: <50ms for 10,000 entries
        """
        results: list[AuditEntry] = []
        
        # Get all audit files (current + rotated)
        audit_files = [self.audit_file] if self.audit_file.exists() else []
        audit_files.extend(sorted(self.audit_dir.glob("audit-*.jsonl")))
        
        for audit_file in audit_files:
            try:
                with open(audit_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        
                        entry_dict = json.loads(line)
                        
                        # Filter by category
                        if entry_dict.get("category") != category:
                            continue
                        
                        # Parse timestamp and filter by since
                        audited_at = datetime.fromisoformat(entry_dict["audited_at"])
                        if audited_at < since:
                            continue
                        
                        # Reconstruct AuditEntry
                        entry = AuditEntry(**entry_dict)
                        results.append(entry)
                
            except (OSError, IOError, json.JSONDecodeError):
                # Query failures are non-fatal; continue to next file
                continue
        
        # Sort by audited_at ascending
        results.sort(key=lambda e: e.audited_at)
        
        return results
    
    def flush(self) -> None:
        """
        Flush buffered entries to disk. Called by F09 exit_cleanup.
        
        Currently a no-op since write() immediately persists to disk.
        Future: May buffer entries in memory for performance optimization.
        
        Raises:
            AuditFlushError: If flush fails
        """
        # Current implementation writes immediately, so flush is a no-op
        # This method is provided for API compatibility with F09 exit_cleanup
        pass
    
    def subscribe_guardrail_events(self, event_bus: Any) -> None:
        """
        Subscribe to guardrail_block events from event bus (F03).
        Automatically writes AuditEntry when event received.
        
        Args:
            event_bus: F03 EventBus instance
        
        Note:
            This is a stub for F03 integration. Full implementation
            will be added when F03 protocol_event_bus is available.
        """
        # Stub implementation for F03 integration
        # Future: event_bus.subscribe("guardrail_block", self._on_guardrail_block)
        pass


__all__ = [
    "AuditFlushError",
    "AuditRecorder",
]
