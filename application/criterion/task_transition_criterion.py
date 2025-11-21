"""
TaskTransitionCriterion for Project Management Application

Validates task state transitions based on user roles and business rules.
Ensures only authorized users can perform specific transitions.
"""

import logging
from typing import Any

from common.criterion.base import CyodaCriterion
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity
from application.entity.task.version_1.task import Task
from services.services import get_entity_service


class TaskTransitionCriterion(CyodaCriterion):
    """
    Criterion for validating task state transitions based on user roles
    and business rules.
    """

    def __init__(self) -> None:
        super().__init__(
            name="TaskTransitionCriterion",
            description="Validates task state transitions based on user roles and permissions",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def evaluate(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Evaluate if the task transition is allowed.

        Args:
            entity: The Task entity to evaluate
            **kwargs: Additional evaluation parameters including:
                - transition_name: The name of the transition being attempted
                - user_id: The ID of the user attempting the transition

        Returns:
            True if transition is allowed, False otherwise
        """
        try:
            self.logger.info(
                f"Evaluating task transition for Task {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Task for type-safe operations
            task = cast_entity(entity, Task)

            # Get transition context from kwargs
            transition_name = kwargs.get("transition_name", "")
            user_id = kwargs.get("user_id", "")

            if not transition_name or not user_id:
                self.logger.warning("Missing transition_name or user_id in evaluation context")
                return False

            # Evaluate based on transition type
            result = await self._evaluate_transition(task, transition_name, user_id)

            self.logger.info(
                f"Task transition evaluation result: {result} for transition '{transition_name}' by user {user_id}"
            )

            return result

        except Exception as e:
            self.logger.error(
                f"Error evaluating task transition {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            return False

    async def _evaluate_transition(self, task: Task, transition_name: str, user_id: str) -> bool:
        """
        Evaluate specific transition based on business rules.

        Args:
            task: The task being transitioned
            transition_name: The transition being attempted
            user_id: The user attempting the transition

        Returns:
            True if transition is allowed
        """
        entity_service = get_entity_service()

        try:
            # Get user information
            user_response = await entity_service.get(
                entity_id=user_id,
                entity_class="User",
                entity_version="1"
            )

            if not user_response or not user_response.entity:
                self.logger.warning(f"User {user_id} not found")
                return False

            user_data = user_response.entity
            user_role = user_data.get("role", "")
            is_active = user_data.get("isActive", True)

            if not is_active:
                self.logger.warning(f"User {user_id} is not active")
                return False

            # Get project information
            project_response = await entity_service.get(
                entity_id=task.project_id,
                entity_class="Project",
                entity_version="1"
            )

            if not project_response or not project_response.entity:
                self.logger.warning(f"Project {task.project_id} not found")
                return False

            project_data = project_response.entity
            project_owner = project_data.get("owner_id", "")
            project_members = project_data.get("members", [])

            # Check if user has access to the project
            has_project_access = (
                user_id == project_owner or
                user_id in project_members or
                user_role == "ADMIN"
            )

            if not has_project_access:
                self.logger.warning(f"User {user_id} does not have access to project {task.project_id}")
                return False

            # Evaluate specific transitions
            return self._evaluate_specific_transition(
                task, transition_name, user_id, user_role, project_owner
            )

        except Exception as e:
            self.logger.error(f"Error evaluating transition: {str(e)}")
            return False

    def _evaluate_specific_transition(
        self, 
        task: Task, 
        transition_name: str, 
        user_id: str, 
        user_role: str, 
        project_owner: str
    ) -> bool:
        """
        Evaluate specific transition rules.

        Args:
            task: The task being transitioned
            transition_name: The transition being attempted
            user_id: The user attempting the transition
            user_role: The role of the user
            project_owner: The project owner ID

        Returns:
            True if transition is allowed
        """
        # Admin can do anything
        if user_role == "ADMIN":
            return True

        # Transition-specific rules
        if transition_name == "start_work":
            # Only assignee can start work on a task
            if task.assignee_id and user_id == task.assignee_id:
                return True
            # Project owner can also start work if no assignee
            if not task.assignee_id and user_id == project_owner:
                return True
            return False

        elif transition_name == "submit_for_review":
            # Only assignee or project owner can submit for review
            return (
                (task.assignee_id and user_id == task.assignee_id) or
                user_id == project_owner
            )

        elif transition_name == "approve":
            # Only project owner or manager can approve
            return user_role in ["ADMIN", "MANAGER"] and user_id == project_owner

        elif transition_name == "request_changes":
            # Only project owner or manager can request changes
            return user_role in ["ADMIN", "MANAGER"] and user_id == project_owner

        elif transition_name == "reopen":
            # Only project owner or admin can reopen completed tasks
            return user_role in ["ADMIN", "MANAGER"] and user_id == project_owner

        else:
            # For other transitions, allow project members
            return True
