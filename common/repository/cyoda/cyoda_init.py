import asyncio
import json
import logging
import os
from pathlib import Path

from common.auth.cyoda_auth import CyodaAuthService
from common.config.config import ENTITY_VERSION, CHAT_ID, CYODA_AI_URL, CYODA_API_URL, IMPORT_WORKFLOWS
from common.repository.cyoda.cyoda_repository import CyodaRepository
from common.repository.cyoda.util.workflow_to_dto_converter import parse_ai_workflow_to_dto
from common.utils.utils import send_cyoda_request
from common.utils.workflow_enricher import enrich_workflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

entity_dir = Path(__file__).resolve().parent.parent.parent.parent / 'entity'

API_V_WORKFLOWS_ = "api/v1/workflows"

class CyodaInitService:
    def __init__(self, cyoda_repository: CyodaRepository, cyoda_auth_service: CyodaAuthService):
        self.cyoda_repository = cyoda_repository
        self.entity_dir = Path(__file__).resolve().parent.parent.parent.parent / 'entity'
        self.API_V_WORKFLOWS_ = "api/v1/workflows"
        self.cyoda_auth_service=cyoda_auth_service

    async def initialize_service(self):
        await self.init_cyoda(token=self.cyoda_auth_service)

    async def init_cyoda(self, token: CyodaAuthService):
        await self.init_entities_schema(entity_dir=self.entity_dir, token=token)

    async def init_entities_schema(self,entity_dir, token: CyodaAuthService):
        if IMPORT_WORKFLOWS:
            for json_file in entity_dir.glob('*/**/*.json'):
                # Ensure the JSON file is in an immediate subdirectory
                if json_file.parent.parent.name != "entity" or json_file.name != 'workflow.json':
                    continue

                try:
                    entity_name = json_file.parent.name
                    await self.init_workflow(entity_dir=json_file.parent, token=token, entity_name = entity_name)
                except Exception as e:
                    print(f"Error reading {json_file}: {e}")
                    logger.exception(e)


    async def init_workflow(self, entity_dir, token: CyodaAuthService, entity_name):
        # Traverse the directory structure
        files_set = {Path('')}
        for root, dirs, files in os.walk(entity_dir):
            # Look for 'workflow.json' files
            if 'workflow.json' in files:
                file_path = Path(root) / 'workflow.json'
                if file_path not in files_set:
                    files_set.add(file_path)
                    workflow_contents = json.loads(file_path.read_text())
                    workflow_contents = enrich_workflow(workflow_contents)
                    workflow_contents['name'] = f"{workflow_contents['name']}:ENTITY_MODEL_VAR:ENTITY_VERSION_VAR:CHAT_ID_VAR"
                    workflow_contents = json.dumps(workflow_contents)
                    workflow_contents = workflow_contents.replace("ENTITY_VERSION_VAR", ENTITY_VERSION)
                    workflow_contents = workflow_contents.replace("ENTITY_MODEL_VAR", entity_name)
                    workflow_contents = workflow_contents.replace("CHAT_ID_VAR", CHAT_ID)
                    dto = parse_ai_workflow_to_dto(input_workflow=json.loads(workflow_contents), class_name="com.cyoda.tdb.model.treenode.TreeNodeEntity")

                    response = await send_cyoda_request(cyoda_auth_service=token, method="post", base_url=CYODA_API_URL, path="platform-api/statemachine/import?needRewrite=true", data=json.dumps(dto))
                    return response
        return None



def main():
    # Initialize required services and repository
    cyoda_auth_service = CyodaAuthService()
    cyoda_repository = CyodaRepository(cyoda_auth_service=cyoda_auth_service)  # Make sure this can be instantiated or mocked appropriately

    # Create the CyodaInitService instance
    init_service = CyodaInitService(cyoda_repository, cyoda_auth_service)

    # Run the async start method using asyncio
    asyncio.run(init_service.initialize_service())

if __name__ == "__main__":
    main()

