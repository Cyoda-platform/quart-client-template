import functools
import logging
import re

from quart import request, jsonify
import jwt

from common.config.config import CYODA_API_URL
from common.exception.exceptions import UnauthorizedAccessException
from common.utils.utils import send_get_request

logger = logging.getLogger(__name__)

def _get_data_from_token(auth_header: str, key: str):
    """
    Extracts and decodes the JWT from the Authorization header.
    Returns the user name (sub claim) if available.
    """
    if not auth_header:
        return None
    parts = auth_header.split(" ")
    if len(parts) != 2:
        return None
    token = parts[1]
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        value = decoded.get(key)
        return value
    except Exception as e:
        logger.exception("Failed to decode JWT: %s", e)
        return None

def auth_required(func):
    """
    Decorator to enforce authentication.
    If ENABLE_AUTH is True, it verifies the presence of an Authorization header
    and then calls an external service to validate the token.
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({"error": "Missing Authorization header"}), 401

        # Split out the token from the header.
        token = auth_header.split(" ")[1]

        # Validate the token via an external call.
        response = await send_get_request(token, CYODA_API_URL, "v1")
        if not response or (response.get("status") and response.get("status") == 401):
            raise UnauthorizedAccessException("Invalid token")
        user_name = _get_data_from_token(auth_header=auth_header, key="sub")
        issuer = _get_data_from_token(auth_header=auth_header, key="iss")
        kwargs['user_name'] = user_name
        return await func(*args, **kwargs)

    return wrapper

def get_env_data_from_user(user_name: str, auth_header=None):
    """
    Transforms the user_name into a valid Cassandra keyspace name and
    a valid Kubernetes namespace.
    """
    # For keyspace: only allow lowercase alphanumeric and underscore.
    keyspace = re.sub(r"[^a-z0-9_]", "_", user_name.lower())
    if not keyspace or not keyspace[0].isalpha():
        keyspace = "a" + keyspace
    # For namespace: only allow lowercase alphanumeric and dash.
    namespace = re.sub(r"[^a-z0-9-]", "-", user_name.lower())
    if not namespace or not namespace[0].isalpha():
        namespace = "a" + namespace
    return {"keyspace": keyspace,
            "namespace": namespace}


def _get_toolbox_legal_entity_owner(auth_header):
    toolbox_legal_entity_owner = None
    if auth_header:
        toolbox_legal_entity_owner = _get_data_from_token(auth_header=auth_header, key='caas_org_id')
    return toolbox_legal_entity_owner