"""
Project Processors for Project Management Application

Handles business logic for Project entity processing including initialization
and completion as specified in functional requirements.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.project.version_1.project import Project
from services.services import get_entity_service


class ProjectInitializationProcessor(CyodaProcessor):
    """
    Processor for Project initialization that sets up project defaults
    and performs initial setup tasks.
    """

    def __init__(self) -> None:
        super().__init__(
            name="ProjectInitializationProcessor",
            description="Initializes Project with default settings and setup tasks",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Initialize the Project with default settings.

        Args:
            entity: The Project entity to initialize
            **kwargs: Additional processing parameters

        Returns:
            The initialized project entity
        """
        try:
            self.logger.info(
                f"Initializing Project {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Project for type-safe operations
            project = cast_entity(entity, Project)

            # Set default start date if not provided
            if not project.start_date:
                project.start_date = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            # Update project status to ACTIVE
            project.status = "ACTIVE"

            # Add owner to team members if not already present
            if not project.team_members:
                project.team_members = []
            if project.owner_id not in project.team_members:
                project.team_members.append(project.owner_id)

            # Update timestamp
            project.update_timestamp()

            self.logger.info(
                f"Project {project.technical_id} initialized successfully with status: {project.status}"
            )

            return project

        except Exception as e:
            self.logger.error(
                f"Error initializing project {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise


class ProjectCompletionProcessor(CyodaProcessor):
    """
    Processor for Project completion that handles project closure tasks
    and updates related entities.
    """

    def __init__(self) -> None:
        super().__init__(
            name="ProjectCompletionProcessor",
            description="Handles Project completion and closure tasks",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Complete the Project and handle closure tasks.

        Args:
            entity: The Project entity to complete
            **kwargs: Additional processing parameters

        Returns:
            The completed project entity
        """
        try:
            self.logger.info(
                f"Completing Project {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Project for type-safe operations
            project = cast_entity(entity, Project)

            # Set completion date if not already set
            if not project.end_date:
                project.end_date = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            # Update project status to COMPLETED
            project.status = "COMPLETED"

            # Update timestamp
            project.update_timestamp()

            # Log completion
            self.logger.info(
                f"Project {project.technical_id} completed successfully on {project.end_date}"
            )

            return project

        except Exception as e:
            self.logger.error(
                f"Error completing project {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise
