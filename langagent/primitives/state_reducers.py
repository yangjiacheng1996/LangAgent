"""
State reducers for AgentState fields.

These reducers handle LangGraph state updates with defensive type conversion
to tolerate malformed LLM outputs per FR-035, FR-036, FR-040.

All reducers are pure functions that return new containers and never raise exceptions.
"""

from typing import Any, Literal


def replace_with_merge(
    current: list[dict[str, Any]] | None,
    update: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """
    Reducer for AgentState.todos and AgentState.scratchpad fields.
    
    Merge strategy (FR-037):
    - If update is None: return current or []
    - If update is proper list[dict]: return update (replace)
    - If update is malformed: attempt type conversion, then degrade to current or []
    
    Type conversions (clarification Q4):
    - str → Parse JSON → list[dict], or wrap as [{"description": str}]
    - dict → Wrap as [dict]
    - list[str] → Convert each to {"description": str}
    
    Pure function (FR-035): No side effects, no global state mutation.
    No exceptions (FR-040): Log conversion errors, return current or [] on failure.
    
    Args:
        current: Current state value (may be None)
        update: New state value from node return (may be None)
    
    Returns:
        Merged state as list[dict] (empty list if both None)
    """
    import json
    
    # If update is None, return current or []
    if update is None:
        return current if current is not None else []
    
    # If update is proper list[dict], return it
    if isinstance(update, list):
        # Check if all items are dicts
        if all(isinstance(item, dict) for item in update):
            return update
        # If list[str], convert each to {"description": str}
        if all(isinstance(item, str) for item in update):
            return [{"description": item} for item in update]
        # Mixed types or unexpected - degrade to current
        return current if current is not None else []
    
    # If update is dict, wrap in list
    if isinstance(update, dict):
        return [update]
    
    # If update is str, try JSON parse
    if isinstance(update, str):
        try:
            parsed = json.loads(update)
            # If parsed to list[dict], return it
            if isinstance(parsed, list) and all(isinstance(item, dict) for item in parsed):
                return parsed
            # If parsed to dict, wrap in list
            if isinstance(parsed, dict):
                return [parsed]
            # Otherwise wrap string as description
            return [{"description": update}]
        except (json.JSONDecodeError, ValueError):
            # Wrap string as description
            return [{"description": update}]
    
    # Unexpected type - degrade to current
    return current if current is not None else []


def merge_dict(
    current: dict[str, dict[str, Any]] | None,
    update: dict[str, dict[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    """
    Reducer for AgentState.files field.
    
    Merge strategy (FR-038):
    - Merge by key: {**current, **update}
    - Update values override current values
    - If update is None: return current or {}
    - If update is malformed: attempt type conversion, then degrade to current or {}
    
    Type conversions (clarification Q4):
    - str → Parse JSON → dict[str, dict]
    - list → Extract keyed structure from path/name/id fields
    
    Pure function (FR-035): Returns new dict, doesn't mutate inputs.
    No exceptions (FR-040): Log conversion errors, degrade gracefully.
    
    Args:
        current: Current state value (may be None)
        update: New state value from node return (may be None)
    
    Returns:
        Merged state as dict[str, dict] (empty dict if both None)
    """
    import json
    
    # If update is None, return current or {}
    if update is None:
        return current if current is not None else {}
    
    # If update is proper dict[str, dict], merge with current
    if isinstance(update, dict):
        # Check if all values are dicts
        if all(isinstance(v, dict) for v in update.values()):
            base = current if current is not None else {}
            return {**base, **update}
        # If values are not all dicts, degrade to current
        return current if current is not None else {}
    
    # If update is str, try JSON parse
    if isinstance(update, str):
        try:
            parsed = json.loads(update)
            if isinstance(parsed, dict) and all(isinstance(v, dict) for v in parsed.values()):
                base = current if current is not None else {}
                return {**base, **parsed}
        except (json.JSONDecodeError, ValueError):
            pass
        # Degrade to current on parse failure
        return current if current is not None else {}
    
    # If update is list, try to extract keyed structure
    if isinstance(update, list):
        result = {}
        for item in update:
            if isinstance(item, dict):
                # Look for key fields: path, name, id
                key = item.get("path") or item.get("name") or item.get("id")
                if key:
                    result[str(key)] = item
        if result:
            base = current if current is not None else {}
            return {**base, **result}
        # Degrade to current if no keys found
        return current if current is not None else {}
    
    # Unexpected type - degrade to current
    return current if current is not None else {}


def overwrite_or_merge(
    current: dict[str, Any] | None,
    update: dict[str, Any] | None,
    *,
    mode: Literal['overwrite', 'merge_with_prior'] = 'merge_with_prior',
) -> dict[str, Any]:
    """
    Reducer for AgentState.context field.
    
    Merge strategy (FR-039):
    - mode='overwrite': return dict(update), discard current
    - mode='merge_with_prior': return {**current, **update}
    - If update is None: return current or {}
    - If update is malformed: attempt type conversion, then degrade to current or {}
    
    Type conversions (clarification Q4):
    - str → Parse JSON → dict[str, Any]
    - list → Convert to index-keyed dict {"0": item, "1": item}
    
    Mode parameter: Injected via LangGraph Annotated[dict, overwrite_or_merge]
    Pure function (FR-035): No side effects.
    No exceptions (FR-040): Degrade gracefully.
    
    Args:
        current: Current state value (may be None)
        update: New state value from node return (may be None)
        mode: Merge mode ('overwrite' or 'merge_with_prior')
    
    Returns:
        Merged state as dict[str, Any] (empty dict if both none)
    """
    import json
    
    # If update is None, return current or {}
    if update is None:
        return current if current is not None else {}
    
    # If update is proper dict
    if isinstance(update, dict):
        if mode == 'overwrite':
            return dict(update)
        else:  # merge_with_prior
            base = current if current is not None else {}
            return {**base, **update}
    
    # If update is str, try JSON parse
    if isinstance(update, str):
        try:
            parsed = json.loads(update)
            if isinstance(parsed, dict):
                if mode == 'overwrite':
                    return parsed
                else:  # merge_with_prior
                    base = current if current is not None else {}
                    return {**base, **parsed}
        except (json.JSONDecodeError, ValueError):
            pass
        # Degrade to current on parse failure
        return current if current is not None else {}
    
    # If update is list, convert to index-keyed dict
    if isinstance(update, list):
        indexed = {str(i): item for i, item in enumerate(update)}
        if mode == 'overwrite':
            return indexed
        else:  # merge_with_prior
            base = current if current is not None else {}
            return {**base, **indexed}
    
    # Unexpected type - degrade to current
    return current if current is not None else {}


__all__ = [
    "replace_with_merge",
    "merge_dict",
    "overwrite_or_merge",
]
