"""
Checkpoint Adapter - Factory and cleanup for LangGraph checkpoint backends.

Supports 3 checkpointer types (memory, sqlite, postgres) with:
- SQLite corruption detection and repair via dump/restore
- PostgreSQL network retry mechanism (3 attempts, 1s intervals)
- Proper resource cleanup for all backends

See: specs/001-primitives-layer-langchain-langraph/contracts/checkpoint_adapter.md
"""

import sqlite3
import os
import time
from typing import Any

from langagent.primitives.langchain_types import BaseCheckpointSaver
from langagent.primitives.exceptions import (
    CheckpointTypeUnsupportedError,
    GraphCompileError,
)

# Import checkpoint implementations (lazy import for postgres to avoid dependency issues)
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

# PostgresSaver and psycopg imports are deferred to avoid module-level import errors


# ============================================================================
# Public Interface
# ============================================================================

def create(config: Any) -> BaseCheckpointSaver:
    """
    Instantiate a checkpointer based on config.checkpointer.
    
    Supported types (FR-024):
    - memory: In-memory checkpoint (no persistence)
    - sqlite: SQLite file-based checkpoint (local persistence)
    - postgres: PostgreSQL checkpoint (networked persistence)
    
    Args:
        config: RuntimeConfig or dict with checkpointer field
    
    Returns:
        BaseCheckpointSaver instance ready for graph compilation
    
    Raises:
        CheckpointTypeUnsupportedError: checkpointer not in 3 supported values
        GraphCompileError: SQLite corruption repair failed OR postgres connection
                          failed after retries
    
    Side Effects:
        - SQLite: Runs PRAGMA integrity_check, attempts dump/restore if corrupted
        - Postgres: Retries 3 times with 1s intervals on network errors
    """
    # Handle both RuntimeConfig objects and dicts
    if isinstance(config, dict):
        checkpointer_type = config.get("checkpointer")
    else:
        checkpointer_type = config.checkpointer
    
    if checkpointer_type == "memory":
        return _create_memory(config)
    elif checkpointer_type == "sqlite":
        return _create_sqlite(config)
    elif checkpointer_type == "postgres":
        return _create_postgres(config)
    else:
        raise CheckpointTypeUnsupportedError(
            f"Unsupported checkpointer type: {checkpointer_type}. "
            f"Supported types: memory, sqlite, postgres"
        )


def close(saver: BaseCheckpointSaver) -> None:
    """
    Close checkpointer connections and release resources.
    
    Args:
        saver: Checkpointer instance from create()
    
    Side Effects (FR-029):
        - Memory: No-op (FR-030)
        - SQLite: Release file lock, close connection
        - Postgres: Close connection pool
    
    Raises:
        Propagates exceptions from underlying checkpoint backend
    """
    if isinstance(saver, MemorySaver):
        # No-op for memory checkpointer (FR-030)
        pass
    elif isinstance(saver, SqliteSaver):
        # Close SQLite connection to release file lock
        if hasattr(saver, 'conn') and saver.conn:
            saver.conn.close()
    else:
        # For postgres or other checkpointers, try to close if it has conn attribute
        if hasattr(saver, 'conn') and saver.conn:
            saver.conn.close()


# ============================================================================
# Private Implementation
# ============================================================================

def _create_memory(config: Any) -> MemorySaver:
    """Create memory checkpointer (FR-025)."""
    return MemorySaver()


def _create_sqlite(config: Any):
    """
    Create SQLite checkpointer with corruption detection and repair (FR-026).
    
    Implements research.md Decision 5:
    - PRAGMA integrity_check detects but does NOT repair
    - Actual repair requires dump/restore to new database
    """
    # Extract database path from config
    if isinstance(config, dict):
        db_path = config.get("checkpoint_sqlite_path")
    else:
        db_path = config.checkpoint_sqlite_path
    
    if not db_path:
        raise GraphCompileError(
            "checkpoint_sqlite_path is required when checkpointer='sqlite'"
        )
    
    # Check if database file exists
    db_exists = os.path.exists(db_path)
    
    # If database doesn't exist, create it directly
    if not db_exists:
        # SqliteSaver.from_conn_string returns a context manager, enter it to get the saver
        cm = SqliteSaver.from_conn_string(db_path)
        return cm.__enter__()
    
    # Database exists - check integrity
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        results = cursor.fetchall()
        
        # Check if database is healthy
        if len(results) == 1 and results[0][0] == "ok":
            conn.close()
            cm = SqliteSaver.from_conn_string(db_path)
            return cm.__enter__()
        
        # Corruption detected - attempt repair
        issues = [row[0] for row in results]
        
        # Emit corruption detection event (would use logger.emit in full implementation)
        print(f"[WARN] SQLite corruption detected: {len(issues)} issues, first: {issues[0]}")
        
        # Attempt dump and restore
        backup_path = f"{db_path}.recovery"
        try:
            sql_dump = list(conn.iterdump())
            
            new_conn = sqlite3.connect(backup_path)
            new_conn.executescript('\n'.join(sql_dump))
            new_conn.close()
            conn.close()
            
            # Replace original with repaired version
            os.replace(backup_path, db_path)
            
            print(f"[INFO] SQLite repair successful: {len(sql_dump)} lines dumped")
            
            cm = SqliteSaver.from_conn_string(db_path)
            return cm.__enter__()
        
        except Exception as e:
            # Clean up failed backup
            if os.path.exists(backup_path):
                os.remove(backup_path)
            
            print(f"[ERROR] SQLite repair failed: {e}")
            
            raise GraphCompileError(
                f"SQLite checkpoint database corruption detected and cannot be repaired. "
                f"Found {len(issues)} integrity violations. First issue: {issues[0]}"
            ) from e
    
    except sqlite3.Error as e:
        raise GraphCompileError(
            f"SQLite checkpoint database error: {e}"
        ) from e


def _create_postgres(config: Any):
    """
    Create PostgreSQL checkpointer with retry mechanism (FR-027).
    
    Implements research.md Decision 4:
    - 3 retry attempts with 1s intervals
    - Fixed intervals (not exponential backoff)
    - Retries on network errors only
    """
    # Lazy import to avoid module-level dependency issues
    try:
        from langgraph.checkpoint.postgres import PostgresSaver
    except ImportError as e:
        raise GraphCompileError(
            f"PostgreSQL checkpoint support not available. Install langgraph-checkpoint-postgres: {e}"
        ) from e
    
    # Import psycopg exceptions for retry logic
    try:
        from psycopg2 import OperationalError, InterfaceError
        POSTGRES_NETWORK_EXCEPTIONS = (
            OperationalError,   # Connection lost, timeout, server unreachable
            InterfaceError,     # Protocol errors
            ConnectionError,    # Socket-level issues
            OSError,            # Broken pipe, connection reset
        )
    except ImportError:
        # Try psycopg (version 3) if psycopg2 not available
        try:
            from psycopg import OperationalError, InterfaceError
            POSTGRES_NETWORK_EXCEPTIONS = (
                OperationalError,
                InterfaceError,
                ConnectionError,
                OSError,
            )
        except ImportError:
            # No psycopg available, use generic exceptions
            POSTGRES_NETWORK_EXCEPTIONS = (ConnectionError, OSError)
    
    # Extract DSN from config
    if isinstance(config, dict):
        dsn = config.get("checkpoint_postgres_dsn")
    else:
        dsn = config.checkpoint_postgres_dsn
    
    if not dsn:
        raise GraphCompileError(
            "checkpoint_postgres_dsn is required when checkpointer='postgres'"
        )
    
    # Retry logic
    max_attempts = 3
    retry_interval = 1.0  # seconds
    
    for attempt in range(1, max_attempts + 1):
        try:
            # Emit attempt event (would use logger.emit in full implementation)
            if attempt > 1:
                print(f"[INFO] PostgreSQL connection attempt {attempt}/{max_attempts}")
            
            saver = PostgresSaver.from_conn_string(dsn)
            
            if attempt > 1:
                print(f"[INFO] PostgreSQL connection succeeded on attempt {attempt}")
            
            return saver
        
        except POSTGRES_NETWORK_EXCEPTIONS as e:
            if attempt < max_attempts:
                print(f"[WARN] PostgreSQL connection failed (attempt {attempt}): {e}, retrying in {retry_interval}s")
                time.sleep(retry_interval)
            else:
                print(f"[ERROR] PostgreSQL connection failed after {max_attempts} attempts: {e}")
                raise GraphCompileError(
                    f"PostgreSQL checkpoint connection failed after {max_attempts} attempts: {e}"
                ) from e
        
        except Exception as e:
            # Non-retryable exception (authentication, permissions, etc.)
            raise GraphCompileError(
                f"PostgreSQL checkpoint connection failed: {e}"
            ) from e
    
    # Should never reach here due to raise in loop, but satisfy type checker
    raise GraphCompileError(
        f"PostgreSQL checkpoint connection failed after {max_attempts} attempts"
    )
