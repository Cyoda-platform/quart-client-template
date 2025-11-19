"""
Task Processors for Project Management Application

Handles business logic for Task entity processing including assignment
and completion as specified in functional requirements.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.task.version_1.task import Task
from services.services import get_entity_service


class TaskAssignmentProcessor(CyodaProcessor):
    """
    Processor for Task assignment that handles task assignment logic
    and notifications.
    """

    def __init__(self) -> None:
        super().__init__(
            name="TaskAssignmentProcessor",
            description="Handles Task assignment and related notifications",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process task assignment.

        Args:
            entity: The Task entity to process assignment for
            **kwargs: Additional processing parameters

        Returns:
            The processed task entity
        """
        try:
            self.logger.info(
                f"Processing Task assignment {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Task for type-safe operations
            task = cast_entity(entity, Task)

            # Update task status based on assignment
            if task.assignee_id:
                task.status = "TODO"  # Ready to be worked on
                self.logger.info(
                    f"Task {task.technical_id} assigned to user {task.assignee_id}"
                )
            else:
                task.status = "TODO"  # Unassigned but ready
                self.logger.info(
                    f"Task {task.technical_id} created without assignment"
                )

            # Update timestamp
            task.update_timestamp()

            self.logger.info(
                f"Task {task.technical_id} assignment processed successfully"
            )

            return task

        except Exception as e:
            self.logger.error(
                f"Error processing task assignment {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise


class TaskCompletionProcessor(CyodaProcessor):
    """
    Processor for Task completion that handles task closure and
    updates related metrics.
    """

    def __init__(self) -> None:
        super().__init__(
            name="TaskCompletionProcessor",
            description="Handles Task completion and closure tasks",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process task completion.

        Args:
            entity: The Task entity to complete
            **kwargs: Additional processing parameters

        Returns:
            The completed task entity
        """
        try:
            self.logger.info(
                f"Processing Task completion {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Task for type-safe operations
            task = cast_entity(entity, Task)

            # Update task status to DONE
            task.status = "DONE"

            # Set actual hours if not already set and estimated hours exist
            if task.actual_hours is None and task.estimated_hours is not None:
                # For demo purposes, set actual hours to estimated hours
                task.actual_hours = task.estimated_hours
                self.logger.info(
                    f"Set actual hours to {task.actual_hours} for task {task.technical_id}"
                )

            # Update timestamp
            task.update_timestamp()

            self.logger.info(
                f"Task {task.technical_id} completed successfully"
            )

            return task

        except Exception as e:
            self.logger.error(
                f"Error completing task {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise
