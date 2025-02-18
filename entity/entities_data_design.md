Based on the provided JSON design document, here are the Mermaid diagrams for the entities and workflows.

### Entity-Relationship (ER) Diagram

```mermaid
erDiagram
    SUBSCRIBER {
        int subscriber_id PK
        string name
        string email
    }
    
    SEND_FACT {
        string fact
    }
    
    CAT_FACT {
        string fact
    }
    
    SUBSCRIBER_COUNT {
        int total_subscribers
    }

    SUBSCRIBER ||--o{ SEND_FACT : sends
    SUBSCRIBER ||--o{ CAT_FACT : receives
    SUBSCRIBER_COUNT ||--o{ SUBSCRIBER : counts
```

### Class Diagram

```mermaid
classDiagram
    class Subscriber {
        +int subscriber_id
        +string name
        +string email
    }

    class SendFact {
        +string fact
    }

    class CatFact {
        +string fact
    }

    class SubscriberCount {
        +int total_subscribers
    }

    Subscriber "1" -- "0..*" SendFact : sends
    Subscriber "1" -- "0..*" CatFact : receives
    SubscriberCount "1" -- "0..*" Subscriber : counts
```

### Flow Chart for Each Workflow

1. **Subscriber Workflow**

```mermaid
flowchart TD
    A[Start] --> B[Subscriber Sign Up]
    B --> C[Store Subscriber Data]
    C --> D[Send Welcome Email]
    D --> E[End]
```

2. **Fact Sending Workflow**

```mermaid
flowchart TD
    A[Start] --> B[Select Subscriber]
    B --> C[Choose Fact to Send]
    C --> D[Send Fact to Subscriber]
    D --> E[Log Sent Fact]
    E --> F[End]
```

3. **Subscriber Count Update Workflow**

```mermaid
flowchart TD
    A[Start] --> B[Get Current Subscriber Count]
    B --> C[Update Subscriber Count]
    C --> D[Notify Admin]
    D --> E[End]
```

These diagrams represent the entities and their relationships, as well as the workflows based on the provided JSON design document.