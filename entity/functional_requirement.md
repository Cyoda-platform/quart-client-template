```markdown
# Functional Requirements

## 1. Fetching Data
- The system must fetch NBA game score data daily at a scheduled time.
- Data is fetched from the external API:  
  `GET https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{today}?key=test`  
  where `{today}` is in `YYYY-MM-DD` format.
- The fetch operation must be handled asynchronously.

## 2. Data Storage
- The system must save fetched NBA game scores locally.
- Stored data includes: game date, team names, scores, and other relevant details.

## 3. Subscription System
- Users subscribe with their email to receive daily NBA score notifications.
- Each email in the subscription list is unique (no duplicates).

## 4. Notification System
- After fetching and storing scores, the system sends daily email summaries of NBA games to all subscribers.
- Emails are simple plain-text summaries.

## 5. API Endpoints

| Method | Endpoint          | Description                                    | Request Body                             | Response                                    |
|--------|-------------------|------------------------------------------------|-----------------------------------------|---------------------------------------------|
| POST   | /fetch-scores     | Fetch, store scores for a date, send notifications | `{ "date": "YYYY-MM-DD" }`              | `{ "status": "success", "message": "Scores fetched, stored, and notifications sent." }` |
| POST   | /subscribe        | Subscribe user email                             | `{ "email": "user@example.com" }`       | `{ "status": "success", "message": "Subscription successful." }`                       |
| GET    | /subscribers      | Get all subscribed emails                        | None                                    | `{ "subscribers": [ "user1@example.com", "user2@example.com" ] }`                      |
| GET    | /games/all        | Get all stored games with pagination             | Query params: `page`, `page_size` (optional) | `{ "games": [ ... ], "pagination": { "page": 1, "page_size": 20, "total_pages": 10, "total_items": 200 } }` |
| GET    | /games/{date}     | Get all games for a specific date                | None                                    | `{ "date": "YYYY-MM-DD", "games": [ ... ] }`                                           |

- Default pagination on `/games/all`: 20 items per page.

## 6. Scheduler
- A background scheduler triggers the daily fetch at a fixed time (e.g., 6:00 PM UTC).
- Scheduler initiates data fetching, storing, and notification sending without user API calls.

```