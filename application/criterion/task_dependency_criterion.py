"""
TaskDependencyCriterion for Project Management Application

Validates that task dependencies are met before allowing certain transitions.
Ensures tasks cannot progress if their dependencies are not completed.
"""

import logging
from typing import Any

from common.data.data_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity
from application.data.task.version_1.task import Task
from services.services import get_entity_service


class TaskDependencyCriterion(CyodaCriteriaChecker):
    """
    Criterion for validating task dependencies are met before transitions.
    """

    def __init__(self) -> None:
        super().__init__(
            name="TaskDependencyCriterion",
            description="Validates task dependencies are completed before allowing transitions",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Evaluate if task dependencies are met.

        Args:
            entity: The Task entity to evaluate
            **kwargs: Additional evaluation parameters

        Returns:
            True if dependencies are met, False otherwise
        """
        try:
            self.logger.info(
                f"Evaluating task dependencies for Task {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Task for type-safe operations
            task = cast_entity(entity, Task)

            # If no dependencies, allow transition
            if not task.dependencies or len(task.dependencies) == 0:
                self.logger.info(f"Task {task.technical_id} has no dependencies")
                return True

            # Check each dependency
            result = await self._check_dependencies(task)

            self.logger.info(
                f"Task dependency evaluation result: {result} for task {task.technical_id}"
            )

            return result

        except Exception as e:
            self.logger.error(
                f"Error evaluating task dependencies {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            return False

    async def _check_dependencies(self, task: Task) -> bool:
        """
        Check if all task dependencies are completed.

        Args:
            task: The task to check dependencies for

        Returns:
            True if all dependencies are completed
        """
        entity_service = get_entity_service()

        try:
            for dependency_id in (task.dependencies or []):
                # Get the dependency task
                dependency_response = await entity_service.get_by_id(
                    entity_id=dependency_id,
                    entity_class="Task",
                    entity_version="1"
                )

                if not dependency_response or not dependency_response.data:
                    self.logger.warning(f"Dependency task {dependency_id} not found")
                    return False

                dependency_data = dependency_response.data
                dependency_state = dependency_data.get("state", "")

                # Dependency must be completed
                if dependency_state != "done":
                    self.logger.info(
                        f"Dependency task {dependency_id} is not completed (state: {dependency_state})"
                    )
                    return False

                # Ensure dependency is in the same project
                dependency_project = dependency_data.get("project_id", "")
                if dependency_project != task.project_id:
                    self.logger.warning(
                        f"Dependency task {dependency_id} is not in the same project"
                    )
                    return False

            self.logger.info(f"All dependencies completed for task {task.technical_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error checking dependencies: {str(e)}")
            return False
