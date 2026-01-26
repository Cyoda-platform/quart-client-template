"""
NewsletterFetchProcessor for the newsletter application.

Fetches a random cat fact from the Cat Fact API and stores it in the newsletter.
"""

import logging
from typing import Any

import aiohttp

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.newsletter import Newsletter


class NewsletterFetchProcessor(CyodaProcessor):
    """
    Processor that fetches a random cat fact from the Cat Fact API
    and stores it in the newsletter entity.
    """

    def __init__(self) -> None:
        super().__init__(
            name="NewsletterFetchProcessor",
            description="Fetches a random cat fact from the Cat Fact API",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Fetch a cat fact and store it in the newsletter.

        Args:
            entity: The Newsletter entity to process
            **kwargs: Additional processing parameters

        Returns:
            The newsletter entity with the fetched cat fact
        """
        try:
            self.logger.info(
                f"Fetching cat fact for newsletter {getattr(entity, 'technical_id', '<unknown>')}"
            )

            newsletter = cast_entity(entity, Newsletter)

            cat_fact = await self._fetch_cat_fact()
            newsletter.cat_fact = cat_fact

            self.logger.info(
                f"Newsletter {newsletter.technical_id} fetched successfully"
            )

            return newsletter

        except Exception as e:
            self.logger.error(
                f"Error fetching cat fact for newsletter {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    async def _fetch_cat_fact(self) -> str:
        """
        Fetch a random cat fact from the Cat Fact API.

        Returns:
            A random cat fact string
        """
        async with aiohttp.ClientSession() as session:
            async with session.get("https://catfact.ninja/fact") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("fact", "Unable to fetch cat fact")
                else:
                    raise Exception(f"Failed to fetch cat fact: {response.status}")
