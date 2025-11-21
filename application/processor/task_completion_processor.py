"""
TaskCompletionProcessor for Project Management Application

Handles task completion logic including final validation,
project statistics updates, and completion notifications.
"""

import logging
from typing import Any

from common.data.data_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.data.task.version_1.task import Task
from services.services import get_entity_service


class TaskCompletionProcessor(CyodaProcessor):
    """
    Processor for Task completion that handles final validation
    and updates project statistics.
    """

    def __init__(self) -> None:
        super().__init__(
            name="TaskCompletionProcessor",
            description="Processes task completion and updates project statistics",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the Task completion.

        Args:
            entity: The Task to complete
            **kwargs: Additional processing parameters

        Returns:
            The completed task with final metadata
        """
        try:
            self.logger.info(
                f"Processing task completion for Task {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Task for type-safe operations
            task = cast_entity(entity, Task)

            # Finalize task metrics
            await self._finalize_task_metrics(task)

            # Update project statistics
            await self._update_project_statistics(task)

            # Update completion metadata
            self._update_completion_metadata(task)

            # Log completion
            self.logger.info(
                f"Task {task.technical_id} completed successfully"
            )

            return task

        except Exception as e:
            self.logger.error(
                f"Error processing task completion {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    async def _finalize_task_metrics(self, task: Task) -> None:
        """
        Finalize task metrics including final time tracking.

        Args:
            task: The task to finalize metrics for
        """
        entity_service = get_entity_service()

        try:
            # Get all approved time entries for this task
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
                    # Only count approved or logged time entries
                    entry_state = entry_data.get("state", "")
                    if entry_state in ["logged", "approved"]:
                        duration_minutes = entry_data.get("duration_minutes", 0)
                        total_logged_hours += duration_minutes / 60.0

            # Update final logged hours
            task.logged_hours = total_logged_hours

            self.logger.info(
                f"Task {task.technical_id} final metrics: {total_logged_hours:.2f} hours logged"
            )

        except Exception as e:
            self.logger.warning(
                f"Could not finalize metrics for task {task.technical_id}: {str(e)}"
            )

    async def _update_project_statistics(self, task: Task) -> None:
        """
        Update project statistics when a task is completed.

        Args:
            task: The completed task
        """
        entity_service = get_entity_service()

        try:
            # Get project to update statistics
            project_response = await entity_service.get_by_id(
                entity_id=task.project_id,
                entity_class="Project",
                entity_version="1"
            )

            if not project_response or not project_response.data:
                self.logger.warning(f"Could not find project {task.project_id} for statistics update")
                return

            # Get all tasks in the project to calculate completion rate
            from common.service.entity_service import SearchConditionRequest, SearchCondition, SearchOperator

            project_search_condition = SearchConditionRequest(
                conditions=[SearchCondition(
                    field="project_id",
                    operator=SearchOperator.EQUALS,
                    value=task.project_id
                )]
            )

            project_tasks_response = await entity_service.search(
                entity_class="Task",
                condition=project_search_condition,
                entity_version="1"
            )

            if project_tasks_response:
                total_tasks = len(project_tasks_response)
                completed_tasks = 0
                for task_response in project_tasks_response:
                    task_data = task_response.data.model_dump() if hasattr(task_response.data, 'model_dump') else task_response.data
                    if task_data.get("state") == "done":
                        completed_tasks += 1
                
                completion_rate = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0

                self.logger.info(
                    f"Project {task.project_id} statistics: "
                    f"{completed_tasks}/{total_tasks} tasks completed ({completion_rate:.1f}%)"
                )

        except Exception as e:
            self.logger.warning(
                f"Could not update project statistics for task {task.technical_id}: {str(e)}"
            )

    def _update_completion_metadata(self, task: Task) -> None:
        """
        Update task metadata after completion processing.

        Args:
            task: The task to update
        """
        # Update timestamp
        task.update_timestamp()

        # Calculate final metrics
        completion_info = {
            "completed_at": task.updated_at,
            "final_logged_hours": task.logged_hours
        }

        if task.estimate_hours and task.estimate_hours > 0 and task.logged_hours is not None:
            completion_info["estimate_accuracy"] = (task.logged_hours / task.estimate_hours) * 100

        self.logger.info(
            f"Task completion metadata updated for {task.technical_id}: {completion_info}"
        )
