"""Safe serialization utilities for handling None and invalid schema inputs."""

import logging
from typing import Any, Dict, Tuple

logger = logging.getLogger(__name__)


def safe_serialize(
    resource: Any, schema: Any = None
) -> Tuple[Dict[str, Any], int]:
    """
    Safely serialize a resource with defensive guards against None/invalid inputs.

    Args:
        resource: The resource to serialize (can be None, dict, Pydantic model, etc.)
        schema: Optional schema for serialization (not used in current implementation)

    Returns:
        Tuple of (response_dict, status_code)
        - If resource is None: returns (404 JSON, 404)
        - If resource is dict: returns (resource, 200)
        - If resource has model_dump: returns (model_dump result, 200)
        - Otherwise: returns (500 error, 500)
    """
    if resource is None:
        return {"error": "Resource not found", "code": "NOT_FOUND"}, 404

    try:
        if isinstance(resource, dict):
            return resource, 200

        if hasattr(resource, "model_dump"):
            return resource.model_dump(by_alias=True), 200

        logger.warning(
            f"Cannot serialize resource of type {type(resource).__name__}: "
            "no model_dump method and not a dict"
        )
        return {"error": "Serialization failed", "code": "SERIALIZATION_ERROR"}, 500

    except Exception as e:
        logger.exception(f"Error during serialization: {e}")
        return {"error": "Serialization failed", "code": "SERIALIZATION_ERROR"}, 500

