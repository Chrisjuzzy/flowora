import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Schedule
from services.agent_runner import run_agent
from services.backup_service import backup_service
import os

import logging

logger = logging.getLogger(__name__)

async def scheduler_loop():
    logger.info("Scheduler service started...")
    while True:
        try:
            await check_schedules()
            await check_backups()
        except Exception as e:
            logger.error(f"Scheduler Error: {e}")
        
        # Check every minute
        await asyncio.sleep(60)

async def check_backups():
    """Automated daily backup"""
    today_str = datetime.now().strftime("%Y%m%d")
    # Check if a backup file with today's date exists
    backups = backup_service.list_snapshots()
    backup_today = any(f"backup_{today_str}" in b for b in backups)
    
    if not backup_today:
        logger.info(f"Creating automated backup for {today_str}...")
        try:
            backup_file = backup_service.create_snapshot()
            logger.info(f"Automated backup created: {backup_file}")
        except Exception as e:
            logger.error(f"Automated backup failed: {e}")

async def check_schedules():
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        # Find schedules that are active and due
        schedules = db.query(Schedule).filter(Schedule.is_active == True).all()
        
        for schedule in schedules:
            if not schedule.next_run or schedule.next_run <= now:
                logger.info(f"Running scheduled agent {schedule.agent_id} for user {schedule.user_id}")
                
                try:
                    # Input for scheduled run
                    input_text = f"Scheduled run at {now}"
                    
                    # Execute Agent (async)
                    await run_agent(db, schedule.agent_id, input_text)
                    
                    # Update Schedule
                    schedule.last_run = now
                    schedule.next_run = calculate_next_run(schedule.cron_expression, now)
                    db.commit()
                    
                except Exception as e:
                    logger.error(f"Failed to run scheduled agent {schedule.agent_id}: {e}")
                    
    finally:
        db.close()

def calculate_next_run(expression: str, last_run: datetime) -> datetime:
    if expression == "daily":
        return last_run + timedelta(days=1)
    elif expression == "weekly":
        return last_run + timedelta(weeks=1)
    elif expression == "hourly": # For testing
        return last_run + timedelta(hours=1)
    else:
        # Default to daily
        return last_run + timedelta(days=1)
