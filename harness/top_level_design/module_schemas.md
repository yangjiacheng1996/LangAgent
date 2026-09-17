---
doc_id: module_schemas
version: v2.1.0
last_updated: 2026-09-15
constitution_ref: ../../.specify/memory/constitution.md
related_docs:
  - workflow.md
  - architecture_modules.md
---

# module_schemas.md — 模块 Schema 设计文档

> 本文档是 LangAgent 顶层设计三份文档之三，定义 **23 个一级章节**（承载 **27 个类型**）的内存类型签名 + 磁盘格式 + schema_version + 与 LangChain / LangGraph 原生类型映射 + reducer 规则。
> 本文档作为 Feature 01-10+ 编写 TDD 失败用例时"我要造什么对象 / 字段是什么 / 序列化到磁盘长什么样"的事实来源。
>
> 与宪法第 I 条关系：本文件不发布 SDK、不暴露 importable API；纯设计文档。
> 与宪法第 II 条关系：所有类型基于 LangChain / LangGraph 原语，不引入 MDA 代码。
> 与宪法第 VI 条关系：AgentState 5 字段 reducer 与宪法第 VI 条 2 款对齐（Q1 澄清）。
> 与宪法第 IX 条关系：Span / Trace / MetricsSnapshot / AuditEntry / EvalReport / DoctorReport 6 类 schema 与宪法第 IX 条 5 项子能力一一对应。
> 与宪法第 X 条关系：**review.md v2.1.0 P1-4 修复新增**：GuardrailPolicy / GuardrailDecision 2 个新类型（承载宪法第 X 条 1 款"不外发数据"+ 第 IV 条 4 款"本地模型必须可作为默认"对齐——内网 vLLM 默认 allow / 公网 endpoint 默认 interrupt）；MDA 无对应 schema，是 LangAgent 针对公司内网 vLLM 部署的自研扩展。
> 与宪法第 XII 条关系：RuntimeConfig 优先级链 + Span 7 字段（trace_id / span_id / parent_span_id / name / start / end / attributes）。
>
> **v2.1.0 变更（review.md P1-4 修复）**：
> - 新增 `## GuardrailPolicy / GuardrailDecision {#schema-guardrail-policy}` 章节（1 级章节 23 / 23，承载 2 个类型 `GuardrailPolicy` + `GuardrailDecision`）；章节总数 22 → 23、类型总数 25 → 27。
> - `RuntimeConfig` 增 `guardrail_policy: GuardrailPolicy | None = None` 字段（`module_schemas.md#schema-runtime-config` §Python 类型签名）；F03 读 env `LANGAGENT_GUARDRAIL_ALLOW_INTERNAL_ENDPOINTS` + `LANGAGENT_INTERNAL_ENDPOINTS` 注入。
> - F09 §3.2 修订：GuardrailPolicy / GuardrailDecision 不再仅作 cross_cutting 内部 Pydantic 模型，进顶层 schema 清单（25 → 27）。
>
> **v0.4.0 变更（review.md M-4 方案 C 修复）**：AgentState 4 个自定义 reducer（`replace_with_merge` / `merge_dict` / `overwrite_or_merge`）的实现位置从 F05 runtime 层迁移到 `langagent/primitives/state_reducers.py`（F10 拥有），消除 primitives → runtime 分层冲突。AgentState TypedDict 仍在 `langagent/runtime/agent_state.py`（F05 拥有），但其 reducer 字段全部 `from langagent.primitives.state_reducers import ...`。新增 §"## StateReducers {#schema-state-reducers}" 章节承载 4 个 reducer 函数签名 + 字段约束 + reducer 协议。

---

## 文档元信息

| 字段 | 值 |
|---|---|
| `doc_id` | `module_schemas` |
| `version` | `v1.2.0`（**review.md v1.1.0 P0-2 修复后**：`LoadedAgent` schema_version v0.1.0 → v0.2.0；本文件主版本号同步升 v0.5.0 → v1.2.0） |
| `last_updated` | `2026-09-15` |
| `constitution_ref` | `../../.specify/memory/constitution.md` |
| `related_docs` | `workflow.md`、`architecture_modules.md` |

---

## Schema 总目录

> 23 个一级章节（合并章节承载 2 个类型，合计 27 个类型，v0.4.0 M-4 方案 C 修复后新增 `state_reducers`，review.md v0.5.0 修复（评审 v0.1.0 §二.A.1）新增 `eval_run_result`，**review.md v2.1.0 P1-4 修复新增 `guardrail_policy`**）；表末必须有合计行 `合计 — — — — 23 / 27`（review.md v0.2.0 S-2 修复：新增 RuntimeConfigSnapshot；v0.4.0 新增 StateReducers；v0.5.0 新增 EvalRunResult；v2.1.0 新增 GuardrailPolicy / GuardrailDecision）。

| schema_id | python_kind | schema_version | disk_format | 承载类型数 |
|---|---|---|---|---|
| `agent_state` | `TypedDict` | `v0.1.0` | `JSON` | 1 |
| `state_reducers` | `Callable` | `v0.1.0` | `JSON` | 1 |
| `runtime_config` | `Pydantic BaseModel` | `v0.2.0` | `YAML` | 1 |
| `runtime_config_snapshot` | `Pydantic BaseModel` | `v0.1.0` | `JSON` | 1 |
| `loaded_agent` | `dataclass(frozen=True)` | `v0.1.0` | `YAML` | 1 |
| `skill_spec_frontmatter` | `dataclass(frozen=True)` + `Pydantic BaseModel` | `v0.1.0` | `YAML` + `Markdown` | 2 |
| `tool_spec_side_effect` | `Pydantic BaseModel` + `Enum` | `v0.1.0` | `JSON` | 2 |
| `middleware_spec` | `Pydantic BaseModel` | `v0.1.0` | `YAML` | 1 |
| `channel_spec` | `Pydantic BaseModel` | `v0.1.0` | `YAML` | 1 |
| `channel_context` | `TypedDict` | `v0.1.0` | `JSON` | 1 |
| `sandbox_spec` | `Pydantic BaseModel` | `v0.1.0` | `YAML` | 1 |
| `schedule_spec` | `Pydantic BaseModel` | `v0.1.0` | `YAML` | 1 |
| `memory_spec` | `Pydantic BaseModel` | `v0.1.0` | `YAML` | 1 |
| `identity_spec` | `Pydantic BaseModel` | `v0.1.0` | `YAML` | 1 |
| `eval_task_spec` | `Pydantic BaseModel` | `v0.2.0` | `YAML` | 1 |
| `span_trace` | `dataclass(frozen=True)` × 2 | `v0.1.0` | `JSONL` | 2 |
| `event` | `Pydantic BaseModel` | `v0.1.0` | `JSONL` | 1 |
| `metrics_snapshot` | `dataclass(frozen=True)` | `v0.1.0` | `JSON` | 1 |
| `audit_entry` | `Pydantic BaseModel` | `v0.1.0` | `JSONL` | 1 |
| `doctor_report` | `Pydantic BaseModel` | `v0.2.0` | `JSON` | 1 |
| `eval_run_result` | `dataclass(frozen=True)` | `v0.1.0` | —（不写盘） | 1 |
| `eval_report` | `Pydantic BaseModel` | `v0.1.0` | `JSON` | 1 |
| `guardrail_policy` | `Pydantic BaseModel` × 2 | `v0.1.0` | `JSON` | 2 |
| **合计** | — | — | — | **23 / 27** |

---

## AgentState {#schema-agent-state}

> 1 级章节 1 / 22。承载 LangGraph 主图 State；与宪法第 VI 条 2 款 5 字段对齐（Q1 澄清）。
> **v0.4.0 M-4 方案 C 修复**：4 个自定义 reducer（`replace_with_merge` / `merge_dict` / `overwrite_or_merge`）的实现位于 `langagent.primitives.state_reducers`（F10 拥有，见 #schema-state-reducers）；AgentState TypedDict 仍在 `langagent/runtime/agent_state.py`（F05 拥有）但仅 import reducer 函数，不持有 reducer 实现。

### Python 类型签名

```python
from typing import Annotated, Any, TypedDict
from langagent.primitives.langchain_types import BaseMessage, add_messages  # v0.4.0: 通过 primitives 层 re-export
from langagent.primitives.state_reducers import (                          # v0.4.0 M-4 方案 C: reducer 从 primitives 层 import
    replace_with_merge, merge_dict, overwrite_or_merge,
)

class AgentState(TypedDict, total=False):
    """LangAgent 主图 State；与 LangGraph 编译态直接对接。"""
    messages:   Annotated[list[BaseMessage], add_messages]              # 必填；reducer = add_messages（LangGraph 内置）
    todos:      Annotated[list[dict[str, Any]], replace_with_merge]     # 必填；自定义 reducer（primitives.state_reducers）
    files:      Annotated[dict[str, dict[str, Any]], merge_dict]        # 必填；自定义 reducer（primitives.state_reducers）
    context:    Annotated[dict[str, Any], overwrite_or_merge]           # 必填；reducer = overwrite / merge_with_prior（primitives.state_reducers）
    scratchpad: Annotated[dict[str, Any], replace_with_merge]           # 必填；自定义 reducer（primitives.state_reducers）
```

> 必填字段均不使用 `Any` 作为字段类型；仅 `scratchpad.value` 与 `files[path].meta` 内部值类型允许 `Any`（FR-034）。

### 磁盘格式与 schema_version

- `disk_format`: `JSON`（用于 checkpoint 序列化）
- `schema_version`: `v0.1.0`

### 与 LangChain / LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| `messages` | `BaseMessage` | `add_messages` | LangGraph 内置 reducer；`BaseMessage` 含 `HumanMessage` / `AIMessage` / `ToolMessage` / `SystemMessage` |
| `todos` | N/A | N/A | 自定义 list[dict]；reducer `replace_with_merge` 由 `primitives.state_reducers` 提供 |
| `files` | N/A | N/A | 自定义 dict；按 file_path 键合并；reducer `merge_dict` 由 `primitives.state_reducers` 提供 |
| `context` | N/A | N/A | 自定义 dict；嵌入 `ChannelContext`（见 `channel_context` schema）；reducer `overwrite_or_merge` 由 `primitives.state_reducers` 提供 |
| `scratchpad` | N/A | N/A | 自定义 dict；用于推理过程临时数据；reducer `replace_with_merge` 由 `primitives.state_reducers` 提供 |

### reducer 与不可变约束

| 字段 | reducer 规则 | reducer 实现位置 | 说明 |
|---|---|---|---|
| `messages` | `add_messages`（LangGraph 内置） | `langgraph.graph.message.add_messages` | 追加式合并；不覆盖历史（FR-037） |
| `todos` | 自定义（`replace_with_merge`） | `langagent/primitives/state_reducers.py:replace_with_merge`（**v0.4.0 M-4 方案 C 修复后**） | 不得使用无脑覆盖式 reducer；每次 update 须提供完整 todo 列表（FR-037） |
| `files` | 自定义（`merge_dict`） | `langagent/primitives/state_reducers.py:merge_dict`（**v0.4.0 M-4 方案 C 修复后**） | 不得使用无脑覆盖式 reducer；按 file_path 键合并（FR-037） |
| `context` | `overwrite` / `merge_with_prior`（二选一） | `langagent/primitives/state_reducers.py:overwrite_or_merge`（**v0.4.0 M-4 方案 C 修复后**） | 仅限这两种；不得使用追加式 reducer（Q1 澄清，FR-037） |
| `scratchpad` | 自定义（`replace_with_merge`） | `langagent/primitives/state_reducers.py:replace_with_merge`（**v0.4.0 M-4 方案 C 修复后**） | 不得使用无脑覆盖式 reducer；每次 update 须提供完整 scratchpad 字典（FR-037） |

---

## StateReducers {#schema-state-reducers}

> 1 级章节 1.5 / 22。AgentState 4 个自定义字段的 reducer 函数集合；v0.4.0 M-4 方案 C 修复后从 F05 runtime 层下沉到 F10 primitives 层（`langagent/primitives/state_reducers.py`）。
> 承载 **3 个唯一 reducer 函数**（`replace_with_merge` / `merge_dict` / `overwrite_or_merge`），覆盖 AgentState 的 4 个自定义字段（`todos` / `files` / `context` / `scratchpad`；`replace_with_merge` 被 `todos` 与 `scratchpad` 共用）；`messages` 字段的 `add_messages` reducer 由 LangGraph 内置提供，不在本 schema。

### Python 类型签名

```python
# langagent/primitives/state_reducers.py
from typing import Any, Literal

def replace_with_merge(
    current: list[dict[str, Any]] | None,
    update: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """replace_with_merge reducer（用于 AgentState.todos / scratchpad 字段）。
    每次 update 必须提供完整列表；不允许增量添加（避免无脑覆盖）。
    """
    if update is None:
        return current if current is not None else []
    return update


def merge_dict(
    current: dict[str, dict[str, Any]] | None,
    update: dict[str, dict[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    """merge_dict reducer（用于 AgentState.files 字段）。
    按 file_path 键合并；后值覆盖前值；不删除旧键。
    """
    if current is None:
        current = {}
    if update is None:
        return current
    return {**current, **update}


def overwrite_or_merge(
    current: dict[str, Any] | None,
    update: dict[str, Any] | None,
    *,
    mode: Literal['overwrite', 'merge_with_prior'] = 'merge_with_prior',
) -> dict[str, Any]:
    """overwrite_or_merge reducer（用于 AgentState.context 字段）。
    mode='overwrite' 整体替换；mode='merge_with_prior' 浅合并（update 键覆盖 current 键）。
    reducer 函数签名为 (current, update) → result；mode 通过 kwargs 注入（LangGraph 支持）。
    """
    if current is None:
        current = {}
    if update is None:
        return current
    if mode == 'overwrite':
        return dict(update)
    return {**current, **update}
```

### 磁盘格式与 schema_version

- `disk_format`: `JSON`（reducer 函数本身的 metadata，例如函数名 / 参数签名；用于 v2+ reducer 序列化迁移）
- `schema_version`: `v0.1.0`

### 与 LangChain / LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| `replace_with_merge` | N/A | N/A | 纯 Python 函数；LangGraph `Annotated[..., reducer]` 协议接受任何 `(current, update) → result` 签名的 callable |
| `merge_dict` | N/A | N/A | 同上 |
| `overwrite_or_merge` | N/A | N/A | 同上；接受 `*` kwargs（`mode` 参数）用于 mode 选择 |

### reducer 协议与不可变约束

- 4 个 reducer 函数均为纯函数（pure function）：相同 `(current, update)` 输入必产生相同输出；不读全局状态、不发起 IO。
- reducer 函数**禁止**抛异常：LangGraph 在每次 reducer 调用失败时整个图执行失败；reducer 内部异常需捕获并降级（如 `replace_with_merge` 失败 → 返回 `current`）。
- reducer 函数**禁止**修改 `current` 输入：必须返回新对象（frozen semantics）；LangGraph 依赖 immutable 更新做 time-travel debug。
- reducer 函数签名固定为 `(current, update) -> result`（LangGraph `Annotated[..., reducer]` 协议）；可选 kwargs（如 `mode`）由 LangGraph 通过 `functools.partial` 注入。
- **不可变约束**：reducer 函数本身不持有状态；无类属性、无模块级 mutable 全局变量。

### 与 AgentState 的关系

- AgentState TypedDict（`#schema-agent-state`）的 4 个自定义 reducer 字段全部通过 `from langagent.primitives.state_reducers import ...` 引用本 schema。
- F10 `primitives_state_graph_builder.build()` 在编译 StateGraph 时通过 `from langagent.primitives.state_reducers import ...` 注入 reducer；F05 AgentState 定义同样从 primitives 层 import（避免分层冲突）。
- **架构归属**：reducer 函数实现位于 primitives 层（F10 拥有）；AgentState TypedDict 位于 runtime 层（F05 拥有）；两者通过 primitives → runtime 单向依赖（F05 依赖 primitives，primitives 不依赖 F05）。

---

## RuntimeConfig {#schema-runtime-config}

> 1 级章节 2 / 22。LangAgent 启动时的配置快照；按"CLI > 环境变量 > .env > 内置默认"优先级合并（宪法第 XII 条）。

### Python 类型签名

```python
from typing import Any, Self
from pydantic import BaseModel
from langchain_core.language_models import BaseChatModel

class RuntimeConfig(BaseModel, frozen=True):
    """LangAgent 启动时的配置快照；优先级链见 docstring。

    不可变（frozen=True）；任何字段变更通过 `with_*` 方法返回新实例。
    `model` 字段在 F03 config_resolve 产出时为 None，由 F01 dispatch 在
    `langagent run` 编排中通过 `config.with_model(chat_model_factory.create(config))` 填充。
    `guardrail_policy` 字段（**review.md v2.1.0 P1-4 修复新增**）：F03 读 env LANGAGENT_GUARDRAIL_ALLOW_INTERNAL_ENDPOINTS
    + LANGAGENT_INTERNAL_ENDPOINTS 注入；F09 evaluate() 通过该字段决策内网 endpoint allow。
    """
    model_config = {"frozen": True}

    cli_args:         dict[str, Any]      # * CLI 参数
    env_vars:         dict[str, Any]      # * 环境变量快照
    dotenv_values:    dict[str, Any]      # * 智能体目录 .env 解析结果
    builtin_defaults: dict[str, Any]      # * 内置默认值
    model:            BaseChatModel | None = None  # - F10 实例化后由 with_model 注入
    model_provider:   str                 # * 'openai' / 'anthropic' / 'google' / 'deepseek' / 'zhipu' / 'openai-compatible'
    model_name:       str | None = None   # - 占位符校验通过后填充（review.md m-5）
    model_base_url:   str | None = None   # - 仅 OpenAI Compatible 必填；不得含 localhost / 内网 IP（review.md S-4 / M-1）
    checkpointer:     str                 # * 'memory' / 'sqlite' / 'postgres'
    middleware_ids:   list[str]           # * 启用的 middleware 列表
    skill_dirs:       list[str]           # * skills/ 子目录名列表
    log_level:        str = "INFO"        # - 默认 INFO
    guardrail_policy: 'GuardrailPolicy | None' = None  # - **review.md v2.1.0 P1-4 修复新增**：F09 guardrail 决策参数；F03 读 env LANGAGENT_GUARDRAIL_* 注入

    def with_model(self, model: BaseChatModel) -> "RuntimeConfig":
        """返回一个新 RuntimeConfig，替换 model 字段；frozen 实例不可 mutate。"""
        return self.model_copy(update={"model": model})

    def with_model_base_url(self, base_url: str) -> "RuntimeConfig":
        """返回一个新 RuntimeConfig，替换 model_base_url 字段。"""
        return self.model_copy(update={"model_base_url": base_url})

    def with_guardrail_policy(self, policy: "GuardrailPolicy") -> "RuntimeConfig":
        """**review.md v2.1.0 P1-4 修复新增**：返回一个新 RuntimeConfig，替换 guardrail_policy 字段。"""
        return self.model_copy(update={"guardrail_policy": policy})
```

### 磁盘格式与 schema_version

- `disk_format`: `YAML`（供 `langagent doctor` 调试输出）
- `schema_version`: `v0.3.0`（review.md v2.1.0 P1-4 修复：`guardrail_policy` 字段新增，schema_version v0.2.0 → v0.3.0）

### 与 LangChain / LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| `model` | `BaseChatModel` | N/A | F03 产出时为 None；F01 dispatch 编排时调用 `with_model()` 注入 |
| `model_base_url` | N/A | N/A | 仅 OpenAI Compatible 必填；不得为 `localhost` / `127.0.0.1` / 内网 IP 字面量 |
| `checkpointer` | N/A | N/A | LangGraph checkpointer 类型由实现决定；本字段仅记名字 |
| `middleware_ids` | N/A | N/A | 引用 `architecture_modules.md` 的 `module_id` |

### reducer 与不可变约束

- 不可变（`frozen=True`）；运行时修改必须通过 `with_model()` / `with_model_base_url()` 等 `with_*` 方法创建新实例。
- 4 字段优先级链：`cli_args` > `env_vars` > `dotenv_values` > `builtin_defaults`；实施者须保证优先级严格生效。
- **占位符校验（review.md m-5）**：F03 解析后扫描所有字符串字段，命中正则 `^<your-.+>$` 即抛 `ConfigPlaceholderError`，退出码 78（提示用户替换占位符）。

---

## RuntimeConfigSnapshot {#schema-runtime-config-snapshot}

> 1 级章节 3 / 22。`langagent doctor` 报告中的可序列化配置快照；不含 `BaseChatModel` 实例。
> 由 review.md v0.2.0 S-2 修复新增：解决 `DoctorReport.runtime` 嵌套 `RuntimeConfig` 后 `BaseChatModel` 无法 JSON 序列化的问题。

### Python 类型签名

```python
from pydantic import BaseModel
from typing import Any

class RuntimeConfigSnapshot(BaseModel, frozen=True):
    """`langagent doctor` 输出用 RuntimeConfig 子集；不含 model 实例与密钥。"""
    model_config = {"frozen": True}

    schema_version:   str             # * "v0.2.0"（**review.md v2.1.0 P1-4 修复**：含 guardrail_allow_internal_endpoints 字段）
    model_provider:   str             # * 'openai' / 'anthropic' / 'google' / 'deepseek' / 'zhipu' / 'openai-compatible'
    model_name:       str | None      # - 实例化时模型名
    model_base_url:   str | None      # - 仅 OpenAI Compatible 后端
    checkpointer:     str             # * 'memory' / 'sqlite' / 'postgres'
    middleware_ids:   list[str]       # * 启用的 middleware 列表
    skill_dirs:       list[str]       # * skills/ 子目录名列表
    log_level:        str = "INFO"    # - 默认 INFO
    guardrail_allow_internal_endpoints: bool = True  # **review.md v2.1.0 P1-4 修复新增**：F09 guardrail 内网 endpoint allow 开关

    @classmethod
    def from_runtime_config(cls, config: "RuntimeConfig") -> "RuntimeConfigSnapshot":
        """从 RuntimeConfig 实例构造 Snapshot；过滤敏感字段（不复制 cli_args / env_vars / dotenv_values / builtin_defaults / model / guardrail_policy 全字段）。"""
        return cls(
            schema_version="v0.2.0",
            model_provider=config.model_provider,
            model_name=config.model_name,
            model_base_url=config.model_base_url,
            checkpointer=config.checkpointer,
            middleware_ids=list(config.middleware_ids),
            skill_dirs=list(config.skill_dirs),
            log_level=config.log_level,
            guardrail_allow_internal_endpoints=(
                config.guardrail_policy.allow_internal_endpoints
                if config.guardrail_policy is not None
                else True
            ),
        )
```

### 磁盘格式与 schema_version

- `disk_format`: `JSON`（嵌入 `DoctorReport.runtime` 字段；DoctorReport 整体写 `reports/doctor-<timestamp>.json`）
- `schema_version`: `v0.2.0`（**review.md v2.1.0 P1-4 修复**：增 `guardrail_allow_internal_endpoints` 字段）

### 与 LangChain / LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| （全部） | N/A | N/A | 自定义；不含 LangChain / LangGraph 原生类型，保证 JSON 序列化 |

### reducer 与不可变约束

- 不可变（`frozen=True`）；构造完成后禁止修改。
- **不复制 `RuntimeConfig.model`**（BaseChatModel 实例不可序列化）；不复制 `cli_args` / `env_vars` / `dotenv_values` / `builtin_defaults`（可能含密钥）。
- 仅 8 个字段：与 `RuntimeConfig` 13 字段相比，缺失 `model` / `cli_args` / `env_vars` / `dotenv_values` / `builtin_defaults`。

---

## LoadedAgent {#schema-loaded-agent}

> 1 级章节 4 / 22。加载完成后的智能体；仅含**智能体目录静态信息**（不含编译后图）。
> **v1.2.0 变更（review.md v1.1.0 P0-2 修复方案 B）**：`compiled_graph` 字段 v1.1.0 已删除。理由：CompiledStateGraph 是运行时产物，由 F10 `primitives_state_graph_builder.build()` 返回给 F01 dispatch，不应在 LoadedAgent（智能体目录静态信息）中承载。`schema_version`: v0.1.0 → **v0.2.0**（字段集合变更）。

### Python 类型签名

```python
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class LoadedAgent:
    """加载完成后的智能体；不可变。仅含智能体目录静态信息。

    v1.1.0 P0-2 修复后：删除 compiled_graph 字段。运行时 CompiledStateGraph 由 F10 build() 返回，
    F01 dispatch 持 LoadedAgent + CompiledStateGraph 两个独立变量管理生命周期。
    """
    agent_dir:    str                       # * 智能体目录绝对路径
    instructions: str                       # * 系统提示词（来自 instructions.md）
    tool_ids:     list[str]                 # * 已注册工具的 module_id 列表
    skill_names:  list[str]                 # * 已加载 skill 的 skill_name 列表
    metadata:     dict[str, Any]            # - 其它元数据（model / checkpointer / middleware）
```

### 磁盘格式与 schema_version

- `disk_format`: `YAML`（不常序列化；仅 debug 用）
- `schema_version`: **v0.2.0**（**review.md v1.1.0 P0-2 修复后**：v0.1.0 → v0.2.0，因 `compiled_graph` 字段删除）

### 与 LangChain / LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| `tool_ids` | N/A | N/A | 引用 `ToolSpec` 的 `tool_id`（见 `tool_spec_side_effect`） |
| `skill_names` | N/A | N/A | 引用 `SkillSpec` 的 `skill_name`（见 `skill_spec_frontmatter`） |

### reducer 与不可变约束

- 不可变（`frozen=True`）；加载完成后禁止修改。
- **不再承载 CompiledStateGraph**（v1.1.0 P0-2 修复后）：运行时图由 F01 dispatch 独立持有；F10 build() 返回值与 LoadedAgent 解耦。

---

## SkillSpec / SkillFrontmatter {#schema-skill-spec-frontmatter}

> 1 级章节 5 / 22。合并章节，承载 2 个类型（SkillSpec + SkillFrontmatter）；FR-033 / Q9 澄清；下挂 6 个二级小节。

### Python 类型签名（共用）

```python
# SkillSpec
from dataclasses import dataclass

@dataclass(frozen=True)
class SkillSpec:
    """技能规范；每个 skill 对应智能体目录 skills/<skill_name>/ 下的一个子目录。"""
    skill_name:  str                      # * skill 目录名
    skill_path:  str                      # * skill 目录绝对路径
    description: str                      # * 单行描述（用于模型判断何时加载）
    body_path:   str                      # * SKILL.md 文件绝对路径
    frontmatter: 'SkillFrontmatter'       # * 关联的 SkillFrontmatter 实例
    enabled:     bool = True              # - 是否启用；默认 True

# SkillFrontmatter
from pydantic import BaseModel, Field

class SkillFrontmatter(BaseModel, frozen=True):
    """SKILL.md 文件顶部的 YAML 头；控制 SkillSpec 的元数据。"""
    model_config = {"frozen": True}

    name:        str                                       # * skill 名称
    description: str                                       # * skill 单行描述
    version:     str = Field(pattern=r'^v\d+\.\d+\.\d+$')  # * 遵循 semver
    author:      str | None = None                         # - 作者
    tags:        list[str] = []                            # - 标签列表
    requires:    list[str] = []                            # - 依赖的工具 / 中间件 ID 列表
```

### 磁盘格式与 schema_version（共用）

- `disk_format`: `YAML`（`SkillFrontmatter` 嵌入 SKILL.md 顶部 YAML 头；`SkillSpec` 完整序列化在加载时输出）
- `schema_version`: `v0.1.0`

### SkillSpec 与 LangChain / LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| `skill_name` | N/A | N/A | 自定义 |
| `skill_path` | N/A | N/A | 运行时绝对路径；磁盘格式中以 `skills/<name>/` 表达 |
| `body_path` | N/A | N/A | 运行时绝对路径；磁盘格式中以 `skills/<name>/SKILL.md` 表达 |
| `frontmatter` | N/A | N/A | 嵌套 `SkillFrontmatter` |

### SkillSpec reducer 与不可变约束

- 不可变（`frozen=True`）；加载完成后禁止修改。

### SkillFrontmatter 与 LangChain / LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| `name` | N/A | N/A | 与 `SkillSpec.skill_name` 一致 |
| `description` | N/A | N/A | 短描述，用于模型 prompt |
| `version` | N/A | N/A | semver；用于版本兼容判断 |
| `author` | N/A | N/A | 仅作元数据 |
| `tags` | N/A | N/A | 仅作元数据 |
| `requires` | N/A | N/A | 引用 `ToolSpec.tool_id` / `MiddlewareSpec.middleware_id` |

### SkillFrontmatter reducer 与不可变约束

- 不可变（`frozen=True`）；加载完成后禁止修改。

---

## ToolSpec / ToolSideEffect {#schema-tool-spec-side-effect}

> 1 级章节 6 / 22。合并章节，承载 2 个类型（ToolSpec + ToolSideEffect）；FR-033 / Q9 澄清；下挂 6 个二级小节。

### Python 类型签名（共用）

```python
# ToolSpec
from pydantic import BaseModel
from typing import Any

class ToolSpec(BaseModel, frozen=True):
    """工具规范；每个 tool 对应智能体目录 tools/<tool_name>.py 中的一个函数。"""
    model_config = {"frozen": True}

    tool_id:           str                    # * tool 函数名（必须可 import）
    tool_name:         str                    # * tool 显示名（用于模型 prompt）
    description:       str                    # * 单行描述
    args_schema:       dict[str, Any]         # * Pydantic schema（JSON Schema 形式）
    side_effects:      list['ToolSideEffect'] # * 工具副作用标注
    enabled:           bool = True            # - 是否启用
    requires_approval: bool = False           # - 是否需要 human-in-the-loop 审批

# ToolSideEffect
from enum import Enum

class ToolSideEffect(str, Enum):
    """工具副作用标注；middleware 据此决定是否 interrupt。"""
    NONE           = "none"           # 纯计算 / 查询
    READ_FILE      = "read_file"      # 读文件
    WRITE_FILE     = "write_file"     # 写文件
    EXEC_SHELL     = "exec_shell"     # 执行 shell 命令
    NETWORK_CALL   = "network_call"   # 调外部 API
    SEND_MESSAGE   = "send_message"   # 发送消息（IM 通道）
    EXTERNAL_STATE = "external_state" # 改外部状态（数据库 / 文件系统 等）
```

### 磁盘格式与 schema_version（共用）

- `disk_format`: `JSON`（`ToolSpec` 序列化为 JSON；`ToolSideEffect` 是字符串 enum，可嵌入 JSON）
- `schema_version`: `v0.1.0`

### ToolSpec 与 LangChain / LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| `tool_id` | `BaseTool.name` | N/A | 与 LangChain `BaseTool` 子类的 `name` 属性对齐 |
| `description` | `BaseTool.description` | N/A | 与 `BaseTool.description` 对齐 |
| `args_schema` | `BaseTool.args_schema` | N/A | Pydantic schema；与 `BaseTool.args_schema` 对齐 |
| `side_effects` | N/A | N/A | 自定义枚举；用于 guardrail middleware |
| `requires_approval` | N/A | `interrupt` | 当 `True` 时，工具调用前触发 `interrupt()` |

### ToolSpec reducer 与不可变约束

- 不可变（`frozen=True`）；加载完成后禁止修改。

### ToolSideEffect 与 LangChain / LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| （枚举值） | N/A | N/A | 自定义枚举；非 LangChain / LangGraph 原生 |

### ToolSideEffect reducer 与不可变约束

- 不可变（`Enum`）；运行时禁止扩展新成员（必须重新发布）。

---

## MiddlewareSpec {#schema-middleware-spec}

> 1 级章节 7 / 22。中间件规范；每个 middleware 对应智能体目录 `middleware/<name>.py` 中的一个对象。

### Python 类型签名

```python
from pydantic import BaseModel
from typing import Any, Literal

class MiddlewareSpec(BaseModel, frozen=True):
    """中间件规范；与 LangChain AgentMiddleware 协议对齐。"""
    model_config = {"frozen": True}

    middleware_id:   str                                    # * middleware 类名（必须可 import）
    middleware_name: str                                    # * 显示名
    hook_points:     list[Literal[
        'before_model', 'after_model',
        'before_tools', 'after_tools',
        'before_agent', 'after_agent'
    ]]                                                       # * 注入点；见 LangChain AgentMiddleware 协议
    priority:        int = 100                              # - 数值越小越先执行
    enabled:         bool = True                            # - 是否启用
    config:          dict[str, Any] = {}                    # - 中间件专属配置
```

### 磁盘格式与 schema_version

- `disk_format`: `YAML`
- `schema_version`: `v0.1.0`

### 与 LangChain / LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| `middleware_id` | `AgentMiddleware` | N/A | 必须实现 LangChain `AgentMiddleware` 协议 |
| `hook_points` | `AgentMiddleware` hook | N/A | 与 `AgentMiddleware` 的 hook 属性对齐 |

### reducer 与不可变约束

- 不可变（`frozen=True`）；加载完成后禁止修改。

---

## ChannelSpec {#schema-channel-spec}

> 1 级章节 8 / 22。消息通道规范（IM 入口，如 Slack / 飞书 / 钉钉）；v1 预留接口，不实现。
> **Owning Feature**: F12（v1 仅类型 stub；v2+ 由新增 channel 加载器 feature 接管）
> **Python 文件**: `langagent/protocol/reserved_types/channel.py`

### Python 类型签名

```python
from pydantic import BaseModel
from typing import Any

class ChannelSpec(BaseModel, frozen=True):
    """消息通道规范；v1 预留接口。"""
    model_config = {"frozen": True}

    channel_id:   str                  # * 通道标识（如 'slack' / 'feishu' / 'dingtalk'）
    channel_type: str                  # * 'slack' / 'feishu' / 'dingtalk' / ...
    enabled:      bool = False         # - v1 预留接口，默认禁用
    config:       dict[str, Any] = {}  # - 通道专属配置（webhook / token / ...）
```

### 磁盘格式与 schema_version

- `disk_format`: `YAML`
- `schema_version`: `v0.1.0`

### 与 LangChain / LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| （全部） | N/A | N/A | 通道为 LangAgent 自研，非 LangChain / LangGraph 原生 |

### reducer 与不可变约束

- 不可变（`frozen=True`）；v1 全部通道 `enabled = False`，由后续 Feature 启用。

---

## ChannelContext {#schema-channel-context}

> 1 级章节 9 / 22。消息通道上下文；嵌入 `AgentState.context` 字段。
> **Owning Feature**: F12（v1 类型 stub；F05 `AgentState.context` 是 `dict[str, Any]`，不特判 `ChannelContext`）
> **Python 文件**: `langagent/protocol/reserved_types/channel.py`

### Python 类型签名

```python
from typing import TypedDict

class ChannelContext(TypedDict, total=False):
    """消息通道上下文；嵌入 AgentState.context 字段。"""
    channel_id:  str                  # * 触发的 channel_id
    user_id:     str                  # * 渠道内用户 ID
    thread_id:   str                  # - 渠道内 thread ID
    raw_message: str                  # * 渠道原始消息（未做 prompt injection 防御处理）
    sender_meta: dict[str, Any]       # - 发送者元数据（昵称 / 头像 等）
```

### 磁盘格式与 schema_version

- `disk_format`: `JSON`
- `schema_version`: `v0.1.0`

### 与 LangChain / LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| （全部） | N/A | N/A | 自定义 dict；无 LangChain / LangGraph 原生对应 |

### reducer 与不可变约束

- 嵌入 `AgentState.context` 字段；reducer 受 `AgentState.context` 约束（仅 `overwrite` / `merge_with_prior`，Q1）。

---

## SandboxSpec {#schema-sandbox-spec}

> 1 级章节 10 / 22。文件系统 / shell 沙箱规范；v1 预留接口，不实现。
> **Owning Feature**: F12（v2+ 由新增 sandbox 执行器 feature 接管）
> **Python 文件**: `langagent/protocol/reserved_types/sandbox.py`

### Python 类型签名

```python
from pydantic import BaseModel
from typing import Any

class SandboxSpec(BaseModel, frozen=True):
    """文件系统 / shell 沙箱规范；v1 预留接口。"""
    model_config = {"frozen": True}

    sandbox_type: str                  # * 'docker' / 'firecracker' / 'local-subprocess' / ...
    enabled:      bool = False         # - v1 预留接口，默认禁用
    config:       dict[str, Any] = {}  # - 沙箱配置（image / cgroup / resource limit）
```

### 磁盘格式与 schema_version

- `disk_format`: `YAML`
- `schema_version`: `v0.1.0`

### 与 LangChain / LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| （全部） | N/A | N/A | 自研；v1 预留接口 |

### reducer 与不可变约束

- 不可变（`frozen=True`）；v1 全部 `enabled = False`。

---

## ScheduleSpec {#schema-schedule-spec}

> 1 级章节 11 / 22。定时调度规范；v1 预留接口，不实现。
> **Owning Feature**: F12（v2+ 由新增 cron 调度器 feature 接管）
> **Python 文件**: `langagent/protocol/reserved_types/schedule.py`

### Python 类型签名

```python
from pydantic import BaseModel
from typing import Any

class ScheduleSpec(BaseModel, frozen=True):
    """定时调度规范；v1 预留接口。"""
    model_config = {"frozen": True}

    schedule_id: str                  # * 调度任务 ID
    cron:        str                  # * cron 表达式
    enabled:     bool = False         # - v1 预留接口
    config:      dict[str, Any] = {}  # - 调度配置
```

### 磁盘格式与 schema_version

- `disk_format`: `YAML`
- `schema_version`: `v0.1.0`

### 与 LangChain / LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| （全部） | N/A | N/A | 自研；v1 预留接口 |

### reducer 与不可变约束

- 不可变（`frozen=True`）；v1 全部 `enabled = False`。

---

## MemorySpec {#schema-memory-spec}

> 1 级章节 12 / 22。长期记忆规范；v1 预留接口，不实现。
> **Owning Feature**: F12（v2+ 由新增 long-term memory feature 接管）
> **Python 文件**: `langagent/protocol/reserved_types/memory.py`

### Python 类型签名

```python
from pydantic import BaseModel
from typing import Any

class MemorySpec(BaseModel, frozen=True):
    """长期记忆规范；v1 预留接口。"""
    model_config = {"frozen": True}

    memory_type: str                  # * 'sqlite' / 'postgres' / 'redis' / ...
    enabled:     bool = False         # - v1 预留接口
    config:      dict[str, Any] = {}  # - 记忆后端配置
```

### 磁盘格式与 schema_version

- `disk_format`: `YAML`
- `schema_version`: `v0.1.0`

### 与 LangChain / LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| （全部） | N/A | N/A | 自研；v1 预留接口 |

### reducer 与不可变约束

- 不可变（`frozen=True`）；v1 全部 `enabled = False`。

---

## IdentitySpec {#schema-identity-spec}

> 1 级章节 13 / 22。调用者身份验证规范。
> **Owning Feature**: F12（v1 默认 `enabled=False`；v2+ 由新增 identity 加载器 feature 接管）
> **Python 文件**: `langagent/protocol/reserved_types/identity.py`

### Python 类型签名

```python
from pydantic import BaseModel
from typing import Any

class IdentitySpec(BaseModel, frozen=True):
    """调用者身份验证规范。"""
    model_config = {"frozen": True}

    identity_type: str                 # * 'none' / 'api-key' / 'oauth' / 'iam'
    enabled:       bool = False        # - 默认禁用（v1 可选）
    config:        dict[str, Any] = {} # - 身份验证配置
```

### 磁盘格式与 schema_version

- `disk_format`: `YAML`
- `schema_version`: `v0.1.0`

### 与 LangChain / LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| （全部） | N/A | N/A | 自研；非 LangChain / LangGraph 原生 |

### reducer 与不可变约束

- 不可变（`frozen=True`）。

---

## EvalTaskSpec {#schema-eval-task-spec}

> 1 级章节 14 / 22。评测任务规范；对应 `evals/<task_name>.yaml`。
> ⚠️ 警示（FR-043 + FR-043 (a) / Q11 / MC-2.6）：本章节禁止使用 `...` / `<其它枚举>` / `etc.` 等省略号表达未来扩展（FR-043）；扩展接口约定见下方"扩展接口约定"二级小节（MC-2.6 路径 1）。

### Python 类型签名

```python
from pydantic import BaseModel, Field
from typing import Literal

class EvalTaskSpec(BaseModel, frozen=True):
    """评测任务规范；对应 evals/<task_name>.yaml。"""
    model_config = {"frozen": True}

    task_id:   str                                                  # * 任务 ID
    input:     str                                                  # * 任务输入（用户消息）
    expected:  str | list[str] | dict[str, Any] | None = None      # - 期望输出（按 grader 取不同形态）
    grader:    Literal[
        'exact_match', 'contains', 'regex',
        'llm_judge', 'tool_call_match'
    ] = 'exact_match'                                               # * grader 类型（5 个候选值）
    timeout_s: int = Field(default=60, ge=1)                        # - 单任务超时（秒）
    metadata:  dict[str, Any] = {}                                  # - 任务元数据
```

> **`expected` 字段类型与 grader 的对应关系**（评审 M-4 修复后新增，schema_version v0.2.0）：
>
> | grader | `expected` 推荐类型 | 说明 |
> |---|---|---|
> | `exact_match` | `str \| list[str]` | 字符串精确匹配；list 时任一命中即 pass |
> | `contains` | `str \| list[str]` | 子串包含；list 时任一命中即 pass |
> | `regex` | `str \| list[str]` | 正则模式；list 时任一命中即 pass |
> | `llm_judge` | `str \| list[str]` | 语义等价判断的 prompt；list 时任一命中即 pass |
> | `tool_call_match` | `dict[str, Any]` | 必须含 `tool_id` + `args` 字段；判定 AIMessage.tool_calls 中存在 tool_id 相等且 args 匹配的项 |
>
> schema 层接受 4 种类型（`str | list[str] | dict | None`），具体取值约束由各 grader 运行时校验。`tool_call_match` grader 在 `expected` 不是 `dict` 时抛 `EvalGraderArgumentMismatchError`，退出码 65。

### 磁盘格式与 schema_version

- `disk_format`: `YAML`
- `schema_version`: `v0.2.0`（评审 M-4 修复：`expected` 类型从 `str | list[str] | None` 扩展为 `str | list[str] | dict[str, Any] | None`）

### 与 LangChain / LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| （全部） | N/A | N/A | 自研；与 `agentevals` 兼容但本项目不依赖 |

### reducer 与不可变约束

- 不可变（`frozen=True`）。

### 扩展接口约定

> MC-2.6 路径 1 落盘形式（FR-043 (a) / Q11）：扩展字段以 `<字段名>_extensibility` 命名约定列出，禁止以 `...` 缩写表达。

- `grader_extensibility: list[str] = []`：未来新增的 grader 取值应登记到此字段。
  - 当 grader 候选值集合需扩展时，由实施者按"schema_version 升版 + 写入 migrators + 更新 Literal 列表"流程操作；扩展点本身在此字段明示登记，避免遗漏。
  - 本约定禁止以省略号占位（如 `grader: Literal[..., 'new_method']`）；新增取值必须先扩展本字段，再升 schema_version。

---

## Span / Trace {#schema-span-trace}

> 1 级章节 15 / 22。合并章节，承载 2 个类型（Span + Trace）；FR-033 / Q9 澄清；下挂 6 个二级小节；宪法第 XII 条 3 款要求。

### Python 类型签名（共用）

```python
# Span
from dataclasses import dataclass
from datetime import datetime
from typing import Any

@dataclass(frozen=True)
class Span:
    """单个 span；宪法第 XII 条 3 款要求。"""
    trace_id:       str               # * trace ID（全局唯一）
    span_id:        str               # * span ID（trace 内唯一）
    parent_span_id: str | None = None # - 父 span ID
    name:           str               # * span 名称
    start:          datetime          # * 开始时间
    end:            datetime | None = None # - 结束时间
    attributes:     dict[str, Any]    # * span 属性（kv）

# Trace
@dataclass(frozen=True)
class Trace:
    """单个 trace；含 ≥ 1 个 Span。"""
    trace_id:    str                   # * trace ID（与根 Span.trace_id 一致）
    root_span_id: str                  # * 根 span ID
    span_count:  int                   # * 包含 span 总数
    started_at:  datetime              # * trace 起始时间
    ended_at:    datetime | None = None # - trace 结束时间
    status:      str                   # * 'ok' / 'error' / 'cancelled'
```

### 磁盘格式与 schema_version（共用）

- `disk_format`: `JSONL`（一行一个 Span；Trace 不单独输出，可由 Span 列表聚合）
- `schema_version`: `v0.1.0`

### Span 与 LangChain / LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| `trace_id` | N/A | N/A | 自定义；可对接 Langfuse / OpenTelemetry |
| `span_id` | N/A | N/A | 同上 |
| `parent_span_id` | N/A | N/A | 同上 |
| `name` | N/A | N/A | 与 LangGraph node name 对齐（如 `model_call` / `tools_execute`） |
| `start` / `end` | N/A | N/A | ISO 8601 datetime |
| `attributes` | N/A | N/A | kv；可对接 OpenTelemetry attributes |

### Span reducer 与不可变约束

- 不可变（`frozen=True`）；span 结束后不可修改，纠正必须创建新 span。

### Trace 与 LangChain / LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| `trace_id` | N/A | N/A | 与根 Span.trace_id 对齐 |
| `root_span_id` | N/A | N/A | 根 Span.span_id |
| `span_count` | N/A | N/A | 聚合字段 |
| `started_at` / `ended_at` | N/A | N/A | ISO 8601 |
| `status` | N/A | N/A | 自定义枚举；非 LangChain / LangGraph 原生 |

### Trace reducer 与不可变约束

- 不可变（`frozen=True`）。

---

## Event {#schema-event}

> 1 级章节 16 / 22。事件总线（"Event 总线"）的单条事件。

### Python 类型签名

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Any

class Event(BaseModel, frozen=True):
    """事件总线中的单条事件。"""
    model_config = {"frozen": True}

    event_id:   str                  # * 事件 ID（全局唯一）
    event_type: str                  # * 事件类型（如 'tool_call' / 'model_response' / 'guardrail_block' / ...）
    emitted_at: datetime             # * 事件发生时间
    source:     str                  # * 事件源（module_id 或 component name）
    payload:    dict[str, Any]       # * 事件载荷
    trace_id:   str | None = None    # - 关联 trace_id
```

### 磁盘格式与 schema_version

- `disk_format`: `JSONL`（一行一个 Event，事件流追加写）
- `schema_version`: `v0.1.0`

### 与 LangChain / LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| `event_type` | N/A | N/A | 自定义事件类型 |
| `payload` | N/A | N/A | 自由 kv；可携带 `AIMessage` / `ToolMessage` 等 LangChain 原生对象（JSON 序列化） |
| `trace_id` | N/A | N/A | 与 `Span.trace_id` 对齐 |

### reducer 与不可变约束

- 不可变（`frozen=True`）；事件发布后禁止修改。

---

## MetricsSnapshot {#schema-metrics-snapshot}

> 1 级章节 17 / 22。指标快照；按时间窗口聚合。

### Python 类型签名

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class MetricsSnapshot:
    """指标快照；按时间窗口聚合。"""
    window_start:  datetime          # * 窗口起始
    window_end:    datetime          # * 窗口结束
    sample_count:  int               # * 样本数
    p50_latency_ms: float            # * P50 延迟
    p95_latency_ms: float            # * P95 延迟
    p99_latency_ms: float            # * P99 延迟
    error_rate:    float             # * 错误率（0-1）
    token_usage:   dict[str, int]    # * 模型 token 消耗（按 model_name 统计）
    cost_usd:      float             # * 估算成本（美元）
```

### 磁盘格式与 schema_version

- `disk_format`: `JSON`（时序文件，追加写）
- `schema_version`: `v0.1.0`

### 与 LangChain / LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| `token_usage` | `AIMessage.usage_metadata` | N/A | 引用 LangChain `AIMessage.usage_metadata` 字段 |

### reducer 与不可变约束

- 不可变（`frozen=True`）。

---

## AuditEntry {#schema-audit-entry}

> 1 级章节 18 / 22。审计条目；记录 PII 泄露 / 越权 tool / prompt injection 等事件；宪法第 X 条。
> ⚠️ 警示（FR-043 + FR-043 (a) / Q11 / MC-2.6）：本章节禁止使用 `...` / `<其它枚举>` / `etc.` 等省略号表达未来扩展；扩展接口约定见下方"扩展接口约定"二级小节（MC-2.6 路径 1）。

### Python 类型签名

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Any, Literal

class AuditEntry(BaseModel, frozen=True):
    """审计条目；记录 PII 泄露 / 越权 tool / prompt injection 等事件。"""
    model_config = {"frozen": True}

    entry_id:   str                              # * 条目 ID
    audited_at: datetime                         # * 审计时间
    severity:   Literal['info', 'warn', 'error', 'critical']  # * 严重级别
    category:   Literal[
        'pii_leak',
        'unauthorized_tool',
        'prompt_injection'
    ]                                            # * 安全事件类别（3 个当前候选值）
    actor:      str                              # * 触发者（user / tool / model）
    action:     str                              # * 触发的动作
    target:     str | None = None                # - 作用对象（tool_id / file_path / ...）
    outcome:    str                              # * 'allowed' / 'blocked' / 'redacted' / 'logged'
    evidence:   dict[str, Any]                   # * 证据（脱敏后）
```

### 磁盘格式与 schema_version

- `disk_format`: `JSONL`（一行一个 AuditEntry，仅追加）
- `schema_version`: `v0.1.0`

### 与 LangChain / LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| `actor` | N/A | N/A | 自定义；非 LangChain / LangGraph 原生 |
| `action` | N/A | N/A | 自定义；可引用 `ToolSideEffect` 枚举值 |

### reducer 与不可变约束

- 不可变（`frozen=True`）；审计一旦写入不得修改。

### 扩展接口约定

> MC-2.6 路径 1 落盘形式（FR-043 (a) / Q11）：扩展字段以 `<字段名>_extensibility` 命名约定列出，禁止以 `...` 缩写表达。

- `category_extensibility: list[str] = []`：未来新增的 category 取值应登记到此字段。
  - 当 category 候选值集合需扩展时，由实施者按"schema_version 升版 + 写入 migrators + 更新 Literal 列表"流程操作；扩展点本身在此字段明示登记，避免遗漏。
  - 当前 3 个候选值：`pii_leak` / `unauthorized_tool` / `prompt_injection`。
  - 本约定禁止以省略号占位（如 `category: Literal[..., 'new_category']`）；新增取值必须先扩展本字段，再升 schema_version。
- `severity_extensibility: list[str] = []`：未来新增的 severity 取值应登记到此字段（当前 4 个候选值：`info` / `warn` / `error` / `critical`）。

---

## DoctorReport {#schema-doctor-report}

> 1 级章节 19 / 22。`langagent doctor` 自检报告。

### Python 类型签名

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Any

class DoctorReport(BaseModel, frozen=True):
    """`langagent doctor` 自检报告。"""
    model_config = {"frozen": True}

    report_id:    str                          # * 报告 ID
    generated_at: datetime                     # * 生成时间
    checks:       list[dict[str, Any]]         # * 单项自检结果（check_name / status / detail）
    overall:      str                          # * 'ok' / 'warn' / 'error'
    agent_dir:    str                          # * 被自检的智能体目录
    runtime:      'RuntimeConfigSnapshot'      # * 当时的可序列化 RuntimeConfig 快照（review.md S-2 修复：不含 BaseChatModel）
```

### 磁盘格式与 schema_version

- `disk_format`: `JSON`
- `schema_version`: `v0.2.0`（review.md S-2 修复：`runtime` 改 `RuntimeConfigSnapshot`）

### 与 LangChain / LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| `runtime` | N/A | N/A | 嵌套 `RuntimeConfigSnapshot`（见 `runtime_config_snapshot` schema）；不含 `BaseChatModel` 实例，保证 JSON 序列化 |

### reducer 与不可变约束

- 不可变（`frozen=True`）。

---

## EvalRunResult {#schema-eval-run-result}

> 1 级章节 20 / 22。`eval.runner.run()` 返回值；review.md v0.4.0 M-NEW-1 修复新增；review.md v0.5.0（评审 v0.1.0 §二.A.1 修复）补建 schema 章节。
> 承载 `langagent eval` 子命令一次运行的全部产物（F11 Phase 3 整合点）；与 `EvalReport` 区别：`EvalReport` 是聚合后写入磁盘的报告，`EvalRunResult` 是 runner 内存返回值（额外携带最后一条 task 的 `final_state` 与 `exit_code`，供 F01 dispatch 调 F06 cleanup）。

### Python 类型签名

```python
from dataclasses import dataclass
from langagent.runtime.agent_state import AgentState  # F05 拥有；F11 仅类型注解引用
from langagent.eval.report_aggregator import EvalReport  # F11 拥有

@dataclass(frozen=True)
class EvalRunResult:
    """`eval.runner.run()` 返回值；review.md v0.4.0 M-NEW-1 修复明确。"""
    eval_report: EvalReport                    # * F11 跑完所有 task 后聚合的报告
    final_state: AgentState                    # * 最后一条 task 跑完后的 final state；F01 传给 F06 cleanup()
    exit_code:   int                           # * worst_of(all_failure_exit_codes)；非 0 表示有 task 失败
```

### 磁盘格式与 schema_version

- `disk_format`: 不写盘（仅作 runner 返回值；EvalReport 单独写盘）
- `schema_version`: `v0.1.0`

### 字段语义

| 字段 | 类型 | 必填 | 来源 | 消费方 |
|---|---|---|---|---|
| `eval_report` | `EvalReport` | * | `eval.report_aggregator.aggregate(task_results)` | F01 stdout 输出（format_eval_report_stdout）+ F06 cleanup 写盘 |
| `final_state` | `AgentState` | * | 最后一条 task 跑 main_loop 后的 state | F01 dispatch 传 F06 `cleanup(state=result.final_state, ...)` |
| `exit_code` | `int` | * | `worst_of([每条 task 的 exit_code + [0]])` 仲裁 | F11 runner 内部使用；F01 dispatch **不直接返回**此字段（统一走 cleanup 路径） |

### reducer 与不可变约束

- 不可变（`frozen=True`）；纯值类型，无 reducer。

### 扩展约束

- `EvalRunResult` 是 F11 runner 内部产物，**不跨 feature 边界被持久化**；如需在外部（CLI / API）暴露 exit_code，由 F01 dispatch 调 `exit_handler.cleanup()` 统一返回。
- `final_state` 字段引用 F05 的 `AgentState`；EvalRunner 不修改 final_state，仅传递。

---

## GuardrailPolicy / GuardrailDecision {#schema-guardrail-policy}

> 1 级章节 23 / 23。合并章节，承载 2 个类型（`GuardrailPolicy` + `GuardrailDecision`）；**review.md v2.1.0 P1-4 修复新增**：F09 §3.2 提升为顶层 schema，与宪法第 X 条 1 款"不外发数据"+ 第 IV 条 4 款"本地模型必须可作为默认"对齐——内网 vLLM 默认 allow（满足本地默认需求），公网 endpoint 默认 interrupt（满足不外发数据）。MDA 无对应 schema（`managed-deep-agents-tools.md:81` 用 `interrupt_on={"tool_name": True}` 简单 dict，且 MDA 默认托管运行无内网 / 公网区分需求）。
> **Owning Feature**: F09（v1 完整实现；RuntimeConfig.guardrail_policy 字段由 F03 读 env LANGAGENT_GUARDRAIL_* 注入）
> **Python 文件**: `langagent/cross_cutting/types.py`（原 §3.2 已规划位置）

### Python 类型签名（共用）

```python
from pydantic import BaseModel
from typing import Any
from langagent.protocol.tool_schemas import ToolSideEffect  # F04 拥有

class GuardrailPolicy(BaseModel, frozen=True):
    """护栏策略；F09 guardrail middleware 据此决定是否 interrupt。
    review.md v2.1.0 P1-4 修复：进顶层 schema 清单（25 → 27）；RuntimeConfig.guardrail_policy 持有本类型实例。
    """
    model_config = {"frozen": True}

    enabled:                       bool                                  # * 是否启用护栏（默认 True）
    interrupt_on:                  list[ToolSideEffect]                  # * 触发 interrupt 的 ToolSideEffect 列表（默认覆盖全部敏感操作）
    redact_pii:                    bool = True                           # - PII 脱敏开关（默认 True）
    allow_internal_endpoints:      bool = True                           # **review.md v2.1.0 P1-4 新增**：内网 vLLM endpoint allow 开关（默认 True 避免误伤宪法第 IV 条 4 款本地默认模型）
    internal_endpoint_patterns:    list[str] = []                        # **review.md v2.1.0 P1-4 新增**：hostname glob / IP CIDR 列表（如 `["*.internal.example.com", "10.0.*.*", "192.168.*.*"]`）；用户通过 .env 字段 LANGAGENT_INTERNAL_ENDPOINTS 配置逗号分隔列表

class GuardrailDecision(BaseModel, frozen=True):
    """护栏决策结果；F09 evaluate() 返回值。"""
    model_config = {"frozen": True}

    allow:                   bool                # * 是否允许执行（True = 放行 / False = 拦截）
    interrupt:               bool                # * 是否触发 LangGraph interrupt()（HITL 审批）
    redact:                  bool = False        # - 是否脱敏（红 PII / prompt injection 标注）
    reason:                  str                 # * 决策理由（写入 AuditEntry.action）
    is_internal_endpoint:    bool = False        # **review.md v2.1.0 P1-4 新增**：标记命中内网 endpoint（便于 audit 区分内网 vs 公外）
```

### 磁盘格式与 schema_version（共用）

- `disk_format`: `JSON`（嵌入 `RuntimeConfigSnapshot` 子字段 + `AuditEntry.evidence.policy_snapshot` 字段；不单独写盘）
- `schema_version`: `v0.1.0`

### GuardrailPolicy 与 LangChain / LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| `interrupt_on` | N/A | `interrupt` 触发 | LangGraph `interrupt()` 在 tool 调用前触发，与 ToolSideEffect 标注对齐 |
| `internal_endpoint_patterns` | N/A | N/A | 自定义 glob / CIDR 列表；F09 evaluate() 调 `is_internal()` 函数命中判断 |

### GuardrailPolicy reducer 与不可变约束

- 不可变（`frozen=True`）；构造完成后禁止修改；变更需重建新实例。
- 默认值：`enabled=True` / `interrupt_on=[7 种 ToolSideEffect 全集]` / `redact_pii=True` / `allow_internal_endpoints=True` / `internal_endpoint_patterns=[]`。
- 用户覆盖：通过 `.env` 字段 `LANGAGENT_GUARDRAIL_ALLOW_INTERNAL_ENDPOINTS`（bool）+ `LANGAGENT_INTERNAL_ENDPOINTS`（逗号分隔 glob / CIDR 列表）注入；F03 config_resolve 在解析后用 `config.with_guardrail_policy(parsed_policy)` 重建 RuntimeConfig 实例。

### GuardrailDecision 与 LangChain / LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| `interrupt` | N/A | `interrupt()` 调用 | LangGraph `interrupt()` 在 tool 调用前被 F09 触发；HITL 审批流程 |
| `is_internal_endpoint` | N/A | N/A | 标记命中 `GuardrailPolicy.internal_endpoint_patterns` 的 endpoint；便于 audit 区分 |

### GuardrailDecision reducer 与不可变约束

- 不可变（`frozen=True`）。
- F09 evaluate() 每次返回新实例；AuditEntry 写入时序列化 `evidence.decision = decision.model_dump()`。

### 扩展接口约定

> MC-2.6 路径 1 落盘形式（FR-043 (a) / Q11）：扩展字段以 `<字段名>_extensibility` 命名约定列出，禁止以 `...` 缩写表达。

- `interrupt_on_extensibility: list[str] = []`：未来新增的 ToolSideEffect 取值（ToolSideEffect schema 已扩展约定）应同步扩展 `interrupt_on` 默认值列表。

---

## EvalReport {#schema-eval-report}

> 1 级章节 21 / 22。`langagent eval` 评测报告。

### Python 类型签名

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Any

class EvalReport(BaseModel, frozen=True):
    """`langagent eval` 评测报告。"""
    model_config = {"frozen": True}

    report_id:     str                    # * 报告 ID
    generated_at:  datetime               # * 生成时间
    agent_dir:     str                    # * 被评测的智能体目录
    task_results:  list[dict[str, Any]]   # * 单条任务结果（task_id / passed / actual / expected / detail）
    pass_rate:     float                  # * 通过率（0-1）
    p50_latency_ms: float                 # * P50 延迟
    p95_latency_ms: float                 # * P95 延迟
    token_usage:   dict[str, int]         # * token 消耗
    cost_usd:      float                  # * 估算成本
```

### 磁盘格式与 schema_version

- `disk_format`: `JSON`
- `schema_version`: `v0.1.0`

### 与 LangChain / LangGraph 原生类型映射

| field | langchain_native | langgraph_native | notes |
|---|---|---|---|
| `token_usage` | `AIMessage.usage_metadata` | N/A | 引用 LangChain `AIMessage.usage_metadata` 字段 |

### reducer 与不可变约束

- 不可变（`frozen=True`）。

---

## 交叉引用

> 本节列出 module_schemas.md 对其它 2 份设计文档的相对路径 + 锚点引用（FR-040 / FR-041）。
> 不带 `./` 前缀、不带 `../` 前缀（FR-040）。

### 引用 workflow.md

- 阶段锚点示例：`workflow.md#stage-dir_load`（目录加载阶段，触发 `LoadedAgent` 构建）。
- 阶段锚点示例：`workflow.md#stage-config_resolve`（配置解析阶段，产出 `RuntimeConfig`）。
- 阶段锚点示例：`workflow.md#stage-main_loop`（主循环阶段，引用 `AgentState` reducer）。
- 退出码锚点示例：`workflow.md#exit-code-78`（EX_CONFIG，与 `RuntimeConfig` 校验失败关联）。
- 日志标签锚点示例：`workflow.md#log-tag-la-cross-cutting-audit-write`（AuditEntry 写入）。

### 引用 architecture_modules.md

- 模块锚点示例：`architecture_modules.md#mod-primitives-chat-model-factory`（实例化 `BaseChatModel`，填充 `RuntimeConfig.model`）。
- 模块锚点示例：`architecture_modules.md#mod-protocol-tool-registry`（注册 `ToolSpec`）。
- 模块锚点示例：`architecture_modules.md#mod-cross-cutting-audit-recorder`（写入 `AuditEntry`）。
- 模块锚点示例：`architecture_modules.md#mod-cross-cutting-metrics-collector`（产出 `MetricsSnapshot`）。

### 引用宪法

- `../../.specify/memory/constitution.md#第-VI-条`（Agent Loop 与 State；AgentState 5 字段 reducer）。
- `../../.specify/memory/constitution.md#第-IX-条`（质量诊断能力矩阵；6 类 schema 与 5 项子能力）。
- `../../.specify/memory/constitution.md#第-XII-条`（配置与可观测契约；RuntimeConfig 优先级链 + Span 7 字段）。

---

## 变更日志

| 日期 | 版本 | 修订摘要 | 作者 |
|---|---|---|---|
| 2026-09-14 | v0.1.0 | Feature 00 初版 | 项目维护者 |
| 2026-09-15 | v0.2.0 | review.md S-1 / S-2 修复：<br>- `RuntimeConfig.model` 改 `BaseChatModel \| None = None`；新增 `with_model()` / `with_model_base_url()` 方法；新增占位符校验（review.md m-5）<br>- 新增 `RuntimeConfigSnapshot` schema（1 级章节 3 / 20）<br>- `DoctorReport.runtime` 改 `RuntimeConfigSnapshot`；schema 章节总数 19 → 20、类型 22 → 23 | 评审者 |
| 2026-09-15 | v0.3.0 | review.md 全部 21 个 issue 在 v0.3.0 修复完成后再次校核；版本号与 feature/README.md v0.3.0 同步对齐 | 评审者 |
| 2026-09-15 | v0.4.0 | review.md v0.3.0 M-4 方案 C 修复：<br>- 新增 `## StateReducers {#schema-state-reducers}` 章节（1 级章节 1.5 / 21）；承载 4 个自定义 reducer 函数（`replace_with_merge` / `merge_dict` / `overwrite_or_merge`）<br>- AgentState schema（`#schema-agent-state`）：5 字段 reducer 的 import 路径改为 `from langagent.primitives.state_reducers import ...`；reducer 实现位置列更新为 `langagent/primitives/state_reducers.py`<br>- Schema 总目录章节总数 20 → 21、类型 23 → 24<br>- 1 级章节序号从 `/ 20` 更新为 `/ 21`<br>- CHK-AR-007 同步更新（增加 `state-reducers` / `runtime-config-snapshot` 锚点） | 评审者 |
| 2026-09-15 | v0.5.0 | review.md v0.1.0（feature 评审）§二.A.1 + §四.C-2 / C-3 / C-8 + B.7 修复：<br>- 新增 `## EvalRunResult {#schema-eval-run-result}` 章节（1 级章节 20 / 22）；承载 3 字段 frozen dataclass（`eval_report` / `final_state` / `exit_code`）；review.md v0.4.0 M-NEW-1 在 feature prompt 中引入但未补 schema 章节，本轮修复<br>- 1 级章节序号从 `/ 21` 更新为 `/ 22`；DoctorReport 18 → 19、EvalReport 20 → 21<br>- Schema 总目录章节总数 21 → 22、类型 24 → 25<br>- StateReducers prose "4 个 reducer 函数" 改 "3 个唯一 reducer 函数覆盖 4 个自定义字段"（B.7）<br>- CHK-AR-007 同步更新（增加 `eval-run-result` 锚点） | 评审者 |
