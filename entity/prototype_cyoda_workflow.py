ENTITY_VERSION = "1.0"

# Assume entity_service and cyoda_auth_service are imported and available in the module scope

# Example async side effect function (placeholder)
async def some_async_side_effect(entity):
    # Simulate an async side effect, e.g., logging, notification, external API call
    # Replace with real implementation
    pass

# Workflow function for "related_entity"
async def process_related_entity(entity):
    # Example: mark related entity as processed
    entity['processed_related'] = True
    # No recursion or add/update/delete of "related_entity" here beyond what is safe
    return entity

# Factory to create workflow function for sample_entity with token context
def make_process_sample_entity(token):
    async def process_sample_entity(entity):
        # Perform async side effect
        await some_async_side_effect(entity)

        # Add supplementary related entity asynchronously
        related_entity_data = {
            "parent_id": entity.get("id"),
            "info": "extra"
        }
        # Add related entity of a different model allowed in workflow
        await entity_service.add_item(
            token=token,
            entity_model="related_entity",
            entity_version=ENTITY_VERSION,
            entity=related_entity_data,
            workflow=process_related_entity
        )

        # Mutate current entity state directly before persistence
        entity['processed'] = True
        return entity
    return process_sample_entity

# Endpoint handler for creating sample_entity
# Assuming FastAPI style with Depends
from fastapi import APIRouter, Depends

router = APIRouter()

# Placeholder for auth dependency
async def get_auth():
    # Return auth token or service required by entity_service
    # Replace with actual auth retrieval
    return "auth_token"

# Pydantic schema for validated input (simplified example)
from pydantic import BaseModel

class SampleEntityCreateSchema(BaseModel):
    id: str
    name: str
    # other fields...

@router.post("/sample-entity")
async def create_sample_entity(data: SampleEntityCreateSchema, cyoda_auth_service=Depends(get_auth)):
    # Create workflow with context token
    workflow = make_process_sample_entity(cyoda_auth_service)

    # Add entity with workflow function applied
    entity_id = await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="sample_entity",
        entity_version=ENTITY_VERSION,
        entity=data.dict(),  # convert Pydantic model to dict
        workflow=workflow
    )
    return {"id": entity_id}

# Additional example: Workflow and endpoint for related_entity creation if needed

def make_process_related_entity(token):
    async def process_related_entity(entity):
        # Potential async side effects or modifications for related_entity
        # For demo, just mark processed
        entity['processed_related'] = True
        return entity
    return process_related_entity

@router.post("/related-entity")
async def create_related_entity(data: dict, cyoda_auth_service=Depends(get_auth)):
    workflow = make_process_related_entity(cyoda_auth_service)
    entity_id = await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="related_entity",
        entity_version=ENTITY_VERSION,
        entity=data,
        workflow=workflow
    )
    return {"id": entity_id}

# Notes to prevent issues:
# - Never call add/update/delete on the same entity_model inside its workflow function to avoid recursion.
# - Workflow functions must be async and return the modified entity dict.
# - Passing token to workflow functions via factory closures to ensure access.
# - Controllers keep minimal logic, delegating async and entity state changes to workflows.
# - All external async calls (e.g., some_async_side_effect) must be awaited properly inside workflows.
# - Entity dicts passed to workflows are mutable and changes persist automatically after workflow completes.