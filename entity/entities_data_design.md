Based on the provided JSON design document, here are the Mermaid diagrams for the entities and workflows.

### Entity-Relationship Diagram (ERD)

```mermaid
erDiagram
    USERS {
        integer id
        string username
        string password
    }

    POSTS {
        integer post_id
        string title
        string topics
        string body
        integer upvotes
        integer downvotes
    }

    POST {
        integer post_id
        string title
        string body
    }

    COMMENT {
        integer comment_id
        string body
        integer upvotes
        integer downvotes
    }

    POST ||--o{ COMMENT : has
    USERS ||--o{ POSTS : creates
```

### Class Diagrams

```mermaid
classDiagram
    class Users {
        +integer id
        +string username
        +string password
    }

    class Posts {
        +integer post_id
        +string title
        +string[] topics
        +string body
        +integer upvotes
        +integer downvotes
    }

    class Post {
        +integer post_id
        +string title
        +string body
    }

    class Comment {
        +integer comment_id
        +string body
        +integer upvotes
        +integer downvotes
    }

    Posts --> Comment : contains
    Users --> Posts : creates
```

### Flow Chart for Each Workflow

Assuming a basic workflow for creating a post and adding comments, here is a flowchart:

#### Workflow: Create Post

```mermaid
flowchart TD
    A[Start] --> B[User logs in]
    B --> C[User fills post details]
    C --> D[User submits post]
    D --> E[Post is saved to database]
    E --> F[Confirmation message]
    F --> G[End]
```

#### Workflow: Add Comment to Post

```mermaid
flowchart TD
    A[Start] --> B[User views post]
    B --> C[User types comment]
    C --> D[User submits comment]
    D --> E[Comment is saved to database]
    E --> F[Confirmation message]
    F --> G[End]
```

These diagrams represent the entities, their relationships, and workflows as specified in the JSON design document.