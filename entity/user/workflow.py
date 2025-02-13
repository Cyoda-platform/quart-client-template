# Here's the `workflow.py` file implementing the user creation workflow as specified:
# 
# ```python
import json
import logging
from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_user(data, meta={"token": "cyoda_token"}):
    """Create a new user with provided details."""
    
    try:
        username = data.get('username')
        password = data.get('password')  # TODO: Hash the password before storing
        email = data.get('email')

        # Mock storage (replace with a database connection in production)
        user_id = len(users) + 1
        users[user_id] = {'username': username, 'password': password, 'email': email}
        
        return {
            'user_id': user_id,
            'message': 'User created successfully.'
        }, 201

    except Exception as e:
        logger.error(f"Error in create_user: {e}")
        raise
# ```
# 
# ### Explanation:
# - The function `create_user` is defined to handle the user creation process.
# - It retrieves the `username`, `password`, and `email` from the incoming `data`.
# - A mock storage mechanism is used to simulate user storage, where a new user is added to the `users` dictionary.
# - The function returns a success message along with the new user's ID.
# - Error handling is included to log any exceptions that occur during the process. 
# 
# This implementation follows the structure and requirements outlined in your request.