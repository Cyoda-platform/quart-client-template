"""
StartReportGenerationProcessor for Cyoda Client Application

Handles the initialization of report generation.
Compiles report data from analyses as specified in functional requirements.
"""

import logging
from typing import Any, Dict, List

from application.entity.report.version_1.report import Report
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class StartReportGenerationProcessor(CyodaProcessor):
    """
    Processor for Report that begins compiling report data from analyses.
    Aggregates analysis results for the specified time period.
    """

    def __init__(self) -> None:
        super().__init__(
            name="StartReportGenerationProcessor",
            description="Begins compiling report data from analyses for the specified period",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the Report entity to begin generation.

        Args:
            entity: The Report entity to process
            **kwargs: Additional processing parameters

        Returns:
            The processed entity with generation started
        """
        try:
            self.logger.info(
                f"Starting report generation for Report {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Report for type-safe operations
            report = cast_entity(entity, Report)

            # Set generation started timestamp
            report.set_generation_started_at()

            # Get analyses for the specified period
            analyses = await self._get_analyses_by_period(
                report.report_period_start, report.report_period_end
            )

            # Calculate report metrics
            total_comments = len(analyses)
            avg_sentiment = self._calculate_average_sentiment(analyses)
            top_keywords = self._extract_top_keywords(analyses)
            toxicity_summary = self._calculate_toxicity_summary(analyses)

            # Set report metrics
            report.set_report_metrics(
                total_comments=total_comments,
                avg_sentiment=avg_sentiment,
                top_keywords=top_keywords,
                toxicity_summary=toxicity_summary,
            )

            self.logger.info(
                f"Report generation started for Report {report.technical_id} "
                f"(period: {report.report_period_start} to {report.report_period_end}, "
                f"comments: {total_comments})"
            )

            return report

        except Exception as e:
            self.logger.error(
                f"Error starting report generation for entity {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    async def _get_analyses_by_period(
        self, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """
        Retrieve analyses for the specified time period.

        Args:
            start_date: Start date in ISO 8601 format
            end_date: End date in ISO 8601 format

        Returns:
            List of analysis entities
        """
        # In a real implementation, this would query the entity service with date filters
        # For now, we'll simulate some analysis data

        self.logger.info(f"Retrieving analyses for period {start_date} to {end_date}")

        # Mock analysis data for demonstration
        mock_analyses = [
            {
                "comment_id": "comment_1",
                "sentiment_score": 0.7,
                "sentiment_label": "positive",
                "keywords": ["great", "product", "quality"],
                "language": "en",
                "toxicity_score": 0.1,
                "analyzed_at": start_date,
            },
            {
                "comment_id": "comment_2",
                "sentiment_score": -0.3,
                "sentiment_label": "negative",
                "keywords": ["bad", "service", "slow"],
                "language": "en",
                "toxicity_score": 0.4,
                "analyzed_at": start_date,
            },
            {
                "comment_id": "comment_3",
                "sentiment_score": 0.1,
                "sentiment_label": "neutral",
                "keywords": ["okay", "average", "normal"],
                "language": "en",
                "toxicity_score": 0.0,
                "analyzed_at": end_date,
            },
        ]

        return mock_analyses

    def _calculate_average_sentiment(self, analyses: List[Dict[str, Any]]) -> float:
        """
        Calculate average sentiment score from analyses.

        Args:
            analyses: List of analysis entities

        Returns:
            Average sentiment score
        """
        if not analyses:
            return 0.0

        sentiment_scores = [
            analysis.get("sentiment_score", 0.0)
            for analysis in analyses
            if analysis.get("sentiment_score") is not None
        ]

        if not sentiment_scores:
            return 0.0

        return sum(sentiment_scores) / len(sentiment_scores)

    def _extract_top_keywords(self, analyses: List[Dict[str, Any]]) -> List[str]:
        """
        Extract top keywords from analyses.

        Args:
            analyses: List of analysis entities

        Returns:
            List of top keywords
        """
        keyword_counts: Dict[str, int] = {}

        for analysis in analyses:
            keywords = analysis.get("keywords", [])
            if keywords:
                for keyword in keywords:
                    keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1

        # Sort by frequency and return top 10
        sorted_keywords = sorted(
            keyword_counts.items(), key=lambda x: x[1], reverse=True
        )
        return [keyword for keyword, count in sorted_keywords[:10]]

    def _calculate_toxicity_summary(
        self, analyses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate toxicity summary from analyses.

        Args:
            analyses: List of analysis entities

        Returns:
            Dictionary containing toxicity metrics
        """
        if not analyses:
            return {"avg_toxicity": 0.0, "high_toxicity_count": 0, "total_analyzed": 0}

        toxicity_scores = [
            analysis.get("toxicity_score", 0.0)
            for analysis in analyses
            if analysis.get("toxicity_score") is not None
        ]

        if not toxicity_scores:
            return {
                "avg_toxicity": 0.0,
                "high_toxicity_count": 0,
                "total_analyzed": len(analyses),
            }

        avg_toxicity = sum(toxicity_scores) / len(toxicity_scores)
        high_toxicity_count = sum(1 for score in toxicity_scores if score > 0.7)

        return {
            "avg_toxicity": avg_toxicity,
            "high_toxicity_count": high_toxicity_count,
            "total_analyzed": len(analyses),
        }
