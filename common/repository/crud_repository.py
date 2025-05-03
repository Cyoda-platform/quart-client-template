from abc import abstractmethod
from enum import Enum
from typing import List, Any, Optional

from common.repository.repository import Repository


class DBKeys(Enum):
    CYODA = "CYODA"

class CrudRepository(Repository):
    """
    Abstract base class defining a repository interface for CRUD operations.
    """
    @abstractmethod
    async def get_meta(self, *args, **kwargs):
        return {}

    @abstractmethod
    async def count(self, meta) -> int:
        """
        Returns the number of entities available.
        """
        pass

    @abstractmethod
    async def delete_by_id(self, meta, id: Any) -> None:
        """
        Deletes a given entity.
        """
        pass

    @abstractmethod
    async def delete(self, meta, entity: Any) -> None:
        """
        Deletes a given entity.
        """
        pass

    @abstractmethod
    async def delete_all(self, meta) -> None:
        """
        Deletes all entities managed by the repository.
        """
        pass

    @abstractmethod
    async def delete_all_entities(self, meta, entities: List[Any]) -> None:
        """
        Deletes the given entities.
        """
        pass

    @abstractmethod
    async def delete_all_by_key(self, meta, keys: List[Any]) -> None:
        """
        Deletes all instances of the type T with the given keys.
        """
        pass

    @abstractmethod
    async def delete_by_key(self, meta, key: Any) -> None:
        """
        Deletes the entity with the given key.
        """
        pass

    @abstractmethod
    async def exists_by_key(self, meta, key: Any) -> bool:
        """
        Returns whether an entity with the given key exists.
        """
        pass

    @abstractmethod
    async def find_all(self, meta) -> List[Any]:
        """
        Returns all instances of the type.
        """
        pass

    @abstractmethod
    async def find_all_by_key(self, meta, keys: List[Any]) -> List:
        """
        Returns all instances of the type T with the given keys.
        """
        pass

    @abstractmethod
    async def find_by_key(self, meta, key: Any) -> Optional[Any]:
        """
        Retrieves an entity by its key.
        """
        pass

    @abstractmethod
    async def find_by_id(self, meta, uuid: Any) -> Optional[Any]:
        """
        Retrieves an entity by its technical id.
        """
        pass

    @abstractmethod
    async def find_all_by_criteria(self, meta, criteria: Any) -> Optional[Any]:
        """
        Retrieves an entity by its technical id.
        """
        pass

    @abstractmethod
    async def save(self, meta, entity: Any) -> Any:
        """
        Saves a given entity.
        """
        pass

    @abstractmethod
    async def save_all(self, meta, entities: List[Any]) -> List[Any]:
        """
        Saves all given entities.
        """
        pass

    @abstractmethod
    async def update(self, meta, technical_id, entity: Any) -> Any:
        """
        Saves all given entities.
        """
        pass

    @abstractmethod
    async def update_all(self, meta, entities: List[Any]) -> List[Any]:
        """
        Saves all given entities.
        """
        pass

    @abstractmethod
    async def get_transitions(self, meta, technical_id):
        """
        Gets next transitions
        """
        pass