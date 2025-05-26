import logging
from datetime import datetime
from typing import Dict, Any
import random

logger = logging.getLogger(__name__)

FUN_FACTS = [
    "Cats sleep 70% of their lives.",
    "Dogs have three eyelids.",
    "Rabbits can see behind them without turning their heads.",
    "Parrots will selflessly help each other.",
    "Guinea pigs communicate with squeaks and purrs."
]

async def process_pet(entity: Dict[str, Any]) -> None:
    # Orchestrate workflow steps without business logic
    await process_add_fun_fact(entity)
    process_set_processed_timestamp(entity)

async def process_add_fun_fact(entity: Dict[str, Any]) -> None:
    try:
        entity["fun_fact"] = random.choice(FUN_FACTS)
    except Exception as e:
        logger.exception(f"Failed to add fun_fact: {e}")
        entity["fun_fact"] = "No fun fact available."

def process_set_processed_timestamp(entity: Dict[str, Any]) -> None:
    entity["processed_timestamp"] = datetime.utcnow().isoformat() + "Z"