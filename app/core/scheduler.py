# app/core/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.job.scheduled_scraper import run_scheduled_scrape
from app.utils.logger import get_logger
from datetime import datetime
logger = get_logger(__name__)
scheduler = AsyncIOScheduler()


def start_scheduler():
    scheduler.add_job(
        run_scheduled_scrape,
        trigger="interval",
        minutes=40,
        id="route_scraper",
        next_run_time=None,  # don't fire instantly on boot; or set to now if you want immediate seed data
        max_instances=1,      # critical: never let two scrape runs overlap
        coalesce=True,        # if a run is missed, don't queue up backlog runs
    )
    scheduler.start()
    logger.info("Scheduler started: route scraper every 45 min")