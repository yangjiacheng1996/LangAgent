# F01 — CLI 入口与子命令分发（init / run / eval / doctor）

> **Feature ID**: F01
> **批次**: 第 8 批（CLI 层）
> **依赖**: F02（dir_loader.load / write_template）/ F03（config_resolver.resolve）/ F05（main_loop_dispatcher.dispatch）/ F06（exit_handler.cleanup + run_doctor_checks）/ F10（chat_model_factory.create + checkpoint_adapter.create + state_graph_builder.build + primitives_state_reducers reducer 注入，**v0.4.0 M-4 方案 C 修复后**）/**F11（仅 `langagent eval` 子命令懒导入 eval_runner.run，review.md v0.3.0 M-5 修复明确；v0.4.0 M-NEW-1 修复后返回 `EvalRunResult` 含 `(eval_report, final_state, exit_code)`）**
> **被依赖**: F11（eval 子系统通过 CLI 入口触发）/ F13（打包 CLI 二进制）
> **状态**: 待启动 speckit.specify（review.md v1.1.0 修复后；本 feature prompt 已应用 v0.4.0 修复：M-NEW-3 log tag rename `la.cli.*` → `la.lifecycle.*`；M-NEW-1 eval dispatch state 来源明确；v1.1.0 修复：P0-2 方案 B §3.4 run dispatch 删 compiled_graph 引用 + LoadedAgent 5 字段 + F01 独立持 CompiledStateGraph；P2-10 §四.2 第 6 项测试改写 dispatch_eval_returns_cleanup_exit_code）

---

## 一、Feature 概述

实现 cli 层 3 个模块：
- **`cli_runner`**：解析 argv，识别 4 个核心子命令（`init` / `run` / `eval` / `doctor`），分发到 runtime 层；返回最终退出码。
- **`cli_parser`**：定义 4 个子命令的 argparse schema；把 Namespace 转换为 `RuntimeConfig.cli_args` 字典。
- **`cli_output_formatter`**：把 `EvalReport` / `DoctorReport` / Event 流格式化为人类可读文本（彩色 + 表格 + 进度条）。

CLI 是用户唯一可见的入口；本 feature 把 6 阶段串联起来。

## 二、必读顶层设计 artefact（宪法第 XV 条）

1. `harness/top_level_design/workflow.md` —— 4 个子命令的输入 / 输出 / 失败模式 / 退出码 / 日志标签（FR-013 / R-3）。
2. `harness/top_level_design/architecture_modules.md#mod-cli-runner` + `#mod-cli-parser` + `#mod-cli-output-formatter` —— 模块依赖矩阵。
3. `harness/top_level_design/module_schemas.md#schema-doctor-report` + `#schema-eval-report` —— 报告格式。

**本 feature 重点对齐的宪法条款**（**review.md v2.2.0 修复 P2-9**）：
- **第 I 条** 项目身份与边界：F01 是 LangAgent 对外暴露的"二进制命令"入口（与宪法第 I 条 2 款对齐）；
- **第 III 条** LangSmith 剥离：F01 CLI 严禁直接 `import langsmith` / 不读 LANGSMITH_* env；
- **第 XI 条** 打包与分发：F01 与 F13 协同——F01 的 `langagent/__main__.py` 是 PyInstaller 入口；
- **第 XIII 条** 禁止项：CLI × primitives 黑名单（F01 不直接 import `chat_model_factory` / `checkpoint_adapter`，避免破坏分层约束；probe 工厂由 F05 `build_doctor_probes()` 提供）。

## 三、本 feature 覆盖的范围

### 3.1 模块

| module_id | 关键 API | 行数估算 |
|---|---|---|
| `cli_runner` | `parse_argv(argv: list[str]) -> CliArgs` + `dispatch(args: CliArgs, runtime: RuntimeDeps) -> int` + `main(argv: list[str] \| None = None) -> int` | ~280 |
| `cli_parser` | `build_parser() -> argparse.ArgumentParser` + `ns_to_cli_args(ns: argparse.Namespace) -> dict[str, Any]` | ~180 |
| `cli_output_formatter` | `format_eval_report(report: EvalReport) -> str` + `format_doctor_report(report: DoctorReport) -> str` + `format_event_stream(stream: Iterable[Event]) -> Iterator[str]` + **`format_chat_message(message_dict: dict) -> str`**（**review.md v0.3.0 M-2 修复新增**：把 AIMessage.to_dict() 序列化结果格式化为 stdout 单行 `[assistant] <content>`；接收 dict 而非 AIMessage 实例，避免 CLI 层直接 import LangChain 类型，违反 cli × primitives 约束）+ **`format_eval_report_stdout(report: EvalReport) -> str`**（stdout 简洁版，与 format_eval_report 文件版区分）+ **`format_doctor_report_stdout(report: DoctorReport) -> str`**（stdout 简洁版） | ~320 |

> **review.md M-4 修复新增**：F01 dispatch 对 `langagent eval` 委托 `eval_runner.run(agent_dir, args)`（**F11 实现**）。`eval_runner` 是 F11 提供的跨 runtime/cli 整合模块，**不属于 17 个 module_id 计数**，由 F11 在 `langagent/eval/runner.py` 实现；F01 仅以 `from langagent.eval.runner import run as eval_runner_run` 形式调用。

### 3.2 Schema（本 feature 消费）

- `CliArgs`（frozen Pydantic）：`subcommand: str` + `agent_dir: str` + `cli_args: dict[str, Any]`（其余字段按子命令扩展）。
- `DoctorReport`（F06 拥有 schema 定义与 4 项 check 函数，本 feature 仅消费并格式化）。
- `EvalReport`（F11 拥有 schema 定义，本 feature 仅消费并格式化）。

### 3.3 4 个核心子命令的 argparse schema（**review.md M-8 修复后 init 子命令移除 `--template`**）

#### `langagent init <name>`

```
langagent init [-h] name
```

| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `name` | str（位置） | （必填） | 智能体目录名；正则 `^[a-zA-Z][a-zA-Z0-9_-]*$` |

> **review.md M-8 修复**：`--template` 参数 v1 不暴露；F02 §3.5 write_template() 不接收 template 参数；仅默认模板。v2 引入多模板时再加。

#### `langagent run [agent-dir]`

```
langagent run [-h] [--model MODEL] [--model-provider PROVIDER]
              [--model-base-url URL] [--checkpointer {memory,sqlite,postgres}]
              [--middleware ID,...] [--max-turns N] [--thread-id ID]
              [agent_dir]
```

| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `agent_dir` | str（位置，可选） | cwd | 智能体目录路径 |
| `--model` | str | None | 覆盖 `MODEL_NAME` |
| `--model-provider` | str | None | 覆盖 `MODEL_PROVIDER` |
| `--model-base-url` | str | None | 覆盖 `MODEL_BASE_URL` |
| `--checkpointer` | 3 选 1 | None | 覆盖 `LANGAGENT_CHECKPOINTER` |
| `--middleware` | str（逗号分隔） | None | 覆盖 `LANGAGENT_MIDDLEWARE` |
| `--max-turns` | int（≥1） | 30 | 主循环最大轮数 |
| `--thread-id` | str | auto-generated | checkpointer thread id |

#### `langagent eval [agent-dir]`

```
langagent eval [-h] [--grader-only TYPE] [--task TASK_ID] [--report-format {json,yaml,table}] [agent_dir]
```

| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `agent_dir` | str（位置，可选） | cwd | 智能体目录路径 |
| `--grader-only` | 5 选 1 | None | 仅跑指定 grader |
| `--task` | str | None | 仅跑指定 task_id |
| `--report-format` | 3 选 1 | `"table"` | 输出格式 |

#### `langagent doctor`

```
langagent doctor [-h] [--checks {model,checkpointer,skills,instructions}] [agent_dir]
```

| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `agent_dir` | str（位置，可选） | cwd | 智能体目录路径 |
| `--checks` | 多选（逗号分隔） | 全部 4 项 | 跑哪些自检项 |

### 3.4 4 个子命令的 dispatch 行为（**review.md v0.3.0 S-1 / S-5 / M-2 / M-4 / M-5 / 第四批 S-5 + v1.0.0 P0-1 修复后**）

```
langagent init <name>:
    write_template(target_dir=./<name>, name=<name>)        # F02 提供（review.md M-8 修复：不接收 template 参数）
    # F02 §3.5 内部发射 la.lifecycle.init.start（review.md v2.1.0 P1-2 修复：init.end 不再由 F02 发射）
    print_template_summary(written_files)
    # review.md v2.1.0 P1-2 修复：init 子命令末尾调 exit_handler.cleanup() 走 exit_cleanup 阶段
    #   由 F06 在 step 10 发射 la.lifecycle.init.end（详见 F06 §3.3 init-only cleanup 模式）
    return exit_handler.cleanup(state=None, config=None, *, init_only=True)   # 阶段 6 exit_cleanup（init-only 分支）

langagent run [agent_dir]:
    loaded = dir_loader.load(agent_dir)                                  # 阶段 1 dir_load（F02 内部发射 la.runtime.dir_load.{start, ok, fail}）
    config = config_resolver.resolve(cli_args, agent_dir)                # 阶段 2 config_resolve（F03 内部发射 la.runtime.config_resolve.{start, priority_merge, ok, fail}）
    model = chat_model_factory.create(config)                            # 阶段 3 model_adapt（F10 内部发射 la.runtime.model_adapt.{start, endpoint_probe, ok, fail}）
    config = config.with_model(model)                                    # frozen 实例重建（review.md S-1 修复：用 with_model）
    checkpoint = checkpoint_adapter.create(config)                       # F10（review.md S-5 修复：先 create 再 build）
    graph = state_graph_builder.build(loaded, config, checkpoint)        # 阶段 4 graph_compose（F10 内部发射 la.runtime.graph_compose.{start, middleware_bind, tool_bind, ok, fail}）
                                                                        # review.md v1.1.0 P0-2 修复后：loaded 仅 5 字段（不含 compiled_graph），graph 由 F01 dispatch 独立持有
    state = AgentState(messages=[HumanMessage(input)], ...)
    final_state = main_loop_dispatcher.run_until_done(graph, state, max_turns)  # 阶段 5 main_loop（F05 内部发射 la.lifecycle.run.* 5 个 + la.runtime.main_loop.* 7 个共 12 个 tag；另 1 个 la.cross_cutting.guardrail.block 由 F09 发射，F05 不重发）
    # stdout 输出对话内容（review.md v0.3.0 M-2 修复新增）：
    for msg in final_state["messages"]:
        if isinstance(msg, AIMessage):
            print(format_chat_message(msg.to_dict()), flush=True)         # stdout 行 [assistant] <content>
    return exit_handler.cleanup(final_state, config)                     # 阶段 6 exit_cleanup（F06 内部发射 la.runtime.exit_cleanup.{start, checkpointer_close, report_write, audit_flush, ok, fail}）

langagent eval [agent_dir]:
    # review.md v2.1.0 P1-3 修复后：F01 dispatch eval 与 run dispatch 同构——入口 resolve config 一次，传 F11 runner + cleanup
    loaded = dir_loader.load(agent_dir)                                  # 阶段 1 dir_load（F02）
    config = config_resolver.resolve(cli_args, agent_dir)                # 阶段 2 config_resolve（F03；review.md v2.1.0 P1-3 修复强调：与 run 分支同构）
    # review.md v2.2.0 P2-9 修复：F01 dispatch 显式构造 args dict（避免 F11 跨层 import F01 CliArgs 类型）
    #   args dict schema（与 F11 §3.1 eval.runner 行 §接口契约一致）：
    #   {'cli_args': vars(parse_argv_result), 'grader_only': cli_args.grader_only, 'task': cli_args.task}
    args = {
        'cli_args':     vars(parse_argv_result),                          # CLI 原始参数字典
        'grader_only':  cli_args.grader_only,                            # 5 选 1 字符串；None = 跑全部 grader
        'task':         cli_args.task,                                   # 任务 ID 过滤；None = 跑全部 task
    }
    # review.md v2.1.0 P1-3 修复：F11 runner.run() 签名改为 run(agent_dir, *, config, args)；F11 不再内部 resolve config
    # F11 内部发射 la.lifecycle.eval.{start, case_done, summary}（review.md v0.3.0 S-4 修复；v0.4.0 M-NEW-3 rename）
    # F11 内部发射 la.cross_cutting.event_handler_error（task 失败时；review.md v1.1.0 P1-2 修复改写）
    # F11 内部 publish eval_task_started / eval_task_done 事件（review.md v2.2.0 P2-6 修复明确）
    # runner.run() 返回 EvalRunResult(eval_report, final_state, exit_code)（review.md v0.4.0 M-NEW-1 修复；v0.5.0 统一字段名）
    result = eval_runner.run(agent_dir, *, config=config, args=args)    # F11 Phase 3 runner 整合
    print(format_eval_report_stdout(result.eval_report), flush=True)    # stdout 简洁版
    return exit_handler.cleanup(result.final_state, config, eval_report=result.eval_report)  # 阶段 6 exit_cleanup（review.md v0.5.0 §二.A.1 修复统一路径）

langagent doctor [agent_dir]:
    loaded = dir_loader.load(agent_dir)                                  # 阶段 1（仅读布局）
    config = config_resolver.resolve(cli_args, agent_dir)                # 阶段 2
    # review.md v1.0.0 P0-1 修复：F01 doctor dispatch 不再直接 import primitives
    #   原 v0.3.0 第四批 S-5 修复的 probe_model / probe_checkpoint lambda 写法违反
    #   architecture_modules.md#mod-cli-runner 硬约束（CLI × primitives 黑名单）。
    #   改为调 F05 新增的 build_doctor_probes() 工厂（详见 F05 §3.6a）：
    from langagent.runtime.main_loop_dispatcher import build_doctor_probes
    probe_model_fn, probe_checkpoint_fn = build_doctor_probes()
    checks = exit_handler.run_doctor_checks(
        config, loaded,
        model_probe_fn=lambda: probe_model_fn(config),       # review.md v1.0.0 P0-1 修复：callable 注入（probe 工厂由 F05 提供）
        checkpoint_probe_fn=lambda: probe_checkpoint_fn(config),
    )                                                                         # 4 项 check；F06 实现（F06 §3.7 接受 probe callable）
    snapshot = RuntimeConfigSnapshot.from_runtime_config(config)         # review.md S-2 修复
    report = DoctorReport(checks=results, overall=..., runtime=snapshot) # S-2 修复：runtime 是 Snapshot
    # review.md v0.3.0 M-2 修复：F01 doctor dispatch 写出 DoctorReport 后 stdout 输出
    print(format_doctor_report_stdout(report), flush=True)              # stdout 简洁版
    return exit_handler.cleanup(None, config, doctor_report=report)      # 阶段 6（review.md S-3：传 doctor_report）
```

### 3.5 退出码（**13 个**，严格对齐 workflow.md；**review.md v1.0.0 P2-1 修复**：原 12 个表述已过期，v0.5.0 §四.C-7 新增退出码 67 = `name_already_exists`）

按 `workflow.md` 退出码表实施；具体见 F06 exit_handler 退出码优先级。

#### 各子命令退出码（**review.md v1.0.0 P2-1 修复新增**）

| 子命令 | 场景 | 退出码 |
|---|---|---|
| `langagent init <name>` | 目录创建成功 | 0 |
| `langagent init <name>` | `<name>` 不符合命名约束（正则 `^[a-zA-Z][a-zA-Z0-9_-]*$`） | 2（argparse）或 64（语义层） |
| `langagent init <name>` | cwd 下同名目录已存在 | 67（name_already_exists；workflow.md v0.5.0 §"退出码 67"） |
| `langagent init <name>` | 内置模板加载失败 | 70 |
| `langagent run [agent-dir]` | 6 阶段全部成功 | 0 |
| `langagent run [agent-dir]` | 用户 Ctrl-C | 130 |
| `langagent run [agent-dir]` | 模型 / tool / 护栏等失败（worst_of 仲裁） | 1 / 4 / 70 / 78（按 §三.3 优先级表） |
| `langagent eval [agent-dir]` | 全部 task 通过 | 0 |
| `langagent eval [agent-dir]` | 任一 task 失败（worst_of 仲裁） | 1 / 70 / 78 / 130（按 task 退出码仲裁） |
| `langagent eval [agent-dir]` | `evals/` 目录不存在 | 66（**review.md v2.2.0 P2-1 修复**：与 `workflow.md#langagent-eval` §失败模式 `evals_dir_missing` 对齐；EX_NOINPUT 语义一致性优于 v1.0.0 提出的"0 tasks 非阻塞"设计意图——后者与 POSIX `EX_NOINPUT=66` 冲突。F11 runner 收到 `EvalsDirMissingError` 后立即返回 `EvalRunResult(eval_report=None, final_state=None, exit_code=66)`，由 F01 dispatch 走 `exit_handler.cleanup()` 统一退出码仲裁路径） |
| `langagent doctor [agent-dir]` | 4 项 check 全 ok / 仅 warn / **skipped** | 0（**review.md v2.2.0 P3-1 修复新增**：skipped 状态语义——若某 check 因 probe_fn 未注入（F06 §3.7 `test_doctor_check_model_without_probe_fn_returns_skipped`）返回 `status="skipped"`，F06 `run_doctor_checks()` 不将其计入 overall 失败项；overall 仍是 `ok` / `warn` / `error` 三选一，skipped 单项不影响退出码 0） |
| `langagent doctor [agent-dir]` | 任一 check error（含 `model_endpoint_unreachable` / `config_invalid`） | 1（worst_of 仲裁） |
| `langagent doctor [agent-dir]` | 用户 Ctrl-C | 130 |

> **注**：`langagent eval` 与 `langagent doctor` 的失败码由 F06 `worst_of()` 统一仲裁（详见 F06 §3.3 退出码优先级表 + v0.3.0 M-7 修复）；本表列出典型场景。具体最严重退出码依失败类型决定。
> **review.md v2.2.0 P2-2 修复补充**：退出码仲裁链路：`task 内部失败` → `EvalRunResult.exit_code = worst_of([task_failure_codes + 0])`（F11 runner 内部） → `result.final_state` 传 `exit_handler.cleanup(state, config, eval_report=...)` → `cleanup` 自身聚合 `worst_of([all_failure_codes + 0])`（F06 §3.3 13 级优先级表）→ 返回给 shell。F01 dispatch eval 路径**不直接读** `EvalRunResult.exit_code` 字段（与 v0.5.0 评审 v0.1.0 §二.A.1 修复后统一路径一致）。

### 3.6 日志标签发射（**review.md v0.3.0 S-2 修复明确**：CLI 层严禁直接发射）

F01 **不再直接发射任何 `la.*` tag**（违反 architecture_modules.md#mod-cli-parser 硬约束：`× cross_cutting_logger`）。F01 启动后，用户在终端可观测到以下 tag 由各 feature 按 workflow.md 触发阶段归属发射：

| 子命令 | 启动后用户可观测到以下 tag 出现 | 实际发射方 feature（按 workflow.md 归属） |
|---|---|---|
| `langagent init` | `la.lifecycle.init.start` / `la.lifecycle.init.end` | F02 `runtime_dir_loader.write_template()` |
| `langagent run` | `la.runtime.dir_load.{start,ok,fail}` + `la.runtime.config_resolve.{start,priority_merge,ok,fail}` + `la.runtime.model_adapt.{start,endpoint_probe,ok,fail}` + `la.runtime.graph_compose.{start,middleware_bind,tool_bind,ok,fail}` + `la.lifecycle.run.{start,turn,tool_call,tool_result,model_response}` + `la.runtime.main_loop.{start,turn.start,turn.end,model_call,tool_call,tool_result,end}` + `la.cross_cutting.guardrail.block`（如触发） + `la.runtime.exit_cleanup.{start,checkpointer_close,report_write,audit_flush,ok,fail}` | F02 / F03 / F05 / F06 / F09 / F10 |
| `langagent eval` | `la.lifecycle.eval.start` / `la.lifecycle.eval.case_done` / `la.lifecycle.eval.summary` | F11 `eval/runner.run()` / `_run_one_task()` |
| `langagent doctor` | `la.lifecycle.doctor.check` / `la.lifecycle.doctor.report` | F06 `runtime_exit_handler.run_doctor_checks()` / `cleanup()` |

> F01 dispatch **不调用** `cross_cutting_logger.emit()`；F01 仅通过 stdout 输出对话内容（review.md v0.3.0 M-2 修复）、格式化报告（review.md v0.3.0 M-2 修复）、编排 probe 函数（**review.md v1.0.0 P0-1 修复**：probe 工厂由 F05 `build_doctor_probes()` 提供；F01 不再直接 import `chat_model_factory` / `checkpoint_adapter`，避免违反 `architecture_modules.md#mod-cli-runner` 的 CLI × primitives 黑名单）。所有 `la.*` tag 由 F02 / F03 / F05 / F06 / F07 / F08 / F09 / F10 / F11 9 个 feature 发射；F08 logger 提供 `emit()` 接口与 ≥**46** 项白名单校验（详见 F08 prompt §3.3）。

## 四、TDD 测试用例先行

### 4.1 `cli_parser` 测试

- [ ] `test_build_parser_has_4_subcommands`：parser 含 4 个子命令（`init` / `run` / `eval` / `doctor`）。
- [ ] `test_build_parser_no_extra_subcommands`：不含 `version` / `tui` / `serve` / `clean` 等。
- [ ] `test_parse_init_name`：解析 `langagent init demo` → `args.subcommand == "init"`, `args.name == "demo"`。
- [ ] `test_parse_init_name_invalid`：解析 `langagent init ..` → argparse 报错，退出码 2。
- [ ] `test_parse_run_with_agent_dir`：解析 `langagent run /tmp/myagent` → `args.agent_dir == "/tmp/myagent"`。
- [ ] `test_parse_run_with_overrides`：解析 `langagent run --model gpt-4o --checkpointer sqlite` → cli_args 含对应字段。
- [ ] `test_parse_eval_with_grader_only`：解析 `langagent eval --grader-only llm_judge` → cli_args.grader_only == "llm_judge"。
- [ ] `test_parse_doctor_with_checks`：解析 `langagent doctor --checks model,checkpointer` → cli_args.checks == ["model", "checkpointer"]`。
- [ ] `test_ns_to_cli_args_returns_dict`：argparse Namespace → dict 转换；值类型与 RuntimeConfig.cli_args 兼容。
- [ ] `test_unknown_flag_returns_exit_code_2`：`langagent run --unknown-flag` → argparse SystemExit(2)。

### 4.2 `cli_runner.dispatch` 测试

- [ ] `test_dispatch_init_calls_write_template`：mock `runtime_dir_loader.write_template` → 调用 1 次。
- [ ] `test_dispatch_run_calls_6_stages`：mock 6 个 runtime 模块 → 全部按顺序调用 1 次。
- [ ] `test_dispatch_eval_returns_eval_runner_exit_code`：mock `eval_runner.run` → 返回其 exit code。
- [ ] **`test_dispatch_eval_returns_cleanup_exit_code`**（**review.md v1.1.0 P2-10 修复改写**：原 `test_dispatch_eval_returns_eval_runner_exit_code` 语义与 v0.5.0 评审 v0.1.0 §二.A.1 修复后"runner.run().exit_code 字段不直接由 dispatch 返回"冲突）：mock `eval_runner.run` 返回 `EvalRunResult(eval_report=mock_report, final_state=mock_state, exit_code=0)` + mock `exit_handler.cleanup` 返回 0 → dispatch eval 后返回 0；mock `eval_runner.run` 返回 `EvalRunResult(exit_code=70)` + mock `exit_handler.cleanup` 返回 70 → dispatch eval 后返回 70（cleanup worst_of 仲裁）；验证 F01 dispatch 不读 `result.exit_code`，统一走 cleanup 路径。
- [ ] `test_dispatch_doctor_runs_4_checks`：mock 4 个 check 函数 → 全部调用。
- [ ] `test_dispatch_returns_exit_code_0_on_success`：所有 mock 成功 → 返回 0。
- [ ] `test_dispatch_returns_propagated_exit_code`：mock runtime 抛 `AgentDirNotFoundError` → 返回 66。
- [ ] `test_dispatch_handles_keyboard_interrupt`：mock main_loop 抛 `KeyboardInterrupt` → 返回 130。
- [ ] `test_dispatch_main_entry_calls_dispatch`：`main()` 函数 → `sys.argv` 解析 → `dispatch()` 调用。

### 4.3 `cli_output_formatter` 测试

- [ ] `test_format_eval_report_table`：mock EvalReport → 输出含 ASCII 表格 + 通过率 + 延迟。
- [ ] `test_format_eval_report_json`：指定 `--report-format json` → 输出合法 JSON 字符串。
- [ ] `test_format_doctor_report`：mock DoctorReport → 输出含每项 check 状态 + 总体结论。
- [ ] `test_format_event_stream`：mock Event 流 → 逐条格式化（时间戳 + tag + 简短 payload）。
- [ ] `test_format_disables_color_when_no_tty`：`os.isatty(stdout) == False` → 输出无 ANSI 色码。
- [ ] `test_format_enables_color_when_tty`：`os.isatty(stdout) == True` → 输出含 ANSI 色码。
- [ ] `test_format_truncates_long_payload`：payload > 1 KB → 截断到 200 字符 + `...`。
- [ ] `test_format_never_logs_secrets`：payload 含 `api_key` → 输出脱敏。

#### 4.3a stdout 格式化测试（**review.md v0.3.0 M-2 修复新增**）

- [ ] `test_format_chat_message_returns_assistant_line`：输入 `{"type": "ai", "content": "Hello, Alice!"}` → 输出 `"[assistant] Hello, Alice!\n"`。
- [ ] `test_format_chat_message_handles_tool_calls`：输入含 `tool_calls` 字段 → 输出 `[assistant] (tool_call: echo("hi"))`。
- [ ] `test_format_chat_message_handles_empty_content`：输入 `content=""` → 输出空行（不抛异常）。
- [ ] `test_format_eval_report_stdout_compact`：mock 10 task 7 pass → 输出简洁 ASCII 表格（≤10 行）。
- [ ] `test_format_eval_report_stdout_does_not_print_secrets`：EvalReport 含 `token_usage` → stdout 不打印原始 token 值，仅打印 `tokens: qwen3-8b=230`。
- [ ] `test_format_doctor_report_stdout_shows_4_checks`：mock 4 项 check 全 ok → 输出 `"✓ model: ok"` 等 4 行 + `"overall: ok"`。

#### 4.3b dispatch stdout 输出测试（**review.md v0.3.0 M-2 修复新增**）

- [ ] `test_dispatch_run_prints_chat_to_stdout`：构造 LoadedAgent + mock F05 run_until_done → F01 dispatch run 后 capture stdout 含 `[assistant] ...`。
- [ ] `test_dispatch_eval_prints_report_to_stdout`：mock F11 eval_runner.run 返回 EvalReport → F01 dispatch eval 后 stdout 含通过率。
- [ ] `test_dispatch_doctor_prints_report_to_stdout`：构造 DoctorReport → F01 dispatch doctor 后 stdout 含 4 项 check 状态。
- [ ] `test_dispatch_run_stderr_only_logs_no_chat`：mock 所有 emitter → capture stderr 含 `la.*` tag；capture stdout 仅含 `[assistant] ...`，无 `la.*`。
- [ ] `test_dispatch_cli_does_not_import_logger`：静态检查（ast.Import 解析）`langagent/cli/runner.py` 与 `langagent/cli/output_formatter.py` 不 import `langagent.cross_cutting.logger`。

### 4.4 端到端 CLI 测试

- [ ] `test_cli_init_creates_directory`：subprocess.run `langagent init demo` → 当前目录有 `demo/` 子目录 + stdout 含创建摘要。
- [ ] `test_cli_doctor_on_fresh_agent`：subprocess.run `langagent doctor demo` → exit code 0 + stdout 含 `model` / `checkpointer` / `skills` / `instructions` 4 项结果。
- [ ] `test_cli_run_with_mock_model`：构造 demo agent 含 fake model endpoint → `langagent run demo --max-turns 1` 跑 1 轮 + capture stdout 含 `[assistant] ...`。
- [ ] `test_cli_help`：subprocess.run `langagent --help` / `langagent run --help` / `langagent init --help` 等 → 输出含所有参数说明。
- [ ] `test_cli_unknown_subcommand`：`langagent foo` → argparse 报错，exit code 2。
- [ ] `test_cli_run_stdout_does_not_contain_la_tags`（**review.md v0.3.0 M-2 修复新增**）：subprocess.run `langagent run demo --max-turns 1` → capture stdout 不含 `la.*`（仅 stderr 含）。

## 五、关键约束

1. **仅 4 个核心子命令**：不预留 `version` / `tui` / `serve` / `clean` / `chat` 等辅助子命令（宪法第 XI 条 2 款 + workflow.md Q5 澄清）。
2. **CLI 不接触磁盘 / 模型 / LangGraph**：所有 IO 与模型实例化在 runtime / primitives 层；CLI 仅解析 + 分发 + 打印。
3. **CLI 严禁直接发射 `la.*` tag**（review.md v0.3.0 S-2 修复明确，architecture_modules.md#mod-cli-parser 硬约束）：F01 dispatch **不得 import `langagent.cross_cutting.logger`**；所有 13 个 cli.* tag 由 runtime / protocol / cross_cutting 各 feature 发射，F01 仅作为入口编排。
4. **依赖方向**：cli → runtime → protocol / cross_cutting / primitives；cli 不得反向依赖 primitives 内部细节（仅通过 runtime API 间接调用）。
5. **stderr = 日志 / stdout = 用户输出**：语义分离（workflow.md run 命令约定）；F01 dispatch 用 `print(format_chat_message(...), flush=True)` 等写入 stdout，用 cli_output_formatter 系列 API 格式化（review.md v0.3.0 M-2 修复明确）。
6. **退出码刚性**：12 个退出码严格对应 workflow.md 退出码表；任何失败必须按规则返回码。
7. **不依赖 LangSmith**：CLI 不读取 LangSmith env；不调用 LangSmith SDK。
9. **TDD 刚性**：先 Red 后 Green 再 Refactor；端到端 CLI 测试可用 subprocess.run 隔离。
10. **doctor 编排注入 probe 函数**（review.md v0.3.0 第四批 S-5 修复 + **v1.0.0 P0-1 修复**）：F01 doctor dispatch **通过 F05 `build_doctor_probes()` 工厂**取得 `probe_model_fn` / `probe_checkpoint_fn`，把两个 probe（`lambda: probe_model_fn(config)` / `lambda: probe_checkpoint_fn(config)`）注入到 F06 `run_doctor_checks(*, model_probe_fn=, checkpoint_probe_fn=)`；**F01 自身不直接 import `langagent.primitives.chat_model_factory` 或 `langagent.primitives.checkpoint_adapter`**（CLI × primitives 黑名单，architecture_modules.md#mod-cli-runner 硬约束）；F06 不直接 import primitives（保留 S-5 修复成果）。F05 是 probe 工厂的天然归属——runtime 层依赖 primitives 是 matrix 允许的，且 F05 已是 primitives 层的消费方（通过 `primitives_state_graph_builder.build()`）。
11. **第 XV 条对齐清单**：与宪法第 I 条（项目身份 — 仅 2 种入口）/ 第 XI 条（打包 — 4 个核心子命令）/ 第 XII 条 2 款（启动日志）/ 第 XIII 条逐项对齐。

## 六、本 feature 不包含

- 不实现 6 阶段本身（→ F02-F06）。
- 不实现 EvalTaskSpec 加载（→ F11）。
- 不实现模型实例化（→ F10）。
- 不实现 checkpointer 实例化（→ F10）。
- 不实现 event_bus / logger / audit（→ F07 / F08 / F09，本 feature 仅调用其 API）。

## 七、Deliverable 清单

- [ ] `langagent/cli/runner.py` + `parser.py` + `output_formatter.py` 3 个模块。
- [ ] `langagent/__main__.py`：PyInstaller / `python -m langagent` 入口。
- [ ] `tests/cli/test_parser.py` + `test_runner.py` + `test_output_formatter.py`：≥39 个测试用例（review.md v0.3.0 M-2 修复后增补：原 25 个 + §4.3a 6 个 stdout 格式化测试 + §4.3b 5 个 dispatch stdout 输出测试 + §4.4 增补 1 个 stdout 不含 la.* 测试 + §3.4 dispatch 重写 - 0 个 = 36 个；含 §4.3 原 8 个 = ≥36 个，按 39 个目标）。
- [ ] `tests/cli/test_cli_end_to_end.py`：≥6 个 subprocess 端到端测试（含 review.md v0.3.0 M-2 修复后 stdout 验证）。
- [ ] `mypy --strict` 通过。
- [ ] spec / plan / tasks 顶部引用宪法第 XV 条。

## 八、与其它 feature 的边界

- **F02**：F01 在 init / run / eval / doctor 中调用 `dir_loader.write_template` 或 `dir_loader.load`；F02 内部发射 `la.lifecycle.init.start` 与 `la.runtime.dir_load.{start,ok,fail}`（F01 不发射；v0.4.0 M-NEW-3 rename；**review.md v2.1.0 P1-2 修复**：F02 不再发射 `la.lifecycle.init.end`，该 tag 改由 F06 `cleanup()` 在 init 子命令末尾的 exit_cleanup 阶段统一发射）。
- **F03**：F01 在 run / eval / doctor 中调用 `config_resolver.resolve(cli_args, agent_dir)`；F03 内部发射 `la.runtime.config_resolve.{start,priority_merge,ok,fail}`。
- **F05**：F01 在 run 中调用 `main_loop_dispatcher.run_until_done(graph, state)`；F05 内部发射 `la.lifecycle.run.*` 5 个 + `la.runtime.main_loop.*` 7 个 tag；F01 run dispatch 把 `final_state["messages"]` 写入 stdout（review.md v0.3.0 M-2 修复；v0.4.0 M-NEW-3 rename；v0.5.0 §三.B.1 修正 lifecycle.run.* 5 个而非 6 个）。
- **F06**：F01 在所有子命令结束后调用 `exit_handler.cleanup(state, config, *, doctor_report=, eval_report=, init_only=False)`；F06 内部发射 `la.runtime.exit_cleanup.{start,checkpointer_close,report_write,audit_flush,ok,fail}` + init-only 分支发 `la.lifecycle.init.end`（**review.md v2.1.0 P1-2 修复新增**）；F01 doctor 编排 `probe_model` / `probe_checkpoint` lambda 注入到 F06 `run_doctor_checks()`（review.md v0.3.0 第四批 S-5 修复）；F01 init dispatch 末尾传 `init_only=True` 走极简分支。
- **F10**：F01 直接调用 `chat_model_factory.create()` + `checkpoint_adapter.create()` + `state_graph_builder.build()`（review.md v0.3.0 S-5 修复：F01 dispatch 显式调用三步）；F10 内部发射 9 个 model_adapt / graph_compose tag（review.md v0.3.0 S-1 修复明确）。
- **F11**：F01 在 eval 中委托 `eval_runner.run(agent_dir, *, config, args)`（**review.md v2.1.0 P1-3 修复**：F01 dispatch 入口 resolve config 后通过 keyword-only `config` 参数注入 runner；F11 runner 不再内部 resolve）；F11 内部发射 `la.lifecycle.eval.{start,case_done,summary}`（review.md v0.3.0 S-4 修复；v0.4.0 M-NEW-3 rename）；F01 dispatch eval 后 stdout 输出 EvalReport（review.md v0.3.0 M-2 修复；v0.4.0 M-NEW-1 修复后返回 `EvalRunResult` 含 `(eval_report, final_state, exit_code)`；v0.5.0 字段名统一为 `final_state`；F01 §3.4 eval dispatch 走 `exit_handler.cleanup()` 统一路径，与 `langagent run` dispatch 同构）。