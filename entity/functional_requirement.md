```markdown
# Functional Requirements for NBA Scores Notification System

## Overview
The system fetches NBA game scores daily from an external API, stores the data locally, allows users to subscribe for daily email notifications, and sends those notifications automatically. It provides RESTful API endpoints for subscription management and game data retrieval.

---

## API Endpoints

### 1. POST /subscribe
- **Description:** Subscribe a user email to daily notifications.
- **Request Body:**
  ```json
  {
    "email": "user@example.com"
  }
  ```
- **Response:**
  - `201 Created` on success
  - `400 Bad Request` if email is invalid or already subscribed

### 2. POST /fetch-scores
- **Description:** Fetch NBA scores for a specific date from the external API and store them locally.
- **Request Body:**
  ```json
  {
    "date": "YYYY-MM-DD"
  }
  ```
- **Response:**
  - `200 OK` with summary of fetched games
  - `400 Bad Request` if date is invalid

### 3. POST /notify
- **Description:** Send daily score notifications to all subscribers for a specific date.
- **Request Body:**
  ```json
  {
    "date": "YYYY-MM-DD"
  }
  ```
- **Response:**
  - `200 OK` on successful notification dispatch

### 4. GET /subscribers
- **Description:** Retrieve a list of all subscribed emails.
- **Response:**
  ```json
  {
    "subscribers": [
      "user1@example.com",
      "user2@example.com"
    ]
  }
  ```

### 5. GET /games/all
- **Description:** Retrieve all stored NBA game data.
- **Optional Query Params:** `page`, `limit`
- **Response:**
  ```json
  {
    "games": [
      {
        "date": "YYYY-MM-DD",
        "home_team": "Team A",
        "away_team": "Team B",
        "home_score": 100,
        "away_score": 98,
        ...
      },
      ...
    ]
  }
  ```

### 6. GET /games/{date}
- **Description:** Retrieve all NBA games for a specific date.
- **Response:**
  ```json
  {
    "date": "YYYY-MM-DD",
    "games": [
      {
        "home_team": "Team A",
        "away_team": "Team B",
        "home_score": 100,
        "away_score": 98,
        ...
      },
      ...
    ]
  }
  ```

---

## Scheduler
- Runs daily at 18:00 UTC
- Automatically triggers `/fetch-scores` and then `/notify` for the current date

---

## Summary
- Unique emails enforced for subscriptions.
- POST endpoints handle any external API calls and data processing.
- GET endpoints serve stored application data only.
- Notifications include a simple summary of the day’s games.

```