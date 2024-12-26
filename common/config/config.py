import base64
import os
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
# Load environment variables
CYODA_AI_URL = os.getenv("CYODA_AI_URL")
CYODA_API_URL = os.getenv("CYODA_API_URL") + "/api"
decoded_bytes_cyoda_api_key = base64.b64decode(os.getenv("CYODA_API_KEY"))
API_KEY = decoded_bytes_cyoda_api_key.decode("utf-8")
decoded_bytes_cyoda_api_secret = base64.b64decode(os.getenv("CYODA_API_SECRET"))
API_SECRET = decoded_bytes_cyoda_api_secret.decode("utf-8")

ENTITY_VERSION = os.getenv("ENTITY_VERSION", "1000")
GRPC_ADDRESS = os.environ["GRPC_ADDRESS"]
GRPC_PROCESSOR_TAG=os.getenv("GRPC_PROCESSOR_TAG", "elt")
CYODA_AI_API = 'cyoda'
WORKFLOW_AI_API = 'workflow'
mock_ai=True
MOCK_AI = os.getenv("MOCK_AI",  "false")
CONNECTION_AI_API = os.getenv("CONNECTION_AI_API")
RANDOM_AI_API = os.getenv("RANDOM_AI_API")
TRINO_AI_API = os.getenv("TRINO_AI_API")
CHAT_ID = os.getenv("CHAT_ID")