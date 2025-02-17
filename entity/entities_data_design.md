Based on the provided JSON design document, here are the Mermaid diagrams for the entities and workflows.

### Entity-Relationship (ER) Diagram

```mermaid
erDiagram
    FLIGHT_SEARCH {
        string departureAirport
        string arrivalAirport
        date departureDate
        date returnDate
        PASSENGERS passengers
    }

    PASSENGERS {
        int adults
        int children
        int infants
    }

    FLIGHT_SORT {
        string sortBy
    }

    FLIGHT_FILTER {
        boolean nonStop
        array airlines
    }

    FLIGHT_SEARCH ||--o{ PASSENGERS : contains
    FLIGHT_SEARCH ||--o{ FLIGHT_SORT : sorts
    FLIGHT_SEARCH ||--o{ FLIGHT_FILTER : filters
```

### Class Diagram

```mermaid
classDiagram
    class FlightSearch {
        +string departureAirport
        +string arrivalAirport
        +date departureDate
        +date returnDate
        +Passengers passengers
    }

    class Passengers {
        +int adults
        +int children
        +int infants
    }

    class FlightSort {
        +string sortBy
    }

    class FlightFilter {
        +boolean nonStop
        +array airlines
    }

    FlightSearch --> Passengers
    FlightSearch --> FlightSort
    FlightSearch --> FlightFilter
```

### Flowchart for Flight Search Workflow

```mermaid
flowchart TD
    A[Start Flight Search] --> B[Input Departure Airport]
    B --> C[Input Arrival Airport]
    C --> D[Input Departure Date]
    D --> E[Input Return Date]
    E --> F[Input Passengers Details]
    F --> G[Sort Options]
    G --> H[Filter Options]
    H --> I[Display Search Results]
    I --> J[End]
```

### Flowchart for Flight Sort Workflow

```mermaid
flowchart TD
    A[Start Flight Sort] --> B[Select Sort Criteria]
    B --> C[Sort Flights]
    C --> D[Display Sorted Flights]
    D --> E[End]
```

### Flowchart for Flight Filter Workflow

```mermaid
flowchart TD
    A[Start Flight Filter] --> B[Select Filter Criteria]
    B --> C[Apply Filters]
    C --> D[Display Filtered Flights]
    D --> E[End]
```

These diagrams represent the entities and workflows as specified in the provided JSON design document.