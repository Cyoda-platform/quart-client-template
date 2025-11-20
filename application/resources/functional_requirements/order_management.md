# Order Management Functional Requirements

## Overview

The Order Management system handles the complete lifecycle of customer orders, from creation through delivery or cancellation. The system automatically calculates order totals and manages state transitions through the OrderProcessing workflow.

## Entity Definition

### Order Entity

The Order entity represents a customer order with the following fields:

- **id** (string/uuid): Unique order identifier (inherited from CyodaEntity as entity_id)
- **customerId** (string): Customer identifier (required)
- **items** (array): List of order items, each containing:
  - **productId** (string): Product identifier (required)
  - **quantity** (integer): Quantity of the product (required, must be > 0)
  - **price** (number): Price per unit (required, must be >= 0)
- **status** (string): Current order status (required)
- **totalAmount** (number): Total order amount (calculated automatically)
- **createdAt** (string): ISO8601 timestamp of order creation

### Allowed Status Values

- `pending`: Initial order state
- `confirmed`: Order confirmed by customer
- `processing`: Order being processed
- `shipped`: Order has been shipped
- `delivered`: Order delivered to customer
- `cancelled`: Order cancelled

## Workflow Definition - OrderProcessing

### States and Transitions

#### 1. Initial State → Pending
- **Transition**: `create_order` (automatic)
- **Processor**: OrderProcessor (calculates totalAmount)
- **Description**: Creates new order and calculates initial total

#### 2. Pending State
- **update_order** (manual) → Pending
  - Processor: OrderProcessor (recalculates totalAmount)
  - Allows order modifications while pending
- **confirm_order** (manual) → Confirmed
  - Confirms the order for processing
- **cancel_order** (manual) → Cancelled
  - Cancels the order

#### 3. Confirmed State
- **update_order** (manual) → Confirmed
  - Processor: OrderProcessor (recalculates totalAmount)
  - Limited updates allowed after confirmation
- **start_processing** (manual) → Processing
  - Begins order fulfillment
- **cancel_order** (manual) → Cancelled
  - Last chance to cancel before processing

#### 4. Processing State
- **ship_order** (manual) → Shipped
  - Order shipped to customer
- **cancel_order** (manual) → Cancelled
  - Emergency cancellation during processing

#### 5. Shipped State
- **deliver_order** (manual) → Delivered
  - Order successfully delivered

#### 6. Delivered State
- **Final state**: No further transitions

#### 7. Cancelled State
- **Final state**: No further transitions

## Validation Rules

### Order Level Validation
1. **Customer ID**: Must be non-empty string
2. **Items**: Must contain at least one item
3. **Status**: Must be one of the allowed status values

### Item Level Validation
1. **Product ID**: Must be non-empty string
2. **Quantity**: Must be integer greater than 0
3. **Price**: Must be number greater than or equal to 0

### Business Rules
1. Orders can only be cancelled in `pending`, `confirmed`, or `processing` states
2. Order updates that modify items trigger total recalculation
3. Total amount is always calculated as sum of (quantity × price) for all items

## Processor Behavior

### OrderProcessor (calculate_order_total)

**Purpose**: Automatically calculates and updates the totalAmount field based on order items.

**Trigger Conditions**:
- Order creation (`create_order` transition)
- Order updates (`update_order` transition)

**Processing Logic**:
1. Validates that order has items
2. Calculates total as: `sum(item.quantity * item.price for item in items)`
3. Rounds result to 2 decimal places for currency precision
4. Updates the `totalAmount` field
5. Logs calculation details for audit trail

**Configuration**:
- Execution Mode: `ASYNC_NEW_TX`
- Attach Entity: `true`
- Calculation Nodes Tags: `cyoda_application`
- Response Timeout: 3000ms
- Retry Policy: `FIXED`

## API Endpoints

### Basic CRUD Operations

#### Create Order
- **Method**: POST
- **Endpoint**: `/ui/order/`
- **Request Body**:
```json
{
  "customerId": "customer-123",
  "items": [
    {
      "productId": "product-456",
      "quantity": 2,
      "price": 29.99
    }
  ],
  "status": "pending"
}
```
- **Response**: `{"id": "order-uuid"}`

#### Get Order
- **Method**: GET
- **Endpoint**: `/ui/order/{orderId}`
- **Response**: Complete order object with calculated totalAmount

#### Update Order
- **Method**: PUT
- **Endpoint**: `/ui/order/{orderId}`
- **Request Body**: Partial order object with fields to update
- **Response**: `{"id": "order-uuid"}`
- **Note**: Triggers OrderProcessor to recalculate totalAmount

#### Delete Order
- **Method**: DELETE
- **Endpoint**: `/ui/order/{orderId}`
- **Response**: `{"success": true}`

### Workflow Transition Endpoints

#### Confirm Order
- **Method**: POST
- **Endpoint**: `/ui/order/{orderId}/confirm`
- **Triggers**: `confirm_order` transition

#### Cancel Order
- **Method**: POST
- **Endpoint**: `/ui/order/{orderId}/cancel`
- **Triggers**: `cancel_order` transition

#### Start Processing
- **Method**: POST
- **Endpoint**: `/ui/order/{orderId}/process`
- **Triggers**: `start_processing` transition

#### Ship Order
- **Method**: POST
- **Endpoint**: `/ui/order/{orderId}/ship`
- **Triggers**: `ship_order` transition

#### Deliver Order
- **Method**: POST
- **Endpoint**: `/ui/order/{orderId}/deliver`
- **Triggers**: `deliver_order` transition

## Acceptance Criteria

### Order Creation
- ✅ Order created with valid customer ID and items
- ✅ Total amount automatically calculated on creation
- ✅ Order starts in `pending` status
- ✅ Creation timestamp set to current time in ISO8601 format

### Order Updates
- ✅ Items can be modified in `pending` and `confirmed` states
- ✅ Total amount recalculated automatically on item changes
- ✅ Status transitions follow workflow rules
- ✅ Invalid transitions are rejected

### Validation
- ✅ Empty items list rejected
- ✅ Zero or negative quantities rejected
- ✅ Negative prices rejected
- ✅ Invalid status values rejected
- ✅ Empty customer ID rejected

### Total Calculation
- ✅ Total equals sum of (quantity × price) for all items
- ✅ Total rounded to 2 decimal places
- ✅ Calculation triggered on create and update
- ✅ Calculation logged for audit trail

### Workflow Compliance
- ✅ All transitions follow defined workflow
- ✅ Manual transitions require explicit triggers
- ✅ Automatic transitions execute on entity creation
- ✅ Final states (delivered, cancelled) have no outgoing transitions

## Error Handling

### Validation Errors
- Return HTTP 400 with detailed validation messages
- Log validation failures for monitoring

### Processing Errors
- Return HTTP 500 for processor failures
- Implement retry logic for transient failures
- Log all processing errors with context

### Workflow Errors
- Return HTTP 409 for invalid state transitions
- Provide clear error messages about allowed transitions
- Log workflow violations for audit

## Performance Considerations

### Total Calculation
- Processor executes asynchronously to avoid blocking
- Calculation complexity is O(n) where n is number of items
- Consider caching for orders with many items

### Database Operations
- Use appropriate indexes on customerId and status fields
- Consider pagination for order listing endpoints
- Implement soft deletes for audit trail

## Security Considerations

### Access Control
- Validate customer ownership of orders
- Implement role-based access for administrative operations
- Audit all order modifications

### Data Validation
- Sanitize all input data
- Validate numeric ranges for prices and quantities
- Prevent injection attacks in string fields
