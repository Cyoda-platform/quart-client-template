```markdown
# Functional Requirements for NBA Scores Application

## 1. Fetching Data
- The system must fetch NBA game score data daily at a scheduled time.
- Data will be fetched asynchronously from the external API endpoint:
  ```
  GET https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{today}?key=test
  ```
- The `{today}` parameter follows the format `YYYY-MM-DD`.

## 2. Data Storage
- The system must save fetched game data locally to persist scores.
- Stored data includes game date, team names, scores, and other relevant details.

## 3. Subscription System
- Users can subscribe by providing their email to receive daily NBA score notifications.
- Upon subscribing, the user’s email is added to the notification list.

## 4. Notification System
- After fetching and storing scores, the system sends email notifications to all subscribers.
- Notifications include a summary of all games played on the specific day.

## 5. API Endpoints

| Endpoint          | Method | Description                                   | Request Body / Params                           | Response                                    |
|-------------------|--------|-----------------------------------------------|------------------------------------------------|---------------------------------------------|
| `/subscribe`      | POST   | Subscribe user email for daily notifications | `{ "email": "user@example.com" }`              | Confirmation message and subscribed email  |
| `/subscribers`    | GET    | Retrieve all subscribed emails                | None                                           | List of subscribed emails                    |
| `/games/all`      | GET    | Retrieve all stored NBA games (optional paging/filtering) | Optional query params: `page`, `pageSize`, `startDate`, `endDate` | List of games with pagination info          |
| `/games/{date}`   | GET    | Retrieve NBA games for a specific date        | Path param: `date` in `YYYY-MM-DD` format       | List of games for given date                 |
| `/fetch-scores`   | POST   | Trigger fetch/store of NBA scores & send notifications | `{ "date": "YYYY-MM-DD" }`                      | Confirmation of fetch, store, and notify    |

## 6. Scheduler
- A background scheduler triggers the `/fetch-scores` endpoint daily at 6:00 PM UTC automatically.
- This process fetches scores, stores them, and sends notifications without user intervention.

---

## Summary

- **POST** endpoints are used to invoke external API calls and trigger workflows (`/subscribe`, `/fetch-scores`).
- **GET** endpoints are used only for retrieving stored data (`/subscribers`, `/games/all`, `/games/{date}`).
- All date parameters follow the `YYYY-MM-DD` format.
- Notifications are sent by email to all subscribed users after data is updated.

```