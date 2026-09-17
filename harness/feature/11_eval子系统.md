# F11 — Eval 子系统（EvalTaskSpec + 5 种 Grader + EvalReport）

> **Feature ID**: F11
> **批次**: **Phase 1 第 4 批**（task_loader + report_aggregator 无运行时依赖，可与 F04 并行）+ **Phase 2 第 6 批**（5 个 graders 与 F05/F06 并行）+ **Phase 3 第 8 批**（runner 整合 F01/F02/F03/F05/F06 完成后）
> **依赖**（**review.md v2.4.0 P1-3 修复后修订**）：
> - **模块 import 依赖**（runner.run() 内部实际 import；可通过 `architecture_modules.md` 依赖矩阵 21×21 边校验）：
>   - F02（`dir_loader.load()` 加载被评测智能体）
>   - **F03（RuntimeConfig 类型消费；**review.md v2.4.0 P0-2 修复**：F11 runner 不再内部调用 `config_resolver.resolve()`——RuntimeConfig 由 F01 dispatch 入口解析后通过 `config` keyword-only 参数注入；F11 内部仅消费 config 实例，不持有 F03 模块 import）**
>   - **F07（**review.md v2.2.0 P2-6 修复新增**：F11 runner.publish `eval_task_started` / `eval_task_done` 事件到 F07 `protocol_event_bus`；F07 §3.4 已登记这 2 种 event_type；F11 §3.1 eval.runner 行需 `from langagent.protocol.event_bus import publish`；F08 metrics_collector 订阅这 2 类事件记 latency）**
>   - F05（`main_loop_dispatcher.run_until_done()` 跑每条任务）
>   - F10（`chat_model_factory.create(config)` 用于 llm_judge judge_model 独立实例，避免 judge bias；config 由 F01 注入）
> - **运行时调用依赖**（接口契约，无 import，非 module_id 依赖矩阵边）：
>   - F01（`cli_runner.parse_argv()` 输出 dict 结构 `{'cli_args': dict, 'grader_only': str | None, 'task': str | None}` 通过 `runner.run(agent_dir, *, config, args)` 参数传入；F11 不反向 import F01 任何符号）
> - **非依赖**（澄清）：F06（runner.run() 不 import F06；F06 写盘由 F01 dispatch 在 eval 分支统一调 `exit_handler.cleanup()` 完成）
> **被依赖**: F13（打包后 `langagent eval` 二进制可独立运行）
> **状态**: 待启动 speckit.specify（review.md v2.1.0 修复后；本 feature prompt 已应用 v0.4.0 修复：M-NEW-1 runner.run() 返回 `EvalRunResult` 含 `(eval_report, final_state, exit_code)`；m-NEW-1 args 类型从 `CliArgs` 改为 `dict[str, Any]`；M-NEW-3 log tag rename `la.cli.eval.*` → `la.lifecycle.eval.*`；m-NEW-9 grader_extensibility 用途澄清；v1.1.0 修复：P0-3 批次按相位展开；P0-4 §三 依赖列补 F03 + §3.1 runner.run() 内部 RuntimeConfig 来源明确 + §四 TDD 新增 test_runner_resolves_config_from_args_cli_args_dict；P1-2 §3.2 exit_code 含义 1 款改写；P2-5 §四.2 补 grader runtime validator 兜底测试；P2-11 §3.3 tool_call_match 双层校验备注；v2.1.0 修复：P1-3 §3.1 runner 签名改为 keyword-only `config` 参数，F11 不再内部 resolve config；P2-4 §3.1 表格加 5 graders 不计入 19 module_id 注释）

---

## 一、Feature 概述

实现 `langagent eval` 子命令的端到端逻辑：
1. 扫描 `<agent-dir>/evals/*.yaml` 加载 `EvalTaskSpec` 列表。
2. 对每条 task 跑 1 次 F05 `run_until_done`，产出实际输出。
3. 用 5 种 grader 之一（`exact_match` / `contains` / `regex` / `llm_judge` / `tool_call_match`）判定 pass/fail。
4. 累计生成 `EvalReport`，写盘 + 通过 F01 输出。

本 feature 不引入独立的 runtime 模块，而是跨 F01 / F02 / F05 / F06 的端到端整合 + 新增 `langagent/eval/` 子包。

## 二、必读顶层设计 artefact（宪法第 XV 条）

1. `harness/top_level_design/workflow.md#stage-exit_cleanup` + `#log-tag-la-cli-eval-summary` —— eval 退出清理与日志。
2. `harness/top_level_design/architecture_modules.md#mod-runtime-main-loop-dispatcher` + `#mod-runtime-exit-handler` —— 跑任务与报告写出。
3. `harness/top_level_design/module_schemas.md#schema-eval-task-spec` + `#schema-eval-report` —— EvalTaskSpec 7 字段 + EvalReport 9 字段 + 5 个 grader 候选值。
4. `harness/Managed_deep_agents/langsmith/python/managed-deep-agents-evals.md` —— MDA evals 设计参考（**仅参考**，不依赖）。

## 三、本 feature 覆盖的范围

### 3.1 新增模块（`eval_runner` 是第 21st module_id；**review.md v3.0.0 P1-1 修复**：`eval_runner` 在 `architecture_modules.md` v2.4.0 依赖矩阵 21×21 显式登记；新增 `langagent/eval/` 子包；review.md M-4 修复明确 `eval_runner` 由 F11 拥有）

| 子包内模块 | 关键 API | 行数估算 | 内部分相位（review.md M-6 修复） |
|---|---|---|---|
| `eval.task_loader` | `load_all(evals_dir: str) -> list[EvalTaskSpec]` | ~100 | Phase 1 |
| `eval.report_aggregator` | `aggregate(task_results: list[TaskResult]) -> EvalReport` | ~150 | Phase 1 |
| `eval.graders.exact_match` | `grade(expected: str \| list[str], actual: str) -> bool` | ~50 | Phase 2 |
| `eval.graders.contains` | `grade(expected: str \| list[str], actual: str) -> bool` | ~50 | Phase 2 |
| `eval.graders.regex` | `grade(expected: str \| list[str], actual: str) -> bool` | ~50 | Phase 2 |
| `eval.graders.tool_call_match` | `grade(expected: dict, actual_ai_message: AIMessage) -> bool` | ~100 | Phase 2 |
| `eval.graders.llm_judge` | `grade(expected: str \| list[str], actual: str, judge_model: BaseChatModel) -> bool` | ~150 | Phase 2（异步，与 F10 弱依赖） |
| `eval.runner` | `run(agent_dir: str, *, config: RuntimeConfig, args: dict[str, Any]) -> EvalRunResult`（**review.md v2.1.0 P1-3 修复后签名修订**：`config` 改为 keyword-only 强制传入；F11 runner 不再 import / 调用 `config_resolver.resolve()`——RuntimeConfig 由 F01 dispatch 入口解析后注入；**args dict schema**：`{'cli_args': dict[str, Any]（cli_runner.parse_argv() 输出）, 'grader_only': str \| None, 'task': str \| None}`；**review.md v0.4.0 m-NEW-1 修复后**：`args` 类型从 `CliArgs` 改为 `dict[str, Any]`，避免 F11 跨层 import F01 的 `CliArgs` 类型；入口发射 `la.lifecycle.eval.start`；出口 EvalReport 写入磁盘前发射 `la.lifecycle.eval.summary`；**review.md v0.4.0 M-NEW-1 修复后**返回 `EvalRunResult(eval_report, final_state, exit_code)` 而非 `int`，由 F01 dispatch 调 `exit_handler.cleanup(result.final_state, config, eval_report=result.eval_report)`；`exit_code` 字段在 runner 内部通过 `worst_of(all_failure_exit_codes)` 仲裁计算，不直接由 dispatch 返回）+ `_run_one_task(spec, agent, graph, config) -> TaskResult`（收尾发射 `la.lifecycle.eval.case_done`；**review.md v2.2.0 P2-6 修复新增**：每条 task 开始 / 完成时 publish `eval_task_started` / `eval_task_done` 事件到 F07 `protocol_event_bus`；F08 metrics_collector 订阅这 2 类事件记 task 级 latency + token 用量；F11 runner 通过 `from langagent.protocol.event_bus import publish` 调用） | ~280 | Phase 3 |

> **5 graders 模块计数**（**review.md v2.1.0 P2-4 修复新增注释**）：5 个 grader 模块（`exact_match` / `contains` / `regex` / `tool_call_match` / `llm_judge`）不计入 **21** 个 module_id 计数；`eval_runner` 本身是 21st module_id（`architecture_modules.md` v2.4.0 显式登记），与 5 graders 同属 F11 跨 runtime/cli 整合模块（详见 architecture_modules.md §模块清单脚注）。

#### 内部开发顺序（review.md M-6 修复明确 + v2.2.0 P1-5 修复：去重标题）

F11 体量 ~900 行实现 + ~50 测试用例，比 F02/F03/F05 大 4-6 倍；为降低 PR 风险，分 3 个相位开发：

- **Phase 1**（首批 PR，独立）：`eval/task_loader.py` + `eval/report_aggregator.py`。两者无运行时依赖，可与 F08 / F04 / F07 并行开发。
- **Phase 2**（并行 PR）：5 个 grader 模块（`exact_match` / `contains` / `regex` / `tool_call_match` 同步开发；`llm_judge` 异步，独立 PR）。每个 grader 文件独立测试，可分 4-5 个 PR 提交。
- **Phase 3**（最后 PR）：`eval/runner.py` 整合（依赖 Phase 1+2）。运行端到端集成测试。

> 不拆分 F11 为 F11a / F11b（README v0.3.0 决定保留 13 个 feature 不变）；仅在 F11 内部明确分相位降低 PR 风险。

### 3.2 Schema

- `EvalTaskSpec`（7 字段，`schema_version=v0.2.0`，M-4 修复后）：
  - `task_id: str`
  - `input: str`
  - `expected: str | list[str] | dict[str, Any] | None = None`（评审 M-4 扩展：`tool_call_match` 用 dict 类型；**review.md v1.0.0 P2-10 修复新增**：`tool_call_match` 必须为 dict，schema 层 `@field_validator('expected')` 按 `grader` 字段值约束 `expected` 类型——`tool_call_match` + 非 dict → Pydantic ValidationError，退出码 65）
  - `grader: Literal['exact_match', 'contains', 'regex', 'llm_judge', 'tool_call_match'] = 'exact_match'`
  - `timeout_s: int = Field(default=60, ge=1)`
  - `metadata: dict[str, Any] = {}`
  - `grader_extensibility: list[str] = []`（**review.md v0.4.0 m-NEW-9 修复后**：v2+ 扩展 grader 时按"schema_version 升版 + 写入 migrators + 更新 Literal 列表 + 同步扩展本字段"流程登记；v1 不强制填充，默认 `[]`）

```python
# review.md v1.0.0 P2-10 修复新增 EvalTaskSpec schema 层 expected 校验
from pydantic import BaseModel, Field, field_validator

class EvalTaskSpec(BaseModel, frozen=True):
    model_config = {"frozen": True}
    task_id:   str
    input:     str
    expected:  str | list[str] | dict[str, Any] | None = None
    grader:    Literal['exact_match', 'contains', 'regex', 'llm_judge', 'tool_call_match'] = 'exact_match'
    timeout_s: int = Field(default=60, ge=1)
    metadata:  dict[str, Any] = {}

    @field_validator('expected')
    @classmethod
    def validate_expected_by_grader(cls, v, info):
        grader = info.data.get('grader')
        if grader == 'tool_call_match' and v is not None and not isinstance(v, dict):
            raise ValueError(
                f"tool_call_match grader requires expected as dict (got {type(v).__name__})"
            )
        return v
```
- `EvalReport`（9 字段）：`report_id` / `generated_at` / `agent_dir` / `task_results` / `pass_rate` / `p50_latency_ms` / `p95_latency_ms` / `token_usage` / `cost_usd`。
- **`EvalRunResult`**（**review.md v0.4.0 M-NEW-1 修复新增**：frozen dataclass）：
  ```python
  from dataclasses import dataclass
  from langagent.runtime.agent_state import AgentState  # F05 拥有；F11 仅类型注解引用

  @dataclass(frozen=True)
  class EvalRunResult:
      """`eval.runner.run()` 返回值；review.md v0.4.0 M-NEW-1 修复明确。"""
      eval_report: EvalReport                    # F11 跑完所有 task 后聚合的报告
      final_state: AgentState                    # 最后一条 task 跑完后的 final state；F01 传给 F06 cleanup()
      exit_code: int                             # worst_of(all_failure_exit_codes)；非 0 表示有 task 失败
  ```

  > **`exit_code` 字段用途说明**（**review.md v2.2.0 修复 P1-4**：原 3 段分散 prose 合并为单一连贯段）：
  >
  > `exit_code: int = worst_of([all_task_exit_codes + 0])`，由 F11 `eval_runner` 内部计算。F11 runner 内部**不发** `la.cross_cutting.metrics.emit` 日志（该 tag 由 F08 metrics_collector 拥有）；F11 runner 在 task 失败时改发 `la.cross_cutting.event_handler_error` 日志（**review.md v1.1.0 P1-2 修复改写**），payload 含 `task_id` / `error_type` / `error_message`；`exit_code != 0` 时 F11 runner 记录到 `runner._failed_task_count` 内部计数器。该字段 3 个用途（不重叠）：
  > 1. **logging / debugging**（P1-2 改写）：F11 内部错误日志含 `exit_code` 值供排错；
  > 2. **`EvalReport.task_results[*]` 子字段写入**（**review.md v1.0.0 P2-11 修复新增**）：F11 runner 把每条 task 的 `exit_code` 写入 `EvalReport.task_results[i].exit_code` 子字段（task_results dict 增加 `exit_code: int` key）；
  > 3. **F01 dispatch 不直接返回此字段**（统一走 `exit_handler.cleanup()` worst_of() 路径返回最终退出码）：F01 §3.4 eval dispatch 调 `result = eval_runner.run(agent_dir, args)` 后调 `exit_handler.cleanup(result.final_state, config, eval_report=result.eval_report)`，`result.exit_code` 字段被忽略（最终退出码由 cleanup 自身聚合决定；与 v0.5.0 §二.A.1 + v2.1.0 P1-3 修复后统一路径一致）。
  >
  > 详见 `module_schemas.md#schema-eval-run-result §字段语义` 表 `exit_code` 行的"消费方"列。

### 3.3 5 种 Grader 语义

| grader | expected 推荐类型 | 判定逻辑 |
|---|---|---|
| `exact_match` | `str \| list[str]` | 实际输出 == expected（strip 后精确匹配） |
| `contains` | `str \| list[str]` | 实际输出 contains expected（任一 expected 子串命中即 pass） |
| `regex` | `str \| list[str]` | 实际输出匹配正则（任一 expected 模式命中即 pass） |
| `llm_judge` | `str \| list[str]` | 调用 judge 模型（独立 BaseChatModel 实例），prompt "Is the actual output semantically equivalent to expected?" |
| `tool_call_match` | `dict[str, Any]`（必须含 `tool_id` + `args`） | 实际 AIMessage.tool_calls 中存在 tool_id 相等且 args 匹配的项；`expected` 不是 dict 时抛 `EvalGraderArgumentMismatchError`，退出码 65（**v0.5.0 评审 v0.1.0 §四.C-14 评估后保留 65**：65 = EX_DATAERR 表示 grader 输入数据格式错，语义合理；tool_call_match 类型不匹配是"输入数据格式错"而非"CLI 用法错"，故不归 64；亦非"配置错"故不归 78）。<br>**双层校验（review.md v1.1.0 P2-11 修复新增）**：(a) schema 层 `task_loader.load_all()` 阶段：`@field_validator('expected')` 在 `grader=tool_call_match` + `expected` 非 dict 时抛 `pydantic.ValidationError`，退出码 65（第一时间拦截；schema_version v0.2.0+）；(b) grader 运行时 `_run_one_task()` 阶段：grader 内部再校验 `expected` 类型（兜底；schema_version v0.1.0 迁移场景或 schema validator 漏过的极端场景），抛 `EvalGraderArgumentMismatchError`，退出码 65 |

> **5 种 grader 模块组织**（**review.md v4.0.0 P2-2 修复新增**）：5 个 grader 分别位于 `langagent/eval/graders/<grader_name>.py`（`exact_match` / `contains` / `regex` / `llm_judge` / `tool_call_match`），统一接口 `grade(actual, expected, **kwargs) -> bool`；详见 `architecture_modules.md` §模块清单脚注。5 种 grader 必须全部实现（TDD 5 个独立 grader 模块测试）。

### 3.4 评测目录布局

```
<agent-dir>/evals/
├── task_001.yaml
├── task_002.yaml
└── task_003.yaml
```

每 YAML 样例：

```yaml
task_id: greeting-001
input: "Say hello to Alice"
expected: "Hello, Alice!"
grader: exact_match
timeout_s: 30
metadata:
  category: greeting
```

## 四、TDD 测试用例先行

### 4.1 `task_loader` 测试

- [ ] `test_load_all_empty_dir`：`evals/` 不存在 → 返回空 list（不抛错）。
- [ ] `test_load_all_single_task`：构造 1 个合法 yaml → 返回 1 个 EvalTaskSpec。
- [ ] `test_load_all_multiple_tasks`：3 个 yaml → 返回 3 个 EvalTaskSpec。
- [ ] `test_load_yaml_parse_error`：非法 YAML → 抛 `EvalYamlParseError`，退出码 65。
- [ ] `test_load_required_field_missing`：缺 `task_id` → 抛错，退出码 65。
- [ ] `test_load_grader_invalid_value`：`grader: "unknown"` → 抛 `EvalGraderUnknownError`，退出码 78。
- [ ] `test_load_timeout_s_must_be_positive`：`timeout_s: 0` → Pydantic ValidationError。
- [ ] `test_load_expected_can_be_list`：`expected: ["foo", "bar"]` → 解析为 list[str]。
- [ ] `test_load_metadata_optional`：缺 `metadata` → 默认空 dict。
- [ ] **`test_load_rejects_tool_call_match_with_string_expected`（review.md v1.0.0 P2-10 修复新增）**：`grader: tool_call_match` + `expected: "some_string"`（非 dict）→ Pydantic ValidationError，退出码 65（schema 层前置校验，运行时双保险 `EvalGraderArgumentMismatchError` 触发概率降低但仍保留）。

### 4.2 5 种 Grader 测试

- [ ] `test_exact_match_pass`：`expected="hello"` + `actual="hello"` → True。
- [ ] `test_exact_match_fail_with_whitespace`：`expected="hello"` + `actual=" hello "` → True（strip）。
- [ ] `test_exact_match_fail`：`expected="hello"` + `actual="hi"` → False。
- [ ] `test_exact_match_list_any_match`：expected: ["a", "b"] + actual="b xxx" → True。
- [ ] `test_contains_pass_substring`：同上 contains 版。
- [ ] `test_contains_case_sensitive`：`expected="HELLO"` + `actual="hello"` → False（默认大小写敏感；提供 case_insensitive 参数化）。
- [ ] `test_regex_pass`：expected: `r"^\\d{3}-\\d{4}$"` + actual: "123-4567" → True。
- [ ] `test_regex_compile_error`：expected: `"["`（非法正则） → 抛 `re.error`。
- [ ] `test_llm_judge_pass`：mock judge 模型返回 "YES" → True。
- [ ] `test_llm_judge_fail`：mock judge 模型返回 "NO" → False。
- [ ] `test_llm_judge_invalid_response`：mock judge 模型返回 "maybe"（非 YES/NO） → 抛 `LlmJudgeInvalidResponseError`。
- [ ] `test_tool_call_match_pass_by_id`：expected: `{"tool_id": "search", "args": {"q": "AI"}}` + AIMessage 含 `tool_calls=[{"name": "search", "args": {"q": "AI"}}]` → True。
- [ ] `test_tool_call_match_fail_by_args_mismatch`：args 不同 → False。
- [ ] `test_tool_call_match_fail_by_id_missing`：无对应 tool_call → False。

### 4.3 `runner` 端到端测试

- [ ] `test_run_one_task_converges`：mock F05 run_until_done 返回 AIMessage("Hello, Alice!") + grader=exact_match + expected="Hello, Alice!" → pass。
- [ ] `test_run_one_task_timeout`：mock run_until_done 阻塞 90 秒 → 抛 `EvalTimeoutError`，退出码 70。
- [ ] `test_run_aggregates_pass_rate`：3 task 跑完，2 pass → `EvalReport.pass_rate ≈ 0.667`。
- [ ] `test_run_aggregates_latency`：3 task latency 100/200/300 ms → `p50=200`, `p95=300`。
- [ ] `test_run_aggregates_token_usage`：3 task 跨 2 个模型 → `token_usage` 按 model 聚合。
- [ ] `test_run_emits_eval_task_started_event`：每条 task 开始 → event 被 publish。
- [ ] `test_run_emits_eval_task_done_event`：每条 task 结束 → event 被 publish（payload 含 pass/fail + latency）。
- [ ] `test_run_handles_grader_failure_gracefully`：grader 抛异常 → task 标记 fail + record error，不中断整个 eval。
- [ ] `test_run_respects_grader_only_filter`：CLI `--grader-only llm_judge` → 仅跑 grader=llm_judge 的 task。
- [ ] `test_run_respects_task_filter`：CLI `--task task_001` → 仅跑 task_001。
- [ ] `test_run_returns_eval_run_result_with_final_state`（**v0.4.0 M-NEW-1 修复新增**）：mock 3 个 task → `run()` 返回 `EvalRunResult(eval_report, final_state, exit_code)` 实例；`final_state` 是最后一条 task 的 final state；`exit_code == 0` 当全部 pass。
- [ ] `test_run_accepts_dict_args_not_cli_args`（**v0.4.0 m-NEW-1 修复新增**）：`run(agent_dir, {"grader_only": "llm_judge", "task": "task_001"})` 正常运行；不依赖 F01 CliArgs 类型。
- [ ] **`test_runner_accepts_config_as_keyword_arg`**（**review.md v2.1.0 P1-3 修复改写**：原 `test_runner_resolves_config_from_args_cli_args_dict` 语义反转——F11 不再 resolve config）：`run(agent_dir, *, config=fake_config, args={"cli_args": {...}})` → mock `config_resolver.resolve` **不**被调用（验证 F11 runner 不再内部 resolve）；fake_config 直接通过 keyword 传入 runner；返回 EvalRunResult.eval_report 中含 fake_config 派生的 metadata。
- [ ] **`test_runner_uses_injected_config_for_llm_judge`**（**review.md v2.1.0 P1-3 修复改写**：原 `test_runner_uses_resolved_config_for_llm_judge`）：构造 EvalTaskSpec grader=llm_judge → mock `chat_model_factory.create(config)` 被调用 1 次且参数 = 调用方注入的 config 实例（fake_config）；返回 judge_model 实例。验证 llm_judge 用注入的 config 而非 args 派生。
- [ ] **`test_tool_call_match_grader_runtime_validator_fallback`**（**review.md v1.1.0 P2-5 修复新增**）：直接构造 EvalTaskSpec（绕过 schema validator，模拟 schema_version v0.1.0 迁移场景）+ grader=tool_call_match + expected="some_string"（非 dict） → grader 抛 `EvalGraderArgumentMismatchError`，退出码 65；TaskResult.passed=False。验证 schema validator 漏过时的 grader runtime 兜底。

### 4.4 `report_aggregator` 测试

- [ ] `test_aggregate_returns_eval_report`：mock task_results → 返回 EvalReport 实例。
- [ ] `test_aggregate_pass_rate`：mock 10 task 7 pass → `pass_rate == 0.7`。
- [ ] `test_aggregate_handles_empty_results`：空 task_results → `pass_rate == 0.0` + 0 task_results。
- [ ] `test_aggregate_frozen_instance`：返回值 `isinstance(report, EvalReport) and not hasattr(report, '__setattr__')`。

### 4.5 端到端 CLI 集成测试

- [ ] `test_cli_eval_runs_and_writes_report`：subprocess.run `langagent eval tests/fixtures/agent-with-evals/` → exit code 0 + `~/.local/share/langagent/reports/<agent-dir>-<timestamp>.json` 含 EvalReport。
- [ ] `test_cli_eval_with_one_failing_task`：构造 1 个 fail task → exit code != 0。
- [ ] `test_cli_eval_no_evals_dir`：智能体目录无 `evals/` → exit code 0 + 报告含 "0 tasks"。
- [ ] `test_cli_eval_emits_lifecycle_eval_summary_log`：跑完 eval → `la.lifecycle.eval.summary` 日志被 emit。

### 4.5b eval 阶段日志发射测试（**review.md v0.3.0 S-4 修复新增**）

F11 在 eval 阶段发射 3 个 `la.lifecycle.eval.*` tag（详见 §3.1 eval.runner）；F11 通过 `from langagent.cross_cutting.logger import emit` 调用 F08 logger 接口。

- [ ] `test_eval_runner_run_emits_lifecycle_eval_start_log`：mock `task_loader.load_all` 返回 3 个 task → `eval_runner.run()` 入口（evals/ 加载完成后）收到 `la.lifecycle.eval.start` 日志，payload 含 `task_count` / `grader_distribution`。
- [ ] `test_eval_runner_run_emits_lifecycle_eval_summary_log`：mock 3 个 task 跑完 → `eval_runner.run()` 出口（EvalReport 写入磁盘前）收到 `la.lifecycle.eval.summary` 日志，payload 含 `pass_rate` / `p50_latency_ms` / `token_usage`。
- [ ] `test_eval_runner_run_one_task_emits_lifecycle_eval_case_done_log`：mock `_run_one_task` 返回 TaskResult → 收到 `la.lifecycle.eval.case_done` 日志，payload 含 `task_id` / `passed` / `latency_ms`。
- [ ] `test_eval_runner_emits_case_done_for_each_task`：mock 3 个 task → 收到 3 次 `la.lifecycle.eval.case_done` 日志（每 task 一次）。
- [ ] `test_eval_runner_log_tags_in_whitelist`：上述 3 个 tag 全部在 F08 `ALLOWED_TAGS` 集合（≥**46** 项）中。

## 五、关键约束

1. **不依赖 LangSmith**：不调用 LangSmith Evaluator SDK；grader 完全本地实现；F11 仅可选对接自托管 Langfuse（v1 不实现）。
2. **不 mock LangGraph 行为**：跑 task 时图必须真实执行（宪法第 VIII 条 4 款）。
3. **grader_extensibility 字段**：仅用于登记未来扩展点；v1 不允许新增 grader 值（FR-043 + 禁止省略号）。
4. **llm_judge 用独立 model 实例**：避免与被评测智能体共用模型导致 judge 偏差；可复用 `primitives_chat_model_factory.create()` 但用同一套 env。
5. **超时刚性**：单 task 超时立即终止该 task，不影响其它 task。
6. **失败不中断整体**：单 task grader 抛异常 → 标记 fail + 继续；汇总报告含 error count。
7. **依赖分两类**（**review.md v2.4.0 P1-2 修复明确**）：
   - **模块 import 依赖**（F11 runner.run() 内部实际 import）：F02（`dir_loader.load()`）+ F03（**仅类型注解引用** RuntimeConfig）+ F05（`main_loop_dispatcher.run_until_done()`）+ F07（`event_bus.publish`）+ F08（`logger.emit`）+ F10（`chat_model_factory.create`）。
   - **运行时调用依赖**（通过 F01 dispatch 间接调用，F11 runner **不 import**）：F01（CLI 入口；F01 `parse_argv()` 输出 args dict 通过 `eval_runner.run(agent_dir, *, config, args)` 参数传入）+ F06（F01 dispatch eval 分支在 `eval_runner.run()` 返回后调 `exit_handler.cleanup(result.final_state, config, eval_report=...)` 写盘 + 退出码仲裁；F11 runner 不直接 import F06）。
   - F11 通过 `from langagent.cross_cutting.logger import emit` 调用 F08 logger 发射 3 个 eval 阶段 tag（`la.lifecycle.eval.{start,case_done,summary}`，**review.md v0.3.0 S-4 修复明确**）；F11 通过 `from langagent.protocol.event_bus import publish` 调用 F07 event_bus 在每条 task 开始 / 完成时 publish `eval_task_started` / `eval_task_done` 2 类事件（**review.md v2.2.0 P2-6 修复明确**：F07 §3.4 已登记这 2 种 event_type；F08 metrics_collector 订阅记 task 级 latency）。
8. **TDD 刚性**：先 Red 后 Green 再 Refactor；grader 必须每个独立测（5 个 grader 文件 = 5 组测试）。
9. **第 XV 条对齐清单**：与宪法第 III 条（剥离 LangSmith）/ 第 IX 条（Evaluation + Testing 子能力）/ 第 XIII 条逐项对齐。

## 六、本 feature 不包含

- 不实现 evals/*.yaml 的 daemon 模式 / 持续集成（v1 仅一次性跑完）。
- 不实现 Langfuse 自托管对接（v1 预留接口）。
- 不实现 6 阶段本身（→ F02 / F05 / F06）。
- 不实现 grader 持久化（grader 是无状态函数；v1 不保存 grader 历史）。

## 七、Deliverable 清单

- [ ] `langagent/eval/__init__.py` + `task_loader.py` + `runner.py` + `report_aggregator.py`。
- [ ] `langagent/eval/graders/exact_match.py` + `contains.py` + `regex.py` + `llm_judge.py` + `tool_call_match.py` + `__init__.py`（grader 路由）。
- [ ] `tests/eval/test_task_loader.py` + `test_runner.py` + `test_report_aggregator.py`：≥30 个测试用例（review.md v0.3.0 S-4 修复后增补：原 25 个 + §4.5b 5 个 eval 阶段 logger 发射测试 = 30 个）。
- [ ] `tests/eval/test_graders/test_exact_match.py` + `test_contains.py` + `test_regex.py` + `test_llm_judge.py` + `test_tool_call_match.py`：≥15 个 grader 单元测试。
- [ ] `tests/eval/test_cli_eval_integration.py`：≥4 个 subprocess 端到端测试。
- [ ] `tests/fixtures/agent-with-evals/`：含 3 个 eval yaml 的 fixture。
- [ ] `mypy --strict` 通过。
- [ ] spec / plan / tasks 顶部引用宪法第 XV 条。

## 八、与其它 feature 的边界

- **F01**：`cli_runner.dispatch()` 对 `langagent eval` 调用 `eval_runner.run(agent_dir, args)`。
- **F02**：F11 调用 `dir_loader.load(agent_dir)` 加载被评测智能体。
- **F03**：F11 仅类型注解引用 `RuntimeConfig`（F03 拥有 schema 定义）；**review.md v2.1.0 P1-3 修复后**：F11 runner 不再 import / 调用 `config_resolver.resolve()`——RuntimeConfig 由 F01 dispatch 入口解析后通过 `config=` keyword-only 参数注入 runner。F03 仍是 RuntimeConfig schema 拥有方 + F01 dispatch 的依赖。
- **F05**：F11 对每条 EvalTaskSpec 调 `main_loop_dispatcher.run_until_done(graph, state, max_turns=...)`。
- **F06**：F11 跑完 eval 后由 F01 dispatch 调用 `exit_handler.cleanup(state, config, eval_report=report)` 写 EvalReport 到磁盘；F11 runner 不直接调 F06。
- **F08**：F08 metrics_collector 在每条 task 完成后产出 task 级 MetricsSnapshot。
- **F07**：F07 event_bus 在每条 task 开始 / 结束 publish `eval_task_started` / `eval_task_done` 事件。
- **F13**：F13 打包后，`./dist/langagent eval <agent-dir>` 可独立运行。