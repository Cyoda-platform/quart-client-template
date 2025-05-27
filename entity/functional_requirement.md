```markdown
# Functional Requirements for NBA Score Update System

## API Endpoints

### 1. Subscribe User  
- **POST /subscribe**  
- **Description:** Add a user subscription with email and preference for summary or full details notifications.  
- **Request Body:**  
```json
{
  "email": "user@example.com",
  "notificationType": "summary"  // or "full"
}
```  
- **Response:**  
```json
{
  "message": "Subscription successful",
  "email": "user@example.com",
  "notificationType": "summary"
}
```

---

### 2. Retrieve Subscribers  
- **GET /subscribers**  
- **Description:** Retrieve list of all subscribers with their notification preferences.  
- **Response:**  
```json
[
  {
    "email": "user@example.com",
    "notificationType": "summary"
  },
  {
    "email": "another@example.com",
    "notificationType": "full"
  }
]
```

---

### 3. Fetch and Store NBA Scores  
- **POST /games/fetch**  
- **Description:** Trigger fetching NBA scores from external API for a specific date, store locally in JSON file, and send notifications to subscribers respecting their preferences.  
- **Request Body:**  
```json
{
  "date": "YYYY-MM-DD"  // e.g., "2025-03-25"
}
```  
- **Response:**  
```json
{
  "message": "Scores fetched, stored and notifications sent",
  "date": "YYYY-MM-DD"
}
```

---

### 4. Retrieve All Games (with Filtering & Pagination)  
- **GET /games/all**  
- **Description:** Retrieve stored NBA games with optional filters and pagination.  
- **Query Parameters:**  
  - `date` (optional, format YYYY-MM-DD)  
  - `team` (optional, string)  
  - `offset` (optional, integer)  
  - `limit` (optional, integer)  
- **Response:**  
```json
{
  "games": [
    {
      "gameId": "12345",
      "date": "YYYY-MM-DD",
      "homeTeam": "Team A",
      "awayTeam": "Team B",
      "homeScore": 100,
      "awayScore": 98,
      "status": "Final"
    }
  ],
  "pagination": {
    "offset": 0,
    "limit": 10,
    "total": 50
  }
}
```

---

### 5. Retrieve Games by Date  
- **GET /games/{date}**  
- **Description:** Retrieve all games for a specific date.  
- **Response:** Same format as `/games/all` filtered by the date parameter.

---

## Scheduler  
- The system includes a fixed-time scheduler (configured as an application property) that triggers the `/games/fetch` endpoint daily at the specified time (e.g., 6:00 PM UTC) without manual API calls.

---

## Email Notifications  
- Notifications are sent in HTML format.  
- Each subscriber receives an email according to their preference: either a summary or full details of the day’s NBA games.

---

## Data Storage  
- Game data is stored locally in JSON files (prototype stage), with plans to migrate to Cyoda database later.

---

## Summary of Key Points  
- File-based JSON storage for game data.  
- Subscription stores email and notification preference.  
- Supports filtering by date and team, pagination with offset & limit.  
- Scheduler runs on fixed application-configured time.  
- Emails sent in HTML respecting user preferences.

```