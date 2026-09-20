"""Exit code priority management for LangAgent.

Defines exit code priority table and arbitration logic.
Constitutional alignment: Article XV (top-level design primacy)
"""

# Exit code priority mapping (lower rank = higher priority)
# Priority 1 = highest (SIGINT), Priority 13 = lowest (SUCCESS)
EXIT_CODE_PRIORITY = {
    130: 1,   # SIGINT (Ctrl-C) - user interrupt
    70: 2,    # EX_SOFTWARE - internal software error
    67: 3,    # name_already_exists (langagent init)
    78: 4,    # EX_CONFIG - configuration error
    66: 5,    # EX_NOINPUT - cannot open input
    65: 6,    # EX_DATAERR - malformed .env file
    64: 7,    # EX_USAGE - command line usage error
    5: 8,     # RequiredFieldMissingError
    4: 9,     # I/O error (AuditFlushError, file writes)
    3: 10,    # data_error - invalid data format
    2: 11,    # usage_error - argument parsing failure
    1: 12,    # generic_failure - StageCapabilityViolationError
    0: 13     # success (lowest priority)
}


def worst_of(codes: list[int]) -> int:
    """Return highest priority exit code from list.
    
    Args:
        codes: List of exit codes (may contain duplicates or be empty)
        
    Returns:
        Highest priority code, or 0 if list is empty
        
    Examples:
        >>> worst_of([])
        0
        >>> worst_of([0, 1, 4])
        4
        >>> worst_of([130, 70, 4])
        130
        >>> worst_of([4, 4, 1])
        4
    """
    if not codes:
        return 0
    
    # Return code with minimum priority rank (1 = highest priority)
    # Unknown codes get priority 999 (treated as lowest)
    return min(codes, key=lambda c: EXIT_CODE_PRIORITY.get(c, 999))
