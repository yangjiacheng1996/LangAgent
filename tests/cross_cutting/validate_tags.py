"""Tag whitelist validator (T061, SC-006).

Success Criterion: Verify exactly 45 tags from workflow.md are present in ALLOWED_TAGS.

Run: python3 -m tests.cross_cutting.validate_tags
"""

from langagent.cross_cutting import ALLOWED_TAGS


def validate_tag_whitelist():
    """Validate ALLOWED_TAGS contains exactly 45 tags with correct namespaces.
    
    SC-006: At least 45 tags registered in ALLOWED_TAGS whitelist.
    Expected distribution:
    - la.lifecycle.* : 12 tags
    - la.runtime.*   : 29 tags
    - la.cross_cutting.* : 4 tags
    Total: 45 tags
    """
    print(f"\n{'='*60}")
    print(f"Tag Whitelist Validation (SC-006)")
    print(f"{'='*60}")
    
    # Count by namespace
    lifecycle_tags = [t for t in ALLOWED_TAGS if t.startswith("la.lifecycle.")]
    runtime_tags = [t for t in ALLOWED_TAGS if t.startswith("la.runtime.")]
    cross_cutting_tags = [t for t in ALLOWED_TAGS if t.startswith("la.cross_cutting.")]
    
    total_tags = len(ALLOWED_TAGS)
    
    print(f"Total tags: {total_tags}")
    print(f"  la.lifecycle.*    : {len(lifecycle_tags)} tags")
    print(f"  la.runtime.*      : {len(runtime_tags)} tags")
    print(f"  la.cross_cutting.* : {len(cross_cutting_tags)} tags")
    print(f"\nExpected: 45 tags (12 + 29 + 4)")
    print(f"Status: {'✓ PASS' if total_tags == 45 else '✗ FAIL'}")
    
    # Detailed breakdown
    if total_tags != 45 or len(lifecycle_tags) != 12 or len(runtime_tags) != 29 or len(cross_cutting_tags) != 4:
        print(f"\n{'='*60}")
        print(f"VALIDATION ERRORS:")
        print(f"{'='*60}")
        
        if len(lifecycle_tags) != 12:
            print(f"✗ lifecycle tags: expected 12, got {len(lifecycle_tags)}")
            print(f"  Tags: {sorted(lifecycle_tags)}")
        
        if len(runtime_tags) != 29:
            print(f"✗ runtime tags: expected 29, got {len(runtime_tags)}")
            print(f"  Tags: {sorted(runtime_tags)}")
        
        if len(cross_cutting_tags) != 4:
            print(f"✗ cross_cutting tags: expected 4, got {len(cross_cutting_tags)}")
            print(f"  Tags: {sorted(cross_cutting_tags)}")
        
        raise AssertionError(f"Tag count mismatch: {total_tags} != 45")
    
    print(f"{'='*60}\n")
    
    # Verify all tags have 'la.' prefix
    non_la_tags = [t for t in ALLOWED_TAGS if not t.startswith("la.")]
    if non_la_tags:
        raise AssertionError(f"Tags without 'la.' prefix: {non_la_tags}")
    
    return True


if __name__ == "__main__":
    validate_tag_whitelist()
    print("✓ Tag whitelist validation complete. All 45 tags present.")
