from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)

@dataclass
class FetchRequest:
    status: Optional[str]
    type: Optional[str]
    limit: int

@dataclass
class CustomizeMessage:
    pet_id: str
    message_template: str

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"


async def fetch_pets_from_petstore(status: Optional[str], pet_type: Optional[str], limit: int) -> List[Dict]:
    url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
    params = {"status": status or "available,pending,sold"}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            pets = response.json()
    except Exception as e:
        logger.exception("Failed to fetch pets from Petstore API")
        raise
    if pet_type:
        pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == pet_type.lower()]
    return pets[:limit]

def enrich_pet_description(pet: Dict) -> str:
    name = pet.get("name", "Unnamed")
    pet_type = pet.get("category", {}).get("name", "pet").lower() if "category" in pet else pet.get("type", "pet").lower()
    status = pet.get("status", "unknown")
    description = f"{name} is a lovely {pet_type} currently {status}."
    if pet_type == "cat":
        description += " Loves naps and chasing yarn balls! 638"
    elif pet_type == "dog":
        description += " Always ready for a walk and lots of belly rubs! 436"
    else:
        description += " A wonderful companion waiting for you!"
    return description


# Workflow for pet entity - enrich description and apply message template
async def process_pet(entity: Dict) -> Dict:
    if not entity.get("description"):
        entity["description"] = enrich_pet_description(entity)
    if "message_template" in entity and entity["message_template"]:
        try:
            entity["description"] = entity["message_template"].format(name=entity.get("name", ""))
        except Exception:
            logger.warning(f"Failed to format message_template for pet id {entity.get('id')}")
        entity["message_template"] = ""  # clear after processing to prevent re-processing
    return entity


# Workflow for pet_fetch_job entity - fetches pets from API, deletes old pets, adds new pets
async def process_pet_fetch_job(entity: Dict) -> Dict:
    entity["status"] = "processing"
    entity["requestedAt"] = datetime.utcnow().isoformat()
    try:
        pets = await fetch_pets_from_petstore(
            entity.get("status_filter"),
            entity.get("type_filter"),
            entity.get("limit_filter", 10),
        )
        # Delete existing pets safely
        existing_pets = []
        try:
            existing_pets = await entity_service.get_items(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
            )
        except Exception as e:
            logger.warning(f"Failed to retrieve existing pets for deletion: {e}")

        for existing_pet in existing_pets:
            pet_id = existing_pet.get("id")
            if not pet_id:
                continue
            try:
                await entity_service.delete_item(
                    token=cyoda_auth_service,
                    entity_model="pet",
                    entity_version=ENTITY_VERSION,
                    technical_id=pet_id,
                    meta={},
                )
            except Exception as e:
                logger.warning(f"Failed to delete existing pet id {pet_id}: {e}")

        # Add new pets, process_pet workflow enriches description
        for pet in pets:
            pet_entity = {
                "id": str(pet.get("id")),
                "name": pet.get("name"),
                "type": pet.get("category", {}).get("name", "").lower() if "category" in pet else pet.get("type", "").lower(),
                "status": pet.get("status"),
            }
            try:
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model="pet",
                    entity_version=ENTITY_VERSION,
                    entity=pet_entity,
                )
            except Exception as e:
                logger.warning(f"Failed to add pet id {pet_entity.get('id')}: {e}")

        entity["status"] = "completed"
        entity["completedAt"] = datetime.utcnow().isoformat()
        entity["count"] = len(pets)
    except Exception as e:
        entity["status"] = "failed"
        entity["error"] = str(e)
        logger.exception("Failed to process pet fetch job")
    return entity


@app.route("/pets/fetch", methods=["POST"])
@validate_request(FetchRequest)
async def fetch_pets(data: FetchRequest):
    job_entity = {
        "status_filter": data.status,
        "type_filter": data.type,
        "limit_filter": data.limit,
        "status": "pending",
        "requestedAt": datetime.utcnow().isoformat(),
    }
    try:
        job_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet_fetch_job",
            entity_version=ENTITY_VERSION,
            entity=job_entity
        )
    except Exception as e:
        logger.exception("Failed to create pet fetch job")
        return jsonify({"error": "Failed to create pet fetch job"}), 500
    return jsonify({"message": "Pets data fetch job created", "job_id": job_id}), 202


@app.route("/pets", methods=["GET"])
async def get_pets():
    try:
        pets = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        logger.exception("Failed to get pets from entity_service")
        return jsonify({"error": "Failed to retrieve pets"}), 500
    return jsonify(pets)


@app.route("/pets/<string:pet_id>", methods=["GET"])
async def get_pet(pet_id: str):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id,
        )
        if not pet:
            return jsonify({"error": f"Pet with id {pet_id} not found"}), 404
    except Exception as e:
        logger.exception(f"Failed to get pet id {pet_id} from entity_service")
        return jsonify({"error": "Failed to retrieve pet"}), 500
    return jsonify(pet)


@app.route("/pets/customize-message", methods=["POST"])
@validate_request(CustomizeMessage)
async def customize_message(data: CustomizeMessage):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=data.pet_id,
        )
        if not pet:
            return jsonify({"error": f"Pet with id {data.pet_id} not found"}), 404
    except Exception as e:
        logger.exception(f"Failed to get pet id {data.pet_id} from entity_service")
        return jsonify({"error": "Failed to retrieve pet"}), 500

    pet["message_template"] = data.message_template
    try:
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            entity=pet,
            technical_id=data.pet_id,
            meta={},
        )
    except Exception as e:
        logger.exception(f"Failed to update pet id {data.pet_id}")
        return jsonify({"error": "Failed to update pet description"}), 500
    return jsonify({"pet_id": data.pet_id, "message_template": data.message_template})


if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
