# Implementation Plan: Eval Subsystem (F11)

**Branch**: `011-eval-subsystem` | **Date**: 2026-09-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/011-eval-subsystem/spec.md`

**Constitutional Alignment**: This plan aligns with Constitution Article XV (Top-Level Design Primacy). Required artifacts from `harness/top_level_design/` have been reviewed:
- `workflow.md` — 6 stages, eval lifecycle, exit codes
- `architecture_modules.md` — 21-module dependency matrix, eval_runner module
- `module_schemas.md` — EvalTaskSpec/EvalReport/EvalRunResult schemas

## Summary

Implement the `langagent eval` subcommand end-to-end evaluation pipeline: load EvalTaskSpec from `<agent-dir>/evals/*.yaml`, execute agent for each task input via F08 main_loop, grade outputs using 5 grader types (exact_match, contains, regex, llm_judge, tool_call_match), aggregate results into EvalReport with pass rate and performance metrics, persist to `~/.local/share/langagent/reports/`, emit lifecycle events, and return exit code based on worst failure.

**Technical Approach**: Create new `langagent/eval/` package with 3-phase development (Phase 1: task_loader + report_aggregator, Phase 2: 5 graders, Phase 3: runner integration). Implement eval_runner as 21st module in dependency matrix, consuming F06 dir_loader, F07 RuntimeConfig, F08 main_loop_dispatcher, F03 event_bus, F02 logger, F01 chat_model_factory. Follow TDD with ≥50 test cases across 6 test files.

## Technical Context

**Language/Version**: Python 3.11+ (per pyproject.toml requires-python field)

**Primary Dependencies**: 
- LangChain (BaseChatModel abstraction for llm_judge grader)
- LangGraph (CompiledStateGraph execution via F08)
- Pydantic 2.x (schema validation)
- PyYAML (evals parsing)
- pytest (TDD framework per Constitution Article VIII)

**Storage**: 
- Read: agent-dir/evals/*.yaml
- Write: ~/.local/share/langagent/reports/agent-name-timestamp.json
- No database

**Testing**: pytest with 50+ test cases (10 task_loader + 15 grader + 16 runner + 4 aggregator + 4 CLI + 5 logger)

**Target Platform**: Linux server (primary), macOS/Windows (secondary)

**Project Type**: CLI tool (langagent eval subcommand)

**Performance Goals**: 
- 50-task suite in under 5 minutes
- Timeout terminates within 2s of threshold
- Filters reduce time by 80%+ for 10% subset

**Constraints**:
- No LangSmith dependency (Constitution Article III)
- Independent model instance for llm_judge (avoid judge bias)
- Individual task failures must not halt suite
- Real LangGraph execution (no mocking per Article VIII)
- Exit code = max of all task exit codes

**Scale/Scope**:
- 5 grader types (exact_match, contains, regex, llm_judge, tool_call_match)
- Support 100+ tasks per suite
- 8-field EvalTaskSpec, 9-field EvalReport

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Article I: Project Identity (PASS)
- ✅ F11 is a CLI subcommand (`langagent eval`), not an SDK
- ✅ No importable API exposed to third parties
- ✅ User interface: binary command + YAML config in agent directory

### Article III: LangSmith Isolation (PASS)
- ✅ No LangSmith imports in eval pipeline
- ✅ Graders implemented locally (5 types, no cloud dependency)
- ✅ Optional Langfuse integration deferred to v2 (v1 fully local)

### Article IV: Model Abstraction (PASS)
- ✅ llm_judge uses BaseChatModel interface via F01 chat_model_factory
- ✅ Independent model instance for judge (avoid bias, spec §五.4)
- ✅ No direct provider SDK calls

### Article V: Agent Directory Contract (PASS)
- ✅ Eval tasks in `<agent-dir>/evals/*.yaml` (optional directory per spec)
- ✅ No modification to agent directory structure
- ✅ Missing evals/ directory returns empty task list (graceful, spec §四.1)

### Article VI: Agent Loop & State (PASS)
- ✅ F08 main_loop_dispatcher.run_until_done() drives real LangGraph execution
- ✅ AgentState used as-is, no schema changes
- ✅ No mock of LangGraph behavior (Constitution Article VIII §4)

### Article VIII: TDD Rigidity (PASS)
- ✅ 50+ test cases written before implementation (spec §四)
- ✅ Red-Green-Refactor workflow enforced
- ✅ 3-phase development with phase-gated testing

### Article IX: Quality Diagnostics (PASS)
- ✅ Evaluation capability: EvalReport with pass_rate/latency/cost
- ✅ Monitoring: MetricsSnapshot per task (F02 metrics_collector subscribes)
- ✅ Testing: pytest framework with TDD coverage

### Article X: Security & Privacy (PASS)
- ✅ No data exfiltration (eval runs locally)
- ✅ llm_judge respects guardrail policy (independent model instance)
- ✅ No PII exposure in eval reports (spec FR-007)

### Article XV: Top-Level Design Primacy (PASS)
- ✅ workflow.md: eval lifecycle stages, exit codes, log tags verified
- ✅ architecture_modules.md: eval_runner as 21st module in 21×21 matrix
- ✅ module_schemas.md: EvalTaskSpec v0.2.0, EvalReport, EvalRunResult schemas

**Constitution Check Result**: ✅ ALL GATES PASS

No violations. No complexity tracking needed.

## Project Structure

### Documentation (this feature)

```text
specs/011-eval-subsystem/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── eval_task_spec_schema.yaml
│   ├── eval_report_schema.yaml
│   └── grader_interface.md
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
langagent/
├── eval/                                    # NEW: F11 eval subsystem package
│   ├── __init__.py
│   ├── task_loader.py                       # Phase 1: load evals/*.yaml
│   ├── report_aggregator.py                 # Phase 1: aggregate TaskResult → EvalReport
│   ├── runner.py                            # Phase 3: eval_runner (21st module)
│   └── graders/                             # Phase 2: 5 grader implementations
│       ├── __init__.py                      # grader registry/router
│       ├── exact_match.py
│       ├── contains.py
│       ├── regex.py
│       ├── llm_judge.py
│       └── tool_call_match.py
├── cli/
│   └── runner.py                            # F10: dispatch() adds eval branch
├── runtime/
│   ├── dir_loader.py                        # F06: load() used by eval runner
│   ├── config_resolver.py                   # F07: RuntimeConfig consumed by eval
│   ├── main_loop_dispatcher.py              # F08: run_until_done() per task
│   └── exit_handler.py                      # F09: cleanup() writes EvalReport
├── protocol/
│   └── event_bus.py                         # F03: publish eval_task_started/done
├── cross_cutting/
│   ├── logger.py                            # F02: emit la.lifecycle.eval.* tags
│   └── metrics_collector.py                 # F02: subscribe to task events
└── primitives/
    └── chat_model_factory.py                # F01: create() for llm_judge

tests/
├── eval/                                    # NEW: F11 test suite
│   ├── test_task_loader.py                  # 10 tests (§4.1)
│   ├── test_report_aggregator.py            # 4 tests (§4.4)
│   ├── test_runner.py                       # 16 tests (§4.3)
│   ├── test_cli_eval_integration.py         # 4 tests (§4.5)
│   └── graders/
│       ├── test_exact_match.py              # 3 tests
│       ├── test_contains.py                 # 3 tests
│       ├── test_regex.py                    # 3 tests
│       ├── test_llm_judge.py                # 3 tests
│       └── test_tool_call_match.py          # 3 tests
└── fixtures/
    └── agent-with-evals/                    # Test fixture
        ├── instructions.md
        ├── agent.py
        └── evals/
            ├── task_001.yaml
            ├── task_002.yaml
            └── task_003.yaml
```

**Structure Decision**: Single project structure with new `langagent/eval/` package. F11 integrates horizontally across existing 5 layers (cli/runtime/protocol/cross_cutting/primitives) without introducing new layers. The eval_runner module is the 21st module in the dependency matrix, consuming F06/F07/F08/F03/F02/F01 without reverse dependencies.

## Complexity Tracking

**Not Required**: No Constitution violations. All gates pass.

---

## Phase 0: Outline & Research

*DELIVERABLE: research.md - resolve all unknowns before design*

**Status**: ✅ COMPLETE

### Research Summary

All technical unknowns resolved. See [research.md](./research.md) for full details.

**Key Decisions Made**:

1. **Grader Implementation Pattern**: Registry-based strategy pattern with uniform `grade()` interface
2. **Task Timeout Mechanism**: ThreadPoolExecutor with timeout parameter (cross-platform)
3. **LLM Judge Independence**: Independent BaseChatModel instance per eval run, not per task
4. **Exit Code Aggregation**: `max(all_task_exit_codes + [0])` preserves highest severity
5. **Tool Call Matching**: Name exact match + args subset comparison
6. **Event Bus Integration**: Publish at task boundaries for real-time metrics
7. **Report Persistence**: platformdirs.user_data_dir() for cross-platform OS conventions

**Research Items Resolved**: 7/7
- ✅ Grader pluggability patterns
- ✅ Timeout implementation (no async complexity)
- ✅ Independent judge model instantiation
- ✅ Exit code worst-of strategy
- ✅ Tool call matching algorithm
- ✅ Event bus payload structure
- ✅ Cross-platform report path resolution

---

## Phase 1: Design & Contracts

*DELIVERABLE: data-model.md, contracts/, quickstart.md*

**Status**: ✅ COMPLETE

### Artifacts Generated

1. **[data-model.md](./data-model.md)**: 5 entities with validation rules and state transitions
   - EvalTaskSpec (Pydantic, frozen, 8 fields including case_sensitive)
   - TaskResult (dataclass, frozen, 7 fields)
   - EvalReport (Pydantic, frozen, 9 fields)
   - EvalRunResult (dataclass, frozen, 3 fields)
   - GraderRegistry (dict, immutable after load)

2. **[contracts/eval_task_spec_schema.yaml](./contracts/eval_task_spec_schema.yaml)**: YAML schema v0.2.0
   - 5 grader enum values
   - Field constraints and validation rules
   - 5 example YAML files
   - Error mapping to exit codes

3. **[contracts/eval_report_schema.json](./contracts/eval_report_schema.json)**: JSON schema v0.1.0
   - 9 top-level fields
   - task_results array structure
   - Aggregated metrics (pass_rate, p50/p95 latency, token_usage, cost_usd)
   - File naming convention

4. **[contracts/grader_interface.md](./contracts/grader_interface.md)**: Uniform grader contract
   - 5 grader function signatures
   - Parameter specifications and logic
   - Registry interface pattern
   - Error handling and testing requirements

5. **[quickstart.md](./quickstart.md)**: 6 validation scenarios
   - Basic eval run (pass/fail mix)
   - All tasks pass (exit code 0)
   - Task timeout enforcement
   - Filter by grader type
   - LLM judge semantic matching
   - Tool call validation

### Design Decisions Summary

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Entity Immutability | All frozen (Pydantic/dataclass) | Constitution Article VI reducer constraints |
| Grader Registration | Dict-based registry | Runtime selection, extensible, testable |
| Report Persistence | platformdirs.user_data_dir() | Cross-platform OS conventions |
| Timeout Strategy | ThreadPoolExecutor | Non-invasive, cross-platform |
| Exit Code | max(all_exit_codes + [0]) | Preserves highest severity |

### Constitution Re-Check (Post-Design)

**Result**: ✅ ALL GATES STILL PASS

- Article I (Project Identity): CLI subcommand, not SDK ✅
- Article III (LangSmith Isolation): No LangSmith imports ✅
- Article V (Agent Directory): evals/ optional, no modifications ✅
- Article VI (State): All entities frozen/immutable ✅
- Article VIII (TDD): 50+ tests specified before implementation ✅

---

## Next Steps

**Phase 2**: Task breakdown (`/speckit.tasks`)

The implementation plan is complete. All design artifacts are ready for task breakdown:
- Data models defined with validation rules
- Contracts specify YAML/JSON schemas and grader interfaces
- Quickstart provides 6 runnable validation scenarios
- Constitution compliance verified pre- and post-design

Ready to proceed with `/speckit.tasks` to generate task breakdown for 3-phase implementation:
- Phase 1: task_loader + report_aggregator (parallel with F02/F03/F05)
- Phase 2: 5 graders (parallel PRs)
- Phase 3: eval_runner integration (after F06/F07/F08/F09/F10)
