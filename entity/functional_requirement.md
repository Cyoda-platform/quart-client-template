```markdown
# Purrfect Pets API - Functional Requirements

## Overview
The app interacts with Petstore API data by invoking external data retrieval or business logic exclusively through POST endpoints. GET endpoints serve cached or processed data for client consumption.

---

## API Endpoints

### 1. POST `/pets/search`
- **Purpose:** Retrieve pet data from the external Petstore API according to search/filter criteria.
- **Request format:**
```json
{
  "type": "string",          // optional, e.g., "dog", "cat"
  "status": "string"         // optional, e.g., "available", "sold"
}
```
- **Response format:**
```json
{
  "pets": [
    {
      "id": "integer",
      "name": "string",
      "type": "string",
      "status": "string",
      "photoUrls": ["string"]
    }
  ]
}
```

---

### 2. POST `/pets/fun-fact`
- **Purpose:** Return a fun random fact related to pets.
- **Request format:** `{ }` (empty JSON)
- **Response format:**
```json
{
  "fact": "string"
}
```

---

### 3. GET `/pets`
- **Purpose:** Retrieve the last searched pets list (cached from previous POST `/pets/search`).
- **Response format:** Same as `/pets/search` response.

---

### 4. GET `/pets/{id}`
- **Purpose:** Retrieve details of a specific pet from the cached data.
- **Response format:**
```json
{
  "id": "integer",
  "name": "string",
  "type": "string",
  "status": "string",
  "photoUrls": ["string"]
}
```

---

## Business Logic Notes
- All external calls to Petstore API happen inside POST endpoints.
- POST `/pets/search` triggers fetching and caching of pet data.
- GET endpoints serve cached data only.
- POST `/pets/fun-fact` serves engaging content without external calls.

---

## User-App Interaction Sequence Diagram

```mermaid
sequenceDiagram
    participant User
    participant PurrfectPetsAPI
    participant PetstoreAPI

    User->>PurrfectPetsAPI: POST /pets/search {type, status}
    PurrfectPetsAPI->>PetstoreAPI: Fetch pets with filters
    PetstoreAPI-->>PurrfectPetsAPI: Return pet data
    PurrfectPetsAPI-->>User: Return filtered pet list

    User->>PurrfectPetsAPI: GET /pets
    PurrfectPetsAPI-->>User: Return cached pet list

    User->>PurrfectPetsAPI: GET /pets/{id}
    PurrfectPetsAPI-->>User: Return pet details

    User->>PurrfectPetsAPI: POST /pets/fun-fact
    PurrfectPetsAPI-->>User: Return random pet fact
```

---

## User Journey Diagram

```mermaid
flowchart TD
    A[User opens app] --> B{Search pets?}
    B -- Yes --> C[Send POST /pets/search]
    C --> D[Show pet list]
    D --> E{View pet details?}
    E -- Yes --> F[Send GET /pets/{id}]
    F --> G[Show pet details]
    E -- No --> H{Want fun fact?}
    H -- Yes --> I[Send POST /pets/fun-fact]
    I --> J[Show fun fact]
    H -- No --> K[End session]
    B -- No --> K
```
```
