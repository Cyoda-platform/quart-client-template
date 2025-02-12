Based on the provided JSON design document, here are the Mermaid entity-relationship (ER) diagrams, class diagrams for each entity, and flow charts for each workflow.

### ER Diagram

```mermaid
erDiagram
    CROCODILES {
        int id PK
        string name
        string sex
        date date_of_birth
        int age
    }

    CROCODILES_FILTER {
        string name
        string sex
        int age_min
        int age_max
    }

    CROCODILES ||--o{ CROCODILES_FILTER : filters
```

### Class Diagram

```mermaid
classDiagram
    class Crocodile {
        +int id
        +string name
        +string sex
        +date date_of_birth
        +int age
    }

    class CrocodilesFilter {
        +string name
        +string sex
        +int age_min
        +int age_max
    }
```

### Flow Chart

Since the JSON does not specify a particular workflow, I will create a generic flow chart that could represent a workflow for filtering crocodiles based on the provided filter criteria.

```mermaid
flowchart TD
    A[Start] --> B[Input Filter Criteria]
    B --> C{Is Name Provided?}
    C -- Yes --> D[Apply Name Filter]
    C -- No --> E[Skip Name Filter]
    D --> F{Is Sex Provided?}
    E --> F
    F -- Yes --> G[Apply Sex Filter]
    F -- No --> H[Skip Sex Filter]
    G --> I{Is Age Range Provided?}
    H --> I
    I -- Yes --> J[Apply Age Range Filter]
    I -- No --> K[Skip Age Range Filter]
    J --> L[Retrieve Filtered Crocodiles]
    K --> L
    L --> M[Display Results]
    M --> N[End]
```

These diagrams and flowcharts represent the entities and their relationships as well as a potential workflow for filtering crocodiles based on the criteria provided in the JSON document.