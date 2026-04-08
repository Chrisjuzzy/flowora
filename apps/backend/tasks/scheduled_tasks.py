from datetime import datetime, timedelta
import logging

from celery_app import celery_app
from sqlalchemy import func, or_

from database_production import get_db_context
from models import Execution, Agent, ExecutionLog
from services.agent_optimizer import AgentOptimizer
from services.prompt_version_service import PromptVersionService
from services.encryption import encryption_service
from config_production import settings
import asyncio
from services.trending_service import TrendingService
from services.innovation_service import DiscoveryService
from services.agent_generator import AgentGenerator
from services.autonomous_workflows import WorkflowAutogenService
from services.marketplace_autopublish import MarketplaceAutopublishService
from services.product_generator import AIProductGenerator
from models import FounderRun, AgentTemplate, WorkflowTemplate, ToolConfigTemplate

logger = logging.getLogger(__name__)

def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return asyncio.run(coro)
    except RuntimeError:
        pass
    return asyncio.run(coro)


@celery_app.task(name="tasks.scheduled_tasks.cleanup_old_executions")
def cleanup_old_executions(days: int = 30):
    cutoff = datetime.utcnow() - timedelta(days=days)
    with get_db_context() as db:
        deleted = db.query(Execution).filter(Execution.timestamp < cutoff).delete()
        db.commit()
        logger.info("Cleaned up %s old executions", deleted)
    return {"deleted": deleted}


@celery_app.task(name="tasks.scheduled_tasks.update_agent_metrics")
def update_agent_metrics():
    with get_db_context() as db:
        agents = db.query(Agent).all()
        for agent in agents:
            agent.execution_count = db.query(Execution).filter(Execution.agent_id == agent.id).count()
        db.commit()
    return {"status": "ok", "agents": len(agents)}


@celery_app.task(name="tasks.scheduled_tasks.send_daily_usage_report")
def send_daily_usage_report():
    logger.info("Daily usage report task executed")
    return {"status": "sent"}


@celery_app.task(name="tasks.scheduled_tasks.monitor_worker_memory")
def monitor_worker_memory():
    try:
        import psutil
        process = psutil.Process()
        mem_mb = process.memory_info().rss / (1024 * 1024)
        logger.info("Worker memory usage: %.2f MB", mem_mb)
        return {"memory_mb": round(mem_mb, 2)}
    except Exception as exc:
        logger.warning("Worker memory monitor unavailable: %s", exc)
        return {"memory_mb": None}


@celery_app.task(name="tasks.scheduled_tasks.optimize_agents")
def optimize_agents(min_runs: int = 5):
    optimizer = AgentOptimizer()
    updated = 0
    with get_db_context() as db:
        agents = db.query(Agent).all()
        for agent in agents:
            try:
                optimized, metrics = _run_async(
                    optimizer.optimize_agent_prompt(db, agent.id, min_runs=min_runs)
                )
                if metrics and metrics.get("total_runs", 0) >= min_runs:
                    updated += 1
            except Exception:
                continue
    return {"optimized": updated}


def _collect_recent_metrics(db, agent_id: int, window_hours: int):
    cutoff = datetime.utcnow() - timedelta(hours=window_hours)
    query = db.query(Execution).filter(
        Execution.agent_id == agent_id,
        Execution.timestamp >= cutoff
    )
    total = query.count()
    successes = query.filter(Execution.status == "completed").count()
    avg_latency = query.with_entities(func.avg(Execution.execution_time_ms)).scalar() or 0
    success_rate = (successes / total) if total else 0.0
    return {
        "total_runs": total,
        "success_rate": round(success_rate, 3),
        "avg_latency_ms": float(avg_latency or 0)
    }


def _summarize_failures(db, agent_id: int, window_hours: int, limit: int = 5) -> str:
    cutoff = datetime.utcnow() - timedelta(hours=window_hours)
    failures = (
        db.query(ExecutionLog.message)
        .filter(
            ExecutionLog.agent_id == agent_id,
            ExecutionLog.created_at >= cutoff,
            or_(
                ExecutionLog.message.ilike("%failed%"),
                ExecutionLog.message.ilike("%error%"),
                ExecutionLog.message.ilike("%blocked%")
            )
        )
        .order_by(ExecutionLog.created_at.desc())
        .limit(50)
        .all()
    )
    if not failures:
        return ""
    counts = {}
    for row in failures:
        msg = row[0]
        counts[msg] = counts.get(msg, 0) + 1
    top = sorted(counts.items(), key=lambda item: item[1], reverse=True)[:limit]
    return "; ".join([f"{msg} ({count})" for msg, count in top])


@celery_app.task(name="tasks.scheduled_tasks.continuous_agent_learning")
def continuous_agent_learning():
    window_hours = settings.LEARNING_EVAL_WINDOW_HOURS
    min_runs = settings.LEARNING_MIN_RUNS
    threshold = settings.LEARNING_SUCCESS_THRESHOLD
    optimized = 0
    evaluated = 0

    optimizer = AgentOptimizer()
    with get_db_context() as db:
        agents = db.query(Agent).all()
        for agent in agents:
            try:
                config = {}
                if agent.config:
                    try:
                        config = encryption_service.decrypt_data(agent.config)
                    except Exception:
                        config = {}

                current_prompt = ""
                if isinstance(config, dict):
                    current_prompt = config.get("system_prompt", "")

                if current_prompt:
                    PromptVersionService.ensure_prompt_version(
                        db,
                        agent,
                        current_prompt,
                        source="seed",
                        activate_if_missing=True
                    )

                metrics = _collect_recent_metrics(db, agent.id, window_hours)
                failure_summary = _summarize_failures(db, agent.id, window_hours)

                if metrics["total_runs"] >= min_runs and metrics["success_rate"] < threshold:
                    _run_async(
                        optimizer.optimize_agent_prompt(
                            db,
                            agent.id,
                            min_runs=min_runs,
                            failure_summary=failure_summary
                        )
                    )
                    optimized += 1

                versions = PromptVersionService.evaluate_prompt_versions(db, agent.id, window_hours)
                rollback_target = PromptVersionService.rollback_if_degraded(
                    db, agent, versions, min_runs, threshold
                )
                if rollback_target:
                    evaluated += 1
                    continue

                best = PromptVersionService.select_best_version(versions, min_runs)
                if best:
                    PromptVersionService.activate_prompt_version(db, agent, best)
                    evaluated += 1
            except Exception as exc:
                logger.warning("Continuous learning failed for agent %s: %s", agent.id, exc)
                db.rollback()
                continue

    return {"optimized": optimized, "evaluated": evaluated}


@celery_app.task(name="tasks.scheduled_tasks.weekly_founder_mode")
def weekly_founder_mode():
    """
    Weekly founder mode automation:
    1. Analyze marketplace trends
    2. Generate automation ideas
    3. Generate agents
    4. Publish templates
    5. Publish marketplace listings
    """
    publisher = MarketplaceAutopublishService()
    agent_generator = AgentGenerator()
    workflow_service = WorkflowAutogenService()
    product_generator = AIProductGenerator()

    run_record = FounderRun(status="running", run_type="weekly")
    with get_db_context() as db:
        db.add(run_record)
        db.commit()
        db.refresh(run_record)

        try:
            trends = {
                "top_agents": TrendingService.top_agents(db, limit=5),
                "top_workflows": TrendingService.top_workflows(db, limit=5),
                "top_plugins": TrendingService.top_plugins(db, limit=5),
                "demand": product_generator.analyze_marketplace_demand(db)
            }

            opportunities = _run_async(DiscoveryService.scan_opportunities(db)) or []
            ideas = [
                {
                    "id": opp.id,
                    "title": opp.title,
                    "description": opp.description,
                    "type": opp.type,
                    "confidence": opp.confidence_score
                }
                for opp in opportunities
            ]

            agents_created = []
            workflows_created = []
            templates_created = {"agents": [], "workflows": [], "tools": []}
            listings_created = []

            for idea in ideas[:3]:
                goal = f"{idea.get('title')} - {idea.get('description')}"
                agent, payload = _run_async(
                    agent_generator.generate_agent(
                        db=db,
                        goal=goal,
                        owner_id=None,
                        workspace_id=None,
                        category=idea.get("type") or "automation"
                    )
                )
                agents_created.append({"id": agent.id, "name": agent.name, "goal": goal})

                workflow = _run_async(
                    workflow_service.generate_workflow(
                        db,
                        goal,
                        owner_id=None
                    )
                )
                workflows_created.append({"id": workflow.id, "name": workflow.name, "goal": goal})

                listing = publisher.publish_agent(
                    db,
                    agent_id=agent.id,
                    seller_id=None,
                    price=19.0,
                    category=idea.get("type") or "automation",
                    auto=True,
                    capabilities=payload.get("capabilities"),
                    pricing_tier="weekly"
                )
                listings_created.append({"id": listing.id, "agent_id": agent.id})

                agent_config = {}
                if agent.config:
                    try:
                        agent_config = encryption_service.decrypt_data(agent.config)
                    except Exception:
                        agent_config = {}

                agent_template = AgentTemplate(
                    name=f"{agent.name} Template",
                    description=agent.description,
                    category=agent.category,
                    tags=agent.tags,
                    base_config=agent_config if isinstance(agent_config, dict) else {},
                    tools=agent_config.get("tools") if isinstance(agent_config, dict) else None,
                    created_by=None
                )
                db.add(agent_template)
                db.commit()
                db.refresh(agent_template)
                templates_created["agents"].append(agent_template.id)

                workflow_template = WorkflowTemplate(
                    name=f"{workflow.name} Template",
                    description=workflow.description,
                    category=idea.get("type") or "automation",
                    config_json=workflow.config_json,
                    created_by=None
                )
                db.add(workflow_template)
                db.commit()
                db.refresh(workflow_template)
                templates_created["workflows"].append(workflow_template.id)

                if isinstance(agent_config, dict) and agent_config.get("tools"):
                    tool_template = ToolConfigTemplate(
                        name=f"{agent.name} Tool Stack",
                        description="Auto-generated tool configuration",
                        category=idea.get("type") or "automation",
                        tool_config={"tools": agent_config.get("tools")},
                        created_by=None
                    )
                    db.add(tool_template)
                    db.commit()
                    db.refresh(tool_template)
                    templates_created["tools"].append(tool_template.id)

            run_record.status = "completed"
            run_record.trend_snapshot = trends
            run_record.automation_ideas = ideas
            run_record.agents_created = agents_created
            run_record.workflows_created = workflows_created
            run_record.templates_published = templates_created
            run_record.listings_published = listings_created
            run_record.summary = {
                "ideas_used": len(ideas[:3]),
                "agents_created": len(agents_created),
                "workflows_created": len(workflows_created),
                "templates_created": templates_created,
                "listings_created": len(listings_created)
            }
            db.commit()
        except Exception as exc:
            logger.error("Weekly founder mode failed: %s", exc, exc_info=True)
            run_record.status = "failed"
            run_record.error = str(exc)
            db.commit()
            return {"status": "failed", "error": str(exc)}

    return {"status": "completed"}
