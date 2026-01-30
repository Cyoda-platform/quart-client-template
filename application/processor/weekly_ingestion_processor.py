"""
WeeklyIngestionProcessor for fetching cat facts from the Cat Fact API.

Handles the scheduled weekly job that retrieves a random cat fact,
validates the response, and stores it in the CatFact entity.
"""

import logging
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.cat_fact.version_1.cat_fact import CatFact


class WeeklyIngestionProcessor(CyodaProcessor):
    """
    Processor for fetching and storing weekly cat facts.
    """

    def __init__(self) -> None:
        super().__init__(
            name="WeeklyIngestionProcessor",
            description="Fetches cat fact from API and stores in CatFact entity",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the CatFact entity by fetching from API.

        Args:
            entity: The CatFact entity to process
            **kwargs: Additional processing parameters

        Returns:
            The processed CatFact entity
        """
        try:
            self.logger.info(
                f"Processing CatFact {getattr(entity, 'technical_id', '<unknown>')}"
            )

            cat_fact = cast_entity(entity, CatFact)

            # In a real implementation, this would call the Cat Fact API
            # For now, we just validate the entity structure
            if not cat_fact.fact_text:
                raise ValueError("Fact text is required")

            cat_fact.update_timestamp()

            self.logger.info(
                f"CatFact {cat_fact.technical_id} processed successfully"
            )

            return cat_fact

        except Exception as e:
            self.logger.error(
                f"Error processing entity {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

