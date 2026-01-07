"""
Payment Transaction Routes for Enterprise Payment Processing System

Manages all PaymentTransaction-related API endpoints.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate, validate_querystring

from common.service.entity_service import SearchConditionRequest
from services.services import get_entity_service
from application.entity.payment_transaction import PaymentTransaction


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()
logger = logging.getLogger(__name__)


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


payment_transactions_bp = Blueprint(
    "payment_transactions", __name__, url_prefix="/api/payment-transactions"
)


@payment_transactions_bp.route("", methods=["POST"])
@tag(["payment-transactions"])
@operation_id("create_payment_transaction")
@validate(
    request=PaymentTransaction,
    responses={
        201: (Dict[str, Any], None),
        400: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    },
)
async def create_payment_transaction(
    data: PaymentTransaction,
) -> ResponseReturnValue:
    """Create a new PaymentTransaction"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=PaymentTransaction.ENTITY_NAME,
            entity_version=str(PaymentTransaction.ENTITY_VERSION),
        )
        logger.info("Created PaymentTransaction with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201

    except ValueError as e:
        logger.warning("Validation error creating PaymentTransaction: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error creating PaymentTransaction: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@payment_transactions_bp.route("/<entity_id>", methods=["GET"])
@tag(["payment-transactions"])
@operation_id("get_payment_transaction")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    }
)
async def get_payment_transaction(entity_id: str) -> ResponseReturnValue:
    """Get PaymentTransaction by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=PaymentTransaction.ENTITY_NAME,
            entity_version=str(PaymentTransaction.ENTITY_VERSION),
        )

        if not response:
            return {"error": "PaymentTransaction not found", "code": "NOT_FOUND"}, 404

        return _to_entity_dict(response.data), 200

    except Exception as e:
        logger.exception("Error getting PaymentTransaction %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@payment_transactions_bp.route("", methods=["GET"])
@tag(["payment-transactions"])
@operation_id("list_payment_transactions")
@validate(
    responses={
        200: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    }
)
async def list_payment_transactions() -> ResponseReturnValue:
    """List all PaymentTransactions"""
    try:
        entities = await service.find_all(
            entity_class=PaymentTransaction.ENTITY_NAME,
            entity_version=str(PaymentTransaction.ENTITY_VERSION),
        )
        entity_list = [_to_entity_dict(r.data) for r in entities]
        return jsonify({"entities": entity_list, "total": len(entity_list)}), 200

    except Exception as e:
        logger.exception("Error listing PaymentTransactions: %s", str(e))
        return jsonify({"error": str(e)}), 500


@payment_transactions_bp.route("/<entity_id>", methods=["PUT"])
@tag(["payment-transactions"])
@operation_id("update_payment_transaction")
@validate(
    request=PaymentTransaction,
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    },
)
async def update_payment_transaction(
    entity_id: str, data: PaymentTransaction
) -> ResponseReturnValue:
    """Update PaymentTransaction"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        entity_data: Dict[str, Any] = data.model_dump(by_alias=True)
        response = await service.update(
            entity_id=entity_id,
            entity=entity_data,
            entity_class=PaymentTransaction.ENTITY_NAME,
            entity_version=str(PaymentTransaction.ENTITY_VERSION),
        )

        logger.info("Updated PaymentTransaction %s", entity_id)
        return jsonify(_to_entity_dict(response.data)), 200

    except Exception as e:
        logger.exception("Error updating PaymentTransaction %s: %s", entity_id, str(e))
        return jsonify({"error": str(e), "code": "INTERNAL_ERROR"}), 500


@payment_transactions_bp.route("/<entity_id>", methods=["DELETE"])
@tag(["payment-transactions"])
@operation_id("delete_payment_transaction")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    }
)
async def delete_payment_transaction(entity_id: str) -> ResponseReturnValue:
    """Delete PaymentTransaction"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        await service.delete_by_id(
            entity_id=entity_id,
            entity_class=PaymentTransaction.ENTITY_NAME,
            entity_version=str(PaymentTransaction.ENTITY_VERSION),
        )

        logger.info("Deleted PaymentTransaction %s", entity_id)
        return {
            "success": True,
            "message": "PaymentTransaction deleted successfully",
        }, 200

    except Exception as e:
        logger.exception("Error deleting PaymentTransaction %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500
