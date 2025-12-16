"""
Centralized service configuration module.

This module provides a single source of truth for service configuration
to avoid duplication across app.py and cyoda_mcp/server.py.
"""

import logging
import os
from typing import Any, Dict

from common.config.config import (
    CYODA_CLIENT_ID,
    CYODA_CLIENT_SECRET,
    CYODA_TOKEN_URL,
    SKIP_SSL,
)

logger = logging.getLogger(__name__)


def get_service_config() -> Dict[str, Any]:
    """
    Get the standard service configuration from environment variables.

    This configuration is used consistently across the application and MCP server.

    Returns:
        Dictionary containing service configuration
    """
    config: Dict[str, Any] = {
        "authentication": {
            "client_id": CYODA_CLIENT_ID,
            "client_secret": CYODA_CLIENT_SECRET,
            "token_url": CYODA_TOKEN_URL,
            "skip_ssl": SKIP_SSL,
            "scope": "read write",
        },
        "repository": {
            "use_in_memory": os.getenv("CHAT_REPOSITORY", "cyoda").lower() != "cyoda",
        },
        "processor": {
            "modules": [
                "application.processor.order_processor",
                "application.processor.trade_processor",
                "application.processor.risk_processor",
                "application.processor.settlement_processor",
                "application.processor.reconciliation_processor",
                "application.criterion.order_validation_criterion",
                "application.criterion.risk_validation_criterion",
                "application.criterion.trade_validation_criterion",
                "example_application.processor",
                "example_application.criterion",
            ],
        },
    }

    # Log configuration (without sensitive data)
    logger.info("Service configuration loaded:")
    logger.info(
        f"  - Repository type: {'In-Memory' if config['repository']['use_in_memory'] else 'Cyoda'}"
    )
    logger.info(f"  - Auth configured: {bool(config['authentication']['client_id'])}")
    logger.info(f"  - Token URL: {config['authentication']['token_url'] or 'Not set'}")
    logger.info(f"  - Processor modules: {config['processor']['modules']}")

    return config


def get_repository_type() -> str:
    """
    Get the repository type being used.

    Returns:
        'in_memory' or 'cyoda'
    """
    return (
        "in_memory"
        if os.getenv("CHAT_REPOSITORY", "cyoda").lower() != "cyoda"
        else "cyoda"
    )


def is_in_memory_repository() -> bool:
    """
    Check if the in-memory repository is being used.

    Returns:
        True if using in-memory repository, False if using Cyoda repository
    """
    return get_repository_type() == "in_memory"


def validate_configuration() -> Dict[str, Any]:
    """
    Validate the current service configuration and return validation results.

    Returns:
        Dictionary containing validation results and warnings
    """
    config = get_service_config()
    validation: Dict[str, Any] = {
        "valid": True,
        "warnings": [],
        "errors": [],
        "repository_type": get_repository_type(),
    }

    # Check authentication configuration
    if not config["authentication"]["client_id"]:
        validation["warnings"].append(
            "CYODA_CLIENT_ID not set - authentication will not work"
        )

    if not config["authentication"]["client_secret"]:
        validation["warnings"].append(
            "CYODA_CLIENT_SECRET not set - authentication will not work"
        )

    if not config["authentication"]["token_url"]:
        validation["warnings"].append(
            "CYODA_TOKEN_URL not set - authentication will not work"
        )

    # Check repository configuration
    if is_in_memory_repository():
        validation["warnings"].append(
            "Using in-memory repository - data will not persist"
        )

    # Log validation results
    if validation["warnings"]:
        logger.warning("Configuration validation warnings:")
        for warning in validation["warnings"]:
            logger.warning(f"  - {warning}")

    if validation["errors"]:
        logger.error("Configuration validation errors:")
        for error in validation["errors"]:
            logger.error(f"  - {error}")
        validation["valid"] = False

    return validation
