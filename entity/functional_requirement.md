```markdown
# Functional Requirements for Cat Orders Events Application

## API Endpoints

### 1. POST /orders/events  
**Description:** Receive and process cat order events (e.g., new order created, updated, canceled).  
**Request Body (JSON):**  
```json
{
  "event_type": "string",    // "created", "updated", "canceled"
  "order_id": "string",
  "cat_type": "string",      // e.g. "siamese", "persian"
  "quantity": "integer",
  "price": "number",
  "timestamp": "string"      // ISO 8601 datetime
}
```  
**Response (JSON):**  
```json
{
  "status": "success",
  "message": "Event processed",
  "order_id": "string"
}
```

---

### 2. GET /orders/{order_id}  
**Description:** Retrieve the current state/details of a specific order by ID.  
**Response (JSON):**  
```json
{
  "order_id": "string",
  "cat_type": "string",
  "quantity": "integer",
  "price": "number",
  "status": "string",         // e.g., "created", "updated", "canceled"
  "last_updated": "string"    // ISO 8601 datetime
}
```

---

### 3. GET /orders  
**Description:** Retrieve the list of all orders with their current status.  
**Response (JSON):**  
```json
[
  {
    "order_id": "string",
    "cat_type": "string",
    "quantity": "integer",
    "price": "number",
    "status": "string",
    "last_updated": "string"
  },
  ...
]
```

---

## Business Logic Notes
- All event processing (validation, state updates, possible external data calls) happens in the `POST /orders/events` endpoint.
- GET endpoints are read-only and return stored state only.

---

## User-App Interaction Sequence Diagram

```mermaid
sequenceDiagram
    participant User
    participant App
    User->>App: POST /orders/events (new order event)
    App->>App: Validate & process event
    App-->>User: 200 OK (event processed)

    User->>App: GET /orders/{order_id}
    App-->>User: Return order details

    User->>App: GET /orders
    App-->>User: Return list of orders
```

---

## User Journey Diagram

```mermaid
graph TD
    A[User submits cat order event] --> B[App processes event]
    B --> C[Order stored/updated]
    C --> D[User requests order info]
    D --> E[App returns current order data]
    C --> F[User requests all orders]
    F --> G[App returns all orders list]
```
```