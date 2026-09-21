# LangAgent 概述

## 什么是 LangAgent？

LangAgent 是一个基于 LangChain 和 LangGraph 打造的通用型 ReAct 智能体框架。它提供了完整的智能体开发、运行、测试和评估的全生命周期管理工具。

## 核心特性

### 1. 模块化架构
- **工具系统**：动态加载和注册自定义工具
- **技能系统**：可组合的技能模块，支持版本管理
- **中间件系统**：可扩展的请求/响应处理管道
- **状态管理**：基于 TypedDict 的结构化状态

### 2. 安全防护
- **Guardrail 机制**：三种模式（all/smart/strict）的工具调用审批
- **PII 保护**：自动检测和脱敏敏感信息（邮箱、电话等）
- **提示词注入检测**：防御恶意提示词攻击
- **内网端点识别**：CIDR 和 glob 模式匹配保护内部资源
- **审计日志**：完整的工具调用和决策记录

### 3. 开发工具链
- **CLI 命令**：init、run、eval、doctor 四大命令
- **配置管理**：四层优先级配置（CLI > 环境变量 > .env > 默认值）
- **模板生成**：一键初始化智能体项目结构
- **健康检查**：自动诊断配置和环境问题

### 4. 评估框架
- **多种评分器**：exact_match、contains、regex、llm_judge、tool_call_match
- **任务管理**：YAML 格式定义评估任务
- **报告聚合**：支持 JSON、YAML、表格三种报告格式
- **超时控制**：任务级别的超时设置

### 5. 运行时管道
六阶段执行流程：
1. **dir_load**：加载智能体目录（工具、技能、指令）
2. **config_resolve**：合并配置源
3. **model_adapt**：创建聊天模型实例
4. **graph_compose**：构建状态图
5. **main_loop**：执行智能体主循环
6. **exit_cleanup**：清理和资源释放

## 项目结构

```
LangAgent/
├── langagent/              # 主包
│   ├── cli/               # 命令行接口
│   ├── cross_cutting/     # 横切关注点（日志、指标、防护）
│   ├── eval/              # 评估框架
│   ├── primitives/        # LangChain/LangGraph 抽象层
│   ├── protocol/          # 工具和技能注册协议
│   └── runtime/           # 运行时管道阶段
├── specs/                 # 设计规范文档（12 个阶段）
├── tests/                 # 测试套件
├── docs/                  # 文档
├── scripts/               # 构建和工具脚本
└── harness/               # 测试工具
```

## 智能体项目结构

使用 `langagent init` 创建的智能体项目包含：

```
my_agent/
├── instructions.md         # 智能体行为指令（必需）
├── agent.py               # 状态定义文件（必需）
├── pyproject.toml         # 项目配置（必需）
├── .env                   # 环境变量（不提交到 Git）
├── .env.example           # 环境变量模板
├── tools/                 # 自定义工具目录
│   └── example_tool.py    # 工具实现文件
├── skills/                # 技能模块目录
│   └── skill_name/
│       └── SKILL.md       # 技能定义文件
├── middleware/            # 中间件目录
│   └── custom_middleware.py
└── evals/                 # 评估任务目录
    └── task_001.yaml      # 评估任务定义
```

## 核心概念

### 工具（Tools）
工具是智能体可以调用的 Python 函数，遵循 LangChain 的 `BaseTool` 协议。每个工具包含：
- **tool_id**：唯一标识符（通常与文件名一致）
- **tool_name**：工具名称
- **description**：工具功能描述（影响 LLM 调用决策）
- **args_schema**：参数 JSON Schema（Draft 7）
- **enabled**：是否启用
- **requires_approval**：是否需要人工审批

### 技能（Skills）
技能是可复用的知识模块，以 Markdown 格式编写，包含 YAML 前置元数据：
- **name**：技能名称
- **description**：技能描述
- **version**：语义化版本号（vX.Y.Z）
- **author**：作者信息（可选）
- **tags**：标签列表（可选）
- **requires**：依赖列表（可选）

### 中间件（Middleware）
中间件提供三个钩子函数：
- **before_tools()**：工具执行前调用
- **after_tools()**：工具执行后调用
- **wrap_model_call()**：包装模型调用

### 状态（AgentState）
智能体状态是一个 TypedDict，包含五个字段：
- **messages**：对话消息列表
- **todos**：待办事项列表
- **files**：文件内容缓存
- **context**：上下文信息
- **scratchpad**：临时工作区

## 配置优先级

配置从以下来源按优先级加载（高到低）：
1. **CLI 参数**：如 `--model gpt-4o`
2. **环境变量**：如 `MODEL_NAME=gpt-4o`
3. **.env 文件**：项目根目录的 `.env`
4. **内置默认值**：框架预定义的默认配置

## 事件驱动架构

LangAgent 使用中央事件总线进行组件间通信：
- **tool_registered**：工具注册成功
- **tool_load_failed**：工具加载失败
- **skill_loaded**：技能加载成功
- **skill_load_failed**：技能加载失败
- **guardrail_triggered**：防护规则触发

## 退出码

LangAgent 使用语义化的退出码：
- **0**：成功
- **5**：必需字段缺失
- **65**：数据错误（格式错误、布局无效）
- **66**：智能体目录未找到
- **67**：名称冲突（目录已存在）
- **70**：软件错误（模板加载失败、超时）
- **72**：配置验证失败
- **73**：模型创建失败
- **74**：运行时错误
- **75**：Token 限制超出
- **76**：人工中断（HITL）
- **78**：评分器错误、占位符检测
- **130**：键盘中断（Ctrl-C）

## 设计哲学

LangAgent 遵循 **Constitutional LLM Agent** 设计理念：
- **治理优先**：强制执行安全策略和审批流程
- **可扩展性**：通过工具、技能、中间件实现功能扩展
- **可观测性**：完整的日志、指标和审计记录
- **可测试性**：内置评估框架和健康检查工具
- **配置即代码**：声明式配置和模板化项目结构

## 下一步

- [快速开始](./quickstart.md)：5 分钟上手指南
- [添加工具](./adding-tools.md)：创建自定义工具
- [修改提示词](./modifying-prompts.md)：定制智能体行为
- [README](../README.md)：CLI 命令参考
