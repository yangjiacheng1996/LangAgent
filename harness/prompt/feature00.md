# 顶层设计

【项目背景】
我想要基于LangSmithGraph和LangChain，打造一个与Managed Deep Agents（MDA）相似的React智能体，本项目名叫LangAgent，一切设计参考MDA。
LangAgent不是SDK，不是智能体开发框架，而是一套开箱即用的通用型智能体产品，打包成二进制可执行文件。可以用于日常问答、调研等，将系统提示词、工具稍加改动就可以作为Coding智能体使用。

- LangAgent的一切功能设计参考MDA。但是根据`harness/reports/about_langsmith.md`的描述，LangSmith的闭源收费是本项目不可接受的。所以在参考MDA时需要剥离LangSmith。
- 本项目LangAgent的运行环境是一个没有外部互联网的公司内网，对接公司自己vllm部署的Qwen3.8-27B模型。所以LangAgent在适配联网的大模型供应商的情况下，还需要适配本地OpenAI Compatible。
- 关于智能体目录。MDA可以通过`uvx --from managed-deepagents mda init research-assistant` 命令创建一个名叫research-assistant的智能体。
此后就会在当前目录出现一个research-assistant目录，目录中包含若干文件，需要用户修改。
目录中Instructions.md中包含Agent的系统提示词，修改.env就能配置自己的大模型。在特定目录中就可以放入自己的Agent Skills。
由此可以看出，MDA的智能体目录是最小化的，将工作目录复制到其他地方就能启动，机动性高，可配置项强，简单易上手。本项目LangAgent照搬MDA工作目录设计原则。
- 关于Agent Loop，采用LangGraph构造React智能体的工作流。
- 在Graph中，LangChain的create_agent()和其他函数作为Node节点。
- 需要设计一套数据结构作为Graph的State。
- 开发过程中采用TDD（Testing Driven Development）测试驱动开发方式，先制定测试用例再开发，防止代码功能写跑偏。


【Feature 00 顶层设计】
我打算使用/speckit命令开发LangAgent。现在需要将整个智能体进行顶层设计。
我已经生成了constitution宪法。现在请你通读MDA文档`harness/Managed_deep_agents/`，掌握MDA设计。然后按需阅读LangGraph和LangChain的官方文档。
根据宪法和我的项目目标，做顶层设计。
顶层设计（top level design）至少包含如下几个文件：
1. 智能体工作流workflow.md，介绍智能体的使用流程和软件业务流程。
2. 架构与模块architecture_modules.md，根据官方文档设计和工作流，设计LangAgent的架构，架构中包含哪些功能模块。
3. 模块之间的数据结构 module_schemas.md，根据官方文档设计、工作流、架构等，设计功能模块之间交互的数据结构。
顶层架构设计文档应该保存在 `harness/top_level_design/`目录中。
但是现在不要编写这三个文件，现在是specify阶段，编写文档应该在implement阶段。

现在请你设计Feature 00 top level design的 feature提示词，我拿到提示词后，执行/speckit.specify + 提示词，生成Feature 00。
为什么是00,而不是01？，因为顶层设计不算真正的Feature。


# 提示词
```markdown
请基于已有的项目宪法与参考文档
（harness/LangChain_doc/、harness/LangGraph_doc/、harness/Managed_deep_agents/），
为 LangAgent 项目生成 Feature 00：顶层设计（Top-Level Design）。

【项目背景】
我想要基于LangSmithGraph和LangChain，打造一个与Managed Deep Agents（MDA）相似的React智能体，本项目名叫LangAgent，一切设计参考MDA。
LangAgent不是SDK，不是智能体开发框架，而是一套开箱即用的通用型智能体产品，打包成二进制可执行文件。可以用于日常问答、调研等，将系统提示词、工具稍加改动就可以作为Coding智能体使用。

- LangAgent的一切功能设计参考MDA。但是根据`harness/reports/about_langsmith.md`的描述，LangSmith的闭源收费是本项目不可接受的。所以在参考MDA时需要剥离LangSmith。
- 本项目LangAgent的运行环境是一个没有外部互联网的公司内网，对接公司自己vllm部署的Qwen3.8-27B模型。所以LangAgent在适配联网的大模型供应商的情况下，还需要适配本地OpenAI Compatible。
- 关于智能体目录。MDA可以通过`uvx --from managed-deepagents mda init research-assistant` 命令创建一个名叫research-assistant的智能体。
此后就会在当前目录出现一个research-assistant目录，目录中包含若干文件，需要用户修改。
目录中Instructions.md中包含Agent的系统提示词，修改.env就能配置自己的大模型。在特定目录中就可以放入自己的Agent Skills。
由此可以看出，MDA的智能体目录是最小化的，将工作目录复制到其他地方就能启动，机动性高，可配置项强，简单易上手。本项目LangAgent照搬MDA工作目录设计原则。
- 关于Agent Loop，采用LangGraph构造React智能体的工作流。
- 在Graph中，LangChain的create_agent()和其他函数作为Node节点。
- 需要设计一套数据结构作为Graph的State。
- 开发过程中采用TDD（Testing Driven Development）测试驱动开发方式，先制定测试用例再开发，防止代码功能写跑偏。

【Feature 00 的本质】
Feature 00 不编写任何 Python 代码、不创建 langagent 包、不写测试。它的唯一产出物是
3 份互相引用、自洽、可被后续所有 Feature（01-10+）作为设计依据使用的 Markdown
设计文档，全部保存在 harness/top_level_design/ 目录：

  1) workflow.md
     ——智能体工作流：用户视角的 CLI 生命周期（init / run / eval / doctor），
       系统视角的运行时 6 阶段（目录加载 → 配置解析 → 模型与 checkpointer 适配 →
       图组合 → 主循环 → 退出与清理），每阶段的输入/输出/失败模式/退出码/日志标签，
       以及与 MDA 的能力对照表。

  2) architecture_modules.md
     ——架构与功能模块：5 层架构（CLI / runtime / protocol / middleware+guardrails+
       observability / LangChain+LangGraph 原语），每个模块的职责、关键 API、
       允许与禁止的依赖方向，模块间的依赖矩阵，模块到 Feature 的拆分映射，
       以及静态约束 CI 校验清单。

  3) module_schemas.md
     ——模块间数据结构：AgentState（含 reducer 规则）、RuntimeConfig、LoadedAgent、
       SkillSpec/SkillFrontmatter、ToolSpec/ToolSideEffect、MiddlewareSpec、
       ChannelSpec、ChannelContext、SandboxSpec、ScheduleSpec、MemorySpec、
       IdentitySpec、EvalTaskSpec、Span/Trace、Event 总线、MetricsSnapshot、
       AuditEntry、DoctorReport、EvalReport，每项给出 Python 类型签名
       （TypedDict / Pydantic BaseModel / dataclass）、磁盘格式与 schema_version、
       与 LangChain / LangGraph 原生类型的兼容性映射。

【生成 spec 时请遵循以下硬性约束】

A. 不写代码、不写包结构、不写测试用例；本 Feature 是纯文档 Feature。
B. spec 中的"用户"指的是后续 Feature 的设计者与实现者（项目维护者本人），
   不是终端用户。所有 user story 应从"我作为后续 Feature 的设计者"出发。
C. 严格保持 WHAT & WHY 视角，避免 HOW（不出现具体 Python 模块路径、
   不出现具体第三方库名作为必选项、不出现具体文件路径作为约束）；
   但允许在举例处提及 LangChain、LangGraph、Pydantic 等用于澄清边界的工具名。
D. 用户故事优先级：3 份文档同等重要，均为 P1（没有 workflow 就没有阶段，
   没有 architecture 就没有模块边界，没有 schema 就没有类型契约）。
E. Functional Requirements 应明确每份文档必须包含哪些"必备小节"，
   并明确文档之间的交叉引用规则（相对路径、章节锚点、命名空间）。
F. Success Criteria 应可被以下方式验证：
   - 文档存在且行数达标（每份 ≥ 200 行）
   - 文档之间交叉引用全部可达
   - 同名概念（阶段名、退出码、日志标签、字段名）在 3 份文档中语义一致
   - 不含 "TODO / TBD / 留待决定" 等占位词
   - 不含绝对路径、内网 IP、硬编码 API key
   - 与宪法第 I-XIV 条无冲突（任何冲突以宪法为准，并在文档中显式标注）
G. Key Entities 至少包括：Workflow Document（阶段+失败模式+退出码+日志标签）、
   Architecture Module（层+职责+依赖方向+越界禁止）、Module Schema
   （内存类型+磁盘格式+schema_version+LangChain/LangGraph 类型映射）。
H. Assumptions 至少包括：
   - 宪法已定稿，Feature 00 期间不会变更
   - LangChain / LangGraph 官方文档以 harness/LangChain_doc/ 与 harness/LangGraph_doc/
     为唯一可信来源
   - MDA 仅作设计参考，不 import、不 pip install
   - 本 Feature 不实现 channels/schedules/long_term_memory/docker_sandbox 等
     v1 占位能力，只在文档中预留接口
   - 文档语言为中文，代码示例与类型名以英文书写
   - 文档完成后由项目维护者人工 review 后再进入后续 Feature
I. Out of Scope 至少包括：编写任何 langagent 代码、生成 pyproject.toml、
   生成 tests/、修改宪法、提前开启 Feature 01-10+ 的 spec。

【交付物】
请把 Feature 00 的 spec 生成到 .specify 流程默认的 specs/ 目录下，
文件名遵循 speckit.specify 命名规则，文档末尾生成一份 requirements.md 校验清单。


```