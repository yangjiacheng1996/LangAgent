# API Contract: build_doctor_probes()

**Module**: `langagent.runtime.main_loop_dispatcher`  
**Function**: `build_doctor_probes`  
**Version**: v1.0.0  
**Date**: 2026-09-20

---

## Signature

```python
def build_doctor_probes() -> tuple[
    Callable[[RuntimeConfig], tuple[bool, str]],
    Callable[[RuntimeConfig], tuple[bool, str]]
]:
    """构造 doctor 子命令用的 model 和 checkpointer 探测函数对。
    
    返回两个探测函数，用于 `langagent doctor` 子命令验证系统连通性：
    1. model_probe: 测试模型 endpoint 是否可达
    2. checkpoint_probe: 测试 checkpointer 是否可初始化
    
    这是 F10 doctor dispatch 与 F09 run_doctor_checks() 之间的解耦点：
    - F10 调用本函数获取 probe 函数对
    - F10 将 probe 注入到 F09 run_doctor_checks(*, model_probe_fn=, checkpoint_probe_fn=)
    - F09 不直接 import primitives 层（保持分层清晰）
    
    Returns:
        (model_probe, checkpoint_probe) 元组
        
        model_probe(config: RuntimeConfig) -> (success: bool, detail: str)
            尝试实例化 BaseChatModel，返回是否成功 + 详细信息
        
        checkpoint_probe(config: RuntimeConfig) -> (success: bool, detail: str)
            尝试实例化 BaseCheckpointSaver，返回是否成功 + 详细信息
    
    Side Effects:
        无。本函数纯粹构造闭包函数，不执行任何 I/O。
    
    Thread Safety:
        线程安全。返回的 probe 函数是无状态闭包。
    
    Notes:
        - F08 是本函数的天然归属：runtime 层依赖 primitives 是 architecture_modules.md 允许的
        - F08 已是 primitives 层消费方（通过 state_graph_builder.build()）
        - 新增 2 条硬例外依赖边（architecture_modules.md v2.4.0）:
          * runtime_main_loop_dispatcher → primitives_chat_model_factory
          * runtime_main_loop_dispatcher → primitives_checkpoint_adapter
        - primitives 是被动接口（create(config) 构造方法），不反向依赖 F08
    """
```

---

## Parameters

无参数。

---

## Return Value

### `tuple[Callable, Callable]`

**Type**: `(model_probe_fn, checkpoint_probe_fn)`

#### 1. `model_probe_fn(config: RuntimeConfig) -> tuple[bool, str]`

**Signature**:
```python
def model_probe(config: RuntimeConfig) -> tuple[bool, str]:
    """探测模型 endpoint 连通性。
    
    Args:
        config: 包含 model_provider, model_name, model_base_url 的 RuntimeConfig
    
    Returns:
        (success, detail)
        - success: True 如模型实例化成功，False 如失败
        - detail: 成功时返回 "endpoint reachable"，失败时返回异常信息
    """
```

**Behavior**:
- 调用 `primitives.chat_model_factory.create(config)` 尝试实例化模型
- **不发送真实请求**（不调用 model.invoke()），仅测试实例化
- 捕获所有异常（ConnectionError, TimeoutError, AuthenticationError 等）
- 返回格式统一为 `(bool, str)`

**Example Returns**:
```python
# 成功
(True, "endpoint reachable")

# 失败示例
(False, "ConnectionError: Failed to connect to https://api.openai.com")
(False, "AuthenticationError: Invalid API key")
(False, "TimeoutError: Request timed out after 5s")
```

#### 2. `checkpoint_probe_fn(config: RuntimeConfig) -> tuple[bool, str]`

**Signature**:
```python
def checkpoint_probe(config: RuntimeConfig) -> tuple[bool, str]:
    """探测 checkpointer 初始化能力。
    
    Args:
        config: 包含 checkpointer 字段的 RuntimeConfig（"memory" | "sqlite" | "postgres"）
    
    Returns:
        (success, detail)
        - success: True 如 checkpointer 初始化成功，False 如失败
        - detail: 成功时返回 "ok"，失败时返回异常信息
    """
```

**Behavior**:
- 调用 `primitives.checkpoint_adapter.create(config)` 实例化 checkpointer
- 立即调用 `checkpoint_adapter.close(checkpointer)` 清理资源
- **不写入真实数据**（不调用 checkpointer.put()）
- 捕获所有异常（FileNotFoundError, PermissionError, DatabaseError 等）
- 返回格式统一为 `(bool, str)`

**Example Returns**:
```python
# 成功
(True, "ok")

# 失败示例
(False, "FileNotFoundError: SQLite database path does not exist")
(False, "PermissionError: Cannot write to checkpoint directory")
(False, "psycopg2.OperationalError: Could not connect to PostgreSQL")
```

---

## Usage Example

### F10 Doctor Dispatch (调用方)

```python
# langagent/cli/runner.py (F10)
from langagent.runtime.main_loop_dispatcher import build_doctor_probes
from langagent.runtime.exit_handler import run_doctor_checks

def dispatch_doctor(config: RuntimeConfig, loaded: LoadedAgent) -> int:
    """执行 doctor 子命令。"""
    
    # 1. 构造 probe 函数
    probe_model_fn, probe_checkpoint_fn = build_doctor_probes()
    
    # 2. 注入到 F09 run_doctor_checks
    checks = run_doctor_checks(
        config,
        loaded,
        model_probe_fn=lambda: probe_model_fn(config),
        checkpoint_probe_fn=lambda: probe_checkpoint_fn(config)
    )
    
    # 3. 打印结果
    for check in checks:
        print(f"{check.name}: {'✓' if check.passed else '✗'} {check.detail}")
    
    # 4. 返回退出码
    return 0 if all(c.passed for c in checks) else 1
```

### F09 run_doctor_checks (接收方)

```python
# langagent/runtime/exit_handler.py (F09)
from typing import Callable

def run_doctor_checks(
    config: RuntimeConfig,
    loaded: LoadedAgent,
    *,
    model_probe_fn: Callable[[], tuple[bool, str]] | None = None,
    checkpoint_probe_fn: Callable[[], tuple[bool, str]] | None = None
) -> list[DoctorCheckResult]:
    """运行 4 项自检（不直接 import primitives）。"""
    
    results = []
    
    # Check 1: Agent directory layout
    results.append(check_agent_layout(loaded))
    
    # Check 2: Model connectivity (使用注入的 probe)
    if model_probe_fn:
        success, detail = model_probe_fn()
        results.append(DoctorCheckResult(
            name="model_connectivity",
            passed=success,
            detail=detail
        ))
    
    # Check 3: Checkpointer (使用注入的 probe)
    if checkpoint_probe_fn:
        success, detail = checkpoint_probe_fn()
        results.append(DoctorCheckResult(
            name="checkpointer",
            passed=success,
            detail=detail
        ))
    
    # Check 4: Skills/tools syntax
    results.append(check_skills_syntax(loaded))
    
    return results
```

---

## Implementation Example

```python
# langagent/runtime/main_loop_dispatcher.py (F08)
from typing import Callable
from langagent.runtime.config_resolver import RuntimeConfig
from langagent.primitives import chat_model_factory, checkpoint_adapter

def build_doctor_probes() -> tuple[
    Callable[[RuntimeConfig], tuple[bool, str]],
    Callable[[RuntimeConfig], tuple[bool, str]]
]:
    """构造 doctor 子命令用的 model / checkpointer probe 函数。"""
    
    def probe_model(config: RuntimeConfig) -> tuple[bool, str]:
        """探测模型 endpoint 连通性。"""
        try:
            model = chat_model_factory.create(config)
            # 仅测试实例化，不发送真实请求
            return (model is not None, "endpoint reachable")
        except Exception as e:
            return (False, f"{type(e).__name__}: {e}")
    
    def probe_checkpoint(config: RuntimeConfig) -> tuple[bool, str]:
        """探测 checkpointer 初始化能力。"""
        try:
            cp = checkpoint_adapter.create(config)
            checkpoint_adapter.close(cp)  # 立即清理
            return (True, "ok")
        except Exception as e:
            return (False, f"{type(e).__name__}: {e}")
    
    return probe_model, probe_checkpoint
```

---

## Design Rationale

### Why in F08?

**Options Considered**:

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| A: F08 (chosen) | Runtime 层依赖 primitives 是 matrix 允许的；F08 已是 primitives 消费方 | F08 模块增加 1 个额外职责 | ✅ Chosen |
| B: F10 CLI | Doctor 逻辑集中在 CLI 层 | 违反 CLI × primitives 黑名单（architecture_modules.md 硬约束） | ❌ Rejected |
| C: F09 exit_handler | Doctor checks 在 exit_handler 中 | F09 不应依赖 primitives（exit_handler 是清理阶段，不应实例化新对象） | ❌ Rejected |
| D: 新模块 F12 | 单一职责原则 | 引入新模块增加复杂度；probe 工厂逻辑简单（~20 LOC） | ❌ Rejected |

**Final Decision**: Option A (F08)
- **Rationale**: 
  - F08 runtime 层依赖 primitives 是 architecture_modules.md 依赖矩阵允许的
  - F08 已通过 `state_graph_builder.build()` 消费 primitives 层
  - 把 probe 工厂放到 F08 避免 F10 / F09 直接 import primitives（保持分层清晰）
  - 新增 2 条硬例外单向边（primitives 不反向依赖 F08）

### Why Not Direct Import in F09?

**Problem**: F09 `run_doctor_checks()` 如果直接 `from langagent.primitives import chat_model_factory`，会引入 runtime → primitives 不必要的耦合。

**Solution**: 依赖注入模式
- F10 doctor dispatch 调用 `build_doctor_probes()` 获取 probe 函数
- F10 将 probe 注入到 F09 `run_doctor_checks(*, model_probe_fn=, checkpoint_probe_fn=)`
- F09 仅调用注入的 callable，不直接 import primitives

**Benefit**: F09 保持与 primitives 层解耦，仅依赖抽象接口（callable signature）

---

## Testing Strategies

### Unit Tests

```python
def test_build_doctor_probes_returns_two_callables():
    """build_doctor_probes 返回 2 个 callable"""
    probe_model, probe_checkpoint = build_doctor_probes()
    assert callable(probe_model)
    assert callable(probe_checkpoint)

def test_model_probe_success(fake_config_openai):
    """model_probe 成功时返回 (True, "endpoint reachable")"""
    probe_model, _ = build_doctor_probes()
    success, detail = probe_model(fake_config_openai)
    assert success is True
    assert "reachable" in detail

def test_model_probe_failure_invalid_api_key(fake_config_invalid_key):
    """model_probe 失败时返回 (False, exception message)"""
    probe_model, _ = build_doctor_probes()
    success, detail = probe_model(fake_config_invalid_key)
    assert success is False
    assert "AuthenticationError" in detail or "API key" in detail

def test_checkpoint_probe_success(fake_config_memory_checkpointer):
    """checkpoint_probe 成功时返回 (True, "ok")"""
    _, probe_checkpoint = build_doctor_probes()
    success, detail = probe_checkpoint(fake_config_memory_checkpointer)
    assert success is True
    assert detail == "ok"

def test_checkpoint_probe_failure_missing_path(fake_config_sqlite_no_path):
    """checkpoint_probe 失败时返回 (False, exception message)"""
    _, probe_checkpoint = build_doctor_probes()
    success, detail = probe_checkpoint(fake_config_sqlite_no_path)
    assert success is False
    assert "FileNotFoundError" in detail or "path" in detail.lower()
```

### Integration Tests

```python
def test_doctor_dispatch_integration(tmp_path):
    """F10 doctor dispatch 调用 build_doctor_probes 并注入到 F09"""
    from langagent.cli.runner import dispatch_doctor
    from langagent.runtime.dir_loader import load
    from langagent.runtime.config_resolver import resolve
    
    # 准备测试环境
    agent_dir = tmp_path / "test-agent"
    setup_test_agent(agent_dir)
    
    loaded = load(str(agent_dir))
    config = resolve(cli_args={}, agent_dir=str(agent_dir))
    
    # 执行 doctor
    exit_code = dispatch_doctor(config, loaded)
    
    # 验证
    assert exit_code in (0, 1)  # 0=全通过, 1=部分失败
```

---

## Performance Characteristics

- **Latency**: O(model_init_time + checkpointer_init_time)
  - Model probe: 100ms - 2s (取决于 endpoint 网络延迟)
  - Checkpoint probe: 10ms - 100ms (本地文件系统)
- **Memory**: O(1) - 仅构造闭包，不持有大对象
- **Side Effects**: 无持久化副作用（不写文件、不发网络请求（除 model endpoint 健康检查））

---

## Changelog

### v1.0.0 (2026-09-20)
- Initial API contract
- Dependency injection pattern for F09 decoupling
- 2 hard-exception edges added to architecture_modules.md v2.4.0
