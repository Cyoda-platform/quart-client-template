import json
import threading
import time
from typing import List, Any, Optional

import logging

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

    def get_meta(self, token, entity_model, entity_version):
        return {"token": token, "entity_model": entity_model, "entity_version": entity_version}

    def count(self, meta) -> int:
        pass

    def delete_all(self, meta) -> None:
        pass

    def delete_all_entities(self, meta, entities: List[Any]) -> None:
        pass

    def delete_all_by_key(self, meta, keys: List[Any]) -> None:
        pass

    def delete_by_key(self, meta, key: Any) -> None:
        pass

    def exists_by_key(self, meta, key: Any) -> bool:
        pass

    def find_all(self, meta) -> List[Any]:
        return self._get_all_entities(meta)

    def find_all_by_key(self, meta, keys: List[Any]) -> List[Any]:
        return self._get_all_by_ids(meta, keys)

    def find_by_key(self, meta, key: Any) -> Optional[Any]:
        return self._get_by_key(meta, key)

    def find_by_id(self, meta, uuid: Any) -> Optional[Any]:
        return self._get_by_id(meta, uuid)

    def find_all_by_criteria(self, meta, criteria: Any) -> Optional[Any]:
        resp = self._search_entities(meta, criteria)
        if (resp['page']['totalElements'] == 0):
            #resp = {'page': {'number': 0, 'size': 10, 'totalElements': 0, 'totalPages': 0}}
            return []
        #resp = {'_embedded': {'objectNodes': [{'id': 'f04bce86-89a9-11b2-aa0c-169608d9bc9e', 'tree': {'email': '4126cf85-61b6-48ec-b7bc-89fc1999d9b9@q.q', 'name': 'test', 'role': 'Start-up', 'user_id': '1703b76f-8b2f-11ef-9910-40c2ba0ac9eb'}}]}, 'page': {'number': 0, 'size': 10, 'totalElements': 1, 'totalPages': 1}}
        resp = resp["_embedded"]["objectNodes"]
        return resp

    def save(self, meta, entity: Any) -> Any:
        return self._save_new_entities(meta, [entity])

    def save_all(self, meta, entities: List[Any]) -> bool:
        return self._save_new_entities(meta, entities)

    def update(self, meta, id, entity: Any) -> Any:
        meta["technical_id"] = id
        if entity is None:
            return self._launch_transition(meta)
        return self._update_entities(meta, [entity])

    def update_all(self, meta, entities: List[Any]) -> List[Any]:
        return self._update_entities(meta, entities)

    def _search_entities(self, meta, condition):
        # Create a snapshot search
        snapshot_response = self._create_snapshot_search(
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
        status_response = self._wait_for_search_completion(
            token=meta["token"],
            snapshot_id=snapshot_id,
            timeout=60,  # Adjust timeout as needed
            interval=300  # Adjust interval (in milliseconds) as needed
        )

        # Retrieve search results
        search_result = self._get_search_result(
            token=meta["token"],
            snapshot_id=snapshot_id,
            page_size=100,  # Adjust page size as needed
            page_number=1  # Starting with the first page
        )
        return search_result

    def _get_all_by_ids(self, meta, keys) -> List[Any]:
        try:
            entities = []
            for key in keys:
                search_result = self._search_entities(meta, meta["condition"])
                if search_result.get('page').get('totalElements', 0) == 0:
                    return []
                result_entities = self._convert_to_entities(search_result)
            return result_entities


        except TimeoutError as te:
            logger.error(f"Timeout while reading key '{key}': {te}")
        except Exception as e:
            logger.error(f"Error reading key '{key}': {e}")

        return None

    def _get_by_key(self, meta, key) -> Optional[Any]:
        try:
            search_result = self._search_entities(meta, meta["condition"])
            # Convert search results to CacheEntity
            if search_result.get('page').get('totalElements', 0) == 0:
                return None
            result_entities = self._convert_to_entities(search_result)
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

    def _save_new_entities(self, meta, entities: List[Any]) -> bool:
        try:
            entities_data = json.dumps(entities)
            resp = self._save_new_entity(
                token=meta["token"],
                model=meta["entity_model"],
                version=meta["entity_version"],
                data=entities_data
            )
            return resp
        except Exception as e:
            logger.error(f"Exception occurred while saving entity: {e}")
            raise e

    def delete(self, meta, entity: Any) -> None:
        pass

    def delete_by_id(self, meta, id: Any) -> None:
        pass

    @staticmethod
    def _save_entity_schema(token, entity_name, version, data):
        path = f"entity/JSON/TREE/{entity_name}/{version}"

        try:
            response = send_post_request(token=token, api_url=CYODA_API_URL, path=path, data=data)
            if response.status_code == 200:
                logger.info(
                    f"Successfully saved schema for entity '{entity_name}' with version '{version}'. Response: {response}")
            else:
                logger.error(
                    f"Failed to save schema for entity '{entity_name}' with version '{version}'. Response: {response}")

            return response

        except Exception as e:
            logger.error(
                f"An error occurred while saving schema for entity '{entity_name}' with version '{version}': {e}")
            return {'error': str(e)}

    @staticmethod
    def _lock_entity_schema(token, entity_name, version, data):
        path = f"treeNode/model/{entity_name}/{version}/lock"

        try:
            response = send_put_request(token=token, api_url=CYODA_API_URL, path=path, data=data)

            if response.status_code == 200:
                logger.info(
                    f"Successfully locked schema for entity '{entity_name}' with version '{version}'. Response: {response}")
            else:
                logger.error(
                    f"Failed to lock schema for entity '{entity_name}' with version '{version}'. Response: {response}")

            return response
        except Exception as e:
            logger.error(
                f"An error occurred while locking schema for entity '{entity_name}' with version '{version}': {e}")
            return {'error': str(e)}

    @staticmethod
    def _model_exists(token, entity_name, version) -> bool:
        export_model_path = f"treeNode/model/export/SIMPLE_VIEW/{entity_name}/{version}"
        response = send_get_request(token, CYODA_API_URL, export_model_path)

        if response.status_code == 200:
            return True
        elif response.status_code == 404:
            return False
        else:
            raise Exception(f"Get: {response.status_code} {response.text}")

    @staticmethod
    def _get_model(token, entity_name, version):
        export_model_url = f"treeNode/model/export/SIMPLE_VIEW/{entity_name}/{version}"

        response = send_get_request(token, CYODA_API_URL, export_model_url)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Getting the model failed: {response.status_code} {response.text}")

    @staticmethod
    def _save_new_entity(token, model, version, data):
        path = f"entity/JSON/TREE/{model}/{version}"
        logger.info(f"Saving new entity to path: {path}")

        try:
            response = send_post_request(token=token, api_url=CYODA_API_URL, path=path, data=data)

            if response.status_code == 200:
                logger.info(f"Successfully saved new entity. Response: {response}")
                return response.json()
            else:
                logger.error(f"Failed to save new entity. Response: {response}")
                raise Exception(f"Failed to save new entity. Response: {response}")

        except Exception as e:
            logger.error(f"An error occurred while saving new entity '{model}' with version '{version}': {e}")
            raise e

    @staticmethod
    def _delete_all_entities(token, model_name, model_version):
        delete_entities_url = f"entity/TREE/{model_name}/{model_version}"

        response = send_delete_request(token, CYODA_API_URL, delete_entities_url)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Deletion failed: {response.status_code} {response.text}")

    @staticmethod
    def _create_snapshot_search(token, model_name, model_version, condition):
        search_url = f"treeNode/search/snapshot/{model_name}/{model_version}"
        logger.info(condition)
        response = send_post_request(token, CYODA_API_URL, search_url, data=json.dumps(condition))
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Snapshot search trigger failed: {response.status_code} {response.text}")

    @staticmethod
    def _get_snapshot_status(token, snapshot_id):
        status_url = f"treeNode/search/snapshot/{snapshot_id}/status"

        response = send_get_request(token, CYODA_API_URL, status_url)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Snapshot search trigger failed: {response.status_code} {response.text}")

    def _wait_for_search_completion(self, token, snapshot_id, timeout=5, interval=10):
        start_time = now()  # Record the start time

        while True:
            status_response = self._get_snapshot_status(token, snapshot_id)
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
    def _get_search_result(token, snapshot_id, page_size, page_number):
        result_url = f"treeNode/search/snapshot/{snapshot_id}"

        params = {
            'pageSize': f"{page_size}",
            'pageNumber': f"{page_number}"
        }

        response = send_get_request(token=token, api_url=CYODA_API_URL, path=result_url)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Get search result failed: {response.status_code} {response.text}")

    @staticmethod
    def _update_entities(meta, entities: List[Any]) -> List[Any]:
        path = "entity/JSON/TREE"
        payload = []
        for entity in entities:
            entities_data = {
                key: value for key, value in entity.to_dict().items()
                if value is not None and key != "technical_id"
            }

            payload_json = json.dumps(entities_data)

            payload.append({
                "id": meta.get("technical_id"),
                "transition": meta.get("update_transition"),
                "payload": payload_json
            })
            data = json.dumps(payload)
            response = send_put_request(meta["token"], CYODA_API_URL, path, data=data)
            if response.status_code == 200:
                return entities
            else:
                raise Exception(f"Get search result failed: {response.status_code} {response.text}")

        return entities

    @staticmethod
    def _update_entity(meta, entities: List[Any]) -> List[Any]:
        path = "entity/JSON/TREE"
        for entity in entities:
            entities_data = {
                key: value for key, value in entity.to_dict().items()
                if value is not None and key != "technical_id"
            }
            payload_json = json.dumps(entities_data)
            response = send_put_request(meta["token"], CYODA_API_URL,
                                        f"{path}/{entity.technical_id}/{meta["update_transition"]}", data=payload_json)
            if response.status_code == 200:
                return entities
            else:
                raise Exception(f"Get search result failed: {response.status_code} {response.text}")

        return entities

    @staticmethod
    def _convert_to_entities(data):
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

    def _get_by_id(self, meta, uuid):
        path = f"entity/TREE/{uuid}"
        response = send_get_request(meta["token"], CYODA_API_URL, path=path)
        logger.info(response.json())
        return response.json()

    def _get_all_entities(self, meta):
        path = f"entity/TREE/{meta["entity_model"]}/{meta["entity_version"]}"
        response = send_get_request(meta["token"], CYODA_API_URL, path=path)
        logger.info(response.json())
        return response.json()

    def _launch_transition(self, meta):
        path = f"/platform-api/entity/transition?entityId={meta["technical_id"]}&entityClass=com.cyoda.tdb.model.treenode.TreeNodeEntity&transitionName={meta["update_transition"]}"
        response = send_put_request(meta["token"], CYODA_API_URL, path)
        return response.json()
