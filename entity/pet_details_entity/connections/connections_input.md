add three status parameters: available, pending, sold


curl -X 'GET' \
  'https://petstore.swagger.io/v2/pet/findByStatus?status=available' \
  -H 'accept: application/json'
Request URL
https://petstore.swagger.io/v2/pet/findByStatus?status=available
Server response
Code	Details
200	
Response body
Download
[
  {
    "id": 9223372036854776000,
    "category": {
      "id": 1,
      "name": "cats"
    },
    "name": "Fluffy",
    "photoUrls": [
      "http://example.com/cat.png"
    ],
    "tags": [
      {
        "id": 1,
        "name": "cute"
      }
    ],
    "status": "available"
  },
  {
    "id": 9223372036854776000,
    "category": {
      "id": 1,
      "name": "cats"
    },
    "name": "Fluffy",
    "photoUrls": [
      "http://example.com/cat.png"
    ],
    "tags": [
      {
        "id": 1,
        "name": "cute"
      }
    ],
    "status": "available"
  }
