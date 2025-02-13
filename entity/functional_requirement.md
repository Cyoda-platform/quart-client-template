Here are the well-formatted final functional requirements for your backend application, structured into user stories, API endpoints, and detailed request/response formats.

### Functional Requirements

#### 1. User Authentication

- **User Story**: As a user, I want to create an account so that I can log in and access the platform.
  - **API Endpoint**: `POST /users/create`
    - **Request**: 
      ```json
      {
        "username": "string",
        "password": "string",
        "email": "string"
      }
      ```
    - **Response**: 
      ```json
      {
        "user_id": "string",
        "message": "User created successfully."
      }
      ```

- **User Story**: As a user, I want to log in to my account so that I can access protected resources.
  - **API Endpoint**: `POST /users/login`
    - **Request**: 
      ```json
      {
        "username": "string",
        "password": "string"
      }
      ```
    - **Response**: 
      ```json
      {
        "token": "JWT_TOKEN"
      }
      ```

#### 2. Post Management

- **User Story**: As a user, I want to create a new post with a title, body, and tags so that I can share my thoughts.
  - **API Endpoint**: `POST /posts`
    - **Request**: 
      ```json
      {
        "title": "string",
        "body": "string",
        "tags": ["string"]
      }
      ```
    - **Response**: 
      ```json
      {
        "post_id": "string",
        "message": "Post created successfully."
      }
      ```

- **User Story**: As a user, I want to view a list of posts to discover new content.
  - **API Endpoint**: `GET /posts`
    - **Response**: 
      ```json
      {
        "posts": [
          {
            "post_id": "string",
            "title": "string",
            "upvotes": number,
            "downvotes": number
          }
        ],
        "total": number
      }
      ```

- **User Story**: As a user, I want to view the details of a specific post to read it in full.
  - **API Endpoint**: `GET /posts/{post-id}`
    - **Response**: 
      ```json
      {
        "post_id": "string",
        "title": "string",
        "body": "string",
        "topics": ["string"],
        "upvotes": number,
        "downvotes": number
      }
      ```

- **User Story**: As a user, I want to delete my own posts to manage my content.
  - **API Endpoint**: `DELETE /posts/{post-id}`
    - **Response**: 
      ```json
      {
        "message": "Post deleted successfully."
      }
      ```

#### 3. Comment Management

- **User Story**: As a user, I want to add comments to posts to share my opinions.
  - **API Endpoint**: `POST /posts/{post-id}/comments`
    - **Request**: 
      ```json
      {
        "