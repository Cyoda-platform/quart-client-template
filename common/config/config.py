import os
import base64
from dotenv import load_dotenv

load_dotenv()  # Loads the .env file automatically from the current working directory

def get_env(key, default=None):
    """Get the environment variable for 'key'.
    If not found and no default is provided, raise an Exception."""
    value = os.getenv(key, default)
    if value is None:
        raise Exception(f"{key} not found")
    return value

# For development, you can supply default values.
# Replace these defaults with your actual values or remove the defaults once you have them set externally.
CYODA_HOST = get_env("CYODA_HOST", "localhost")
CYODA_AI_URL = os.getenv("CYODA_AI_URL", f"https://{CYODA_HOST}/ai")
CYODA_API_URL = os.getenv("CYODA_API_URL", f"https://{CYODA_HOST}/api")
GRPC_ADDRESS = os.getenv("GRPC_ADDRESS", f"grpc-{CYODA_HOST}")

# Here, default API keys are provided as base64 encoded strings ("default_api_key" and "default_api_secret").
decoded_bytes_cyoda_api_key = base64.b64decode(get_env("CYODA_API_KEY", "ZGVmYXVsdF9hcGlfa2V5"))
API_KEY = decoded_bytes_cyoda_api_key.decode("utf-8")

decoded_bytes_cyoda_api_secret = base64.b64decode(get_env("CYODA_API_SECRET", "ZGVmYXVsdF9hcGlfc2VjcmV0"))
API_SECRET = decoded_bytes_cyoda_api_secret.decode("utf-8")

CHAT_ID = os.getenv("CHAT_ID")

ENTITY_VERSION = os.getenv("ENTITY_VERSION", "1000")
GRPC_PROCESSOR_TAG = os.getenv("GRPC_PROCESSOR_TAG", CHAT_ID)

CYODA_AI_API = 'cyoda'
WORKFLOW_AI_API = 'workflow'
MOCK_AI = os.getenv("MOCK_AI", "false")
CONNECTION_AI_API = get_env("CONNECTION_AI_API", "default_connection_ai_api")
RANDOM_AI_API = get_env("RANDOM_AI_API", "default_random_ai_api")
TRINO_AI_API = get_env("TRINO_AI_API", "default_trino_ai_api")
CHAT_REPOSITORY = os.getenv("CHAT_REPOSITORY", "cyoda")
PROJECT_DIR = os.getenv("PROJECT_DIR", "/tmp")
REPOSITORY_URL = os.getenv("REPOSITORY_URL", "https://github.com/Cyoda-platform/quart-client-template")
REPOSITORY_NAME = REPOSITORY_URL.split('/')[-1].replace('.git', '')