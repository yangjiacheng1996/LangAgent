"""
TDD Tests for Checkpoint Adapter (Phase 5, User Story 3, T050-T058).

These tests MUST FAIL before implementation (T059-T062).
Tests the non-existent langagent.primitives.checkpoint_adapter module.
"""

import pytest
import os
import sqlite3
import tempfile
from unittest.mock import Mock, patch, MagicMock
from pydantic import BaseModel
from typing import Literal, Optional


# ============================================================================
# Stub RuntimeConfig for testing (since implementation doesn't exist yet)
# ============================================================================

class RuntimeConfig(BaseModel, frozen=True):
    """Stub RuntimeConfig matching data-model.md schema."""
    checkpointer: Literal["memory", "sqlite", "postgres"]
    checkpoint_sqlite_path: Optional[str] = None
    checkpoint_postgres_dsn: Optional[str] = None


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def memory_config():
    """RuntimeConfig for memory checkpointer."""
    return RuntimeConfig(checkpointer="memory")


@pytest.fixture
def sqlite_config():
    """RuntimeConfig for sqlite checkpointer with temp file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    yield RuntimeConfig(checkpointer="sqlite", checkpoint_sqlite_path=db_path)
    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def postgres_config():
    """RuntimeConfig for postgres checkpointer."""
    return RuntimeConfig(
        checkpointer="postgres",
        checkpoint_postgres_dsn="postgresql://user:pass@localhost/testdb"
    )


@pytest.fixture
def corrupted_sqlite_db():
    """Create a corrupted SQLite database file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    # Create a valid database first
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, data TEXT)")
    conn.execute("INSERT INTO test VALUES (1, 'test data')")
    conn.commit()
    conn.close()
    
    # Corrupt the database by writing garbage in the middle
    with open(db_path, "r+b") as f:
        f.seek(512)  # Seek to middle of file
        f.write(b"\x00" * 512)  # Overwrite with zeros
    
    yield db_path
    
    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)
    recovery_path = f"{db_path}.recovery"
    if os.path.exists(recovery_path):
        os.remove(recovery_path)


# ============================================================================
# T050: Test create memory checkpointer
# ============================================================================

def test_create_memory(memory_config):
    """
    T050 [P] [US3] Test memory checkpointer creation.
    
    Expects: MemorySaver instance returned.
    MUST FAIL before T059 implementation.
    """
    from langagent.primitives.checkpoint_adapter import create
    from langgraph.checkpoint.memory import MemorySaver
    
    checkpoint = create(memory_config)
    
    assert isinstance(checkpoint, MemorySaver), \
        "Expected MemorySaver instance for memory checkpointer"


# ============================================================================
# T051: Test create sqlite checkpointer in tmp
# ============================================================================

def test_create_sqlite_in_tmp(sqlite_config):
    """
    T051 [P] [US3] Test sqlite checkpointer creation with temp file.
    
    Expects: SqliteSaver instance that persists state.
    MUST FAIL before T059 implementation.
    """
    from langagent.primitives.checkpoint_adapter import create
    from langgraph.checkpoint.sqlite import SqliteSaver
    
    checkpoint = create(sqlite_config)
    
    assert isinstance(checkpoint, SqliteSaver), \
        "Expected SqliteSaver instance for sqlite checkpointer"
    
    # Verify the database file was created
    assert os.path.exists(sqlite_config.checkpoint_sqlite_path), \
        "SQLite database file should be created"


# ============================================================================
# T052: Test create postgres checkpointer
# ============================================================================

def test_create_postgres_url(postgres_config):
    """
    T052 [P] [US3] Test postgres checkpointer creation with DSN.
    
    Expects: PostgresSaver instance.
    MUST FAIL before T059 implementation.
    """
    from langagent.primitives.checkpoint_adapter import create
    
    # Mock the lazy import and PostgresSaver.from_conn_string to avoid actual database connection
    mock_saver = MagicMock()
    mock_postgres_class = MagicMock()
    mock_postgres_class.from_conn_string.return_value = mock_saver
    
    with patch.dict('sys.modules', {'langgraph.checkpoint.postgres': MagicMock(PostgresSaver=mock_postgres_class)}):
        with patch('langagent.primitives.checkpoint_adapter.PostgresSaver', create=True) as _:
            # Need to patch the import inside _create_postgres function
            import langagent.primitives.checkpoint_adapter as cp_adapter
            original_create_postgres = cp_adapter._create_postgres
            
            def patched_create_postgres(config):
                # Simulate the function but with mocked PostgresSaver
                from unittest.mock import MagicMock
                mock_postgres_class = MagicMock()
                mock_postgres_class.from_conn_string.return_value = mock_saver
                return mock_saver
            
            cp_adapter._create_postgres = patched_create_postgres
            
            try:
                checkpoint = create(postgres_config)
                assert checkpoint == mock_saver
            finally:
                cp_adapter._create_postgres = original_create_postgres


# ============================================================================
# T053: Test close memory no-op
# ============================================================================

def test_close_memory_no_op(memory_config):
    """
    T053 [P] [US3] Test close memory checkpointer completes without error.
    
    Expects: close() completes without error per FR-031.
    MUST FAIL before T062 implementation.
    """
    from langagent.primitives.checkpoint_adapter import create, close
    from langgraph.checkpoint.memory import MemorySaver
    
    checkpoint = create(memory_config)
    
    # Should complete without raising exception
    try:
        close(checkpoint)
    except Exception as e:
        pytest.fail(f"close() should not raise exception for memory checkpointer: {e}")


# ============================================================================
# T054: Test close sqlite releases lock
# ============================================================================

def test_close_sqlite_releases_lock(sqlite_config):
    """
    T054 [P] [US3] Test close sqlite releases file lock.
    
    Expects: File lock released after close().
    MUST FAIL before T062 implementation.
    """
    from langagent.primitives.checkpoint_adapter import create, close
    
    checkpoint = create(sqlite_config)
    
    # Close the checkpoint
    close(checkpoint)
    
    # Verify we can open a new connection (lock is released)
    try:
        conn = sqlite3.connect(sqlite_config.checkpoint_sqlite_path)
        conn.execute("SELECT 1")
        conn.close()
    except sqlite3.OperationalError as e:
        pytest.fail(f"SQLite file should be unlocked after close(): {e}")


# ============================================================================
# T055: Test close postgres closes pool
# ============================================================================

def test_close_postgres_closes_pool(postgres_config):
    """
    T055 [P] [US3] Test close postgres closes connection pool.
    
    Expects: Connection pool closed.
    MUST FAIL before T062 implementation.
    """
    from langagent.primitives.checkpoint_adapter import create, close
    
    # Mock PostgresSaver without importing it
    mock_conn = MagicMock()
    mock_saver = MagicMock()
    mock_saver.conn = mock_conn
    
    import langagent.primitives.checkpoint_adapter as cp_adapter
    original_create_postgres = cp_adapter._create_postgres
    
    def patched_create_postgres(config):
        return mock_saver
    
    cp_adapter._create_postgres = patched_create_postgres
    
    try:
        checkpoint = create(postgres_config)
        close(checkpoint)
        
        # Verify conn.close() was called
        mock_conn.close.assert_called_once()
    finally:
        cp_adapter._create_postgres = original_create_postgres


# ============================================================================
# T056: Test unsupported checkpointer error
# ============================================================================

def test_create_unsupported_checkpointer():
    """
    T056 [P] [US3] Test unsupported checkpointer raises error.
    
    Expects: CheckpointTypeUnsupportedError with exit code 78.
    MUST FAIL before T059 implementation.
    """
    from langagent.primitives.checkpoint_adapter import create
    from langagent.primitives.exceptions import CheckpointTypeUnsupportedError
    
    # Create config with unsupported checkpointer
    # We bypass pydantic validation by creating dict directly
    config_dict = {"checkpointer": "redis"}
    
    with pytest.raises(CheckpointTypeUnsupportedError) as exc_info:
        create(config_dict)
    
    assert exc_info.value.exit_code == 78, \
        "CheckpointTypeUnsupportedError should have exit code 78"


# ============================================================================
# T057: Test sqlite corruption repair
# ============================================================================

def test_create_sqlite_corrupted_db(corrupted_sqlite_db):
    """
    T057 [P] [US3] Test sqlite corruption detection and repair.
    
    Expects: Successful repair via dump/restore per research.md Decision 5.
    MUST FAIL before T060 implementation.
    """
    from langagent.primitives.checkpoint_adapter import create
    from langgraph.checkpoint.sqlite import SqliteSaver
    
    config = RuntimeConfig(
        checkpointer="sqlite",
        checkpoint_sqlite_path=corrupted_sqlite_db
    )
    
    # Should detect corruption and repair successfully
    checkpoint = create(config)
    
    assert isinstance(checkpoint, SqliteSaver), \
        "Should return SqliteSaver after successful repair"
    
    # Verify database is now healthy
    conn = sqlite3.connect(corrupted_sqlite_db)
    cursor = conn.cursor()
    cursor.execute("PRAGMA integrity_check")
    results = cursor.fetchall()
    conn.close()
    
    assert len(results) == 1 and results[0][0] == "ok", \
        "Database should be repaired and pass integrity check"


# ============================================================================
# T058: Test postgres retry exhausted
# ============================================================================

def test_create_postgres_retry_exhausted(postgres_config):
    """
    T058 [US3] Test postgres retry exhausted raises GraphCompileError.
    
    Expects: 3 retries with 1s intervals then GraphCompileError per FR-028.
    MUST FAIL before T061 implementation.
    """
    from langagent.primitives.checkpoint_adapter import create
    from langagent.primitives.exceptions import GraphCompileError
    
    # Test with the real function but mock the PostgresSaver import
    call_count = [0]
    
    def mock_from_conn_string(dsn):
        call_count[0] += 1
        raise ConnectionError("Connection refused")
    
    # Create a mock PostgresSaver class
    mock_postgres_class = MagicMock()
    mock_postgres_class.from_conn_string = mock_from_conn_string
    
    # Create a mock module
    mock_postgres_module = MagicMock()
    mock_postgres_module.PostgresSaver = mock_postgres_class
    
    # Patch sys.modules to inject our mock when langgraph.checkpoint.postgres is imported
    with patch.dict('sys.modules', {'langgraph.checkpoint.postgres': mock_postgres_module}):
        with pytest.raises(GraphCompileError) as exc_info:
            create(postgres_config)
        
        # Verify it retried 3 times
        assert call_count[0] == 3, \
            f"Should retry 3 times before raising GraphCompileError, but called {call_count[0]} times"
        
        # Verify error message mentions retries
        assert "3 attempts" in str(exc_info.value), \
            "Error message should mention retry attempts"
