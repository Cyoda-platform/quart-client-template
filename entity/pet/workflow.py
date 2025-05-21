async def process_create_pet(entity: dict):
    entity["status"] = "created"
    entity["workflowProcessed"] = True

async def process_update_pet_info(entity: dict):
    entity["status"] = "info_updated"
    entity["workflowProcessed"] = True

async def process_vaccinate_pet(entity: dict):
    if "vaccinations" not in entity:
        entity["vaccinations"] = []
    entity["vaccinations"].append({"vaccine_name": "example", "date_administered": "2024-01-01"})
    entity["workflowProcessed"] = True

async def process_adopt_pet(entity: dict):
    entity["status"] = "adopted"
    entity["adoption_date"] = "2024-01-01"
    entity["workflowProcessed"] = True

async def process_deactivate_pet(entity: dict):
    entity["status"] = "deactivated"
    entity["workflowProcessed"] = True