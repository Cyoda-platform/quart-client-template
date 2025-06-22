```markdown
# Functional Requirements for Cyoda Python Quart Application

## API Endpoints

### 1. POST `/process`
**Purpose:**  
- Accept input data  
- Perform business logic including external data retrieval or calculations  
- Trigger Cyoda entity workflows  
- Store processing results  

**Request Format (JSON):**  
```json
{
  "inputData": { /* arbitrary input structure */ }
}
```

**Response Format (JSON):**  
```json
{
  "processId": "string",        // Unique identifier for the processing instance
  "status": "processing|completed|failed"
}
```

---

### 2. GET `/result/<processId>`
**Purpose:**  
- Retrieve results of a previously processed request by `processId`  
- Read-only endpoint returning application results only  

**Response Format (JSON):**  
```json
{
  "processId": "string",
  "resultData": { /* output data structure */ },
  "status": "completed|failed"
}
```

---

## Business Logic Notes

- All external data retrieval and calculations are executed within the POST `/process` endpoint.  
- The GET `/result/<processId>` endpoint only returns stored results, no external calls.  
- POST `/process` triggers Cyoda entity workflows driven by the input event.  
- The entity’s state machine manages workflow execution and result generation.

---

## User-App Interaction Sequence Diagram

```mermaid
sequenceDiagram
    participant User
    participant App
    participant CyodaEntity
    participant ExternalDataSource

    User->>App: POST /process (inputData)
    App->>CyodaEntity: Trigger workflow with inputData
    CyodaEntity->>ExternalDataSource: Request external data
    ExternalDataSource-->>CyodaEntity: Return external data
    CyodaEntity->>App: Workflow completes with resultData
    App-->>User: Return processId and status

    User->>App: GET /result/{processId}
    App-->>User: Return resultData and status
```

---

## Alternative User Journey (Error Handling)

```mermaid
sequenceDiagram
    participant User
    participant App
    participant CyodaEntity

    User->>App: POST /process (inputData)
    App->>CyodaEntity: Trigger workflow
    CyodaEntity-->>App: Workflow error/failure
    App-->>User: Return processId and status=failed

    User->>App: GET /result/{processId}
    App-->>User: Return failure details
```
```
