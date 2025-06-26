from datetime import datetime
from typing import Dict, Any
import logging
import httpx

logger = logging.getLogger(__name__)

OPENAI_API_KEY = "your_openai_api_key_here"
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

async def process_event_detect(entity: Dict[str, Any]) -> None:
    entity["event_id"] = entity.get("event_id") or f"{entity.get('cat_id')}-{datetime.utcnow().timestamp()}"
    entity["status"] = "processing"
    entity["requestedAt"] = datetime.utcnow().isoformat()

    try:
        if entity.get("input_type") == "text":
            await analyze_text_for_food_request(entity)
        else:
            logger.info(f"Input type '{entity.get('input_type')}' is not supported yet for event detection.")
            entity["event_detected"] = False
        
        await create_notification(entity)
        
        entity["processed_at"] = datetime.utcnow().isoformat()
        entity["status"] = "completed"
        entity["result"] = {
            "event_detected": entity.get("event_detected"),
            "event_type": entity.get("event_type"),
            "message": entity.get("message")
        }
    except Exception as e:
        logger.exception(f"Error in event_detect workflow: {e}")
        entity["status"] = "failed"
        entity["result"] = {
            "event_detected": False,
            "event_type": None,
            "message": None,
            "error": str(e)
        }

async def input_type_is_text(entity: Dict[str, Any]) -> bool:
    return entity.get("input_type") == "text"

async def input_type_is_not_text(entity: Dict[str, Any]) -> bool:
    return entity.get("input_type") != "text"

async def analyze_text_for_food_request(entity: Dict[str, Any]) -> None:
    text = entity.get("input_data", "")
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an assistant that detects if a cat is dramatically requesting food. "
                    "Return 'yes' if the input text shows a dramatic food request, otherwise 'no'."
                )
            },
            {
                "role": "user",
                "content": text
            }
        ],
        "max_tokens": 5,
        "temperature": 0
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(OPENAI_API_URL, json=data, headers=headers, timeout=10)
            response.raise_for_status()
            result = response.json()
            answer = result["choices"][0]["message"]["content"].strip().lower()
            entity["event_detected"] = (answer == "yes")
        except Exception as e:
            logger.exception(f"Error calling OpenAI API: {e}")
            entity["event_detected"] = False

async def create_notification(entity: Dict[str, Any]) -> None:
    if entity.get("event_detected"):
        entity["event_type"] = "food_request"
        entity["message"] = "Emergency! A cat demands snacks"
        entity["notification"] = {
            "cat_id": entity.get("cat_id"),
            "timestamp": datetime.utcnow().isoformat(),
            "message": entity["message"]
        }
        logger.info(f"Notification created for cat_id={entity.get('cat_id')}: {entity['message']}")
    else:
        entity["event_type"] = None
        entity["message"] = None
        entity["notification"] = None

async def mark_event_not_detected(entity: Dict[str, Any]) -> None:
    entity["event_detected"] = False

async def finalize_entity(entity: Dict[str, Any]) -> None:
    entity["workflowProcessed"] = True
    entity["finalizedAt"] = datetime.utcnow().isoformat()