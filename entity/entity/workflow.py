import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TRINO_MOCK_API = "https://httpbin.org/delay/1"  # simulates 1 second delay

default_workflow = {
    "states": ["Created", "HelloSent", "Completed"],
    "transitions": [
        {"from": "Created", "to": "HelloSent", "event": "StartGreeting"},
        {"from": "HelloSent", "to": "Completed", "event": "Complete"},
    ],
}

workflows = {}  # Assume workflows defined elsewhere or default used

def get_next_state(current_state: str, event: str, workflow_def: dict) -> str:
    for t in workflow_def.get("transitions", []):
        if t["from"] == current_state and t["event"] == event:
            return t["to"]
    return current_state

async def process_trino_call(entity: dict):
    # Simulate external API call (Trino query)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            trino_response = await client.get(TRINO_MOCK_API)
            trino_response.raise_for_status()
            # TODO: use trino_response.json() if needed
    except Exception as e:
        entity_id = entity.get("entityId", "unknown")
        logger.warning(f"Failed to fetch Trino mock data for entity {entity_id}: {e}")

async def process_message_update(entity: dict):
    next_state = entity.get("currentState")
    params = entity.get("_pendingParameters", {})
    message = ""
    if next_state == "HelloSent":
        lang = str(params.get("language", "en")).lower()
        greetings = {
            "en": "Hello World",
            "es": "Hola Mundo",
            "fr": "Bonjour le monde",
            "de": "Hallo Welt",
            "it": "Ciao Mondo",
        }
        message = greetings.get(lang, greetings["en"])
    elif next_state:
        message = f"Transitioned to state '{next_state}'."
    else:
        message = ""
    entity["message"] = message

async def process_history_update(entity: dict):
    next_state = entity.get("currentState")
    entity.setdefault("history", [])
    if not entity["history"] or entity["history"][-1].get("state") != next_state:
        entity["history"].append(
            {"state": next_state, "timestamp": datetime.utcnow().isoformat()}
        )