"""Scheduler service for periodic concept tracking."""

import asyncio
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlmodel import Session, select

from cloud_loader.database import engine
from cloud_loader.models import Concept, ConceptStatus, ConceptRunStatus


# Global scheduler instance
scheduler: AsyncIOScheduler = None


async def run_due_concepts():
    """Check and run concepts that are due for execution."""
    from cloud_loader.tracker.agents.orchestrator import orchestrator

    print("[Scheduler] Checking for due concepts...")

    with Session(engine) as session:
        now = datetime.now(timezone.utc)

        # Find active concepts that need to run
        # Either never run, or last run was longer than interval ago
        concepts = session.exec(
            select(Concept).where(
                Concept.status == ConceptStatus.ACTIVE,
                Concept.run_status != ConceptRunStatus.RUNNING,  # Not currently running
            )
        ).all()

        due_concepts = []
        for concept in concepts:
            if concept.last_searched_at is None:
                # Never run before
                due_concepts.append(concept)
            else:
                # Check if interval has passed
                hours_since = (now - concept.last_searched_at).total_seconds() / 3600
                if hours_since >= concept.search_interval_hours:
                    due_concepts.append(concept)

        if not due_concepts:
            print("[Scheduler] No concepts due for execution")
            return

        print(f"[Scheduler] Found {len(due_concepts)} concepts due for execution")

        # Run each concept (in sequence to avoid overwhelming the system)
        for concept in due_concepts:
            try:
                print(f"[Scheduler] Running concept: {concept.name} (id={concept.id})")
                # Need a fresh session for each concept to avoid transaction issues
                with Session(engine) as concept_session:
                    # Re-fetch the concept in this session
                    fresh_concept = concept_session.get(Concept, concept.id)
                    if fresh_concept:
                        await orchestrator.run_concept(fresh_concept, concept_session)
            except Exception as e:
                print(f"[Scheduler] Error running concept {concept.id}: {e}")

            # Small delay between concepts
            await asyncio.sleep(5)


def start_scheduler():
    """Start the APScheduler."""
    global scheduler

    scheduler = AsyncIOScheduler()

    # Run every 15 minutes to check for due concepts
    scheduler.add_job(
        run_due_concepts,
        trigger=IntervalTrigger(minutes=15),
        id="loader_tracker",
        name="Run due topics",
        replace_existing=True,
    )

    scheduler.start()
    print("[Scheduler] Started Loader Tracker scheduler (checking every 15 minutes)")


def stop_scheduler():
    """Stop the APScheduler."""
    global scheduler

    if scheduler:
        scheduler.shutdown(wait=False)
        print("[Scheduler] Stopped Loader Tracker scheduler")
