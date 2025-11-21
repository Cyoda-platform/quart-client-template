"""
AttachmentValidationProcessor for Project Management Application

Handles attachment validation including file type checking,
size validation, and security scanning.
"""

import logging
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.attachment.version_1.attachment import Attachment
from services.services import get_entity_service


class AttachmentValidationProcessor(CyodaProcessor):
    """
    Processor for Attachment validation that checks file types,
    sizes, and performs security validation.
    """

    def __init__(self) -> None:
        super().__init__(
            name="AttachmentValidationProcessor",
            description="Validates attachments for security and compliance",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the Attachment validation.

        Args:
            entity: The Attachment to validate
            **kwargs: Additional processing parameters

        Returns:
            The validated attachment
        """
        try:
            self.logger.info(
                f"Processing attachment validation for Attachment {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Attachment for type-safe operations
            attachment = cast_entity(entity, Attachment)

            # Validate file properties
            self._validate_file_properties(attachment)

            # Validate uploader permissions
            await self._validate_uploader_permissions(attachment)

            # Perform security checks
            self._perform_security_checks(attachment)

            # Update validation metadata
            self._update_validation_metadata(attachment)

            # Log validation completion
            self.logger.info(
                f"Attachment {attachment.technical_id} validated successfully"
            )

            return attachment

        except Exception as e:
            self.logger.error(
                f"Error validating attachment {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    def _validate_file_properties(self, attachment: Attachment) -> None:
        """
        Validate file properties including size and type.

        Args:
            attachment: The attachment to validate
        """
        # Validate file size
        if attachment.file_size and attachment.file_size > attachment.MAX_FILE_SIZE:
            raise ValueError(
                f"File size {attachment.file_size} exceeds maximum allowed size "
                f"{attachment.MAX_FILE_SIZE} bytes"
            )

        # Validate content type if provided
        if attachment.content_type:
            content_type = attachment.content_type.lower()
            
            # Check for dangerous content types
            dangerous_types = [
                "application/x-executable",
                "application/x-msdownload",
                "application/x-msdos-program",
                "application/x-winexe",
                "application/x-bat",
                "application/x-sh",
                "text/x-script",
            ]
            
            if any(dangerous in content_type for dangerous in dangerous_types):
                raise ValueError(f"Content type {content_type} is not allowed for security reasons")

        # Validate filename extension
        file_extension = attachment.get_file_extension()
        if file_extension:
            dangerous_extensions = [
                "exe", "bat", "cmd", "com", "pif", "scr", "vbs", "js", "jar",
                "sh", "ps1", "py", "rb", "pl", "php"
            ]
            
            if file_extension in dangerous_extensions:
                raise ValueError(f"File extension .{file_extension} is not allowed for security reasons")

        self.logger.info(f"File properties validated for {attachment.filename}")

    async def _validate_uploader_permissions(self, attachment: Attachment) -> None:
        """
        Validate that the uploader has permissions to upload to the task.

        Args:
            attachment: The attachment to validate uploader for
        """
        entity_service = get_entity_service()

        try:
            # Get the uploader
            uploader_response = await entity_service.get(
                entity_id=attachment.uploaded_by,
                entity_class="User",
                entity_version="1"
            )

            if not uploader_response or not uploader_response.entity:
                raise ValueError(f"Uploader {attachment.uploaded_by} not found")

            uploader_data = uploader_response.entity
            is_active = uploader_data.get("isActive", True)

            if not is_active:
                raise ValueError(f"Cannot upload attachment for inactive user {attachment.uploaded_by}")

            # Get the task to validate access
            task_response = await entity_service.get(
                entity_id=attachment.task_id,
                entity_class="Task",
                entity_version="1"
            )

            if not task_response or not task_response.entity:
                raise ValueError(f"Task {attachment.task_id} not found")

            task_data = task_response.entity
            project_id = task_data.get("project_id")

            # Get project to validate membership
            if project_id:
                project_response = await entity_service.get(
                    entity_id=project_id,
                    entity_class="Project",
                    entity_version="1"
                )

                if project_response and project_response.entity:
                    project_data = project_response.entity
                    project_members = project_data.get("members", [])
                    project_owner = project_data.get("owner_id", "")

                    # Check if uploader has access to the project
                    if (attachment.uploaded_by not in project_members and 
                        attachment.uploaded_by != project_owner):
                        raise ValueError(
                            f"User {attachment.uploaded_by} does not have access to project {project_id}"
                        )

            self.logger.info(f"Uploader permissions validated for {attachment.uploaded_by}")

        except Exception as e:
            self.logger.error(f"Failed to validate uploader permissions: {str(e)}")
            raise

    def _perform_security_checks(self, attachment: Attachment) -> None:
        """
        Perform security checks on the attachment.

        Args:
            attachment: The attachment to check
        """
        # Basic filename security checks
        filename = attachment.filename.lower()
        
        # Check for suspicious patterns
        suspicious_patterns = [
            "..", "\\", "/", "<script", "javascript:", "data:", "vbscript:"
        ]
        
        for pattern in suspicious_patterns:
            if pattern in filename:
                raise ValueError(f"Filename contains suspicious pattern: {pattern}")

        # Check URL security
        url = attachment.url.lower()
        if not (url.startswith("http://") or url.startswith("https://") or url.startswith("/")):
            raise ValueError("URL must be a valid HTTP/HTTPS URL or relative path")

        self.logger.info(f"Security checks passed for {attachment.filename}")

    def _update_validation_metadata(self, attachment: Attachment) -> None:
        """
        Update attachment metadata after validation.

        Args:
            attachment: The attachment to update
        """
        # Update timestamp if not already set
        if not attachment.updated_at:
            attachment.update_timestamp()

        validation_info = {
            "validated_at": attachment.created_at,
            "file_size": attachment.file_size,
            "content_type": attachment.content_type,
            "is_secure": True
        }

        self.logger.info(
            f"Attachment validation metadata updated for {attachment.technical_id}: {validation_info}"
        )
