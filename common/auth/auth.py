import json
import logging
import requests

from common.config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Helper function to authenticate and retrieve token
def authenticate():
    login_url = f"{config.CYODA_API_URL}/auth/login"
    headers = {"Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest"}
    auth_data = {"username": config.API_KEY, "password": config.API_SECRET}

    logger.info("Attempting to authenticate with Cyoda API.")

    try:
        response = requests.post(login_url, headers=headers, data=json.dumps(auth_data), timeout=10)

        if response.status_code == 200:
            token = response.json().get("token")
            logger.info("Authentication successful!")
            return token
        else:
            logger.error(f"Authentication failed with {response}")
            return None

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return None