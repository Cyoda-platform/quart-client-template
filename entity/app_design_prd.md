# Product Requirements Document (PRD) for Library Manager Pro Cyoda Design

## Introduction

This document provides a comprehensive overview of the Cyoda-based application design for Library Manager Pro. This system is intended to manage library operations, including book management, author management, user management, task management, and user activity management via integration with the FakeRest API. The design outlined aligns directly with the specified requirements and focuses on the structure of entities, workflows, and the event-driven architecture that underpins the application.

## Cyoda Overview

Cyoda is a serverless, event-driven framework that simplifies workflow management through entities which represent jobs and data. Each entity in the framework has a defined state, with transitions between states governed by events. This enables a responsive and scalable architecture suitable for applications like Library Manager Pro.

## Cyoda Entity Database

The Cyoda design JSON outlines several key entities for the Library Manager Pro application:

1. **Library Management Job (`library_management_job`)**:
   - **Type**: JOB
   - **Source**: SCHEDULED
   - **Description**: Responsible for orchestrating workflows that fetch data from the FakeRest API for books, authors, users, tasks, and user activities.

2. **Book Entity (`book_entity`)**:
   - **Type**: EXTERNAL_SOURCES_PULL_BASED_RAW_DATA
   - **Source**: ENTITY_EVENT
   - **Description**: Stores data fetched about books.

3. **Author Entity (`author_entity`)**:
   - **Type**: EXTERNAL_SOURCES_PULL_BASED_RAW_DATA
   - **Source**: ENTITY_EVENT
   - **Description**: Stores data fetched about authors.

4. **User Entity (`user_entity`)**:
   - **Type**: EXTERNAL_SOURCES_PULL_BASED_RAW_DATA
   - **Source**: ENTITY_EVENT
   - **Description**: Stores data fetched about users.

5. **Task Entity (`task_entity`)**:
   - **Type**: EXTERNAL_SOURCES_PULL_BASED_RAW_DATA
   - **Source**: ENTITY_EVENT
   - **Description**: Stores data fetched about tasks.

6. **User Activity Entity (`user_activity_entity`)**:
   - **Type**: EXTERNAL_SOURCES_PULL_BASED_RAW_DATA
   - **Source**: ENTITY_EVENT
   - **Description**: Stores data fetched about user activities.

## Workflow Overview

The workflows in Cyoda are primarily managed through the `library_management_job`. This job coordinates the fetching of data from various API endpoints and saves them into their respective entities.

### Flowchart for Library Management Job

```mermaid
flowchart TD
    A[Start State] -->|transition: fetch_books, processor: fetch_books_process| B[Books Fetched]
    B -->|transition: fetch_authors, processor: fetch_authors_process| C[Authors Fetched]
    C -->|transition: fetch_users, processor: fetch_users_process| D[Users Fetched]
    D -->|transition: fetch_tasks, processor: fetch_tasks_process| E[Tasks Fetched]
    E -->|transition: fetch_user_activities, processor: fetch_user_activities_process| F[User Activities Fetched]

    %% Decision point for criteria
    B -->|criteria: books_available| D1{Decision: Check Books Availability}
    D1 -->|true| C
    D1 -->|false| E1[Error: No Books Available]

    class A,B,C,D,E,F,D1,E1 automated;
```

## Event-Driven Architecture

The event-driven architecture allows the Library Manager Pro application to respond automatically to changes or triggers. In this case, the following events are significant:

1. **Data Fetching Events**: The library management job initiates at scheduled intervals to fetch data from various endpoints of the FakeRest API.
  
2. **Entity Updates**: Each fetched data set is stored within its respective entity, ready for future processing or presentation.

### Sequence Diagram for Library Management Job

```mermaid
sequenceDiagram
    participant User
    participant Scheduler
    participant Library Management Job
    participant API

    User->>Scheduler: Schedule library management job
    Scheduler->>Library Management Job: Trigger job to fetch data
    Library Management Job->>API: Fetch books
    API-->>Library Management Job: Return books data
    Library Management Job->>API: Fetch authors
    API-->>Library Management Job: Return authors data
    Library Management Job->>API: Fetch users
    API-->>Library Management Job: Return users data
    Library Management Job->>API: Fetch tasks
    API-->>Library Management Job: Return tasks data
    Library Management Job->>API: Fetch user activities
    API-->>Library Management Job: Return user activities data
    Library Management Job->>User: Notify data fetch completion
```

## Entities and Their Relationships

This section highlights the relationships between entities. The `library_management_job` orchestrates the fetching of data, which populates the respective data entities according to the following diagram:

```mermaid
graph TD;
    A[library_management_job] -->|triggers| B[book_entity];
    A -->|triggers| C[author_entity];
    A -->|triggers| D[user_entity];
    A -->|triggers| E[task_entity];
    A -->|triggers| F[user_activity_entity];
```

## Conclusion

The Cyoda design aligns effectively with the requirements for the Library Manager Pro application. By utilizing the event-driven model, the application efficiently manages state transitions of each entity involved from data fetching to storage. The outlined entities, workflows, and events comprehensively cover the needs of the application, ensuring a smooth and automated process for library management.

This PRD serves as a foundational guide for the implementation and development of the Library Manager Pro application using the Cyoda framework.