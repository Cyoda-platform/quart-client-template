curl -X GET "https://fakerestapi.azurewebsites.net/api/v1/Activities" -H  "accept: text/plain; v=1.0"
Request URL
https://fakerestapi.azurewebsites.net/api/v1/Activities
Server response
Code	Details
200	
Response body
Download
[
  {
    "id": 1,
    "title": "Activity 1",
    "dueDate": "2025-01-29T14:32:51.4152486+00:00",
    "completed": false
  },
  {
    "id": 2,
    "title": "Activity 2",
    "dueDate": "2025-01-29T15:32:51.4152516+00:00",
    "completed": true
  },
  {
    "id": 3,
    "title": "Activity 3",
    "dueDate": "2025-01-29T16:32:51.415252+00:00",
    "completed": false
  }
