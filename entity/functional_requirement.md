```markdown
# Functional Requirements for NBA Scores Notification System

## API Endpoints

### 1. Subscribe to Notifications
- **Endpoint:** `POST /subscribe`
- **Description:** Add a new subscriber email to the notification list.
- **Request Body:**
  ```json
  {
    "email": "user@example.com"
  }
  ```
- **Response:**
  - `201 Created` on success
  - `400 Bad Request` if email is invalid or already subscribed

---

### 2. Fetch and Store NBA Scores (Trigger External API Fetch)
- **Endpoint:** `POST /games/fetch`
- **Description:** Trigger fetching of NBA scores for a given date from the external API, store results locally, and send notifications.
- **Request Body:**
  ```json
  {
    "date": "YYYY-MM-DD"
  }
  ```
- **Response:**
  - `200 OK` with summary of fetched games
  - `400 Bad Request` for invalid date format
  - `500 Internal Server Error` on failure

---

### 3. Get All Subscribers
- **Endpoint:** `GET /subscribers`
- **Description:** Retrieve list of all subscribed email addresses.
- **Response:**
  ```json
  {
    "subscribers": ["user1@example.com", "user2@example.com"]
  }
  ```

---

### 4. Get All Games Data
- **Endpoint:** `GET /games/all`
- **Description:** Retrieve all stored NBA games data.
- **Response:**
  ```json
  {
    "games": [
      {
        "date": "YYYY-MM-DD",
        "home_team": "Team A",
        "away_team": "Team B",
        "home_score": 100,
        "away_score": 95,
        "status": "Final"
      },
      ...
    ]
  }
  ```

---

### 5. Get Games by Date
- **Endpoint:** `GET /games/{date}`
- **Description:** Retrieve all NBA games for the specified date.
- **Response:**
  ```json
  {
    "date": "YYYY-MM-DD",
    "games": [
      {
        "home_team": "Team A",
        "away_team": "Team B",
        "home_score": 100,
        "away_score": 95,
        "status": "Final"
      },
      ...
    ]
  }
  ```

---

## Business Logic Notes
- External API calls happen only in the `POST /games/fetch` endpoint or via background scheduler.
- `GET` endpoints only return stored data with no external requests.
- Email notifications are sent after successful data fetch and storage.
- Duplicate subscriber emails are not allowed.
- Email notifications include detailed scores for all games.
- Only key game details are stored (date, team names, scores, status).

---
```