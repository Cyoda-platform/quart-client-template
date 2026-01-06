"""
AlertingProcessor for institutional trading platform.

Pushes alerts for risk breaches and compliance flags to operator channels.
Used by risk_checking.transition 'reject' and execution_processing.transition 'investigate'.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from common.processor.base import CyodaEntity, CyodaProcessor


class AlertingProcessor(CyodaProcessor):
    """
    Sends alerts for risk breaches and compliance issues to operators.
    """

    def __init__(self) -> None:
        super().__init__(
            name="AlertingProcessor",
            description="Sends alerts for risk breaches and compliance flags",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Send alert for the entity event.

        Args:
            entity: The entity triggering the alert
            **kwargs: Additional alert parameters (alert_type, severity, reason)

        Returns:
            The entity unchanged
        """
        try:
            entity_id = getattr(entity, "technical_id", None)
            self.logger.info(f"Processing alert for {entity_id}")

            # Determine alert type and severity
            alert_info = self._determine_alert_info(entity, **kwargs)

            if alert_info["should_alert"]:
                # Send alerts to appropriate channels
                await self._send_alerts(entity, alert_info)

                # Store alert metadata
                if not hasattr(entity, "alertMetadata"):
                    setattr(entity, "alertMetadata", {})
                alert_metadata = getattr(entity, "alertMetadata")
                alert_metadata["last_alert"] = alert_info
                alert_metadata["alert_sent_at"] = (
                    datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                )

                self.logger.info(
                    f"Alert sent: {alert_info['type']} - {alert_info['message']}"
                )
            else:
                self.logger.debug("No alert needed for this event")

            return entity

        except Exception as e:
            self.logger.error(f"Error sending alert: {str(e)}")
            raise

    def _determine_alert_info(
        self, entity: CyodaEntity, **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Determine alert type, severity, and recipients.

        Args:
            entity: The entity triggering the alert
            **kwargs: Additional context

        Returns:
            Alert information dictionary
        """
        entity_type = getattr(entity, "entity_type", "unknown")
        current_state = getattr(entity, "state", None)

        alert_type = kwargs.get("alert_type", "UNKNOWN")
        severity = kwargs.get("severity", "INFO")
        reason = kwargs.get("reason", "No reason provided")

        # Determine if alert should be sent
        should_alert = severity in ["WARNING", "ERROR", "CRITICAL"]

        # Determine recipients based on severity
        recipients = self._determine_recipients(severity, entity_type)

        alert_info: Dict[str, Any] = {
            "should_alert": should_alert,
            "type": alert_type,
            "severity": severity,
            "message": reason,
            "entity_type": entity_type,
            "entity_id": getattr(entity, "technical_id", None),
            "state": current_state,
            "recipients": recipients,
            "timestamp": (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            ),
        }

        return alert_info

    def _determine_recipients(self, severity: str, entity_type: str) -> list[str]:
        """
        Determine alert recipients based on severity and entity type.

        Args:
            severity: Alert severity level
            entity_type: Type of entity triggering alert

        Returns:
            List of recipient channels
        """
        recipients: list[str] = []

        # All alerts go to compliance
        recipients.append("compliance@trading.internal")

        # Risk alerts go to risk team
        if entity_type == "order" or entity_type == "execution":
            recipients.append("risk@trading.internal")

        # Critical alerts go to operations
        if severity == "CRITICAL":
            recipients.append("operations@trading.internal")
            recipients.append("management@trading.internal")

        # High severity alerts go to trading desk
        if severity in ["ERROR", "CRITICAL"]:
            recipients.append("trading@trading.internal")

        return recipients

    async def _send_alerts(
        self, entity: CyodaEntity, alert_info: Dict[str, Any]
    ) -> None:
        """
        Send alerts to appropriate channels.

        Args:
            entity: The entity triggering the alert
            alert_info: Alert information
        """
        # TODO: Implement alert delivery channels
        # - Email notifications
        # - Slack/Teams messages
        # - SMS for critical alerts
        # - PagerDuty for on-call escalation
        # - Alert dashboard updates

        recipients = alert_info.get("recipients", [])
        alert_type = alert_info.get("type", "UNKNOWN")
        severity = alert_info.get("severity", "INFO")
        message = alert_info.get("message", "")

        self.logger.info(
            f"Sending {severity} alert ({alert_type}) to {len(recipients)} recipients: {message}"
        )

        # Mock email alert
        for recipient in recipients:
            self.logger.debug(f"Email alert to {recipient}: {message}")

        # Mock Slack alert for critical issues
        if severity == "CRITICAL":
            self.logger.warning(
                f"CRITICAL ALERT: {alert_type} - {message} - Entity: {alert_info.get('entity_id')}"
            )

    def _format_alert_message(self, alert_info: Dict[str, Any]) -> str:
        """
        Format alert message for delivery.

        Args:
            alert_info: Alert information

        Returns:
            Formatted alert message
        """
        message = (
            f"[{alert_info['severity']}] {alert_info['type']}\n"
            f"Entity: {alert_info['entity_type']} {alert_info['entity_id']}\n"
            f"State: {alert_info['state']}\n"
            f"Message: {alert_info['message']}\n"
            f"Time: {alert_info['timestamp']}"
        )

        return message
