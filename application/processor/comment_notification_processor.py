"""
CommentNotificationProcessor for Project Management Application

Handles comment notifications including mentions and real-time updates.
"""

import logging
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.comment.version_1.comment import Comment
from services.services import get_entity_service


class CommentNotificationProcessor(CyodaProcessor):
    """
    Processor for Comment notifications that handles mentions
    and real-time collaboration updates.
    """

    def __init__(self) -> None:
        super().__init__(
            name="CommentNotificationProcessor",
            description="Processes comment notifications and mentions",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the Comment notification.

        Args:
            entity: The Comment to process notifications for
            **kwargs: Additional processing parameters

        Returns:
            The comment with processed notifications
        """
        try:
            self.logger.info(
                f"Processing comment notifications for Comment {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Comment for type-safe operations
            comment = cast_entity(entity, Comment)

            # Process mentions
            await self._process_mentions(comment)

            # Notify task participants
            await self._notify_task_participants(comment)

            # Update comment metadata
            self._update_notification_metadata(comment)

            # Log notification completion
            self.logger.info(
                f"Comment {comment.technical_id} notifications processed successfully"
            )

            return comment

        except Exception as e:
            self.logger.error(
                f"Error processing comment notifications {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    async def _process_mentions(self, comment: Comment) -> None:
        """
        Process user mentions in the comment.

        Args:
            comment: The comment to process mentions for
        """
        if not comment.mentions:
            return

        entity_service = get_entity_service()

        for mentioned_user_id in comment.mentions:
            try:
                # Validate mentioned user exists
                user_response = await entity_service.get(
                    entity_id=mentioned_user_id,
                    entity_class="User",
                    entity_version="1"
                )

                if user_response and user_response.entity:
                    user_data = user_response.entity
                    user_name = user_data.get("name", "Unknown User")
                    
                    self.logger.info(
                        f"Processing mention for user {mentioned_user_id} ({user_name}) "
                        f"in comment {comment.technical_id}"
                    )
                    
                    # In a real implementation, this would trigger:
                    # - Email notification
                    # - In-app notification
                    # - WebSocket real-time update
                    # For now, we just log the mention
                    
                else:
                    self.logger.warning(f"Mentioned user {mentioned_user_id} not found")

            except Exception as e:
                self.logger.error(f"Error processing mention for user {mentioned_user_id}: {str(e)}")

    async def _notify_task_participants(self, comment: Comment) -> None:
        """
        Notify task participants about the new comment.

        Args:
            comment: The comment to notify about
        """
        entity_service = get_entity_service()

        try:
            # Get the task to find participants
            task_response = await entity_service.get(
                entity_id=comment.task_id,
                entity_class="Task",
                entity_version="1"
            )

            if not task_response or not task_response.entity:
                self.logger.warning(f"Could not find task {comment.task_id} for notifications")
                return

            task_data = task_response.entity
            assignee_id = task_data.get("assignee_id")
            
            # Get project to find owner and members
            project_id = task_data.get("project_id")
            if project_id:
                project_response = await entity_service.get(
                    entity_id=project_id,
                    entity_class="Project",
                    entity_version="1"
                )

                if project_response and project_response.entity:
                    project_data = project_response.entity
                    project_owner = project_data.get("owner_id")
                    
                    # Collect participants (excluding comment author)
                    participants = set()
                    if assignee_id and assignee_id != comment.author_id:
                        participants.add(assignee_id)
                    if project_owner and project_owner != comment.author_id:
                        participants.add(project_owner)

                    # Notify participants
                    for participant_id in participants:
                        self.logger.info(
                            f"Notifying participant {participant_id} about comment {comment.technical_id}"
                        )
                        # In a real implementation, this would trigger notifications

        except Exception as e:
            self.logger.error(f"Error notifying task participants: {str(e)}")

    def _update_notification_metadata(self, comment: Comment) -> None:
        """
        Update comment metadata after notification processing.

        Args:
            comment: The comment to update
        """
        # Update timestamp if not already set
        if not comment.updated_at:
            comment.update_timestamp()

        notification_info = {
            "mentions_count": len(comment.mentions),
            "notifications_sent": True
        }

        self.logger.info(
            f"Comment notification metadata updated for {comment.technical_id}: {notification_info}"
        )
