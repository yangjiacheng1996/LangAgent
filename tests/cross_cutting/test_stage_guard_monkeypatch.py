"""Tests for monkeypatch functionality in stage guard."""

import pytest
from langagent.cross_cutting.stage_guard_monkeypatch import (
    Monkeystack,
    patch_class_method,
    restore_class_method,
)
from langagent.cross_cutting.stage_guard import StageCapabilityViolationError


class TestMonkeypatch:
    """Test monkeypatch utilities."""
    
    def test_stage_guard_monkeypatch_patch_restore(self):
        """Test patch and restore functionality."""
        class TestClass:
            def method(self):
                return "original"
        
        original_method = TestClass.method
        
        # Patch the method
        blocking_method = patch_class_method(TestClass, 'method', 'test_stage')
        TestClass.method = blocking_method
        
        # Verify patch works
        obj = TestClass()
        with pytest.raises(StageCapabilityViolationError):
            obj.method()
        
        # Restore the method
        restore_class_method(TestClass, 'method', original_method)
        
        # Verify restoration
        obj2 = TestClass()
        result = obj2.method()
        assert result == "original"
    
    def test_stage_guard_monkeypatch_nested(self):
        """Test nested monkeypatch operations."""
        class TestClass:
            def method(self):
                return "original"
        
        stack = Monkeystack()
        
        # Push first patch
        stack.push(TestClass, 'method', 'stage1')
        
        obj = TestClass()
        with pytest.raises(StageCapabilityViolationError):
            obj.method()
        
        # Pop patch
        stack.pop()
        
        # Verify restoration
        obj2 = TestClass()
        result = obj2.method()
        assert result == "original"
    
    def test_stage_guard_monkeypatch_exception_safety(self):
        """Test that monkeypatch cleanup happens even with exceptions."""
        class TestClass:
            def method(self):
                return "original"
        
        stack = Monkeystack()
        
        try:
            stack.push(TestClass, 'method', 'test_stage')
            raise ValueError("Test exception")
        except ValueError:
            pass
        finally:
            # Cleanup should happen in finally block
            stack.pop()
        
        # Verify method is restored
        obj = TestClass()
        result = obj.method()
        assert result == "original"
