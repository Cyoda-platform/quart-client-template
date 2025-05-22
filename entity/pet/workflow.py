from typing import Dict
import logging

logger = logging.getLogger(__name__)

async def process_enrich_description(entity: Dict):
    if not entity.get("description"):
        name = entity.get("name", "Unnamed")
        pet_type = entity.get("category", {}).get("name", "pet").lower() if "category" in entity else entity.get("type", "pet").lower()
        status = entity.get("status", "unknown")
        description = f"{name} is a lovely {pet_type} currently {status}."
        if pet_type == "cat":
            description += " Loves naps and chasing yarn balls! 😸"
        elif pet_type == "dog":
            description += " Always ready for a walk and lots of belly rubs! 🐶"
        else:
            description += " A wonderful companion waiting for you!"
        entity["description"] = description

async def process_apply_message_template(entity: Dict):
    if "message_template" in entity and entity["message_template"]:
        try:
            entity["description"] = entity["message_template"].format(name=entity.get("name", ""))
        except Exception:
            logger.warning(f"Failed to format message_template for pet id {entity.get('id')}")
        entity["message_template"] = ""  # clear after processing to prevent re-processing

async def process_pet(entity: Dict) -> Dict:
    # workflow orchestration only
    await process_enrich_description(entity)
    await process_apply_message_template(entity)
    return entity