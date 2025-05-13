import asyncio
import logging
import os

from common.config.config import CHAT_REPOSITORY
from common.grpc_client.grpc_client import GrpcClient
from common.repository.cyoda.cyoda_init import CyodaInitService
from common.repository.cyoda.cyoda_repository import CyodaRepository
from common.repository.in_memory_db import InMemoryRepository
from common.service.service import EntityServiceImpl
from common.auth.cyoda_auth import CyodaAuthService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class BeanFactory:
    _instance = None
    _initialized = False

    def __new__(cls, config=None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config=None):
        # Only run the initialization logic a single time
        if self.__class__._initialized:
            return
        self.__class__._initialized = True

        # === your existing init logic ===
        self.chat_lock = asyncio.Lock()

        try:
            self.cyoda_auth_service = CyodaAuthService()
            self.entity_repository = self._create_repository(
                repo_type=CHAT_REPOSITORY,
                cyoda_auth_service=self.cyoda_auth_service
            )
            self.entity_service = EntityServiceImpl(
                repository=self.entity_repository
            )
            self.grpc_client = GrpcClient(auth=self.cyoda_auth_service)

        except Exception as e:
            logger.exception("Error during BeanFactory initialization:", e)
            raise

    def _load_default_config(self):
        """
        Load default configuration values, optionally from environment variables.
        """
        return {
            "CHAT_REPOSITORY": os.getenv("CHAT_REPOSITORY", "inmemory")
        }

    def _create_repository(self, repo_type, cyoda_auth_service):
        """
        Create the appropriate repository based on configuration.
        """
        if repo_type.lower() == "cyoda":
            return CyodaRepository(cyoda_auth_service=cyoda_auth_service)
        else:
            return InMemoryRepository()

    def get_services(self):
        """
        Retrieve a dictionary of all managed services for further use.
        """
        return {
            "grpc_client": self.grpc_client,
            "entity_repository": self.entity_repository,
            "entity_service": self.entity_service,
            "cyoda_auth_service": self.cyoda_auth_service,
        }