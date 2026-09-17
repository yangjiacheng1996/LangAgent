# 项目背景
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

# 官方文档
- LangChain官方文档：`harness/LangChain_doc` 。
- LangGraph官方文档：`harness/LangGraph_doc` 。
- MDA官方文档：`harness/Managed_deep_agents` 。

# feature 排班
我设计了第一个feature 000：顶层设计三大件。
在这个feature中，为本项目LangAgent设计智能体的业务流程、软件架构与功能模块划分、模块之间的通信数据格式。
我通过不停地speckit.clarify，回答了许多选择题，最终implement完成了顶层设计，交付物如下：
1. LangAgent智能体工作流。`harness/top_level_design/workflow.md`
2. LangAgent智能体架构设计与功能模块划分。`harness/top_level_design/architecture_modules.md`
3. LangAgent智能体功能模块之间交互数据格式。`harness/top_level_design/module_schemas.md`


我认为“没有大局观的程序员，不是优秀的程序员” ，所以我在顶层设计交付物完成后，修订了宪法，指导speckit每个阶段全文阅读顶层设计。

【当前任务】
现在我很迷茫，不知道宪法修订后，接下来如何一步一步实现整个智能体的开发。
需要你根据顶层设计交付物，将智能体开发过程，拆解成多个feature。feature可以有先后顺序，每个feature我都会启动一个speckit.specify，然后开始后续流程。

1. feature拆解与排序。整个智能体包含哪些feature？feature之间的开发顺序是怎样的，先开发什么后开发什么？将feature排序表写入`harness/feature/README.md`中。
注意，feature拆解要做到“不重复不遗漏”，feature之间不能有功能重叠，所有feature的功能之和不能少于顶层设计。俗话说1+1不能大于2,也不能小于2。
2. 针对每一个feature，设计一段需求提示词，写入`harness/feature`中的markdown文件，文件名以feature编号和名称来命名。
```
<编号>_<feature名称>.md
```
我会根据每个feature的需求提示词，启动 /speckit.specify + feature提示词。

---

# 项目背景
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

# 官方文档
- LangChain官方文档：`harness/LangChain_doc` 。
- LangGraph官方文档：`harness/LangGraph_doc` 。
- MDA官方文档：`harness/Managed_deep_agents` 。

# 评审
我设计了第一个feature 000：顶层设计三大件。
在这个feature中，为本项目LangAgent设计智能体的业务流程、软件架构与功能模块划分、模块之间的通信数据格式。
我通过不停地speckit.clarify，回答了许多选择题，最终implement完成了顶层设计，交付物如下：
1. LangAgent智能体工作流。`harness/top_level_design/workflow.md`
2. LangAgent智能体架构设计与功能模块划分。`harness/top_level_design/architecture_modules.md`
3. LangAgent智能体功能模块之间交互数据格式。`harness/top_level_design/module_schemas.md`


我认为“没有大局观的程序员，不是优秀的程序员” ，所以我在顶层设计交付物完成后，修订了宪法，指导speckit每个阶段全文阅读顶层设计。

【当前任务】
现在我很迷茫，不知道宪法修订后，接下来如何一步一步实现整个智能体的开发。
我已经根据顶层设计交付物，将智能体开发过程，拆解成多个feature。feature可以有先后顺序，每个feature我都会启动一个speckit.specify，然后开始后续流程。

1. feature拆解与排序。整个智能体包含哪些feature？feature之间的开发顺序是怎样的，先开发什么后开发什么？将feature排序表写入`harness/feature/README.md`中。
注意，feature拆解要做到“不重复不遗漏”，feature之间不能有功能重叠，所有feature的功能之和不能少于顶层设计。俗话说1+1不能大于2,也不能小于2。
2. 针对每一个feature，设计一段需求提示词，写入`harness/feature`中的markdown文件，文件名以feature编号和名称来命名。
```
<编号>_<feature名称>.md
```

以上feature排班工作都已完成，现在需要评审一下这些feature排班和feature提示词是否合理，是否与顶层设计有冲突、有遗漏？
将评审意见和推荐解决办法写入harness/feature/review.md
