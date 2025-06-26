from datetime import datetime
import logging
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

OPENAI_API_KEY = "your_openai_api_key_here"  # TODO: replace with env var
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

async def analyze_text_for_food_request(entity: dict):
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
                "content": entity['input_data']
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
            entity['event_detected'] = (answer == "yes")
        except Exception as e:
            logger.exception(f"Error calling OpenAI API: {e}")
            entity['event_detected'] = False

async def process_notification(entity: dict):
    if entity.get('event_detected'):
        entity['event_type'] = "food_request"
        entity['message'] = "Emergency! A cat demands snacks"
        timestamp = datetime.utcnow().isoformat()
        if 'notifications' not in entity:
            entity['notifications'] = []
        entity['notifications'].append({
            "timestamp": timestamp,
            "message": entity['message']
        })
        logger.info(f"Notification processed for cat_id={entity.get('cat_id')}: {entity['message']}")
    else:
        entity['event_type'] = None
        entity['message'] = None

async def None(entity: dict):
    # Workflow orchestration only
    entity['status'] = "processing"
    if entity.get('input_type') == "text":
        await analyze_text_for_food_request(entity)
    else:
        logger.info(f"Unsupported input_type: {entity.get('input_type')}")
        entity['event_detected'] = False
    await process_notification(entity)
    entity['status'] = "completed"