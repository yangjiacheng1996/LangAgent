# LangAgent 宪法（First Constitution）

> 本文件是 LangAgent 项目的最高级别约束文件。任何规范（spec）、方案（plan）、任务（task）、代码改动在与之冲突时，均以本宪法为准。修改本宪法需走"第 XIV 条 宪法修订程序"。

---

## 第 I 条　项目身份与边界

1. **LangAgent 是一款"开箱即用的通用型智能体产品"，不是 SDK，不是智能体开发框架。**
   - 不发布 `langagent` Python 包供第三方 import。
   - 不向用户提供可编程 API 来"构造智能体"。用户面对的是一个可执行二进制文件 + 一个最小化智能体目录。
2. **对外只暴露两种入口**：
   - 二进制命令（`langagent run` / `langagent init` / `langagent eval` 等）。
   - 智能体目录文件（`instructions.md` / `.env` / `skills/*` / `tools/*` / `middleware/*`）。
3. **LangAgent 的存在意义**：把 LangChain 的能力 + LangGraph 的工作流编排 + MDA 的设计哲学，封装成一个普通用户能直接运行、不依赖任何云服务的本地产品。

### 非目标（Non-Goals）

- 不做云端 SaaS、不做远程托管运行时、不做任何需要公网账号才能跑的功能。
- 不复用、不链接、不 fork LangSmith 的任何闭源代码、API、容器镜像、Helm chart。
- 不引入任何"必须有外网才能 install / run"的运行时依赖（安装期与运行期皆然）。
- 不追求成为一个覆盖所有智能体范式的通用引擎；本宪法覆盖 ReAct 系智能体即可。

---

## 第 II 条　技术栈与依赖范围

1. **能力来源（functions/primitives）**：LangChain。优先使用 `langchain.agents.create_agent` 及官方 middleware / tools / models。版本号以 `pyproject.toml` 锁定。
2. **流程编排（workflow）**：LangGraph。React 智能体的主循环必须是 LangGraph 编译出的图。
3. **设计参考**：Managed Deep Agents（MDA）。仅借鉴其"项目结构 + 概念模型"，不复制其代码、不依赖其运行时。
4. **官方文档本地副本**（项目知识来源，**不是运行依赖**）：
   - `harness/LangChain_doc/` —— LangChain Python 文档
   - `harness/LangGraph_doc/` —— LangGraph Python 文档
   - `harness/Managed_deep_agents/` —— MDA 文档（仅作设计参考）
   任何 API 用法、MDA 行为猜测，必须先回到上述目录查证，不得凭印象。
5. **运行时 Python 版本**：以 `pyproject.toml` 中 `requires-python` 字段为准；CI 必须与之一致。
6. **依赖新增原则**：新增第三方库需满足下列任一条件，否则拒绝：
   - LangChain / LangGraph 官方文档中已示范使用；
   - 已存在于 LangChain / LangGraph 的可选依赖中；
   - 在离线内网 PyPI 镜像可拉取，且许可证允许商用分发。

---

## 第 III 条　LangSmith 剥离原则

LangSmith 是 LangChain 公司的闭源商业产品，是本项目**绝对禁止**依赖的对象。下列条款刚性约束：

1. **禁止 import**：`from langsmith import ...` 及其衍生模块一律不得出现在 `langagent/` 主代码中。
2. **禁止环境变量依赖**：不得读取 `LANGSMITH_API_KEY`、`LANGCHAIN_TRACING_V2`、`LANGCHAIN_API_KEY`、`LANGCHAIN_ENDPOINT` 等以驱动产品功能。如 LangChain 自身 SDK 默认读取这些变量，必须显式关闭或在配置层隔离。
3. **禁止托管运行时假设**：不得假设存在 LangSmith Deployment / Agent Server / Studio；所有"运行"必须在本地进程内完成。
4. **可观测性替代方案**：Tracing / Monitoring / Evaluation / Guardrails 能力必须由 LangAgent 自研或对接开源自托管方案（如 Langfuse、agentevals），不得借用 LangSmith 闭源后端。
5. **设计参考边界**：可以阅读 MDA 文档学习其"项目结构、概念术语、能力列表"，但禁止直接 `pip install managed-deepagents`。代码层面零复用。

---

## 第 IV 条　模型抽象层

1. **唯一契约**：业务代码、智能体图节点、middleware 一律通过 LangChain 的 Chat Model 接口（`BaseChatModel`）访问模型，**不直接调用任何 provider SDK**。
2. **必须支持的两类后端**（同等优先级，缺一不可）：
   - **联网模型供应商**：OpenAI / Anthropic / Google / DeepSeek / 智谱等，通过 LangChain 自带 provider 接入。
   - **本地 OpenAI Compatible**：公司内网 vLLM 部署的 Qwen3.8-27B（及同类）。通过 `ChatOpenAI(base_url=..., api_key=...)` 适配。
3. **模型选择必须可声明**：智能体目录的 `.env` 或 `agent.yaml` 中指定 `MODEL_PROVIDER` 与 `MODEL_NAME`（或 `MODEL_BASE_URL`），LangAgent 启动时据此构建模型实例，**不硬编码任何 provider**。
4. **本地模型必须可作为默认**：Qwen3.8-27B（OpenAI Compatible）是默认与基准模型；任何回归测试、性能基线、护栏示例都必须能在该模型上跑通。
5. **模型行为差异**：本地模型与商用模型在 tool-calling、system prompt 服从度、上下文长度上存在差异；middleware 层必须对差异做归一化或显式告警，禁止"在 OpenAI 上能跑就当能跑"。

---

## 第 V 条　智能体目录契约（Agent Directory Contract）

LangAgent 的智能体目录是用户**唯一需要理解**的概念，必须做到：复制到任何位置、配置 `.env` 后即可运行。

### 1. 强制布局

```
my-agent/
├── instructions.md         # 系统提示词（managed context）
├── .env                   # 模型与运行时密钥（启动时加载，不入构建产物）
├── skills/                # 技能：每个技能一个子目录，目录内必有 SKILL.md
│   └── <skill-name>/
│       └── SKILL.md
├── tools/                 # 工具：普通 Python 模块，被 agent.py import
├── middleware/            # 中间件：普通 Python 模块，被 agent.py import
├── channels/              # 可选：消息通道适配（IM 入口）
├── identity.py            # 可选：调用者身份验证
├── memory.py              # 可选：长期记忆
├── sandbox/               # 可选：文件系统 / shell 沙箱
├── evals/                 # 可选：Harbor 评测任务
├── agent.py               # 智能体入口：导出变量名必须为 agent
└── pyproject.toml         # 依赖声明
```

### 2. 强制性规则

- `agent.py` 必须导出名为 `agent` 的 LangGraph CompiledGraph，不允许其他导出名。
- `instructions.md` 是系统提示词**唯一**来源；不得在 `agent.py` 中以字符串硬编码 prompt。
- `.env` 不得进入打包产物；构建脚本必须显式排除。
- 缺失任何**非可选**文件（`agent.py` / `instructions.md` / `pyproject.toml`）时，`langagent run` 必须报错并指出缺哪个文件。
- 用户**不得**需要编辑 LangAgent 自身的源码即可修改智能体行为；修改点在目录内必须全部可见。

### 3. `langagent init <name>` 命令

- 在当前目录创建 `<name>/` 子目录，按上述布局生成模板。
- 模板必须包含一个最小可运行示例（默认模型 = 本地 vLLM Qwen3.8-27B），用户改 `.env` 即可切换。
- 模板必须自带至少一个 sample skill、一个 sample tool，方便用户理解范式。

---

## 第 VI 条　Agent Loop 与 State 设计

1. **主循环**：`Agent Loop` 由 LangGraph 编译出的图实现，遵循 ReAct（Reason + Act）模式，节点至少包含：
   - `model_call`：调用模型，得到 AIMessage。
   - `tools_execute`：执行 AIMessage 中的 tool_calls。
   - `should_continue`：决策边，决定回到 `model_call` 还是结束。
2. **State 必须自研**：禁止直接复用 LangGraph 预置的 `MessagesState` 作为终态；必须定义本项目专属的 `AgentState` TypedDict，至少包含：
   - `messages`：消息历史。
   - `todos`：规划/任务清单（用于 plan-then-execute）。
   - `files`：虚拟文件系统状态（若启用 FS tools）。
   - `context`：短期上下文元数据（用户、渠道、session id 等）。
   - `scratchpad`：中间推理 / 子任务结果。
   - 上述字段皆为可选，但其存在必须在 State schema 中显式声明。
3. **Node 来源**：Node 可以来自 LangChain（如 `create_agent` 子图）、自研 middleware、自研 tools；调用方不感知其来源。
4. **Edge 来源**：Edge 优先用 LangGraph 原生（`add_conditional_edges` / `Send`），自定义边通过路由函数实现。
5. **Checkpointer**：默认使用 LangGraph 自带的内存或 sqlite checkpointer（按部署形态切换）；持久化格式必须可被人工 `cat` 查看。
6. **Interrupt**：Human-in-the-loop 必须基于 LangGraph 的 `interrupt` 机制实现，不得绕开图直接 sleep / poll。

---

## 第 VII 条　Middleware 与工具规则

1. **Middleware 是 LangAgent 的扩展主轴**：横切关注点（日志、限速、重试、护栏、token 计数、敏感词过滤）一律通过 middleware 注入，不在业务节点里散写。
2. **middleware 接入方式**：优先 LangChain 内置 middleware；项目专属行为放入智能体目录的 `middleware/`，遵循 LangChain middleware 协议。
3. **工具（Tool）设计准则**：
   - 每个 tool 一个函数 + Pydantic schema，禁止动态字符串拼 schema。
   - 工具副作用（写文件、调外部 API、发送消息）必须显式标注，便于 middleware 决策是否 interrupt。
   - 工具不得在 `__init__` 里偷偷起后台线程 / 异步任务。

---

## 第 VIII 条　开发方法论（TDD 刚性约束）

本项目所有功能开发必须遵循**测试驱动开发**，不得跳过。

1. **任务拆分**：每个 spec 必须拆分为可独立验证的子任务；每个子任务进入实现前，必须先有其失败用例。
2. **红绿重构顺序**：
   - **Red**：先写一个或多个自动化测试，运行，必须失败。
   - **Green**：写最少代码让测试通过。
   - **Refactor**：在测试保持绿色的前提下重构。
3. **测试金字塔**：
   - **单元测试**：覆盖 middleware / tools / State schema / 模型适配层。
   - **集成测试**：构造最小智能体目录，跑端到端 ReAct 至少 1 轮，断言 messages / tool_calls / 最终输出。
   - **回归测试**：核心场景固化快照（fixtures），任何 prompt / middleware / 边改动须跑回归。
4. **不可 mock 真实 LangGraph 行为**：测试中可以用 fake model / fake tool 替代 LLM 调用，但不能 mock LangGraph 自身的图执行；图必须真的跑起来。
5. **CI 必跑**：lint + 类型检查 + 单元 + 集成 + 回归；任何一步失败即阻断合并。
6. **禁止的写法**：
   - 禁止"先写实现后补测试"。
   - 禁止把 `pass` / `pytest.skip` 作为占位留在 PR 里。
   - 禁止在主分支直接 push；改动走 feature 分支 + PR 评审。

---

## 第 IX 条　质量诊断能力矩阵

LangAgent 必须覆盖"智能体质量诊断"的 5 项子能力，实现形态可自研，但产出物、运行时机与 LangSmith 概念对齐：

| 子能力 | 必须解决的问题 | 产出物 | 何时运行 | 离线实现责任方 |
|---|---|---|---|---|
| **Tracing / 可观测性** | 智能体在做什么 / 哪一步慢 / token 消耗 | Span / Trace JSONL | 运行期 | LangAgent 自研写入本地文件；可对接 Langfuse 自托管 |
| **Monitoring / 监控** | 胜率 / 延迟 / 成本漂移 | 时序指标 / 告警 | 运维期 | 同上 |
| **Evaluation / 评分** | 结果对不对 / 轨迹合不合理 | Score / Metric / 报告 | 离线下 / 回归期 | 自研 eval runner + `agentevals` 兼容 |
| **Testing / 测试** | 改 prompt / tool / edge 后是否退化 | Pass/Fail + 覆盖率 | 开发期 / CI | pytest 体系（见第 VIII 条） |
| **Guardrails / 护栏** | PII 泄露 / 越权 tool / prompt injection | 拦截 / 改写 / 告警 | 运行期 inline + 审计期 post-hoc | LangChain Middleware + LangAgent 增强 middleware |

每项能力都必须有对应的：**最小可用实现 + 对应测试 + 文档说明**，缺一不得宣称支持。

---

## 第 X 条　安全与隐私

1. **不外发数据**：LangAgent 默认所有调用仅在内网；不得静默将 prompt / message / 文件内容上传至任何外部服务。
2. **工具权限最小化**：工具默认 deny-all 敏感操作（写文件、执行 shell、调用网络）；智能体目录中通过显式声明开启。
3. **prompt injection 防御**：
   - 来自工具返回值、检索片段、用户上传文件的文本，不得被无差别拼进 system prompt。
   - middleware 层提供"untrusted content"标注工具，所有外部输入源须标注，模型行为约束在 system 侧、而非直接信任 content。
4. **PII**：本地默认不做 PII 脱敏，但 middleware 接口必须预留，以便企业版开启。
5. **密钥管理**：`.env` 不入构建产物；打包脚本自动 strip；CI 日志禁止打印密钥。

---

## 第 XI 条　打包与分发

1. **目标形态**：单文件二进制可执行（PyInstaller 或同等方案），用户无需安装 Python 即可运行。
2. **入口二进制**：`langagent`，子命令至少包括：
   - `langagent run [agent-dir]` —— 启动智能体（默认当前目录）
   - `langagent init <name>` —— 创建智能体目录模板
   - `langagent eval [agent-dir]` —— 运行 evals
   - `langagent doctor` —— 自检（Python / 模型连通性 / 目录完整性）
3. **可复现构建**：打包脚本锁定 Python 版本、依赖版本、LangChain / LangGraph 版本；构建产物带版本号与 commit hash。
4. **离线安装**：必须支持 `pip install --no-index --find-links=./wheels` 方式预装依赖；不允许首次运行触发网络下载。
5. **升级策略**：LangAgent 主程序与智能体目录分离升级；智能体目录内容随用户意愿持久保留，升级不得覆盖用户的 `instructions.md` / `skills/` / `tools/`。

---

## 第 XII 条　配置与可观测契约

1. **配置来源优先级**：CLI 参数 > 环境变量 > 智能体目录 `.env` > 内置默认值。优先级冲突必须显式记录在启动日志中。
2. **启动日志**：每次启动必须打印（a）LangAgent 版本（b）智能体目录路径（c）模型 provider + model name（d）checkpointer 类型（e）启用的 middleware 列表。日志不得包含密钥原文。
3. **Trace 格式**：单条 JSONL 一行一个 span，含 `trace_id` / `span_id` / `parent_span_id` / `name` / `start` / `end` / `attributes`；schema 字段稳定，向后兼容。

---

## 第 XIII 条　禁止项（Hard No）

以下事项视为违规，发现即阻断：

- 任何依赖 LangSmith 闭源代码、API、镜像的代码或配置。
- 在主代码里写死 API key、模型名、文件路径假设。
- 在业务节点里直接调用 provider SDK（必须经 Chat Model 抽象）。
- 跳过 TDD 直接提交实现代码。
- 把用户 prompt / message / 文件内容写入任何外部网络地址。
- 让智能体目录丢失可移植性（出现绝对路径、`/Users/...`、内网 IP 硬编码等）。
- 用 `print` / `console.log` 替代结构化日志。

---

## 第 XIV 条　宪法修订程序

1. 本宪法效力高于 spec、plan、task；后者冲突时让位于本宪法。
2. 修订必须由"修订提案（RFC 文档）"发起，说明动机、影响范围、向后兼容性；存放在 `harness/prompt/constitution_changes/`。
3. 修订提案须通过项目维护者审阅；通过后更新本文件，并在文末追加修订日志。
4. 修订日志格式：

```
| 日期 | 版本 | 修订摘要 | 提案文件 |
| --- | --- | --- | --- |
| YYYY-MM-DD | v0.1 | 首版宪法 | (init_constitution.md 衍生) |
```

---

## 附：术语表

- **Agent**：由模型 + harness（提示词、工具、中间件）组成的能完成任务的实体。
- **Harness**：模型之外的"套子"，负责给模型在正确时机送入正确上下文。
- **Agent Loop**：ReAct 主循环，模型推理 → 工具执行 → 观察结果 → 再推理，直到结束。
- **Middleware**：横切关注点（重试、限速、护栏、日志、截断）在 agent 各阶段插入的钩子。
- **Skill**：放在 `skills/<name>/SKILL.md` 的领域知识 / SOP，由模型按需加载到上下文。
- **Checkpointer**：LangGraph 用于保存图执行状态的组件，支持中断恢复与时间旅行。
- **MDA**：Managed Deep Agents，LangChain 的智能体产品，本项目的**设计参考**（非依赖）。
