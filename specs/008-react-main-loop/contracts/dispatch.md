# API Contract: dispatch()

**Module**: `langagent.runtime.main_loop_dispatcher`  
**Function**: `dispatch`  
**Version**: v1.0.0  
**Date**: 2026-09-20

---

## Signature

```python
@stage_guard_decorator('main_loop')
def dispatch(
    graph: CompiledStateGraph,
    state: AgentState
) -> AgentState:
    """执行单轮 ReAct 循环（推理 → 工具 → 观察）。
    
    驱动 LangGraph 编译后的图执行一次迭代，包括：
    1. 调用 model_call 节点（生成 AIMessage）
    2. 如 AIMessage 含 tool_calls，执行 tools_execute 节点
    3. 返回更新后的 AgentState
    
    如遇 LangGraph Interrupt（guardrail 拦截或工具需审批），
    抛出 HitlInterruptedError 异常并携带当前状态。
    
    Args:
        graph: F01 编译的 CompiledStateGraph（含 model_call/tools_execute 节点）
        state: 当前 AgentState（必须含 messages 字段，其他字段可选）
    
    Returns:
        更新后的 AgentState（messages 已追加 AIMessage/ToolMessage）
    
    Raises:
        HitlInterruptedError: 
            - reason="keyboard_interrupt": 用户按 Ctrl-C
            - reason="guardrail_block": F04 guardrail 拦截
            - reason="tool_approval_required": 工具需审批
            异常携带 error.state 属性（当前 AgentState 快照）
        
        StageCapabilityViolationError: 
            main_loop 阶段尝试禁止操作（如读 .env、实例化模型）
        
        TokenLimitExceededError: 
            不由 dispatch 抛出（由 run_until_done 检查 turn_count）
    
    Side Effects:
        - 通过 protocol_event_bus 发布 Event:
          * tool_call (每个工具调用前)
          * tool_result (每个工具执行后)
          * model_response (模型回复后)
        
        - 通过 cross_cutting_logger 发射 Log:
          * la.lifecycle.run.turn (轮次开始)
          * la.runtime.main_loop.turn.start (轮次开始，运行时视角)
          * la.lifecycle.run.tool_call (每个工具调用)
          * la.runtime.main_loop.tool_call (每个工具调用，运行时视角)
          * la.lifecycle.run.tool_result (每个工具结果)
          * la.runtime.main_loop.tool_result (每个工具结果，运行时视角)
          * la.lifecycle.run.model_response (模型回复)
          * la.runtime.main_loop.model_call (模型调用，运行时视角)
          * la.runtime.main_loop.turn.end (轮次结束)
        
        - 调用 F02 metrics_collector:
          * increment_turn_count()
          * record_latency(duration_ms)
        
        - 如工具抛异常，追加到 state.scratchpad["errors"]:
          * ErrorEntry(turn=N, tool="...", error="...", timestamp="...")
    
    Thread Safety:
        非线程安全。调用者必须保证串行调用（单线程或外部锁）。
    
    Performance:
        - 同步阻塞调用（等待 LangGraph 图执行完成）
        - 延迟取决于模型响应时间 + 工具执行时间
        - 典型单轮：本地 vLLM 1-3 秒，OpenAI API 2-5 秒
    """
```

---

## Parameters

### `graph: CompiledStateGraph`

- **Type**: `langagent.primitives.langchain_types.CompiledStateGraph` (LangGraph re-export)
- **Required**: Yes
- **Constraints**:
  - 必须由 F01 `primitives_state_graph_builder.build()` 编译
  - 必须包含 `model_call` 和 `tools_execute` 节点
  - 必须配置 checkpointer（如 MemorySaver 或 SqliteSaver）
  - 中间件（F04 guardrail + 用户中间件）已在 F01 graph_compose 阶段注入
- **Validation**: dispatch 不验证图结构（信任 F01 输出）

### `state: AgentState`

- **Type**: `langagent.runtime.agent_state.AgentState` (TypedDict)
- **Required**: Yes
- **Constraints**:
  - `messages` 字段必须存在（至少含 1 个 BaseMessage，通常为 HumanMessage）
  - `todos`, `files`, `context`, `scratchpad` 字段可选（不存在时自动初始化为空）
  - 如 `scratchpad["errors"]` 存在，必须为 `list[ErrorEntry]`
- **Validation**: dispatch 不验证 state 内容（LangGraph 图节点负责）

---

## Return Value

### `AgentState`

- **Type**: `langagent.runtime.agent_state.AgentState`
- **Guarantees**:
  - `messages` 字段已追加至少 1 个 AIMessage
  - 如 AIMessage 含 tool_calls，`messages` 还追加了 ToolMessage(s)
  - 如工具执行失败，`scratchpad["errors"]` 追加了 ErrorEntry(s)
  - 其他字段（todos/files/context）可能被图节点更新（取决于图逻辑）
- **State Consistency**: 返回的 state 已通过所有 reducer 合并（add_messages, replace_with_merge, merge_dict, overwrite_or_merge）

---

## Exceptions

### `HitlInterruptedError`

**When**: LangGraph 抛出 `GraphInterrupt` 或 `Interrupt`，或捕获 `KeyboardInterrupt`

**Attributes**:
- `error.state: dict[str, Any]` - 中断时的 AgentState 快照
- `error.reason: str` - 中断原因（"keyboard_interrupt" | "guardrail_block" | "tool_approval_required"）
- `error.message: str` - 人类可读消息（默认 "Agent execution interrupted"）

**Caller Responsibility**:
- F10 CLI: 捕获后打印提示，退出码 130
- F11 eval: 捕获后记录 `TaskResult.guardrail_blocked=True`，继续下一任务

**Example**:
```python
try:
    updated_state = dispatch(graph, state)
except HitlInterruptedError as e:
    print(f"Interrupted: {e.reason}")
    # 访问中断时的状态
    print(f"Messages at interrupt: {len(e.state['messages'])}")
    # F10: sys.exit(130)
    # F11: task_result.guardrail_blocked = True
```

### `StageCapabilityViolationError`

**When**: main_loop 阶段尝试执行黑名单操作（monkeypatch 或 audit_event 拦截）

**Blacklist** (from F06 cross_cutting_stage_guard):
- Monkeypatch: `RuntimeDirLoader.load`, `RuntimeConfigResolver.resolve`, `BaseChatModel.__init__`, `chat_model_factory.create`
- Audit event: `open` (拦截 `open(.env)`)

**Caller Responsibility**: 记录错误，退出码 1

**Example**:
```python
# 这段代码会触发 StageCapabilityViolationError（在 @stage_guard_decorator 保护下）
from langagent.runtime.config_resolver import RuntimeConfigResolver
config = RuntimeConfigResolver.resolve(...)  # ❌ 禁止：main_loop 不得重新解析 config
```

---

## Side Effects

### Event Bus Emission

**Published Events**:

1. **tool_call** (每个 tool_call 执行前)
   ```python
   Event(
       type="tool_call",
       payload={
           "tool_id": str,
           "tool_name": str,
           "args": dict[str, Any],
           "turn": int
       }
   )
   ```

2. **tool_result** (每个 ToolMessage 生成后)
   ```python
   Event(
       type="tool_result",
       payload={
           "tool_id": str,
           "result": str,
           "turn": int
       }
   )
   ```

3. **model_response** (AIMessage 生成后)
   ```python
   Event(
       type="model_response",
       payload={
           "message": dict,  # AIMessage.to_dict()
           "usage_metadata": dict | None,
           "turn": int
       }
   )
   ```

**Subscribers** (由 F02/F04 注册):
- `cross_cutting_metrics_collector.on_tool_call()` - 记录延迟
- `cross_cutting_audit_recorder.on_guardrail_block()` - 写审计日志

### Structured Logging

**Emitted Tags** (9 个，dispatch 单轮范围):

| Tag | Timing | Payload Keys |
|-----|--------|--------------|
| `la.lifecycle.run.turn` | dispatch 入口 | `turn`, `state_snapshot` |
| `la.runtime.main_loop.turn.start` | dispatch 入口 | `turn` |
| `la.lifecycle.run.tool_call` | 每个 tool_call 前 | `tool_id`, `tool_name`, `args` |
| `la.runtime.main_loop.tool_call` | 每个 tool_call 前 | `tool_id` |
| `la.lifecycle.run.tool_result` | 每个 ToolMessage 后 | `tool_id`, `result` |
| `la.runtime.main_loop.tool_result` | 每个 ToolMessage 后 | `tool_id` |
| `la.lifecycle.run.model_response` | AIMessage 后 | `usage_metadata` |
| `la.runtime.main_loop.model_call` | model_call 节点后 | `model_name` |
| `la.runtime.main_loop.turn.end` | dispatch 收尾 | `turn`, `duration_ms` |

**Not Emitted by dispatch** (但 dispatch 在其范围内观测到):
- `la.cross_cutting.guardrail.block` - F04 直接发射（当 guardrail 拦截时）

### Metrics Updates

```python
from langagent.cross_cutting.metrics_collector import increment_turn_count, record_latency

# dispatch 收尾处
increment_turn_count()
record_latency(turn_duration_ms)
```

**Metrics Impact**:
- `MetricsSnapshot.turn_count` +1
- `MetricsSnapshot.total_latency_ms` += turn_duration_ms
- 如工具失败，`MetricsSnapshot.error_rate` 更新

---

## Examples

### Example 1: 正常单轮（无工具调用）

```python
from langagent.primitives.langchain_types import HumanMessage
from langagent.runtime.main_loop_dispatcher import dispatch

# 初始 state
state = {
    "messages": [HumanMessage(content="Hello, what is 2+2?")]
}

# 调用 dispatch
updated_state = dispatch(graph, state)

# 结果
assert len(updated_state["messages"]) == 2  # HumanMessage + AIMessage
assert "4" in updated_state["messages"][-1].content
```

### Example 2: 单轮含工具调用

```python
state = {
    "messages": [HumanMessage(content="Echo 'hello'")]
}

updated_state = dispatch(graph, state)

# 结果
assert len(updated_state["messages"]) == 3  # HumanMessage + AIMessage(tool_calls) + ToolMessage
assert updated_state["messages"][-1].content == "hello"
```

### Example 3: 工具执行失败

```python
state = {
    "messages": [HumanMessage(content="Call failing tool")]
}

updated_state = dispatch(graph, state)

# 结果：工具失败记录在 scratchpad
assert "errors" in updated_state["scratchpad"]
assert len(updated_state["scratchpad"]["errors"]) == 1
error_entry = updated_state["scratchpad"]["errors"][0]
assert error_entry["tool"] == "failing_tool"
assert "TimeoutError" in error_entry["error"]
```

### Example 4: Guardrail 中断

```python
state = {
    "messages": [HumanMessage(content="Call sensitive tool")]
}

try:
    dispatch(graph, state)
except HitlInterruptedError as e:
    assert e.reason == "guardrail_block"
    # 中断时的状态包含 HumanMessage + 部分处理的 AIMessage
    assert len(e.state["messages"]) >= 1
```

---

## Testing Strategies

### Unit Tests

```python
def test_dispatch_single_turn_no_tools(fake_graph, fake_model):
    """dispatch 返回含 AIMessage 的 state（无工具调用）"""
    state = {"messages": [HumanMessage(content="Hi")]}
    result = dispatch(fake_graph, state)
    assert len(result["messages"]) == 2
    assert isinstance(result["messages"][-1], AIMessage)

def test_dispatch_emits_events(fake_graph, mock_event_bus):
    """dispatch 发布 tool_call/tool_result/model_response 事件"""
    state = {"messages": [HumanMessage(content="Echo test")]}
    dispatch(fake_graph, state)
    assert mock_event_bus.published_count("tool_call") == 1
    assert mock_event_bus.published_count("model_response") == 1

def test_dispatch_stage_violation_raises(fake_graph):
    """dispatch 内尝试读 .env 触发 StageCapabilityViolationError"""
    with pytest.raises(StageCapabilityViolationError):
        # 模拟在 dispatch 内部调用禁止操作
        dispatch_with_env_read(fake_graph, state)
```

### Integration Tests

```python
def test_dispatch_real_graph_fake_model(real_graph_with_fake_model):
    """使用真实 LangGraph + FakeListChatModel"""
    state = {"messages": [HumanMessage(content="Test")]}
    result = dispatch(real_graph_with_fake_model, state)
    # 真实图执行，无 mock
    assert "messages" in result
```

---

## Performance Characteristics

- **Latency**: O(model_latency + tool_latency)
  - 本地 vLLM: 1-3s per turn (Qwen3.8-27B)
  - OpenAI API: 2-5s per turn (gpt-4o)
- **Memory**: O(state_size)
  - AgentState 通常 <10KB (messages + scratchpad)
  - Checkpointer 持久化不计入内存
- **Complexity**: O(num_tool_calls)
  - 单轮可能有 0-N 个 tool_call（N 通常 ≤ 5）

---

## Changelog

### v1.0.0 (2026-09-20)
- Initial API contract
- Dual-mode support (invoke + stream) planned for implementation
- Exception handling with HitlInterruptedError
- Stage guard enforcement via @decorator
