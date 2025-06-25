from datetime import datetime  
import logging  
import asyncio  
import httpx  

logger = logging.getLogger(__name__)  

async def process_subscribe_request(entity: dict) -> dict:  
    """  
    Workflow orchestration for subscribe_request entity.  
    Calls business logic steps in sequence.  
    """  
    await process_validate_email(entity)  
    await process_check_duplicate_email(entity)  
    process_set_subscribed_at(entity)  
    return entity  

async def process_validate_email(entity: dict):  
    email = entity.get("email")  
    if not email:  
        raise ValueError("Email is required in subscribe_request entity")  
    # email remains unchanged, no update needed  

async def process_check_duplicate_email(entity: dict):  
    email = entity.get("email")  
    condition = {  
        "cyoda": {  
            "type": "group",  
            "operator": "AND",  
            "conditions": [  
                {  
                    "jsonPath": "$.email",  
                    "operatorType": "EQUALS",  
                    "value": email,  
                    "type": "simple"  
                }  
            ]  
        }  
    }  
    existing = await entity_service.get_items_by_condition(  
        token=cyoda_auth_service,  
        entity_model="subscribe_request",  
        entity_version=ENTITY_VERSION,  
        condition=condition  
    )  
    if existing:  
        raise ValueError(f"Email {email} already subscribed")  

def process_set_subscribed_at(entity: dict):  
    if "subscribedAt" not in entity:  
        entity["subscribedAt"] = datetime.utcnow().isoformat()