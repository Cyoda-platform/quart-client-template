# Architecture Overview: How Everything Works Together

## The Big Picture

This is a **Cyoda Calculation Node** - a specialized application that acts as a bridge between users and the Cyoda platform. It:

1. **Receives data** from users via REST APIs
2. **Persists entities** to the Cyoda platform
3. **Executes business logic** when Cyoda triggers workflow events
4. **Returns results** to Cyoda for workflow progression

## Three Layers of Integration

### Layer 1: User-Facing REST API
- **Location**: `application/routes/`
- **Purpose**: Accept data from users/external systems
- **Example**: `POST /api/orders` creates a new order entity
- **Technology**: Quart (async Python web framework)

### Layer 2: Cyoda Integration (REST)
- **Location**: `common/repository/cyoda/`
- **Purpose**: Persist entities to Cyoda platform
- **Technology**: REST API calls to Cyoda backend
- **Flow**: Route handler → Entity Service → Repository → Cyoda

### Layer 3: Workflow Execution (gRPC)
- **Location**: `common/grpc_client/`
- **Purpose**: Receive workflow events and execute business logic
- **Technology**: gRPC bidirectional streaming
- **Flow**: Cyoda → gRPC Event → Handler → Processor Manager → Business Logic

## Key Architectural Patterns

### 1. Entity Factory Pattern
**Problem**: Cyoda sends generic entity data; we need type-safe objects
**Solution**: `entity_factory.py` creates typed entity objects
```python
entity = create_entity("Order", data)  # Returns Order or CyodaEntity
```

### 2. Processor Manager Pattern
**Problem**: How do we discover and execute business logic functions?
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
```python
entity_service = services.entity_service
processor_manager = services.processor_manager
```

## Data Flow: Step by Step

### Step 1: User Creates Entity
```
User → REST API (POST /api/orders) → Route Handler
```

### Step 2: Application Persists Entity
```
Route Handler → entity_service.save() → Cyoda REST API
Cyoda assigns UUID and initializes workflow state
```

### Step 3: Cyoda Triggers Workflow
```
Cyoda Workflow Engine → gRPC CloudEvent → Application
```

### Step 4: Application Executes Business Logic
```
gRPC Event → Event Router → Handler → Processor Manager → 
Workflow Function (criteria or processor) → Business Logic
```

### Step 5: Application Returns Results
```
Business Logic Result → gRPC Response → Cyoda
```

### Step 6: Cyoda Updates Entity and Continues
```
Cyoda updates entity state → Triggers next workflow event → Loop
```

## Component Responsibilities

| Component | Responsibility |
|-----------|-----------------|
| **Routes** | Accept user requests, validate input |
| **Entity Service** | Persist/retrieve entities from Cyoda |
| **Repository** | Low-level Cyoda API communication |
| **gRPC Facade** | Maintain streaming connection with Cyoda |
| **Event Router** | Route incoming events to handlers |
| **Handlers** | Process specific event types |
| **Processor Manager** | Discover and execute business logic |
| **Workflow Functions** | Custom criteria and processor logic |
| **Entity Models** | Type-safe entity representations |

## Configuration & Initialization

### Startup Sequence
1. **app.py** starts
2. **services.py** initializes all services
3. **gRPC facade** establishes streaming connection
4. **Processor manager** discovers all processors and criteria
5. Application ready to receive requests

### Environment Variables
```bash
CYODA_CLIENT_ID      # Authentication
CYODA_CLIENT_SECRET  # Authentication
CYODA_HOST          # Cyoda platform address
GRPC_ADDRESS        # gRPC server address
```

## Workflow Definition Structure

### workflow.json (Cyoda Platform)
Defines the state machine:
```json
{
  "states": {
    "initial_state": { "transitions": [...] },
    "created": { "transitions": [...] },
    "validated": { "transitions": [...] }
  }
}
```

### workflow.py (Application)
Implements the business logic:
```python
async def OrderValidationCriterion(entity: CyodaEntity) -> bool:
    return entity.amount > 0

async def OrderProcessor(entity: CyodaEntity) -> CyodaEntity:
    entity.processed_amount = entity.amount * 1.1
    return entity
```

## Execution Modes

### Synchronous (SYNC)
- Processor executes immediately
- Response sent back to Cyoda
- Workflow waits for completion

### Asynchronous (ASYNC_NEW_TX)
- Processor executes in background
- Cyoda continues workflow
- New transaction for processor

### Asynchronous Same Transaction (ASYNC_SAME_TX)
- Processor executes in background
- Same transaction context
- Useful for related operations

## Error Handling

### Validation Errors
- Caught at route level
- Return 400 Bad Request

### Processing Errors
- Caught in handlers
- Entity marked as FAILED
- Error logged and returned to Cyoda

### Connection Errors
- gRPC facade handles reconnection
- Automatic retry with backoff

## Scalability Considerations

### Horizontal Scaling
- Multiple instances can run
- Each maintains gRPC connection to Cyoda
- Cyoda distributes events based on tags

### Vertical Scaling
- Async/await for efficient I/O
- Non-blocking processor execution
- Connection pooling for Cyoda API

## Security

### Authentication
- JWT tokens for Cyoda API
- Token refresh handled automatically
- Credentials from environment variables

### Data Validation
- Pydantic models validate all input
- Type hints throughout codebase
- gRPC message validation

## Monitoring & Logging

### Key Metrics
- Entity creation/update/delete counts
- Processor execution times
- gRPC event processing latency
- Error rates

### Logging
- Structured logging throughout
- Request/response logging
- Error stack traces
- Performance metrics

## See Also

- **[USER_JOURNEY.md](USER_JOURNEY.md)** - Detailed step-by-step user journey
- **[../README.md](../README.md)** - Project overview
- **[../cyoda_mcp/README.md](../cyoda_mcp/README.md)** - MCP server documentation

