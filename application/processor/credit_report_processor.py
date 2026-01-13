from datetime import datetime, timezone
from typing import Any, Dict, List

from application.entity.credit_report.version_1.credit_report import CreditReport
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class CreditReportProcessor(CyodaProcessor):
    def __init__(self) -> None:
        super().__init__(
            name="CreditReportProcessor",
            description="Analyzes credit report and identifies risk indicators",
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        try:
            self.logger.info(
                f"Processing CreditReport {getattr(entity, 'technical_id', '<unknown>')}"
            )

            credit_report = cast_entity(entity, CreditReport)

            risk_indicators = self._analyze_credit_report(credit_report)
            credit_report.risk_indicators = risk_indicators

            self.logger.info(
                f"CreditReport {credit_report.technical_id} analyzed successfully"
            )
            return credit_report

        except Exception as e:
            self.logger.error(f"Error processing credit report: {str(e)}")
            raise

    def _analyze_credit_report(self, report: CreditReport) -> List[str]:
        indicators: List[str] = []

        if report.credit_score and report.credit_score < 620:
            indicators.append("LOW_CREDIT_SCORE")

        if report.credit_utilization_percent > 80:
            indicators.append("HIGH_UTILIZATION")

        if report.delinquencies_30_days > 0:
            indicators.append("RECENT_DELINQUENCY")

        if report.delinquencies_60_days > 0 or report.delinquencies_90_days > 0:
            indicators.append("SERIOUS_DELINQUENCY")

        if report.public_records > 0:
            indicators.append("PUBLIC_RECORDS")

        if report.inquiries_last_6_months > 5:
            indicators.append("MULTIPLE_INQUIRIES")

        if report.average_account_age_months < 12:
            indicators.append("NEW_CREDIT_ACCOUNTS")

        return indicators
