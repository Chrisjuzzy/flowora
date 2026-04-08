from sqlalchemy.orm import Session
from models import Workflow, Agent
from services.agent_runner import run_agent
from services.intelligence_service import MessagingDelegationService, WorkspaceMemoryService, ConflictResolver
import logging
from typing import List, Optional, Dict, Any
import json
import time
from config_production import settings

logger = logging.getLogger(__name__)

async def run_workflow(db: Session, workflow_id: int, initial_input: str = None):
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise ValueError("Workflow not found")
    
    config = workflow.config_json
    if not config or "steps" not in config:
        raise ValueError("Invalid workflow configuration: missing 'steps'")
    
    steps = config["steps"]
    if len(steps) > settings.WORKFLOW_MAX_DEPTH:
        raise ValueError("Workflow depth exceeds maximum allowed steps")
    current_input = initial_input
    results = []
    start_time = time.monotonic()
    recent_agents: List[int] = []

    for i, step in enumerate(steps):
        if (time.monotonic() - start_time) > settings.WORKFLOW_MAX_EXECUTION_SECONDS:
            raise TimeoutError("Workflow execution time exceeded")
        agent_id = step.get("agent_id")
        if not agent_id:
            logger.warning(f"Step {i} missing agent_id, skipping")
            continue

        recent_agents.append(agent_id)
        if len(recent_agents) >= 6 and recent_agents[-3:] == recent_agents[-6:-3]:
            raise ValueError("Detected repeated agent cycle; terminating workflow")
            
        # Run agent
        try:
            execution = await run_agent(db, agent_id, input_data=current_input)
            results.append({
                "step": i,
                "agent_id": agent_id,
                "status": execution.status,
                "result": execution.result
            })
            
            # Pass result as input to next step if successful
            if execution.status == "completed":
                current_input = execution.result
            else:
                # Stop if step fails? Or continue? For now, stop.
                break
        except Exception as e:
            results.append({
                "step": i,
                "agent_id": agent_id,
                "status": "failed",
                "error": str(e)
            })
            break
            
    return {
        "workflow_id": workflow_id,
        "status": "completed" if all(r["status"] == "completed" for r in results) else "failed",
        "steps_results": results,
        "final_output": current_input
    }

# --- Swarm Orchestration ---
async def run_swarm(
    db: Session,
    agent_ids: List[int],
    goal: str,
    workspace_id: Optional[int] = None,
    max_rounds: int = 3
) -> Dict[str, Any]:
    """
    Coordinator / Worker / Reviewer swarm:
    - Coordinator breaks the goal into tasks
    - Workers execute tasks in parallel (round-robin assignment)
    - Reviewer validates and merges results into a final answer
    """
    if not agent_ids:
        raise ValueError("agent_ids cannot be empty")

    coordinator_id = agent_ids[0]
    reviewer_id = agent_ids[-1] if len(agent_ids) > 1 else coordinator_id
    worker_ids = agent_ids[1:-1] if len(agent_ids) > 2 else [coordinator_id]

    def _extract_json_list(text: str) -> List[str]:
        if not text:
            return []
        start = text.find("[")
        end = text.rfind("]")
        if start == -1 or end == -1 or end <= start:
            return []
        try:
            data = json.loads(text[start : end + 1])
            return [str(item).strip() for item in data if str(item).strip()]
        except Exception:
            return []

    # Coordinator creates tasks
    coordinator_prompt = (
        "Break down the goal into a short list of executable tasks. "
        f"Return a JSON array of task strings. Limit to {max_rounds * max(1, len(worker_ids))} tasks.\n\n"
        f"Goal: {goal}"
    )
    coordinator_res = await run_agent(db, coordinator_id, input_data=coordinator_prompt, simulation_mode=False)
    coordinator_text = coordinator_res.get("result", "") if isinstance(coordinator_res, dict) else getattr(coordinator_res, "result", "")
    tasks = _extract_json_list(coordinator_text)
    if not tasks:
        tasks = [goal]

    worker_results: List[Dict[str, Any]] = []
    round_summaries: List[str] = []

    for i, task in enumerate(tasks):
        worker_id = worker_ids[i % len(worker_ids)]
        task_prompt = f"Goal: {goal}\nTask: {task}\nProvide a concrete result or recommendation."
        try:
            MessagingDelegationService.delegate_task(
                db,
                parent_agent_id=coordinator_id,
                child_agent_id=worker_id,
                goal=goal,
                input_payload=task_prompt
            )
        except Exception:
            pass

        res = await run_agent(db, worker_id, input_data=task_prompt, simulation_mode=False)
        text = res.get("result", "") if isinstance(res, dict) else getattr(res, "result", "")
        worker_results.append({"task": task, "agent_id": worker_id, "result": text})
        round_summaries.append(f"Task {i + 1}: {text[:200]}")

        try:
            MessagingDelegationService.send_message(db, sender_agent_id=worker_id, receiver_agent_id=coordinator_id, content=text[:500])
        except Exception:
            pass

    # Reviewer consolidates
    review_payload = json.dumps(worker_results, ensure_ascii=True)
    reviewer_prompt = (
        "You are the reviewer. Validate the worker results, resolve conflicts, and produce a final answer. "
        "Return JSON with keys: `final` (string) and `issues` (array of strings).\n\n"
        f"Goal: {goal}\nWorker results: {review_payload}"
    )
    reviewer_res = await run_agent(db, reviewer_id, input_data=reviewer_prompt, simulation_mode=False)
    reviewer_text = reviewer_res.get("result", "") if isinstance(reviewer_res, dict) else getattr(reviewer_res, "result", "")

    final_answer = reviewer_text
    review_data: Dict[str, Any] = {"final": reviewer_text, "issues": []}
    if "{" in reviewer_text and "}" in reviewer_text:
        try:
            parsed = json.loads(reviewer_text[reviewer_text.find("{") : reviewer_text.rfind("}") + 1])
            if isinstance(parsed, dict):
                review_data = {
                    "final": parsed.get("final", reviewer_text),
                    "issues": parsed.get("issues", [])
                }
                final_answer = review_data.get("final") or reviewer_text
        except Exception:
            pass

    chosen = ConflictResolver.resolve([{"text": final_answer, "agent_id": reviewer_id}])
    summary = f"Reviewer consensus: {chosen.get('text', '')}"
    round_summaries.append(summary)

    if workspace_id is not None:
        try:
            WorkspaceMemoryService.write_memory(
                db,
                workspace_id,
                key=f"swarm_goal_{abs(hash(goal))}",
                value=summary,
                author_agent_id=reviewer_id
            )
        except Exception:
            pass

    return {
        "goal": goal,
        "final": final_answer,
        "round_summaries": round_summaries,
        "rounds": len(round_summaries),
        "tasks": tasks,
        "worker_results": worker_results,
        "review": review_data
    }
