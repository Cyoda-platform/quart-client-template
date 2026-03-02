"""
Enhanced configuration module with backward compatibility.

This module provides backward compatibility with the old configuration system
while using the new configuration manager under the hood.
"""

import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import new configuration system
try:
    from .manager import get_config_manager  # type: ignore[import-untyped]

    _use_new_config = True
    _config_manager = get_config_manager()
except ImportError:
    _use_new_config = False


# Legacy function for backward compatibility
def get_env(key: str) -> str:
    """Get environment variable or raise exception if not found."""
    value = os.getenv(key)
    if value is None:
        raise Exception(f"{key} not found")
    return value


SKIP_SSL = os.getenv("SKIP_SSL", False)
# Whether to verify SSL certificates in HTTP requests. Set CYODA_VERIFY_SSL=false
# for self-signed certificates in development; defaults to True (verify).
CYODA_VERIFY_SSL: bool = os.getenv("CYODA_VERIFY_SSL", "true").lower() not in (
    "false",
    "0",
    "no",
)
CYODA_HOST = get_env("CYODA_HOST")
CYODA_CLIENT_ID = get_env("CYODA_CLIENT_ID")
CYODA_CLIENT_SECRET = get_env("CYODA_CLIENT_SECRET")
CYODA_TOKEN_URL = f"{'http' if SKIP_SSL else 'https'}://{CYODA_HOST}/api/oauth/token"
CHAT_ID = os.getenv("CHAT_ID", "cyoda-client")
ENTITY_VERSION = os.getenv("ENTITY_VERSION", "1")
GRPC_PROCESSOR_TAG = os.getenv("GRPC_PROCESSOR_TAG", "cloud_manager_app")
CYODA_AI_URL = os.getenv(
    "CYODA_AI_URL", f"{'http' if SKIP_SSL else 'https'}://{CYODA_HOST}/ai"
)
CYODA_API_URL = os.getenv(
    "CYODA_API_URL", f"{'http' if SKIP_SSL else 'https'}://{CYODA_HOST}/api"
)
GRPC_ADDRESS = os.getenv("GRPC_ADDRESS", f"grpc-{CYODA_HOST}")
PROJECT_DIR = os.getenv("PROJECT_DIR", os.path.expanduser("~/cyoda_projects"))
CHAT_REPOSITORY = os.getenv("CHAT_REPOSITORY", "cyoda")
IMPORT_WORKFLOWS = bool(os.getenv("IMPORT_WORKFLOWS", "true"))

# Constants
CYODA_ENTITY_TYPE_EDGE_MESSAGE = "EDGE_MESSAGE"
GENERAL_MEMORY_TAG = "general"
