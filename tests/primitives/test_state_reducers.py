"""
Test state reducers with edge cases per research.md Decision 6.

Tests cover:
- None input handling (FR-039)
- Type conversion scenarios from Decision 6 table
- LLM output mistakes (incomplete JSON, wrong types, etc.)
- Defensive fallback behavior (FR-040: never raise exceptions)
"""

import pytest
from langagent.primitives.state_reducers import (
    replace_with_merge,
    merge_dict,
    overwrite_or_merge,
)


# ============================================================================
# replace_with_merge Tests (todos/scratchpad fields)
# ============================================================================

def test_replace_with_merge_none_inputs():
    """Test replace_with_merge with None inputs per FR-039."""
    # Both None -> empty list
    result = replace_with_merge(None, None)
    assert result == []
    
    # Current is None, update is valid -> return update
    result = replace_with_merge(None, [{"task": "new"}])
    assert result == [{"task": "new"}]
    
    # Current is valid, update is None -> return current
    result = replace_with_merge([{"task": "existing"}], None)
    assert result == [{"task": "existing"}]


def test_replace_with_merge_valid_list_dict():
    """Test replace_with_merge with valid list[dict] input."""
    current = [{"id": 1, "task": "old"}]
    update = [{"id": 2, "task": "new"}]
    
    result = replace_with_merge(current, update)
    assert result == update
    assert result is update  # Returns update directly (replace strategy)


def test_replace_with_merge_str_to_list_dict():
    """Test type conversion: str → list[dict] via JSON parse."""
    current = [{"task": "existing"}]
    
    # Valid JSON string -> list[dict]
    update = '[{"task": "new1"}, {"task": "new2"}]'
    result = replace_with_merge(current, update)
    assert result == [{"task": "new1"}, {"task": "new2"}]
    
    # Valid JSON string -> dict (wrap in list)
    update = '{"task": "single"}'
    result = replace_with_merge(current, update)
    assert result == [{"task": "single"}]
    
    # Invalid JSON string -> wrap as description
    update = "not json"
    result = replace_with_merge(current, update)
    assert result == [{"description": "not json"}]
    
    # Empty string -> wrap as description
    update = ""
    result = replace_with_merge(current, update)
    assert result == [{"description": ""}]


def test_replace_with_merge_dict_to_list_dict():
    """Test type conversion: dict → [dict]."""
    current = [{"task": "existing"}]
    update = {"task": "new", "priority": "high"}
    
    result = replace_with_merge(current, update)
    assert result == [{"task": "new", "priority": "high"}]


def test_replace_with_merge_list_str_to_list_dict():
    """Test type conversion: list[str] → list[dict] with description field."""
    current = [{"task": "existing"}]
    update = ["task1", "task2", "task3"]
    
    result = replace_with_merge(current, update)
    assert result == [
        {"description": "task1"},
        {"description": "task2"},
        {"description": "task3"},
    ]


def test_replace_with_merge_mixed_list_fallback():
    """Test list with mixed types falls back to current."""
    current = [{"task": "existing"}]
    update = [{"task": "valid"}, "string", 123, None]
    
    result = replace_with_merge(current, update)
    assert result == current  # Fallback to current on mixed types


def test_replace_with_merge_unexpected_type_fallback():
    """Test unexpected types (int, bool, bytes) fall back to current."""
    current = [{"task": "existing"}]
    
    # Int
    result = replace_with_merge(current, 123)
    assert result == current
    
    # Bool
    result = replace_with_merge(current, True)
    assert result == current
    
    # Bytes
    result = replace_with_merge(current, b"bytes")
    assert result == current


def test_replace_with_merge_incomplete_json():
    """Test incomplete JSON strings fall back gracefully."""
    current = [{"task": "existing"}]
    
    # Missing closing bracket
    update = '[{"task": "incomplete"'
    result = replace_with_merge(current, update)
    # Should wrap as description since JSON parse fails
    assert result == [{"description": '[{"task": "incomplete"'}]


def test_replace_with_merge_empty_list():
    """Test empty list returns empty list (replace strategy)."""
    current = [{"task": "existing"}]
    update = []
    
    result = replace_with_merge(current, update)
    assert result == []


# ============================================================================
# merge_dict Tests (files field)
# ============================================================================

def test_merge_dict_none_inputs():
    """Test merge_dict with None inputs per FR-039."""
    # Both None -> empty dict
    result = merge_dict(None, None)
    assert result == {}
    
    # Current is None, update is valid -> return update
    result = merge_dict(None, {"file1.txt": {"content": "new"}})
    assert result == {"file1.txt": {"content": "new"}}
    
    # Current is valid, update is None -> return current
    result = merge_dict({"file1.txt": {"content": "old"}}, None)
    assert result == {"file1.txt": {"content": "old"}}


def test_merge_dict_valid_merge():
    """Test merge_dict with valid dict[str, dict] inputs."""
    current = {"file1.txt": {"content": "old"}}
    update = {"file2.txt": {"content": "new"}}
    
    result = merge_dict(current, update)
    assert result == {
        "file1.txt": {"content": "old"},
        "file2.txt": {"content": "new"},
    }
    
    # Update overrides current
    current = {"file1.txt": {"content": "old"}}
    update = {"file1.txt": {"content": "updated"}}
    
    result = merge_dict(current, update)
    assert result == {"file1.txt": {"content": "updated"}}


def test_merge_dict_str_to_dict():
    """Test type conversion: str → dict via JSON parse."""
    current = {"file1.txt": {"content": "old"}}
    
    # Valid JSON string
    update = '{"file2.txt": {"content": "new"}}'
    result = merge_dict(current, update)
    assert result == {
        "file1.txt": {"content": "old"},
        "file2.txt": {"content": "new"},
    }
    
    # Invalid JSON string -> fall back to current
    update = "not json"
    result = merge_dict(current, update)
    assert result == current


def test_merge_dict_list_to_dict():
    """Test type conversion: list → dict by extracting keys from path/name/id fields."""
    current = {"file1.txt": {"content": "old"}}
    
    # List with path keys
    update = [
        {"path": "file2.txt", "content": "new2"},
        {"path": "file3.txt", "content": "new3"},
    ]
    result = merge_dict(current, update)
    assert result == {
        "file1.txt": {"content": "old"},
        "file2.txt": {"path": "file2.txt", "content": "new2"},
        "file3.txt": {"path": "file3.txt", "content": "new3"},
    }
    
    # List with name keys
    update = [
        {"name": "file4.txt", "content": "new4"},
    ]
    result = merge_dict(current, update)
    assert result == {
        "file1.txt": {"content": "old"},
        "file4.txt": {"name": "file4.txt", "content": "new4"},
    }
    
    # List with id keys
    update = [
        {"id": "file5", "content": "new5"},
    ]
    result = merge_dict(current, update)
    assert result == {
        "file1.txt": {"content": "old"},
        "file5": {"id": "file5", "content": "new5"},
    }


def test_merge_dict_list_without_keys_fallback():
    """Test list without path/name/id keys falls back to current."""
    current = {"file1.txt": {"content": "old"}}
    update = [
        {"content": "no key field"},
        {"data": "also no key"},
    ]
    
    result = merge_dict(current, update)
    assert result == current  # Fallback to current


def test_merge_dict_invalid_value_types_fallback():
    """Test dict with non-dict values falls back to current."""
    current = {"file1.txt": {"content": "old"}}
    
    # Dict with string values (not dict[str, dict])
    update = {"file2.txt": "string value"}
    result = merge_dict(current, update)
    assert result == current
    
    # Dict with mixed value types
    update = {"file2.txt": {"content": "valid"}, "file3.txt": "invalid"}
    result = merge_dict(current, update)
    assert result == current


def test_merge_dict_unexpected_type_fallback():
    """Test unexpected types fall back to current."""
    current = {"file1.txt": {"content": "old"}}
    
    # Int
    result = merge_dict(current, 123)
    assert result == current
    
    # Bool
    result = merge_dict(current, False)
    assert result == current


def test_merge_dict_empty_dict():
    """Test empty dict merges successfully."""
    current = {"file1.txt": {"content": "old"}}
    update = {}
    
    result = merge_dict(current, update)
    assert result == current


# ============================================================================
# overwrite_or_merge Tests (context field)
# ============================================================================

def test_overwrite_or_merge_none_inputs():
    """Test overwrite_or_merge with None inputs per FR-039."""
    # Both None -> empty dict
    result = overwrite_or_merge(None, None)
    assert result == {}
    
    # Current is None, update is valid (merge mode)
    result = overwrite_or_merge(None, {"key": "value"}, mode="merge_with_prior")
    assert result == {"key": "value"}
    
    # Current is None, update is valid (overwrite mode)
    result = overwrite_or_merge(None, {"key": "value"}, mode="overwrite")
    assert result == {"key": "value"}
    
    # Current is valid, update is None -> return current
    result = overwrite_or_merge({"key": "old"}, None)
    assert result == {"key": "old"}


def test_overwrite_or_merge_mode_overwrite():
    """Test overwrite mode discards current state."""
    current = {"key1": "old1", "key2": "old2"}
    update = {"key3": "new3"}
    
    result = overwrite_or_merge(current, update, mode="overwrite")
    assert result == {"key3": "new3"}
    assert "key1" not in result
    assert "key2" not in result


def test_overwrite_or_merge_mode_merge_with_prior():
    """Test merge_with_prior mode merges with current state."""
    current = {"key1": "old1", "key2": "old2"}
    update = {"key2": "updated2", "key3": "new3"}
    
    result = overwrite_or_merge(current, update, mode="merge_with_prior")
    assert result == {
        "key1": "old1",
        "key2": "updated2",  # Update overrides current
        "key3": "new3",
    }


def test_overwrite_or_merge_str_to_dict():
    """Test type conversion: str → dict via JSON parse."""
    current = {"key1": "old"}
    
    # Valid JSON string (merge mode)
    update = '{"key2": "new"}'
    result = overwrite_or_merge(current, update, mode="merge_with_prior")
    assert result == {"key1": "old", "key2": "new"}
    
    # Valid JSON string (overwrite mode)
    result = overwrite_or_merge(current, update, mode="overwrite")
    assert result == {"key2": "new"}
    
    # Invalid JSON string -> fall back to current
    update = "not json"
    result = overwrite_or_merge(current, update)
    assert result == current


def test_overwrite_or_merge_list_to_dict():
    """Test type conversion: list → index-keyed dict."""
    current = {"key1": "old"}
    
    # List conversion (merge mode)
    update = ["item0", "item1", "item2"]
    result = overwrite_or_merge(current, update, mode="merge_with_prior")
    assert result == {
        "key1": "old",
        "0": "item0",
        "1": "item1",
        "2": "item2",
    }
    
    # List conversion (overwrite mode)
    result = overwrite_or_merge(current, update, mode="overwrite")
    assert result == {
        "0": "item0",
        "1": "item1",
        "2": "item2",
    }
    assert "key1" not in result


def test_overwrite_or_merge_unexpected_type_fallback():
    """Test unexpected types fall back to current."""
    current = {"key1": "old"}
    
    # Int
    result = overwrite_or_merge(current, 123)
    assert result == current
    
    # Bool
    result = overwrite_or_merge(current, True)
    assert result == current
    
    # None type (already tested separately)
    result = overwrite_or_merge(current, None)
    assert result == current


def test_overwrite_or_merge_empty_dict():
    """Test empty dict behavior in both modes."""
    current = {"key1": "old"}
    update = {}
    
    # Merge mode: returns current (no keys to merge)
    result = overwrite_or_merge(current, update, mode="merge_with_prior")
    assert result == current
    
    # Overwrite mode: returns empty dict
    result = overwrite_or_merge(current, update, mode="overwrite")
    assert result == {}


def test_overwrite_or_merge_default_mode():
    """Test default mode is merge_with_prior."""
    current = {"key1": "old"}
    update = {"key2": "new"}
    
    # Default mode (no mode specified)
    result = overwrite_or_merge(current, update)
    assert result == {"key1": "old", "key2": "new"}


# ============================================================================
# Cross-Cutting Edge Cases
# ============================================================================

def test_all_reducers_never_raise_exceptions():
    """Test FR-040: All reducers never raise exceptions on malformed input."""
    malformed_inputs = [
        123,
        True,
        False,
        None,
        b"bytes",
        {"nested": {"dict": {"deep": "value"}}},
        [1, 2, 3],
        "invalid json [[[",
        "",
    ]
    
    for malformed in malformed_inputs:
        # replace_with_merge should not raise
        try:
            result = replace_with_merge([{"task": "test"}], malformed)
            assert result is not None
        except Exception as e:
            pytest.fail(f"replace_with_merge raised exception on {malformed}: {e}")
        
        # merge_dict should not raise
        try:
            result = merge_dict({"file": {"content": "test"}}, malformed)
            assert result is not None
        except Exception as e:
            pytest.fail(f"merge_dict raised exception on {malformed}: {e}")
        
        # overwrite_or_merge should not raise
        try:
            result = overwrite_or_merge({"key": "test"}, malformed)
            assert result is not None
        except Exception as e:
            pytest.fail(f"overwrite_or_merge raised exception on {malformed}: {e}")


def test_reducers_return_new_containers():
    """Test FR-035: Reducers are pure functions that return new containers."""
    # replace_with_merge
    current_list = [{"task": "test"}]
    update_list = [{"task": "new"}]
    result = replace_with_merge(current_list, update_list)
    assert result is update_list  # Returns update directly (replace strategy)
    
    # merge_dict
    current_dict = {"file1": {"content": "old"}}
    update_dict = {"file2": {"content": "new"}}
    result = merge_dict(current_dict, update_dict)
    assert result is not current_dict  # Returns new dict
    assert result is not update_dict
    assert current_dict == {"file1": {"content": "old"}}  # Original unchanged
    
    # overwrite_or_merge
    current_ctx = {"key1": "old"}
    update_ctx = {"key2": "new"}
    result = overwrite_or_merge(current_ctx, update_ctx)
    assert result is not current_ctx  # Returns new dict
    assert result is not update_ctx
    assert current_ctx == {"key1": "old"}  # Original unchanged
