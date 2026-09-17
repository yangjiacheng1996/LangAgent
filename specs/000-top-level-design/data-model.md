# Data Model: Feature 00 — 顶层设计（Top-Level Design）

**Branch**: `000-top-level-design` | **Date**: 2026-09-14 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md)

> 本文档是 Phase 1 数据模型产物。Feature 00 是纯文档 Feature——本 data-model.md **不**描述运行时代码的实体类，而是把 module_schemas.md 须承载的 19 个一级章节（22 个类型）的"内存类型签名 / 磁盘格式 / schema_version / 与 LangChain/LangGraph 原生类型映射 / reducer 规则"沉淀为可机械核验的描述表，作为实施者落盘 module_schemas.md 的字段层依据。

## DM-1 Schema 总目录

> 严格 19 个一级章节（合并章节承载 2 个类型，合计 22 个类型），与 spec FR-031 / FR-032 / Clarifications Q2 一致。

| schema_id（蛇形）| 章节标题（PascalCase）| python_kind | schema_version | disk_format | 承载类型数 |
|---|---|---|---|---|---|
| `agent_state` | `AgentState` | `TypedDict` | `v0.1.0` | `JSON` | 1 |
| `runtime_config` | `RuntimeConfig` | `Pydantic BaseModel` | `v0.1.0` | `YAML` | 1 |
| `loaded_agent` | `LoadedAgent` | `dataclass(frozen=True)` | `v0.1.0` | `YAML` | 1 |
| `skill_spec_frontmatter` | `SkillSpec / SkillFrontmatter` | `SkillSpec: dataclass(frozen=True)` + `SkillFrontmatter: Pydantic BaseModel` | `v0.1.0` | `YAML` + `Markdown` | 2 |
| `tool_spec_side_effect` | `ToolSpec / ToolSideEffect` | `ToolSpec: Pydantic BaseModel` + `ToolSideEffect: Enum` | `v0.1.0` | `JSON` | 2 |
| `middleware_spec` | `MiddlewareSpec` | `Pydantic BaseModel` | `v0.1.0` | `YAML` | 1 |
| `channel_spec` | `ChannelSpec` | `Pydantic BaseModel` | `v0.1.0` | `YAML` | 1 |
| `channel_context` | `ChannelContext` | `TypedDict` | `v0.1.0` | `JSON` | 1 |
| `sandbox_spec` | `SandboxSpec` | `Pydantic BaseModel` | `v0.1.0` | `YAML` | 1 |
| `schedule_spec` | `ScheduleSpec` | `Pydantic BaseModel` | `v0.1.0` | `YAML` | 1 |
| `memory_spec` | `MemorySpec` | `Pydantic BaseModel` | `v0.1.0` | `YAML` | 1 |
| `identity_spec` | `IdentitySpec` | `Pydantic BaseModel` | `v0.1.0` | `YAML` | 1 |
| `eval_task_spec` | `EvalTaskSpec` | `Pydantic BaseModel` | `v0.1.0` | `YAML` | 1 |
| `span_trace` | `Span / Trace` | `Span: dataclass(frozen=True)` + `Trace: dataclass(frozen=True)` | `v0.1.0` | `JSONL` | 2 |
| `event` | `Event` | `Pydantic BaseModel` | `v0.1.0` | `JSONL` | 1 |
| `metrics_snapshot` | `MetricsSnapshot` | `dataclass(frozen=True)` | `v0.1.0` | `JSON` | 1 |
| `audit_entry` | `AuditEntry` | `Pydantic BaseModel` | `v0.1.0` | `JSONL` | 1 |
| `doctor_report` | `DoctorReport` | `Pydantic BaseModel` | `v0.1.0` | `JSON` | 1 |
| `eval_report` | `EvalReport` | `Pydantic BaseModel` | `v0.1.0` | `JSON` | 1 |
| **合计** | — | — | — | — | **19 / 22** |

## DM-2 19 个 schema 的字段级描述

> 下列每个 schema 给出：（a）`Python 类型签名`（字段名 + 类型 + 必填标记 + 默认值 + 说明）；（b）`磁盘格式与 schema_version`（一行字面量）；（c）`与 LangChain/LangGraph 原生类型映射`（以表格列出 `field` / `langchain_native` / `langgraph_native` / `notes`）；（d）`reducer 与不可变约束`（仅 AgentState 给出 reducer 规则；其余 schema 给出不可变约束说明）。
>
> 标记约定：`*` 必填；`-` 可选；类型以 `typing` 标注。

### DM-2.1 `agent_state`（AgentState）

#### Python 类型签名

```python
from typing import Annotated, Any, NotRequired, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages

class AgentState(TypedDict, total=False):
    """LangAgent 主图的 State；与 LangGraph 编译态直接对接。"""
    messages: Annotated[list[BaseMessage], add_messages]   # 必填；reducer = add_messages
    todos:    Annotated[list[TodoItem], replace_with_merge]  # 必填；reducer 自定义
    files:    Annotated[dict[str, FileEntry], merge_dict]   # 必填；reducer 自定义
    context:  Annotated[Context, overwrite_or_merge]       # 必填；reducer = overwrite / merge_with_prior
    scratchpad: Annotated[dict[str, Any], replace_with_merge]  # 必填；reducer 自定义
```

#### 磁盘格式与 schema_version

- `disk_format`: `JSON`（用于 checkpoint 序列化）
- `schema_version`: `v0.1.0`

#### reducer 与不可变约束

| 字段 | reducer 规则 | 说明 |
|---|---|---|
| `messages` | `add_messages` | LangGraph 内置；追加式合并；不覆盖历史 |
| `todos` | 自定义（`replace_with_merge`）| 不得使用无脑覆盖式 reducer；每次 update 须提供完整 todo 列表 |
| `files` | 自定义（`merge_dict`）| 不得使用无脑覆盖式 reducer；按 file_path 键合并 |
| `context` | `overwrite` / `merge_with_prior`（Q1 澄清）| 仅限这两种；不得使用追加式 reducer |
| `scratchpad` | 自定义（`replace_with_merge`）| 不得使用无脑覆盖式 reducer；每次 update 须提供完整 scratchpad 字典 |

#### 与 LangChain/LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| `messages` | `BaseMessage` | `add_messages` | LangGraph reducer；`BaseMessage` 含 `HumanMessage` / `AIMessage` / `ToolMessage` / `SystemMessage` |
| `todos` | N/A | N/A | 自定义 dict，无 LangChain/LangGraph 原生对应 |
| `files` | N/A | N/A | 自定义 dict，无 LangChain/LangGraph 原生对应 |
| `context` | N/A | N/A | 自定义 dict，无 LangChain/LangGraph 原生对应 |
| `scratchpad` | N/A | N/A | 自定义 dict，无 LangChain/LangGraph 原生对应 |

### DM-2.2 `runtime_config`（RuntimeConfig）

#### Python 类型签名

```python
from typing import Any
from pydantic import BaseModel, Field
from langchain_core.language_models import BaseChatModel

class RuntimeConfig(BaseModel, frozen=True):
    """LangAgent 启动时的配置快照；按 CLI > 环境变量 > .env > 内置默认 优先级合并。"""
    model_config = {"frozen": True}

    cli_args:        dict[str, Any]                        # * CLI 参数（含 --model / --checkpointer 等）
    env_vars:        dict[str, Any]                        # * 环境变量快照
    dotenv_values:   dict[str, Any]                        # * 智能体目录 .env 解析结果
    builtin_defaults: dict[str, Any]                       # * 内置默认值
    model:           BaseChatModel                         # * 已实例化模型（ChatOpenAI / ChatAnthropic / ...）
    model_provider:  str                                   # * 'openai' / 'anthropic' / 'google' / 'deepseek' / 'zhipu' / 'openai-compatible' ...
    model_name:      str                                   # * 'gpt-4o' / 'claude-3-5-sonnet' / 'qwen3-8b' / ...
    model_base_url:  str | None = None                     # - 仅 OpenAI Compatible 后端必填；联网模型为 None
    checkpointer:    str                                   # * 'memory' / 'sqlite' / 'postgres'（后续 Feature 实现）
    middleware_ids:  list[str]                             # * 已启用 middleware 的 module_id 列表
    skill_dirs:      list[str]                             # * 智能体目录 skills/ 下的子目录名列表
    log_level:       str = "INFO"                          # - 默认 INFO
```

#### 磁盘格式与 schema_version

- `disk_format`: `YAML`（供 `langagent doctor` 调试输出）
- `schema_version`: `v0.1.0`

#### reducer 与不可变约束

- 不可变（`frozen=True`）；运行时修改必须创建新实例。
- `cli_args` / `env_vars` / `dotenv_values` / `builtin_defaults` 4 字段共同表达"优先级链"——实施者需保证 `cli_args` 优先级最高，`builtin_defaults` 最低（中间层按 `env_vars` > `dotenv_values` 排列）。

#### 与 LangChain/LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| `model` | `BaseChatModel` | N/A | 必须是 `langchain_core.language_models.BaseChatModel` 子类 |
| `model_base_url` | N/A | N/A | 仅 OpenAI Compatible 必填；示例占位 `internal.example` |
| `checkpointer` | N/A | N/A | LangGraph checkpointer 类型由具体实现决定；本字段仅记名字 |
| `middleware_ids` | N/A | N/A | 引用 `architecture_modules.md` 的 `module_id` |

### DM-2.3 `loaded_agent`（LoadedAgent）

#### Python 类型签名

```python
from dataclasses import dataclass, field
from typing import Any
from langgraph.graph import CompiledStateGraph

@dataclass(frozen=True)
class LoadedAgent:
    """加载完成后的智能体；`compiled_graph` 是 LangGraph 编译态的图。"""
    agent_dir:           str                                # * 智能体目录绝对路径（运行时解析为绝对）
    instructions:        str                                # * 系统提示词（来自 instructions.md）
    compiled_graph:      CompiledStateGraph                  # * 已编译的 LangGraph 图
    tool_ids:            list[str]                           # * 已注册工具的 module_id 列表
    skill_names:         list[str]                           # * 已加载 skill 的 skill_name 列表
    metadata:            dict[str, Any]                      # - 其它元数据（model / checkpointer / 中间件 等）
```

#### 磁盘格式与 schema_version

- `disk_format`: `YAML`（不常序列化；仅 debug 用）
- `schema_version`: `v0.1.0`

#### reducer 与不可变约束

- 不可变（`frozen=True`）；加载完成后禁止修改。

#### 与 LangChain/LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| `compiled_graph` | N/A | `CompiledStateGraph` | 必须由 `langgraph.graph.StateGraph.compile()` 产生 |
| `tool_ids` | N/A | N/A | 引用 `ToolSpec` 的 tool_id |

### DM-2.4 `skill_spec_frontmatter`（合并章节，承载 2 个类型）

> 本章节为合并章节，前 2 个二级小节（Python 类型签名 / 磁盘格式与 schema_version）共用，后 2 个二级小节按类型拆分（FR-033 / Q9 澄清）。

#### Python 类型签名（共用）

```python
# SkillSpec
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class SkillSpec:
    """技能规范；每个 skill 对应智能体目录 skills/<skill_name>/ 下的一个子目录。"""
    skill_name:    str                                              # * skill 目录名
    skill_path:    str                                              # * skill 目录绝对路径
    description:   str                                              # * 单行描述（用于模型判断何时加载）
    body_path:     str                                              # * SKILL.md 文件绝对路径
    frontmatter:   'SkillFrontmatter'                               # * 关联的 SkillFrontmatter 实例
    enabled:       bool = True                                       # - 是否启用；默认 True

# SkillFrontmatter
from pydantic import BaseModel, Field

class SkillFrontmatter(BaseModel, frozen=True):
    """SKILL.md 文件顶部的 YAML 头；控制 SkillSpec 的元数据。"""
    model_config = {"frozen": True}

    name:         str                                                # * skill 名称
    description:  str                                                # * skill 单行描述
    version:      str = Field(pattern=r'^v\d+\.\d+\.\d+$')           # * 遵循 semver 字符串
    author:       str | None = None                                  # - 作者
    tags:         list[str] = []                                     # - 标签列表
    requires:     list[str] = []                                     # - 依赖的工具 ID / 中间件 ID 列表
```

#### 磁盘格式与 schema_version（共用）

- `disk_format`: `YAML`（`SkillFrontmatter` 嵌入在 SKILL.md 的 YAML 头中；`SkillSpec` 完整序列化在加载时输出）
- `schema_version`: `v0.1.0`

#### SkillSpec 与 LangChain/LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| `skill_name` | N/A | N/A | 自定义 |
| `skill_path` | N/A | N/A | 运行时绝对路径；磁盘格式中以相对路径 `skills/<name>/` 表达 |
| `body_path` | N/A | N/A | 运行时绝对路径；磁盘格式中以相对路径 `skills/<name>/SKILL.md` 表达 |
| `frontmatter` | N/A | N/A | 嵌套 `SkillFrontmatter` |

#### SkillSpec reducer 与不可变约束

- 不可变（`frozen=True`）；加载完成后禁止修改。

#### SkillFrontmatter 与 LangChain/LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| `name` | N/A | N/A | 与 `SkillSpec.skill_name` 一致 |
| `description` | N/A | N/A | 短描述，用于模型 prompt |
| `version` | N/A | N/A | semver；用于版本兼容判断 |
| `author` | N/A | N/A | 仅作元数据 |
| `tags` | N/A | N/A | 仅作元数据 |
| `requires` | N/A | N/A | 引用 `ToolSpec.tool_id` / `MiddlewareSpec.middleware_id` |

#### SkillFrontmatter reducer 与不可变约束

- 不可变（`frozen=True`）；加载完成后禁止修改。

### DM-2.5 `tool_spec_side_effect`（合并章节，承载 2 个类型）

#### Python 类型签名（共用）

```python
# ToolSpec
from pydantic import BaseModel, Field
from typing import Literal

class ToolSpec(BaseModel, frozen=True):
    """工具规范；每个 tool 对应智能体目录 tools/<tool_name>.py 中的一个函数。"""
    model_config = {"frozen": True}

    tool_id:      str                                                # * tool 函数名（必须可 import）
    tool_name:    str                                                # * tool 显示名（用于模型 prompt）
    description:  str                                                # * 单行描述
    args_schema:  dict[str, Any]                                      # * Pydantic schema（JSON Schema 形式）
    side_effects: list['ToolSideEffect']                              # * 工具副作用标注；用于 middleware 决策
    enabled:      bool = True                                         # - 是否启用
    requires_approval: bool = False                                   # - 是否需要 human-in-the-loop 审批

# ToolSideEffect
from enum import Enum

class ToolSideEffect(str, Enum):
    """工具副作用标注；middleware 据此决定是否 interrupt。"""
    NONE            = "none"                                          # 纯计算 / 查询
    READ_FILE       = "read_file"                                     # 读文件
    WRITE_FILE      = "write_file"                                    # 写文件
    EXEC_SHELL      = "exec_shell"                                    # 执行 shell 命令
    NETWORK_CALL    = "network_call"                                  # 调外部 API
    SEND_MESSAGE    = "send_message"                                  # 发送消息（IM 通道）
    EXTERNAL_STATE  = "external_state"                                # 改外部状态（数据库 / 文件系统 等）
```

#### 磁盘格式与 schema_version（共用）

- `disk_format`: `JSON`（`ToolSpec` 序列化为 JSON；`ToolSideEffect` 是字符串 enum，可嵌入 JSON）
- `schema_version`: `v0.1.0`

#### ToolSpec 与 LangChain/LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| `tool_id` | `BaseTool.name` | N/A | 与 LangChain `BaseTool` 子类的 `name` 属性对齐 |
| `description` | `BaseTool.description` | N/A | 与 `BaseTool.description` 对齐 |
| `args_schema` | `BaseTool.args_schema` | N/A | Pydantic schema；与 `BaseTool.args_schema` 对齐 |
| `side_effects` | N/A | N/A | 自定义枚举；用于 guardrail 中间件 |
| `requires_approval` | N/A | `interrupt` | 当 `True` 时，工具调用前会触发 `interrupt()` |

#### ToolSpec reducer 与不可变约束

- 不可变（`frozen=True`）；加载完成后禁止修改。

#### ToolSideEffect 与 LangChain/LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| （枚举值）| N/A | N/A | 自定义；非 LangChain / LangGraph 原生枚举 |

#### ToolSideEffect reducer 与不可变约束

- 不可变（`Enum`）；运行时禁止扩展新成员（必须重新发布）。

### DM-2.6 `middleware_spec`（MiddlewareSpec）

#### Python 类型签名

```python
from pydantic import BaseModel, Field
from typing import Literal

class MiddlewareSpec(BaseModel, frozen=True):
    """中间件规范；每个 middleware 对应智能体目录 middleware/<name>.py 中的一个对象。"""
    model_config = {"frozen": True}

    middleware_id:   str                                              # * middleware 类名（必须可 import）
    middleware_name: str                                              # * 显示名
    hook_points:     list[Literal[
        'before_model', 'after_model',
        'before_tools', 'after_tools',
        'before_agent', 'after_agent'
    ]]                                                                 # * 注入点；见 LangChain AgentMiddleware 协议
    priority:        int = 100                                         # - 数值越小越先执行；默认 100
    enabled:         bool = True                                       # - 是否启用
    config:          dict[str, Any] = {}                               # - 中间件专属配置（如 token 上限 / 限速阈值）
```

#### 磁盘格式与 schema_version

- `disk_format`: `YAML`
- `schema_version`: `v0.1.0`

#### 与 LangChain/LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| `middleware_id` | `AgentMiddleware` | N/A | 必须实现 LangChain `AgentMiddleware` 协议 |
| `hook_points` | `AgentMiddleware` hook | N/A | 与 `AgentMiddleware` 的 hook 属性对齐 |

#### reducer 与不可变约束

- 不可变（`frozen=True`）；加载完成后禁止修改。

### DM-2.7 `channel_spec`（ChannelSpec）

#### Python 类型签名

```python
from pydantic import BaseModel

class ChannelSpec(BaseModel, frozen=True):
    """消息通道规范（IM 入口，如 Slack / 飞书 / 钉钉）；v1 占位接口。"""
    model_config = {"frozen": True}

    channel_id:    str                                                 # * 通道标识（如 'slack' / 'feishu' / 'dingtalk'）
    channel_type:  str                                                 # * 'slack' / 'feishu' / 'dingtalk' / ...
    enabled:       bool = False                                         # - v1 占位，默认禁用
    config:        dict[str, any] = {}                                 # - 通道专属配置（webhook / token / ...）
```

#### 磁盘格式与 schema_version

- `disk_format`: `YAML`
- `schema_version`: `v0.1.0`

#### 与 LangChain/LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| （全部）| N/A | N/A | 通道为 LangAgent 自研，非 LangChain / LangGraph 原生 |

#### reducer 与不可变约束

- 不可变（`frozen=True`）；v1 全部通道 `enabled = False`，由后续 Feature 启用。

### DM-2.8 `channel_context`（ChannelContext）

#### Python 类型签名

```python
from typing import Annotated, TypedDict
from langgraph.graph import overwrite

class ChannelContext(TypedDict, total=False):
    """消息通道上下文；嵌入 AgentState.context 字段。"""
    channel_id:    str                                                 # * 触发的 channel_id
    user_id:       str                                                 # * 渠道内用户 ID
    thread_id:     str                                                 # - 渠道内 thread ID
    raw_message:   str                                                 # * 渠道原始消息（未做 prompt injection 防御处理）
    sender_meta:   dict[str, any]                                      # - 发送者元数据（昵称 / 头像 等）
```

#### 磁盘格式与 schema_version

- `disk_format`: `JSON`
- `schema_version`: `v0.1.0`

#### 与 LangChain/LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| （全部）| N/A | N/A | 自定义 dict |

#### reducer 与不可变约束

- 嵌入 `AgentState.context` 字段；reducer 受 `AgentState.context` 约束（仅 `overwrite` / `merge_with_prior`）。

### DM-2.9 `sandbox_spec`（SandboxSpec）

#### Python 类型签名

```python
from pydantic import BaseModel

class SandboxSpec(BaseModel, frozen=True):
    """文件系统 / shell 沙箱规范；v1 占位接口。"""
    model_config = {"frozen": True}

    sandbox_type:  str                                                 # * 'docker' / 'firecracker' / 'local-subprocess' / ...
    enabled:       bool = False                                        # - v1 占位，默认禁用
    config:        dict[str, any] = {}                                 # - 沙箱配置（image / cgroup / resource limit）
```

#### 磁盘格式与 schema_version

- `disk_format`: `YAML`
- `schema_version`: `v0.1.0`

#### 与 LangChain/LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| （全部）| N/A | N/A | 自研；v1 占位 |

#### reducer 与不可变约束

- 不可变（`frozen=True`）；v1 全部 `enabled = False`。

### DM-2.10 `schedule_spec`（ScheduleSpec）

#### Python 类型签名

```python
from pydantic import BaseModel

class ScheduleSpec(BaseModel, frozen=True):
    """定时调度规范；v1 占位接口。"""
    model_config = {"frozen": True}

    schedule_id:   str                                                 # * 调度任务 ID
    cron:          str                                                 # * cron 表达式
    enabled:       bool = False                                        # - v1 占位
    config:        dict[str, any] = {}                                 # - 调度配置
```

#### 磁盘格式与 schema_version

- `disk_format`: `YAML`
- `schema_version`: `v0.1.0`

#### 与 LangChain/LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| （全部）| N/A | N/A | 自研；v1 占位 |

#### reducer 与不可变约束

- 不可变（`frozen=True`）；v1 全部 `enabled = False`。

### DM-2.11 `memory_spec`（MemorySpec）

#### Python 类型签名

```python
from pydantic import BaseModel

class MemorySpec(BaseModel, frozen=True):
    """长期记忆规范；v1 占位接口。"""
    model_config = {"frozen": True}

    memory_type:   str                                                 # * 'sqlite' / 'postgres' / 'redis' / ...
    enabled:       bool = False                                        # - v1 占位
    config:        dict[str, any] = {}                                 # - 记忆后端配置
```

#### 磁盘格式与 schema_version

- `disk_format`: `YAML`
- `schema_version`: `v0.1.0`

#### 与 LangChain/LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| （全部）| N/A | N/A | 自研；v1 占位 |

#### reducer 与不可变约束

- 不可变（`frozen=True`）；v1 全部 `enabled = False`。

### DM-2.12 `identity_spec`（IdentitySpec）

#### Python 类型签名

```python
from pydantic import BaseModel

class IdentitySpec(BaseModel, frozen=True):
    """调用者身份验证规范。"""
    model_config = {"frozen": True}

    identity_type: str                                                 # * 'none' / 'api-key' / 'oauth' / 'iam'
    enabled:       bool = False                                        # - 默认禁用（v1 可选）
    config:        dict[str, any] = {}                                 # - 身份验证配置
```

#### 磁盘格式与 schema_version

- `disk_format`: `YAML`
- `schema_version`: `v0.1.0`

#### 与 LangChain/LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| （全部）| N/A | N/A | 自研；非 LangChain / LangGraph 原生 |

#### reducer 与不可变约束

- 不可变（`frozen=True`）。

### DM-2.13 `eval_task_spec`（EvalTaskSpec）

#### Python 类型签名

```python
from pydantic import BaseModel, Field

class EvalTaskSpec(BaseModel, frozen=True):
    """评测任务规范；对应 evals/<task_name>.yaml。"""
    model_config = {"frozen": True}

    task_id:       str                                                 # * 任务 ID
    input:         str                                                 # * 任务输入（用户消息）
    expected:      str | list[str] | None = None                       # - 期望输出（可多行）
    grader:        str = "exact_match"                                 # * 'exact_match' / 'contains' / 'regex' / 'llm_judge' / ...
    timeout_s:     int = Field(default=60, ge=1)                       # - 单任务超时（秒）
    metadata:      dict[str, any] = {}                                 # - 任务元数据
```

#### 磁盘格式与 schema_version

- `disk_format`: `YAML`
- `schema_version`: `v0.1.0`

#### 与 LangChain/LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| （全部）| N/A | N/A | 自研；与 `agentevals` 兼容但本项目不依赖 |

#### reducer 与不可变约束

- 不可变（`frozen=True`）。

### DM-2.14 `span_trace`（合并章节，承载 2 个类型：Span + Trace）

#### Python 类型签名（共用）

```python
# Span
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class Span:
    """单个 span；宪法第 XII 条 3 款要求。"""
    trace_id:        str                                               # * trace ID（全局唯一）
    span_id:         str                                               # * span ID（trace 内唯一）
    parent_span_id:  str | None = None                                 # - 父 span ID
    name:            str                                               # * span 名称
    start:           datetime                                           # * 开始时间
    end:             datetime | None = None                            # - 结束时间（未结束 span 为 None）
    attributes:      dict[str, any]                                     # * span 属性（kv）

# Trace
from dataclasses import dataclass

@dataclass(frozen=True)
class Trace:
    """单个 trace；含 ≥ 1 个 Span。"""
    trace_id:    str                                                    # * trace ID（与根 Span.trace_id 一致）
    root_span_id: str                                                   # * 根 span ID
    span_count:  int                                                    # * 包含 span 总数
    started_at:  datetime                                               # * trace 起始时间
    ended_at:    datetime | None = None                                 # - trace 结束时间
    status:      str                                                    # * 'ok' / 'error' / 'cancelled'
```

#### 磁盘格式与 schema_version（共用）

- `disk_format`: `JSONL`（一行一个 Span；Trace 不单独输出，可由 Span 列表聚合）
- `schema_version`: `v0.1.0`

#### Span 与 LangChain/LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| `trace_id` | N/A | N/A | 自定义；可对接 Langfuse / OpenTelemetry |
| `span_id` | N/A | N/A | 同上 |
| `parent_span_id` | N/A | N/A | 同上 |
| `name` | N/A | N/A | 与 LangGraph node name 对齐（如 `model_call` / `tools_execute`）|
| `start` / `end` | N/A | N/A | ISO 8601 datetime |
| `attributes` | N/A | N/A | kv；可对接 OpenTelemetry attributes |

#### Span reducer 与不可变约束

- 不可变（`frozen=True`）；span 结束后不可修改，纠正必须创建新 span。

#### Trace 与 LangChain/LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| `trace_id` | N/A | N/A | 与根 Span.trace_id 对齐 |
| `root_span_id` | N/A | N/A | 根 Span.span_id |
| `span_count` | N/A | N/A | 聚合字段 |
| `started_at` / `ended_at` | N/A | N/A | ISO 8601 |
| `status` | N/A | N/A | 自定义枚举；非 LangChain / LangGraph 原生 |

#### Trace reducer 与不可变约束

- 不可变（`frozen=True`）。

### DM-2.15 `event`（Event / Event 总线）

#### Python 类型签名

```python
from pydantic import BaseModel
from datetime import datetime

class Event(BaseModel, frozen=True):
    """事件总线中的单条事件。"""
    model_config = {"frozen": True}

    event_id:    str                                                    # * 事件 ID（全局唯一）
    event_type:  str                                                    # * 事件类型（如 'tool_call' / 'model_response' / 'guardrail_block' / ...）
    emitted_at:  datetime                                               # * 事件发生时间
    source:      str                                                    # * 事件源（module_id 或 component name）
    payload:     dict[str, any]                                         # * 事件载荷
    trace_id:    str | None = None                                      # - 关联 trace_id
```

#### 磁盘格式与 schema_version

- `disk_format`: `JSONL`（一行一个 Event，事件流追加写）
- `schema_version`: `v0.1.0`

#### 与 LangChain/LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| `event_type` | N/A | N/A | 自定义事件类型 |
| `payload` | N/A | N/A | 自由 kv；可携带 `AIMessage` / `ToolMessage` 等 LangChain 原生对象（JSON 序列化） |
| `trace_id` | N/A | N/A | 与 `Span.trace_id` 对齐 |

#### reducer 与不可变约束

- 不可变（`frozen=True`）；事件发布后禁止修改。

### DM-2.16 `metrics_snapshot`（MetricsSnapshot）

#### Python 类型签名

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class MetricsSnapshot:
    """指标快照；按时间窗口聚合。"""
    window_start:  datetime                                              # * 窗口起始
    window_end:    datetime                                              # * 窗口结束
    sample_count:  int                                                   # * 样本数
    p50_latency_ms: float                                                # * P50 延迟
    p95_latency_ms: float                                                # * P95 延迟
    p99_latency_ms: float                                                # * P99 延迟
    error_rate:     float                                                # * 错误率（0-1）
    token_usage:    dict[str, int]                                       # * 模型 token 消耗（按 model_name 统计）
    cost_usd:       float                                                # * 估算成本（美元）
```

#### 磁盘格式与 schema_version

- `disk_format`: `JSON`（时序文件，追加写）
- `schema_version`: `v0.1.0`

#### 与 LangChain/LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| `token_usage` | `AIMessage.usage_metadata` | N/A | 引用 LangChain `AIMessage.usage_metadata` 字段 |

#### reducer 与不可变约束

- 不可变（`frozen=True`）。

### DM-2.17 `audit_entry`（AuditEntry）

#### Python 类型签名

```python
from pydantic import BaseModel
from datetime import datetime

class AuditEntry(BaseModel, frozen=True):
    """审计条目；记录 PII 泄露 / 越权 tool / prompt injection 等事件。"""
    model_config = {"frozen": True}

    entry_id:    str                                                     # * 条目 ID
    audited_at:  datetime                                                # * 审计时间
    severity:    str                                                     # * 'info' / 'warn' / 'error' / 'critical'
    category:    str                                                     # * 'pii_leak' / 'unauthorized_tool' / 'prompt_injection' / ...
    actor:       str                                                     # * 触发者（user / tool / model）
    action:      str                                                     # * 触发的动作
    target:      str | None = None                                       # - 作用对象（tool_id / file_path / ...）
    outcome:     str                                                     # * 'allowed' / 'blocked' / 'redacted' / 'logged'
    evidence:    dict[str, any]                                          # * 证据（脱敏后）
```

#### 磁盘格式与 schema_version

- `disk_format`: `JSONL`（一行一个 AuditEntry，仅追加）
- `schema_version`: `v0.1.0`

#### 与 LangChain/LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| `actor` | N/A | N/A | 自定义；非 LangChain / LangGraph 原生 |
| `action` | N/A | N/A | 自定义；可引用 `ToolSideEffect` 枚举值 |

#### reducer 与不可变约束

- 不可变（`frozen=True`）；审计一旦写入不得修改。

### DM-2.18 `doctor_report`（DoctorReport）

#### Python 类型签名

```python
from pydantic import BaseModel
from datetime import datetime

class DoctorReport(BaseModel, frozen=True):
    """`langagent doctor` 自检报告。"""
    model_config = {"frozen": True}

    report_id:   str                                                     # * 报告 ID
    generated_at: datetime                                               # * 生成时间
    checks:      list[dict[str, any]]                                    # * 单项自检结果（check_name / status / detail）
    overall:     str                                                     # * 'ok' / 'warn' / 'error'
    agent_dir:   str                                                     # * 被自检的智能体目录
    runtime:     'RuntimeConfig'                                         # * 当时的 RuntimeConfig 快照
```

#### 磁盘格式与 schema_version

- `disk_format`: `JSON`
- `schema_version`: `v0.1.0`

#### 与 LangChain/LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| `runtime` | N/A | N/A | 嵌套 `RuntimeConfig`（见 DM-2.2） |

#### reducer 与不可变约束

- 不可变（`frozen=True`）。

### DM-2.19 `eval_report`（EvalReport）

#### Python 类型签名

```python
from pydantic import BaseModel
from datetime import datetime

class EvalReport(BaseModel, frozen=True):
    """`langagent eval` 评测报告。"""
    model_config = {"frozen": True}

    report_id:    str                                                    # * 报告 ID
    generated_at: datetime                                               # * 生成时间
    agent_dir:    str                                                    # * 被评测的智能体目录
    task_results: list[dict[str, any]]                                   # * 单条任务结果（task_id / passed / actual / expected / detail）
    pass_rate:    float                                                  # * 通过率（0-1）
    p50_latency_ms: float                                                # * P50 延迟
    p95_latency_ms: float                                                # * P95 延迟
    token_usage:  dict[str, int]                                         # * token 消耗
    cost_usd:     float                                                  # * 估算成本
```

#### 磁盘格式与 schema_version

- `disk_format`: `JSON`
- `schema_version`: `v0.1.0`

#### 与 LangChain/LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| `token_usage` | `AIMessage.usage_metadata` | N/A | 引用 LangChain `AIMessage.usage_metadata` |

#### reducer 与不可变约束

- 不可变（`frozen=True`）。

## DM-3 字段约束总结表

> 把 19 个 schema 的关键约束汇总，便于实施者 / review 时核验。

| schema_id | python_kind | disk_format | schema_version | 关键不可变约束 | 关键 LangChain/LangGraph 映射 |
|---|---|---|---|---|---|
| `agent_state` | `TypedDict` | `JSON` | `v0.1.0` | 5 字段 reducer 规则（Q1）| `BaseMessage` / `add_messages` |
| `runtime_config` | `Pydantic BaseModel` | `YAML` | `v0.1.0` | `frozen=True`；优先级链 | `BaseChatModel` |
| `loaded_agent` | `dataclass(frozen=True)` | `YAML` | `v0.1.0` | `frozen=True` | `CompiledStateGraph` |
| `skill_spec_frontmatter` | mixed | `YAML` + `Markdown` | `v0.1.0` | `frozen=True` | N/A |
| `tool_spec_side_effect` | mixed | `JSON` | `v0.1.0` | `frozen=True`；`Enum` 不可扩展 | `BaseTool` |
| `middleware_spec` | `Pydantic BaseModel` | `YAML` | `v0.1.0` | `frozen=True` | `AgentMiddleware` |
| `channel_spec` | `Pydantic BaseModel` | `YAML` | `v0.1.0` | `frozen=True`；v1 禁用 | N/A |
| `channel_context` | `TypedDict` | `JSON` | `v0.1.0` | 嵌入 `AgentState.context` | N/A |
| `sandbox_spec` | `Pydantic BaseModel` | `YAML` | `v0.1.0` | `frozen=True`；v1 禁用 | N/A |
| `schedule_spec` | `Pydantic BaseModel` | `YAML` | `v0.1.0` | `frozen=True`；v1 禁用 | N/A |
| `memory_spec` | `Pydantic BaseModel` | `YAML` | `v0.1.0` | `frozen=True`；v1 禁用 | N/A |
| `identity_spec` | `Pydantic BaseModel` | `YAML` | `v0.1.0` | `frozen=True` | N/A |
| `eval_task_spec` | `Pydantic BaseModel` | `YAML` | `v0.1.0` | `frozen=True` | N/A |
| `span_trace` | mixed | `JSONL` | `v0.1.0` | `frozen=True` | N/A |
| `event` | `Pydantic BaseModel` | `JSONL` | `v0.1.0` | `frozen=True` | N/A |
| `metrics_snapshot` | `dataclass(frozen=True)` | `JSON` | `v0.1.0` | `frozen=True` | `AIMessage.usage_metadata` |
| `audit_entry` | `Pydantic BaseModel` | `JSONL` | `v0.1.0` | `frozen=True`；不可修改 | N/A |
| `doctor_report` | `Pydantic BaseModel` | `JSON` | `v0.1.0` | `frozen=True` | N/A |
| `eval_report` | `Pydantic BaseModel` | `JSON` | `v0.1.0` | `frozen=True` | `AIMessage.usage_metadata` |

## DM-4 与宪法一致性

| 宪法条款 | data-model 体现 |
|---|---|
| 第 VI 条（Agent Loop 与 State）| `AgentState` 5 字段与 reducer 规则（Q1 澄清）|
| 第 IX 条（质量诊断能力矩阵）| `Span / Trace` ↔ Tracing；`MetricsSnapshot` ↔ Monitoring；`AuditEntry` ↔ Guardrails；`EvalReport` ↔ Evaluation；`DoctorReport` ↔ Testing |
| 第 X 条（安全与隐私）| `ToolSideEffect` 标注 7 类副作用；`AuditEntry` 记录 4 类安全事件 |
| 第 XII 条（配置与可观测契约）| `RuntimeConfig` 4 字段优先级链；`Span / Trace` 7 字段（trace_id / span_id / parent_span_id / name / start / end / attributes）|
| 第 XIII 条（禁止项）| 所有 schema 不引用 LangSmith |

## DM-5 data-model 与 module_schemas.md 的关系

`data-model.md` 是 `module_schemas.md` 的"字段层蓝本"——实施者在落盘 `module_schemas.md` 时，19 个一级章节下的 4 个二级小节（即"Python 类型签名" / "磁盘格式与 schema_version" / "与 LangChain/LangGraph 原生类型映射" / "reducer 与不可变约束"）的字段内容**必须与本 data-model.md DM-2 节一致**，但表述形式是 Markdown 文档（不是真 Python 代码），允许使用 `python` 围栏块展示字段定义。

本 data-model.md **不**作为 module_schemas.md 自身的章节（即不写到 module_schemas.md 中），而是作为 review 时对照的依据。
