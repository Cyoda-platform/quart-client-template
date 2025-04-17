```markdown
# Functional Requirements for Hello World App

## API Endpoints

### 1. GET /hello
- **Description**: Returns a simple "Hello, World!" message.
- **Request Format**: 
  - No request body.
- **Response Format**: 
  - **200 OK**
    ```json
    {
      "message": "Hello, World!"
    }
    ```

### 2. POST /greet
- **Description**: Accepts a name and returns a personalized greeting.
- **Request Format**: 
  ```json
  {
    "name": "string"
  }
  ```
- **Response Format**: 
  - **200 OK**
    ```json
    {
      "message": "Hello, {name}!"
    }
    ```
  - **400 Bad Request** (if name is missing or invalid)
    ```json
    {
      "error": "Name is required."
    }
    ```

## User-App Interaction Diagram

```mermaid
sequenceDiagram
    participant User
    participant App

    User->>App: GET /hello
    App-->>User: 200 OK {"message": "Hello, World!"}

    User->>App: POST /greet {"name": "Alice"}
    App-->>User: 200 OK {"message": "Hello, Alice!"}

    User->>App: POST /greet {"name": ""}
    App-->>User: 400 Bad Request {"error": "Name is required."}
```
```