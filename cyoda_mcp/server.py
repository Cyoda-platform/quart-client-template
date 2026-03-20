# cyoda_mcp/server.py
from __future__ import annotations

# Add the parent directory to the path so we can import from the main app
# This MUST be done before any other imports that depend on the main app modules
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

"""
Main MCP Server for Cyoda Integration

This module provides a unified FastMCP server that composes all category servers
with proper prefixes for organized tool catalogs.
"""

import asyncio  # noqa: E402
import logging  # noqa: E402
from typing import Literal  # noqa: E402

from fastmcp import FastMCP  # noqa: E402

from cyoda_mcp.tools.async_search import mcp as mcp_async_search  # noqa: E402
from cyoda_mcp.tools.edge_message import mcp as mcp_edge_message  # noqa: E402
from cyoda_mcp.tools.entity_audit import mcp as mcp_entity_audit  # noqa: E402
from cyoda_mcp.tools.entity_management import mcp as mcp_entity  # noqa: E402
from cyoda_mcp.tools.entity_model import mcp as mcp_entity_model  # noqa: E402
from cyoda_mcp.tools.entity_stats import mcp as mcp_entity_stats  # noqa: E402
from cyoda_mcp.tools.search import mcp as mcp_search  # noqa: E402
from cyoda_mcp.tools.workflow_management import (  # noqa: E402
    mcp as mcp_workflow_management,
)

logger = logging.getLogger(__name__)


def initialize_mcp_services() -> bool:
    """Initialize all services with proper dependency injection configuration.

    Returns:
        bool: True if services initialized successfully, False otherwise.
    """
    from services.config import get_service_config, validate_configuration
    from services.services import initialize_services

    try:
        # Validate configuration first
        validation = validate_configuration()
        if not validation["valid"]:
            logger.error("MCP service configuration validation failed!")
            return False

        # Use centralized configuration
        config = get_service_config()
        logger.info("Initializing MCP services at startup...")
        initialize_services(config)
        logger.info("MCP services initialized successfully with dependency injection")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize MCP services: {e}")
        return False


# Initialize services when the module is loaded
_services_initialized: bool = initialize_mcp_services()

# Single, unified server
mcp: FastMCP = FastMCP("Cyoda Client Tools 🚀")


async def setup() -> None:
    """Setup the main server by importing all category servers with prefixes."""
    try:
        # Namespace each category to keep the catalog tidy
        await mcp.import_server(mcp_entity, prefix="entity")
        await mcp.import_server(mcp_search, prefix="search")
        await mcp.import_server(mcp_edge_message, prefix="edge_message")
        await mcp.import_server(mcp_workflow_management, prefix="workflow_mgmt")
        await mcp.import_server(mcp_entity_model, prefix="entity_model")
        await mcp.import_server(mcp_entity_audit, prefix="entity_audit")
        await mcp.import_server(mcp_entity_stats, prefix="entity_stats")
        await mcp.import_server(mcp_async_search, prefix="async_search")

        logger.info("All MCP category servers imported successfully")
    except Exception as e:
        logger.error(f"Failed to setup MCP servers: {e}")
        raise


def set_integrated_mode() -> None:
    """Set the server to integrated mode (not standalone)."""
    # Services are already initialized, nothing to do
    return None


def get_mcp() -> FastMCP:
    """
    Get the configured FastMCP server instance.

    Returns:
        FastMCP: The FastMCP server instance.
    """
    return mcp


def run_mcp(
    transport: Literal["stdio", "http", "sse"] = "stdio",
    host: str = "127.0.0.1",
    port: int = 8002,
) -> None:
    """
    Run the FastMCP server (synchronous).

    Args:
        transport: Transport type ("stdio", "http", "sse")
        host: Host to bind to (for HTTP/SSE transport)
        port: Port to bind to (for HTTP/SSE transport)
    """
    if transport == "stdio":
        logger.info("Starting FastMCP server with STDIO transport")
        mcp.run()
    elif transport == "http":
        logger.info(f"Starting FastMCP server with HTTP transport on {host}:{port}")
        mcp.run(transport="http", host=host, port=port)
    elif transport == "sse":
        logger.info(f"Starting FastMCP server with SSE transport on {host}:{port}")
        mcp.run(transport="sse", host=host, port=port)
    else:
        raise ValueError(f"Unsupported transport: {transport}")


def start(
    transport: Literal["stdio", "http", "sse"] = "stdio",
    host: str = "127.0.0.1",
    port: int = 8002,
) -> None:
    """
    Boot the MCP server with the specified transport.
    Read any API keys from env vars.
    Don't require users to edit this file.

    This is the main entry point for the packaged CLI.

    Args:
        transport: Transport type ("stdio", "http", "sse")
        host: Host to bind to (for HTTP/SSE transport)
        port: Port to bind to (for HTTP/SSE transport)
    """
    # Setup the server composition first
    asyncio.run(setup())

    # Then run the server
    run_mcp(transport=transport, host=host, port=port)


if __name__ == "__main__":
    # Setup the server composition
    asyncio.run(setup())

    # Run the MCP server standalone
    MCP_TRANSPORT = os.getenv("MCP_TRANSPORT")
    mcp_host = os.getenv("MCP_HOST", "127.0.0.1")  # Default to localhost for security
    mcp_port = int(os.getenv("MCP_PORT", "8002"))

    if MCP_TRANSPORT == "http":
        run_mcp(transport="http", host=mcp_host, port=mcp_port)
    elif MCP_TRANSPORT == "sse":
        run_mcp(transport="sse", host=mcp_host, port=mcp_port)
    else:
        run_mcp(transport="stdio")
