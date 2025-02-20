Based on the provided JSON design document, I will create a Mermaid ER diagram, class diagram, and a flowchart for the given entity. The entity described is "company."

### Mermaid ER Diagram

```mermaid
erDiagram
    COMPANY {
        string name
        string address
        string registration_number
        int total
    }
```

### Mermaid Class Diagram

```mermaid
classDiagram
    class Company {
        +string name
        +string address
        +string registration_number
        +int total
    }
```

### Flowchart for Company Workflow

Assuming a simple workflow for managing a company, such as creating, updating, and deleting a company, here is a flowchart:

```mermaid
flowchart TD
    A[Start] --> B[Create Company]
    B --> C[Enter Company Details]
    C --> D{Is Details Valid?}
    D -- Yes --> E[Save Company]
    D -- No --> F[Show Error Message]
    F --> C
    E --> G[Update Company]
    G --> H[Enter New Details]
    H --> I{Is New Details Valid?}
    I -- Yes --> J[Save Updated Company]
    I -- No --> K[Show Error Message]
    K --> H
    J --> L[Delete Company]
    L --> M{Confirm Deletion?}
    M -- Yes --> N[Remove Company]
    M -- No --> O[End]
    N --> O
    O --> P[End]
```

This representation captures the entity "company" and outlines a basic workflow for managing company data. If you have specific workflows or additional entities to include, please provide that information for further refinement.