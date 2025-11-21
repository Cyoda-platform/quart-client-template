"""
ProjectActivationProcessor for Project Management Application

Handles project activation logic including validation of project owner
and initial setup of project metadata.
"""

import logging
from typing import Any

from application.data.project.version_1.project import Project
from common.data.data_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from services.services import get_entity_service


class ProjectActivationProcessor(CyodaProcessor):
    """
    Processor for Project activation that validates project setup
    and initializes project metadata.
    """

    def __init__(self) -> None:
        super().__init__(
            name="ProjectActivationProcessor",
            description="Activates projects and validates project setup",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the Project activation.

        Args:
            entity: The Project to activate
            **kwargs: Additional processing parameters

        Returns:
            The activated project with updated metadata
        """
        try:
            self.logger.info(
                f"Activating Project {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Project for type-safe operations
            project = cast_entity(entity, Project)

            # Validate project owner exists and has proper role
            await self._validate_project_owner(project)

            # Initialize project metadata
            self._initialize_project_metadata(project)

            # Log activation completion
            self.logger.info(f"Project {project.technical_id} activated successfully")

            return project

        except Exception as e:
            self.logger.error(
                f"Error activating project {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    async def _validate_project_owner(self, project: Project) -> None:
        """
        Validate that the project owner exists and has proper role.

        Args:
            project: The project to validate
        """
        entity_service = get_entity_service()

        try:
            # Get the project owner
            owner_response = await entity_service.get_by_id(
                entity_id=project.owner_id, entity_class="User", entity_version="1"
            )

            if not owner_response or not owner_response.data:
                raise ValueError(f"Project owner {project.owner_id} not found")

            owner_data = owner_response.data
            owner_role = owner_data.get("role", "")

            # Validate owner has proper role
            if owner_role not in ["ADMIN", "MANAGER"]:
                raise ValueError(
                    f"Project owner must have ADMIN or MANAGER role, got: {owner_role}"
                )

            self.logger.info(
                f"Project owner {project.owner_id} validated with role {owner_role}"
            )

        except Exception as e:
            self.logger.error(
                f"Failed to validate project owner {project.owner_id}: {str(e)}"
            )
            raise

    def _initialize_project_metadata(self, project: Project) -> None:
        """
        Initialize project metadata upon activation.

        Args:
            project: The project to initialize
        """
        # Update timestamp
        project.update_timestamp()

        # Ensure owner is in members list
        if project.members is None:
            project.members = []
        if project.owner_id not in project.members:
            project.members.append(project.owner_id)

        self.logger.info(f"Project metadata initialized for {project.technical_id}")
