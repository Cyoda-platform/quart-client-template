Here are the final functional requirements for your flight search application, presented in an organized format:

### Functional Requirements for Flight Search Application

#### User Stories

1. **Search Flights**
   - **As a user**, I want to search for flights by entering departure and arrival airports, travel dates, and the number of passengers, so that I can find suitable flights.

2. **View Flight Details**
   - **As a user**, I want to view the search results with flight details (airline, flight number, departure/arrival times, price), so that I can compare different options.

3. **Sort Flights**
   - **As a user**, I want to sort the search results by price, departure time, and airline, so that I can find the best flight for my needs.

4. **Filter Flights**
   - **As a user**, I want to filter the search results to show only non-stop flights or flights from specific airlines, so that I can narrow down my options.

5. **Error Handling**
   - **As a user**, I want to receive informative error messages when no flights are found or if there are issues with the API, so that I understand what went wrong.

#### API Endpoints

1. **Search Flights**
   - **Endpoint**: `POST /api/flights/search`
   - **Request Format**:
     ```json
     {
       "departureAirport": "JFK",
       "arrivalAirport": "LAX",
       "departureDate": "2023-12-01",
       "returnDate": "2023-12-15",
       "passengers": {
         "adults": 1,
         "children": 0,
         "infants": 0
       }
     }
     ```
   - **Response Format**:
     ```json
     {
       "flights": [
         {
           "airline": "Delta",
           "flightNumber": "DL123",
           "departureTime": "2023-12-01T08:00:00Z",
           "arrivalTime": "2023-12-01T11:00:00Z",
           "price": 300
         },
         ...
       ],
       "error": null
     }
     ```

2. **Sort Flights**
   - **Endpoint**: `GET /api/flights/sort`
   - **Request Format**:
     ```json
     {
       "sortBy": "price" // or "departureTime", "airline"
     }
     ```
   - **Response Format**: Same as the search response, sorted accordingly.

3. **Filter Flights**
   - **Endpoint**: `GET /api/flights/filter`
   - **Request Format**:
     ```json
     {
       "nonStop": true,
       "airlines": ["Delta", "United"]
     }
     ```
   - **Response Format**: Same as the search response, filtered accordingly.

#### User-App Interaction Diagram (Mermaid)

```mermaid
journey
    title Flight Search User Journey
    section Search Flights
      User enters search criteria: 5: User
      User submits search request: 5: User
      App queries Airport Gap API: 5: App
      App returns flight results: 5: App
    section Sort and Filter
      User selects sorting option: 5: User
      App sorts results: