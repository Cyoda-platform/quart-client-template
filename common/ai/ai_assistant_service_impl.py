import json
import logging

from common.ai.ai_assistant_service import IAiAssistantService
from common.config.config import CYODA_AI_URL, CYODA_AI_API, WORKFLOW_AI_API, CONNECTION_AI_API, RANDOM_AI_API, MOCK_AI, \
    TRINO_AI_API
from common.util.utils import parse_json, validate_result, send_post_request, ValidationErrorException

API_V_CONNECTIONS_ = "api/v1/connections"
API_V_CYODA_ = "api/v1/cyoda"
API_V_WORKFLOWS_ = "api/v1/workflows"
API_V_RANDOM_ = "api/v1/random"
API_V_TRINO_ = "api/v1/trino"

logger = logging.getLogger(__name__)


class AiAssistantService(IAiAssistantService):
    def __init__(self):
        pass

    async def init_chat(self, token, chat_id):
        if MOCK_AI=="true":
            return {"success": True}
        data = json.dumps({"chat_id": f"{chat_id}"})
        endpoints = [API_V_CYODA_, API_V_WORKFLOWS_, API_V_RANDOM_]
        for endpoint in endpoints:
            await send_post_request(token, CYODA_AI_URL, "%s/initial" % endpoint, data)
        return {"success": True}

    async def init_workflow_chat(self, token, chat_id):
        data = json.dumps({"chat_id": f"{chat_id}"})
        resp = await send_post_request(token, CYODA_AI_URL, "%s/initial" % API_V_WORKFLOWS_, data)
        return resp.get('json').get('message')

    async def init_connections_chat(self, token, chat_id):
        data = json.dumps({"chat_id": f"{chat_id}"})
        resp = await send_post_request(token, CYODA_AI_URL, "%s/initial" % API_V_CONNECTIONS_, data)
        return resp.get('json').get('message')

    async def init_random_chat(self, token, chat_id):
        data = json.dumps({"chat_id": f"{chat_id}"})
        resp = await send_post_request(token, CYODA_AI_URL, "%s/initial" % API_V_RANDOM_, data)
        return resp.get('json').get('message')

    async def init_cyoda_chat(self, token, chat_id):
        data = json.dumps({"chat_id": f"{chat_id}"})
        resp = await send_post_request(token, CYODA_AI_URL, "%s/initial" % API_V_CYODA_, data)
        return resp.get('json').get('message')

    async def init_trino_chat(self, token, chat_id, schema_name):
        data = json.dumps({"chat_id": f"{chat_id}", "schema_name": f"{schema_name}"})
        resp = await send_post_request(token, CYODA_AI_URL, "%s/initial" % API_V_TRINO_, data)
        return resp.get('json')

    async def ai_chat(self, token, chat_id, ai_endpoint, ai_question):
        if ai_question and len(str(ai_question).encode('utf-8')) > 1 * 1024 * 1024:
            return {"error": "Answer size exceeds 1MB limit"}
        if MOCK_AI=="true":
            return {"entity": "some random text"}
        if ai_endpoint == CYODA_AI_API:
            resp = await self.chat_cyoda(token=token, chat_id=chat_id, ai_question=ai_question)
            return resp
        if ai_endpoint == WORKFLOW_AI_API:
            resp = await self.chat_workflow(token=token, chat_id=chat_id, ai_question=ai_question)
            return resp
        if ai_endpoint == CONNECTION_AI_API:
            resp = await self.chat_connection(token=token, chat_id=chat_id, ai_question=ai_question)
            return resp
        if ai_endpoint == RANDOM_AI_API:
            resp = await self.chat_random(token=token, chat_id=chat_id, ai_question=ai_question)
            return resp
        if ai_endpoint == TRINO_AI_API:
            resp = await self.chat_trino(token=token, chat_id=chat_id, ai_question=ai_question)
            return resp

    async def chat_cyoda(self, token, chat_id, ai_question):
        if ai_question and len(str(ai_question).encode('utf-8')) > 1 * 1024 * 1024:
            return {"error": "Answer size exceeds 1MB limit"}
        data = json.dumps({"chat_id": f"{chat_id}", "question": f"{ai_question}"})
        resp = await send_post_request(token, CYODA_AI_URL, "%s/chat" % API_V_CYODA_, data)
        return resp.get('json').get('message')

    async def chat_workflow(self, token, chat_id, ai_question):
        if ai_question and len(str(ai_question).encode('utf-8')) > 1 * 1024 * 1024:
            return {"error": "Answer size exceeds 1MB limit"}
        data = json.dumps({
            "question": f"{ai_question}",
            "return_object": "workflow",
            "chat_id": f"{chat_id}",
            "class_name": "com.cyoda.tdb.model.treenode.TreeNodeEntity"
        })
        resp = await send_post_request(token, CYODA_AI_URL, "%s/chat" % API_V_WORKFLOWS_, data)
        return resp.get('json').get('message')

    async def export_workflow_to_cyoda_ai(self, token, chat_id, data):
        try:
            data = json.dumps({
                "name": data["name"],
                "chat_id": chat_id,
                "class_name": data["class_name"],
                "transitions": data["transitions"]
            })
            resp = await send_post_request(token, CYODA_AI_URL, "%s/generate-workflow" % API_V_WORKFLOWS_, data)
            return resp.get('json').get('message')
        except Exception as e:
            logger.error(f"Failed to export workflow: {e}")

    async def validate_and_parse_json(self, token:str, chat_id: str, data: str, schema: str, ai_endpoint:str, max_retries: int):
        try:
            parsed_data = parse_json(data)
        except Exception as e:
            logger.error(f"Failed to parse JSON: {e}")
            raise ValueError("Invalid JSON entity provided.") from e

        attempt = 0
        while attempt <= max_retries:
            try:
                parsed_data = await validate_result(parsed_data, '', schema)
                logger.info(f"JSON validation successful on attempt {attempt + 1}.")
                return parsed_data
            except ValidationErrorException as e:
                logger.warning(
                    f"JSON validation failed on attempt {attempt + 1} with error: {e.message}"
                )
                if attempt < max_retries:
                    question = (
                        f"Retry the last step. JSON validation failed with error: {e.message}. "
                        f"using this json schema: {json.dumps(schema)}. "
                        f"Return only the DTO JSON."
                    )
                    retry_result = await self.ai_chat(token=token, chat_id=chat_id, ai_endpoint=ai_endpoint, ai_question=question)
                    parsed_data = parse_json(retry_result)
            finally:
                attempt += 1
        logger.error(f"Maximum retry attempts reached. Validation failed. Attempt: {attempt}")
        raise ValueError("JSON validation failed after retries.")

    async def chat_connection(self, token, chat_id, ai_question):
        if ai_question and len(str(ai_question).encode('utf-8')) > 1 * 1024 * 1024:
            return {"error": "Answer size exceeds 1MB limit"}
        data = json.dumps({
            "question": f"{ai_question}",
            "return_object": "import-connections",
            "chat_id": f"{chat_id}"
        })
        resp = await send_post_request(token, CYODA_AI_URL, "%s/chat" % API_V_CONNECTIONS_, data)
        return resp.get('json').get('message')

    async def chat_random(self, token, chat_id, ai_question):
        if ai_question and len(str(ai_question).encode('utf-8')) > 1 * 1024 * 1024:
            return {"error": "Answer size exceeds 1MB limit"}
        data = json.dumps({
            "question": f"{ai_question}",
            "return_object": "random",
            "chat_id": f"{chat_id}"
        })
        resp = await send_post_request(token, CYODA_AI_URL, "%s/chat" % API_V_RANDOM_, data)
        return resp.get('json').get('message')

    async def chat_trino(self, token, chat_id, ai_question):
        data = json.dumps({
            "question": f"{ai_question}",
            "return_object": "random",
            "chat_id": f"{chat_id}"})
        resp = await send_post_request(token, CYODA_AI_URL, "%s/chat" % API_V_TRINO_, data)
        return resp.get('json').get('message')