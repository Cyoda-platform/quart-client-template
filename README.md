# Cyoda MCP Client

A Model Context Protocol (MCP) server for the Cyoda platform, providing AI assistants with seamless access to Cyoda's entity management, search, workflow, and deployment capabilities.

## Quick Start (One-liner Install)

### Zero-setup run (no clone, no venv)
```bash
# Set your Cyoda credentials
export CYODA_CLIENT_ID="your-client-id"
export CYODA_CLIENT_SECRET="your-client-secret"
export CYODA_HOST="client-<id>.eu.cyoda.net"

# Run immediately with pipx
pipx run mcp-cyoda
```

### Install once and run repeatedly
```bash
# Install the package
pipx install mcp-cyoda

# Run the server
mcp-cyoda

# Or with custom options
mcp-cyoda --transport http --port 9000
mcp-cyoda --help
```

## Getting Your Cyoda Environment

1. **Sign up**: Go to [https://ai.cyoda.net](https://ai.cyoda.net) and create an account
2. **Deploy environment**: In a new chat, either:
   - Build an example application, or
   - Directly ask: "Please deploy a Cyoda environment for me"
3. **Get credentials**: Once your environment is deployed, ask for your credentials in the chat

You'll receive:
- `CYODA_CLIENT_ID` - Your unique client identifier
- `CYODA_CLIENT_SECRET` - Your client secret key
- `CYODA_HOST` - Your environment host (e.g., `client-123.eu.cyoda.net`)

## Customer API Implementation

This repository includes a complete REST API implementation for Customer entities using the Cyoda template. The Customer API provides full CRUD operations with comprehensive validation and workflow management.

### Customer API Features

- **Complete CRUD Operations**: Create, Read, Update, Delete customers
- **Input Validation**: Email format validation, required fields, field length constraints
- **Pagination**: Page-based pagination with metadata
- **Workflow Integration**: Full Cyoda workflow with states and transitions
- **Business Logic**: Customer classification (BASIC, STANDARD, PREMIUM)
- **Comprehensive Testing**: Unit tests for all components
- **OpenAPI Documentation**: Complete API specification in `openapi.yaml`

### Quick Start - Customer API

1. **Install Dependencies**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -e ".[dev]"
   ```

2. **Run the Application**:
   ```bash
   python application/app.py
   ```

3. **Access the API**:
   - API Base URL: `http://localhost:8000/api/customers`
   - OpenAPI Spec: See `openapi.yaml`
   - Implementation Details: See `CUSTOMER_API_IMPLEMENTATION_SUMMARY.md`

### Customer API Endpoints

- `POST /api/customers` - Create customer
- `GET /api/customers` - List customers with pagination
- `GET /api/customers/{id}` - Get customer by ID
- `PUT /api/customers/{id}` - Full update customer
- `PATCH /api/customers/{id}` - Partial update customer
- `DELETE /api/customers/{id}` - Delete customer
- `POST /api/customers/search` - Search customers

### Example Usage

```bash
# Create a customer
curl -X POST http://localhost:8000/api/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john.doe@example.com",
    "phone": "+1-555-123-4567",
    "address": "123 Main St, Anytown, USA"
  }'

# List customers with pagination
curl "http://localhost:8000/api/customers?page=1&page_size=10"

# Get customer by ID
curl "http://localhost:8000/api/customers/{customer_id}"
```

For complete documentation, see `CUSTOMER_API_IMPLEMENTATION_SUMMARY.md`.

## Configuration

### Required Environment Variables
```bash
export CYODA_CLIENT_ID="your-client-id"
export CYODA_CLIENT_SECRET="your-client-secret"
export CYODA_HOST="client-<id>.eu.cyoda.net"  # Host only, no https://
```

### Optional Environment Variables
- `MCP_TRANSPORT` - Default transport type (stdio, http, sse)

### IDE/AI Assistant Integration

Add this to your MCP configuration (e.g., in Cursor, Claude Desktop, or other MCP-compatible tools):

```json
{
  "mcpServers": {
    "cyoda": {
      "command": "mcp-cyoda",
      "env": {
        "CYODA_CLIENT_ID": "your-client-id-here",
        "CYODA_CLIENT_SECRET": "your-client-secret-here",
        "CYODA_HOST": "client-123.eu.cyoda.net"
      }
    }
  }
}
```

## Available Tools

The MCP server provides comprehensive access to Cyoda platform capabilities:

### Entity Management
- **Create entities** - Store structured data in Cyoda
- **Read entities** - Retrieve entities by ID or search criteria
- **Update entities** - Modify existing entity data
- **Delete entities** - Remove entities from the system
- **List entities** - Browse all entities of a specific type

### Advanced Search
- **Field-based search** - Find entities by specific field values
- **Complex queries** - Use advanced search conditions with operators
- **Full-text search** - Search across entity content

### Edge Messages
- **Send messages** - Dispatch messages through Cyoda's messaging system
- **Retrieve messages** - Get message history and status

### Workflow Management
- **Export workflows** - Download workflow definitions
- **Import workflows** - Upload and deploy new workflows
- **Copy workflows** - Duplicate workflows between entities

## Example Conversations

With the MCP server connected to your AI assistant (Cursor, Claude Desktop, etc.), you can have natural conversations like:

### Data Collection and Storage
```
You: "Go to website https://example.com and fetch the product data"
AI: [Fetches data from the website]
You: "Save this data as entities in Cyoda"
AI: [Creates entities in your Cyoda environment using the MCP tools]
```

### Data Retrieval
```
You: "Search for entities where category equals 'electronics'"
AI: [Uses search tools to find matching entities]
You: "Get the entity with ID abc-123"
AI: [Retrieves the specific entity using entity management tools]
```

### Workflow Operations
```
You: "Export the workflow from my product entity"
AI: [Exports workflow definition using workflow management tools]
You: "Copy this workflow to my order entity"
AI: [Copies workflow between entities]
```

The AI assistant can seamlessly combine web scraping, data processing, and Cyoda operations in a single conversation, making complex data workflows as simple as natural language requests.

## Development Setup

This template also provides a structured framework for developing a web client using the asynchronous web framework Quart. It offers a foundation to quickly begin development and testing, leveraging Python's asyncio capabilities for efficient handling of requests.

### Features

- **Asynchronous**: Utilizes Python's asyncio capabilities for efficient request handling.
- **Extensibility**: A flexible and configurable project structure designed for easy customization.
- **MCP Integration**: Full Model Context Protocol server for AI assistant integration

## Utility Scripts

The project includes standalone utility scripts for common operations:

### Workflow Import Script

Import workflows manually without using MCP tools:

```bash
# Import a specific workflow
python scripts/import_workflows.py --entity ExampleEntity --version 1 --file example_application/resources/workflow/exampleentity/version_1/ExampleEntity.json

# List available workflow files
python scripts/import_workflows.py --list

# Validate a workflow file
python scripts/import_workflows.py --entity ExampleEntity --version 1 --file path/to/workflow.json --validate-only

# Get help
python scripts/import_workflows.py --help
```

This script provides:
- ✅ Workflow validation before import
- ✅ File listing and discovery
- ✅ Comprehensive error handling
- ✅ Support for both relative and absolute paths
- ✅ Detailed success/failure reporting

## Contributing

We welcome contributions! Please see our comprehensive guides:

- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Complete contributor guide with development workflow, code quality standards, and testing requirements
- **[AI_TESTING_GUIDE.md](AI_TESTING_GUIDE.md)** - Specific commands for testing with AI assistants
- **[CYODA_E2E_TESTING_GUIDE.md](CYODA_E2E_TESTING_GUIDE.md)** - End-to-end testing procedures

### Quick Contributor Setup
```bash
git clone <repository-url>
cd mcp-cyoda-quart-app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run code quality checks
python -m black . && python -m isort . && python -m mypy . && python -m flake8 . && python -m bandit -r .

# Run integration tests
python -m pytest tests/integration/test_grpc_handlers_e2e.py -v
```

**Important**: Contributors can edit all code except the `application/` directory, which is reserved for end users.

## Development Installation Guide

For development or if you want to modify the source code:

### 1. Clone the Repository

```bash
git clone <your-repository-URL>
cd quart-client-template
```

### 2. Set Up a Virtual Environment

**Windows:**

```bash
python -m venv venv
venv\Scripts\activate
```

**Unix/MacOS:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Environment Variables

```bash
export CYODA_CLIENT_ID="your-client-id"
export CYODA_CLIENT_SECRET="your-client-secret"
export CYODA_HOST="client-<id>.eu.cyoda.net"
```

### 5. Run the MCP Server

```bash
# Run directly from source
python -m cyoda_mcp

# Or use the standalone runner
python run_mcp_server.py
```

### 6. Build and Test the Package Locally

```bash
# Install build tools
pip install build twine

# Build the package
python -m build

# Install locally for testing
pipx install dist/mcp_cyoda-0.1.2-py3-none-any.whl

# Test the installed package
mcp-cyoda --version
```

## Project Structure Overview

### 1. app_init/

This module contains a service factory responsible for initializing all essential services.

### 2. common/

This module contains boilerplate code for integration with Cyoda. Key components include:

- **auth**: Manages login and refresh token logic (modifications not typically required).
- **config**: Contains constants, environment variables from .env, and enums.
- **exception**: Customize error handling logic as necessary.
- **grpc_client**: Handles integration with the Cyoda gRPC server (modifications usually unnecessary).
- **repository**: Facilitates integration with the Coda REST API (modifications usually unnecessary).
- **service**: Additional services for your application.
- **utils**: Various utility functions.

To interact with Cyoda, use the common/service/entity_service_interface.py, which provides all the necessary methods. To add new integrations with Cyoda, extend the following files:

Interface: You can, but don't have to modify common/service/entity_service_interface.py to define the required service methods. This provides the abstraction layer for Cyoda interaction.

Implementation: You can, but don't have to modify common/service/service.py to implement the methods from the interface. Add business logic for Cyoda integration here.

Repository Interface: The common/repository/crud_repository.py file defines the generic repository interface. Modify only if new operations are needed for Cyoda.

Cyoda Repository: Update common/repository/cyoda/cyoda_repository.py implement the methods from the interface. Modify only if new operations are needed for Cyoda.
crud_repository.py and cyoda_repository.py changes are rare, needed only for significant changes to the data access layer.

Always interact with the service interface, not directly with the repository.

### 3. entity/

The primary module for business logic development. Key files include:

- **workflow.py**: Dispatches gRPC events to your entity upon receipt. Modifications unnecessary.
- **functional_requirements.md**: Describes the application's functional requirements—review this file before making changes.
- **prototype.py**: Contains the initial prototype configuration.

Entities should be defined using the following structure:

- **adding new entity/editing existing entity**:
```
entity/$entity_name/$entity_name.json
```

Define entity data model

Example:

```json
{
    "attribute": "value",
    "my_quality": "quality_value"
}
```

- **adding new entity workflow configuration/editing existing entity workflow configuration**:

```
entity/$entity_name/workflow.json
```

This file defines the workflow configuration using a finite-state machine (FSM) model, which specifies states and transitions between them.

Construct workflow JSON using a typical FSM model.
The FSM json should consist of an ordered dictionary of states. Each state has a dictionary of transitions. Each transition has a next attribute, which identifies the next state.
Each transition may have an action (will map directly to a function).
Action names/condition functions should be the same as functions names in the workflow.py code.
Ideally, there should be one action per transition. If user doesn't specify, derive from transition name.
Always start from an initial state 'none'.
Avoid loops.
If we have multiple transitions from one state we need a condition for each transition to decide which to use.

Example:

```json
{
  "version": "1.0",
  "name": "template_workflow",
  "desc": "Template FSM with structured states, transitions, processors, and criterions",
  "initialState": "none",
  "active": true,
  "states": {
    "none": {
      "transitions": [
        {
          "name": "transition_to_01",
          "next": "state_01"
        }
      ]
    },
    "state_01": {
      "transitions": [
        {
          "name": "transition_to_02",
          "next": "state_02",
          "manual": true,
          "processors": [
            {
              "name": "example_function_name",
              "executionMode": "ASYNC_NEW_TX",
              "config": {
                "attachEntity": true,
                "calculationNodesTags": "cyoda_application",
                "responseTimeoutMs": 3000,
                "retryPolicy": "FIXED"
              }
            }
          ]
        }
      ]
    },
    "state_02": {
      "transitions": [
        {
          "name": "transition_with_criterion_simple",
          "next": "state_criterion_check_01",
          "processors": [
            {
              "name": "example_function_name",
              "executionMode": "ASYNC_NEW_TX",
              "config": {
                "attachEntity": true,
                "calculationNodesTags": "cyoda_application",
                "responseTimeoutMs": 3000,
                "retryPolicy": "FIXED"
              }
            }
          ],
          "criterion": {
            "type": "function",
            "function": {
              "name": "example_function_name_returns_bool",
              "config": {
                "attachEntity": true,
                "calculationNodesTags": "cyoda_application",
                "responseTimeoutMs": 5000,
                "retryPolicy": "FIXED"
              }
            }
          }
        }
      ]
    },
    "state_criterion_check_01": {
      "transitions": [
        {
          "name": "transition_with_criterion_group",
          "next": "state_terminal",
          "criterion": {
            "type": "group",
            "operator": "AND",
            "conditions": [
              {
                "type": "simple",
                "jsonPath": "$.sampleFieldA",
                "operation": "EQUALS",
                "value": "template_value_01"
              }
            ]
          }
        }
      ]
    },
    "state_terminal": {
      "transitions": []
    }
  }
}
```

Available operator values:
- `AND`
- `OR`
- `NOT`

Available operatorType values:
EQUALS, NOT_EQUAL, IS_NULL, NOT_NULL, GREATER_THAN, GREATER_OR_EQUAL, LESS_THAN, LESS_OR_EQUAL,
CONTAINS, STARTS_WITH, ENDS_WITH, NOT_CONTAINS, NOT_STARTS_WITH, NOT_ENDS_WITH, MATCHES_PATTERN, BETWEEN, BETWEEN_INCLUSIVE

- **adding new workflow processors code/editing existing workflow processors code**:

The logic for processing workflows is implemented in entity/$entity_name/workflow.py:
Each function name matches action/processor or criteria function name.

```python
async def process_compute_status(entity: dict):
    final_result = do_some_user_request(...)
    entity["final_result"] = final_result
    entity["workflowProcessed"] = True
```

Example for condition functions:

```python
async def function_name(entity: dict) -> bool:
    return True
```

Please make sure all action functions and condition functions for the newly generated workflow are implemented in the code.
Generate new action functions and condition functions if necessary and remove any 'orphan' functions.
Processes should take only one argument entity.

### 4. helm/

This folder contains deployment configurations for the Cyoda cloud. **Do not modify** unless you are certain of what you're doing.

### 5. routes/

The routes/routes.py file contains the core API logic. Feel free to improve this code, but always preserve the existing structure and business logic.

## API Integration Guidelines

### 1. Adding an Item

```python
id = await entity_service.add_item(
    token=cyoda_auth_service,
    entity_model="{entity_name}",
    entity_version=ENTITY_VERSION,
    entity=data
)
```

### 2. Retrieving an Item

```python
await entity_service.get_item(...)
await entity_service.get_items(...)
await entity_service.get_items_by_condition(...)
```

### 3. Updating an Item

```python
await entity_service.update_item(...)
```

### 4. Deleting an Item

```python
await entity_service.delete_item(...)
```

Important: Ensure that the `id` is treated as a string. If numeric values were previously used, now use a string as the technical ID.

For managing entity versions, always use:

```python
from common.config.config import ENTITY_VERSION
```

### Example Condition Format

```json
{
  "cyoda": {
    "type": "group",
    "operator": "AND",
    "conditions": [
      {
        "jsonPath": "$.my_attribute",
        "operatorType": "EQUALS",
        "value": false,
        "type": "simple"
      },
      {
        "jsonPath": "$.my_attribute",
        "operatorType": "GREATER_THAN",
        "value": 1,
        "type": "simple"
      }
    ]
  }
}
```

## Response Format

### 1. Adding an Item

```python
id = await entity_service.add_item(
    token=cyoda_auth_service,
    entity_model="{entity_name}",
    entity_version=ENTITY_VERSION,
    entity=data
)
return id  # Return the id, without retrieving the result immediately.
```

### 2. Retrieving an Item

```python
await entity_service.get_item(
    token=cyoda_auth_service,
    entity_model="{entity_name}",
    entity_version=ENTITY_VERSION,
    technical_id=<id>
)
await entity_service.get_items(...)
await entity_service.get_items_by_condition(...)
```

### 3. Updating an Item

```python
await entity_service.update_item(
    token=cyoda_auth_service,
    entity_model="{entity_name}",
    entity_version=ENTITY_VERSION,
    entity=data,
    technical_id=id,
    meta={}
)
```

### 4. Deleting an Item

```python
await entity_service.delete_item(
    token=cyoda_auth_service,
    entity_model="{entity_name}",
    entity_version=ENTITY_VERSION,
    technical_id=id,
    meta={}
)
```

## Logging Example

```python
import logging

def get_services():
    """Lazy import services to avoid circular import issues."""
    from app_init.app_init import entity_service, cyoda_auth_service
    return entity_service, cyoda_auth_service

entity_service, cyoda_auth_service = get_services()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.exception(e)
```
