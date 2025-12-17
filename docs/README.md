# Documentation Index

This directory contains comprehensive documentation about the Cyoda Calculation Node application architecture and user journey.

## Quick Navigation

### 🎯 Start Here
- **[USER_JOURNEY.md](USER_JOURNEY.md)** - Complete walkthrough of how everything works together
  - User sets environment
  - Creates entities via REST API
  - Cyoda triggers workflows via gRPC
  - Application executes business logic
  - Results flow back to Cyoda
  - Includes visual data flow diagram

### 🏗️ Architecture
- **[ARCHITECTURE_OVERVIEW.md](ARCHITECTURE_OVERVIEW.md)** - High-level system design
  - Three layers of integration (REST API, Cyoda REST, gRPC)
  - Key architectural patterns
  - Component responsibilities
  - Configuration and initialization
  - Scalability and security considerations

### 💻 Technical Details
- **[TECHNICAL_FLOW.md](TECHNICAL_FLOW.md)** - Code-level walkthrough
  - Application startup sequence
  - Entity creation flow
  - gRPC event handling
  - Processor manager execution
  - Business logic implementation
  - Complete request-response cycle with code examples

### 📁 Architecture Diagrams
- **[architecture/](architecture/)** - Visual architecture diagrams

## The System in One Sentence

**A bidirectional gRPC-based integration where users ingest data via REST APIs, the application persists entities to Cyoda, Cyoda orchestrates workflows and pushes events back via gRPC, the application executes business logic, and results flow back to Cyoda for state progression.**

## Key Concepts

### Entities
Structured data models managed by Cyoda. Each entity has:
- **Data**: User-defined fields (order_id, customer, amount, etc.)
- **State**: Current workflow state (initial_state, created, validated, processed)
- **UUID**: Technical identifier assigned by Cyoda
- **Metadata**: Version, timestamps, state history

### Workflows
Finite-state machines defined in `workflow.json`:
- **States**: Named states in the workflow
- **Transitions**: Connections between states
- **Criteria**: Boolean conditions that gate transitions
- **Processors**: Functions that enrich/transform entities

### Processors
Custom business logic functions:
- **Criteria Functions**: Return boolean (true/false)
- **Processor Functions**: Return enriched entity
- **Auto-discovered**: Automatically found and registered
- **Async**: All execute asynchronously

### gRPC Events
Cyoda sends two types of events:
- **CRITERIA_CALC_REQUEST**: Evaluate a condition
- **CALC_REQUEST**: Execute a processor

## Component Interaction

```
User
  ↓ (REST API)
Route Handler
  ↓ (entity_service.save)
Entity Service
  ↓ (REST API)
Cyoda Platform
  ↓ (gRPC CloudEvent)
gRPC Facade
  ↓ (route event)
Event Router
  ↓ (dispatch to handler)
Handler (Criteria or Processor)
  ↓ (processor_manager)
Processor Manager
  ↓ (execute function)
Business Logic (workflow.py)
  ↓ (return result)
Handler
  ↓ (gRPC Response)
Cyoda Platform
  ↓ (update state)
Workflow Engine
  ↓ (continue or complete)
```

## File Structure

```
application/
├── entity/
│   ├── order/
│   │   ├── version_1/
│   │   │   ├── order.json          # Entity schema
│   │   │   └── workflow.json       # Workflow definition
│   │   └── workflow.py             # Business logic
│   └── [other entities...]
└── routes/
    └── orders.py                   # REST API endpoints

common/
├── grpc_client/
│   ├── facade.py                   # gRPC connection
│   ├── router.py                   # Event routing
│   └── handlers/
│       ├── criteria_calc.py        # Criteria handler
│       └── calc.py                 # Processor handler
├── processor/
│   └── manager.py                  # Processor discovery & execution
├── service/
│   └── entity_service.py           # Entity operations
└── repository/
    └── cyoda/
        └── cyoda_repository.py     # Cyoda API calls
```

## Getting Started

1. **Read** [USER_JOURNEY.md](USER_JOURNEY.md) to understand the complete flow
2. **Review** [ARCHITECTURE_OVERVIEW.md](ARCHITECTURE_OVERVIEW.md) for system design
3. **Study** [TECHNICAL_FLOW.md](TECHNICAL_FLOW.md) for code-level details
4. **Explore** the codebase with this understanding

## Key Files to Understand

| File | Purpose |
|------|---------|
| `application/app.py` | Application entry point |
| `application/routes/*.py` | REST API endpoints |
| `application/entity/*/workflow.py` | Business logic |
| `common/grpc_client/facade.py` | gRPC connection |
| `common/processor/manager.py` | Processor execution |
| `common/service/entity_service.py` | Entity operations |

## Common Tasks

### Add a New Entity Type
1. Create `application/entity/myentity/version_1/myentity.json`
2. Create `application/entity/myentity/version_1/workflow.json`
3. Create `application/entity/myentity/workflow.py` with processor functions
4. Create REST routes in `application/routes/myentities.py`

### Add a New Processor
1. Create function in `application/entity/*/workflow.py`
2. Function name must match processor name in workflow.json
3. Processor manager auto-discovers it
4. Reference in workflow.json transitions

### Debug a Workflow
1. Check logs in `application/app.py` startup
2. Look for gRPC events in `common/grpc_client/handlers/`
3. Verify processor function in `application/entity/*/workflow.py`
4. Check Cyoda platform for workflow state

## See Also

- **[../README.md](../README.md)** - Project overview
- **[../cyoda_mcp/README.md](../cyoda_mcp/README.md)** - MCP server documentation
- **[../CONTRIBUTING.md](../CONTRIBUTING.md)** - Contribution guidelines

