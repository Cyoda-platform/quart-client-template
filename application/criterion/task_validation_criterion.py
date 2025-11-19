"""
Task Validation Criterion for Project Management Application

Validates Task entities according to business rules and requirements
before allowing workflow transitions.
"""

import logging
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.task.version_1.task import Task


class TaskValidationCriterion(CyodaProcessor):
    """
    Validation criterion for Task entities that checks business rules
    and data integrity before allowing workflow transitions.
    """

    def __init__(self) -> None:
        super().__init__(
            name="TaskValidationCriterion",
            description="Validates Task entities according to business rules",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Validate the Task entity according to business rules.

        Args:
            entity: The Task entity to validate
            **kwargs: Additional validation parameters

        Returns:
            The validated task entity

        Raises:
            ValueError: If validation fails
        """
        try:
            self.logger.info(
                f"Validating Task {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Task for type-safe operations
            task = cast_entity(entity, Task)

            # Validate required fields
            self._validate_required_fields(task)

            # Validate business rules
            self._validate_business_rules(task)

            # Validate data consistency
            self._validate_data_consistency(task)

            self.logger.info(
                f"Task {task.technical_id} validation completed successfully"
            )

            return task

        except Exception as e:
            self.logger.error(
                f"Validation failed for task {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    def _validate_required_fields(self, task: Task) -> None:
        """Validate that all required fields are present and valid."""
        if not task.title or len(task.title.strip()) == 0:
            raise ValueError("Task title is required")

        if not task.project_id or len(task.project_id.strip()) == 0:
            raise ValueError("Project ID is required")

        if not task.reporter_id or len(task.reporter_id.strip()) == 0:
            raise ValueError("Reporter ID is required")

    def _validate_business_rules(self, task: Task) -> None:
        """Validate business rules specific to tasks."""
        # Validate status
        if task.status not in task.ALLOWED_STATUSES:
            raise ValueError(f"Invalid task status: {task.status}")

        # Validate priority
        if task.priority not in task.ALLOWED_PRIORITIES:
            raise ValueError(f"Invalid task priority: {task.priority}")

        # Validate hours
        if task.estimated_hours is not None and task.estimated_hours < 0:
            raise ValueError("Estimated hours cannot be negative")

        if task.actual_hours is not None and task.actual_hours < 0:
            raise ValueError("Actual hours cannot be negative")

    def _validate_data_consistency(self, task: Task) -> None:
        """Validate data consistency and relationships."""
        # Validate due date format if provided
        if task.due_date:
            try:
                from datetime import datetime
                datetime.fromisoformat(task.due_date.replace("Z", "+00:00"))
            except ValueError:
                raise ValueError("Invalid due date format. Use ISO 8601 format")

        # Validate tags
        if task.tags:
            # Check for empty tags
            empty_tags = [tag for tag in task.tags if not tag or len(tag.strip()) == 0]
            if empty_tags:
                raise ValueError("Tags cannot be empty")

            # Check for duplicate tags
            if len(task.tags) != len(set(task.tags)):
                raise ValueError("Duplicate tags are not allowed")

        # Business rule: If task is assigned, assignee should not be the same as reporter
        if task.assignee_id and task.assignee_id == task.reporter_id:
            self.logger.warning(
                f"Task {task.technical_id} assigned to the same user who reported it"
            )
