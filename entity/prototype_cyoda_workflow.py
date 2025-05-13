Certainly! I've updated the code to add the required `workflow` parameter to the calls to `entity_service.add_item` and implemented the workflow function `process_adoption_request` (following the `process_{entity_name}` naming convention with underscore lowercase entity name). This function applies the asynchronous processing to the adoption request entity before it is persisted, in line with your description.

Here is the complete updated code:

```python
from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from uuid import uuid4

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class PetSearch:
    type: str
    status: str
    name: str = None

@dataclass
class AdoptRequest:
    petId: str
    adopterName: str
    contactInfo: str

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

async def fetch_pets_from_petstore(type_, status, name):
    params = {}
    if type_ and type_.lower() != "all":
        params["type"] = type_.lower()
    if status and status.lower() != "all":
        params["status"] = status.lower()
    status_param = params.get("status", "available")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": status_param})
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(e)
            return []
    filtered = []
    for pet in pets:
        pet_type = pet.get("category", {}).get("name", "").lower() if pet.get("category") else ""
        pet_name = pet.get("name", "").lower()
        if type_.lower() != "all" and pet_type != type_.lower():
            continue
        if name and name.lower() not in pet_name:
            continue
        filtered.append({
            "id": str(pet.get("id")),
            "name": pet.get("name", ""),
            "type": pet_type or "unknown",
            "status": pet.get("status", ""),
            "description": pet.get("tags")[0]["name"] if pet.get("tags") else "",
            "imageUrl": pet.get("photoUrls")[0] if pet.get("photoUrls") else "",
        })
    return filtered

async def process_adoption(adoption_id, adoption_data):
    try:
        await asyncio.sleep(2)
        adoption_data["status"] = "approved"
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="adoption_request",
            entity=adoption_data,
            entity_version=ENTITY_VERSION,
            technical_id=adoption_id,
            meta={}
        )
        logger.info(f"Adoption {adoption_id} approved for pet {adoption_data['petId']}")
    except Exception as e:
        logger.exception(e)
        adoption_data["status"] = "error"
        try:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="adoption_request",
                entity=adoption_data,
                entity_version=ENTITY_VERSION,
                technical_id=adoption_id,
                meta={}
            )
        except Exception as e2:
            logger.exception(e2)

# New workflow function for adoption_request entity
async def process_adoption_request(entity_data):
    """
    Workflow function applied asynchronously to the adoption_request entity before persistence.
    This example simply sets the status to 'pending' (or could do other preprocessing).
    """
    # Example: ensure status is always 'pending' on creation (or could be other logic)
    entity_data["status"] = "pending"
    # Could add additional async calls or modifications here if needed
    # Do NOT add/update/delete entity of the same entity_model here (to avoid recursion)
    return entity_data

@app.route("/pets/search", methods=["POST"])
@validate_request(PetSearch)
async def pets_search(data: PetSearch):
    pets = await fetch_pets_from_petstore(data.type, data.status, data.name)
    # Save pets to external service
    # We can add/update pets one by one asynchronously
    for pet in pets:
        pet_id = pet["id"]
        try:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="pet",
                entity=pet,
                entity_version=ENTITY_VERSION,
                technical_id=pet_id,
                meta={}
            )
        except Exception as e:
            logger.exception(e)
    return jsonify({"pets": pets})

@app.route("/pets/adopt", methods=["POST"])
@validate_request(AdoptRequest)
async def pets_adopt(data: AdoptRequest):
    pet_id = data.petId
    # Retrieve pet via entity_service
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=str(pet_id)
        )
    except Exception as e:
        logger.exception(e)
        pet = None

    if not pet:
        return jsonify({"message": "Pet not found or not cached; please search first"}), 404

    adoption_id = str(uuid4())
    requested_at = datetime.utcnow().isoformat()
    adoption_record = {
        "adoptionId": adoption_id,
        "petId": pet_id,
        "adopterName": data.adopterName,
        "contactInfo": data.contactInfo,
        # Initial status is set in workflow function, so can omit here or keep for clarity
        "status": "pending",
        "requestedAt": requested_at,
    }
    try:
        # Pass workflow function process_adoption_request to add_item
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="adoption_request",
            entity_version=ENTITY_VERSION,
            entity=adoption_record,
            workflow=process_adoption_request
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Failed to submit adoption request"}), 500

    # Start background approval process
    asyncio.create_task(process_adoption(adoption_id, adoption_record))
    return jsonify({"message": "Adoption request submitted successfully", "adoptionId": adoption_id})

@app.route("/pets/<pet_id>", methods=["GET"])
async def get_pet(pet_id):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=str(pet_id)
        )
    except Exception as e:
        logger.exception(e)
        pet = None
    if not pet:
        return jsonify({"message": "Pet not found"}), 404
    return jsonify(pet)

@app.route("/adoptions/<adoption_id>", methods=["GET"])
async def get_adoption(adoption_id):
    try:
        adoption = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="adoption_request",
            entity_version=ENTITY_VERSION,
            technical_id=str(adoption_id)
        )
    except Exception as e:
        logger.exception(e)
        adoption = None
    if not adoption:
        return jsonify({"message": "Adoption request not found"}), 404
    return jsonify(adoption)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```

### Summary of changes:
- Added a new async function `process_adoption_request(entity_data)` to act as the workflow function for the `adoption_request` entity.
- Updated the `entity_service.add_item` call inside `pets_adopt` endpoint to pass the `workflow=process_adoption_request` parameter.
- The workflow function modifies the entity data (sets `"status": "pending"`) before the entity is persisted.
- The rest of the code remains unchanged.

Let me know if you need any further adjustments!