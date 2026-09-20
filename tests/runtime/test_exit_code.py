"""Tests for exit_code module.

Tests cover:
- worst_of() function with all priority combinations
- Empty list edge case
- Duplicate codes handling
- Unknown codes handling
"""

import pytest
from langagent.runtime.exit_code import worst_of, EXIT_CODE_PRIORITY


class TestWorstOfFunction:
    """T011: Test worst_of() function behavior."""
    
    def test_worst_of_empty_list(self):
        """Empty list should return 0."""
        assert worst_of([]) == 0
    
    def test_worst_of_single_code(self):
        """Single code should return that code."""
        assert worst_of([0]) == 0
        assert worst_of([4]) == 4
        assert worst_of([130]) == 130
    
    def test_worst_of_priority_ordering(self):
        """T012: Higher priority code should win."""
        assert worst_of([0, 1, 4]) == 4  # I/O error (priority 9) > generic failure (priority 12)
    
    def test_worst_of_with_user_interrupt(self):
        """T013: SIGINT (130) should be highest priority."""
        assert worst_of([130, 70, 4]) == 130
    
    def test_worst_of_priority_130_overrides_all(self):
        """T014: 130 should override all other codes."""
        assert worst_of([130, 70, 4, 1, 0]) == 130
    
    def test_worst_of_with_duplicates(self):
        """Duplicate codes should be handled correctly."""
        assert worst_of([4, 4, 1]) == 4
    
    def test_worst_of_unknown_codes(self):
        """Unknown codes should be treated as lowest priority."""
        assert worst_of([999, 1]) == 1
        assert worst_of([999]) == 999  # Only unknown code


class TestExitCodePriorityTable:
    """Validate EXIT_CODE_PRIORITY table structure."""
    
    def test_priority_table_has_all_13_codes(self):
        """Verify all 13 exit codes are defined."""
        assert len(EXIT_CODE_PRIORITY) == 13
    
    def test_priority_ranks_are_unique(self):
        """All priority ranks should be unique."""
        ranks = list(EXIT_CODE_PRIORITY.values())
        assert len(ranks) == len(set(ranks))
    
    def test_priority_130_is_highest(self):
        """SIGINT (130) should have priority 1 (highest)."""
        assert EXIT_CODE_PRIORITY[130] == 1
    
    def test_priority_0_is_lowest(self):
        """Success (0) should have priority 13 (lowest)."""
        assert EXIT_CODE_PRIORITY[0] == 13
