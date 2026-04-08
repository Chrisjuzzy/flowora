# Agent Brain Architecture

This document describes the Agent Brain system for the Flowora backend, including reasoning loop, tools, memory, swarm orchestration, and execution logging.

**Core Modules**
- `apps/backend/services/agent_runtime/runtime.py` orchestrates persistence, sandbox validation, and AI provider selection.
- `apps/backend/services/agent_runtime/brain.py` implements the reasoning loop, tool selection, and evaluation.
- `apps/backend/services/agent_runtime/planner.py` generates step-by-step plans.
- `apps/backend/services/agent_runtime/memory.py` provides layered memory retrieval and storage.
- `apps/backend/tools/tool_registry.py` defines the tool registry and built-in tool stubs.
- `apps/backend/services/workflow_runner.py` provides coordinator/worker/reviewer swarm execution.
- `apps/backend/services/agent_runtime/execution_logger.py` writes structured execution logs.
- `apps/backend/models/execution_log.py` stores execution log records.

**Reasoning Loop**
1. Receive task input and load agent configuration.
2. Retrieve memory context from layered memory.
3. Build a plan with `PlanGenerator`.
4. Iterate through plan steps, invoking the LLM with tool list and scratchpad.
5. Execute tool calls when requested and append observations.
6. Evaluate outputs and continue until goal achieved or max steps reached.
7. Persist execution, logs, memory, and reflections.

**Tool System**
Each tool defines:
- `name`
- `description`
- `input_schema`
- `execution handler`

Built-in tools are registered in `apps/backend/tools/tool_registry.py`:
- `web_search`
- `http_request`
- `code_execution`
- `database_query`
- `document_analysis`
- `automation_task`

Tool handlers can accept an optional context object, enabling safe access to runtime details like `db` and `agent_id`.

**Memory System**
Layered memory is combined into a single context block.
- Short-term memory is the runtime scratchpad from the current run.
- Conversation memory uses recent `AgentRun` records.
- Long-term memory uses `MemoryService` and `AgentMemory`.
- Vector knowledge base uses `VectorMemoryService` semantic search.

**Planning Engine**
`PlanGenerator` produces a JSON array of steps:
- Step index
- Description
- Optional tool hint
- Optional expected output

Plans are logged and reused throughout the reasoning loop.

**Reflection System**
After each run:
- `SelfImprovementService.write_agent_memory` stores outcome data.
- `ReflectionService.reflect_on_execution` generates critique and improvement suggestions.
- `EvolutionService` can propose prompt changes when confidence is low.

**Swarm Orchestration**
Coordinator, worker, reviewer roles are implemented in `apps/backend/services/workflow_runner.py`.
- Coordinator generates task list.
- Workers execute tasks and report results.
- Reviewer validates outputs and returns final answer.

Swarm responses include:
- `final`
- `tasks`
- `worker_results`
- `review`
- `round_summaries`

**Execution Logging**
Execution steps are logged with:
- `step`
- `phase`
- `message`
- `payload`
- `timestamp`

Logs are stored in `execution_logs` for observability and debugging.
