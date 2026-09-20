# API Contract: run_until_done()

**Module**: `langagent.runtime.main_loop_dispatcher`  
**Function**: `run_until_done`  
**Version**: v1.0.0  
**Date**: 2026-09-20

---

## Signature

```python
@stage_guard_decorator('main_loop')
def run_until_done(
    graph: CompiledStateGraph,
    state: AgentState,
    max_turns: int = 30
) -> AgentState:
    """运行完整 ReAct 主循环，直至收敛、中断或超限。
    
    重复调用 dispatch() 直到满足终止条件之一：
    1. 收敛：模型返回不含 tool_calls 的 AIMessage（任务完成）
    2. 超限：turn_count >= max_turns（触发 TokenLimitExceededError）
    3. 中断：用户 Ctrl-C 或 guardrail 拦截（触发 HitlInterruptedError）
    
    每轮调用 dispatch()，累积更新 state，直到循环终止。
    
    Args:
        graph: F01 编译的 CompiledStateGraph
        state: 初始 AgentState（必须含 messages 字段，通常含 HumanMessage）
        max_turns: 最大轮次限制（默认 30）
    
    Returns:
        最终 AgentState（包含完整对话历史、工具执行结果、错误记录）
    
    Raises:
        TokenLimitExceededError: 
            turn_count >= max_turns 且模型仍生成 tool_calls
            退出码 70
        
        HitlInterruptedError:
            - reason="keyboard_interrupt": 用户按 Ctrl-C
            - reason="guardrail_block": F04 guardrail 拦截
            - reason="tool_approval_required": 工具需审批
            异常携带 error.state（当前 AgentState 快照）
            退出码 130
        
        StageCapabilityViolationError:
            main_loop 阶段尝试禁止操作
            退出码 1
    
    Side Effects:
        - 所有 dispatch() 的副作用 × N 轮
        - 额外发射 Log:
          * la.lifecycle.run.start (循环开始)
          * la.runtime.main_loop.start (循环开始，运行时视角)
          * la.runtime.main_loop.end (循环结束)
        - 当 turn >= max_turns * 0.9 时发射警告日志:
          * la.runtime.main_loop.near_limit (接近限制)
    
    Thread Safety:
        非线程安全。调用者必须保证串行调用。
    
    Performance:
        - 总延迟 = dispatch_latency × turn_count
        - 典型 3 轮任务：本地 vLLM 3-9s，OpenAI API 6-15s
        - 最坏情况 30 轮：本地 vLLM 30-90s，OpenAI API 60-150s
    """
```

---

## Parameters

### `graph: CompiledStateGraph`

- **Type**: `langagent.primitives.langchain_types.CompiledStateGraph`
- **Required**: Yes
- **Same as dispatch()**: 参见 [dispatch.md](./dispatch.md#graph-compiledstategraph)

### `state: AgentState`

- **Type**: `langagent.runtime.agent_state.AgentState`
- **Required**: Yes
- **Same as dispatch()**: 参见 [dispatch.md](./dispatch.md#state-agentstate)

### `max_turns: int`

- **Type**: `int`
- **Required**: No (default 30)
- **Constraints**:
  - 必须 > 0
  - 推荐范围: 10-100
  - 过小（<5）可能导致复杂任务无法完成
  - 过大（>100）可能消耗大量 token 和时间
- **Rationale**: 
  - 默认 30 基于假设"95% 的真实任务在 30 轮内收敛"（使用 GPT-4/Claude/Qwen 等能力模型）
  - 较弱模型（如本地 7B 模型）可能需要更多轮次

---

## Return Value

### `AgentState`

- **Type**: `langagent.runtime.agent_state.AgentState`
- **Guarantees**:
  - `messages` 字段包含完整对话历史（HumanMessage → AIMessage → ToolMessage → ... → final AIMessage）
  - 最后一条 AIMessage **不含** tool_calls（收敛标志）
  - 如有工具失败，`scratchpad["errors"]` 包含所有 ErrorEntry（按 turn 升序）
  - Turn count = len([msg for msg in messages if isinstance(msg, AIMessage)])
- **Post-Conditions**:
  - State 可直接传递给 F09 exit_cleanup 阶段
  - F11 eval runner 可提取最后一条 AIMessage.content 作为答案

---

## Exceptions

### `TokenLimitExceededError`

**When**: `turn_count >= max_turns` 且最后一条 AIMessage 仍含 tool_calls

**Attributes**:
```python
@dataclass(frozen=True)
class TokenLimitExceededError(Exception):
    turn_count: int       # 当前轮次（>= max_turns）
    max_turns: int        # 配置的最大轮次
    message: str = "Agent exceeded maximum turn limit"
```

**Caller Responsibility**:
- F10 CLI: 打印错误提示，建议检查模型配置或提示词，退出码 70
- F11 eval: 记录 `TaskResult.exceeded_limit=True`，继续下一任务

**Example**:
```python
try:
    final_state = run_until_done(graph, state, max_turns=10)
except TokenLimitExceededError as e:
    print(f"Agent did not converge after {e.turn_count} turns")
    print(f"Consider: 1) Increasing max_turns, 2) Simplifying task, 3) Reviewing system prompt")
```

### `HitlInterruptedError`

**Same as dispatch()**: 参见 [dispatch.md](./dispatch.md#hitlinterruptederror)

**Additional Context**: 
- 中断可能发生在任意轮次（turn 1 到 turn N）
- `error.state` 包含中断轮次之前的所有 messages

### `StageCapabilityViolationError`

**Same as dispatch()**: 参见 [dispatch.md](./dispatch.md#stagecapabilityviolationerror)

---

## Side Effects

### Event Bus Emission

**Published Events** (N 轮累积):
- `tool_call` × (total tool calls across all turns)
- `tool_result` × (total tool calls across all turns)
- `model_response` × N (每轮 1 个)

### Structured Logging

**Emitted Tags** (run_until_done 范围):

| Tag | Timing | Frequency |
|-----|--------|-----------|
| `la.lifecycle.run.start` | 循环入口 | 1次 |
| `la.runtime.main_loop.start` | 循环入口 | 1次 |
| `la.lifecycle.run.turn` | 每轮开始 | N次 |
| `la.runtime.main_loop.turn.start` | 每轮开始 | N次 |
| `la.runtime.main_loop.turn.end` | 每轮结束 | N次 |
| `la.lifecycle.run.tool_call` | 每个工具调用 | M次（M=总工具调用数） |
| `la.runtime.main_loop.tool_call` | 每个工具调用 | M次 |
| `la.lifecycle.run.tool_result` | 每个工具结果 | M次 |
| `la.runtime.main_loop.tool_result` | 每个工具结果 | M次 |
| `la.lifecycle.run.model_response` | 每轮模型回复 | N次 |
| `la.runtime.main_loop.model_call` | 每轮模型调用 | N次 |
| `la.runtime.main_loop.near_limit` | 接近 max_turns | 0或多次（turn >= max_turns * 0.9） |
| `la.runtime.main_loop.end` | 循环收尾 | 1次 |

**Total Tags**: 12 个唯一 tag（其中 10 个每轮重复，2 个仅 1 次）

**Not Emitted** (但观测到):
- `la.cross_cutting.guardrail.block` - F04 发射（如触发）

### Near-Limit Warning

当 `turn >= max_turns * 0.9` 时，每轮发射警告：

```python
# 伪代码
if turn >= max_turns * 0.9:
    logger.emit("la.runtime.main_loop.near_limit", {
        "turn": turn,
        "max_turns": max_turns,
        "remaining": max_turns - turn,
        "message": f"Approaching turn limit: {turn}/{max_turns}"
    })
```

**Example** (max_turns=30):
- Turn 27: 发射警告（27 >= 30 * 0.9 = 27）
- Turn 28: 发射警告
- Turn 29: 发射警告
- Turn 30: 如收敛则正常结束；如未收敛则抛 TokenLimitExceededError

---

## Loop Termination Conditions

### 1. 收敛（正常终止）

**Condition**: 最后一条 AIMessage 不含 tool_calls（`len(ai_message.tool_calls) == 0`）

**Example**:
```python
# 最后一条 AIMessage
AIMessage(content="The answer is 42.", tool_calls=[])
# → 循环终止，返回 state
```

**Exit Code**: 0

### 2. 超限（异常终止）

**Condition**: `turn_count >= max_turns` 且最后一条 AIMessage 仍含 tool_calls

**Example**:
```python
# Turn 30
AIMessage(content="Let me check one more thing...", tool_calls=[{"name": "search", ...}])
# → 抛出 TokenLimitExceededError
```

**Exit Code**: 70

### 3. 中断（异常终止）

**Condition**: 
- KeyboardInterrupt 捕获
- LangGraph GraphInterrupt/Interrupt 抛出

**Example**:
```python
# Turn 5: 用户按 Ctrl-C
# → 抛出 HitlInterruptedError(reason="keyboard_interrupt", state=...)
```

**Exit Code**: 130

---

## Examples

### Example 1: 正常收敛（3 轮）

```python
from langagent.primitives.langchain_types import HumanMessage
from langagent.runtime.main_loop_dispatcher import run_until_done

state = {
    "messages": [HumanMessage(content="What is 10 + 5?")]
}

final_state = run_until_done(graph, state, max_turns=30)

# 结果
assert len(final_state["messages"]) >= 2  # 至少 HumanMessage + AIMessage
assert "15" in final_state["messages"][-1].content
```

### Example 2: 超限终止

```python
state = {
    "messages": [HumanMessage(content="Complex task requiring 50 steps")]
}

try:
    run_until_done(graph, state, max_turns=10)
except TokenLimitExceededError as e:
    assert e.turn_count == 10
    assert e.max_turns == 10
    print(f"Task too complex for {e.max_turns} turns")
```

### Example 3: 中断恢复（伪代码）

```python
state = {"messages": [HumanMessage(content="Long task")]}

try:
    final_state = run_until_done(graph, state, max_turns=30)
except HitlInterruptedError as e:
    # F10 CLI: 保存 e.state 到文件，退出
    save_checkpoint(e.state, "checkpoint.json")
    sys.exit(130)

# 恢复（需要额外逻辑，F08 不提供）
# resumed_state = load_checkpoint("checkpoint.json")
# final_state = run_until_done(graph, resumed_state, max_turns=30)
```

### Example 4: 工具错误累积

```python
state = {"messages": [HumanMessage(content="Call 3 tools, 2 fail")]}

final_state = run_until_done(graph, state, max_turns=30)

# 结果：2 个工具失败记录
assert len(final_state["scratchpad"]["errors"]) == 2
for error_entry in final_state["scratchpad"]["errors"]:
    assert "turn" in error_entry
    assert "tool" in error_entry
```

---

## Testing Strategies

### Unit Tests

```python
def test_run_until_done_converges_3_turns(fake_graph_3_turns):
    """模型在 3 轮后收敛，返回最终 state"""
    state = {"messages": [HumanMessage(content="Task")]}
    result = run_until_done(fake_graph_3_turns, state, max_turns=30)
    assert len(result["messages"]) >= 4  # Human + (AI + Tool) × 2 + final AI

def test_run_until_done_exceeds_max_turns(fake_graph_infinite_loop):
    """模型永不收敛，30 轮后抛 TokenLimitExceededError"""
    state = {"messages": [HumanMessage(content="Infinite")]}
    with pytest.raises(TokenLimitExceededError) as exc_info:
        run_until_done(fake_graph_infinite_loop, state, max_turns=30)
    assert exc_info.value.turn_count == 30

def test_run_until_done_emits_near_limit_warning(fake_graph, mock_logger):
    """接近 max_turns 时发射警告日志"""
    state = {"messages": [HumanMessage(content="Task")]}
    # 模拟 28 轮收敛（触发 27/28 轮警告）
    run_until_done(fake_graph_28_turns, state, max_turns=30)
    warnings = mock_logger.get_emitted("la.runtime.main_loop.near_limit")
    assert len(warnings) >= 2  # Turn 27, 28
```

### Integration Tests

```python
def test_run_until_done_real_graph_fake_model(real_graph_with_fake_model):
    """真实 LangGraph + FakeListChatModel（3 轮收敛）"""
    fake_model_responses = [
        AIMessage(content="Step 1", tool_calls=[{"name": "echo", "args": {"text": "a"}}]),
        AIMessage(content="Step 2", tool_calls=[{"name": "echo", "args": {"text": "b"}}]),
        AIMessage(content="Done", tool_calls=[])
    ]
    # 配置 FakeListChatModel 返回上述响应
    state = {"messages": [HumanMessage(content="Test")]}
    result = run_until_done(real_graph_with_fake_model, state, max_turns=10)
    assert len(result["messages"]) == 7  # Human + (AI + Tool) × 2 + final AI
```

---

## Performance Characteristics

### Time Complexity

- **Best Case**: O(1 turn) - 任务简单，模型直接给出答案（无工具调用）
- **Average Case**: O(3-5 turns) - 典型任务需要几轮工具调用
- **Worst Case**: O(max_turns) - 任务复杂或模型未收敛

### Space Complexity

- **Memory**: O(turn_count × messages_per_turn)
  - 每轮追加 1-3 条 message（AI + Tool(s)）
  - 30 轮最多 ~90 条 message，~100KB 内存
- **Disk** (checkpointer): O(turn_count × state_size)
  - 每轮 checkpoint 写入 ~10KB
  - 30 轮 ~300KB checkpoint 文件

### Latency

| Scenario | Turns | Local vLLM | OpenAI API |
|----------|-------|------------|------------|
| Simple question | 1 | 1-3s | 2-5s |
| Tool-assisted task | 3-5 | 3-15s | 6-25s |
| Complex multi-step | 10-20 | 10-60s | 20-100s |
| Max turns (30) | 30 | 30-90s | 60-150s |

---

## Changelog

### v1.0.0 (2026-09-20)
- Initial API contract
- Near-limit warning at 90% threshold (clarification Q2)
- Error recording without early termination (clarification Q1)
- Both invoke + stream modes supported (clarification Q3)
