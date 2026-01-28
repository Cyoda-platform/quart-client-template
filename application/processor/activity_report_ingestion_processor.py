"""
ActivityReportIngestionProcessor for Activity Tracker application.

Fetches activity data from the Fakerest API with retries and exponential backoff.
Handles rate limits and transient errors gracefully.
"""

import asyncio
import logging
from typing import Any, Dict, List

import aiohttp

from application.entity.activity_report.version_1.activity_report import (
    ActivityReport,
)
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor

logger = logging.getLogger(__name__)

FAKEREST_API_BASE = "https://fakerestapi.azurewebsites.net"
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0


class ActivityReportIngestionProcessor(CyodaProcessor):
    """Fetches activity data from Fakerest API with retry logic."""

    def __init__(self) -> None:
        super().__init__(
            name="ActivityReportIngestionProcessor",
            description="Fetches activity data from Fakerest API",
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Fetch activity data from Fakerest API and populate the report.

        Args:
            entity: The ActivityReport entity to populate
            **kwargs: Additional processing parameters

        Returns:
            The populated ActivityReport entity
        """
        try:
            self.logger.info(
                f"Starting ingestion for ActivityReport {getattr(entity, 'technical_id', '<unknown>')}"
            )

            report = cast_entity(entity, ActivityReport)

            activities = await self._fetch_all_activities()
            self.logger.info(f"Fetched {len(activities)} activities from API")

            report.total_activities = len(activities)
            report.raw_data_location = f"memory://activities/{report.report_date}"

            processing_metadata = {
                "ingestionStartTime": report.created_at,
                "apiCallsAttempted": 1,
                "apiCallsSuccessful": 1,
                "apiCallsFailed": 0,
                "retryCount": 0,
                "totalActivitiesFetched": len(activities),
            }
            report.processing_metadata = processing_metadata

            self.logger.info(
                f"ActivityReport {report.technical_id} ingestion completed"
            )
            return report

        except Exception as e:
            self.logger.error(
                f"Error ingesting data for entity {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    async def _fetch_all_activities(self) -> List[Dict[str, Any]]:
        """
        Fetch all activities from Fakerest API with retry logic.

        Returns:
            List of activity dictionaries
        """
        activities: List[Dict[str, Any]] = []
        retry_count = 0

        while retry_count < MAX_RETRIES:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{FAKEREST_API_BASE}/api/v1/Activities",
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as response:
                        if response.status == 200:
                            activities = await response.json()
                            self.logger.info(
                                f"Successfully fetched {len(activities)} activities"
                            )
                            return activities
                        elif response.status == 429:
                            retry_count += 1
                            backoff = INITIAL_BACKOFF * (2 ** (retry_count - 1))
                            self.logger.warning(
                                f"Rate limited. Retrying in {backoff}s (attempt {retry_count}/{MAX_RETRIES})"
                            )
                            await asyncio.sleep(backoff)
                        else:
                            self.logger.error(f"API returned status {response.status}")
                            retry_count += 1
                            if retry_count < MAX_RETRIES:
                                backoff = INITIAL_BACKOFF * (2 ** (retry_count - 1))
                                await asyncio.sleep(backoff)

            except asyncio.TimeoutError:
                retry_count += 1
                if retry_count < MAX_RETRIES:
                    backoff = INITIAL_BACKOFF * (2 ** (retry_count - 1))
                    self.logger.warning(
                        f"Timeout. Retrying in {backoff}s (attempt {retry_count}/{MAX_RETRIES})"
                    )
                    await asyncio.sleep(backoff)
                else:
                    self.logger.error("Max retries exceeded for API call")
                    raise

            except Exception as e:
                retry_count += 1
                if retry_count < MAX_RETRIES:
                    backoff = INITIAL_BACKOFF * (2 ** (retry_count - 1))
                    self.logger.warning(
                        f"Error fetching activities: {str(e)}. Retrying in {backoff}s"
                    )
                    await asyncio.sleep(backoff)
                else:
                    self.logger.error(
                        f"Failed to fetch activities after retries: {str(e)}"
                    )
                    raise

        return activities
