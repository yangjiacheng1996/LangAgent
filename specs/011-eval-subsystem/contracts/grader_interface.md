# Grader Interface Contract

**Version**: v0.1.0  
**Feature**: F11 Eval Subsystem  
**Purpose**: Define the uniform interface contract for all 5 grader implementations

---

## Overview

All graders must implement a stateless pure function with the signature:

```python
def grade(actual: str, expected: str | list[str] | dict[str, Any], **kwargs) -> bool:
    """
    Evaluate whether actual output matches expected output.
    
    Args:
        actual: Agent's actual output (typically AIMessage.content or full state)
        expected: Expected output (type depends on grader)
        **kwargs: Grader-specific optional parameters
    
    Returns:
        True if output passes grader criteria, False otherwise
    
    Raises:
        EvalGraderArgumentMismatchError: If expected type doesn't match grader requirements
    """
```

---

## Grader 1: exact_match

### Purpose
Exact string equality after whitespace normalization.

### Signature
```python
def grade(actual: str, expected: str | list[str], **kwargs) -> bool
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `actual` | str | Yes | Agent's output |
| `expected` | str \| list[str] | Yes | Single expected string or list of acceptable strings |

### Logic

1. Strip leading/trailing whitespace from `actual`
2. If `expected` is a list, try matching against each item (any match → pass)
3. Return `actual == expected` (or any match if list)

### Notes

- **exact_match is always case-sensitive** and does not accept `case_sensitive` parameter
- For case-insensitive matching, use `contains` grader with `case_sensitive=false`

### Example

```python
# Pass: exact match after strip
grade("Hello, Alice!", "Hello, Alice!")  # → True

# Pass: matches one of list
grade("Hello", ["Hello", "Hi", "Hey"])  # → True

# Fail: case mismatch (exact_match is always case-sensitive)
grade("hello", "Hello")  # → False
```

---

## Grader 2: contains

### Purpose
Substring containment check (expected substring must appear in actual).

### Signature
```python
def grade(actual: str, expected: str | list[str], **kwargs) -> bool
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `actual` | str | Yes | Agent's output |
| `expected` | str \| list[str] | Yes | Substring(s) that must appear in actual |
| `case_sensitive` | bool | No (kwarg) | Default: True |

### Logic

1. If `expected` is a list, try matching each substring (any match → pass)
2. If `case_sensitive=False`, lowercase both strings before checking
3. Return `expected in actual` (or any substring match if list)

### Example

```python
# Pass: substring present
grade("The answer is 42", "42")  # → True

# Pass: one of multiple substrings
grade("def factorial(n):", ["def ", "return"])  # → True

# Fail: substring not found
grade("Hello World", "Goodbye")  # → False

# Pass: case-insensitive match
grade("Hello World", "hello", case_sensitive=False)  # → True

# Fail: case-sensitive by default
grade("Hello World", "hello")  # → False
```

---

## Grader 3: regex

### Purpose
Regular expression pattern matching.

### Signature
```python
def grade(actual: str, expected: str | list[str], **kwargs) -> bool
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `actual` | str | Yes | Agent's output |
| `expected` | str \| list[str] | Yes | Regex pattern(s) to match |
| `case_sensitive` | bool | No (kwarg) | Default: True (controls re.IGNORECASE flag) |

### Logic

1. If `case_sensitive=False`, compile with `re.IGNORECASE` flag
2. Compile each `expected` pattern with `re.compile(pattern, flags)`
3. If `expected` is a list, try matching each pattern (any match → pass)
4. Return `pattern.search(actual) is not None`
5. If pattern compilation fails, raise `EvalGraderRegexCompileError`

### Example

```python
import re

# Pass: phone number format
grade("Call me at 123-456-7890", r"\d{3}-\d{3}-\d{4}")  # → True

# Pass: one of multiple patterns
grade("The result: 42", [r"\d+", r"result"])  # → True

# Fail: pattern not found
grade("Hello", r"^\d+$")  # → False

# Pass: case-insensitive regex
grade("Hello World", r"^hello", case_sensitive=False)  # → True

# Fail: case-sensitive by default
grade("Hello World", r"^hello")  # → False

# Error: invalid regex
grade("test", "[")  # → raises EvalGraderRegexCompileError
```

---

## Grader 4: llm_judge

### Purpose
Use independent LLM to judge semantic equivalence.

### Signature
```python
def grade(actual: str, expected: str | list[str], judge_model: BaseChatModel, **kwargs) -> bool
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `actual` | str | Yes | Agent's output |
| `expected` | str \| list[str] | Yes | Reference answer(s) |
| `judge_model` | BaseChatModel | Yes | Independent model instance for judging |
| `threshold` | float | No (kwarg) | Confidence threshold (default: 0.7) |

### Logic

1. Construct judge prompt:
   ```
   You are an evaluation judge. Compare the actual output to the expected output.
   Answer with ONLY "YES" if semantically equivalent, or "NO" if not.
   
   Expected: {expected}
   Actual: {actual}
   ```
2. Call `judge_model.invoke([HumanMessage(prompt)])`
3. Extract response text, strip whitespace, uppercase
4. If response starts with "YES" → return True
5. If response starts with "NO" → return False
6. Otherwise → raise `LlmJudgeInvalidResponseError`

### Example

```python
# Pass: semantic equivalence
judge_model = chat_model_factory.create(config)
grade("Buenos días", "Hello", judge_model=judge_model)  # → True (if judge says YES)

# Fail: semantic difference
grade("Goodbye", "Hello", judge_model=judge_model)  # → False
```

### Notes
- **Independence**: `judge_model` must be separate instance from agent's model (avoid judge bias)
- **Caching**: Runner creates judge_model once per eval run, reuses across all llm_judge tasks
- **Cost**: Each call incurs API cost (input + output tokens)

---

## Grader 5: tool_call_match

### Purpose
Verify agent invoked specific tool with correct arguments.

### Signature
```python
def grade(actual_ai_message: AIMessage, expected: dict[str, Any], **kwargs) -> bool
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `actual_ai_message` | AIMessage | Yes | Agent's output message with tool_calls |
| `expected` | dict | Yes | Must contain `tool_id` and `args` keys |
| `strict_args` | bool | No (kwarg) | Default: False (subset match) |

### Logic

1. Validate `expected` is dict with keys `tool_id` and `args`
2. If not, raise `EvalGraderArgumentMismatchError`
3. Iterate over `actual_ai_message.tool_calls` list
4. For each tool call:
   - Check if `call["name"] == expected["tool_id"]`
   - If `strict_args=False`: Check if all `expected["args"]` items are subset of `call["args"]`
   - If `strict_args=True`: Check if `call["args"] == expected["args"]` (exact match)
5. Return True if any tool call matches, False otherwise

### Example

```python
# Pass: tool called with matching args (subset)
expected = {"tool_id": "web_search", "args": {"query": "LangChain"}}
ai_message = AIMessage(
    content="",
    tool_calls=[
        {"name": "web_search", "args": {"query": "LangChain", "limit": 10}, "id": "call_123"}
    ]
)
grade(ai_message, expected)  # → True (subset match: query present, limit ignored)

# Fail: wrong tool
expected = {"tool_id": "calculator", "args": {"expression": "2+2"}}
grade(ai_message, expected)  # → False (web_search != calculator)

# Fail: missing required arg
expected = {"tool_id": "web_search", "args": {"query": "Python"}}
ai_message = AIMessage(tool_calls=[{"name": "web_search", "args": {"limit": 5}}])
grade(ai_message, expected)  # → False (query missing)

# Error: expected not dict
grade(ai_message, "some_string")  # → raises EvalGraderArgumentMismatchError
```

### Notes
- **Double Validation**: Schema validator checks grader-expected type at YAML load time; runtime validator is fallback
- **Subset vs Exact**: Default subset matching allows extra args (flexible), strict mode requires exact match

---

## Registry Interface

Graders are registered in `langagent/eval/graders/__init__.py`:

```python
from typing import Callable, Any

GraderFunction = Callable[..., bool]

GRADER_REGISTRY: dict[str, GraderFunction] = {
    "exact_match": exact_match.grade,
    "contains": contains.grade,
    "regex": regex.grade,
    "llm_judge": llm_judge.grade,
    "tool_call_match": tool_call_match.grade,
}

def get_grader(grader_name: str) -> GraderFunction:
    """Retrieve grader function by name. Raises EvalGraderUnknownError if not found."""
    if grader_name not in GRADER_REGISTRY:
        raise EvalGraderUnknownError(f"Unknown grader: {grader_name}")
    return GRADER_REGISTRY[grader_name]
```

---

## Error Handling

| Error Type | Raised When | Exit Code |
|------------|-------------|-----------|
| `EvalGraderArgumentMismatchError` | tool_call_match receives non-dict expected | 65 |
| `EvalGraderRegexCompileError` | regex pattern invalid | 65 |
| `LlmJudgeInvalidResponseError` | judge model returns non-YES/NO | 70 |
| `EvalGraderUnknownError` | grader name not in registry | 78 |

---

## Testing Contract

Each grader must have ≥3 unit tests:
1. **Pass case**: Valid input returns True
2. **Fail case**: Invalid input returns False
3. **Error case**: Invalid arguments raise appropriate exception

Example test structure:

```python
# tests/eval/graders/test_exact_match.py

def test_exact_match_pass():
    assert exact_match.grade("hello", "hello") is True

def test_exact_match_fail():
    assert exact_match.grade("hello", "goodbye") is False

def test_exact_match_list_any_match():
    assert exact_match.grade("hello", ["hi", "hello", "hey"]) is True
```

---

## Extension Guidelines (Future)

To add a 6th grader in v2:
1. Create `langagent/eval/graders/new_grader.py` with `grade()` function
2. Update `EvalTaskSpec.grader` Literal enum in `module_schemas.md`
3. Register in `GRADER_REGISTRY` dict
4. Add ≥3 tests in `tests/eval/graders/test_new_grader.py`
5. Document in `grader_extensibility` field usage
6. Bump `EvalTaskSpec.schema_version` to v0.3.0

---

## Implementation Checklist

- [ ] All 5 graders implement `grade()` function
- [ ] All graders are stateless pure functions (no side effects)
- [ ] Registry populated in `__init__.py`
- [ ] Each grader has ≥3 unit tests
- [ ] Error types defined in `langagent/eval/exceptions.py`
- [ ] llm_judge uses independent model instance
- [ ] tool_call_match validates expected type at runtime
