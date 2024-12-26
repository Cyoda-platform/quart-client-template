import json
import os
from pathlib import Path

from common.ai.ai_assistant_service_impl import API_V_WORKFLOWS_
from common.app_init import ai_service
from common.config.config import ENTITY_VERSION, CHAT_ID, CYODA_AI_URL, CYODA_API_URL
from common.repository.cyoda.cyoda_repository import CyodaRepository
from common.util.utils import send_post_request, send_get_request

cyoda_repository = CyodaRepository()
entity_dir = Path(__file__).resolve().parent.parent.parent.parent / 'entity'


def init_cyoda(token):
    init_entities_schema(entity_dir=entity_dir, token=token)
    load_config_json()

def init_entities_schema(entity_dir, token):
    for json_file in entity_dir.glob('*/**/*.json'):
        # Ensure the JSON file is in an immediate subdirectory
        if json_file.parent.parent.name != entity_dir.name or json_file.parent.name != json_file.name.replace(".json",                                                                                                  ""):
            continue

        try:
            with open(json_file, 'r') as file:
                entity = file.read()
                entity_name = json_file.name.replace(".json", "")
                if not cyoda_repository._model_exists(token, entity_name, ENTITY_VERSION):
                    meta = cyoda_repository.get_meta(token, entity_name, ENTITY_VERSION)
                    cyoda_repository.save(meta=meta, entity=json.loads(entity))
                    init_trino(entity_name=entity_name, token=token)
                    init_workflow(entity_dir=json_file.parent, token=token)

                    # cyoda_repository._lock_entity_schema(token, entity_name, ENTITY_VERSION, None)
        except Exception as e:
            print(f"Error reading {json_file}: {e}")


def init_workflow(entity_dir, token):
    # Traverse the directory structure
    for root, dirs, files in os.walk(entity_dir):
        # Look for 'workflow.json' files
        if 'workflow.json' in files:
            file_path = Path(root) / 'workflow.json'
            workflow_contents = file_path.read_text()
            data = json.dumps({
                "question": f"{workflow_contents}",
                "return_object": "save",
                "chat_id": CHAT_ID,
                "class_name": "com.cyoda.tdb.model.treenode.TreeNodeEntity"
            })
            resp = send_post_request(token=token, api_url=CYODA_AI_URL, path="%s/chat" % API_V_WORKFLOWS_, data=data)
            return resp.json()



def init_trino(entity_name, token):
    trino_models_config = {}
    resp = send_get_request(token=token, api_url=CYODA_API_URL, path="treeNode/model/")
    trino_models = resp.json()
    for model in trino_models:
        if model['modelName'] == entity_name and str(model['modelVersion']) == str(ENTITY_VERSION):
            model_details = send_get_request(token=token, api_url=CYODA_API_URL,
                                             path=f"sql/schema/genTables/{model['id']}")
            data = {
                "id": None,
                "schemaName": entity_name,
                "tables": model_details.json()
            }
            resp = send_post_request(token=token, api_url=CYODA_API_URL, path="sql/schema/", data=json.dumps(data))
            chat_id = resp.json()
            ai_service.init_trino_chat(token=token, chat_id=chat_id, schema_name=entity_name)
            trino_models_config[entity_name] = chat_id
            break
    config_file_path = entity_dir / 'config.json'
    with open(config_file_path, 'w') as file:
        # Write the dictionary as JSON
        json.dump(trino_models_config, file, indent=4)

def load_config_json():
    config_file_path = entity_dir / 'config.json'
    return json.loads(config_file_path.read_text())