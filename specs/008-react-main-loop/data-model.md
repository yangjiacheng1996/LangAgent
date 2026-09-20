# Phase 1: Data Model

**Feature**: ReAct Main Loop Runtime Dispatcher (F08)  
**Date**: 2026-09-20  
**Status**: Completed

---

## Overview

This document defines the data structures used by F08 main_loop dispatcher. All schemas align with `module_schemas.md` from top-level design.

---

## 1. AgentState (TypedDict)

**Purpose**: Authoritative state container for LangGraph execution with 5 annotated fields.

**Location**: `langagent/runtime/agent_state.py`

**Schema Version**: v0.1.0

### Fields

```python
from typing import Annotated, Any, TypedDict
from langagent.primitives.langchain_types import BaseMessage, add_messages
from langagent.primitives.state_reducers import (
    replace_with_merge, merge_dict, overwrite_or_merge
)

class AgentState(TypedDict, total=False):
    """LangAgent 主图 State；与 LangGraph 编译态直接对接。
    
    所有字段可选（total=False），初始化时可部分提供。
    Reducer 函数从 primitives.state_reducers 导入（F08 不定义 reducer）。
    """
    
    messages: Annotated[list[BaseMessage], add_messages]
    """消息历史。Reducer: add_messages (LangGraph 内置，追加不覆盖)。"""
    
    todos: Annotated[list[dict[str, Any]], replace_with_merge]
    """任务列表。Reducer: replace_with_merge (每次更新提供完整列表)。"""
    
    files: Annotated[dict[str, dict[str, Any]], merge_dict]
    """文件状态字典 (path → metadata)。Reducer: merge_dict (按键合并)。"""
    
    context: Annotated[dict[str, Any], overwrite_or_merge]
    """上下文元数据 (user/channel/session)。Reducer: overwrite_or_merge (显式 mode 参数)。"""
    
    scratchpad: Annotated[dict[str, Any], replace_with_merge]
    """临时推理数据。Reducer: replace_with_merge (每次更新提供完整字典)。
    
    特殊键：
    - "errors": list[ErrorEntry] - 工具执行错误记录（结构见 ErrorEntry）
    """
```

### Relationships

- **Owned by**: F08 runtime layer (定义) + F01 primitives layer (提供 reducers)
- **Used by**: 
  - F01 `primitives_state_graph_builder.build()` - 构造 StateGraph 时使用此 TypedDict 作为 state schema
  - F08 `dispatch()` / `run_until_done()` - 输入/输出类型
  - F10 CLI runner - 初始化 state with HumanMessage
  - F11 eval runner - 初始化 state with eval task input

### Validation Rules

- **messages**: 非空时必须含至少 1 个 BaseMessage；LangGraph 自动验证
- **todos**: 如存在，每个 dict 必须含 `id` 和 `status` 键（业务规则，F08 不强制）
- **files**: 键为文件路径字符串；值为 dict 含 `content` / `metadata`
- **context**: 可含任意键；常见键 `user_id`, `channel`, `session_id`
- **scratchpad["errors"]**: 如存在，必须为 `list[ErrorEntry]`（见下文 ErrorEntry 定义）

### State Transitions

AgentState 在 dispatch loop 中按以下顺序更新：

1. **Initial**: 调用者提供 `{"messages": [HumanMessage(...)]}`
2. **After model_call**: `messages` 追加 AIMessage（含 tool_calls 或 final answer）
3. **After tools_execute**: `messages` 追加 ToolMessage(s)；如工具失败，`scratchpad["errors"]` 追加 ErrorEntry
4. **Loop continues**: 回到步骤 2，直到 AIMessage 无 tool_calls（收敛）或 max_turns 超限

---

## 2. ErrorEntry (TypedDict)

**Purpose**: 结构化工具错误记录格式（存储在 `state.scratchpad["errors"]`）。

**Location**: `langagent/runtime/agent_state.py` (与 AgentState 同文件)

**Schema Version**: v0.1.0

### Fields

```python
from typing import TypedDict

class ErrorEntry(TypedDict):
    """单条工具执行错误记录。"""
    
    turn: int
    """错误发生的轮次编号 (1-indexed)。"""
    
    tool: str
    """工具名称（如 "echo", "search"）。"""
    
    error: str
    """错误消息，格式为 "ExceptionClass: message"。"""
    
    timestamp: str
    """ISO8601 UTC 时间戳（如 "2026-09-20T10:30:45.123456Z"）。"""
```

### Example

```python
{
    "turn": 3,
    "tool": "echo",
    "error": "TimeoutError: Operation timed out after 5s",
    "timestamp": "2026-09-20T10:30:45.123456Z"
}
```

### Validation Rules

- **turn**: 必须 > 0
- **tool**: 非空字符串
- **error**: 非空字符串，推荐格式 `ExceptionClass: message`
- **timestamp**: 必须符合 ISO8601 格式，以 "Z" 结尾（UTC）

### Lifecycle

- **Created**: 工具抛异常时，dispatch loop 捕获并构造 ErrorEntry
- **Appended**: 追加到 `state.scratchpad["errors"]` 列表（如列表不存在则创建）
- **Read**: F09 exit_cleanup 阶段可读取汇总错误；F11 eval runner 可检查错误率
- **Persisted**: 随 AgentState 一起由 LangGraph checkpointer 持久化

---

## 3. HitlInterruptedError (Exception)

**Purpose**: 主循环中断异常，携带当前 AgentState 供调用者恢复或检查。

**Location**: `langagent/runtime/main_loop_dispatcher.py`

**Schema Version**: v0.1.0

### Fields

```python
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class HitlInterruptedError(Exception):
    """主循环被用户或护栏中断时抛出。
    
    携带当前 AgentState 供调用者检查或恢复执行。
    """
    
    state: dict[str, Any]
    """中断时的 AgentState 快照（TypedDict 转为 dict）。"""
    
    reason: str
    """中断原因字符串：
    - "keyboard_interrupt": 用户按 Ctrl-C
    - "guardrail_block": F04 护栏拦截
    - "tool_approval_required": 工具需要审批（requires_approval=True）
    """
    
    message: str = "Agent execution interrupted"
    """人类可读错误消息。"""
    
    def __str__(self) -> str:
        return f"{self.message}: {self.reason}"
```

### Relationships

- **Raised by**: 
  - F08 `dispatch()` - 捕获 LangGraph GraphInterrupt/Interrupt 或 KeyboardInterrupt 后抛出
  - F08 `run_until_done()` - 同上
- **Caught by**:
  - F10 CLI runner - 捕获后打印提示，退出码 130
  - F11 eval runner - 捕获后记录 `TaskResult.guardrail_blocked=True`，继续 eval 循环

### Validation Rules

- **state**: 必须包含 AgentState 的当前快照（至少含 `messages` 键）
- **reason**: 必须为 3 个预定义值之一（枚举式字符串）
- **message**: 可选自定义，默认值足够

### State Transitions

```
dispatch() 执行中
    ↓
捕获 GraphInterrupt / KeyboardInterrupt
    ↓
构造 HitlInterruptedError(state=当前 state, reason=推断原因)
    ↓
抛出异常
    ↓
调用者 (F10/F11) 捕获
    ↓
访问 error.state 检查中断点
    ↓
决定：退出 (F10) 或记录+继续 (F11)
```

### Exit Code Mapping

| reason | F10 CLI exit code | F11 eval behavior |
|--------|------------------|-------------------|
| `keyboard_interrupt` | 130 (SIGINT) | 记录 interrupted=True，继续 |
| `guardrail_block` | 130 | 记录 guardrail_blocked=True，继续 |
| `tool_approval_required` | 130 | 记录 guardrail_blocked=True，继续 |

---

## 4. MetricsSnapshot (Integration Point)

**Purpose**: F08 更新指标快照，F02 持有数据结构。

**Owned by**: F02 cross_cutting_metrics_collector

**F08 Interaction**: F08 在每轮 dispatch 结束时调用：

```python
from langagent.cross_cutting.metrics_collector import increment_turn_count, record_latency

# 在 dispatch() 收尾处
increment_turn_count()
record_latency(turn_duration_ms)
```

**Schema** (参考 `module_schemas.md#schema-metrics-snapshot`):

```python
@dataclass(frozen=True)
class MetricsSnapshot:
    turn_count: int
    total_latency_ms: float
    error_rate: float  # errors / total_tool_calls
    # ... 其他 F02 定义的字段
```

**F08 不持有 MetricsSnapshot 实例**，仅通过 F02 提供的函数更新。

---

## 5. Event (Integration Point)

**Purpose**: F08 发布事件到 F03 event_bus，F03 持有数据结构。

**Owned by**: F03 protocol_event_bus

**F08 Interaction**: F08 在关键点调用：

```python
from langagent.protocol.event_bus import publish, Event

# tool_call 事件
publish(Event(
    type="tool_call",
    payload={
        "tool_id": tool_call.id,
        "tool_name": tool_call.name,
        "args": tool_call.args,
        "turn": current_turn
    }
))

# tool_result 事件
publish(Event(
    type="tool_result",
    payload={
        "tool_id": tool_message.tool_call_id,
        "result": tool_message.content,
        "turn": current_turn
    }
))

# model_response 事件
publish(Event(
    type="model_response",
    payload={
        "message": ai_message.to_dict(),
        "usage_metadata": ai_message.usage_metadata,
        "turn": current_turn
    }
))
```

**Schema** (参考 `module_schemas.md#schema-event`):

```python
class Event(BaseModel):
    type: str  # "tool_call" | "tool_result" | "model_response" | "guardrail_block"
    payload: dict[str, Any]
    timestamp: float = field(default_factory=time.time)
```

**F08 不构造 Event 类本身**（由 F03 提供），仅调用 `publish()`。

---

## 6. CompiledStateGraph (Input Dependency)

**Purpose**: LangGraph 编译后的图，F08 的输入参数。

**Owned by**: F01 primitives_state_graph_builder

**F08 Interaction**: F08 接收已编译的图，调用其方法：

```python
from langagent.primitives.langchain_types import CompiledStateGraph

def dispatch(graph: CompiledStateGraph, state: AgentState) -> AgentState:
    # 调用图的 invoke 或 stream 方法
    result = graph.invoke(state, config={"configurable": {"thread_id": "main"}})
    return result
```

**F08 不构造 CompiledStateGraph**，仅消费。图的结构（nodes/edges/middleware）由 F01 在 graph_compose 阶段完成。

---

## Entity Relationship Diagram

```
┌─────────────────────┐
│   AgentState        │ ◄──── F08 dispatch() 输入/输出
│  (TypedDict)        │
├─────────────────────┤
│ messages            │ ──┐
│ todos               │   │
│ files               │   │  所有字段使用 Annotated[type, reducer]
│ context             │   │  reducer 从 primitives.state_reducers 导入
│ scratchpad          │ ──┘
│   └─ "errors"       │ ───► list[ErrorEntry]
└─────────────────────┘
         │
         │ (序列化/反序列化)
         ▼
┌─────────────────────┐
│ LangGraph           │ ◄──── F01 构造
│ Checkpointer        │        F08 不直接调用
└─────────────────────┘

┌─────────────────────┐
│ HitlInterruptedError│ ◄──── F08 dispatch() 抛出
│  (Exception)        │
├─────────────────────┤
│ state: dict         │ ───► 保存中断时的 AgentState
│ reason: str         │ ───► 原因（keyboard/guardrail/approval）
│ message: str        │
└─────────────────────┘
         │
         │ (捕获)
         ▼
┌─────────────────────┐
│  F10 CLI runner     │ ───► 退出码 130
│       OR            │
│  F11 eval runner    │ ───► TaskResult.guardrail_blocked=True
└─────────────────────┘

┌─────────────────────┐
│  ErrorEntry         │ ◄──── 工具异常时创建
│  (TypedDict)        │
├─────────────────────┤
│ turn: int           │
│ tool: str           │
│ error: str          │
│ timestamp: str      │
└─────────────────────┘
         │
         │ (追加到)
         ▼
  state.scratchpad["errors"]
```

---

## Data Flow Summary

1. **输入**: F10/F11 构造初始 AgentState (含 HumanMessage) + F01 提供的 CompiledStateGraph
2. **执行**: F08 dispatch() 调用 graph.invoke(state) → LangGraph 执行 model_call → tools_execute 节点
3. **更新**: 每轮后 state 通过 reducer 更新 (messages 追加, scratchpad["errors"] 追加)
4. **发射**: F08 同时发布 Event (F03) 和 emit Log (F02)
5. **中断**: 如遇 GraphInterrupt/KeyboardInterrupt，F08 抛 HitlInterruptedError (携带 state)
6. **输出**: run_until_done() 返回最终 AgentState 或抛异常

---

## Validation Checklist

- [x] AgentState 5 字段全部定义，类型注解正确
- [x] Reducer 函数从 primitives.state_reducers 导入（F08 不定义）
- [x] ErrorEntry 4 字段符合 clarification 决策
- [x] HitlInterruptedError 携带 state + reason
- [x] MetricsSnapshot / Event / CompiledStateGraph 明确为外部依赖
- [x] ERD 图展示实体关系
- [x] 数据流总结涵盖输入→执行→输出→中断路径
