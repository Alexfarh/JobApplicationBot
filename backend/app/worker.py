"""
Worker entrypoint for Playwright automation.
Dequeues next QUEUED task, transitions to RUNNING, and calls Playwright autofill logic.
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.services.queue import dequeue_next_task
from app.services.state_machine import transition_task
from app.models.application_task import TaskState
from app.services.playwright_bot import autofill_job_application

from app.config import settings

async def worker_main(run_id: str):
    engine = create_async_engine(settings.database_url, echo=settings.debug)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as db:
        # Step 1: Dequeue next QUEUED task
        task = await dequeue_next_task(db, run_id)
        if not task:
            print("No QUEUED tasks found.")
            return
        print(f"Dequeued task {task.id} (job_id={task.job_id})")
        # Step 2: Transition to RUNNING
        await transition_task(db, str(task.id), TaskState.QUEUED, TaskState.RUNNING)
        await db.commit()
        print(f"Task {task.id} transitioned to RUNNING.")
        # Step 3: Call Playwright autofill logic
        await autofill_job_application(task, db)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python worker.py <run_id>")
        exit(1)
    run_id = sys.argv[1]
    asyncio.run(worker_main(run_id))
