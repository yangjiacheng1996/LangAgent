# 添加工具

本指南详细介绍如何为 LangAgent 智能体创建自定义工具。

## 工具基础

### 什么是工具？

工具是智能体可以调用的 Python 函数，用于执行特定任务。每个工具：
- 继承自 LangChain 的 `BaseTool` 类
- 包含名称、描述和参数模式
- 实现 `_run()` 方法执行具体逻辑
- 可选：实现 `_arun()` 方法支持异步调用

### 工具加载机制

LangAgent 从智能体目录的 `tools/` 文件夹动态加载工具：

1. 扫描 `tools/*.py` 文件
2. 为每个文件创建独立的命名空间（`langagent_dynamic_tool_{tool_id}`）
3. 查找与文件名匹配的 `BaseTool` 实例
4. 注册到工具注册表，触发 `tool_registered` 事件

**重要**：工具文件名必须与导出的工具实例变量名一致。

## 创建简单工具

### 示例：时间工具

创建 `tools/current_time.py`：

```python
from langchain.tools import BaseTool
from pydantic import BaseModel
from datetime import datetime

class CurrentTimeInput(BaseModel):
    """时间工具不需要输入参数"""
    pass

class CurrentTimeTool(BaseTool):
    name = "current_time"
    description = "获取当前日期和时间"
    args_schema = CurrentTimeInput
    
    def _run(self) -> str:
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S")

# 导出工具实例（变量名必须与文件名一致）
current_time = CurrentTimeTool()
```

### 示例：文件读取工具

创建 `tools/read_file.py`：

```python
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
import os

class ReadFileInput(BaseModel):
    file_path: str = Field(description="要读取的文件路径")
    encoding: str = Field(default="utf-8", description="文件编码")

class ReadFileTool(BaseTool):
    name = "read_file"
    description = "读取指定路径的文本文件内容"
    args_schema = ReadFileInput
    
    def _run(self, file_path: str, encoding: str = "utf-8") -> str:
        try:
            if not os.path.exists(file_path):
                return f"错误: 文件不存在 {file_path}"
            
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            
            return f"文件内容 ({len(content)} 字符):\n{content}"
        except Exception as e:
            return f"读取文件失败: {str(e)}"

read_file = ReadFileTool()
```

## 创建带参数的工具

### 示例：HTTP 请求工具

创建 `tools/http_request.py`：

```python
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional, Dict
import requests

class HttpRequestInput(BaseModel):
    url: str = Field(description="请求的 URL")
    method: str = Field(default="GET", description="HTTP 方法 (GET, POST, PUT, DELETE)")
    headers: Optional[Dict[str, str]] = Field(default=None, description="请求头")
    body: Optional[str] = Field(default=None, description="请求体 (JSON 字符串)")
    timeout: int = Field(default=30, description="超时时间（秒）")

class HttpRequestTool(BaseTool):
    name = "http_request"
    description = "发送 HTTP 请求并返回响应"
    args_schema = HttpRequestInput
    
    def _run(
        self, 
        url: str, 
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
        timeout: int = 30
    ) -> str:
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                data=body,
                timeout=timeout
            )
            
            return f"状态码: {response.status_code}\n响应: {response.text[:500]}"
        except Exception as e:
            return f"请求失败: {str(e)}"

http_request = HttpRequestTool()
```

## 异步工具

### 示例：异步 API 调用

创建 `tools/async_api.py`：

```python
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
import asyncio
import aiohttp

class AsyncApiInput(BaseModel):
    url: str = Field(description="API 端点 URL")

class AsyncApiTool(BaseTool):
    name = "async_api"
    description = "异步调用 API 接口"
    args_schema = AsyncApiInput
    
    def _run(self, url: str) -> str:
        # 同步包装器
        return asyncio.run(self._arun(url))
    
    async def _arun(self, url: str) -> str:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    text = await response.text()
                    return f"状态: {response.status}\n响应: {text[:500]}"
        except Exception as e:
            return f"异步请求失败: {str(e)}"

async_api = AsyncApiTool()
```

## 工具元数据和配置

### ToolSpec 模型

工具加载后会被包装为 `ToolSpec` 对象，包含以下字段：

```python
@dataclass
class ToolSpec:
    tool_id: str              # 工具唯一标识符
    tool_name: str            # 工具名称
    description: str          # 工具描述
    args_schema: Dict         # JSON Schema (Draft 7)
    enabled: bool = True      # 是否启用
    requires_approval: bool = False  # 是否需要人工审批
```

### 设置审批要求

对于敏感操作，可以要求人工审批：

```python
class DeleteFileTool(BaseTool):
    name = "delete_file"
    description = "删除指定文件（需要审批）"
    args_schema = DeleteFileInput
    
    # 标记为需要审批
    requires_approval = True
    
    def _run(self, file_path: str) -> str:
        import os
        try:
            os.remove(file_path)
            return f"已删除文件: {file_path}"
        except Exception as e:
            return f"删除失败: {str(e)}"

delete_file = DeleteFileTool()
```

配合 Guardrail 中间件使用：

```bash
# smart 模式：尊重 requires_approval 标志
langagent run --middleware guardrail
export LANGAGENT_GUARDRAIL_MODE=smart

# all 模式：所有工具调用都需要审批
export LANGAGENT_GUARDRAIL_MODE=all

# strict 模式：拒绝所有工具调用
export LANGAGENT_GUARDRAIL_MODE=strict
```

## 高级特性

### 1. 工具状态管理

使用类属性存储工具状态：

```python
class CounterTool(BaseTool):
    name = "counter"
    description = "计数器工具"
    args_schema = CounterInput
    
    # 类属性存储状态
    _count: int = 0
    
    def _run(self, action: str) -> str:
        if action == "increment":
            self._count += 1
        elif action == "reset":
            self._count = 0
        
        return f"当前计数: {self._count}"

counter = CounterTool()
```

### 2. 工具依赖注入

访问智能体配置和资源：

```python
from langagent.runtime.agent_state import RuntimeConfig

class ConfigAwareTool(BaseTool):
    name = "config_aware"
    description = "访问运行时配置"
    args_schema = ConfigAwareInput
    
    def __init__(self, config: RuntimeConfig = None):
        super().__init__()
        self.config = config
    
    def _run(self) -> str:
        if self.config:
            return f"模型: {self.config.model_name}"
        return "配置未加载"

# 注意：LangAgent 目前不自动注入配置，需要手动传递
config_aware = ConfigAwareTool()
```

### 3. 错误处理和日志

使用标准日志记录：

```python
import logging
from langchain.tools import BaseTool

logger = logging.getLogger(__name__)

class RobustTool(BaseTool):
    name = "robust_tool"
    description = "带错误处理的工具"
    args_schema = RobustInput
    
    def _run(self, data: str) -> str:
        try:
            logger.info(f"处理数据: {data[:50]}")
            result = self._process(data)
            logger.info("处理成功")
            return result
        except ValueError as e:
            logger.error(f"数据验证失败: {e}")
            return f"输入错误: {str(e)}"
        except Exception as e:
            logger.exception("工具执行失败")
            return f"内部错误: {str(e)}"
    
    def _process(self, data: str) -> str:
        # 实际处理逻辑
        return f"处理结果: {data}"

robust_tool = RobustTool()
```

### 4. 工具返回结构化数据

返回 JSON 格式的结构化数据：

```python
import json
from typing import Dict, Any

class StructuredTool(BaseTool):
    name = "structured_tool"
    description = "返回结构化数据"
    args_schema = StructuredInput
    
    def _run(self, query: str) -> str:
        result = {
            "status": "success",
            "query": query,
            "data": {
                "count": 42,
                "items": ["item1", "item2"]
            },
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        # 返回格式化的 JSON 字符串
        return json.dumps(result, ensure_ascii=False, indent=2)

structured_tool = StructuredTool()
```

## 最佳实践

### 1. 描述编写

工具描述直接影响 LLM 的调用决策，应该：

- **明确功能**：清晰说明工具的作用
- **指明场景**：说明何时应该使用
- **列出限制**：说明工具的局限性

```python
class SearchTool(BaseTool):
    name = "search"
    description = """
    在指定目录下搜索文件内容。
    
    使用场景:
    - 查找包含特定关键词的文件
    - 代码库中搜索函数或类名
    
    限制:
    - 仅支持文本文件
    - 最大搜索深度 10 层
    - 忽略 .git 和 node_modules 目录
    """
    args_schema = SearchInput
```

### 2. 参数设计

使用 Pydantic 的 Field 提供详细的参数说明：

```python
from pydantic import BaseModel, Field, validator

class AdvancedInput(BaseModel):
    query: str = Field(
        description="搜索查询字符串，支持通配符 * 和 ?",
        min_length=1,
        max_length=200
    )
    
    case_sensitive: bool = Field(
        default=False,
        description="是否区分大小写"
    )
    
    max_results: int = Field(
        default=10,
        description="最大返回结果数量",
        ge=1,
        le=100
    )
    
    @validator('query')
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError("查询字符串不能为空")
        return v
```

### 3. 返回值格式

保持返回值格式一致和易读：

```python
def _run(self, query: str) -> str:
    # ✓ 好的实践
    return f"""
搜索完成
查询: {query}
找到: 5 个结果

1. file1.py:42 - def search_function()
2. file2.py:128 - class SearchEngine
...
"""

    # ✗ 避免的写法
    return "5"  # 太简略
    return str(complex_object)  # 不可读
```

### 4. 性能考虑

- **设置超时**：避免工具执行时间过长
- **限制资源**：限制内存和 CPU 使用
- **缓存结果**：对重复调用缓存结果

```python
from functools import lru_cache
import signal

class OptimizedTool(BaseTool):
    name = "optimized"
    description = "性能优化的工具"
    args_schema = OptimizedInput
    
    @lru_cache(maxsize=128)
    def _cached_operation(self, key: str) -> str:
        # 昂贵的操作
        return f"cached result for {key}"
    
    def _run(self, query: str) -> str:
        # 设置超时
        def timeout_handler(signum, frame):
            raise TimeoutError("操作超时")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)  # 30 秒超时
        
        try:
            result = self._cached_operation(query)
            signal.alarm(0)  # 取消超时
            return result
        except TimeoutError:
            return "错误: 操作超时"

optimized = OptimizedTool()
```

### 5. 测试工具

为每个工具编写单元测试：

```python
# tests/test_tools.py
import pytest
from tools.calculator import calculator

def test_calculator_addition():
    result = calculator._run("2 + 2")
    assert "4" in result

def test_calculator_invalid():
    result = calculator._run("invalid")
    assert "错误" in result or "error" in result.lower()
```

## 工具调试

### 启用详细日志

```bash
export LANGAGENT_LOG_LEVEL=DEBUG
langagent run
```

### 使用 doctor 命令检查

```bash
langagent doctor --checks tools
```

### 手动测试工具

创建测试脚本 `test_my_tool.py`：

```python
from tools.my_tool import my_tool

# 直接调用工具
result = my_tool._run("test input")
print(result)
```

运行测试：

```bash
cd my_agent
python test_my_tool.py
```

## 常见问题

### Q: 工具加载失败

**错误**：`[WARNING] 工具加载失败: my_tool`

**原因**：
1. 文件名与导出变量名不一致
2. 未继承 `BaseTool`
3. 语法错误

**解决**：
```bash
langagent doctor  # 查看详细错误
```

### Q: 工具未被调用

**原因**：
1. 描述不够清晰，LLM 不理解何时使用
2. 参数定义不明确
3. 工具被禁用

**解决**：
1. 改进 `description` 说明
2. 添加详细的 `Field(description=...)`
3. 检查 `enabled = True`

### Q: 参数解析错误

**错误**：`ValidationError: field required`

**原因**：参数 schema 与实际调用不匹配

**解决**：
```python
# 确保 args_schema 参数与 _run() 参数一致
class MyInput(BaseModel):
    param1: str = Field(...)  # 必需参数
    param2: int = Field(default=10)  # 可选参数

def _run(self, param1: str, param2: int = 10) -> str:
    ...
```

## 工具示例库

查看更多工具示例：
- `test-agent-smoke/tools/` - 官方示例工具
- [LangChain Tools](https://python.langchain.com/docs/modules/tools/) - LangChain 官方工具文档

## 下一步

- [修改提示词](./modifying-prompts.md) - 优化智能体指令
- [概述](./overview.md) - 了解工具注册机制
- [快速开始](./quickstart.md) - 创建第一个工具
