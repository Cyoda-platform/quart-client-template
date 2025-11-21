"""
TaskAssignmentProcessor for Project Management Application

Handles task assignment logic including validation of assignee permissions
and notification of assignment.
"""

import logging
from typing import Any

from application.data.task.version_1.task import Task
from common.data.data_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from services.services import get_entity_service


class TaskAssignmentProcessor(CyodaProcessor):
    """
    Processor for Task assignment that validates assignee permissions
    and handles assignment notifications.
    """

    def __init__(self) -> None:
        super().__init__(
            name="TaskAssignmentProcessor",
            description="Handles task assignment and validation",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the Task assignment.

        Args:
            entity: The Task to process assignment for
            **kwargs: Additional processing parameters

        Returns:
            The task with validated assignment
        """
        try:
            self.logger.info(
                f"Processing task assignment for Task {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Task for type-safe operations
            task = cast_entity(entity, Task)

            # Validate assignee if assigned
            if task.assignee_id:
                await self._validate_assignee(task)

            # Update task metadata
            self._update_task_metadata(task)

            # Log assignment completion
            self.logger.info(
                f"Task {task.technical_id} assignment processed successfully"
            )

            return task

        except Exception as e:
            self.logger.error(
                f"Error processing task assignment {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    async def _validate_assignee(self, task: Task) -> None:
        """
        Validate that the assignee exists and has access to the project.

        Args:
            task: The task to validate assignee for
        """
        entity_service = get_entity_service()

        try:
            # Get the assignee
            if not task.assignee_id:
                raise ValueError("Task assignee ID is required")

            assignee_response = await entity_service.get_by_id(
                entity_id=task.assignee_id, entity_class="User", entity_version="1"
            )

            if not assignee_response or not assignee_response.data:
                raise ValueError(f"Task assignee {task.assignee_id} not found")

            assignee_data = assignee_response.data
            is_active = assignee_data.get("isActive", True)

            if not is_active:
                raise ValueError(
                    f"Cannot assign task to inactive user {task.assignee_id}"
                )

            # Get the project to validate membership
            project_response = await entity_service.get_by_id(
                entity_id=task.project_id, entity_class="Project", entity_version="1"
            )

            if not project_response or not project_response.data:
                raise ValueError(f"Project {task.project_id} not found")

            project_data = project_response.data
            project_members = project_data.get("members", [])
            project_owner = project_data.get("owner_id", "")

            # Check if assignee is project member or owner
            if (
                task.assignee_id not in project_members
                and task.assignee_id != project_owner
            ):
                raise ValueError(
                    f"User {task.assignee_id} is not a member of project {task.project_id}"
                )

            self.logger.info(f"Task assignee {task.assignee_id} validated")

        except Exception as e:
            self.logger.error(
                f"Failed to validate task assignee {task.assignee_id}: {str(e)}"
            )
            raise

    def _update_task_metadata(self, task: Task) -> None:
        """
        Update task metadata after assignment processing.

        Args:
            task: The task to update
        """
        # Update timestamp
        task.update_timestamp()

        # Initialize logged hours if not set
        if task.logged_hours is None:
            task.logged_hours = 0.0

        self.logger.info(f"Task metadata updated for {task.technical_id}")
