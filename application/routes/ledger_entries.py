"""
LedgerEntry routes for institutional trading platform.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.ledger_entry import LedgerEntry
from common.exception import is_not_found
from services.services import get_entity_service

logger = logging.getLogger(__name__)

ledger_entries_bp = Blueprint(
    "ledger_entries", __name__, url_prefix="/api/ledger-entries"
)


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


def _to_entity_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert entity data to response format."""
    return data if isinstance(data, dict) else data.model_dump(by_alias=True)


@ledger_entries_bp.route("", methods=["POST"])
@tag(["ledger-entries"])
@operation_id("create_ledger_entry")
@validate(
    request=LedgerEntry,
    responses={201: (Dict[str, Any], None), 500: (Dict[str, Any], None)},
)
async def create_ledger_entry(data: LedgerEntry) -> ResponseReturnValue:
    """Create a new LedgerEntry"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=LedgerEntry.ENTITY_NAME,
            entity_version=str(LedgerEntry.ENTITY_VERSION),
        )
        logger.info("Created LedgerEntry with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201
    except Exception as e:
        logger.error("Error creating ledger entry: %s", str(e))
        return {"error": str(e)}, 500


@ledger_entries_bp.route("/<entity_id>", methods=["GET"])
@tag(["ledger-entries"])
@operation_id("get_ledger_entry")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    }
)
async def get_ledger_entry(entity_id: str) -> ResponseReturnValue:
    """Get a LedgerEntry by ID"""
    try:
        response = await service.get(
            entity_id=entity_id,
            entity_class=LedgerEntry.ENTITY_NAME,
        )
        if is_not_found(response):
            return {"error": "Not found"}, 404
        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.error("Error getting ledger entry: %s", str(e))
        return {"error": str(e)}, 500


@ledger_entries_bp.route("", methods=["GET"])
@tag(["ledger-entries"])
@operation_id("list_ledger_entries")
@validate(responses={200: (Dict[str, Any], None), 500: (Dict[str, Any], None)})
async def list_ledger_entries() -> ResponseReturnValue:
    """List all LedgerEntries"""
    try:
        response = await service.list(
            entity_class=LedgerEntry.ENTITY_NAME,
        )
        return {"data": response.data}, 200
    except Exception as e:
        logger.error("Error listing ledger entries: %s", str(e))
        return {"error": str(e)}, 500
