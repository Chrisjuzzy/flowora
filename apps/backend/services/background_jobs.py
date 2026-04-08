from typing import Callable, Any, Dict, List, Optional
import asyncio
from datetime import datetime
from uuid import uuid4
from utils.logger import logger
import heapq

class Job:
    def __init__(self, func: Callable, args: tuple = (), kwargs: Dict = None, priority: int = 1, max_retries: int = 3):
        self.id = str(uuid4())
        self.func = func
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.status = "pending" # pending, running, completed, failed, retrying
        self.result = None
        self.error = None
        self.created_at = datetime.utcnow()
        self.started_at = None
        self.completed_at = None
        
        # New features
        self.priority = priority # Lower number = Higher priority
        self.max_retries = max_retries
        self.retry_count = 0

    # For priority queue comparison
    def __lt__(self, other):
        return self.priority < other.priority

class JobQueue:
    def __init__(self):
        # Using PriorityQueue for priority handling
        # NOTE: For horizontal scaling, replace this in-memory queue with Redis or RabbitMQ
        # Example: self.queue = RedisQueue("jobs")
        self.queue = asyncio.PriorityQueue()
        self.jobs: Dict[str, Job] = {}

    async def enqueue(self, func: Callable, *args, priority: int = 1, max_retries: int = 3, **kwargs) -> str:
        job = Job(func, args, kwargs, priority=priority, max_retries=max_retries)
        self.jobs[job.id] = job
        await self.queue.put(job)
        logger.info(f"Job {job.id} enqueued (Priority: {priority})")
        return job.id

    def get_job(self, job_id: str) -> Optional[Job]:
        return self.jobs.get(job_id)

    async def worker(self):
        logger.info("Background Worker Started")
        while True:
            job = await self.queue.get()
            try:
                job.status = "running"
                job.started_at = datetime.utcnow()
                logger.info(f"Processing Job {job.id} (Attempt {job.retry_count + 1})")
                
                if asyncio.iscoroutinefunction(job.func):
                    result = await job.func(*job.args, **job.kwargs)
                else:
                    # Run sync functions in thread pool to avoid blocking
                    result = await asyncio.to_thread(job.func, *job.args, **job.kwargs)
                
                job.result = result
                job.status = "completed"
                job.completed_at = datetime.utcnow()
                logger.info(f"Job {job.id} completed")
                
            except Exception as e:
                logger.error(f"Job {job.id} failed: {e}")
                
                if job.retry_count < job.max_retries:
                    job.retry_count += 1
                    job.status = "retrying"
                    logger.info(f"Retrying Job {job.id} ({job.retry_count}/{job.max_retries})")
                    # Re-enqueue with slightly lower priority or same
                    await self.queue.put(job)
                    # Optional: Add delay mechanism here if needed
                else:
                    job.status = "failed"
                    job.error = str(e)
                    job.completed_at = datetime.utcnow()
            finally:
                self.queue.task_done()

# Global Job Queue
job_queue = JobQueue()
