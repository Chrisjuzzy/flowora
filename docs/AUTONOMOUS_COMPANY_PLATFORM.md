# Autonomous AI Company Platform

This document describes the autonomous company extensions for Flowora.

**New Services**
- `services/agent_generator.py` creates agents from goals using templates and planning.
- `services/agent_optimizer.py` improves prompts based on execution logs and success rates.
- `services/product_generator.py` builds market-informed agents and workflows, then auto-publishes.
- `services/company_mode.py` coordinates multi-agent roles (CEO, Planner, Developer, Marketing, Support).
- `services/autonomous_workflows.py` generates workflow graphs from goals.
- `services/tool_permissions.py` enforces tool permissions per agent.
- `services/marketplace_autopublish.py` auto-publishes agents to marketplace.

**New Models**
- `models/agent_template.py` provides reusable agent templates.
- `models/agent_tool_permission.py` tracks tool access control.
- `models/execution_log.py` stores step-level execution logs.

**New Endpoints**
- `POST /autonomy/agent-generation` generate new agent from a goal.
- `POST /autonomy/agents/{agent_id}/optimize` optimize prompts from execution logs.
- `POST /autonomy/products/generate` generate and publish a SaaS product agent.
- `POST /autonomy/workflows/generate` auto-create a workflow graph.
- `POST /autonomy/company/run` run company-mode coordination.
- `POST /autonomy/agents/{agent_id}/tools` set tool permissions.
- `GET /autonomy/templates` list agent templates.
- `POST /autonomy/templates` create new agent template.
- `GET /analytics/agents/{agent_id}/success-rate` agent success rate.
- `GET /analytics/agents/{agent_id}/tool-performance` tool usage stats.
- `GET /analytics/summary` platform execution completion rate.

**Autonomous Agent Generation Flow**
1. Goal submitted.
2. Plan generated via `PlanGenerator`.
3. Agent spec created from templates + tool registry.
4. Agent stored with encrypted config and version snapshot.
5. Tool permissions registered.
6. Optional auto-publish to marketplace.

**Self-Improving Loop**
1. Execution logs recorded (`execution_logs`).
2. Optimizer computes success rate and latency metrics.
3. Prompt is updated and versioned.
4. Agent version increments (patch bump).

**Company Mode**
- Coordinator (CEO) + Planner + Developer + Marketing + Support agents.
- Planner breaks goal into tasks.
- Workers execute tasks.
- CEO aggregates outputs into a final plan.

**Example Autonomous Workflow Output**
```json
{
  "goal": "Launch a competitor analysis SaaS",
  "workflow": {
    "name": "Auto Workflow: Launch a competitor analysis SaaS",
    "nodes": [
      {"id": "start", "type": "input", "label": "Trigger"},
      {"id": "agent-1", "type": "agent", "label": "Research Competitors"},
      {"id": "agent-2", "type": "agent", "label": "Design Product Workflow"},
      {"id": "end", "type": "output", "label": "Final Report"}
    ],
    "edges": [
      {"source": "start", "target": "agent-1"},
      {"source": "agent-1", "target": "agent-2"},
      {"source": "agent-2", "target": "end"}
    ]
  }
}
```
