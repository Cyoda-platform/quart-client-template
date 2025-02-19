Based on the provided JSON design document, I will create a Mermaid entity-relationship (ER) diagram and a class diagram for the "company" entity, as well as a flowchart for a hypothetical workflow related to the "company" entity.

### Mermaid ER Diagram

```mermaid
erDiagram
    COMPANY {
        string name
        string address
        string contact_number
    }
```

### Mermaid Class Diagram

```mermaid
classDiagram
    class Company {
        +string name
        +string address
        +string contact_number
    }
```

### Flowchart for Company Workflow

Assuming a simple workflow for managing a company (e.g., adding a new company), here is a flowchart:

```mermaid
flowchart TD
    A[Start] --> B[Input Company Details]
    B --> C{Is Input Valid?}
    C -- Yes --> D[Save Company to Database]
    C -- No --> E[Show Error Message]
    E --> B
    D --> F[End]
```

### Summary

- The ER diagram represents the structure of the "company" entity with its attributes.
- The class diagram illustrates the "Company" class with its properties.
- The flowchart outlines a basic workflow for adding a new company, including validation and error handling.

If you have any specific workflows or additional entities to include, please let me know!