"""
ActivityReportPublishingProcessor for Activity Tracker application.

Generates HTML and plaintext report content and sends email to admin.
"""

import logging
import os
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from application.entity.activity_report.version_1.activity_report import (
    ActivityReport,
)
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor

logger = logging.getLogger(__name__)


class ActivityReportPublishingProcessor(CyodaProcessor):
    """Generates and publishes activity reports via email."""

    def __init__(self) -> None:
        super().__init__(
            name="ActivityReportPublishingProcessor",
            description="Generates and publishes activity reports",
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Generate report content and send email.

        Args:
            entity: The ActivityReport entity to publish
            **kwargs: Additional processing parameters

        Returns:
            The published ActivityReport entity
        """
        try:
            tech_id = getattr(entity, "technical_id", "<unknown>")
            self.logger.info(f"Publishing ActivityReport {tech_id}")

            report = cast_entity(entity, ActivityReport)

            html_content = self._generate_html_report(report)
            text_content = self._generate_text_report(report)

            report.report_content_html = html_content
            report.report_content_text = text_content

            admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
            await self._send_email(
                recipient=admin_email,
                subject=f"Daily Activity Report - {report.report_date}",
                html_content=html_content,
                text_content=text_content,
            )

            report.email_recipient = admin_email
            report.email_sent_at = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )

            self.logger.info(
                f"ActivityReport {report.technical_id} published successfully"
            )
            return report

        except Exception as e:
            tech_id = getattr(entity, "technical_id", "<unknown>")
            self.logger.error(f"Error publishing entity {tech_id}: {str(e)}")
            raise

    def _generate_html_report(self, report: ActivityReport) -> str:
        """Generate HTML formatted report."""
        anomalies_html = ""
        if report.flagged_anomalies:
            anomalies_html = "<h3>Flagged Anomalies</h3><ul>"
            for anomaly in report.flagged_anomalies:
                anomalies_html += (
                    f"<li>{anomaly['type']}: {anomaly['id']} "
                    f"(z-score: {anomaly['zScore']}) - {anomaly['reason']}</li>"
                )
            anomalies_html += "</ul>"

        top_types_html = "<h3>Top Activity Types</h3><ol>"
        for activity in report.top_activity_types:
            top_types_html += (
                f"<li>{activity['type']}: {activity['count']} activities</li>"
            )
        top_types_html += "</ol>"

        trends_html = "<h3>Trend Highlights</h3><ul>"
        for trend in report.trend_highlights:
            trends_html += f"<li>{trend}</li>"
        trends_html += "</ul>"

        return f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                h1 {{ color: #333; }}
                h3 {{ color: #666; }}
            </style>
        </head>
        <body>
            <h1>Daily Activity Report</h1>
            <p><strong>Report Date:</strong> {report.report_date}</p>
            <p><strong>Total Activities:</strong> {report.total_activities}</p>
            {top_types_html}
            {trends_html}
            {anomalies_html}
            <hr>
            <p><small>Generated at {report.email_sent_at}</small></p>
        </body>
        </html>
        """

    def _generate_text_report(self, report: ActivityReport) -> str:
        """Generate plaintext formatted report."""
        lines = [
            "=" * 60,
            "DAILY ACTIVITY REPORT",
            "=" * 60,
            f"Report Date: {report.report_date}",
            f"Total Activities: {report.total_activities}",
            "",
            "TOP ACTIVITY TYPES:",
        ]

        for activity in report.top_activity_types:
            lines.append(f"  - {activity['type']}: {activity['count']} activities")

        lines.extend(["", "TREND HIGHLIGHTS:"])
        for trend in report.trend_highlights:
            lines.append(f"  - {trend}")

        if report.flagged_anomalies:
            lines.extend(["", "FLAGGED ANOMALIES:"])
            for anomaly in report.flagged_anomalies:
                lines.append(
                    f"  - {anomaly['type']}: {anomaly['id']} "
                    f"(z-score: {anomaly['zScore']}) - {anomaly['reason']}"
                )

        lines.extend(["", "=" * 60, f"Generated at {report.email_sent_at}"])

        return "\n".join(lines)

    async def _send_email(
        self,
        recipient: str,
        subject: str,
        html_content: str,
        text_content: str,
    ) -> None:
        """
        Send email with HTML and plaintext content.

        Args:
            recipient: Email recipient address
            subject: Email subject
            html_content: HTML formatted content
            text_content: Plaintext formatted content
        """
        smtp_host = os.getenv("SMTP_HOST", "localhost")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")
        sender_email = os.getenv("SENDER_EMAIL", "noreply@activity-tracker.local")

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = sender_email
            msg["To"] = recipient

            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(smtp_host, smtp_port) as server:
                if smtp_user and smtp_password:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                server.sendmail(sender_email, recipient, msg.as_string())

            self.logger.info(f"Email sent successfully to {recipient}")

        except Exception as e:
            self.logger.error(f"Failed to send email: {str(e)}")
            raise
