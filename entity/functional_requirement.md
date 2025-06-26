```markdown
# Weekly Cat Fact Subscription - Functional Requirements

## API Endpoints

### 1. User Subscription

- **POST** `/api/subscribers`
  - Description: Register a new subscriber.
  - Request Body (application/json):
    ```json
    {
      "email": "user@example.com"
    }
    ```
  - Response:
    - 201 Created
    - 400 Bad Request (if email invalid or already subscribed)
  - Business logic: Validate and store subscriber email.

- **GET** `/api/subscribers`
  - Description: Retrieve list of all subscribers.
  - Response Body (application/json):
    ```json
    {
      "subscribers": [
        { "email": "user1@example.com" },
        { "email": "user2@example.com" }
      ],
      "count": 2
    }
    ```

---

### 2. Cat Fact Ingestion and Email Publishing

- **POST** `/api/catfact/send`
  - Description: Trigger ingestion of a new cat fact from external API and send emails to all subscribers.
  - Request Body: Empty or optional control parameters.
  - Response:
    - 200 OK with summary
    ```json
    {
      "catFact": "Cats have five toes on their front paws, but only four toes on their back paws.",
      "emailsSent": 42
    }
    ```
  - Business logic:
    - Fetch cat fact from https://catfact.ninja/fact (external API)
    - Store fact for reporting
    - Send email with fact to all subscribers

- **GET** `/api/catfact/latest`
  - Description: Retrieve the latest cat fact sent.
  - Response Body:
    ```json
    {
      "catFact": "Cats have five toes on their front paws, but only four toes on their back paws.",
      "sentAt": "2024-06-15T12:00:00Z"
    }
    ```

---

### 3. Reporting

- **GET** `/api/report`
  - Description: Get reporting data about subscribers and interactions.
  - Response Body:
    ```json
    {
      "subscriberCount": 42,
      "factsSent": 10,
      "lastSentAt": "2024-06-15T12:00:00Z"
    }
    ```

---

## User-App Interaction Sequence Diagram

```mermaid
sequenceDiagram
    participant User
    participant App
    participant CatFactAPI
    participant EmailService

    User->>App: POST /api/subscribers {email}
    App-->>User: 201 Created

    App->>CatFactAPI: POST /api/catfact/send (internal step)
    CatFactAPI-->>App: Cat fact JSON

    App->>EmailService: Send emails with cat fact
    EmailService-->>App: Email sent confirmations

    App-->>User: 200 OK with summary

    User->>App: GET /api/catfact/latest
    App-->>User: Latest cat fact

    User->>App: GET /api/report
    App-->>User: Reporting data
```

---

## Subscriber Sign-up and Weekly Fact Delivery Flow

```mermaid
flowchart TD
    A[User submits email] --> B[App validates & stores subscriber]
    B --> C[Store subscriber data]

    subgraph Weekly Scheduler
        D[Trigger weekly POST /api/catfact/send]
        D --> E[Fetch cat fact from external API]
        E --> F[Store cat fact]
        F --> G[Send cat fact emails to subscribers]
    end

    G --> H[Update reporting data]
```
```