"""
DataAnalysisValidationCriterion for validating CSV URLs.

Checks that the CSV URL is valid and accessible before processing.
"""

import logging
from typing import Any

import requests

from application.entity.data_analysis import DataAnalysis
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity

logger = logging.getLogger(__name__)


class DataAnalysisValidationCriterion(CyodaCriteriaChecker):
    """Validation criterion for DataAnalysis entities."""

    def __init__(self) -> None:
        super().__init__(
            name="DataAnalysisValidationCriterion",
            description="Validates CSV URL accessibility and format",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if DataAnalysis entity is valid for processing.

        Args:
            entity: The CyodaEntity to validate
            **kwargs: Additional criteria parameters

        Returns:
            True if valid, False otherwise
        """
        try:
            data_analysis = cast_entity(entity, DataAnalysis)
            logger.info(f"Validating DataAnalysis {data_analysis.technical_id}")

            # Check URL format
            if not data_analysis.csv_url:
                logger.warning("CSV URL is empty")
                return False

            if not data_analysis.csv_url.startswith(("http://", "https://")):
                logger.warning(f"Invalid URL format: {data_analysis.csv_url}")
                return False

            # Check URL accessibility
            try:
                response = requests.head(data_analysis.csv_url, timeout=10)
                if response.status_code != 200:
                    logger.warning(
                        f"URL not accessible: {data_analysis.csv_url} "
                        f"(status {response.status_code})"
                    )
                    return False
            except requests.RequestException as e:
                logger.warning(f"Failed to access URL: {str(e)}")
                return False

            logger.info(f"Validation passed for {data_analysis.technical_id}")
            return True

        except Exception as e:
            logger.exception(f"Error validating DataAnalysis: {str(e)}")
            return False
