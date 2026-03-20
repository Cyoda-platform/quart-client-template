"""
Simple Service Management

Direct access to services without unnecessary abstraction layers.
Uses dependency-injector for dependency management but with a simple interface.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, cast

from dependency_injector import containers, providers

from common.interfaces.services import IAuthService, IGrpcClient, IProcessorManager
from common.repository.crud_repository import CrudRepository
from common.service.entity_service import EntityService

logger = logging.getLogger(__name__)


def _create_auth_service(
    client_id: str,
    client_secret: str,
    token_url: str,
    skip_ssl: bool,
    scope: str = "read write",
) -> IAuthService:
    """Create auth service with lazy import."""
    from common.auth.cyoda_auth import CyodaAuthService

    # CyodaAuthService may not be typed; cast to the interface
    return cast(
        IAuthService,
        CyodaAuthService(
            client_id=client_id,
            client_secret=client_secret,
            token_url=token_url,
            skip_ssl=skip_ssl,
            scope=scope,
        ),
    )


def _create_repository(
    auth_service: IAuthService, use_in_memory: bool
) -> CrudRepository[Any]:
    """Create repository with lazy import."""
    if use_in_memory:
        from common.repository.in_memory_db import InMemoryRepository

        # InMemoryRepository may be untyped; cast to CrudRepository[Any]
        return cast(CrudRepository[Any], InMemoryRepository())
    else:
        from common.repository.cyoda.cyoda_repository import CyodaRepository

        # CyodaRepository may be untyped; cast to CrudRepository[Any]
        return cast(
            CrudRepository[Any], CyodaRepository(cyoda_auth_service=auth_service)
        )


def _create_entity_service(repository: CrudRepository[Any]) -> EntityService:
    """Create entity service with lazy import."""
    from common.service.service import EntityServiceImpl

    # EntityServiceImpl should conform to EntityService
    return cast(EntityService, EntityServiceImpl(repository=repository))


def _create_grpc_client(auth_service: IAuthService) -> IGrpcClient:
    """Create gRPC client with lazy import."""
    from common.grpc_client.grpc_client import GrpcClient

    # Third-party/legacy code may be untyped; silence with cast
    return cast(IGrpcClient, GrpcClient(auth=auth_service))  # type: ignore[no-untyped-call]


def _create_entity_management_service(
    entity_service: EntityService, auth_service: IAuthService
) -> Any:
    """Create entity management service with lazy import."""
    from cyoda_mcp.mcp_services.entity_management import EntityManagementService

    return cast(  # type: ignore[no-untyped-call]
        Any,
        EntityManagementService(entity_service=entity_service, auth_service=auth_service),
    )


def _create_entity_model_service(auth_service: IAuthService) -> Any:
    """Create entity model service with lazy import."""
    from cyoda_mcp.mcp_services.entity_model import EntityModelService

    return cast(Any, EntityModelService(auth_service=auth_service))  # type: ignore[no-untyped-call]


def _create_entity_audit_service(auth_service: IAuthService) -> Any:
    """Create entity audit service with lazy import."""
    from cyoda_mcp.mcp_services.entity_audit import EntityAuditService

    return cast(Any, EntityAuditService(auth_service=auth_service))  # type: ignore[no-untyped-call]


def _create_entity_stats_service(auth_service: IAuthService) -> Any:
    """Create entity stats service with lazy import."""
    from cyoda_mcp.mcp_services.entity_stats import EntityStatsService

    return cast(Any, EntityStatsService(auth_service=auth_service))  # type: ignore[no-untyped-call]


def _create_async_search_service(auth_service: IAuthService) -> Any:
    """Create async search service with lazy import."""
    from cyoda_mcp.mcp_services.async_search import AsyncSearchService

    return cast(Any, AsyncSearchService(auth_service=auth_service))  # type: ignore[no-untyped-call]


def _create_search_service(entity_service: EntityService) -> Any:
    """Create search service with lazy import."""
    from cyoda_mcp.mcp_services.search import SearchService

    return cast(Any, SearchService(entity_service=entity_service))  # type: ignore[no-untyped-call]


def _create_edge_message_repository(auth_service: IAuthService) -> Any:
    """Create edge message repository with lazy import."""
    from common.repository.cyoda.edge_message_repository import EdgeMessageRepository

    return cast(Any, EdgeMessageRepository(cyoda_auth_service=auth_service))  # type: ignore[no-untyped-call]


def _create_edge_message_service(edge_message_repository: Any) -> Any:
    """Create edge message service with lazy import."""
    from cyoda_mcp.mcp_services.edge_message import EdgeMessageService

    return cast(  # type: ignore[no-untyped-call]
        Any, EdgeMessageService(edge_message_repository=edge_message_repository)
    )


def _create_workflow_repository(auth_service: IAuthService) -> Any:
    """Create workflow repository with lazy import."""
    from common.repository.cyoda.workflow_repository import WorkflowRepository

    return cast(Any, WorkflowRepository(cyoda_auth_service=auth_service))  # type: ignore[no-untyped-call]


def _create_workflow_management_service(workflow_repository: Any) -> Any:
    """Create workflow management service with lazy import."""
    from cyoda_mcp.mcp_services.workflow_management import WorkflowManagementService

    return cast(  # type: ignore[no-untyped-call]
        Any, WorkflowManagementService(workflow_repository=workflow_repository)
    )


def _create_deployment_repository(auth_service: IAuthService) -> Any:
    """Create deployment repository with lazy import."""
    from common.repository.cyoda.deployment_repository import DeploymentRepository

    return cast(Any, DeploymentRepository(cyoda_auth_service=auth_service))  # type: ignore[no-untyped-call,arg-type]


def _create_deployment_service(deployment_repository: Any) -> Any:
    """Create deployment service with lazy import."""
    from cyoda_mcp.mcp_services.deployment import DeploymentService

    return cast(Any, DeploymentService(deployment_repository=deployment_repository))  # type: ignore[no-untyped-call]


def _create_processor_manager(modules: List[str]) -> IProcessorManager:
    """Create processor manager with lazy import."""
    from common.processor import get_processor_manager

    return cast(IProcessorManager, get_processor_manager(modules))


class ServiceContainer(containers.DeclarativeContainer):
    """Simple service container with all dependencies."""

    # Configuration
    config = providers.Configuration()

    # Core services
    auth_service = providers.Singleton(
        _create_auth_service,
        client_id=config.authentication.client_id,
        client_secret=config.authentication.client_secret,
        token_url=config.authentication.token_url,
        skip_ssl=config.authentication.skip_ssl,
        scope=config.authentication.scope,
    )

    # Repository - can be either Cyoda or InMemory based on config
    repository = providers.Singleton(
        _create_repository,
        auth_service=auth_service,
        use_in_memory=config.repository.use_in_memory.as_(bool),
    )

    # Entity service
    entity_service = providers.Singleton(
        _create_entity_service,
        repository=repository,
    )

    # Processor manager
    processor_manager = providers.Singleton(
        _create_processor_manager,
        modules=config.processor.modules.as_(list),
    )

    # gRPC client
    grpc_client = providers.Singleton(
        _create_grpc_client,
        auth_service=auth_service,
    )

    # Utilities
    chat_lock = providers.Singleton(asyncio.Lock)

    # MCP Services
    entity_management_service = providers.Singleton(
        _create_entity_management_service,
        entity_service=entity_service,
        auth_service=auth_service,
    )

    entity_model_service = providers.Singleton(
        _create_entity_model_service,
        auth_service=auth_service,
    )

    entity_audit_service = providers.Singleton(
        _create_entity_audit_service,
        auth_service=auth_service,
    )

    entity_stats_service = providers.Singleton(
        _create_entity_stats_service,
        auth_service=auth_service,
    )

    async_search_service = providers.Singleton(
        _create_async_search_service,
        auth_service=auth_service,
    )

    search_service = providers.Singleton(
        _create_search_service,
        entity_service=entity_service,
    )

    # Edge Message Repository and Service
    edge_message_repository = providers.Singleton(
        _create_edge_message_repository,
        auth_service=auth_service,
    )

    edge_message_service = providers.Singleton(
        _create_edge_message_service,
        edge_message_repository=edge_message_repository,
    )

    # Workflow Repository and Management Service
    workflow_repository = providers.Singleton(
        _create_workflow_repository,
        auth_service=auth_service,
    )

    workflow_management_service = providers.Singleton(
        _create_workflow_management_service,
        workflow_repository=workflow_repository,
    )

    # Deployment Repository and Service
    deployment_repository = providers.Singleton(
        _create_deployment_repository,
        auth_service=auth_service,
    )

    deployment_service = providers.Singleton(
        _create_deployment_service,
        deployment_repository=deployment_repository,
    )


# Global container instance
_container: Optional[ServiceContainer] = None
_initialized: bool = False


def initialize_services(config: Dict[str, Any]) -> None:
    """
    Initialize services with the provided configuration.

    Args:
        config: Configuration dictionary
    """
    global _container, _initialized

    if _initialized:
        logger.warning("Services already initialized")
        return

    logger.info("Initializing services...")

    # Create and configure container
    _container = ServiceContainer()
    _container.config.from_dict(config)

    # Eagerly initialize all services
    logger.info("Eagerly initializing all services...")
    try:
        _ = _container.auth_service()
        logger.info("✓ Auth service initialized")

        _ = _container.repository()
        logger.info("✓ Repository initialized")

        _ = _container.entity_service()
        logger.info("✓ Entity service initialized")

        _ = _container.processor_manager()
        logger.info("✓ Processor manager initialized")

        _ = _container.grpc_client()
        logger.info("✓ gRPC client initialized")

        _ = _container.chat_lock()
        logger.info("✓ Chat lock initialized")

        _ = _container.entity_management_service()
        logger.info("✓ Entity management service initialized")

        logger.info("All services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

    _initialized = True
    logger.info("Service initialization complete")


def _ensure_initialized() -> ServiceContainer:
    """Ensure services are initialized and return the container."""
    if not _initialized or _container is None:
        raise RuntimeError(
            "Services not initialized. Call initialize_services() first."
        )
    # Narrow Optional[ServiceContainer] to ServiceContainer for type-checker
    return _container


# Direct service access functions
def get_auth_service() -> IAuthService:
    """Get the authentication service."""
    container = _ensure_initialized()
    return container.auth_service()  # type: ignore[return-value]


def get_repository() -> CrudRepository[Any]:
    """Get the repository."""
    container = _ensure_initialized()
    return container.repository()  # type: ignore[return-value]


def get_entity_service() -> EntityService:
    """Get the entity service."""
    container = _ensure_initialized()
    return container.entity_service()  # type: ignore[return-value]


def get_processor_manager() -> IProcessorManager:
    """Get the processor manager."""
    container = _ensure_initialized()
    return container.processor_manager()  # type: ignore[return-value]


def get_grpc_client() -> IGrpcClient:
    """Get the gRPC client."""
    container = _ensure_initialized()
    return container.grpc_client()  # type: ignore[return-value]


def get_chat_lock() -> asyncio.Lock:
    """Get the chat lock."""
    container = _ensure_initialized()
    return container.chat_lock()  # type: ignore[return-value]


def get_entity_management_service() -> Any:
    """Get the entity management service."""
    container = _ensure_initialized()
    return container.entity_management_service()


def get_search_service() -> Any:
    """Get the search service."""
    container = _ensure_initialized()
    return container.search_service()


def get_edge_message_repository() -> Any:
    """Get the edge message repository."""
    container = _ensure_initialized()
    return container.edge_message_repository()


def get_edge_message_service() -> Any:
    """Get the edge message service."""
    container = _ensure_initialized()
    return container.edge_message_service()


def get_workflow_repository() -> Any:
    """Get the workflow repository."""
    container = _ensure_initialized()
    return container.workflow_repository()


def get_workflow_management_service() -> Any:
    """Get the workflow management service."""
    container = _ensure_initialized()
    return container.workflow_management_service()


def get_deployment_repository() -> Any:
    """Get the deployment repository."""
    container = _ensure_initialized()
    return container.deployment_repository()


def get_deployment_service() -> Any:
    """Get the deployment service."""
    container = _ensure_initialized()
    return container.deployment_service()


def get_entity_model_service() -> Any:
    """Get the entity model service."""
    container = _ensure_initialized()
    return container.entity_model_service()


def get_entity_audit_service() -> Any:
    """Get the entity audit service."""
    container = _ensure_initialized()
    return container.entity_audit_service()


def get_entity_stats_service() -> Any:
    """Get the entity stats service."""
    container = _ensure_initialized()
    return container.entity_stats_service()


def get_async_search_service() -> Any:
    """Get the async search service."""
    container = _ensure_initialized()
    return container.async_search_service()


def is_initialized() -> bool:
    """Check if services are initialized."""
    return _initialized


def shutdown_services() -> None:
    """Shutdown services and clean up resources."""
    global _container, _initialized

    if _initialized and _container:
        logger.info("Shutting down services...")
        _container.unwire()
        _container = None
        _initialized = False
        logger.info("Services shut down successfully")
