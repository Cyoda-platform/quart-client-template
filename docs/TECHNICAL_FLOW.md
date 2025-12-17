# Technical Flow: Code-Level Walkthrough

## Phase 1: Application Startup

### 1.1 Application Initialization (app.py)
```python
@app.before_serving
async def startup() -> None:
    # Initialize all services
    initialize_services(config)
    
    # Get gRPC client and start streaming
    grpc_client = get_grpc_client()
    _background_task = asyncio.create_task(grpc_client.grpc_stream())
```

### 1.2 Service Initialization (services.py)
```python
def initialize_services(config):
    # Create authentication service
    cyoda_auth_service = CyodaAuthService(config)
    
    # Create entity service
    entity_service = EntityServiceImpl(cyoda_auth_service)
    
    # Create processor manager (auto-discovers processors)
    processor_manager = get_processor_manager([
        "application.processor",
        "application.criterion"
    ])
    
    # Store in global services
    services.entity_service = entity_service
    services.processor_manager = processor_manager
```

### 1.3 gRPC Connection (facade.py)
```python
async def start(self) -> None:
    async with grpc.aio.secure_channel(GRPC_ADDRESS, creds) as channel:
        stub = CloudEventsServiceStub(channel)
        call = stub.startStreaming(self.outbox.event_generator())
        
        async for response in call:
            self._on_event(response)  # Process incoming event
```

## Phase 2: User Creates Entity

### 2.1 REST API Request
```bash
POST /api/orders
{
  "order_id": "ORD-123",
  "customer": "John Doe",
  "amount": 1000
}
```

### 2.2 Route Handler (application/routes/orders.py)
```python
@orders_bp.route("/", methods=["POST"])
async def create_order(data: Order) -> Tuple[Dict[str, Any], int]:
    try:
        # Convert Pydantic model to dict
        entity_data = data.model_dump(by_alias=True)
        
        # Save to Cyoda
        response = await service.save(
            entity=entity_data,
            entity_class="Order",
            entity_version="1"
        )
        
        # Return created entity with UUID
        return _to_entity_dict(response.data), 201
    except Exception as e:
        return {"error": str(e)}, 500
```

### 2.3 Entity Service (common/service/entity_service.py)
```python
async def save(self, entity: Dict[str, Any], entity_class: str, 
               entity_version: str = "1") -> EntityResponse:
    # Call repository to persist
    response = await self.repository.save(
        entity=entity,
        entity_class=entity_class,
        entity_version=entity_version
    )
    
    # Return with metadata (includes technical UUID)
    return EntityResponse(
        data=response.data,
        metadata=EntityMetadata(
            id=response.metadata.id,  # UUID from Cyoda
            state=response.metadata.state
        )
    )
```

### 2.4 Repository (common/repository/cyoda/cyoda_repository.py)
```python
async def save(self, entity: Dict[str, Any], entity_class: str,
               entity_version: str) -> EntityResponse:
    # Send REST API call to Cyoda
    response = await send_cyoda_request(
        cyoda_auth_service=self._cyoda_auth_service,
        method="post",
        path=f"entity/{entity_class}/{entity_version}",
        data=json.dumps(entity)
    )
    
    # Parse response and return
    return EntityResponse.from_api_response(response)
```

## Phase 3: Cyoda Triggers Workflow

### 3.1 Cyoda Sends gRPC Event
```
CloudEvent {
  type: "CRITERIA_CALC_REQUEST"
  id: "event-123"
  text_data: {
    "criteriaName": "OrderValidationCriterion",
    "entityId": "abc-123-def",
    "payload": {
      "data": { "order_id": "ORD-123", "amount": 1000 },
      "meta": { "modelKey": { "name": "Order" } }
    }
  }
}
```

### 3.2 gRPC Facade Receives Event (facade.py)
```python
def _on_event(self, event: CloudEvent) -> None:
    # Process through middleware chain
    asyncio.create_task(self.first_middleware.handle(event))
```

### 3.3 Event Router (router.py)
```python
async def route(self, event: CloudEvent) -> None:
    event_type = event.type
    
    if event_type == "CRITERIA_CALC_REQUEST":
        handler = CriteriaCalcRequestHandler()
    elif event_type == "CALC_REQUEST":
        handler = CalcRequestHandler()
    else:
        handler = DefaultHandler()
    
    response = await handler.handle(event, services)
    await self.outbox.send(response)
```

## Phase 4: Handler Processes Event

### 4.1 Criteria Handler (common/grpc_client/handlers/criteria_calc.py)
```python
async def handle(self, request: CloudEvent, services: Any) -> ResponseSpec:
    data = json.loads(request.text_data)
    criteria_name = data.get("criteriaName")
    
    # Create entity from gRPC payload
    entity = create_entity(
        entity_type="order",
        data=data["payload"]["data"]
    )
    entity.technical_id = data["entityId"]
    
    # Execute criteria check
    matches = await services.processor_manager.check_criteria(
        criteria_name=criteria_name,
        entity=entity
    )
    
    # Return response
    return ResponseSpec(
        response_type="CRITERIA_CALC_RESPONSE",
        data={
            "requestId": data.get("requestId"),
            "entityId": data.get("entityId"),
            "matches": matches
        }
    )
```

### 4.2 Processor Handler (common/grpc_client/handlers/calc.py)
```python
async def handle(self, request: CloudEvent, services: Any) -> ResponseSpec:
    data = json.loads(request.text_data)
    processor_name = data.get("processorName")
    
    # Create entity from gRPC payload
    entity = create_entity(
        entity_type="order",
        data=data["payload"]["data"]
    )
    entity.technical_id = data["entityId"]
    
    # Execute processor
    entity = await services.processor_manager.process_entity(
        processor_name=processor_name,
        entity=entity
    )
    
    # Return response with modified entity
    return ResponseSpec(
        response_type="CALC_RESPONSE",
        data={
            "requestId": data.get("requestId"),
            "entityId": data.get("entityId"),
            "payload": { "data": entity.to_dict() }
        }
    )
```

## Phase 5: Processor Manager Executes Logic

### 5.1 Processor Manager (common/processor/manager.py)
```python
async def check_criteria(self, criteria_name: str, 
                        entity: CyodaEntity) -> bool:
    if criteria_name not in self.criteria:
        raise CriteriaNotFoundError(criteria_name)
    
    criteria = self.criteria[criteria_name]
    return await criteria.check(entity)

async def process_entity(self, processor_name: str,
                        entity: CyodaEntity) -> CyodaEntity:
    if processor_name not in self.processors:
        raise ProcessorNotFoundError(processor_name)
    
    processor = self.processors[processor_name]
    return await processor.process(entity)
```

### 5.2 Auto-Discovery (manager.py)
```python
def _discover_and_register(self) -> None:
    for module_name in self.modules:
        module = importlib.import_module(module_name)
        
        for name, obj in inspect.getmembers(module):
            # Find processor classes
            if inspect.isclass(obj) and issubclass(obj, CyodaProcessor):
                self._register_processor_class(obj)
            
            # Find criteria classes
            if inspect.isclass(obj) and issubclass(obj, CyodaCriteriaChecker):
                self._register_criteria_class(obj)
```

## Phase 6: Business Logic Execution

### 6.1 Criteria Function (application/entity/order/workflow.py)
```python
async def OrderValidationCriterion(entity: CyodaEntity) -> bool:
    """Check if order is valid for processing"""
    try:
        # Cast to typed entity
        order = cast_entity(entity, Order)
        
        # Business logic
        is_valid = (
            order.amount > 0 and
            order.customer is not None and
            len(order.customer) > 0
        )
        
        return is_valid
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return False
```

### 6.2 Processor Function (application/entity/order/workflow.py)
```python
async def OrderProcessor(entity: CyodaEntity) -> CyodaEntity:
    """Process order and enrich with calculated data"""
    try:
        # Cast to typed entity
        order = cast_entity(entity, Order)
        
        # Business logic
        order.processed_amount = order.amount * 1.1  # Add tax
        order.processed_at = datetime.now()
        order.status = "processed"
        
        return order
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        entity.set_state("FAILED")
        return entity
```

## Phase 7: Response Sent Back to Cyoda

### 7.1 Response Serialization
```python
response_spec = ResponseSpec(
    response_type="CALC_RESPONSE",
    data={
        "requestId": "req-123",
        "entityId": "abc-123-def",
        "payload": {
            "data": entity.to_dict()
        }
    }
)
```

### 7.2 gRPC Outbox Sends Response (outbox.py)
```python
async def send(self, response: ResponseSpec) -> None:
    # Convert to CloudEvent
    cloud_event = CloudEvent(
        type=response.response_type,
        id=str(uuid.uuid4()),
        text_data=json.dumps(response.data)
    )
    
    # Add to outbox queue
    await self.queue.put(cloud_event)
```

### 7.3 Cyoda Receives Response
```
Cyoda Platform:
1. Receives CALC_RESPONSE
2. Updates entity with new data
3. Evaluates next workflow transition
4. Sends next gRPC event (if applicable)
5. Loop continues until workflow completes
```

## Complete Request-Response Cycle

```
User Request
    ↓
Route Handler validates & converts
    ↓
Entity Service saves to Cyoda
    ↓
Cyoda persists & initializes workflow
    ↓
Cyoda sends gRPC CRITERIA_CALC_REQUEST
    ↓
gRPC Facade receives event
    ↓
Event Router routes to CriteriaCalcRequestHandler
    ↓
Handler deserializes entity
    ↓
Processor Manager finds criteria function
    ↓
Criteria function executes business logic
    ↓
Handler sends CRITERIA_CALC_RESPONSE
    ↓
Cyoda receives response & updates state
    ↓
Cyoda sends gRPC CALC_REQUEST
    ↓
[Same flow as above for processor]
    ↓
Handler sends CALC_RESPONSE
    ↓
Cyoda receives response & updates entity
    ↓
Workflow continues or completes
```

## Key Takeaways

1. **Bidirectional Communication**: gRPC streaming allows Cyoda to push events
2. **Async Throughout**: All operations are non-blocking
3. **Type Safety**: Entity factory and casting ensure type safety
4. **Auto-Discovery**: Processors and criteria are auto-discovered
5. **Error Handling**: Errors are caught and returned to Cyoda
6. **Scalability**: Multiple instances can run independently

