```markdown
# Functional Requirements for NBA Scores Notification Application

## API Endpoints

### 1. Subscribe to Notifications

- **Endpoint:** `POST /subscribe`
- **Description:** Add a user email to the subscription list to receive daily NBA scores notifications.
- **Request:**
  ```json
  {
    "email": "user@example.com"
  }
  ```
- **Response:**
  ```json
  {
    "message": "Subscription successful",
    "email": "user@example.com"
  }
  ```

### 2. Fetch and Store NBA Scores (Triggered by Scheduler)

- **Endpoint:** `POST /fetch-scores`
- **Description:** Fetch NBA scores from the external API for a specified date (or today by default), store them locally, and send notifications to subscribers.
- **Request:**
  ```json
  {
    "date": "YYYY-MM-DD"  // optional; defaults to current date
  }
  ```
- **Response:**
  ```json
  {
    "message": "Scores fetched, stored, and notifications sent",
    "date": "YYYY-MM-DD",
    "games_fetched": 15
  }
  ```

### 3. Retrieve All Subscribers

- **Endpoint:** `GET /subscribers`
- **Description:** Retrieve the list of all subscribed email addresses.
- **Response:**
  ```json
  {
    "subscribers": [
      "user1@example.com",
      "user2@example.com"
    ]
  }
  ```

### 4. Retrieve All Stored Games

- **Endpoint:** `GET /games/all`
- **Description:** Retrieve all NBA games stored in the system, optionally with pagination/filtering.
- **Request Parameters (optional):**
  - `page` (integer)
  - `limit` (integer)
- **Response:**
  ```json
  {
    "games": [
      {
        "date": "YYYY-MM-DD",
        "home_team": "Team A",
        "away_team": "Team B",
        "home_score": 110,
        "away_score": 105,
        "details": {...}
      }
    ],
    "page": 1,
    "limit": 20,
    "total": 100
  }
  ```

### 5. Retrieve Games by Date

- **Endpoint:** `GET /games/{date}`
- **Description:** Retrieve all NBA games for a specific date.
- **Path Parameter:**
  - `date` (string in `YYYY-MM-DD` format)
- **Response:**
  ```json
  {
    "date": "YYYY-MM-DD",
    "games": [
      {
        "home_team": "Team A",
        "away_team": "Team B",
        "home_score": 110,
        "away_score": 105,
        "details": {...}
      }
    ]
  }
  ```

---

## Scheduler

- Runs daily at a specified time (e.g., 6:00 PM UTC).
- Triggers the `POST /fetch-scores` endpoint internally to:
  - Fetch latest NBA game scores asynchronously from the external API.
  - Store fetched data locally.
  - Send email notifications with daily scores to all subscribers.

---

## Data Storage

- Store game details:
  - Date
  - Team names (home and away)
  - Scores
  - Other relevant game info

- Store subscriber emails for notification.

---

## Notification System

- After successful data fetch and storage, send email notifications to all subscribers.
- Email content includes a summary of all games played on that day with final scores.

---
```