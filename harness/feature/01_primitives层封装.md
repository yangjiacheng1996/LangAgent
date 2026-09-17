# F01 — Primitives 层封装（LangChain / LangGraph 唯一接触面）

> **Feature ID**: F01
> **批次**: 第 1 批（基座）
> **依赖**: 
> - **F02 Phase 1（`cross_cutting_logger` 模块 + `emit(tag, payload)` 接口 + `ALLOWED_TAGS` ≥**46** 项白名单校验）**（**review.md v1.1.0 P0-5 修复后**：F01 通过 `from langagent.cross_cutting.logger import emit` 调用 F02 emit 接口发射 model_adapt 4 个 + graph_compose 5 个 = 9 个 tag。**硬例外单向边**：`primitives_chat_model_factory → cross_cutting_logger` + `primitives_state_graph_builder → cross_cutting_logger` 在 `architecture_modules.md` v2.4.0 依赖矩阵带 →¹ 标记，CHK-AR-021 校验单向性；**review.md v3.0.0 P2-2 修复补充**：logger 是被动接口（仅提供 `emit()` 方法供调用），不反向依赖 F01。F02 Phase 1 与 F01 在第 1 批并行启动，TDD 阶段 F01 mock `emit()` 测试先于 F02 实现通过）
> - **F06（`cross_cutting_stage_guard.py` 模块 + `@cross_cutting_stage_guard_decorator` 装饰器）**（**review.md v2.2.2 P0-1 修复新增**）：F01 在 `chat_model_factory.create()` 入口应用 `@cross_cutting_stage_guard_decorator('model_adapt')` 装饰器，在 `state_graph_builder.build()` 入口应用 `@cross_cutting_stage_guard_decorator('graph_compose')` 装饰器。**硬例外单向边**：`primitives_chat_model_factory → cross_cutting_stage_guard` + `primitives_state_graph_builder → cross_cutting_stage_guard` 在 matrix 带 →¹ 标记，CHK-AR-023 校验装饰器应用。
> - **F04（`cross_cutting_guardrail_middleware.build_middleware`）**（**review.md v2.2.2 P0-2 修复新增**）：F01 §3.4a 步骤 5 在 `state_graph_builder.build()` 内部调用 `build_middleware(policy=RuntimeConfig.guardrail_policy)` 实例化系统护栏 middleware 并注入图。**硬例外单向边**：`primitives_state_graph_builder → cross_cutting_guardrail_middleware` 在 matrix 带 →² 标记，CHK-AR-024 校验单向性。
> **被依赖**: F05 / F03 / F02 / F04 / F08 / F09 / F10 / F12（直接或间接）
> **状态**: 待启动 speckit.specify（review.md v1.1.0 + v2.2.2 修复后；本 feature prompt 已应用 v0.4.0 修复：M-4 方案 C 新增 `primitives_state_reducers` 模块；M-NEW-2 方案 B primitives → logger 硬例外单向边登记；m-NEW-6 importlib 强化；v1.1.0 修复：P0-2 §3.2 + §3.4a 删 compiled_graph 引用；P0-5 §一 依赖列补 F02 Phase 1；**v2.2.2 修复**：P0-1 §3.1 装饰器应用 + §一 依赖列补 F06 cross_cutting_stage_guard；P0-2 §3.4a 步骤 5 + §五 约束 8 硬例外单向边扩 1 条）

---

## 一、Feature 概述

将 LangChain 与 LangGraph 的原生类型封装到 LangAgent 自有 primitives 层。**primitives 层是 LangAgent 与 LangChain / LangGraph 的唯一接触面；其他层严禁直接 import `langchain` / `langgraph` 包**。

本 feature 完成后，LangAgent 启动时能根据 `RuntimeConfig.model_provider` / `model_name` / `model_base_url` 实例化任一 6 种 LLM 后端，并根据 `checkpointer` 字段接入 3 种状态持久化后端，并能根据 `AgentState` + tools + middleware 编译出可执行的 `CompiledStateGraph`。

## 二、必读顶层设计 artefact（宪法第 XV 条）

按顺序通读下列 3 份 artefact，并对本 feature 形成对齐清单：

1. `harness/top_level_design/workflow.md#stage-model_adapt` + `#stage-graph_compose` —— 6 阶段中的第 3、4 阶段，定义输入/输出/失败模式。
2. `harness/top_level_design/architecture_modules.md#mod-primitives-chat-model-factory` + `#mod-primitives-state-graph-builder` + `#mod-primitives-checkpoint-adapter` —— 3 个模块的职责、关键 API、依赖方向、禁止的依赖。
3. `harness/top_level_design/module_schemas.md#schema-runtime-config` + `#schema-agent-state` + `#schema-loaded-agent` + `#schema-middleware-spec` —— 相关 schema 的字段约束与冻结性。

**本 feature 重点对齐的宪法条款**（**review.md v2.2.0 修复 P2-9**）：
- **第 II 条** 技术栈与依赖范围：F01 是 LangAgent 与 LangChain / LangGraph 的唯一接触面；其他层不得直接 `import langchain` / `import langgraph`；
- **第 III 条** LangSmith 剥离：F01 不依赖 LangSmith SDK；6 种 provider 不含 LangSmith 选项；
- **第 IV 条** 模型抽象层：F01 是该条款的核心实施方（6 种 provider + base_url 无硬编码 + 3 种 checkpointer）；
- **第 XIII 条** 禁止项：F01 不硬编码 base_url / 不内网 IP 字面量。

## 三、本 feature 覆盖的范围

### 3.1 模块

| module_id | 关键 API | 行数估算 |
|---|---|---|
| `primitives_chat_model_factory` | `create(config: RuntimeConfig) -> BaseChatModel`（**仅返回 BaseChatModel，不修改 config，不构造新 RuntimeConfig**；RuntimeConfig 重建由 F10 在 langagent run 编排中通过 `config = config.with_model(model)` 完成，**review.md S-1 修复对齐**）**入口应用 `@cross_cutting_stage_guard_decorator('model_adapt', monkeypatch_blacklist=[RuntimeDirLoader.load, RuntimeConfigResolver.resolve])` 装饰器（**review.md v2.2.2 P0-1 修复新增**）—— F06 `cross_cutting/stage_guard.py` 实现，详见 F06 §3.4b** | ~150 |
| `primitives_state_graph_builder` | `build(loaded_agent: LoadedAgent, config: RuntimeConfig, checkpoint: BaseCheckpointSaver) -> CompiledStateGraph`（**review.md S-5 修复**：`checkpoint` 显式作为必传参数，不再由 builder 内部隐式创建；**review.md v0.4.0 M-4 方案 C 修复后**：build() 内部从 `primitives_state_reducers` import reducer 函数并注入到 StateGraph）**入口应用 `@cross_cutting_stage_guard_decorator('graph_compose', monkeypatch_blacklist=[BaseChatModel.__init__, chat_model_factory.create, RuntimeDirLoader.load])` 装饰器（**review.md v2.2.2 P0-1 修复新增**）；build() 步骤 5 实例化系统护栏 middleware（**review.md v2.2.2 P0-2 修复新增**）** | ~210 |
| `primitives_checkpoint_adapter` | `create(config: RuntimeConfig) -> BaseCheckpointSaver` + `close(saver: BaseCheckpointSaver) -> None` | ~120 |
| `primitives_langchain_types`（**review.md M-3 修复新增**） | re-export：`add_messages` / `BaseMessage` / `HumanMessage` / `AIMessage` / `SystemMessage` / `ToolMessage` / `AgentMiddleware` / `StateGraph` / `CompiledStateGraph` / `BaseCheckpointSaver` / `BaseTool` / `@tool` / `interrupt` 等所有 LangChain / LangGraph 原生类型 | ~50 |
| `primitives_state_reducers`（**review.md v0.4.0 M-4 方案 C 修复新增**） | **3 个唯一 reducer 函数**：`replace_with_merge`（用于 `todos` / `scratchpad` 字段）/ `merge_dict`（用于 `files` 字段）/ `overwrite_or_merge`（用于 `context` 字段）；纯函数；覆盖 AgentState 的 4 个自定义字段（`replace_with_merge` 被 `todos` 与 `scratchpad` 共用）；`messages` 字段的 `add_messages` reducer 由 `primitives_langchain_types` re-export 提供 | ~80 |

### 3.2 Schema（仅引用 / 类型注解，不重新定义）

- `RuntimeConfig`：`model_provider` / `model_name` / `model_base_url` / `checkpointer` 字段；**`model` 字段在 F07 产出时为 None**（**review.md S-1 修复**），由 F10 通过 `config.with_model(chat_model_factory.create(config))` 重建。
- `LoadedAgent`：**review.md v1.1.0 P0-2 修复方案 B 后**：5 字段（`agent_dir` / `instructions` / `tool_ids` / `skill_names` / `metadata`），**已删除 `compiled_graph` 字段**；F01 `build()` 仅消费前 5 字段构建图，CompiledStateGraph 由 build() 自身返回给 F10 dispatch 独立持有。
- `AgentState`：作为 StateGraph 的 State 输入。

`MiddlewareSpec` schema 由 F01 拥有（见 §3.4a）；F01 实现 loader + 把 MiddlewareSpec 转译为 LangChain `AgentMiddleware` 实例。

### 3.3 阶段

- 阶段 3 `model_adapt`：根据 `model_provider` 实例化 `BaseChatModel`。`chat_model_factory.create(config)` 仅返回 BaseChatModel；RuntimeConfig 的 `model` 字段填充 + frozen 实例重建由 F10 在 `langagent run` 编排时通过 `config = config.with_model(model)` 完成（**review.md S-1 修复**）。**`chat_model_factory.create()` 入口应用 `@cross_cutting_stage_guard_decorator('model_adapt', monkeypatch_blacklist=[RuntimeDirLoader.load, RuntimeConfigResolver.resolve])` 装饰器（**review.md v2.2.2 P0-1 修复新增**），黑名单严格使用 F06 §3.4 `{#stage-blacklist-table}` 锚点行（model_adapt 黑名单 2 项；`chat_model_factory.create` 不在黑名单——是该阶段合法操作）**。
- 阶段 4 `graph_compose`：根据 State + tools + middleware 编译 `CompiledStateGraph`。checkpointer 由 `primitives_checkpoint_adapter.create(config)` 产生后传入 `state_graph_builder.build()`；F10 dispatch 调用顺序：`checkpoint = primitives_checkpoint_adapter.create(config); graph = primitives_state_graph_builder.build(loaded, config, checkpoint=checkpoint)`（**review.md S-5 修复**：F10 必须显式调用 `checkpoint_adapter.create` 后传给 builder，不再由 builder 内部隐式创建）。**`state_graph_builder.build()` 入口应用 `@cross_cutting_stage_guard_decorator('graph_compose', monkeypatch_blacklist=[BaseChatModel.__init__, chat_model_factory.create, RuntimeDirLoader.load])` 装饰器（**review.md v2.2.2 P0-1 修复新增**）；build() 步骤 5 实例化系统护栏 middleware（**review.md v2.2.2 P0-2 修复新增**）**。

#### 3.3.1 model_adapt / graph_compose 阶段日志发射（**review.md v0.3.0 S-1 修复新增职责**）

F01 是 primitives 层唯一接触 LangChain / LangGraph 的模块，因此**也是 model_adapt / graph_compose 阶段日志标签的发射方**（workflow.md 日志标签表 9 个 tag 归属 F01）。F01 通过 `from langagent.cross_cutting.logger import emit` 调用 F02 的 `emit()` 接口（**不直接 import `langchain` / `langgraph` 之外的其它 LangAgent 模块**，但允许 import cross_cutting 层 logger；primitives 层依赖 cross_cutting 层的 logger 接口属于"低层依赖高层"——本项目 primitives 层是 LangChain / LangGraph 的唯一接触面，而 cross_cutting 层 logger 是基础设施，依赖方向在 `architecture_modules.md` 隐式允许）。

具体发射点：

| 标签 | 触发时机 | 位置 |
|---|---|---|
| `la.runtime.model_adapt.start` | `chat_model_factory.create()` 入口 | F01 `create()` 第一行 |
| `la.runtime.model_adapt.endpoint_probe` | endpoint 连通性探测前后 | F01 `create()` 内部（如 OpenAI protocol 的 `/models` 列表探测） |
| `la.runtime.model_adapt.ok` | `chat_model_factory.create()` 成功返回前 | F01 `create()` 出口（return 前） |
| `la.runtime.model_adapt.fail` | `chat_model_factory.create()` 异常路径 | F01 `create()` 异常捕获（任何 `ProviderUnsupportedError` / `AuthFailedError` / `EndpointUnreachableError` 抛出前） |
| `la.runtime.graph_compose.start` | `state_graph_builder.build()` 入口 | F01 `build()` 第一行 |
| `la.runtime.graph_compose.middleware_bind` | `build()` middleware 步骤前后 | F01 `build()` 注入 `AgentMiddleware` 实例前后 |
| `la.runtime.graph_compose.tool_bind` | `build()` tool 步骤前后 | F01 `build()` 注入 `BaseTool` 实例前后 |
| `la.runtime.graph_compose.ok` | `state_graph_builder.build()` 成功返回前 | F01 `build()` 出口（return 前） |
| `la.runtime.graph_compose.fail` | `state_graph_builder.build()` 异常路径 | F01 `build()` 异常捕获（任何 `GraphCompileError` / `ToolBindingError` 抛出前） |

> **删除 review.md v0.3.0 之前的"不实现日志"声明**：F01 §六 原写"不实现 Event / Span / Metrics 写入；本 feature 不打日志标签，只返回结果"，违反 workflow.md 日志标签表对 9 个 tag 的发射要求。**review.md v0.3.0 S-1 修复后**：F01 必须在 model_adapt / graph_compose 两个阶段发射上述 9 个 tag。F02 提供 `emit()` 接口 + **46** 项 tag 白名单校验；F01 通过 import `from langagent.cross_cutting.logger import emit` 调用。

### 3.4a Middleware 加载协议（MiddlewareSpec 由 F01 拥有）

F01 是 `MiddlewareSpec` schema 的实际拥有者与消费者（F05 prompt §3.2 仅引用 schema 定义，不实现加载）。`primitives_state_graph_builder.build()` 的 middleware 加载流程：

1. 读 `agent_dir/middleware/<name>.py`（**review.md v1.1.0 P0-2 修复后**：不再依赖 `LoadedAgent.compiled_graph`；中间件来源由 `loaded_agent.agent_dir` 路径解析得出）。**严格遵循宪法第 V 条 + F05 / F06 约束**：必须用 `importlib.util.spec_from_file_location()` + `module_from_spec()`；**严禁 `sys.path.insert()` 污染 sys.path**；**review.md v0.4.0 m-NEW-6 修复后**强化 wording）。**review.md v1.0.0 P2-9 修复新增命名空间约定**：`spec = importlib.util.spec_from_file_location(f"langagent_dynamic_middleware_{name}", path)`，使用 unique 命名空间避免与其它模块冲突；loader 加载完成后负责清理 `sys.modules` 中对应键（避免 `spec_from_file_location` 复用同一 name 时静默命中旧模块）。
   - **sys.modules 清理策略（review.md v2.2.0 P2-4 修复新增，与 F05 同步）**：F01 middleware_loader 在 `state_graph_builder.build()` 返回前调 `sys.modules.pop(f"langagent_dynamic_middleware_{name}", None)`（每个 middleware 单独清理）；命名空间前缀 `langagent_dynamic_middleware_` 与 F05 tool_loader 的 `langagent_dynamic_tool_` 不同，**避免 tool / middleware 同名（如 `tools/echo.py` 与 `middleware/echo.py`）时冲突**。
   - 进程退出前由 F09 cleanup 兜底扫描：清空 `sys.modules` 中所有前缀 `langagent_dynamic_` 的 entry（详见 F05 §3.4 + F09 §3.3 关闭顺序）。
   - 新增测试 `test_middleware_loader_cleans_sys_modules_on_build`：断言 build 返回后 `langagent_dynamic_middleware_*` 全部从 `sys.modules` 移除；F01 §四.2 测试配套。
2. 解析每个 middleware 模块的 `MIDDLEWARE_SPEC: MiddlewareSpec` 模块级常量（开发者按 schema 声明）。
3. 校验 `MiddlewareSpec.hook_points` 仅含 LangChain `AgentMiddleware` 协议支持的 6 个值之一。
4. 把 `MiddlewareSpec` 转译为 LangChain `AgentMiddleware` 实例（按 `priority` 升序注入到图）。
5. **实例化系统护栏 middleware（**review.md v2.2.2 P0-2 修复新增**）**：调用 `cross_cutting_guardrail_middleware.build_middleware(policy=RuntimeConfig.guardrail_policy)` 得到系统 `AgentMiddleware` 实例，按 `priority` 升序与步骤 4 的 USER middleware 一同注入图。**系统护栏无需 `agent_dir/middleware/` 目录存在；缺失时不报错**——`RuntimeConfig.guardrail_policy` 非 None 时（由 F07 §三.4 注入；详见 `module_schemas.md#schema-guardrail-policy`），F01 build() 必须实例化 guardrail 中间件；为 None 时跳过此步骤（理论上不会发生，因 F07 产出的 RuntimeConfig 总有 guardrail_policy；本兜底仅为 schema 边界情况）。

   **F04 `build_middleware` 接口 stub 预放（**review.md v2.4.0 P2-1 修复**）**：F01 处于第 1 批，F04 处于第 3 批，存在跨批次硬例外单向边。F04 路径 `langagent/cross_cutting/guardrail_middleware.py` 在 F01 启动前需预放 1 段 Protocol stub（**v2.4.0 P2-1 修复明确**），保证 F01 TDD Red 阶段能 import 接口：
   ```python
   # F04 拥有文件，由 F06 在 F01 启动前 stub 到位；F04 Phase 1 填充实现
   from typing import Protocol
   from langagent.primitives.langchain_types import AgentMiddleware
   from langagent.cross_cutting.types import GuardrailPolicy

   class BuildMiddlewareProtocol(Protocol):
       """F01 跨批次依赖的硬例外单向接口；F04 实现；primitives 不反向依赖。"""
       def __call__(self, policy: GuardrailPolicy) -> AgentMiddleware: ...

   # 模块级单例；F04 实现填充
   build_middleware: BuildMiddlewareProtocol
   ```
   该 stub 由 F06 在首批实现 `langagent/cross_cutting/stage_guard.py` 时同步预放（在 F06 §七 deliverable 中说明）；F04 Phase 1 speckit.specify 时填充 `build_middleware` 实际实现（构造 `AgentMiddleware` 实例 + 注册 interrupt hook + 注册 audit_recorder.write）。F01 TDD `test_build_instantiates_guardrail_middleware` 阶段用 `unittest.mock.patch('langagent.cross_cutting.guardrail_middleware.build_middleware')` 验证 F01 build() 步骤 5 调用接口即可。

   **依赖方向约束（review.md v2.2.2 P0-2 修复后正式化）**：`primitives_state_graph_builder → cross_cutting_guardrail_middleware` 是 `architecture_modules.md` v2.4.0 依赖矩阵新增的第 3 条硬例外单向边（带 →² 标记，与 2 条 `→¹` logger 边 + 6 条 `→¹` stage_guard 边 + 2 条 `→²` F08 build_doctor_probes 边合计 11 条硬例外单向边）；CHK-AR-024 校验硬例外单向性（cross_cutting_guardrail_middleware 不得反向依赖 primitives）。guardrail_middleware 是被动接口（F04 提供 `build_middleware(policy)` 构造方法），不反向依赖 F01。

> F01 prompt §3.2 把 `MiddlewareSpec` 列为"类型注解引用"；本节明确 F01 拥有该 schema 的 loader 实现 + 步骤 5 系统护栏实例化入口。F05 仅在 §3.2 文案层面引用该 schema，不重复实现。

> **review.md v0.4.0 m-NEW-6 修复后**：F01 §四.2 测试增加 `test_middleware_loader_no_sys_path_pollution`（仿 F05 §四.2 `test_tool_dynamic_import_no_sys_path_pollution`）；断言测试前后 `sys.path` 长度不变。

### 3.4 必须支持的 model_provider（6 种，同等优先级，**review.md S-4 修复后无硬编码 base_url**）

| `model_provider` 值 | LangChain 类 | 关键参数（全部从 env / RuntimeConfig 读取，**不硬编码任何 URL**） |
|---|---|---|
| `openai` | `langchain_openai.ChatOpenAI` | `model=RuntimeConfig.model_name`；API key 来自 env `OPENAI_API_KEY`；base_url 由 LangChain ChatOpenAI 默认（`https://api.openai.com/v1`） |
| `anthropic` | `langchain_anthropic.ChatAnthropic` | `model=RuntimeConfig.model_name`；env `ANTHROPIC_API_KEY`；base_url 由 LangChain ChatAnthropic 默认 |
| `google` | `langchain_google_genai.ChatGoogleGenerativeAI` | `model=RuntimeConfig.model_name`；env `GOOGLE_API_KEY`；base_url 由 LangChain ChatGoogleGenerativeAI 默认 |
| `deepseek` | `langchain_openai.ChatOpenAI`（OpenAI 协议兼容） | `base_url=RuntimeConfig.model_base_url`（**review.md v2.2.0 P2-8 修复统一**：不再读 env `DEEPSEEK_BASE_URL`，改读 `RuntimeConfig.model_base_url`，与 `openai-compatible` 行一致；**不硬编码** `https://api.deepseek.com`）；env `DEEPSEEK_API_KEY` |
| `zhipu` | `langchain_openai.ChatOpenAI`（OpenAI 协议兼容） | `base_url=RuntimeConfig.model_base_url`（**review.md v2.2.0 P2-8 修复统一**：不再读 env `ZHIPUAI_BASE_URL`）；env `ZHIPUAI_API_KEY` |
| `openai-compatible` | `langchain_openai.ChatOpenAI` | `base_url=RuntimeConfig.model_base_url`（**review.md M-1 修复**：不得为 `localhost` / `127.0.0.1` / 内网 IP 字面量；空则抛 `RequiredFieldMissingError`） |

> **本地 OpenAI Compatible 是默认模型**（宪法第 IV 条 4 款）；回归测试必须在 vLLM 部署的 Qwen3.8-27B 上能跑通。
> **base_url 来源优先级（**review.md v2.2.0 P2-8 修复后统一**）**：所有 6 种 model_provider 的 base_url 都从 **`RuntimeConfig.model_base_url`** 读取（不再从 env 专用字段读）；`RuntimeConfig.model_base_url` 的优先级链在 F07 §3.4 维护——CLI `--model-base-url` > env `MODEL_BASE_URL`（**v0.3.0 S-4 修复后**：F07 §3.4 表按 provider 分流 env 字段 `DEEPSEEK_BASE_URL` / `ZHIPUAI_BASE_URL` / `OPENAI_BASE_URL`；F01 读取的是已合并的 `RuntimeConfig.model_base_url`，provider 字段处理由 F07 完成）> 内置默认（None）> 必填校验。**所有 provider 共用同一份 base_url 优先级链**，避免 P2-8 描述的 `deepseek`/`zhipu` 与 `openai-compatible` 不一致问题。
> **迁移注意（**review.md v2.2.0 P2-8 修复后**）**：原 v0.3.0 S-4 修复时 `deepseek` / `zhipu` 直接读 env 字段；本修复统一改为读 `RuntimeConfig.model_base_url`，由 F07 在优先级链阶段合并 provider 特定 env 字段 → `model_base_url` 统一字段。F06 `.env.example` 仍保留 `DEEPSEEK_BASE_URL` / `ZHIPUAI_BASE_URL` 字段（F07 读），但 F01 不直接读。

### 3.5 必须支持的 checkpointer（3 种）

| `checkpointer` 值 | LangGraph 类 | 关闭方式 |
|---|---|---|
| `memory` | `MemorySaver`（langgraph 自带） | 无需关闭（内存） |
| `sqlite` | `SqliteSaver`（langgraph-checkpoint-sqlite） | 调用 `saver.close()` |
| `postgres` | `PostgresSaver`（langgraph-checkpoint-postgres） | 调用 `saver.close()` |

## 四、TDD 测试用例先行（Red 阶段先写这些）

> 下列测试用例如失败 → 实现 → 通过。先 Red 后 Green 再 Refactor（宪法第 VIII 条）。

### 4.1 `primitives_chat_model_factory` 测试

- [ ] `test_create_openai_default`：仅指定 `model_provider="openai"`，从 env `OPENAI_API_KEY` 取 key → 返回 `ChatOpenAI` 实例且 `.model_name` 与 config 一致。
- [ ] `test_create_anthropic_default`：仅指定 `model_provider="anthropic"`，从 env `ANTHROPIC_API_KEY` 取 key → 返回 `ChatAnthropic` 实例。
- [ ] `test_create_google_default`：仅指定 `model_provider="google"`，从 env `GOOGLE_API_KEY` 取 key → 返回 `ChatGoogleGenerativeAI` 实例。
- [ ] `test_create_deepseek_default`（**review.md S-4 修复后**）：`model_provider="deepseek"` + env `DEEPSEEK_BASE_URL=https://api.deepseek.com` → 返回 `ChatOpenAI` 且 `base_url` 字段一致。
- [ ] `test_create_deepseek_base_url_required`（**review.md S-4 修复新增**）：`model_provider="deepseek"` 但无 env `DEEPSEEK_BASE_URL` → 抛 `RequiredFieldMissingError`，退出码 5。
- [ ] `test_create_zhipu_default`（**review.md S-4 修复后**）：`model_provider="zhipu"` + env `ZHIPUAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4/` → 返回 `ChatOpenAI` 且 `base_url` 字段一致。
- [ ] `test_create_zhipu_base_url_required`（**review.md S-4 修复新增**）：`model_provider="zhipu"` 但无 env `ZHIPUAI_BASE_URL` → 抛 `RequiredFieldMissingError`，退出码 5。
- [ ] `test_create_openai_compatible_local`：本地 vLLM，`model_provider="openai-compatible"`、`model_base_url="http://10.0.0.5:8000/v1"`、`model_name="qwen3-8b"` → 返回 `ChatOpenAI` 且 `base_url` 字段一致。
- [ ] `test_create_openai_compatible_base_url_required`（**review.md M-1 修复新增**）：`model_provider="openai-compatible"` 但 `model_base_url` 为 None → 抛 `RequiredFieldMissingError`，退出码 5。
- [ ] `test_create_provider_unsupported`：`model_provider="unknown"` → 抛 `ProviderUnsupportedError`，退出码 78（EX_CONFIG）。
- [ ] `test_create_api_key_missing`：缺少对应 env → 抛 `AuthFailedError`，退出码 78。
- [ ] `test_create_endpoint_unreachable`：`model_base_url` 指向不可达地址 → 抛 `EndpointUnreachableError`，退出码 70（EX_SOFTWARE）。
- [ ] `test_create_preserves_frozen_runtime_config`：调用 `create()` 前后 `RuntimeConfig` 实例 `id()` 不变（冻结性验证）。

### 4.1b `primitives_chat_model_factory` 阶段日志发射测试（**review.md v0.3.0 S-1 修复新增**）

F01 在 `chat_model_factory.create()` 入口 / 出口 / 异常路径 / endpoint_probe 时刻发射 4 个 `la.runtime.model_adapt.*` tag（详见 §3.3.1）。

- [ ] `test_create_emits_model_adapt_start_log`：mock F02 `cross_cutting_logger.emit` → 调用 `create()` 入口收到 `la.runtime.model_adapt.start` 日志，payload 含 `model_provider` / `model_name`。
- [ ] `test_create_emits_model_adapt_endpoint_probe_log`：mock `chat_model_factory.create()` 内部 endpoint_probe 前后 → 收到 `la.runtime.model_adapt.endpoint_probe` 日志，payload 含 `endpoint` / `probe_result`。
- [ ] `test_create_emits_model_adapt_ok_log`：成功 create → 出口前收到 `la.runtime.model_adapt.ok` 日志，payload 含 `latency_ms` / `model_class`。
- [ ] `test_create_emits_model_adapt_fail_log_on_provider_unsupported`：mock 抛 `ProviderUnsupportedError` → 异常捕获路径收到 `la.runtime.model_adapt.fail` 日志，payload 含 `error_type` / `error_message`。
- [ ] `test_create_emits_model_adapt_fail_log_on_endpoint_unreachable`：mock 抛 `EndpointUnreachableError` → 同上。
- [ ] `test_create_emits_model_adapt_fail_log_on_auth_failed`：mock 抛 `AuthFailedError` → 同上。
- [ ] `test_create_log_tags_in_whitelist`：上述 4 个 tag 全部在 F02 `ALLOWED_TAGS` 集合（≥**46** 项）中（验证不抛 `UnknownLogTagError`）。

### 4.1a `primitives_langchain_types` re-export 测试（**review.md M-3 修复新增**）

- [ ] `test_langchain_types_module_exists`：`from langagent.primitives.langchain_types import add_messages, BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage, AgentMiddleware, StateGraph, CompiledStateGraph, BaseCheckpointSaver, BaseTool, tool, interrupt` 全部成功。
- [ ] `test_langchain_types_no_re_export_of_langchain`：除 primitives 层外，runtime / cross_cutting / cli 层模块的 `ast.Import` 解析中**不应出现** `from langchain` 或 `from langgraph` 字面量（grep 验证）。
- [ ] `test_state_graph_builder_uses_re_exported_types`：`primitives_state_graph_builder.build()` 内部 import 用 `from langagent.primitives.langchain_types import StateGraph`，不直接 `from langgraph.graph import StateGraph`。

#### 4.1c `primitives_chat_model_factory` 装饰器应用测试（**review.md v2.2.2 P0-1 修复新增**）

- [ ] `test_create_uses_stage_guard_decorator`（静态检查装饰器应用）：`ast` 解析 `langagent/primitives/chat_model_factory.py` → `create()` 函数顶部有 `@cross_cutting_stage_guard_decorator('model_adapt', ...)` 装饰器；装饰器参数 keyword-only `monkeypatch_blacklist` 含 `[RuntimeDirLoader.load, RuntimeConfigResolver.resolve]`（严格匹配 F06 §3.4 `{#stage-blacklist-table}` model_adapt 行；**不包含 `chat_model_factory.create`**——是该阶段合法操作）。
- [ ] `test_create_stage_guard_blocks_violations_runtime`：mock `RuntimeDirLoader.load` → `create()` 内部尝试调用 → 抛 `StageCapabilityViolationError`。
- [ ] `test_create_stage_guard_blocks_violations_config_resolver`：mock `RuntimeConfigResolver.resolve` → `create()` 内部尝试调用 → 抛 `StageCapabilityViolationError`。
- [ ] `test_create_stage_guard_allows_chat_model_init`（兜底）：`create()` 内部 `BaseChatModel.__init__` 调用**不被拦截**（mock 验证 `BaseChatModel.__init__` 可被调用）；验证装饰器未误拦截合法操作。

### 4.2 `primitives_state_graph_builder` 测试

- [ ] `test_build_minimal_agent_state`：传入最小 `AgentState`（仅 `messages`）→ 编译成功且 `CompiledStateGraph` 可 `invoke({"messages": [HumanMessage("hi")]})`。
- [ ] `test_build_with_tools`：`LoadedAgent.tool_ids` 含 1 个 fake tool → 图节点含 `tools` 节点且能调用 tool。
- [ ] `test_build_with_middleware`：传入 `AgentMiddleware` 实例 → 编译后中间件的 hook 实际触发（用 spy mock 验证）。
- [ ] `test_build_with_checkpointer`：`RuntimeConfig.checkpointer="memory"` → 编译后图具备 state 持久化能力（用 thread_id 二次 invoke 验证历史）。
- [ ] `test_build_state_reducer_messages`：连续两次追加 `HumanMessage` → `state["messages"]` 长度增加且不覆盖历史（验证 `add_messages` reducer）。
- [ ] `test_build_state_reducer_todos`：连续两次覆盖式写入 `todos` → 每次都按 reducer 规则合并，不允许无脑覆盖（FR-037）。
- [ ] `test_build_compile_failed`：传入非法 schema（如 `messages` 类型错误）→ 抛 `GraphCompileError`，退出码 70。
- [ ] `test_build_returns_compiled_state_graph`：返回值类型严格为 `langgraph.graph.CompiledStateGraph`，不是 `StateGraph`。
- [ ] **`test_build_uses_stage_guard_decorator`**（**review.md v2.2.2 P0-1 修复新增**：静态检查装饰器应用）：`ast` 解析 `langagent/primitives/state_graph_builder.py` → `build()` 函数顶部有 `@cross_cutting_stage_guard_decorator('graph_compose', ...)` 装饰器；装饰器参数 keyword-only `monkeypatch_blacklist` 含 `[BaseChatModel.__init__, chat_model_factory.create, RuntimeDirLoader.load]`（严格匹配 F06 §3.4 `{#stage-blacklist-table}` graph_compose 行）。
- [ ] **`test_build_stage_guard_blocks_violations_chat_model_init`**：`build()` 内部尝试调用 `BaseChatModel.__init__` → 抛 `StageCapabilityViolationError`。
- [ ] **`test_build_stage_guard_blocks_violations_chat_model_create`**：`build()` 内部尝试调用 `chat_model_factory.create` → 抛 `StageCapabilityViolationError`。
- [ ] **`test_build_stage_guard_allows_state_graph_compile`**（兜底）：`build()` 内部 `StateGraph.compile` 调用**不被拦截**（mock 验证）；验证装饰器未误拦截合法操作。

### 4.2b `primitives_state_graph_builder` 阶段日志发射测试（**review.md v0.3.0 S-1 修复新增**）

F01 在 `state_graph_builder.build()` 入口 / middleware_bind / tool_bind / 出口 / 异常路径发射 5 个 `la.runtime.graph_compose.*` tag（详见 §3.3.1）。

- [ ] `test_build_emits_graph_compose_start_log`：mock F02 logger → 调用 `build()` 入口收到 `la.runtime.graph_compose.start` 日志，payload 含 `agent_dir` / `middleware_count` / `tool_count`。
- [ ] `test_build_emits_graph_compose_middleware_bind_log`：mock `build()` 注入 AgentMiddleware 前后 → 收到 `la.runtime.graph_compose.middleware_bind` 日志，payload 含 `middleware_id` / `priority` / `hook_points`。
- [ ] `test_build_emits_graph_compose_tool_bind_log`：mock `build()` 注入 BaseTool 前后 → 收到 `la.runtime.graph_compose.tool_bind` 日志，payload 含 `tool_id` / `side_effects`。
- [ ] `test_build_emits_graph_compose_ok_log`：成功 build → 出口前收到 `la.runtime.graph_compose.ok` 日志，payload 含 `latency_ms` / `checkpointer_type`。
- [ ] `test_build_emits_graph_compose_fail_log_on_compile_error`：mock 抛 `GraphCompileError` → 异常路径收到 `la.runtime.graph_compose.fail` 日志。
- [ ] `test_build_emits_graph_compose_fail_log_on_tool_binding_error`：mock 抛 `ToolBindingError` → 同上。
- [ ] `test_build_log_tags_in_whitelist`：上述 5 个 tag 全部在 F02 `ALLOWED_TAGS` 集合（≥**46** 项）中。
- [ ] **`test_build_instantiates_system_guardrail_middleware`**（**review.md v2.2.2 P0-2 修复新增**）：mock `cross_cutting_guardrail_middleware.build_middleware` → 调用 `build()` 时该函数被调用 1 次，参数 = `policy=RuntimeConfig.guardrail_policy`；返回的 `AgentMiddleware` 实例被加入 graph 的 middleware 列表；mock F04 产出的 `AgentMiddleware` 实例被注入到 `CompiledStateGraph` 编译产物中。
- [ ] **`test_build_skips_guardrail_when_policy_is_none`**（**review.md v2.2.2 P0-2 修复新增兜底测试**）：构造 `RuntimeConfig.guardrail_policy=None`（schema 边界情况）→ `build()` 不调用 `build_middleware`；graph 编译成功；仅 USER middleware 注入。验证 schema 边界兜底逻辑。
- [ ] **`test_build_imports_guardrail_via_cross_cutting_path`**（**review.md v2.2.2 P0-2 修复新增静态检查**）：grep `langagent/primitives/state_graph_builder.py` import 块 → 应包含 `from langagent.cross_cutting.guardrail_middleware import build_middleware`；不应包含 `from langagent.cross_cutting.stage_guard import ...`（**review.md v2.2.2 P0-1 修复后**：stage_guard 在 cross_cutting 层，F01 primitives 通过 cross_cutting_stage_guard 调用而非通过 cross_cutting_guardrail_middleware 调用；详见 F01 §3.1 装饰器应用）。

### 4.3 `primitives_checkpoint_adapter` 测试

- [ ] `test_create_memory`：返回 `MemorySaver` 实例。
- [ ] `test_create_sqlite_in_tmp`：传入临时 sqlite 路径 → 返回 `SqliteSaver` 且可正常持久化。
- [ ] `test_create_postgres_url`：传入 DSN → 返回 `PostgresSaver`（用 mock 避免真连 DB）。
- [ ] `test_create_unsupported`：`checkpointer="redis"` → 抛 `CheckpointTypeUnsupportedError`，退出码 78。
- [ ] `test_close_memory`：memory saver 调用 `close()` 不抛异常。
- [ ] `test_close_sqlite`：sqlite saver 调用 `close()` 后文件锁释放。
- [ ] `test_close_postgres`：postgres saver 调用 `close()` 触发底层 pool 关闭（用 mock 验证）。
- [ ] `test_close_failed`：底层 close 抛异常 → 上层 `close()` 不静默吞掉，重新抛出。

## 五、关键约束（宪法 + 顶层设计硬约束）

1. **不依赖 LangSmith**：primitives 层只 import `langchain` / `langgraph` / `langchain_*` / `langgraph_*` 系列包；不得 `from langsmith import ...`（宪法第 III 条 1 款）。
2. **不硬编码 API key / endpoint**：全部从 env / config 取；测试用 `.env.test` 或 monkeypatch（宪法第 XIII 条 2 款）。
3. **不引入 MDA 代码**：不得 `pip install managed-deepagents` 或 `from managed_deep_agents import ...`（宪法第 III 条 5 款）。
4. **TDD 刚性**：先写失败测试，再写实现；CI 必跑 lint + 类型 + 单测（宪法第 VIII 条）。
5. **不可 mock LangGraph 行为**：图必须真的跑起来；可以用 fake model 替代 LLM 调用（宪法第 VIII 条 4 款）。
6. **OpenAI Compatible 优先**：所有 6 种 provider 共用同一份测试用例模板；本地 vLLM 是基准模型。
8. **依赖方向（review.md v0.4.0 M-NEW-2 方案 B + v2.2.2 P0-2 修复后正式化）**：primitives 层**不直接依赖** runtime / cli / protocol / cross_cutting 中的业务模块（`architecture_modules.md` 模块依赖矩阵）。**硬例外单向边（3 条，全部带 →¹ 标记）**：
   - `primitives_chat_model_factory → cross_cutting_logger`：F01 发射 4 个 model_adapt tag 用 `emit()` 接口
   - `primitives_state_graph_builder → cross_cutting_logger`：F01 发射 5 个 graph_compose tag 用 `emit()` 接口
   - **`primitives_state_graph_builder → cross_cutting_guardrail_middleware`（review.md v2.2.2 P0-2 修复新增）**：F01 §3.4a 步骤 5 实例化系统护栏 middleware
   
   这 3 条边属"primitives → cross_cutting 基础设施 / 安全 middleware 注入"的硬例外单向边，**已显式登记在 architecture_modules.md v2.3.0 依赖矩阵**（带 →¹ 标记）；**CHK-AR-021** 校验 `primitives_* → cross_cutting_logger` 单向性；**CHK-AR-024** 校验 `primitives_state_graph_builder → cross_cutting_guardrail_middleware` 单向性（cross_cutting_guardrail_middleware 不得反向依赖 primitives）。logger 与 guardrail_middleware 都是被动接口，不反向依赖 primitives。其它 cross_cutting 模块（metrics_collector / audit_recorder / event_bus_protocol / **stage_guard**）仍禁止依赖。
9. **禁止 `print` / `console.log`**：调试信息必须走 `cross_cutting_logger.emit("la.runtime.model_adapt.ok", {...})`（宪法第 XIII 条 7 款）。
10. **第 XV 条对齐清单**：本 feature 必须显式声明与宪法第 II 条（技术栈）/ 第 III 条（LangSmith 剥离）/ 第 IV 条（模型抽象）/ 第 VI 条（Agent Loop）/ 第 XIII 条（Hard No）的逐项对齐或偏离声明；偏离项必须标注 RFC 文件路径。

## 六、本 feature 不包含（避免 1+1>2）

- 不实现 CLI 入口（→ F10）。
- 不实现 `LoadedAgent` 构造（→ F06）。
- 不实现 `RuntimeConfig` 优先级链合并（→ F07；本 feature 只读已冻结的 config）。
- 不实现 SkillSpec / ToolSpec 加载（→ F05）。
- 不实现 Event / Span 整体框架写入（→ F03 / F02；F01 仅按 §3.3.1 表发射 9 个阶段 tag，不负责 Event 总线本身或 Span 持久化）；**review.md v2.1.0 P3-2 修复**：F01 §3.3.1 9 个阶段 tag 发射走 F02 `cross_cutting_logger.emit()` 接口；F01 不持有 logger 实现，仅调用其 `emit()` 公共 API。
- 不实现 `@cross_cutting_stage_guard_decorator` 装饰器实现（→ F06 `langagent/cross_cutting/stage_guard.py`；**review.md v2.2.2 P0-1 修复后**：F01 仅在 `chat_model_factory.create()` 与 `state_graph_builder.build()` 入口**应用**装饰器实施 model_adapt / graph_compose 阶段能力边界，不持有装饰器实现）。
- 不实现 `cross_cutting_guardrail_middleware.build_middleware` 实现（→ F04；**review.md v2.2.2 P0-2 修复后**：F01 §3.4a 步骤 5 仅**调用** `build_middleware(policy=RuntimeConfig.guardrail_policy)` 实例化系统护栏，不持有 middleware 构造实现）。
- 不实现 AuditEntry 写入（→ F04）。
- 不实现 ReAct 主循环驱动（→ F08；本 feature 只 `build()` 不 `invoke()`）。
- 不实现退出码与退出清理（→ F09）。
- 不实现 EvalTaskSpec 与 grader（→ F11）。
- 不实现 v1 预留 schema 类型（→ F13）。
- 不实现 PyInstaller 打包（→ F12）。

## 七、Deliverable 清单（实现完成后应有）

- [ ] `langagent/primitives/chat_model_factory.py` + `state_graph_builder.py` + `checkpoint_adapter.py` + `langchain_types.py`（**review.md M-3 修复新增**）+ **`state_reducers.py`**（**review.md v0.4.0 M-4 方案 C 修复新增**：4 个 reducer 函数实现）5 个模块。
- [ ] 单元测试 `tests/primitives/test_chat_model_factory.py` + `test_state_graph_builder.py` + `test_checkpoint_adapter.py` + `test_langchain_types.py`，至少 **42 个测试用例**（review.md v0.3.0 S-1 修复后增补：原 28 个 + §4.1b 7 个 model_adapt 日志发射测试 + §4.2b 7 个 graph_compose 日志发射测试 = 42 个）。
- [ ] `tests/fixtures/openai_compatible_local/`：本地 vLLM 最小可用测试夹具（仅在测试网可达时跑）。
- [ ] 类型注解完整；`mypy --strict` 通过。
- [ ] `pyproject.toml` 增加 `langchain` / `langgraph` / `langchain-openai` / `langchain-anthropic` / `langchain-google-genai` / `langgraph-checkpoint-sqlite` / `langgraph-checkpoint-postgres` 等依赖（按需最小集）。
- [ ] 本 feature 的 `spec.md` / `plan.md` / `tasks.md` 顶部显式引用宪法第 XV 条："已对齐第 XV 条 / 对齐清单见 `<path>`"。

## 八、开发顺序提示

F01 是批次 1，开发顺序：

1. **第一子步**：`primitives_chat_model_factory`（无图依赖，纯模型实例化）。
2. **第二子步**：`primitives_checkpoint_adapter`（独立）。
3. **第三子步**：`primitives_state_graph_builder`（依赖前两者类型注解）。

> 不要先写 graph_compose：图构造依赖 `AgentState` schema；`AgentState` 在 module_schemas.md 已冻结为 TypedDict，可以直接 import，但测试时建议同时 stub 一个最小 AgentState fixture 避免反向依赖。

## 九、与其它 feature 的边界

- 后续 F05 会在 `graph_compose` 阶段把 `protocol_tool_registry` 注册的 `BaseTool` 实例传入 `state_graph_builder.build(loaded_agent, config)`；F01 必须在 `LoadedAgent.tool_ids` 列表里能拿到对应 BaseTool 实例。F01 本阶段可在测试中自己构造假 `BaseTool`。
- F04 的 `cross_cutting_guardrail_middleware` 在 F01 之后开发，会 import `langchain.agents.middleware.AgentMiddleware`；F01 应确认 primitives 层对该协议的类型注解可用。