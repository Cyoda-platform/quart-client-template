import threading
from typing import List

from common.config.config import CYODA_API_URL
from common.repository.crud_repository import CrudRepository
from common.util.utils import *

logger = logging.getLogger('quart')


class CyodaRepository(CrudRepository):
    _instance = None
    _lock = threading.Lock()  # Lock for thread safety

    def __new__(cls):
        logger.info("initializing CyodaService")
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(CyodaRepository, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        pass

    async def get_meta(self, token, entity_model, entity_version):
        return {"token": token, "entity_model": entity_model, "entity_version": entity_version,  "update_transition": "update"}

    async def count(self, meta) -> int:
        pass

    async def delete_all(self, meta) -> None:
        pass

    async def delete_all_entities(self, meta, entities: List[Any]) -> None:
        pass

    async def delete_all_by_key(self, meta, keys: List[Any]) -> None:
        pass

    async def delete_by_key(self, meta, key: Any) -> None:
        pass

    async def exists_by_key(self, meta, key: Any) -> bool:
        pass

    async def find_all(self, meta) -> List[Any]:
        entities = await self._get_all_entities(meta)
        return entities

    async def find_all_by_key(self, meta, keys: List[Any]) -> List[Any]:
        ids = await self._get_all_by_ids(meta, keys)
        return ids

    async def find_by_key(self, meta, key: Any) -> Optional[Any]:
        res = await self._get_by_key(meta, key)
        return res

    async def find_by_id(self, meta, _uuid: Any) -> Optional[Any]:
        res = await self._get_by_id(meta, _uuid)
        return res

    async def find_all_by_criteria(self, meta, criteria: Any) -> Optional[Any]:
        try:
            resp = await self._search_entities(meta, criteria)
            if resp['page']['totalElements'] == 0:
                # resp = {'page': {'number': 0, 'size': 10, 'totalElements': 0, 'totalPages': 0}}
                return []
            # resp = {'_embedded': {'objectNodes': [{'id': 'f04bce86-89a9-11b2-aa0c-169608d9bc9e', 'tree': {'email': '4126cf85-61b6-48ec-b7bc-89fc1999d9b9@q.q', 'name': 'test', 'role': 'Start-up', 'user_id': '1703b76f-8b2f-11ef-9910-40c2ba0ac9eb'}}]}, 'page': {'number': 0, 'size': 10, 'totalElements': 1, 'totalPages': 1}}
            #entities = resp["_embedded"]["objectNodes"]
            result_entities = await self._convert_to_entities(resp)
            return result_entities
        except Exception as e:
            logger.exception(e)
            return []

    async def save(self, meta, entity: Any) -> Any:
        res = await self._save_new_entities(meta, [entity])
        return res[0]['entityIds'][0]

    async def save_all(self, meta, entities: List[Any]) -> bool:
        res = await self._save_new_entities(meta, entities)
        return res[0]['entityIds'][0]

    async def update(self, meta, _id, entity: Any) -> Any:
        meta["technical_id"] = _id
        if entity is None:
            res = await self._launch_transition(meta)
            return res
        res = await self._update_entity(meta=meta, _id=_id, entity=entity)
        return res['entityIds'][0]

    async def update_all(self, meta, entities: List[Any]) -> List[Any]:
        res = await self._update_entities(meta, entities)
        return res

    async def _search_entities(self, meta, condition):
        # Create a snapshot search
        snapshot_response = await self._create_snapshot_search(
            token=meta["token"],
            model_name=meta["entity_model"],
            model_version=meta["entity_version"],
            condition=condition
        )
        snapshot_id = snapshot_response
        if not snapshot_id:
            logger.error(f"Snapshot ID not found in response: {snapshot_response}")
            return None

        # Wait for the search to complete
        await self._wait_for_search_completion(
            token=meta["token"],
            snapshot_id=snapshot_id,
            timeout=60,  # Adjust timeout as needed
            interval=300  # Adjust interval (in milliseconds) as needed
        )

        # Retrieve search results
        search_result = await self._get_search_result(
            token=meta["token"],
            snapshot_id=snapshot_id,
            page_size=100,  # Adjust page size as needed
            page_number=1  # Starting with the first page
        )
        return search_result

    async def _get_all_by_ids(self, meta, keys) -> List[Any]:
        try:
            for key in keys:
                search_result = await self._search_entities(meta, meta["condition"])
                if search_result.get('page').get('totalElements', 0) == 0:
                    return []
                result_entities = await self._convert_to_entities(search_result)
            return result_entities


        except TimeoutError as te:
            logger.error(f"Timeout while reading key '{key}': {te}")
        except Exception as e:
            logger.error(f"Error reading key '{key}': {e}")

        return None

    async def _get_by_key(self, meta, key) -> Optional[Any]:
        try:
            search_result = await self._search_entities(meta, meta["condition"])
            # Convert search results to CacheEntity
            if search_result.get('page').get('totalElements', 0) == 0:
                return None
            result_entities = await self._convert_to_entities(search_result)
            entity = result_entities[0]
            logger.info(f"Successfully retrieved CacheEntity for key '{key}'.")
            if entity is not None:
                return entity
            return None

        except TimeoutError as te:
            logger.error(f"Timeout while reading key '{key}': {te}")
        except Exception as e:
            logger.error(f"Error reading key '{key}': {e}")

        return None


    async def _save_new_entities(self, meta, entities: List[Any]) -> bool:
        try:

            # Serialize the entity with the custom serializer
            entities_data = json.dumps(entities, default=custom_serializer)
            resp = await self._save_new_entity(
                token=meta["token"],
                model=meta["entity_model"],
                version=meta["entity_version"],
                data=entities_data
            )
            return resp
        except Exception as e:
            logger.error(f"Exception occurred while saving entity: {e}")
            raise e

    async def delete(self, meta, entity: Any) -> None:
        pass

    async def delete_by_id(self, meta, id: Any) -> None:
        pass

    @staticmethod
    async def _save_entity_schema(token, entity_name, version, data):
        path = f"entity/JSON/{entity_name}/{version}"

        try:
            response = await send_post_request(token=token, api_url=CYODA_API_URL, path=path, data=data)
            if response:
                logger.info(
                    f"Successfully saved schema for entity '{entity_name}' with version '{version}'. Response: {response}")
            else:
                logger.error(
                    f"Failed to save schema for entity '{entity_name}' with version '{version}'. Response: {response}")

            return response.get('json')

        except Exception as e:
            logger.error(
                f"An error occurred while saving schema for entity '{entity_name}' with version '{version}': {e}")
            return {'error': str(e)}

    @staticmethod
    async def _lock_entity_schema(token, entity_name, version, data):
        path = f"model/{entity_name}/{version}/lock"

        try:
            response = await send_put_request(token=token, api_url=CYODA_API_URL, path=path, data=data)

            if response:
                logger.info(
                    f"Successfully locked schema for entity '{entity_name}' with version '{version}'. Response: {response}")
            else:
                logger.error(
                    f"Failed to lock schema for entity '{entity_name}' with version '{version}'. Response: {response}")

            return response.get('json')
        except Exception as e:
            logger.error(
                f"An error occurred while locking schema for entity '{entity_name}' with version '{version}': {e}")
            return {'error': str(e)}

    @staticmethod
    async def _model_exists(token, entity_name, version) -> bool:
        export_model_path = f"model/export/SIMPLE_VIEW/{entity_name}/{version}"
        response = await send_get_request(token, CYODA_API_URL, export_model_path)

        if response['status'] == 200:
            return True
        else:
            return False

    @staticmethod
    async def _get_model(token, entity_name, version):
        export_model_url = f"model/export/SIMPLE_VIEW/{entity_name}/{version}"

        response = await send_get_request(token, CYODA_API_URL, export_model_url)

        if response:
            return response.get('json')
        else:
            raise Exception(f"Getting the model failed: {response}")

    @staticmethod
    async def _save_new_entity(token, model, version, data):
        path = f"entity/JSON/{model}/{version}"
        logger.info(f"Saving new entity to path: {path}")

        try:
            response = await send_post_request(token=token, api_url=CYODA_API_URL, path=path, data=data)

            if response:
                logger.info(f"Successfully saved new entity. Response: {response}")
                return response.get('json')
            else:
                logger.error(f"Failed to save new entity. Response: {response}")
                raise Exception(f"Failed to save new entity. Response: {response}")

        except Exception as e:
            logger.error(f"An error occurred while saving new entity '{model}' with version '{version}': {e}")
            raise e

    @staticmethod
    async def _delete_all_entities(token, model_name, model_version):
        delete_entities_url = f"entity/{model_name}/{model_version}"

        response = await send_delete_request(token, CYODA_API_URL, delete_entities_url)

        if response:
            return response.get('json')
        else:
            raise Exception(f"Deletion failed: {response}")

    @staticmethod
    async def _create_snapshot_search(token, model_name, model_version, condition):
        search_url = f"search/snapshot/{model_name}/{model_version}"
        logger.info(condition)
        response = await send_post_request(token, CYODA_API_URL, search_url, data=json.dumps(condition))
        if response:
            return response.get('json')
        else:
            raise Exception(f"Snapshot search trigger failed: {response}")

    @staticmethod
    async def _get_snapshot_status(token, snapshot_id):
        status_url = f"search/snapshot/{snapshot_id}/status"

        response = await send_get_request(token, CYODA_API_URL, status_url)
        if response:
            return response.get('json')
        else:
            raise Exception(f"Snapshot search trigger failed: {response}")

    async def _wait_for_search_completion(self, token, snapshot_id, timeout=5, interval=10):
        start_time = now()  # Record the start time

        while True:
            status_response = await self._get_snapshot_status(token, snapshot_id)
            status = status_response.get("snapshotStatus")

            # Check if the status is SUCCESSFUL or FAILED
            if status == "SUCCESSFUL":
                return status_response
            elif status != "RUNNING":
                raise Exception(f"Snapshot search failed: {json.dumps(status_response, indent=4)}")

            elapsed_time = now() - start_time

            if elapsed_time > timeout:
                raise TimeoutError(f"Timeout exceeded after {timeout} seconds")

            time.sleep(interval / 1000)  # Wait for the given interval (msec) before checking again

    @staticmethod
    async def _get_search_result(token, snapshot_id, page_size, page_number):
        result_url = f"search/snapshot/{snapshot_id}"

        params = {
            'pageSize': f"{page_size}",
            'pageNumber': f"{page_number}"
        }

        response = await send_get_request(token=token, api_url=CYODA_API_URL, path=result_url)

        if response:
            return response.get('json')
        else:
            raise Exception(f"Get search result failed: {response}")

    @staticmethod
    async def _update_entities(meta, entities: List[Any]) -> List[Any]:
        path = "entity/JSON"
        payload = []
        for entity in entities:
            payload_json = json.dumps(entity, default=custom_serializer)

            payload.append({
                "id": meta.get("technical_id"),
                "transition": meta.get("update_transition"),
                "payload": payload_json
            })
            data = json.dumps(payload)
            response = await send_put_request(meta["token"], CYODA_API_URL, path, data=data)
            if response:
                return entities
            else:
                raise Exception(f"Get search result failed: {response}")

        return entities

    @staticmethod
    async def _update_entity(meta, _id, entity: Any) -> List[Any]:
        path = "entity/JSON"

        # entities_data = {
        #     key: value for key, value in entity.to_dict().items()
        #     if value is not None and key != "technical_id"
        # }
        payload_json = json.dumps(entity, default=custom_serializer)
        response = await send_put_request(meta["token"], CYODA_API_URL,
                                          f"{path}/{_id}/{meta["update_transition"]}",
                                          data=payload_json)
        if response:
            return response.get('json')
        else:
            raise Exception(f"Get search result failed: {response}")

    @staticmethod
    async def _convert_to_entities(data):
        # Check if totalElements is zero
        if data.get("page", {}).get("totalElements", 0) == 0:
            return None

        # Extract entities from _embedded.objectNodes
        entities = []
        object_nodes = data.get("_embedded", {}).get("objectNodes", [])

        for node in object_nodes:
            # Extract the tree object
            tree = node.get("tree")
            tree["technical_id"] = node.get("id")
            if tree:
                entities.append(tree)

        return entities

    async def _get_by_id(self, meta, _uuid):
        path = f"entity/{_uuid}"
        response = await send_get_request(meta["token"], CYODA_API_URL, path=path)
        logger.info(response)
        return response.get('json').get('tree')

    async def _get_all_entities(self, meta):
        path = f"entity/{meta["entity_model"]}/{meta["entity_version"]}"
        response = await send_get_request(meta["token"], CYODA_API_URL, path=path)
        logger.info(response)
        return response.get('json')

    async def _launch_transition(self, meta):
        path = f"/platform-api/entity/transition?entityId={meta["technical_id"]}&entityClass=com.cyoda.tdb.model.treenode.TreeNodeEntity&transitionName={meta["update_transition"]}"
        response = await send_put_request(meta["token"], CYODA_API_URL, path)
        return response.get('json')
