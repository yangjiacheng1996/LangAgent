# F08 — ReAct 主循环（main_loop 阶段）

> **Feature ID**: F08
> **批次**: 第 7 批（运行时 2.a）
> **依赖**: F01（primitives_state_graph_builder 提供 CompiledStateGraph + primitives_langchain_types re-export + **v0.4.0 M-4 方案 C 修复后** primitives_state_reducers 提供 **3 个唯一 reducer 函数覆盖 4 个自定义字段**（**review.md v1.0.0 P1-4 修复**：reducer 函数实现位于 primitives_state_reducers；`replace_with_merge` 被 `todos` 与 `scratchpad` 共用，`merge_dict` 仅 `files`，`overwrite_or_merge` 仅 `context`；AgentState `messages` 字段的 `add_messages` reducer 由 LangGraph 内置提供，不在本模块））/ F02（logger + metrics）/ F03（event bus 发 `tool_call` / `tool_result` / `model_response`）/ F04（guardrail middleware 注入图）
> **被依赖**: F10（CLI run 调 dispatch）/ F11（eval 跑 dispatch）/ F09（exit_cleanup 接 state）
> **状态**: 待启动 speckit.specify（review.md v1.1.0 修复后；本 feature prompt 已应用 v0.4.0 修复：M-4 方案 C reducer 从 primitives 层 import；M-NEW-3 log tag rename `la.cli.run.*` → `la.lifecycle.run.*`；v1.1.0 修复：P1-4 + P2-6 §3.5.2 guardrail_block 转发语义统一，明确 F08 不重发；P1-7 §三.4 main_loop 阶段黑名单引用 F06 §3.4）

---

## 一、Feature 概述

实现 runtime 层阶段 5 `main_loop`：驱动 LangGraph `CompiledStateGraph` 跑 ReAct 主循环（推理→工具→观察），直至任务完成 / 用户中断 / 终止条件触发。

这是 LangAgent 的核心运行时。F08 不构造图（F01 负责），F08 只"驱动"已编译的图。

## 二、必读顶层设计 artefact（宪法第 XV 条）

1. `harness/top_level_design/workflow.md#stage-main_loop` —— 阶段 5 输入 / 输出 / 失败模式 / 退出码。
2. `harness/top_level_design/architecture_modules.md#mod-runtime-main-loop-dispatcher` —— 模块职责、API、依赖矩阵。
3. `harness/top_level_design/module_schemas.md#schema-agent-state` —— AgentState 5 字段 reducer。
4. 宪法第 VI 条（Agent Loop 与 State）—— ReAct 节点 + 自研 State + 5 字段 reducer + Edge 来源。

**本 feature 重点对齐的宪法条款**（**review.md v2.2.0 修复 P2-9**）：
- **第 VI 条** Agent Loop 与 State：F08 是该条款的核心实施方（main_loop dispatcher 通过 primitives.langchain_types re-export LangChain 类型；reducer 从 primitives.state_reducers import）；
- **第 VIII 条** TDD 刚性：先 Red 后 Green 再 Refactor；
- **第 IX 条** 质量诊断：F08 通过 Event 总线（tool_call / model_response / guardrail_block）与 F02 metrics_collector / F04 audit_recorder / F04 guardrail_middleware 联动。

## 三、本 feature 覆盖的范围

### 3.1 模块

| module_id | 关键 API | 行数估算 |
|---|---|---|
| `runtime_main_loop_dispatcher` | `dispatch(graph: CompiledStateGraph, state: AgentState) -> AgentState` + `run_until_done(graph: CompiledStateGraph, state: AgentState, max_turns: int = 30) -> AgentState` + `handle_interrupt(state: AgentState, decision: str) -> AgentState` + **`build_doctor_probes() -> tuple[Callable[[RuntimeConfig], tuple[bool, str]], Callable[[RuntimeConfig], tuple[bool, str]]]`**（**review.md v1.0.0 P0-1 修复新增**：构造 doctor 子命令用的 model / checkpointer probe 函数对；F08 runtime 层依赖 primitives 是 matrix 允许的，把 probe 工厂放到 F08 既不引入新的分层违例，又避免 F10 / F09 各自直接 import `chat_model_factory` / `checkpoint_adapter`；F10 dispatch doctor 调 `build_doctor_probes()` 后注入到 F09 `run_doctor_checks(*, model_probe_fn=, checkpoint_probe_fn=)`；F09 不直接依赖 primitives；**review.md v3.0.0 P2-3 修复补充**：2 条硬例外边 `runtime_main_loop_dispatcher → primitives_{chat_model_factory, checkpoint_adapter}`；primitives 是被动接口 `create(config)` 构造方法，不反向依赖 F08；CHK-AR-025 校验这 2 条硬例外边的单向性） | ~340 |

### 3.2 Schema（**review.md v0.3.0 M-3 修复 + v0.4.0 M-4 方案 C 修复后**）

- `AgentState`（TypedDict, 5 字段；LangGraph 原生类型 + reducer 函数全部从 F01 `primitives` 层 import）：
  ```python
  from typing import Annotated, Any, TypedDict
  # v0.4.0 M-4 方案 C: reducer 函数从 primitives.state_reducers import（不在 runtime 层定义 reducer）
  from langagent.primitives.langchain_types import BaseMessage, add_messages      # review.md v0.3.0 M-3: 不直接 import langchain
  from langagent.primitives.state_reducers import (                                # review.md v0.4.0 M-4 方案 C: reducer 从 primitives 层 import
      replace_with_merge, merge_dict, overwrite_or_merge,
  )

  class AgentState(TypedDict, total=False):
      """LangAgent 主图 State；与 LangGraph 编译态直接对接。"""
      messages:   Annotated[list[BaseMessage], add_messages]              # LangGraph 内置 reducer
      todos:      Annotated[list[dict[str, Any]], replace_with_merge]     # primitives.state_reducers
      files:      Annotated[dict[str, dict[str, Any]], merge_dict]        # primitives.state_reducers
      context:    Annotated[dict[str, Any], overwrite_or_merge]           # primitives.state_reducers
      scratchpad: Annotated[dict[str, Any], replace_with_merge]           # primitives.state_reducers
  ```

> **v0.4.0 M-4 方案 C 修复后**：F08 **不持有** reducer 函数实现（仅持有 AgentState TypedDict 定义 + import primitives 层的 reducer）；F01 `primitives_state_graph_builder.build()` 在编译 StateGraph 时同样从 primitives 层注入 reducer；reducer 函数定义详见 module_schemas.md#schema-state-reducers。

### 3.3 ReAct 节点与边（LangGraph 构造的图）

F08 假设图已由 F01 / F05 编译完成，含以下节点：
- `model_call`：调用模型，产出 AIMessage。
- `tools_execute`：执行 AIMessage.tool_calls 中的 tool 调用，产出 ToolMessage 列表。
- `should_continue`：决策边，决定回到 `model_call` 还是结束（`END`）。

F08 的 `dispatch()` 仅负责**驱动**这张图：`graph.invoke(state, config)` 或 `graph.stream(state, config)`，并捕获 LangGraph `Interrupt` 异常。

### 3.4 主循环生命周期

```
while not done:
    state = dispatch(graph, state)
    if state["messages"][-1] is final AIMessage (no tool_calls):
        break
    if turn_count >= max_turns:
        raise TokenLimitExceededError  # 退出码 70
    if user interrupts (Ctrl-C):
        raise HitlInterruptedError  # 退出码 130
```

### 3.5 事件 + 日志双通道发射（**review.md v0.3.0 S-3 修复明确**）

F08 在 main_loop 阶段**同时通过 Event 总线（protocol_event_bus）+ 结构化日志（cross_cutting_logger）双通道发射**信号：

#### 3.5.1 Event 总线通道（F03）

- `tool_call`：每条 tool_call 在执行前 publish（F02 metrics_collector 订阅记 latency）。
- `tool_result`：每条 tool_message 在追加到 state.messages 前 publish。
- `model_response`：每条 AIMessage 在追加到 state.messages 前 publish（含 `usage_metadata` 给 metrics）。
- `guardrail_block`：F04 guardrail 拦截时 publish（F04 直接发，F08 转发）。

#### 3.5.2 结构化日志通道（F02 logger，**review.md v0.3.0 S-3 修复明确**）

F08 在 5 个 `la.lifecycle.run.*` + 7 个 `la.runtime.main_loop.*` = **12 个 tag 发射点**（**v0.4.0 M-NEW-3 rename**：原 `la.cli.run.*`；**v0.5.0 评审 v0.1.0 §三.B.1 修正**：原 prose 误写 6 个 lifecycle.run.*，实际只有 5 个 start / turn / tool_call / tool_result / model_response）；另 1 个 `la.cross_cutting.guardrail.block` 由 **F04** 直接发射，**F08 不重发**——但 F08 在 `run_until_done()` 范围内共观测到 **13 个 tag**（含 F04 发的 guardrail.block，F08 仅在 GraphInterrupt 时转发捕获）。F08 **通过 `from langagent.cross_cutting.logger import emit` 调用 F02 logger 接口**（与 F06 / F07 / F09 / F04 / F01 / F11 共享同一发射机制）：

| tag | 触发时机 | 位置 |
|---|---|---|
| `la.lifecycle.run.start` | `run_until_done()` 入口 | F08 `run_until_done()` 第一行 |
| `la.lifecycle.run.turn` | 每轮 ReAct 入口 | F08 `dispatch()` 入口（每轮） |
| `la.lifecycle.run.tool_call` | 模型发起 tool_call | F08 `dispatch()` 解析 `AIMessage.tool_calls` 后 |
| `la.lifecycle.run.tool_result` | tool 执行返回 | F08 `dispatch()` `tools_execute` 节点收尾 |
| `la.lifecycle.run.model_response` | 模型回复 | F08 `model_call` 节点收尾 |
| `la.runtime.main_loop.start` | 主循环开始 | F08 `run_until_done()` 第一行 |
| `la.runtime.main_loop.turn.start` | 单轮开始 | F08 `dispatch()` 入口 |
| `la.runtime.main_loop.turn.end` | 单轮结束 | F08 `dispatch()` 收尾 |
| `la.runtime.main_loop.model_call` | 模型调用 | F08 `model_call` 节点前后 |
| `la.runtime.main_loop.tool_call` | 工具调用（runtime 层视角） | F08 `tools_execute` 节点单 tool 前后 |
| `la.runtime.main_loop.tool_result` | 工具结果（runtime 层视角） | F08 `tools_execute` 节点产出 ToolMessage 后 |
| `la.runtime.main_loop.end` | 主循环结束 | F08 `run_until_done()` 收尾 |
| `la.cross_cutting.guardrail.block`（如触发） | guardrail 拦截 | **F04 `cross_cutting_guardrail_middleware.evaluate()` 决定时直接发**；**review.md v1.1.0 P1-4 + P2-6 修复后**：F08 `run_until_done()` 捕获 `GraphInterrupt` / `Interrupt` 异常时**不重发**（F04 已发，避免重复）。F08 行为分流：<br>(a) `langagent run` 场景：F08 抛 `HitlInterruptedError`，退出码 130；<br>(b) `langagent eval` 场景：F11 `_run_one_task()` 捕获后记录 `TaskResult.guardrail_blocked=True`，不中断整个 eval 循环，由 report_aggregator 聚合时标记。<br>**review.md v2.2.0 修复 P1-2**：本 tag 计入 F08 阶段观测总数（13 个），不计入 F08 自主发射数（12 个）；F04 是唯一发射方。 |

### 3.6 中间件注入（**review.md v1.0.0 P2-6 修复 + v2.2.2 P0-2 修复**）

- F01 §3.4a 步骤 5 在 `state_graph_builder.build()` 内部实例化系统护栏 middleware（调用 `cross_cutting_guardrail_middleware.build_middleware(policy=RuntimeConfig.guardrail_policy)`）并按 priority 升序与 USER middleware 一同注入图；F08 跑图时通过 `GraphInterrupt` 异常捕获机制接收 guardrail interrupt。
- F08 **不构造** `AgentMiddleware`，**不持有** MiddlewareSpec 列表——**MiddlewareSpec 由 F01 拥有**（review.md s-3 修复后归 F01）；F08 仅依赖 F01 `primitives_state_graph_builder.build()` 返回的已编译 `CompiledStateGraph`，所有 middleware（含系统 guardrail + USER）在 F01 `build()` 时按 `priority` 升序注入到图。

### 3.6a doctor 子命令 probe 工厂（**review.md v1.0.0 P0-1 修复新增**）

F08 新增 `build_doctor_probes()` API（详见 §三.1 模块清单），构造 doctor 子命令所需的 model / checkpointer probe 函数对。这是 F10 doctor dispatch 与 F09 `run_doctor_checks()` 之间的解耦点：

- **F10 dispatch doctor** 调 `probe_model_fn, probe_checkpoint_fn = build_doctor_probes()`，把两个 probe 注入到 F09；
- **F09 `run_doctor_checks(config, loaded, *, model_probe_fn=, checkpoint_probe_fn=)`** 接受 `Callable[[RuntimeConfig], tuple[bool, str]]` 形式注入，**不再直接 import primitives**（review.md v0.3.0 第四批 S-5 修复保留）；
- **F08 `build_doctor_probes()`** 是 probe 工厂的天然归属——runtime 层依赖 primitives 是 `architecture_modules.md` 依赖矩阵允许的，且 F08 已是 primitives 层的消费方（通过 `primitives_state_graph_builder.build()`）。

```python
# F08 runtime/main_loop_dispatcher.py 实现示例
from typing import Callable
from langagent.runtime.config_resolver import RuntimeConfig
from langagent.primitives import chat_model_factory, checkpoint_adapter

def build_doctor_probes() -> tuple[
    Callable[[RuntimeConfig], tuple[bool, str]],
    Callable[[RuntimeConfig], tuple[bool, str]],
]:
    """构造 doctor 子命令用的 model / checkpointer probe 函数。"""
    def probe_model(config: RuntimeConfig) -> tuple[bool, str]:
        try:
            m = chat_model_factory.create(config)
            return (m is not None, "endpoint reachable")
        except Exception as e:
            return (False, f"{type(e).__name__}: {e}")

    def probe_checkpoint(config: RuntimeConfig) -> tuple[bool, str]:
        try:
            cp = checkpoint_adapter.create(config)
            checkpoint_adapter.close(cp)
            return (True, "ok")
        except Exception as e:
            return (False, f"{type(e).__name__}: {e}")

    return probe_model, probe_checkpoint
```

F10 doctor dispatch 改为：

```python
from langagent.runtime.main_loop_dispatcher import build_doctor_probes
probe_model_fn, probe_checkpoint_fn = build_doctor_probes()
checks = exit_handler.run_doctor_checks(
    config, loaded,
    model_probe_fn=lambda: probe_model_fn(config),
    checkpoint_probe_fn=lambda: probe_checkpoint_fn(config),
)
```

> **替代方案 B（次推荐，已废弃）**：原 F10 doctor dispatch 直接 `import chat_model_factory.create()` —— 违反 `architecture_modules.md#mod-cli-runner` 硬约束（CLI × primitives 黑名单）。本修复废弃该方案。

## 四、TDD 测试用例先行

### 4.1 `dispatch` 单轮测试

- [ ] `test_dispatch_simple_greeting`：构造 LoadedAgent 含 1 个 fake tool（无副作用）+ state 含 HumanMessage("hi") → 调 1 轮 dispatch → state["messages"] 含 AIMessage；若无 tool_call 则主循环结束。
- [ ] `test_dispatch_with_tool_call`：fake tool 必被调用 1 次 → AIMessage.tool_calls 非空 → 调 tools_execute → state["messages"] 含 ToolMessage → 再调 model_call → 主循环结束。
- [ ] `test_dispatch_emits_tool_call_event`：mock event bus → `tool_call` 事件被 publish，payload 含 tool_id + args。
- [ ] `test_dispatch_emits_tool_result_event`：同上，`tool_result` 事件被 publish。
- [ ] `test_dispatch_emits_model_response_event`：同上，`model_response` 事件被 publish，payload 含 AIMessage.to_dict() + usage_metadata。
- [ ] `test_dispatch_increments_turn_count`：每次 dispatch 自增计数，写入 MetricsSnapshot。

### 4.2 `run_until_done` 端到端测试

- [ ] `test_run_until_done_converges`：构造 LoadedAgent + HumanMessage("echo 'hi'") + fake echo tool → `run_until_done` 跑完后 state["messages"][-1] 是 final AIMessage，无 tool_call。
- [ ] `test_run_until_done_max_turns_exceeded`：构造"模型永远生成 tool_call"的 fake → 30 轮后抛 `TokenLimitExceededError`，退出码 70。
- [ ] `test_run_until_done_user_interrupt`：mock `KeyboardInterrupt` → 抛 `HitlInterruptedError`，退出码 130。
- [ ] `test_run_until_done_tool_exception`：fake tool 抛异常 → 主循环记录到 state["scratchpad"]["errors"]，不立即终止；最终 metrics 记 `error_rate > 0`。
- [ ] `test_run_until_done_guardrail_interrupt`：tool `requires_approval=True` → LangGraph `Interrupt` 异常抛出 → F08 捕获 → 返回 control 到 caller（CLI 显示 HITL 提示）。

### 4.3 AgentState reducer 测试（宪法第 VI 条 + FR-037）

- [ ] `test_state_messages_add_messages_reducer`：连续两次 dispatch → state["messages"] 长度 +2，不覆盖历史。
- [ ] `test_state_todos_replace_with_merge`：连续两次更新 todos（提供完整列表）→ 每次按规则合并，无脑覆盖违反抛错。
- [ ] `test_state_files_merge_dict`：连续两次更新同一 file_path → 后值覆盖前值（按 key 合并）。
- [ ] `test_state_context_overwrite_or_merge`：显式 `overwrite` 时整体替换；`merge_with_prior` 时浅合并。
- [ ] `test_state_scratchpad_replace_with_merge`：与 todos 类似，每次提供完整字典。

### 4.4 Event 总线订阅者联动

- [ ] `test_metrics_subscriber_records_latency`：mock F02 metrics_collector → tool_call / model_response 事件触发 `record_latency`。
- [ ] `test_audit_subscriber_writes_on_guardrail_block`：mock F04 audit_recorder → guardrail_block 事件触发 `audit_recorder.write`。
- [ ] `test_logger_emits_la_runtime_main_loop_turn`：每轮开始 → `la.runtime.main_loop.turn.start` 日志；结束 → `la.runtime.main_loop.turn.end`。

### 4.4b main_loop 阶段日志发射测试（**review.md v0.3.0 S-3 修复新增 + v1.0.0 P2-5 修正**）

F08 在 main_loop 阶段自主发射 **12 个 tag**（5 个 `la.lifecycle.run.*` + 7 个 `la.runtime.main_loop.*`；**v0.4.0 M-NEW-3 rename**；详见 §3.5.2；**v0.5.0 评审 v0.1.0 §三.B.1 修正**：原 prose 误写 6 个 lifecycle.run.*，实际只有 5 个；**v1.0.0 P2-5 修正**：本节原"6 个"同步改为"5 个"）。另 1 个 `la.cross_cutting.guardrail.block` 由 F04 拥有，**F08 仅在 GraphInterrupt 时转发捕获（计入阶段观测总数 13 个，不计入自主发射数 12 个）**。

- [ ] `test_run_until_done_emits_lifecycle_run_start_log`：`run_until_done()` 入口 → 收到 `la.lifecycle.run.start` 日志。
- [ ] `test_run_until_done_emits_runtime_main_loop_start_log`：`run_until_done()` 入口 → 收到 `la.runtime.main_loop.start` 日志。
- [ ] `test_dispatch_emits_lifecycle_run_turn_log_per_round`：mock 3 轮 → 收到 3 次 `la.lifecycle.run.turn` 日志。
- [ ] `test_dispatch_emits_runtime_main_loop_turn_start_end_logs`：每轮 → 收到 `turn.start` + `turn.end` 各 1 次。
- [ ] `test_dispatch_emits_lifecycle_run_tool_call_log`：mock `AIMessage.tool_calls=[{...}]` → 收到 `la.lifecycle.run.tool_call` 日志，payload 含 `tool_id` / `args`。
- [ ] `test_dispatch_emits_lifecycle_run_tool_result_log`：mock `ToolMessage` → 收到 `la.lifecycle.run.tool_result` 日志。
- [ ] `test_dispatch_emits_lifecycle_run_model_response_log`：mock `AIMessage` → 收到 `la.lifecycle.run.model_response` 日志。
- [ ] `test_dispatch_emits_runtime_main_loop_model_call_log`：model_call 节点 → 收到 `la.runtime.main_loop.model_call` 日志。
- [ ] `test_dispatch_emits_runtime_main_loop_tool_call_log`：tools_execute 节点单 tool 前后 → 收到 `la.runtime.main_loop.tool_call` 日志。
- [ ] `test_dispatch_emits_runtime_main_loop_tool_result_log`：同上 → 收到 `la.runtime.main_loop.tool_result` 日志。
- [ ] `test_run_until_done_emits_runtime_main_loop_end_log`：`run_until_done()` 收尾 → 收到 `la.runtime.main_loop.end` 日志。
- [ ] `test_main_loop_log_tags_in_whitelist`：上述 13 个 tag 全部在 F02 `ALLOWED_TAGS` 集合（≥**46** 项）中。
- [ ] `test_main_loop_event_and_log_both_emitted`：`tool_call` 事件 publish 与 `la.lifecycle.run.tool_call` logger emit **同时**触发（双通道并存）。

### 4.5 LangGraph 集成测试（不可 mock 图行为）

- [ ] `test_real_graph_with_fake_model`：用 `langchain_core.language_models.fake.FakeListChatModel` 替代真实模型 → 图真实跑 → AIMessage 真实追加。
- [ ] `test_real_graph_with_fake_tool`：用 `@tool` 装饰器 + LangChain `BaseTool` 子类 → tools_execute 节点真实执行 → ToolMessage 真实返回。
- [ ] `test_real_graph_with_checkpointer_memory`：传入 `MemorySaver` → 跑两轮 invoke(thread_id="x") → 第二次 invoke 自动恢复 state。

## 五、关键约束

1. **不可 mock LangGraph 行为**：图必须真实跑；仅可 mock 模型与 tool 实现（宪法第 VIII 条 4 款）。
2. **AgentState 自研**：不得直接用 LangGraph 内置 `MessagesState` 作为终态；必须定义项目专属的 5 字段 TypedDict（宪法第 VI 条 2 款）。
3. **reducer 规则刚性**：
   - `messages`：`add_messages`（LangGraph 内置）。
   - `todos` / `scratchpad`：自定义 `replace_with_merge`（每次 update 提供完整列表/字典）。
   - `files`：自定义 `merge_dict`（按 path 键合并）。
   - `context`：仅 `overwrite` 或 `merge_with_prior`，不得追加式（FR-037）。
4. **阶段能力边界**：
   - `main_loop` 不得重新加载目录（→ F06）。
   - `main_loop` 不得重新解析 config（→ F07）。
   - `main_loop` 不得直接实例化模型（→ F01）。
   - `main_loop` 不得重新读 .env（→ F07）；**review.md v2.2.0 P2-5 修复明确**：main_loop 阶段读 .env 的越权事件**不走** `la.runtime.main_loop.fail` tag 而走 **`la.cross_cutting.guardrail.block`**（与 `workflow.md#langagent-run` §失败模式 `stage_capability_violation` 一致——main_loop 阶段违规由 F04 guardrail middleware 实施，归属 cross_cutting 命名空间；F08 §3.5.2 guardrail_block 表已明确不重发，F04 直接发射）。
   - 越权检测失败抛 `StageCapabilityViolationError`，退出码 1。
   - **F08 阶段级黑名单**（**review.md v1.1.0 P1-7 修复后引用 F06 §3.4 + v2.2.0 P1-6 修复后严格对齐权威源 + v2.2.2 P0-1 修复后引用 cross_cutting_stage_guard**）：monkeypatch 黑名单 = `[RuntimeDirLoader.load, RuntimeConfigResolver.resolve, BaseChatModel.__init__, chat_model_factory.create]`；audit_event 黑名单 = `["open"]`（拦截 `open(.env)`）；阶段装饰器 `@cross_cutting_stage_guard_decorator('main_loop', monkeypatch_blacklist=[...], audit_event_blacklist=['open'])` 由 F06 `cross_cutting/stage_guard.py` 提供。详细黑名单内容见 F06 §3.4 阶段级黑名单表 `{#stage-blacklist-table}`。
     > **来源注（review.md v0.1.0 R-005 修复明确）**：`stage_guard` 是 `workflow.md §"失败模式" stage_capability_violation` 的实现，**不是宪法第 V 条子条款**（宪法第 V 条仅含智能体目录契约，不含 6 阶段能力约束）。
5. **Edge 来源**：优先 LangGraph 原生 `add_conditional_edges`；自定义边通过路由函数实现（宪法第 VI 条 4 款）。
6. **HITL**：必须基于 LangGraph `interrupt()` 机制，不得绕开图 sleep / poll（宪法第 VI 条 6 款）。
7. **依赖方向**：runtime 不得反向依赖 cli；本模块依赖 F03（event_bus）+ F02（logger + metrics_collector）+ F04（guardrail_middleware）+ F01（primitives_langchain_types + state_graph_builder）。F08 通过 `from langagent.cross_cutting.logger import emit` 调用 F02 logger 发射 13 个阶段 tag（review.md v0.3.0 S-3 修复明确）。
8. **分层约束（review.md M-3 修复明确）**：F08 是 runtime 层模块，**不得直接 `import langchain` / `import langgraph`**；所有 LangChain / LangGraph 原生类型（如 `add_messages` / `BaseMessage` / `interrupt`）必须通过 F01 `langagent.primitives.langchain_types` 模块 re-export 后再 import。测试用 `grep -E '^(from|import) (langchain|langgraph)' langagent/runtime/*.py` 应无输出（CI 校验）。
9. **TDD 刚性**：先 Red 后 Green 再 Refactor。
10. **第 XV 条对齐清单**：与宪法第 VI 条（Agent Loop 与 State）/ 第 IX 条（Tracing / Evaluation / Testing 子能力）/ 第 XIII 条逐项对齐。

## 六、本 feature 不包含

- 不构造 StateGraph（→ F01）。
- 不实现 ReAct 节点（model_call / tools_execute / should_continue）本身的逻辑——由 `langchain.agents.create_agent` 或 LangGraph 原语提供，F01 负责装配。
- 不实现 logger / metrics / event_bus 本身（→ F03 / F02）。
- 不实现 guardrail middleware 本身（→ F04）。
- 不实现 EvalReport 生成（→ F11）。
- 不实现退出清理（→ F09）。

## 七、Deliverable 清单

- [ ] `langagent/runtime/main_loop_dispatcher.py`：`MainLoopDispatcher` 类 + `dispatch` / `run_until_done` / `handle_interrupt` 方法。
- [ ] `langagent/runtime/agent_state.py`：`AgentState` TypedDict 定义（**v0.4.0 M-4 方案 C 修复后**：仅 TypedDict；reducer 函数从 `langagent.primitives.state_reducers` import，**不在本文件定义 reducer**）。
- [ ] F08 **不复现** stage_guard.py（评审 m-1 修复）：从 F06 `from langagent.cross_cutting.stage_guard import stage_guard_decorator` 复用（**review.md v2.2.2 P0-1 修复后路径**：原 `langagent.runtime.stage_guard` 改为 `langagent.cross_cutting.stage_guard`），main_loop 入口加 `@cross_cutting_stage_guard_decorator('main_loop')`。
- [ ] `tests/runtime/test_main_loop_dispatcher.py`：≥28 个测试用例（review.md v0.3.0 S-3 修复后增补：原 15 个 + §4.4b 13 个 logger 发射测试 = 28 个）。
- [ ] `tests/runtime/test_agent_state_reducers.py`：≥5 个 reducer 单元测试。
- [ ] `tests/fixtures/sample_agent_with_fake_model/`：用 `FakeListChatModel` 的 fixture。
- [ ] `mypy --strict` 通过。
- [ ] spec / plan / tasks 顶部引用宪法第 XV 条。

## 八、与其它 feature 的边界

- **F06**：F08 复用 F06 实现的 `cross_cutting/stage_guard.py`（`@cross_cutting_stage_guard_decorator('main_loop')`）；不在 F08 单独实现 stage_guard。
- **F01**：F01 的 `primitives_state_graph_builder.build()` 编译出的 `CompiledStateGraph` 是 F08 的输入。F01 自身也应用 `@cross_cutting_stage_guard_decorator('graph_compose')`（**review.md v2.2.2 P0-1 修复新增**），F08 复用 build() 返回的产物已含阶段能力边界保障。
- **F05**：F05 的 `ToolSpec` 在 F01 graph_compose 阶段注入到图；F08 仅消费。
- **F04**：F04 的 `cross_cutting_guardrail_middleware.build_middleware(policy)` 在 F01 §3.4a 步骤 5 实例化并注入图；F08 跑图时遇 `Interrupt` 抛 `langgraph.errors.GraphInterrupt` 异常，F08 捕获并转换。F08 不直接 import F04 的 guardrail_middleware（仅类型注解通过 primitives_langchain_types re-export AgentMiddleware；F04 由 F01 持有并注入）。
- **F09**：F09 接收 F08 返回的最终 state，做 checkpointer 关闭 + report 写出；F09 也复用 F06 的 `cross_cutting/stage_guard.py`。
- **F11**：F11 对每条 EvalTaskSpec 调一次 F08 的 `run_until_done`，跑完调 grader 判定 pass/fail。