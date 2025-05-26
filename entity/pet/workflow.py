from datetime import datetime
from typing import Dict, Any, List, Optional

FUN_FACTS = [
    "Cats sleep 70% of their lives.",
    "Dogs have three eyelids.",
    "Rabbits can see behind them without turning their heads.",
    "Parrots will selflessly help each other.",
    "Guinea pigs communicate with squeaks and purrs."
]

async def process_fetch(entity: Dict[str, Any]) -> None:
    # Simulate fetching and setting status
    entity["status"] = "fetched"
    entity["fetched_at"] = datetime.utcnow().isoformat() + "Z"

async def process_enrich(entity: Dict[str, Any]) -> None:
    import random
    entity["fun_fact"] = random.choice(FUN_FACTS)
    entity["processed_timestamp"] = datetime.utcnow().isoformat() + "Z"

async def process_filter(entity: Dict[str, Any]) -> None:
    # Example placeholder for filtering logic
    entity["filtered"] = True

async def process_pet(entity: Dict[str, Any]) -> None:
    # Workflow orchestration: order of processing steps
    await process_fetch(entity)
    await process_enrich(entity)
    await process_filter(entity)