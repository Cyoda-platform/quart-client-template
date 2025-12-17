# How Everything Works Together: Complete System Explanation

## The Core Concept

This is a **Cyoda Calculation Node** - a specialized application that acts as a bridge between users and the Cyoda platform. It creates a seamless loop where:

1. **Users ingest data** via REST APIs
2. **Application persists** entities to Cyoda
3. **Cyoda orchestrates** workflows via gRPC
4. **Application executes** business logic
5. **Results flow back** to Cyoda
6. **Loop continues** until workflow completes

## The Three Integration Layers

### Layer 1: User-Facing REST API
- **What**: REST endpoints that accept user data
- **Where**: `application/routes/`
- **Example**: `POST /api/orders` creates a new order
- **Technology**: Quart (async Python web framework)

### Layer 2: Cyoda Persistence (REST)
- **What**: Saves entities to Cyoda platform
- **Where**: `common/repository/cyoda/`
- **How**: REST API calls to Cyoda backend
- **Result**: Entity stored with UUID and initial workflow state

### Layer 3: Workflow Execution (gRPC)
- **What**: Receives workflow events and executes business logic
- **Where**: `common/grpc_client/`
- **How**: Bidirectional gRPC streaming connection
- **Result**: Processors and criteria functions execute, results sent back

## The Complete User Journey

### Step 1: User Sets Environment
```bash
export CYODA_CLIENT_ID="your-client-id"
export CYODA_CLIENT_SECRET="your-client-secret"
export CYODA_HOST="client-<id>.eu.cyoda.net"
```

### Step 2: Developer Defines Entities & Workflows
```
application/entity/order/version_1/
├── order.json          # Entity data model
└── workflow.json       # Finite-state machine

application/entity/order/
└── workflow.py         # Processor and criteria functions
```

### Step 3: Deploy Workflows to Cyoda
```bash
python scripts/import_workflows.py --entity Order --version 1 \
  --file application/entity/order/version_1/workflow.json
```

### Step 4: User Creates Entity via REST API
```bash
POST /api/orders
{
  "order_id": "ORD-123",
  "customer": "John Doe",
  "amount": 1000
}
```

### Step 5: Application Persists to Cyoda
- Route handler validates data
- Entity service saves to Cyoda
- Cyoda assigns UUID and initializes workflow state

### Step 6: Cyoda Triggers Workflow
- Cyoda sends gRPC CloudEvent: `CRITERIA_CALC_REQUEST`
- Application receives event via gRPC facade
- Event router dispatches to handler

### Step 7: Application Executes Criteria
- Handler deserializes entity from gRPC payload
- Processor manager finds criteria function
- Criteria function executes business logic
- Returns boolean result to Cyoda

### Step 8: Cyoda Updates State & Continues
- Cyoda receives criteria result
- Updates workflow state based on result
- Sends next gRPC event: `CALC_REQUEST` for processor

### Step 9: Application Executes Processor
- Handler deserializes entity
- Processor manager finds processor function
- Processor function enriches entity with calculated data
- Returns modified entity to Cyoda

### Step 10: Cyoda Updates Entity & Continues
- Cyoda receives processed entity
- Updates entity with new data
- Updates workflow state
- Continues workflow or completes

## How Components Link Together

### REST API → Entity Service → Repository → Cyoda
```
User Request
    ↓
Route Handler (validates, converts)
    ↓
Entity Service (orchestrates save)
    ↓
Repository (REST API call)
    ↓
Cyoda Platform (persists entity)
```

### Cyoda → gRPC Facade → Event Router → Handler → Processor Manager → Business Logic
```
Cyoda Workflow Engine
    ↓ (gRPC CloudEvent)
gRPC Facade (streaming connection)
    ↓ (route event)
Event Router (dispatch to handler)
    ↓ (CRITERIA_CALC_REQUEST or CALC_REQUEST)
Handler (deserialize entity)
    ↓ (processor_manager.check_criteria or process_entity)
Processor Manager (auto-discover function)
    ↓ (execute function)
Business Logic (workflow.py)
    ↓ (return result)
Handler (serialize response)
    ↓ (gRPC Response)
Cyoda Platform (update state)
```

## Key Architectural Patterns

### 1. Entity Factory Pattern
**Problem**: Cyoda sends generic data; we need type-safe objects
**Solution**: `create_entity()` creates typed entity objects
```python
entity = create_entity("Order", data)  # Returns Order or CyodaEntity
```

### 2. Processor Manager Pattern
**Problem**: How do we discover and execute business logic?
**Solution**: `ProcessorManager` auto-discovers processors and criteria
```python
await processor_manager.process_entity("OrderProcessor", entity)
await processor_manager.check_criteria("OrderValidationCriterion", entity)
```

### 3. Event Router Pattern
**Problem**: Different gRPC events need different handlers
**Solution**: `EventRouter` routes events to appropriate handlers
```
CRITERIA_CALC_REQUEST → CriteriaCalcRequestHandler
CALC_REQUEST → CalcRequestHandler
```

### 4. Service Locator Pattern
**Problem**: Components need access to shared services
**Solution**: `services.py` provides centralized service initialization

## Workflow Definition Structure

### workflow.json (Cyoda Platform)
Defines the state machine:
```json
{
  "states": {
    "initial_state": {
      "transitions": [
        { "name": "create", "next": "created", "manual": false }
      ]
    },
    "created": {
      "transitions": [
        {
          "name": "validate",
          "next": "validated",
          "criterion": {
            "type": "function",
            "function": { "name": "OrderValidationCriterion" }
          }
        }
      ]
    },
    "validated": {
      "transitions": [
        {
          "name": "process",
          "next": "processed",
          "processors": [
            { "name": "OrderProcessor", "executionMode": "SYNC" }
          ]
        }
      ]
    }
  }
}
```

### workflow.py (Application)
Implements the business logic:
```python
async def OrderValidationCriterion(entity: CyodaEntity) -> bool:
    return entity.amount > 0 and entity.customer is not None

async def OrderProcessor(entity: CyodaEntity) -> CyodaEntity:
    entity.processed_amount = entity.amount * 1.1
    entity.processed_at = datetime.now()
    return entity
```

## Why This Architecture Works

### Separation of Concerns
- **Cyoda**: Manages workflow state machine
- **Application**: Executes business logic
- **gRPC**: Enables real-time communication

### Scalability
- Multiple application instances can run
- Each maintains independent gRPC connection
- Cyoda distributes events based on tags

### Reliability
- Async/await for non-blocking operations
- Error handling at each layer
- Automatic retry mechanisms

### Flexibility
- Easy to add new entities
- Easy to add new processors
- Easy to modify workflows
- Auto-discovery of business logic

## Documentation

For detailed information, see:
- **[docs/USER_JOURNEY.md](docs/USER_JOURNEY.md)** - Step-by-step walkthrough
- **[docs/ARCHITECTURE_OVERVIEW.md](docs/ARCHITECTURE_OVERVIEW.md)** - System design
- **[docs/TECHNICAL_FLOW.md](docs/TECHNICAL_FLOW.md)** - Code-level details
- **[docs/README.md](docs/README.md)** - Documentation index

## Summary

The system creates a **seamless bidirectional integration** where:
- Users push data in via REST APIs
- Application persists to Cyoda
- Cyoda pushes workflow events back via gRPC
- Application executes business logic
- Results flow back to Cyoda
- Workflow progresses automatically

All components work together smoothly through clear interfaces, auto-discovery, and event-driven architecture.

