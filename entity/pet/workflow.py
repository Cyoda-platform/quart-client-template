from datetime import datetime

async def process_fetch_pet(entity: dict):
    # Simulate fetching pets from external API and store results in entity
    # TODO: actual fetch logic should be implemented in real use case
    entity["pets_fetched"] = entity.get("pets_fetched", [])
    entity["status"] = "fetched"
    entity["fetchedAt"] = datetime.utcnow().isoformat()

async def process_filter_pet(entity: dict):
    # Apply filtering and assign fun_category on pets in entity
    pets = entity.get("pets_fetched", [])
    min_age = entity.get("min_age")
    max_age = entity.get("max_age")
    fun_category = entity.get("fun_category")

    filtered = []
    for pet in pets:
        age = pet.get("age")
        if min_age is not None and (age is None or age < min_age):
            continue
        if max_age is not None and (age is None or age > max_age):
            continue
        pet_copy = pet.copy()
        if fun_category:
            pet_copy["fun_category"] = fun_category
        else:
            if age is not None:
                if age <= 3:
                    pet_copy["fun_category"] = "playful"
                elif age >= 7:
                    pet_copy["fun_category"] = "sleepy"
                else:
                    pet_copy["fun_category"] = "neutral"
            else:
                pet_copy["fun_category"] = "unknown"
        filtered.append(pet_copy)

    entity["pets_filtered"] = filtered
    entity["status"] = "filtered"
    entity["filteredAt"] = datetime.utcnow().isoformat()

async def process_pet(entity: dict):
    # Workflow orchestration: run fetch then filter sequentially
    if entity.get("status") != "fetched":
        await process_fetch_pet(entity)
    if entity.get("status") == "fetched":
        await process_filter_pet(entity)
    # Add processed timestamp
    entity["processedAt"] = datetime.utcnow().isoformat()