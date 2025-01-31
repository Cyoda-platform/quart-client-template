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
    "dueDate": "2025-01-31T11:14:08.5119324+00:00",
    "completed": false
  },
  {
    "id": 2,
    "title": "Activity 2",
    "dueDate": "2025-01-31T12:14:08.511935+00:00",
    "completed": true
  },