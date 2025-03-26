```markdown
# Library Manager Pro Functional Requirements

## API Endpoints

### Book Management
- **POST /books**
  - **Description:** Add a new book.
  - **Request Body:**
    ```json
    {
      "title": "string",
      "description": "string",
      "authorId": "integer"
    }
    ```
  - **Response:**
    ```json
    {
      "id": "integer",
      "title": "string",
      "description": "string",
      "authorId": "integer"
    }
    ```

- **GET /books**
  - **Description:** Retrieve a list of all books.
  - **Response:**
    ```json
    [
      {
        "id": "integer",
        "title": "string",
        "description": "string",
        "authorId": "integer"
      }
    ]
    ```

- **POST /books/{id}**
  - **Description:** Update an existing book's information.
  - **Request Body:**
    ```json
    {
      "title": "string",
      "description": "string",
      "authorId": "integer"
    }
    ```
  - **Response:**
    ```json
    {
      "id": "integer",
      "title": "string",
      "description": "string",
      "authorId": "integer"
    }
    ```

- **DELETE /books/{id}**
  - **Description:** Delete a book.
  - **Response:**
    ```json
    {
      "message": "Book deleted successfully"
    }
    ```

### Author Management
- **POST /authors**
  - **Description:** Add a new author.
  - **Request Body:**
    ```json
    {
      "name": "string",
      "biography": "string"
    }
    ```
  - **Response:**
    ```json
    {
      "id": "integer",
      "name": "string",
      "biography": "string"
    }
    ```

- **GET /authors**
  - **Description:** Retrieve a list of all authors.
  - **Response:**
    ```json
    [
      {
        "id": "integer",
        "name": "string",
        "biography": "string"
      }
    ]
    ```

- **POST /authors/{id}**
  - **Description:** Update an author's information.
  - **Request Body:**
    ```json
    {
      "name": "string",
      "biography": "string"
    }
    ```
  - **Response:**
    ```json
    {
      "id": "integer",
      "name": "string",
      "biography": "string"
    }
    ```

- **DELETE /authors/{id}**
  - **Description:** Delete an author.
  - **Response:**
    ```json
    {
      "message": "Author deleted successfully"
    }
    ```

### User Management
- **POST /users**
  - **Description:** Create a new user.
  - **Request Body:**
    ```json
    {
      "name": "string",
      "email": "string"
    }
    ```
  - **Response:**
    ```json
    {
      "id": "integer",
      "name": "string",
      "email": "string"
    }
    ```

- **GET /users**
  - **Description:** Retrieve a list of all users.
  - **Response:**
    ```json
    [
      {
        "id": "integer",
        "name": "string",
        "email": "string"
      }
    ]
    ```

- **POST /users/{id}**
  - **Description:** Update user information.
  - **Request Body:**
    ```json
    {
      "name": "string",
      "email": "string"
    }
    ```
  - **Response:**
    ```json
    {
      "id": "integer",
      "name": "string",
      "email": "string"
    }
    ```

- **DELETE /users/{id}**
  - **Description:** Delete a user.
  - **Response:**
    ```json
    {
      "message": "User deleted successfully"
    }
    ```

### Task Management
- **POST /tasks**
  - **Description:** Add a new task.
  - **Request Body:**
    ```json
    {
      "title": "string",
      "description": "string",
      "status": "string"
    }
    ```
  - **Response:**
    ```json
    {
      "id": "integer",
      "title": "string",
      "description": "string",
      "status": "string"
    }
    ```

- **GET /tasks**
  - **Description:** Retrieve a list of all tasks.
  - **Response:**
    ```json
    [
      {
        "id": "integer",
        "title": "string",
        "description": "string",
        "status": "string"
      }
    ]
    ```

- **POST /tasks/{id}**
  - **Description:** Update a task's information.
  - **Request Body:**
    ```json
    {
      "title": "string",
      "description": "string",
      "status": "string"
    }
    ```
  - **Response:**
    ```json
    {
      "id": "integer",
      "title": "string",
      "description": "string",
      "status": "string"
    }
    ```

- **DELETE /tasks/{id}**
  - **Description:** Delete a task.
  - **Response:**
    ```json
    {
      "message": "Task deleted successfully"
    }
    ```

### Authentication
- **POST /authentication**
  - **Description:** Authenticate a user.
  - **Request Body:**
    ```json
    {
      "username": "string",
      "password": "string"
    }
    ```
  - **Response:**
    ```json
    {
      "token": "string"
    }
    ```

### User Activities
- **GET /activities**
  - **Description:** Retrieve user activities.
  - **Response:**
    ```json
    [
      {
        "userId": "integer",
        "activity": "string",
        "timestamp": "string"
      }
    ]
    ```

## User-App Interaction Diagram

```mermaid
journey
    title Library Manager Pro User Journey
    section User Authentication
      User logs in: 5: User
      System validates credentials: 2: System
      User logged in successfully: 5: User
    section Book Management
      User views book list: 5: User
      User adds a new book: 5: User
      System confirms book addition: 2: System
      User updates a book: 5: User
      System confirms book update: 2: System
      User deletes a book: 5: User
      System confirms book deletion: 2: System
    section Author Management
      User views author list: 5: User
      User adds a new author: 5: User
      System confirms author addition: 2: System
      User updates an author: 5: User
      System confirms author update: 2: System
      User deletes an author: 5: User
      System confirms author deletion: 2: System
    section User Management
      User views user list: 5: User
      User adds a new user: 5: User
      System confirms user addition: 2: System
      User updates user information: 5: User
      System confirms user update: 2: System
      User deletes a user: 5: User
      System confirms user deletion: 2: System
    section Task Management
      User views task list: 5: User
      User adds a new task: 5: User
      System confirms task addition: 2: System
      User updates a task: 5: User
      System confirms task update: 2: System
      User deletes a task: 5: User
      System confirms task deletion: 2: System
```
```