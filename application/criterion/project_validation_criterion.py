"""
Project Validation Criterion for Project Management Application

Validates Project entities according to business rules and requirements
before allowing workflow transitions.
"""

import logging
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.project.version_1.project import Project


class ProjectValidationCriterion(CyodaProcessor):
    """
    Validation criterion for Project entities that checks business rules
    and data integrity before allowing workflow transitions.
    """

    def __init__(self) -> None:
        super().__init__(
            name="ProjectValidationCriterion",
            description="Validates Project entities according to business rules",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Validate the Project entity according to business rules.

        Args:
            entity: The Project entity to validate
            **kwargs: Additional validation parameters

        Returns:
            The validated project entity

        Raises:
            ValueError: If validation fails
        """
        try:
            self.logger.info(
                f"Validating Project {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Project for type-safe operations
            project = cast_entity(entity, Project)

            # Validate required fields
            self._validate_required_fields(project)

            # Validate business rules
            self._validate_business_rules(project)

            # Validate data consistency
            self._validate_data_consistency(project)

            self.logger.info(
                f"Project {project.technical_id} validation completed successfully"
            )

            return project

        except Exception as e:
            self.logger.error(
                f"Validation failed for project {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    def _validate_required_fields(self, project: Project) -> None:
        """Validate that all required fields are present and valid."""
        if not project.name or len(project.name.strip()) == 0:
            raise ValueError("Project name is required")

        if not project.description or len(project.description.strip()) == 0:
            raise ValueError("Project description is required")

        if not project.owner_id or len(project.owner_id.strip()) == 0:
            raise ValueError("Project owner ID is required")

    def _validate_business_rules(self, project: Project) -> None:
        """Validate business rules specific to projects."""
        # Validate status
        if project.status not in project.ALLOWED_STATUSES:
            raise ValueError(f"Invalid project status: {project.status}")

        # Validate priority
        if project.priority not in project.ALLOWED_PRIORITIES:
            raise ValueError(f"Invalid project priority: {project.priority}")

        # Validate budget
        if project.budget is not None and project.budget < 0:
            raise ValueError("Project budget cannot be negative")

    def _validate_data_consistency(self, project: Project) -> None:
        """Validate data consistency and relationships."""
        # Validate date consistency
        if project.start_date and project.end_date:
            try:
                from datetime import datetime
                start = datetime.fromisoformat(project.start_date.replace("Z", "+00:00"))
                end = datetime.fromisoformat(project.end_date.replace("Z", "+00:00"))
                if end <= start:
                    raise ValueError("Project end date must be after start date")
            except ValueError as e:
                if "end date must be after start date" in str(e).lower():
                    raise
                raise ValueError("Invalid date format in project dates")

        # Validate team members list
        if project.team_members:
            # Check for duplicates
            if len(project.team_members) != len(set(project.team_members)):
                raise ValueError("Duplicate team members are not allowed")

            # Validate that owner is in team members
            if project.owner_id not in project.team_members:
                # This is a warning, not an error - will be fixed in processor
                self.logger.warning(
                    f"Project owner {project.owner_id} not in team members list"
                )
