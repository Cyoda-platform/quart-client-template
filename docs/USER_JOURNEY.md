# Complete User Journey: From Setup to Workflow Execution

This document explains how all components work together seamlessly from initial setup through entity creation, workflow execution, and processor invocation.

## 1. Initial Setup Phase

### User Sets Environment Variables
```bash
export CYODA_CLIENT_ID="your-client-id"
export CYODA_CLIENT_SECRET="your-client-secret"
export CYODA_HOST="client-<id>.eu.cyoda.net"
```

### Application Starts
- **app.py** initializes on startup
- Services are initialized (authentication, gRPC client, processor manager)
- **gRPC streaming connection** is established with Cyoda platform
- Application listens for incoming events from Cyoda

## 2. Entity & Workflow Definition Phase

### Developer Defines Entity Structure
```
application/entity/order/version_1/
├── order.json          # Entity data model
└── workflow.json       # Finite-state machine definition
```

### Developer Implements Workflow Logic
```
application/entity/order/
├── workflow.py         # Processor and criteria functions
```

### Deploy to Cyoda
Using MCP tools or scripts:
```bash
python scripts/import_workflows.py --entity Order --version 1 --file application/entity/order/version_1/workflow.json
```

Workflows are now registered in Cyoda platform.

## 3. Data Ingestion Phase

### User Creates Entity via REST API
```bash
POST /api/orders
{
  "order_id": "ORD-123",
  "customer": "John Doe",
  "amount": 1000,
  "status": "pending"
}
```

### Application Route Handler
- Route receives request in `application/routes/orders.py`
- Validates data using Pydantic models
- Calls `entity_service.save()` to persist entity

### Entity Persisted to Cyoda
- REST API sends entity to Cyoda platform
- Cyoda assigns technical UUID (e.g., `abc-123-def`)
- Entity stored with initial workflow state

## 4. Workflow Trigger Phase

### Cyoda Detects State Change
- Entity is now persisted in Cyoda
- Workflow engine evaluates initial state transitions
- Cyoda sends **gRPC CloudEvent** to calculation node

### gRPC Event Received
- **gRPC facade** receives CloudEvent from Cyoda
- Event is routed through middleware chain
- **EventRouter** determines handler type

## 5. Processor Execution Phase

### Two Types of gRPC Events

#### A. Criteria Calculation Request
```
Event Type: CRITERIA_CALC_REQUEST
├─ Criteria Name: "OrderValidationCriterion"
├─ Entity Data: {...}
└─ Entity ID: "abc-123-def"
```

**CriteriaCalcRequestHandler** processes:
1. Deserializes entity data from gRPC payload
2. Creates entity object using factory
3. Calls `processor_manager.check_criteria("OrderValidationCriterion", entity)`
4. Executes matching function in `application/entity/order/workflow.py`:
   ```python
   async def OrderValidationCriterion(entity: CyodaEntity) -> bool:
       return entity.amount > 0 and entity.customer is not None
   ```
5. Returns boolean result to Cyoda
6. Cyoda uses result to decide workflow transition

#### B. Processor Calculation Request
```
Event Type: CALC_REQUEST
├─ Processor Name: "OrderProcessor"
├─ Entity Data: {...}
└─ Entity ID: "abc-123-def"
```

**CalcRequestHandler** processes:
1. Deserializes entity data from gRPC payload
2. Creates entity object using factory
3. Calls `processor_manager.process_entity("OrderProcessor", entity)`
4. Executes matching processor in `application/entity/order/workflow.py`:
   ```python
   async def OrderProcessor(entity: CyodaEntity) -> CyodaEntity:
       # Enrich entity with processed data
       entity.processed_amount = entity.amount * 1.1  # Add tax
       entity.processed_at = datetime.now()
       return entity
   ```
5. Returns modified entity to Cyoda
6. Cyoda updates entity with new data

## 6. Workflow State Progression

### Workflow Definition (workflow.json)
```json
{
  "states": {
    "initial_state": {
      "transitions": [
        {
          "name": "create",
          "next": "created",
          "manual": false
        }
      ]
    },
    "created": {
      "transitions": [
        {
          "name": "validate",
          "next": "validated",
          "criterion": {
            "type": "function",
            "function": {
              "name": "OrderValidationCriterion"
            }
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
            {
              "name": "OrderProcessor",
              "executionMode": "SYNC"
            }
          ]
        }
      ]
    }
  }
}
```

### Execution Flow
1. Entity created → State: `initial_state`
2. Cyoda triggers `create` transition → State: `created`
3. Cyoda evaluates `OrderValidationCriterion` via gRPC
   - If true → State: `validated`
   - If false → State remains `created`
4. Cyoda executes `OrderProcessor` via gRPC
   - Processor enriches entity
   - State: `processed`

## 7. Complete Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ USER / APPLICATION                                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
                   REST API Request
                   (POST /api/orders)
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ APPLICATION (Calculation Node)                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Route Handler (orders.py)                               │ │
│ │ - Validate request                                      │ │
│ │ - Call entity_service.save()                            │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          ↓
                   REST API Call
                   (Save to Cyoda)
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ CYODA PLATFORM                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Entity Storage                                          │ │
│ │ - Persist entity with UUID                             │ │
│ │ - Initialize workflow state                            │ │
│ └─────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Workflow Engine                                         │ │
│ │ - Evaluate state transitions                           │ │
│ │ - Trigger criteria checks                              │ │
│ │ - Invoke processors                                    │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          ↓
                   gRPC CloudEvent
                   (CRITERIA_CALC_REQUEST)
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ APPLICATION (Calculation Node)                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ gRPC Facade                                             │ │
│ │ - Receive CloudEvent                                   │ │
│ │ - Route to handler                                     │ │
│ └─────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ CriteriaCalcRequestHandler                              │ │
│ │ - Deserialize entity                                   │ │
│ │ - Call processor_manager.check_criteria()              │ │
│ └─────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Processor Manager                                       │ │
│ │ - Find criteria function                               │ │
│ │ - Execute: OrderValidationCriterion(entity)            │ │
│ └─────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Workflow Logic (workflow.py)                            │ │
│ │ - Run business logic                                   │ │
│ │ - Return boolean result                                │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          ↓
                   gRPC Response
                   (CRITERIA_CALC_RESPONSE)
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ CYODA PLATFORM                                              │
│ - Receive criteria result                                   │
│ - Update workflow state based on result                     │
│ - Trigger next transition (if applicable)                   │
│ - Send next gRPC event (CALC_REQUEST for processor)         │
└─────────────────────────────────────────────────────────────┘
                          ↓
                   gRPC CloudEvent
                   (CALC_REQUEST)
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ APPLICATION (Calculation Node)                              │
│ - CalcRequestHandler receives event                         │
│ - Calls processor_manager.process_entity()                  │
│ - Executes: OrderProcessor(entity)                          │
│ - Returns enriched entity                                   │
└─────────────────────────────────────────────────────────────┘
                          ↓
                   gRPC Response
                   (CALC_RESPONSE)
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ CYODA PLATFORM                                              │
│ - Receive processed entity                                  │
│ - Update entity with new data                              │
│ - Update workflow state                                    │
│ - Continue workflow execution                              │
└─────────────────────────────────────────────────────────────┘
```

## Key Components Working Together

| Component | Role |
|-----------|------|
| **REST API Routes** | Entry point for data ingestion |
| **Entity Service** | Persists entities to Cyoda |
| **gRPC Facade** | Maintains bidirectional streaming connection |
| **Event Router** | Routes incoming gRPC events to handlers |
| **Handlers** | Process criteria and processor requests |
| **Processor Manager** | Discovers and executes business logic |
| **Workflow Functions** | Custom criteria and processor implementations |
| **Cyoda Platform** | Orchestrates workflow state machine |

## Summary

The system creates a seamless loop:
1. **User ingests data** via REST API
2. **Application persists** entity to Cyoda
3. **Cyoda triggers** workflow via gRPC
4. **Application executes** business logic (criteria/processors)
5. **Application returns** results to Cyoda
6. **Cyoda updates** entity state and continues workflow
7. **Loop repeats** until workflow completes

All components are loosely coupled through gRPC, allowing the application to scale independently while maintaining real-time synchronization with the Cyoda platform.

