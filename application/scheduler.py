"""
Scheduled job runner for Activity Tracker application.

Runs daily ingestion and processing pipeline at configured time (default 02:00 UTC).
"""

import asyncio
import logging
import os
from datetime import datetime, timezone

from application.entity.activity_report.version_1.activity_report import (
    ActivityReport,
)
from services.services import get_entity_service

logger = logging.getLogger(__name__)


class ActivityTrackerScheduler:
    """Manages scheduled jobs for activity tracking."""

    def __init__(self) -> None:
        self.service = get_entity_service()
        self.schedule_time = os.getenv("SCHEDULE_TIME", "02:00")

    async def run_daily_pipeline(self) -> None:
        """
        Run the daily ingestion and processing pipeline.

        Creates a new ActivityReport and triggers the workflow transitions.
        """
        try:
            logger.info("Starting daily activity tracking pipeline")

            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            report = ActivityReport(
                report_date=today,
                total_activities=0,
                top_activity_types=[],
                trend_highlights=[],
                flagged_anomalies=[],
            )

            response = await self.service.save(
                entity=report.model_dump(by_alias=True),
                entity_class=ActivityReport.ENTITY_NAME,
                entity_version=str(ActivityReport.ENTITY_VERSION),
            )

            entity_id = response.metadata.id
            logger.info(f"Created ActivityReport {entity_id}")

            await self._trigger_workflow(entity_id)

            logger.info("Daily activity tracking pipeline completed successfully")

        except Exception as e:
            logger.error(f"Error running daily pipeline: {str(e)}")
            raise

    async def _trigger_workflow(self, entity_id: str) -> None:
        """
        Trigger the workflow transitions for the report.

        Args:
            entity_id: The ID of the ActivityReport to process
        """
        transitions = ["ingest", "process", "report", "complete"]

        for transition in transitions:
            try:
                logger.info(f"Triggering transition: {transition}")
                await self.service.execute_transition(
                    entity_id=entity_id,
                    transition=transition,
                    entity_class=ActivityReport.ENTITY_NAME,
                    entity_version=str(ActivityReport.ENTITY_VERSION),
                )
                logger.info(f"Transition {transition} completed")

            except Exception as e:
                logger.error(f"Error triggering transition {transition}: {str(e)}")
                raise


async def start_scheduler() -> None:
    """Start the activity tracker scheduler."""
    scheduler = ActivityTrackerScheduler()

    logger.info(
        f"Activity Tracker Scheduler started. "
        f"Daily pipeline will run at {scheduler.schedule_time} UTC"
    )

    while True:
        now = datetime.now(timezone.utc)
        schedule_hour, schedule_minute = map(int, scheduler.schedule_time.split(":"))

        if now.hour == schedule_hour and now.minute == schedule_minute:
            await scheduler.run_daily_pipeline()
            await asyncio.sleep(60)

        await asyncio.sleep(30)
