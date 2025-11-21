# Order Management - Developer Guide

This document provides instructions for running and testing the Order management processors locally in the Cyoda Client Application.

## Overview

The Order management system consists of:

- **Order Entity**: Data model representing customer orders
- **Order Processors**: Business logic for create, update, and cancel operations
- **Order Workflow**: State machine managing order lifecycle
- **Validation Utilities**: Input validation and business rule enforcement
- **HTTP Client**: External service integration with retry policies

## Architecture

### Order Entity
- **Location**: `application/entity/order/version_1/order.py`
- **JSON Definition**: `application/resources/entity/order/version_1/order.json`
- **States**: initial_state → created → updated → cancelled

### Order Processors

#### OrderCreateProcessor
- **Location**: `application/processor/order/order_create_processor.py`
- **Purpose**: Handle order creation with status setting and event emission
- **Execution**: SYNC, 5s timeout, FIXED retry policy

#### OrderUpdateProcessor
- **Location**: `application/processor/order/order_update_processor.py`
- **Purpose**: Handle order updates with change application and event emission
- **Execution**: SYNC, 5s timeout, FIXED retry policy

#### OrderCancelProcessor
- **Location**: `application/processor/order/order_cancel_processor.py`
- **Purpose**: Handle order cancellation with external service calls and event emission
- **Execution**: ASYNC_NEW_TX, 10s timeout, EXPONENTIAL retry policy

### Workflow Definition
- **Location**: `application/resources/workflow/orderprocessing/version_1/OrderProcessing.json`
- **States**: initial_state, created, updated, cancelled
- **Transitions**: create, update, cancel

## Local Development Setup

### Prerequisites

1. Python 3.8+ with virtual environment
2. Required dependencies installed
3. Cyoda platform access (or in-memory mode for testing)

### Environment Setup

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables for local testing
export CHAT_REPOSITORY=in_memory  # Use in-memory repository for testing
export APP_DEBUG=true
export APP_HOST=127.0.0.1
export APP_PORT=8000
```

### Running the Application

```bash
# Start the application
python -m application.app

# Or using the main module
python application/app.py
```

The application will start on `http://localhost:8000` with Swagger UI available at `http://localhost:8000/docs`.

## Testing Order Processors

### Unit Tests

Run the unit tests for Order processors:

```bash
# Run all Order processor tests
pytest tests/unit/processors/test_order_processors.py -v

# Run specific test class
pytest tests/unit/processors/test_order_processors.py::TestOrderCreateProcessor -v

# Run with coverage
pytest tests/unit/processors/test_order_processors.py --cov=application.processor.order
```

### Manual Testing

#### 1. Test Order Creation

```bash
# Create a new order
curl -X POST http://localhost:8000/api/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "CUST123",
    "amount": 99.99,
    "description": "Test order"
  }'
```

#### 2. Test Order Update

```bash
# Update an existing order
curl -X PUT http://localhost:8000/api/orders/{order_id} \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 149.99,
    "description": "Updated test order"
  }'
```

#### 3. Test Order Cancellation

```bash
# Cancel an order
curl -X POST http://localhost:8000/api/orders/{order_id}/cancel \
  -H "Content-Type: application/json"
```

### Validation Testing

Test the validation utilities:

```python
from application.utils.order_validation import validate_order_payload, OrderValidationError

# Test valid payload
try:
    valid_payload = {
        "customer_id": "CUST123",
        "amount": 99.99,
        "description": "Test order"
    }
    result = validate_order_payload(valid_payload)
    print("Validation passed:", result)
except OrderValidationError as e:
    print("Validation failed:", e.message)

# Test invalid payload
try:
    invalid_payload = {
        "customer_id": "",  # Invalid: empty
        "amount": -10.0,    # Invalid: negative
        "description": "x" * 600  # Invalid: too long
    }
    result = validate_order_payload(invalid_payload)
except OrderValidationError as e:
    print("Expected validation error:", e.message)
```

### HTTP Client Testing

Test the HTTP client wrapper:

```python
import asyncio
from application.utils.http_client import create_order_cancellation_client

async def test_http_client():
    async with create_order_cancellation_client() as client:
        try:
            # Test with a mock service (will fail but shows retry behavior)
            response = await client.post(
                "http://httpbin.org/status/503",  # Returns 503 to test retries
                json_data={"test": "data"}
            )
            print("Response:", response)
        except Exception as e:
            print("Expected error (demonstrates retry):", str(e))

# Run the test
asyncio.run(test_http_client())
```

## Debugging and Troubleshooting

### Logging

The processors use structured logging. To see detailed logs:

```bash
# Set log level to DEBUG
export LOG_LEVEL=DEBUG

# Run application with verbose logging
python application/app.py
```

### Common Issues

#### 1. Processor Not Found
**Error**: `ProcessorNotFoundError: OrderCreateProcessor`

**Solution**: Ensure processors are in the correct module path and the module is included in the processor discovery configuration in `services/config.py`.

#### 2. Validation Errors
**Error**: `OrderValidationError: Amount must be greater than 0`

**Solution**: Check the input payload against the validation rules in `application/utils/order_validation.py`.

#### 3. Workflow Transition Errors
**Error**: `Invalid transition from state 'cancelled'`

**Solution**: Check the workflow definition in `application/resources/workflow/orderprocessing/version_1/OrderProcessing.json` and ensure the transition is valid for the current state.

### Debugging Workflow Execution

1. **Check Entity State**: Verify the current state of the order entity
2. **Validate Transition**: Ensure the transition is allowed from the current state
3. **Check Processor Configuration**: Verify processor names match exactly in the workflow
4. **Review Logs**: Check application logs for detailed error information

## Code Quality Checks

Run code quality tools before committing:

```bash
# Type checking
mypy application/

# Code formatting
black application/

# Import sorting
isort application/

# Linting
flake8 application/

# Security checks
bandit -r application/
```

## Performance Testing

### Load Testing

Test processor performance under load:

```python
import asyncio
import time
from application.processor.order.order_create_processor import OrderCreateProcessor
from application.entity.order.version_1.order import Order

async def load_test_create_processor():
    processor = OrderCreateProcessor()
    
    # Create test orders
    orders = [
        Order(customer_id=f"CUST{i}", amount=99.99)
        for i in range(100)
    ]
    
    start_time = time.time()
    
    # Process orders concurrently
    tasks = [processor.process(order) for order in orders]
    results = await asyncio.gather(*tasks)
    
    end_time = time.time()
    
    print(f"Processed {len(results)} orders in {end_time - start_time:.2f} seconds")
    print(f"Average time per order: {(end_time - start_time) / len(results):.4f} seconds")

# Run load test
asyncio.run(load_test_create_processor())
```

## Integration with External Services

### Mock External Services

For testing the OrderCancelProcessor with external service calls:

```python
# Create a mock HTTP server for testing
from aiohttp import web
import json

async def mock_cancel_service(request):
    data = await request.json()
    return web.json_response({
        "success": True,
        "cancellation_id": f"CANCEL_{data['order_id']}",
        "message": "Order cancelled successfully"
    })

app = web.Application()
app.router.add_post('/api/orders/cancel', mock_cancel_service)

# Run mock server
web.run_app(app, host='localhost', port=9000)
```

Then update the OrderCancelProcessor to use the mock service URL.

## Deployment Considerations

### Environment Variables

For production deployment, set:

```bash
export CHAT_REPOSITORY=cyoda  # Use Cyoda repository
export CYODA_CLIENT_ID=your_client_id
export CYODA_CLIENT_SECRET=your_client_secret
export CYODA_TOKEN_URL=https://your-cyoda-instance/oauth/token
export APP_DEBUG=false
```

### Monitoring

Monitor processor performance and errors:

- Check application logs for processor execution times
- Monitor external service call success rates
- Track order processing throughput
- Set up alerts for validation errors and processing failures

## Next Steps

1. **Implement Real External Service**: Replace simulated external service calls with actual HTTP endpoints
2. **Add Event Bus Integration**: Replace logging-based events with actual event bus integration
3. **Enhance Validation**: Add more sophisticated business rules and validation logic
4. **Performance Optimization**: Optimize processor performance for high-throughput scenarios
5. **Monitoring and Alerting**: Add comprehensive monitoring and alerting for production use
