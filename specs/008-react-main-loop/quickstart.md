# Quickstart: Validation Guide

**Feature**: ReAct Main Loop Runtime Dispatcher (F08)  
**Date**: 2026-09-20  
**Purpose**: 提供可运行的验证场景，证明 F08 端到端工作正常

---

## Prerequisites

### 1. 依赖模块已实现

F08 依赖以下模块，必须先完成：

- ✅ **F01 primitives layer**
  - `primitives.langchain_types` (BaseMessage, add_messages, CompiledStateGraph re-exports)
  - `primitives.state_reducers` (replace_with_merge, merge_dict, overwrite_or_merge)
  - `primitives.state_graph_builder` (build() 返回 CompiledStateGraph)
  - `primitives.chat_model_factory` (create() 实例化 BaseChatModel)
  - `primitives.checkpoint_adapter` (create() 实例化 checkpointer)

- ✅ **F02 cross_cutting_logger**
  - `emit(tag, payload)` 函数
  - `ALLOWED_TAGS` 集合包含 ≥46 个 tag（含 F08 的 12 个 tag）

- ✅ **F03 protocol_event_bus**
  - `publish(event)` 函数
  - `Event` 类型（type + payload + timestamp）

- ✅ **F04 cross_cutting_guardrail_middleware**
  - `build_middleware(policy)` 构造 guardrail middleware
  - 拦截时抛出 LangGraph `GraphInterrupt` 异常

- ✅ **F06 cross_cutting_stage_guard**
  - `@stage_guard_decorator('main_loop')` 装饰器
  - `STAGE_BLACKLIST_TABLE['main_loop']` 黑名单定义

### 2. 开发环境设置

```bash
# 1. 克隆仓库
git clone <repo-url>
cd LangAgent

# 2. 切换到 feature 分支
git checkout 008-react-main-loop

# 3. 安装依赖
pip install -e ".[dev]"  # 包含 pytest, mypy, langchain, langgraph

# 4. 验证依赖
python -c "from langchain_core.language_models.fake import FakeListChatModel; print('OK')"
python -c "from langgraph.graph import StateGraph; print('OK')"
```

### 3. 测试夹具

F08 测试需要 `FakeListChatModel` 夹具，位于：

```
tests/fixtures/sample_agent_with_fake_model/
├── instructions.md          # 最小系统提示词
├── tools/
│   └── echo.py             # 简单 echo 工具
└── fake_model_config.py    # FakeListChatModel 配置
```

---

## Validation Scenarios

### Scenario 1: 单轮执行（无工具调用）

**Goal**: 验证 `dispatch()` 可执行单轮 ReAct，模型直接返回答案（无 tool_calls）

**Setup**:
```python
# tests/runtime/test_main_loop_dispatcher.py
from langchain_core.language_models.fake import FakeListChatModel
from langchain_core.messages import HumanMessage, AIMessage
from langagent.runtime.main_loop_dispatcher import dispatch
from langagent.runtime.agent_state import AgentState

def test_dispatch_single_turn_no_tools(compiled_graph_with_fake_model):
    """dispatch 返回含 AIMessage 的 state（无工具调用）"""
    # 准备 fake model（直接返回答案）
    fake_model = FakeListChatModel(responses=[
        AIMessage(content="The answer is 42.", tool_calls=[])
    ])
    graph = build_graph_with_model(fake_model)  # F01 state_graph_builder.build()
    
    # 初始 state
    state: AgentState = {
        "messages": [HumanMessage(content="What is the answer?")]
    }
    
    # 执行
    result = dispatch(graph, state)
    
    # 验证
    assert len(result["messages"]) == 2  # HumanMessage + AIMessage
    assert isinstance(result["messages"][-1], AIMessage)
    assert "42" in result["messages"][-1].content
```

**Run**:
```bash
pytest tests/runtime/test_main_loop_dispatcher.py::test_dispatch_single_turn_no_tools -v
```

**Expected Output**:
```
PASSED tests/runtime/test_main_loop_dispatcher.py::test_dispatch_single_turn_no_tools
```

---

### Scenario 2: 单轮执行（含工具调用）

**Goal**: 验证 `dispatch()` 可执行工具调用流程（模型 → tool_call → tool_execute → ToolMessage）

**Setup**:
```python
def test_dispatch_with_tool_call(compiled_graph_with_echo_tool):
    """dispatch 执行工具调用并返回 ToolMessage"""
    # 准备 fake model（返回含 tool_call 的 AIMessage）
    fake_model = FakeListChatModel(responses=[
        AIMessage(
            content="Let me echo that.",
            tool_calls=[{
                "id": "call_1",
                "name": "echo",
                "args": {"text": "hello"}
            }]
        )
    ])
    graph = build_graph_with_model_and_tool(fake_model, echo_tool)
    
    # 初始 state
    state: AgentState = {
        "messages": [HumanMessage(content="Echo 'hello'")]
    }
    
    # 执行
    result = dispatch(graph, state)
    
    # 验证
    assert len(result["messages"]) == 3  # HumanMessage + AIMessage + ToolMessage
    assert result["messages"][-1].content == "hello"  # echo 工具返回
```

**Run**:
```bash
pytest tests/runtime/test_main_loop_dispatcher.py::test_dispatch_with_tool_call -v
```

---

### Scenario 3: 多轮收敛

**Goal**: 验证 `run_until_done()` 可执行完整 ReAct 循环并在模型收敛时终止

**Setup**:
```python
def test_run_until_done_converges(compiled_graph_3_turns):
    """run_until_done 执行 3 轮后收敛"""
    # 准备 fake model（3 轮：2 轮工具调用 + 1 轮最终答案）
    fake_model = FakeListChatModel(responses=[
        AIMessage(content="Step 1", tool_calls=[{"name": "echo", "args": {"text": "a"}}]),
        AIMessage(content="Step 2", tool_calls=[{"name": "echo", "args": {"text": "b"}}]),
        AIMessage(content="Final answer: done", tool_calls=[])
    ])
    graph = build_graph_with_model_and_tool(fake_model, echo_tool)
    
    # 初始 state
    state: AgentState = {
        "messages": [HumanMessage(content="Multi-step task")]
    }
    
    # 执行
    result = run_until_done(graph, state, max_turns=10)
    
    # 验证
    assert len(result["messages"]) == 7  # Human + (AI + Tool) × 2 + final AI
    assert "done" in result["messages"][-1].content
```

**Run**:
```bash
pytest tests/runtime/test_main_loop_dispatcher.py::test_run_until_done_converges -v
```

---

### Scenario 4: Max Turns 超限

**Goal**: 验证 `run_until_done()` 在达到 max_turns 时抛出 `TokenLimitExceededError`

**Setup**:
```python
def test_run_until_done_max_turns_exceeded():
    """run_until_done 达到 max_turns 抛异常"""
    # 准备 fake model（永远返回 tool_calls，永不收敛）
    fake_model = FakeListChatModel(responses=[
        AIMessage(content="Loop", tool_calls=[{"name": "echo", "args": {"text": "x"}}])
    ] * 50)  # 50 个相同响应
    graph = build_graph_with_model_and_tool(fake_model, echo_tool)
    
    # 初始 state
    state: AgentState = {"messages": [HumanMessage(content="Infinite task")]}
    
    # 执行
    with pytest.raises(TokenLimitExceededError) as exc_info:
        run_until_done(graph, state, max_turns=10)
    
    # 验证
    assert exc_info.value.turn_count == 10
    assert exc_info.value.max_turns == 10
```

**Run**:
```bash
pytest tests/runtime/test_main_loop_dispatcher.py::test_run_until_done_max_turns_exceeded -v
```

---

### Scenario 5: 工具错误记录

**Goal**: 验证工具执行失败时，错误记录到 `state.scratchpad["errors"]`

**Setup**:
```python
def test_dispatch_tool_error_recorded():
    """工具抛异常时记录到 scratchpad["errors"]"""
    # 准备会失败的工具
    @tool
    def failing_tool(x: int) -> int:
        """Always fails."""
        raise TimeoutError("Operation timed out after 5s")
    
    fake_model = FakeListChatModel(responses=[
        AIMessage(content="Try", tool_calls=[{"name": "failing_tool", "args": {"x": 1}}]),
        AIMessage(content="Give up", tool_calls=[])
    ])
    graph = build_graph_with_model_and_tool(fake_model, failing_tool)
    
    # 初始 state
    state: AgentState = {"messages": [HumanMessage(content="Try failing tool")]}
    
    # 执行
    result = run_until_done(graph, state, max_turns=5)
    
    # 验证
    assert "errors" in result["scratchpad"]
    assert len(result["scratchpad"]["errors"]) == 1
    error_entry = result["scratchpad"]["errors"][0]
    assert error_entry["tool"] == "failing_tool"
    assert "TimeoutError" in error_entry["error"]
    assert "turn" in error_entry
    assert "timestamp" in error_entry
```

**Run**:
```bash
pytest tests/runtime/test_main_loop_dispatcher.py::test_dispatch_tool_error_recorded -v
```

---

### Scenario 6: Guardrail 中断

**Goal**: 验证 F04 guardrail 拦截时，dispatch 抛出 `HitlInterruptedError`

**Setup**:
```python
def test_dispatch_guardrail_interrupt():
    """guardrail 拦截时抛 HitlInterruptedError"""
    # 准备工具（requires_approval=True）
    @tool
    def sensitive_tool(secret: str) -> str:
        """Requires approval."""
        return f"Processed: {secret}"
    
    fake_model = FakeListChatModel(responses=[
        AIMessage(content="Call", tool_calls=[{"name": "sensitive_tool", "args": {"secret": "api_key"}}])
    ])
    
    # F01 在 build() 时已注入 F04 guardrail middleware
    # ToolSpec.requires_approval=True → guardrail 拦截 → 抛 GraphInterrupt
    graph = build_graph_with_guardrail(fake_model, sensitive_tool, requires_approval=True)
    
    # 初始 state
    state: AgentState = {"messages": [HumanMessage(content="Call sensitive tool")]}
    
    # 执行
    with pytest.raises(HitlInterruptedError) as exc_info:
        dispatch(graph, state)
    
    # 验证
    assert exc_info.value.reason in ("guardrail_block", "tool_approval_required")
    assert "messages" in exc_info.value.state  # 携带当前 state
```

**Run**:
```bash
pytest tests/runtime/test_main_loop_dispatcher.py::test_dispatch_guardrail_interrupt -v
```

---

### Scenario 7: Event 和 Log 双通道发射

**Goal**: 验证每个 tool_call 同时发布 Event（F03 event_bus）和 Log（F02 logger）

**Setup**:
```python
def test_dispatch_dual_channel_emission(compiled_graph, mock_event_bus, mock_logger):
    """dispatch 同时发布 Event 和 Log"""
    fake_model = FakeListChatModel(responses=[
        AIMessage(content="Call", tool_calls=[{"name": "echo", "args": {"text": "test"}}]),
        AIMessage(content="Done", tool_calls=[])
    ])
    graph = build_graph_with_model_and_tool(fake_model, echo_tool)
    
    # Mock event_bus 和 logger
    with patch('langagent.protocol.event_bus.publish') as mock_publish, \
         patch('langagent.cross_cutting.logger.emit') as mock_emit:
        
        state: AgentState = {"messages": [HumanMessage(content="Test")]}
        result = run_until_done(graph, state, max_turns=5)
        
        # 验证 Event 发布
        tool_call_events = [call for call in mock_publish.call_args_list 
                           if call[0][0].type == "tool_call"]
        assert len(tool_call_events) == 1
        
        # 验证 Log 发射
        tool_call_logs = [call for call in mock_emit.call_args_list 
                         if call[0][0] == "la.lifecycle.run.tool_call"]
        assert len(tool_call_logs) == 1
```

**Run**:
```bash
pytest tests/runtime/test_main_loop_dispatcher.py::test_dispatch_dual_channel_emission -v
```

---

### Scenario 8: Stage Guard 边界执法

**Goal**: 验证 main_loop 阶段尝试禁止操作时抛出 `StageCapabilityViolationError`

**Setup**:
```python
def test_dispatch_stage_violation_raises():
    """dispatch 内尝试读 .env 触发 StageCapabilityViolationError"""
    
    # 构造恶意节点（尝试读 .env）
    def malicious_node(state):
        # 这会触发 audit_event blacklist
        with open(".env", "r") as f:
            content = f.read()
        return state
    
    # 构造包含恶意节点的图
    graph = build_graph_with_malicious_node(malicious_node)
    
    state: AgentState = {"messages": [HumanMessage(content="Test")]}
    
    # 执行
    with pytest.raises(StageCapabilityViolationError):
        dispatch(graph, state)
```

**Run**:
```bash
pytest tests/runtime/test_main_loop_dispatcher.py::test_dispatch_stage_violation_raises -v
```

---

## Full Test Suite Run

运行完整 F08 测试套件（≥28 个测试用例）：

```bash
# 运行所有 F08 测试
pytest tests/runtime/test_main_loop_dispatcher.py -v

# 运行 reducer 测试
pytest tests/runtime/test_agent_state_reducers.py -v

# 运行覆盖率检查
pytest tests/runtime/ --cov=langagent.runtime.main_loop_dispatcher --cov-report=term-missing

# 类型检查
mypy --strict langagent/runtime/main_loop_dispatcher.py
mypy --strict langagent/runtime/agent_state.py
```

**Expected Output**:
```
tests/runtime/test_main_loop_dispatcher.py::test_dispatch_single_turn_no_tools PASSED
tests/runtime/test_main_loop_dispatcher.py::test_dispatch_with_tool_call PASSED
tests/runtime/test_main_loop_dispatcher.py::test_run_until_done_converges PASSED
tests/runtime/test_main_loop_dispatcher.py::test_run_until_done_max_turns_exceeded PASSED
... (总计 28+ 个测试)

---------- coverage: platform linux, python 3.11.x -----------
Name                                                Stmts   Miss  Cover   Missing
---------------------------------------------------------------------------------
langagent/runtime/main_loop_dispatcher.py             340      0   100%
langagent/runtime/agent_state.py                       25      0   100%
---------------------------------------------------------------------------------
TOTAL                                                 365      0   100%
```

---

## Integration with CLI (F10)

验证 F08 与 F10 CLI runner 的集成：

```bash
# 1. 创建测试智能体
langagent init test-agent
cd test-agent

# 2. 配置 .env（使用本地 vLLM 或 OpenAI API）
cat > .env <<EOF
MODEL_PROVIDER=openai-compatible
MODEL_BASE_URL=http://localhost:8000/v1
MODEL_NAME=Qwen3.8-27B
EOF

# 3. 运行智能体（F10 调用 F08 run_until_done）
langagent run

# 4. 输入测试任务
> Echo "Hello from F08"

# 5. 验证输出
Expected: Agent 执行 echo 工具，返回 "Hello from F08"，退出码 0
```

---

## Integration with Eval Runner (F11)

验证 F08 与 F11 eval runner 的集成：

```bash
# 1. 创建评测任务
cat > evals/test_f08.yaml <<EOF
task_id: test_f08
input: "What is 2 + 2?"
expected_output: "4"
grader: exact_match
timeout: 30
EOF

# 2. 运行评测（F11 调用 F08 run_until_done）
langagent eval

# 3. 验证输出
Expected:
  - Task: test_f08 [PASS]
  - Exit code: 0
```

---

## Troubleshooting

### Issue 1: `ImportError: cannot import name 'CompiledStateGraph'`

**Cause**: F01 primitives_langchain_types 未实现 re-export

**Fix**: 
```python
# langagent/primitives/langchain_types.py
from langgraph.graph import CompiledStateGraph
__all__ = ["CompiledStateGraph", ...]
```

### Issue 2: `StageCapabilityViolationError` 在正常 dispatch

**Cause**: @stage_guard_decorator 黑名单配置错误

**Fix**: 检查 F06 `STAGE_BLACKLIST_TABLE['main_loop']` 是否正确

### Issue 3: 测试中 Event 未发布

**Cause**: F03 event_bus 未初始化或 mock 未设置

**Fix**: 在测试 setup 中初始化 event_bus 或使用 mock

---

## Success Criteria Validation

运行完整测试套件后，验证以下成功标准（对应 spec.md SC-001 到 SC-010）：

- [x] **SC-001**: 3 轮任务在 <5s 完成（本地 vLLM）
- [x] **SC-002**: 100 轮压力测试无内存泄漏
- [x] **SC-003**: 13 个 log tag 全部出现
- [x] **SC-004**: 工具错误不崩溃循环
- [x] **SC-005**: Reducer 测试通过 10+ 轮
- [x] **SC-006**: KeyboardInterrupt 返回 130
- [x] **SC-007**: 真实 LangGraph 集成测试通过
- [x] **SC-008**: Stage violation 在 <1ms 检测
- [x] **SC-009**: Event 订阅者收到所有事件
- [x] **SC-010**: build_doctor_probes 返回可用 probe

---

## Next Steps

F08 验证通过后：

1. **集成到 F10 CLI**: 在 `cli/runner.py` 中调用 `run_until_done()`
2. **集成到 F11 eval**: 在 `eval/runner.py` 中调用 `run_until_done()`
3. **添加文档**: 更新 `docs/architecture.md` 描述 main_loop 阶段
4. **性能基准**: 运行 benchmark 套件，记录 latency/memory baseline

---

## References

- [dispatch.md](./contracts/dispatch.md) - dispatch() API 契约
- [run_until_done.md](./contracts/run_until_done.md) - run_until_done() API 契约
- [build_doctor_probes.md](./contracts/build_doctor_probes.md) - build_doctor_probes() API 契约
- [data-model.md](./data-model.md) - AgentState / ErrorEntry / HitlInterruptedError 数据模型
- [research.md](./research.md) - 技术决策和研究发现
