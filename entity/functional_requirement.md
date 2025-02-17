Here are the well-formatted final functional requirements for your project, structured for clarity and completeness:

---

## Functional Requirements

### 1. User Authentication and Authorization
- **User Signup**
  - Users can create an account by providing a username, password, and email.
  - **Endpoint**: `POST /users/create`
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
      "message": "User created successfully",
      "user_id": "string"
    }
    ```

- **User Login**
  - Users can log in using their username and password.
  - **Endpoint**: `POST /users/login`
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

### 2. Post Management
- **Create Post**
  - Users can create a new post with a title, topic tags, and body content.
  - **Endpoint**: `POST /posts`
  - **Request**: 
    ```json
    {
      "title": "string",
      "topics": ["string"],
      "body": "string"
    }
    ```
  - **Response**: 
    ```json
    {
      "post_id": "string",
      "message": "Post created successfully"
    }
    ```

- **View Posts**
  - Users can retrieve a paginated list of posts.
  - **Endpoint**: `GET /posts`
  - **Request**: 
    ```
    GET /posts?limit=20&offset=0
    ```
  - **Response**: 
    ```json
    {
      "posts": [{ "post_id": "string", "title": "string", ... }],
      "total": "number"
    }
    ```

- **View Specific Post**
  - Users can view details of a specific post.
  - **Endpoint**: `GET /posts/{post-id}`
  - **Response**: 
    ```json
    {
      "post_id": "string",
      "title": "string",
      "body": "string",
      "comments": [...]
    }
    ```

- **Delete Post**
  - Users can delete their own posts.
  - **Endpoint**: `DELETE /posts/{post-id}`
  - **Response**: 
    ```json
    {
      "message": "Post deleted successfully"
    }
    ```

### 3. Comment Management
- **Add Comment**
  - Users can add comments to posts.
  - **Endpoint**: `POST /posts/{post-id}/comments`
  - **Request**: 
    ```json
    {
      "body": "string"
    }
    ```
  - **Response**: 
    ```json
    {
      "comment_id": "string",
      "message": "Comment added successfully"
    }
    ```

- **View Comments**
  - Users can retrieve comments for a specific post.
  - **Endpoint**: `GET /posts/{post-id}/comments`
  - **Response**: 
    ```json
    {
      "comments": [{ "comment_id": "string", "body": "string", ... }]
    }
    ```

- **Delete Comment**
  - Users can delete their own comments.
  - **Endpoint**: `DELETE /posts/{post-id}/comments/{comment-id}`
  - **Response**: 
    ```json
    {
      "message": "Comment deleted successfully"
    }
    ```

### 4. Image Management
- **Upload Image**
  - Users can upload images for their posts.
  - **Endpoint**: `POST /posts/{post-id}/images`
  - **Request**: `FormData with image file`
  - **Response**: 
    ```json
    {
      "image_id": "string",
      "message": "Image uploaded successfully"
    }
    ```

- **Retrieve Image**
  - Users can retrieve images associated with a specific post.
  - **Endpoint**: `GET /posts/{post-id}/images/{image-id}`
  - **Response**: `Image file`

### 5. Voting System
- **Vote on Post**
  - Users can upvote or downvote posts.
  - **Endpoint**: `POST /posts/{post-id}/vote`
  - **Request**: 
    ```json
    {
      "vote": "upvote" | "downvote"
    }
    ```
  - **Response**: 
    ```json
    {
      "message": "Vote recorded"
    }
    ```

- **Vote on Comment**
  - Users can upvote or downvote comments.
  - **Endpoint**: `POST /posts/{post-id}/comments/{comment-id}/vote`
  - **Request**: 
    ```json
    {
      "vote": "upvote" | "downvote"
    }
    ```
  - **Response**: 
    ```json
    {
      "message": "Vote recorded"
    }
    ```

---

This format clearly outlines the functional requirements for your application, detailing user interactions and the corresponding API specifications. If you need any further modifications or additional details, feel free to let me know!