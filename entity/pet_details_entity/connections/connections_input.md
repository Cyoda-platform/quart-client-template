add three status parameters: available, pending, sold

1. available

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

2. pending

curl -X 'GET' \
  'https://petstore.swagger.io/v2/pet/findByStatus?status=pending' \
  -H 'accept: application/json'
Request URL
https://petstore.swagger.io/v2/pet/findByStatus?status=pending
Server response
Code	Details
200	
Response body
Download
[
  {
    "id": 50366267417,
    "name": "CfcTHzsSQmzezcrKyMJidBFNZATeohuworpZRPebpjpLiFXZEqKkSCFtUVxaIlcLHjpmEquiLnVwpzEcQfUfUm",
    "photoUrls": [
      "OZpvcj"
    ],
    "tags": [],
    "status": "pending"
  },
  {
    "id": 911117203295477600,
    "name": "chedder-89811222",
    "photoUrls": [
      "./dog.png"
    ],
    "tags": [],
    "status": "pending"
  }

3. sold

curl -X 'GET' \
  'https://petstore.swagger.io/v2/pet/findByStatus?status=sold' \
  -H 'accept: application/json'
Request URL
https://petstore.swagger.io/v2/pet/findByStatus?status=sold
Server response
Code	Details
200	
Response body
Download
[
  {
    "id": 201393731033398340,
    "category": {
      "id": 7612786423,
      "name": "mOgBHmxNKUsIbiucPodIMzUVJvAOdeswwwvQjWQZjFSzZYPyiOcEtRIqGOsadXSVDOEGOoZhXAkmEaHdUUkErQQLTCKUAOq"
    },
    "name": "111",
    "photoUrls": [
      "GGlUhP"
    ],
    "tags": [
      {
        "id": 9280721785,
        "name": "qwgbnrDAjJNcnHzxkPyGaZpQVFhNAbmTH"
      }
    ],
    "status": "sold"
  },
  {
    "id": 777666,
    "category": {
      "id": 1,
      "name": "Котик"
    },
    "name": "Барсик",
    "photoUrls": [
      "https://ref_to_img.png"
    ],
    "tags": [
      {
        "id": 1,
        "name": "Тэг 1"
      }
    ],
    "status": "sold"
  }
