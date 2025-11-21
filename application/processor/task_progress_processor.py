"""
TaskProgressProcessor for Project Management Application

Handles task progress updates including time tracking calculations
and progress metrics.
"""

import logging
from typing import Any

from common.data.data_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.data.task.version_1.task import Task
from services.services import get_entity_service


class TaskProgressProcessor(CyodaProcessor):
    """
    Processor for Task progress that calculates progress metrics
    and updates time tracking information.
    """

    def __init__(self) -> None:
        super().__init__(
            name="TaskProgressProcessor",
            description="Processes task progress and calculates metrics",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the Task progress update.

        Args:
            entity: The Task to process progress for
            **kwargs: Additional processing parameters

        Returns:
            The task with updated progress metrics
        """
        try:
            self.logger.info(
                f"Processing task progress for Task {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Task for type-safe operations
            task = cast_entity(entity, Task)

            # Calculate and update progress metrics
            await self._calculate_progress_metrics(task)

            # Update task metadata
            self._update_progress_metadata(task)

            # Log progress completion
            self.logger.info(
                f"Task {task.technical_id} progress processed successfully"
            )

            return task

        except Exception as e:
            self.logger.error(
                f"Error processing task progress {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    async def _calculate_progress_metrics(self, task: Task) -> None:
        """
        Calculate progress metrics for the task including time tracking.

        Args:
            task: The task to calculate metrics for
        """
        entity_service = get_entity_service()

        try:
            # Get all time entries for this task
            from common.service.data_service import SearchConditionRequest, SearchCondition, SearchOperator

            search_condition = SearchConditionRequest(
                conditions=[SearchCondition(
                    field="task_id",
                    operator=SearchOperator.EQUALS,
                    value=task.technical_id or task.data_id
                )]
            )

            time_entries_response = await entity_service.search(
                entity_class="TimeEntry",
                condition=search_condition,
                entity_version="1"
            )

            total_logged_hours = 0.0
            if time_entries_response:
                for entry_response in time_entries_response:
                    if hasattr(entry_response.data, 'model_dump'):
                        entry_data = entry_response.data.model_dump()
                    else:
                        entry_data = entry_response.data
                    duration_minutes = entry_data.get("duration_minutes", 0)
                    total_logged_hours += duration_minutes / 60.0

            # Update task logged hours
            task.logged_hours = total_logged_hours

            # Log progress calculation
            self.logger.info(
                f"Task {task.technical_id} progress calculated: "
                f"{total_logged_hours:.2f} hours logged"
            )

        except Exception as e:
            self.logger.warning(
                f"Could not calculate progress metrics for task {task.technical_id}: {str(e)}"
            )
            # Don't fail the entire process if metrics calculation fails

    def _update_progress_metadata(self, task: Task) -> None:
        """
        Update task metadata after progress processing.

        Args:
            task: The task to update
        """
        # Update timestamp
        task.update_timestamp()

        # Calculate progress percentage if estimate is available
        progress_info = {}
        if task.estimate_hours and task.estimate_hours > 0 and task.logged_hours is not None:
            progress_percentage = min(100.0, (task.logged_hours / task.estimate_hours) * 100)
            progress_info["progress_percentage"] = round(progress_percentage, 2)
            progress_info["is_over_estimate"] = task.logged_hours > task.estimate_hours

        self.logger.info(
            f"Task progress metadata updated for {task.technical_id}: {progress_info}"
        )
