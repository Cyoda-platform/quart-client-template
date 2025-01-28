This documentation provides details on the endpoints used to retrieve user information from the ReqRes API, specifically focusing on the endpoints for fetching a single user and handling cases where a user is not found.

#### Base URL

The base URL for the ReqRes API is:
```
https://reqres.in/api
```

### Endpoints

#### 1. Single User

**Endpoint**: 
```
GET /users/{id}
```

**Description**: 
This endpoint retrieves the details of a single user based on the provided user ID.

**Request Example**: 
To retrieve the user with ID 2:
```
GET https://reqres.in/api/users/2
```

**Response Example**:
```json
{
  "data": {
    "id": 2,
    "email": "janet.weaver@reqres.in",
    "first_name": "Janet",
    "last_name": "Weaver",
    "avatar": "https://reqres.in/img/faces/2-image.jpg"
  },
  "support": {
    "url": "https://reqres.in/#support-heading",
    "text": "To keep ReqRes free, contributions towards server costs are appreciated!"
  }
}
```

**Final Entity Structure (after mapping)**:
```json
{
  "id": 2,
  "email": "janet.weaver@reqres.in",
  "first_name": "Janet",
  "last_name": "Weaver",
  "avatar": "https://reqres.in/img/faces/2-image.jpg"
}
```

#### 2. Single User Not Found

**Endpoint**: 
```
GET /users/{id}
```

**Description**: 
This endpoint handles requests for user IDs that do not exist in the database. It returns a 404 status code indicating that the user was not found.

**Request Example**: 
To retrieve a user with an ID that does not exist (for example, ID 23):
```
GET https://reqres.in/api/users/23
```

**Response Example**:
```json
{
  "status": 404,
  "error": "Not Found"
}
```

**Final Entity Structure (after mapping)**:
```json
{
  "status": 404,
  "error": "Not Found"
}
```

### Summary

- **Single User Endpoint**: Used to retrieve user details by ID, returning relevant user information.
- **Single User Not Found Endpoint**: Used to check for non-existent users, returning an error message with a 404 status code.
