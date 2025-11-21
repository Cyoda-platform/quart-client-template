"""
TimeEntryProcessor for Project Management Application

Handles time entry processing including validation,
task time updates, and duration calculations.
"""

import logging
from typing import Any

from application.data.time_entry.version_1.time_entry import TimeEntry
from common.data.data_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from services.services import get_entity_service


class TimeEntryProcessor(CyodaProcessor):
    """
    Processor for TimeEntry that validates time entries
    and updates task time tracking.
    """

    def __init__(self) -> None:
        super().__init__(
            name="TimeEntryProcessor",
            description="Processes time entries and updates task time tracking",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the TimeEntry.

        Args:
            entity: The TimeEntry to process
            **kwargs: Additional processing parameters

        Returns:
            The processed time entry
        """
        try:
            self.logger.info(
                f"Processing time entry for TimeEntry {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to TimeEntry for type-safe operations
            time_entry = cast_entity(entity, TimeEntry)

            # Validate time entry permissions
            await self._validate_time_entry_permissions(time_entry)

            # Validate duration consistency
            self._validate_duration_consistency(time_entry)

            # Update task logged hours
            await self._update_task_logged_hours(time_entry)

            # Update time entry metadata
            self._update_time_entry_metadata(time_entry)

            # Log processing completion
            self.logger.info(
                f"TimeEntry {time_entry.technical_id} processed successfully"
            )

            return time_entry

        except Exception as e:
            self.logger.error(
                f"Error processing time entry {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    async def _validate_time_entry_permissions(self, time_entry: TimeEntry) -> None:
        """
        Validate that the user has permissions to log time for the task.

        Args:
            time_entry: The time entry to validate
        """
        entity_service = get_entity_service()

        try:
            # Get the user
            user_response = await entity_service.get_by_id(
                entity_id=time_entry.user_id, entity_class="User", entity_version="1"
            )

            if not user_response or not user_response.data:
                raise ValueError(f"User {time_entry.user_id} not found")

            user_data = user_response.data
            is_active = user_data.get("isActive", True)

            if not is_active:
                raise ValueError(
                    f"Cannot log time for inactive user {time_entry.user_id}"
                )

            # Get the task
            task_response = await entity_service.get_by_id(
                entity_id=time_entry.task_id, entity_class="Task", entity_version="1"
            )

            if not task_response or not task_response.data:
                raise ValueError(f"Task {time_entry.task_id} not found")

            task_data = task_response.data
            task_assignee = task_data.get("assignee_id")
            project_id = task_data.get("project_id")

            # Get project to validate membership
            if project_id:
                project_response = await entity_service.get_by_id(
                    entity_id=project_id, entity_class="Project", entity_version="1"
                )

                if project_response and project_response.data:
                    project_data = project_response.data
                    project_members = project_data.get("members", [])
                    project_owner = project_data.get("owner_id", "")

                    # User can log time if they are:
                    # 1. Task assignee
                    # 2. Project owner
                    # 3. Project member (with some restrictions)
                    can_log_time = (
                        time_entry.user_id == task_assignee
                        or time_entry.user_id == project_owner
                        or time_entry.user_id in project_members
                    )

                    if not can_log_time:
                        raise ValueError(
                            f"User {time_entry.user_id} does not have permission to log time for task {time_entry.task_id}"
                        )

            self.logger.info(
                f"Time entry permissions validated for user {time_entry.user_id}"
            )

        except Exception as e:
            self.logger.error(f"Failed to validate time entry permissions: {str(e)}")
            raise

    def _validate_duration_consistency(self, time_entry: TimeEntry) -> None:
        """
        Validate duration consistency with start/end times if provided.

        Args:
            time_entry: The time entry to validate
        """
        if time_entry.start_time and time_entry.end_time:
            calculated_duration = time_entry.calculate_duration_from_times()

            if calculated_duration is not None:
                # Allow 1 minute tolerance for rounding
                if abs(calculated_duration - time_entry.duration_minutes) > 1:
                    raise ValueError(
                        f"Duration {time_entry.duration_minutes} minutes does not match "
                        f"calculated duration {calculated_duration} minutes from start/end times"
                    )

        # Validate reasonable duration
        if time_entry.duration_minutes > time_entry.MAX_DURATION_MINUTES:
            raise ValueError(
                f"Duration {time_entry.duration_minutes} minutes exceeds maximum allowed "
                f"{time_entry.MAX_DURATION_MINUTES} minutes"
            )

        self.logger.info(
            f"Duration consistency validated: {time_entry.duration_minutes} minutes"
        )

    async def _update_task_logged_hours(self, time_entry: TimeEntry) -> None:
        """
        Update the task's logged hours with this time entry.

        Args:
            time_entry: The time entry to add to task
        """
        entity_service = get_entity_service()

        try:
            # Get the current task
            task_response = await entity_service.get_by_id(
                entity_id=time_entry.task_id, entity_class="Task", entity_version="1"
            )

            if task_response and task_response.data:
                task_data = task_response.data.copy()
                current_logged_hours = task_data.get("logged_hours", 0.0) or 0.0

                # Add this time entry's hours
                additional_hours = time_entry.get_duration_hours()
                new_logged_hours = current_logged_hours + additional_hours

                # Update task with new logged hours
                task_data["logged_hours"] = new_logged_hours

                # Save the updated task (this will trigger task workflow if needed)
                await entity_service.save(
                    entity=task_data, entity_class="Task", entity_version="1"
                )

                self.logger.info(
                    f"Updated task {time_entry.task_id} logged hours: "
                    f"{current_logged_hours:.2f} + {additional_hours:.2f} = {new_logged_hours:.2f}"
                )

        except Exception as e:
            self.logger.error(f"Failed to update task logged hours: {str(e)}")
            # Don't fail the entire process if task update fails

    def _update_time_entry_metadata(self, time_entry: TimeEntry) -> None:
        """
        Update time entry metadata after processing.

        Args:
            time_entry: The time entry to update
        """
        # Update timestamp if not already set
        if not time_entry.updated_at:
            time_entry.update_timestamp()

        entry_info = {
            "duration_hours": time_entry.get_duration_hours(),
            "is_long_session": time_entry.is_long_session(),
            "processed_at": time_entry.updated_at or time_entry.created_at,
        }

        self.logger.info(
            f"Time entry metadata updated for {time_entry.technical_id}: {entry_info}"
        )
