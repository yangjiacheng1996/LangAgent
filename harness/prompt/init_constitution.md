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
