"""Exit cleanup handler for LangAgent runtime.

This module implements the exit_cleanup stage (stage 6 of 6) which:
- Flushes cross-cutting concerns (metrics, audit, events)
- Closes resource connections (checkpointer)
- Writes diagnostic reports (doctor, eval, metrics)
- Returns appropriate exit codes

Constitutional alignment: Articles III, IX, X, XII, XV
"""

import sys
from typing import Any
from pathlib import Path

from langagent.runtime.exit_code import worst_of


class RuntimeExitHandler:
    """Handles cleanup operations at exit_cleanup stage."""
    
    def cleanup(
        self,
        state: Any,
        config: Any,
        *,
        doctor_report: Any = None,
        eval_report: Any = None,
        metrics_snapshot: Any = None,
        init_only: bool = False
    ) -> int:
        """Execute 11-step cleanup sequence with continue-on-failure.
        
        Args:
            state: Current agent state
            config: Runtime configuration
            doctor_report: Optional doctor check report to write
            eval_report: Optional eval report to write (takes precedence)
            metrics_snapshot: Optional metrics snapshot to write
            init_only: If True, skip resource cleanup (fast path for init command)
            
        Returns:
            Exit code (0 for success, non-zero for failures)
        """
        # FR-018: Emit cleanup start event
        try:
            from langagent.cross_cutting import logger
            logger.emit("la.runtime.exit_cleanup.start", {
                "message": "Starting exit cleanup",
                "init_only": init_only,
            })
        except Exception:
            pass  # Logger failure is non-fatal
        
        # Continue-on-failure tracking (FR-003)
        failed_steps: list[str] = []
        failed_exit_codes: list[int] = []
        
        # FR-021: Skip resource cleanup for init-only mode
        if init_only:
            try:
                from langagent.cross_cutting import logger
                logger.emit("la.lifecycle.init.end", {"message": "Init complete"})
                logger.emit("la.runtime.exit_cleanup.ok", {"message": "Cleanup complete (init-only)"})
            except Exception:
                pass
            return 0
        
        # Step 1: Flush event bus (timeout is not a failure)
        try:
            if hasattr(config, 'event_bus') and config.event_bus:
                config.event_bus.flush(timeout=5)
        except TimeoutError:
            # FR-024: Timeout is logged but not counted as failure
            try:
                from langagent.cross_cutting import logger
                logger.emit("la.cross_cutting.event_handler_error", {
                    "message": "Event bus flush timed out after 5s (non-fatal)"
                })
            except Exception:
                pass
        except Exception as e:
            # Unexpected error (not timeout)
            failed_steps.append("event_bus.flush")
            exit_code = getattr(e, 'exit_code', 1)
            failed_exit_codes.append(exit_code)
        
        # Step 2: Flush metrics collector
        try:
            from langagent.cross_cutting import metrics_collector
            metrics_collector.flush()
        except Exception as e:
            failed_steps.append("metrics.flush")
            exit_code = getattr(e, 'exit_code', 1)
            failed_exit_codes.append(exit_code)
        
        # Step 3: Flush audit recorder
        try:
            from langagent.cross_cutting.audit_recorder import AuditRecorder
            try:
                recorder = AuditRecorder()
                recorder.flush()
            except PermissionError:
                # Skip audit flush if directory not accessible (e.g., in tests)
                pass
        except Exception as e:
            failed_steps.append("audit.flush")
            # AuditFlushError has exit_code = 4 (I/O error)
            exit_code = getattr(e, 'exit_code', 4)
            failed_exit_codes.append(exit_code)
        
        # Step 4: Close checkpointer
        try:
            if hasattr(config, 'checkpointer_instance') and config.checkpointer_instance:
                self._close_checkpointer(config.checkpointer_instance)
        except Exception as e:
            failed_steps.append("checkpointer.close")
            exit_code = getattr(e, 'exit_code', 1)
            failed_exit_codes.append(exit_code)
        
        # Step 5: Take metrics snapshot
        snapshot_result = metrics_snapshot
        if snapshot_result is None:
            try:
                from langagent.cross_cutting import metrics_collector
                from datetime import datetime, timezone
                
                # Create a time window for the entire session
                # Use a reasonable window (e.g., last 24 hours to now)
                window_end = datetime.now(timezone.utc)
                window_start = datetime.fromtimestamp(0, tz=timezone.utc)  # Unix epoch start
                
                snapshot_result = metrics_collector.snapshot(window_start, window_end)
                if snapshot_result is None:
                    # FR-005: Missing snapshot gets exit code 70
                    failed_steps.append("metrics.snapshot")
                    failed_exit_codes.append(70)
            except Exception as e:
                failed_steps.append("metrics.snapshot")
                exit_code = getattr(e, 'exit_code', 70)
                failed_exit_codes.append(exit_code)
        
        # Step 6: Drain spans
        spans = []
        try:
            from langagent.cross_cutting import logger
            spans = logger.drain_spans()
        except Exception as e:
            failed_steps.append("drain_spans")
            exit_code = getattr(e, 'exit_code', 4)
            failed_exit_codes.append(exit_code)
        
        # Step 7: Drain events
        events = []
        try:
            if hasattr(config, 'event_bus') and config.event_bus:
                if hasattr(config.event_bus, 'drain_events'):
                    events = config.event_bus.drain_events()
        except Exception as e:
            failed_steps.append("drain_events")
            exit_code = getattr(e, 'exit_code', 4)
            failed_exit_codes.append(exit_code)
        
        # Step 8: Write reports
        try:
            self._write_reports(
                state=state,
                config=config,
                doctor_report=doctor_report,
                eval_report=eval_report,
                metrics_snapshot=snapshot_result,
                spans=spans,
                events=events,
            )
        except Exception as e:
            failed_steps.append("write_reports")
            exit_code = getattr(e, 'exit_code', 4)
            failed_exit_codes.append(exit_code)
        
        # Step 9: Emit final log (FR-019)
        try:
            from langagent.cross_cutting import logger
            if failed_steps:
                logger.emit("la.runtime.exit_cleanup.fail", {
                    "message": f"Cleanup completed with {len(failed_steps)} failures",
                    "failed_steps": failed_steps,
                    "exit_codes": failed_exit_codes,
                })
            else:
                logger.emit("la.runtime.exit_cleanup.ok", {
                    "message": "Cleanup completed successfully"
                })
        except Exception:
            pass  # Logger failure is non-fatal
        
        # Step 11: Return worst exit code (FR-010)
        final_exit_code = worst_of(failed_exit_codes) if failed_exit_codes else 0
        return final_exit_code
    
    def _close_checkpointer(self, saver: Any) -> None:
        """Close checkpointer connections idempotently.
        
        Args:
            saver: Checkpointer instance from checkpoint_adapter.create(), or None
        """
        if saver is None:
            return
        
        # FR-030: Memory checkpointer has no resources to clean up
        try:
            from langgraph.checkpoint.memory import MemorySaver
            if isinstance(saver, MemorySaver):
                return
        except ImportError:
            pass
        
        # Check if saver has connection attribute
        if not hasattr(saver, 'conn') or saver.conn is None:
            return
        
        # Try to close connection
        try:
            import sqlite3
            try:
                from langgraph.checkpoint.sqlite import SqliteSaver
                if isinstance(saver, SqliteSaver):
                    try:
                        saver.conn.execute("SELECT 1")
                        saver.conn.close()
                    except sqlite3.ProgrammingError:
                        pass  # Already closed
            except ImportError:
                pass
        except Exception as e:
            print(f"[WARN] Checkpointer close failed: {e}", file=sys.stderr)
    
    def _write_reports(
        self,
        state: Any,
        config: Any,
        doctor_report: Any,
        eval_report: Any,
        metrics_snapshot: Any,
        spans: list,
        events: list,
    ) -> None:
        """Write reports to disk based on routing priority.
        
        Priority: eval_report > doctor_report > metrics_snapshot
        """
        import json
        import os
        from datetime import datetime, timezone
        
        reports_dir = Path.home() / ".local/share/langagent/reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        logs_dir = Path.home() / ".local/share/langagent/logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Priority routing: eval_report > doctor_report > metrics_snapshot
        if eval_report is not None:
            # Write EvalReport
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
            agent_dir_name = getattr(eval_report, 'agent_dir', 'unknown').split('/')[-1]
            report_path = reports_dir / f"{agent_dir_name}-{timestamp}.json"
            self._write_json_atomic(report_path, eval_report)
        elif doctor_report is not None:
            # Write DoctorReport
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
            report_path = reports_dir / f"doctor-{timestamp}.json"
            self._write_json_atomic(report_path, doctor_report)
        elif metrics_snapshot is not None:
            # Write MetricsSnapshot
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
            report_path = reports_dir / f"metrics-{timestamp}.json"
            self._write_json_atomic(report_path, metrics_snapshot)
        
        # Write spans to JSONL (FR-006)
        if spans:
            self._write_spans_jsonl(spans, logs_dir)
        
        # Write events to JSONL (FR-007)
        if events:
            self._write_events_jsonl(events, logs_dir)
    
    def _write_json_atomic(self, filepath: Path, data: Any) -> None:
        """Write JSON data atomically using temp file + rename.
        
        Args:
            filepath: Target file path
            data: Data object (Pydantic model or dict)
        """
        import json
        import os
        
        # Convert Pydantic models to dict
        if hasattr(data, 'model_dump'):
            data_dict = data.model_dump()
        elif hasattr(data, 'dict'):
            data_dict = data.dict()
        else:
            data_dict = data
        
        # Write to temp file first
        tmp_path = filepath.with_suffix('.tmp')
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(data_dict, f, indent=2, ensure_ascii=False, default=str)
            f.flush()
            os.fsync(f.fileno())
        
        # Atomic rename
        os.replace(tmp_path, filepath)
    
    def _write_spans_jsonl(self, spans: list, logs_dir: Path) -> None:
        """Write spans to logs/<run-id>.jsonl.
        
        FR-006: Span JSONL must have exactly 7 fields per line.
        """
        import json
        import fcntl
        import os
        from langagent.runtime.run_id import generate_run_id
        
        if not spans:
            return
        
        # Generate run ID for this execution
        run_id = generate_run_id()
        filepath = logs_dir / f"{run_id}.jsonl"
        
        # Atomic append with file lock
        with open(filepath, 'a', encoding='utf-8') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                for span in spans:
                    # Convert span to dict with 7 fields
                    if hasattr(span, '__dict__'):
                        span_dict = {
                            "trace_id": span.trace_id,
                            "span_id": span.span_id,
                            "parent_span_id": span.parent_span_id,
                            "name": span.name,
                            "start": span.start,
                            "end": span.end,
                            "attributes": span.attributes,
                        }
                    else:
                        span_dict = span
                    
                    json_line = json.dumps(span_dict, ensure_ascii=False) + "\n"
                    f.write(json_line)
                
                f.flush()
                os.fsync(f.fileno())
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    
    def _write_events_jsonl(self, events: list, logs_dir: Path) -> None:
        """Write events to logs/<run-id>.jsonl.
        
        FR-007: Event JSONL format.
        """
        import json
        import fcntl
        import os
        from langagent.runtime.run_id import generate_run_id
        
        if not events:
            return
        
        # Generate run ID for this execution
        run_id = generate_run_id()
        filepath = logs_dir / f"{run_id}-events.jsonl"
        
        # Atomic append with file lock
        with open(filepath, 'a', encoding='utf-8') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                for event in events:
                    # Convert event to dict
                    if hasattr(event, '__dict__'):
                        event_dict = event.__dict__
                    else:
                        event_dict = event
                    
                    json_line = json.dumps(event_dict, ensure_ascii=False, default=str) + "\n"
                    f.write(json_line)
                
                f.flush()
                os.fsync(f.fileno())
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
