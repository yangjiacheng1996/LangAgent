"""Validation script: Verify ALLOWED_TAGS has exactly 46 tags.

This script validates that the tag whitelist matches the specification from workflow.md.
"""
from langagent.cross_cutting import ALLOWED_TAGS


def validate_tags():
    """Validate ALLOWED_TAGS count and structure."""
    expected_count = 46
    actual_count = len(ALLOWED_TAGS)
    
    print(f"Expected tags: {expected_count}")
    print(f"Actual tags: {actual_count}")
    
    if actual_count == expected_count:
        print("✓ PASS: ALLOWED_TAGS has exactly 46 tags")
        return True
    else:
        print(f"✗ FAIL: Expected {expected_count} tags, got {actual_count}")
        return False


if __name__ == "__main__":
    success = validate_tags()
    exit(0 if success else 1)
