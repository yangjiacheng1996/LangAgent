# 快速开始

本指南将带你在 5 分钟内创建并运行你的第一个 LangAgent 智能体。

## 前置要求

- Python 3.8+
- pip 包管理器
- OpenAI API Key 或其他兼容的 LLM API

## 步骤 1：安装 LangAgent

```bash
# 克隆仓库
git clone https://github.com/your-org/LangAgent.git
cd LangAgent

# 安装包（开发模式）
pip install -e .
```

安装完成后，验证安装：

```bash
langagent --help
```

你应该看到 LangAgent 的命令列表：`init`、`run`、`eval`、`doctor`。

## 步骤 2：创建智能体项目

使用 `init` 命令创建新的智能体项目：

```bash
langagent init my_first_agent
cd my_first_agent
```

创建的项目结构如下：

```
my_first_agent/
├── instructions.md      # 智能体指令
├── agent.py            # 状态定义
├── pyproject.toml      # 项目配置
├── .env.example        # 环境变量模板
├── tools/              # 工具目录
├── skills/             # 技能目录
├── middleware/         # 中间件目录
└── evals/              # 评估任务目录
```

## 步骤 3：配置环境变量

复制环境变量模板并配置你的 API 密钥：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的配置：

```bash
# 模型提供商配置
MODEL_PROVIDER=openai
MODEL_NAME=gpt-4o
OPENAI_API_KEY=sk-your-api-key-here

# 可选：自定义 API 端点
# MODEL_BASE_URL=https://api.openai.com/v1

# 可选：日志级别
# LANGAGENT_LOG_LEVEL=INFO

# 可选：Guardrail 模式
# LANGAGENT_GUARDRAIL_MODE=smart
```

## 步骤 4：自定义智能体指令

编辑 `instructions.md` 文件定义智能体的行为：

```markdown
# 我的智能体

你是一个友好的助手，专门帮助用户完成日常任务。

## 核心能力

- 回答问题
- 执行计算
- 处理文本

## 行为准则

1. 始终保持礼貌和专业
2. 对不确定的信息如实说明
3. 提供清晰简洁的回答
```

指令文件支持 Markdown 格式，最大 100KB。

## 步骤 5：运行智能体

启动智能体交互式对话：

```bash
langagent run
```

你将看到类似以下的提示：

```
[LangAgent] 智能体已启动
[LangAgent] 模型: gpt-4o (openai)
[LangAgent] 加载工具: 0
[LangAgent] 加载技能: 0

你: 
```

现在可以开始对话了！尝试输入：

```
你好，请介绍一下你自己
```

## 步骤 6：添加自定义工具（可选）

创建一个简单的计算器工具。在 `tools/` 目录下创建 `calculator.py`：

```python
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

class CalculatorInput(BaseModel):
    expression: str = Field(description="数学表达式，如 '2 + 2' 或 '3 * 4'")

class CalculatorTool(BaseTool):
    name = "calculator"
    description = "执行简单的数学计算"
    args_schema = CalculatorInput
    
    def _run(self, expression: str) -> str:
        try:
            result = eval(expression)
            return f"计算结果: {result}"
        except Exception as e:
            return f"计算错误: {str(e)}"

# 导出工具实例（变量名必须与文件名一致）
calculator = CalculatorTool()
```

重新运行智能体：

```bash
langagent run
```

现在智能体可以使用计算器工具了！尝试：

```
你: 计算 123 * 456
```

## 步骤 7：运行健康检查

使用 `doctor` 命令检查智能体配置：

```bash
langagent doctor
```

输出示例：

```
✓ 配置文件有效
✓ 环境变量完整
✓ 模型连接正常
✓ 工具加载成功 (1)
✓ 技能加载成功 (0)

所有检查通过！
```

## 步骤 8：创建评估任务（可选）

在 `evals/` 目录下创建 `test_calculator.yaml`：

```yaml
task_id: test_calculator
input: "计算 2 + 2"
expected: "4"
grader: contains
case_sensitive: false
timeout_s: 30
metadata:
  category: math
  difficulty: easy
```

运行评估：

```bash
langagent eval
```

## 常用命令速查

| 命令 | 用途 | 示例 |
|------|------|------|
| `langagent init <name>` | 创建新智能体 | `langagent init my_agent` |
| `langagent run` | 运行智能体 | `langagent run --model gpt-4o` |
| `langagent eval` | 运行评估 | `langagent eval --grader-only exact_match` |
| `langagent doctor` | 健康检查 | `langagent doctor` |

## 高级功能

### 启用检查点（对话持久化）

```bash
langagent run --checkpointer sqlite --thread-id session_001
```

支持的检查点类型：
- `memory`：内存存储（默认）
- `sqlite`：SQLite 数据库
- `redis`：Redis 存储
- `postgres`：PostgreSQL 存储

### 加载中间件

```bash
langagent run --middleware logging,guardrail
```

### 限制最大轮次

```bash
langagent run --max-turns 50
```

### 使用自定义模型端点

```bash
langagent run \
  --model-provider openai \
  --model gpt-4o \
  --model-base-url https://your-custom-endpoint.com/v1
```

## 故障排除

### 问题：命令未找到

```bash
langagent: command not found
```

**解决方案**：确保已正确安装并激活虚拟环境：

```bash
pip install -e .
# 或者重新激活虚拟环境
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
```

### 问题：API 密钥错误

```
Error: MODEL_PROVIDER or MODEL_NAME not configured
```

**解决方案**：检查 `.env` 文件是否正确配置：

```bash
cat .env | grep MODEL_PROVIDER
cat .env | grep OPENAI_API_KEY
```

### 问题：工具加载失败

```
[WARNING] 工具加载失败: my_tool
```

**解决方案**：
1. 检查工具文件名与导出变量名是否一致
2. 确保工具类继承自 `BaseTool`
3. 运行 `langagent doctor` 查看详细错误

### 问题：模型连接失败

```
Error: Failed to create chat model
```

**解决方案**：
1. 检查网络连接
2. 验证 API 密钥是否有效
3. 测试自定义端点是否可访问：`curl https://your-endpoint.com`

## 下一步

- [添加工具](./adding-tools.md)：深入了解工具系统
- [修改提示词](./modifying-prompts.md)：优化智能体指令
- [概述](./overview.md)：了解 LangAgent 架构
- [README](../README.md)：完整 CLI 参考

## 获取帮助

如果遇到问题：
1. 运行 `langagent doctor` 进行诊断
2. 查看日志文件（如果启用了日志记录）
3. 查阅 [specs/](../specs/) 目录中的设计文档
4. 提交 Issue 到项目仓库
