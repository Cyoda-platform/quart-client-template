import asyncio
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def process_set_default_status(entity: Dict[str, Any]) -> None:
    if not entity.get('status'):
        entity['status'] = 'available'

async def process_normalize_type(entity: Dict[str, Any]) -> None:
    pet_type = entity.get('type')
    if pet_type:
        pet_type = pet_type.lower()
        entity['type'] = pet_type
    else:
        entity['type'] = None

async def process_add_fun_facts_and_toys(entity: Dict[str, Any]) -> None:
    pet_type = entity.get('type')
    fun_facts = {
        "dog": "Dogs have about 1,700 taste buds!",
        "cat": "Cats have whiskers that help them sense their surroundings.",
        "bird": "Some birds can mimic human speech."
    }
    toys = {
        "dog": ["ball", "frisbee"],
        "cat": ["feather wand", "laser pointer"],
        "bird": ["mirror", "bell"]
    }
    entity['funFact'] = fun_facts.get(pet_type, "Pets bring joy to our lives!")
    entity['recommendedToys'] = toys.get(pet_type, ["toy"])

async def process_pet(entity: Dict[str, Any]) -> None:
    # Workflow orchestration only
    await process_set_default_status(entity)
    await process_normalize_type(entity)
    await process_add_fun_facts_and_toys(entity)
    logger.info(f"Workflow processed pet entity: {entity}")