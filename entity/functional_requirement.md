```markdown
# Functional Requirements for NBA Scores Notification Application

## 1. Data Fetching
- The system must fetch NBA game score data daily at a scheduled time (6:00 PM UTC).
- Data is fetched asynchronously from the external API endpoint:
  ```
  GET https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{today}?key=test
  ```
  where `{today}` is the current date in `YYYY-MM-DD` format.

## 2. Data Storage
- The system must store fetched NBA game data locally.
- Stored data includes game date, team names, scores, and relevant game information.

## 3. Subscription System
- Users can subscribe with their email to receive daily NBA score notifications.
- Each subscribed email is saved uniquely in the system.

## 4. Notification System
- After fetching and storing scores, the system sends email notifications to all subscribers.
- Notifications contain a summary of all games played on the respective day.

## 5. API Endpoints

| Method | Endpoint          | Description                              | Request Body                        | Response                         |
|--------|-------------------|--------------------------------------|-----------------------------------|---------------------------------|
| POST   | `/subscribe`      | Subscribe user with email             | `{ "email": "user@example.com" }` | Confirmation message            |
| POST   | `/fetch-scores`   | Fetch & store scores, send notifications (used by scheduler) | `{ "date": "YYYY-MM-DD" }`        | Status message with game count |
| GET    | `/subscribers`    | Retrieve list of subscribed emails    | N/A                               | List of emails                  |
| GET    | `/games/all`      | Retrieve all stored NBA games (supports pagination) | Query params: `page`, `limit` (optional) | List of games, page info        |
| GET    | `/games/{date}`   | Retrieve NBA games for a specified date | N/A                               | List of games on the date       |

## 6. Scheduler
- A background scheduler triggers the `POST /fetch-scores` endpoint daily at 6:00 PM UTC.
- This process fetches data, stores it, and sends notification emails automatically.

---

This completes the confirmed functional requirements for the application.
```