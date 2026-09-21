# LangAgent
LangAgent是一个基于LangChain和LangGraph打造的通用型React智能体。

## 安装

```bash
pip install -e .
```

## CLI 使用指南

LangAgent 提供了4个主要命令用于智能体的开发和运行：

### 1. `langagent init` - 初始化智能体项目

创建新的智能体项目结构：

```bash
# 创建名为 my_agent 的智能体
langagent init my_agent

# 在指定目录创建
langagent init my_agent --agent-dir ./projects
```

创建的项目包含：
- `instructions.md` - 智能体指令文档
- `agent.py` - 智能体主逻辑
- `pyproject.toml` - 项目配置
- `.env.example` - 环境变量示例
- `skills/` - 技能模块目录
- `tools/` - 工具函数目录
- `middleware/` - 中间件目录

**退出码**:
- `0` - 成功
- `67` - 目录已存在
- `70` - 模板加载失败

### 2. `langagent run` - 运行智能体

运行智能体交互式对话：

```bash
# 运行当前目录的智能体
langagent run

# 运行指定目录的智能体
langagent run --agent-dir ./my_agent

# 使用自定义模型
langagent run --model gpt-4o --model-provider openai

# 设置自定义base URL
langagent run --model-base-url https://api.custom.com/v1

# 启用检查点功能
langagent run --checkpointer sqlite --thread-id session_001

# 加载中间件
langagent run --middleware logging,auth,rate_limit

# 限制最大轮次
langagent run --max-turns 50
```

**退出码**:
- `0` - 成功
- `66` - 智能体目录未找到
- `72` - 配置验证失败
- `73` - 模型创建失败
- `74` - 运行时错误
- `75` - Token限制超出
- `76` - 人工中断（HITL）
- `130` - Ctrl-C中断

### 3. `langagent eval` - 评估智能体性能

运行评估任务测试智能体：

```bash
# 运行所有评估任务
langagent eval --agent-dir ./my_agent

# 只运行特定评估器类型的任务
langagent eval --grader-only exact_match

# 运行指定任务
langagent eval --task task_001

# 自定义报告格式
langagent eval --report-format json     # JSON格式
langagent eval --report-format yaml     # YAML格式
langagent eval --report-format table    # 表格格式（默认）
```

支持的评估器类型：
- `exact_match` - 精确匹配
- `contains` - 包含匹配
- `regex` - 正则表达式匹配
- `llm_judge` - LLM评分
- `tool_call_match` - 工具调用匹配

**退出码**:
- `0` - 评估完成
- `66` - 评估目录未找到
- `78` - 评估器错误

### 4. `langagent doctor` - 诊断智能体健康状态

检查智能体配置和环境：

```bash
# 运行所有健康检查
langagent doctor --agent-dir ./my_agent

# 运行指定检查项
langagent doctor --checks config,env,model
```

诊断检查项包括：
- 配置文件有效性
- 环境变量完整性
- 模型连接可用性
- 依赖项版本兼容性
- 检查点存储可访问性

**退出码**:
- `0` - 所有检查通过
- `1` - 部分检查失败

### 通用选项

所有命令支持：

```bash
-h, --help           显示帮助信息
--agent-dir PATH     指定智能体目录（默认: 当前目录）
```

## 项目结构

```
my_agent/
├── instructions.md      # 智能体行为指令
├── agent.py            # 主入口文件
├── pyproject.toml      # 项目配置
├── .env                # 环境变量（不提交到Git）
├── .env.example        # 环境变量示例
├── skills/             # 自定义技能
├── tools/              # 自定义工具
└── middleware/         # 自定义中间件
```

## 快速开始

```bash
# 1. 创建智能体
langagent init my_first_agent
cd my_first_agent

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API keys

# 3. 运行智能体
langagent run

# 4. 运行评估（可选）
langagent eval

# 5. 诊断检查（可选）
langagent doctor
```

## 开发指南

详细的开发文档请参考 `specs/` 目录：
- `specs/010-cli-entry-dispatch/` - CLI命令实现规范
- `specs/020-runtime-pipeline/` - 运行时管道规范
- `specs/030-eval-framework/` - 评估框架规范

## 贡献

欢迎提交 Issue 和 Pull Request！
