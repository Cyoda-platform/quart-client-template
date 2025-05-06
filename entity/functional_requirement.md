```markdown
# Functional Requirements and API Specification

## Overview
The application retrieves Finnish companies data from the PRH Avoindata API based on a given company name, filters out inactive companies, enriches the data by fetching the Legal Entity Identifier (LEI) from official registries or reliable financial data sources, and outputs the results in structured JSON or CSV format. The business logic involving external data retrieval and enrichment is implemented in POST endpoints, while GET endpoints are used to fetch processed results.

---

## API Endpoints

### 1. POST /api/companies/search

- **Description:**  
  Accepts a company name or partial name, queries the PRH Avoindata API for matching companies, filters for active companies, enriches each with LEI data, and stores the results for retrieval.

- **Request Body (application/json):**  
  ```json
  {
    "companyName": "string",          // Required: full or partial company name
    "maxResults": 50                  // Optional: maximum number of companies to process (default 50)
  }
  ```

- **Response (application/json):**  
  ```json
  {
    "searchId": "string",             // Unique identifier for this search session
    "totalCompanies": 12,             // Number of companies processed
    "message": "Search and enrichment completed"
  }
  ```

- **Business Logic:**  
  - Query PRH API using the provided company name.  
  - Filter results to include only active companies.  
  - For each active company, fetch the LEI from official or reliable data sources.  
  - Store the enriched results associated with the generated `searchId`.

---

### 2. GET /api/companies/results/{searchId}

- **Description:**  
  Retrieves the enriched company data for a previously executed search identified by `searchId`.

- **Path Parameter:**  
  - `searchId` (string): Identifier for the search session whose results are requested.

- **Response:**  
  - Content-Type depends on the `Accept` header (JSON or CSV).

  - **JSON Example:**  
    ```json
    {
      "searchId": "string",
      "results": [
        {
          "companyName": "string",
          "businessId": "string",
          "companyType": "string",
          "registrationDate": "YYYY-MM-DD",
          "status": "Active",
          "LEI": "string or Not Available"
        },
        ...
      ]
    }
    ```

  - **CSV Example:**  
    ```
    companyName,businessId,companyType,registrationDate,status,LEI
    ...
    ```

---

## User-App Interaction Sequence

```mermaid
sequenceDiagram
    participant User
    participant App
    participant PRH_API as PRH API
    participant LEI_Source as LEI Registry

    User->>App: POST /api/companies/search {companyName}
    App->>PRH_API: Query companies by name
    PRH_API-->>App: Return company list
    App: Filter active companies
    loop For each active company
        App->>LEI_Source: Query LEI by company info
        LEI_Source-->>App: Return LEI or Not Available
    end
    App->>App: Store enriched results with searchId
    App-->>User: Return searchId and summary

    User->>App: GET /api/companies/results/{searchId}
    App-->>User: Return enriched company data (JSON or CSV)
```

---

## Additional Notes

- External API queries and LEI enrichment occur only in the POST `/api/companies/search` endpoint.  
- GET `/api/companies/results/{searchId}` is read-only and returns stored results without triggering external calls.  
- The `searchId` allows users to retrieve past search results without re-executing the entire process.  
- Output format (JSON or CSV) is determined by the `Accept` HTTP header in the GET request.  
- The application filters companies strictly by their active status as provided by the PRH API.

```
