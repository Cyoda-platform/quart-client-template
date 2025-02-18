# Here's the completed `save_favorite_flight` function. It interacts with the `entity_service` to persist favorite flights, removing any mock or non-relevant code, and includes logging for significant actions. The supplementary functions start with an underscore as requested.
# 
# ```python
import json
import logging
from app_init.app_init import entity_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def save_favorite_flight(data, meta={'token': 'cyoda_token'}):
    """
    Create a new flight_favorite.
    """
    try:
        flight_id = data.get('flightId')
        
        if not flight_id:
            logger.error("No flight ID provided.")
            return {"error": "Flight ID is required."}

        # Save the favorite flight using the entity service
        favorite_id = await entity_service.add_item(
            token=meta['token'],
            entity_model='favorite_flight',
            entity_version='v1',  # Assuming versioning is necessary
            entity={"flight_id": flight_id}
        )

        logger.info(f"Favorite flight saved with ID: {favorite_id}")
        return {"message": "Flight added to favorites.", "favoriteId": favorite_id}

    except Exception as e:
        logger.error(f"Error in save_favorite_flight: {e}")
        return {"error": str(e)}

async def _fetch_favorite_flights(token):
    """
    Fetch all favorite flights for the user.
    """
    try:
        favorites = await entity_service.get_items(
            token=token,
            entity_model='favorite_flight',
            entity_version='v1'
        )
        logger.info("Fetched favorite flights successfully.")
        return favorites
    except Exception as e:
        logger.error(f"Error fetching favorite flights: {e}")
        return []
# ```
# 
# ### Explanation:
# 1. **Error Handling**:
#    - The function checks if a `flightId` is provided and logs an error if it's missing.
#    - It catches exceptions and logs them, returning an appropriate error message.
# 
# 2. **Saving Favorite Flight**:
#    - The flight ID is used to create a new favorite flight entity using the `entity_service.add_item` method.
#    - The function assumes a versioning scheme for entities, which can be adjusted based on your actual implementation.
# 
# 3. **Logging**:
#    - Added logging statements to trace the operations, including successful saves and any errors.
# 
# 4. **Private Function**:
#    - `_fetch_favorite_flights` is an example of a private function that fetches all favorite flights for a user, demonstrating how to interact with the `entity_service`.
# 
# This implementation provides a complete workflow for saving favorite flights while adhering to the requirements you've specified.