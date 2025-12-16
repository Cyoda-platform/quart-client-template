from quart import Blueprint, request
from services.services import get_entity_service
from application.entity.account.version_1.Account import Account

bp = Blueprint("account", __name__, url_prefix="/ui/account")

@bp.route("/", methods=["POST"])
async def create_account():
    """Create new account."""
    entity_service = get_entity_service()
    data = await request.get_json()
    
    entity = Account(**data)
    
    result = await entity_service.create(entity)
    
    return {"id": result.id}

@bp.route("/<entity_id>", methods=["PUT"])
async def update_account(entity_id: str):
    """Update account."""
    entity_service = get_entity_service()
    data = await request.get_json()
    
    existing = await entity_service.get_by_id(
        entity_id, 
        Account.ENTITY_NAME, 
        str(Account.ENTITY_VERSION)
    )
    
    updated = existing.data.model_copy(update=data)
    
    result = await entity_service.update(updated, transition="update_account")
    
    return {"id": result.id}
