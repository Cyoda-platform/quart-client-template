import logging
import threading
from typing import Any, List

from common.config.config import CHAT_REPOSITORY
from common.repository.crud_repository import CrudRepository
from common.service.entity_service_interface import EntityService
from common.utils.utils import parse_entity

logger = logging.getLogger('quart')

class EntityServiceImpl(EntityService):
    _instance = None
    _lock = threading.Lock()
    _repository: CrudRepository = None
    _model_registry: None

    def __new__(cls, repository: CrudRepository = None, model_registry = None, mock=False):
        logger.info("initializing CyodaService")
        # Ensuring only one instance is created
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(EntityServiceImpl, cls).__new__(cls)
                    # Only initialize _repository during the first instantiation
                    if repository is not None:
                        cls._instance._repository = repository
                    cls._model_registry=model_registry if model_registry else {}
        return cls._instance

    def __init__(self, repository: CrudRepository, model_registry = None):
        # You can leave this empty if no further initialization is required,
        # or add additional initialization app_init here if needed.
        pass

    async def get_item(self, token: str, entity_model: str, entity_version: str, technical_id: str, meta = None) -> Any:
        """Retrieve a single item based on its ID."""
        repository_meta = await self._repository.get_meta(token, entity_model, entity_version)
        if meta:
            repository_meta.update(meta)
        resp = await self._repository.find_by_id(meta, technical_id)
        if resp and isinstance(resp, dict) and resp.get("errorMessage"):
            return []
        if entity_model:
            model_cls = self._model_registry.get(entity_model.lower())
            resp = parse_entity(model_cls, resp)
        return resp

    async def get_items(self, token: str, entity_model: str, entity_version: str) -> List[Any]:
        """Retrieve multiple items based on their IDs."""
        meta = await self._repository.get_meta(token, entity_model, entity_version)
        resp = await self._repository.find_all(meta)
        if resp and isinstance(resp, dict) and resp.get("errorMessage"):
            return []
        model_cls = self._model_registry.get(entity_model.lower())
        resp = parse_entity(model_cls, resp)
        return resp

    async def get_single_item_by_condition(self, token: str, entity_model: str, entity_version: str, condition: Any) -> List[Any]:
        """Retrieve multiple items based on their IDs."""
        resp = await self._find_by_criteria(token, entity_model, entity_version, condition)
        if resp and isinstance(resp, dict) and resp.get("errorMessage"):
            return []
        model_cls = self._model_registry.get(entity_model.lower())
        resp = parse_entity(model_cls, resp)
        return resp

    async def get_items_by_condition(self, token: str, entity_model: str, entity_version: str, condition: Any) -> List[Any]:
        """Retrieve multiple items based on their IDs."""
        resp = await self._find_by_criteria(token, entity_model, entity_version, condition.get(CHAT_REPOSITORY))
        if resp and isinstance(resp, dict) and resp.get("errorMessage"):
            return []
        model_cls = self._model_registry.get(entity_model.lower())
        resp = parse_entity(model_cls, resp)
        return resp

    async def add_item(self, token: str, entity_model: str, entity_version: str, entity: Any, meta: Any = None) -> Any:
        """Add a new item to the repository."""
        repository_meta = await self._repository.get_meta(token, entity_model, entity_version)
        if meta:
            repository_meta.update(meta)
        resp = await self._repository.save(repository_meta, entity)
        return resp

    async def update_item(self, token: str, entity_model: str, entity_version: str, technical_id: str, entity: Any, meta: Any) -> Any:
        """Update an existing item in the repository."""
        repository_meta = await self._repository.get_meta(token, entity_model, entity_version)
        meta.update(repository_meta)
        resp = await self._repository.update(meta=meta, technical_id=technical_id, entity=entity)
        return resp

    async def _find_by_criteria(self, token, entity_model, entity_version, condition):
        meta = await self._repository.get_meta(token, entity_model, entity_version)
        resp = await self._repository.find_all_by_criteria(meta, condition)
        model_cls = self._model_registry.get(entity_model.lower())
        resp = parse_entity(model_cls, resp)
        return resp

    async def delete_item(self, token: str, entity_model: str, entity_version: str, technical_id: str, meta: Any) -> Any:
        """Update an existing item in the repository."""
        repository_meta = await self._repository.get_meta(token, entity_model, entity_version)
        meta.update(repository_meta)
        resp = await self._repository.delete_by_id(meta, technical_id)
        return resp

    async def get_transitions(self, token: str, technical_id: str, meta: Any) -> Any:
        """Get next transitions"""
        resp = await self._repository.get_transitions(meta=meta, technical_id=technical_id)
        return resp