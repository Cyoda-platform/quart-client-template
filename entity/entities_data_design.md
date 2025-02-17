Based on the provided JSON design document, here are the Mermaid diagrams for the entities and workflows.

### Entity-Relationship (ER) Diagram

```mermaid
erDiagram
    USERS {
        string username
        string password
    }
    
    POSTS {
        string post_id
        string title
        string topics
        string body
        int upvotes
        int downvotes
    }
    
    POST {
        string post_id
        string title
        string body
    }

    USERS ||--o{ POSTS : creates
    POSTS ||--o{ POST : contains
```

### Class Diagram

```mermaid
classDiagram
    class Users {
        +string username
        +string password
    }

    class Posts {
        +string post_id
        +string title
        +string[] topics
        +string body
        +int upvotes
        +int downvotes
    }

    class Post {
        +string post_id
        +string title
        +string body
    }
```

### Flowchart for User Registration Workflow

```mermaid
flowchart TD
    A[Start] --> B[User enters username and password]
    B --> C{Is username unique?}
    C -- Yes --> D[Store user data in database]
    C -- No --> E[Show error message]
    D --> F[Registration successful]
    E --> F
    F --> G[End]
```

### Flowchart for Creating a Post Workflow

```mermaid
flowchart TD
    A[Start] --> B[User enters post details]
    B --> C{Are all fields filled?}
    C -- Yes --> D[Store post data in database]
    C -- No --> E[Show error message]
    D --> F[Post creation successful]
    E --> F
    F --> G[End]
```

These diagrams represent the entities and their relationships, as well as the workflows for user registration and post creation based on the provided JSON design document.