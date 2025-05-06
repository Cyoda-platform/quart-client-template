import os
import base64
from dotenv import load_dotenv
load_dotenv()  # Loads the .env file automatically
# Lambda to get an environment variable or raise an Exception if not found
get_env = lambda key: os.getenv(key) or (_ for _ in ()).throw(Exception(f"{key} not found"))

CYODA_HOST = get_env("CYODA_HOST")
decoded_bytes_cyoda_api_key = base64.b64decode(get_env("CYODA_API_KEY"))
API_KEY = decoded_bytes_cyoda_api_key.decode("utf-8")
decoded_bytes_cyoda_api_secret = base64.b64decode(get_env("CYODA_API_SECRET"))
API_SECRET = decoded_bytes_cyoda_api_secret.decode("utf-8")
CHAT_ID = get_env("CHAT_ID")
ENTITY_VERSION = get_env("ENTITY_VERSION")
GRPC_PROCESSOR_TAG = os.getenv("GRPC_PROCESSOR_TAG", "cloud_manager_app")
CYODA_AI_URL = os.getenv("CYODA_AI_URL", f"https://{CYODA_HOST}/ai")
CYODA_API_URL = os.getenv("CYODA_API_URL", f"https://{CYODA_HOST}/api")
GRPC_ADDRESS = os.getenv("GRPC_ADDRESS", f"grpc-{CYODA_HOST}")
PROJECT_DIR = os.getenv("PROJECT_DIR", "/tmp")
CYODA_ENTITY_TYPE_EDGE_MESSAGE = "EDGE_MESSAGE"
CHAT_REPOSITORY = os.getenv("CHAT_REPOSITORY", "cyoda")
IMPORT_WORKFLOWS = bool(os.getenv("IMPORT_WORKFLOWS", "false"))