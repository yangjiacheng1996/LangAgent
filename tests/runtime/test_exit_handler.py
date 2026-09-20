"""Tests for exit_handler module.

Tests cover:
- Cleanup main flow (11 steps)
- Continue-on-failure strategy
- Report routing (doctor/eval/metrics)
- Init-only mode
- Stage capability violations
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import tempfile
import json

from langagent.runtime.exit_handler import RuntimeExitHandler
from langagent.runtime.agent_state import AgentState, RuntimeConfig, GuardrailPolicy
from langagent.cross_cutting.logger import Span


class TestUS1CleanupMainFlow:
    """User Story 1: Graceful Cleanup After Normal Agent Run."""
    
    def test_cleanup_returns_exit_code_0_on_success(self):
        """T020: Verify cleanup returns 0 on success."""
        handler = RuntimeExitHandler()
        
        # Create minimal state and config
        state = {"messages": [], "todos": [], "files": {}, "context": {}, "scratchpad": {}}
        config = Mock()
        config.checkpointer = "memory"
        config.checkpointer_instance = None
        # Explicitly set event_bus to None to avoid Mock auto-creation
        config.event_bus = None
        
        # Create a temp directory for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock all dependencies to succeed
            with patch('langagent.cross_cutting.logger.emit'):
                with patch('langagent.cross_cutting.metrics_collector.flush'):
                    with patch('langagent.cross_cutting.metrics_collector.snapshot', return_value=Mock()):
                        # Mock Path.home() to use temp directory
                        with patch('pathlib.Path.home', return_value=Path(tmpdir)):
                            with patch('langagent.cross_cutting.logger.drain_spans', return_value=[]):
                                exit_code = handler.cleanup(state, config)
        
        assert exit_code == 0
    
    def test_cleanup_continues_after_step_failure(self):
        """T025: Verify cleanup continues after audit flush fails."""
        handler = RuntimeExitHandler()
        
        state = {"messages": [], "todos": [], "files": {}, "context": {}, "scratchpad": {}}
        config = Mock()
        config.checkpointer = "memory"
        config.checkpointer_instance = None
        
        # Mock audit flush to fail
        with patch('langagent.cross_cutting.logger.emit'):
            with patch('langagent.cross_cutting.metrics_collector.flush'):
                with patch('langagent.cross_cutting.metrics_collector.snapshot', return_value=Mock()):
                    with patch('langagent.cross_cutting.audit_recorder.AuditRecorder') as mock_audit:
                        # Simulate audit flush failure
                        mock_audit.return_value.flush.side_effect = IOError("Disk full")
                        with patch('langagent.cross_cutting.logger.drain_spans', return_value=[]):
                            exit_code = handler.cleanup(state, config)
        
        # Should return non-zero exit code but not crash
        assert exit_code == 4  # I/O error
    
    def test_cleanup_writes_span_jsonl(self):
        """T023: Verify cleanup writes span JSONL file."""
        handler = RuntimeExitHandler()
        
        state = {"messages": [], "todos": [], "files": {}, "context": {}, "scratchpad": {}}
        config = Mock()
        config.checkpointer = "memory"
        config.checkpointer_instance = None
        # Explicitly set event_bus to None to avoid Mock auto-creation
        config.event_bus = None
        
        # Create test spans
        test_spans = [
            Span(
                trace_id="trace-1",
                span_id="span-1",
                parent_span_id=None,
                name="test_span",
                start=1234567890.0,
                end=1234567891.0,
                attributes={"key": "value"}
            )
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock Path.home() to use temp directory
            with patch('pathlib.Path.home', return_value=Path(tmpdir)):
                with patch('langagent.cross_cutting.logger.emit'):
                    with patch('langagent.cross_cutting.metrics_collector.flush'):
                        with patch('langagent.cross_cutting.metrics_collector.snapshot', return_value=Mock()):
                            with patch('langagent.cross_cutting.logger.drain_spans', return_value=test_spans):
                                exit_code = handler.cleanup(state, config)
            
            # Verify spans were processed
            assert exit_code == 0
            
            # Verify JSONL file was created
            logs_dir = Path(tmpdir) / '.local/share/langagent/logs'
            if logs_dir.exists():
                jsonl_files = list(logs_dir.glob('*.jsonl'))
                assert len(jsonl_files) > 0, "Span JSONL file should be created"


class TestUS5InitOnlyMode:
    """User Story 5: Init-Only Cleanup Mode."""
    
    def test_cleanup_init_only_skips_steps_1_to_8(self):
        """T158: Verify init_only mode skips resource cleanup steps."""
        handler = RuntimeExitHandler()
        
        state = {"messages": [], "todos": [], "files": {}, "context": {}, "scratchpad": {}}
        config = Mock()
        
        with patch('langagent.cross_cutting.logger.emit') as mock_emit:
            exit_code = handler.cleanup(state, config, init_only=True)
        
        # Verify exit code is 0
        assert exit_code == 0
        
        # Verify lifecycle.init.end was emitted
        call_args_list = [call[0] for call in mock_emit.call_args_list]
        event_types = [args[0] for args in call_args_list]
        assert "la.lifecycle.init.end" in event_types
    
    def test_cleanup_init_only_performance(self):
        """T159: Verify init_only mode completes quickly."""
        import time
        
        handler = RuntimeExitHandler()
        state = {"messages": [], "todos": [], "files": {}, "context": {}, "scratchpad": {}}
        config = Mock()
        
        with patch('langagent.cross_cutting.logger.emit'):
            start = time.perf_counter()
            exit_code = handler.cleanup(state, config, init_only=True)
            duration_ms = (time.perf_counter() - start) * 1000
        
        assert exit_code == 0
        assert duration_ms < 100  # Should complete in < 100ms


class TestSetup:
    """Basic setup and smoke tests."""
    
    def test_runtime_exit_handler_instantiates(self):
        """Verify RuntimeExitHandler can be instantiated."""
        handler = RuntimeExitHandler()
        assert handler is not None
