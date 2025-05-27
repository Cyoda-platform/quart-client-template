```markdown
# Functional Requirements

## 1. Fetching NBA Game Scores

- The system must fetch NBA game score data daily at a scheduled time (e.g., 6:00 PM UTC).
- Data will be fetched asynchronously from the external API:
  ```
  GET https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{today}?key=test
  ```
  where `{today}` uses the format `YYYY-MM-DD`.
- The fetching process will be triggered by a background scheduler calling a POST endpoint internally (no external API call required).
- After fetching, the data will be stored locally in the database.

## 2. Data Storage

- Store game details including:
  - Game date
  - Team names (home and away)
  - Scores (home and away)
  - Additional relevant information from the API response
- Store subscriber emails for daily notifications.

## 3. Subscription System

- Users can subscribe via email to receive daily NBA scores notifications.
- Subscription is done via a POST request providing the email.
- Subscriber emails are stored in the database.

## 4. Notification System

- After fetching and storing daily scores, the system sends an email notification to all subscribers.
- Notifications include a summary of all games played on that day.

## 5. API Endpoints

| Method | Endpoint           | Description                                     | Request Body                        | Response                         |
|--------|--------------------|------------------------------------------------|-----------------------------------|---------------------------------|
| POST   | /fetch-scores      | Trigger fetching, storing, and notifying scores | `{ "date": "YYYY-MM-DD" }`          | `{ "status": "success", "message": "Scores fetched, stored, and notifications sent." }` |
| POST   | /subscribe         | Subscribe user by email                          | `{ "email": "user@example.com" }` | `{ "status": "success", "message": "Subscription successful." }` |
| GET    | /subscribers       | Retrieve list of subscribed emails               | None                              | `{ "subscribers": ["email1", "email2", ...] }` |
| GET    | /games/all         | Retrieve all stored NBA game data (optional pagination and filtering) | Optional query params `page`, `limit` | `{ "games": [ ... ], "pagination": { ... } }` |
| GET    | /games/{date}      | Retrieve NBA games for a specific date          | None                              | `{ "date": "YYYY-MM-DD", "games": [ ... ] }` |

## 6. Scheduler

- A background scheduler triggers the `POST /fetch-scores` endpoint daily at the configured time with the current date.
- This automatically fetches data, stores it, and sends notifications without user intervention.

---

## Summary

This design respects RESTful principles by using POST for business logic that interacts with external APIs and triggers workflows, and GET for retrieving stored data only.

The system is event-driven: the scheduler event triggers the fetch-store-notify workflow, ensuring timely and automated updates for subscribers.
```