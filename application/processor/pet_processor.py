"""
Pet processors for Cyoda Client Application.

Handles downloading and processing pet data from the Swagger Petstore API.
"""

import logging
from typing import Any, Dict, Optional

import aiohttp

from application.entity.pet import Pet
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class PetDownloadProcessor(CyodaProcessor):
    """
    Processor for downloading pet data from the Swagger Petstore API.
    """

    PETSTORE_API_BASE = "https://petstore3.swagger.io/api/v3"

    def __init__(self) -> None:
        super().__init__(
            name="PetDownloadProcessor",
            description="Downloads pet data from Swagger Petstore API",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Download pet data from Petstore API.

        Args:
            entity: The Pet entity to process
            **kwargs: Additional processing parameters

        Returns:
            The pet entity with downloaded data
        """
        try:
            self.logger.info(
                f"Downloading pet data for {getattr(entity, 'technical_id', '<unknown>')}"
            )

            pet = cast_entity(entity, Pet)

            # If pet has a pet_id, fetch from API
            if pet.pet_id:
                await self._fetch_pet_from_api(pet)

            # Update timestamp
            pet.update_timestamp()

            self.logger.info(
                f"Pet {pet.technical_id} downloaded successfully"
            )

            return pet

        except Exception as e:
            self.logger.error(
                f"Error downloading pet {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    async def _fetch_pet_from_api(self, pet: Pet) -> None:
        """
        Fetch pet data from Petstore API by pet ID.

        Args:
            pet: The Pet entity to update with API data
        """
        try:
            url = f"{self.PETSTORE_API_BASE}/pet/{pet.pet_id}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Update pet with API data
                        pet.name = data.get("name", pet.name)
                        pet.status = data.get("status", pet.status)
                        pet.category = data.get("category")
                        pet.photo_urls = data.get("photoUrls")
                        pet.tags = data.get("tags")
                        self.logger.info(
                            f"Fetched pet {pet.pet_id} from API"
                        )
                    else:
                        self.logger.warning(
                            f"Failed to fetch pet {pet.pet_id}: HTTP {response.status}"
                        )
        except Exception as e:
            self.logger.error(
                f"Error fetching pet from API: {str(e)}"
            )
            raise


class PetProcessProcessor(CyodaProcessor):
    """
    Processor for processing and enriching pet data.
    """

    def __init__(self) -> None:
        super().__init__(
            name="PetProcessProcessor",
            description="Processes and enriches pet data",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process and enrich pet data.

        Args:
            entity: The Pet entity to process
            **kwargs: Additional processing parameters

        Returns:
            The processed pet entity
        """
        try:
            self.logger.info(
                f"Processing pet {getattr(entity, 'technical_id', '<unknown>')}"
            )

            pet = cast_entity(entity, Pet)

            # Create processed data
            processed_data = self._create_processed_data(pet)
            pet.set_processed_data(processed_data)

            self.logger.info(
                f"Pet {pet.technical_id} processed successfully"
            )

            return pet

        except Exception as e:
            self.logger.error(
                f"Error processing pet {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    def _create_processed_data(self, pet: Pet) -> Dict[str, Any]:
        """
        Create processed data for the pet.

        Args:
            pet: The Pet entity to process

        Returns:
            Dictionary containing processed data
        """
        processed_data: Dict[str, Any] = {
            "name_upper": pet.name.upper(),
            "status": pet.status,
            "has_photos": bool(pet.photo_urls and len(pet.photo_urls) > 0),
            "photo_count": len(pet.photo_urls) if pet.photo_urls else 0,
            "has_tags": bool(pet.tags and len(pet.tags) > 0),
            "tag_count": len(pet.tags) if pet.tags else 0,
        }

        if pet.category:
            processed_data["category_name"] = pet.category.get("name", "Unknown")

        return processed_data

