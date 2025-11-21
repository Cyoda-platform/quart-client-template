# Project Management Application - Functional Requirements

## Overview
A comprehensive project management web application that enables teams to organize projects, assign tasks to team members, set deadlines, track progress, and collaborate in real-time.

## Core Entities

### 1. User Entity
**Purpose**: Represents system users with role-based access control
**Fields**:
- `user_id` (string, required): Business identifier for the user
- `name` (string, required): Full name of the user
- `email` (string, required): Email address (unique)
- `role` (string, required): User role - ADMIN, MANAGER, MEMBER
- `is_active` (boolean, optional): Whether user account is active

**Business Rules**:
- Email must be unique across all users
- Role determines permissions (ADMIN > MANAGER > MEMBER)
- Only ADMIN can create/modify users
- Users can update their own profile information

**Workflow States**: initial_state -> active -> (optional: suspended -> active)

### 2. Project Entity
**Purpose**: Represents projects that contain tasks and have team members
**Fields**:
- `project_id` (string, required): Business identifier for the project
- `name` (string, required): Project name
- `description` (string, required): Project description
- `owner_id` (string, required): Technical ID of the project owner (User)
- `members` (array of strings, optional): List of user technical IDs who are project members
- `start_date` (string, optional): Project start date (ISO 8601)
- `end_date` (string, optional): Project end date (ISO 8601)

**Business Rules**:
- Owner must be a valid User with MANAGER or ADMIN role
- Members must be valid active Users
- End date must be after start date if both are provided
- Only project owner or ADMIN can modify project details

**Workflow States**: initial_state -> created -> active -> (optional: completed/archived)

### 3. Task Entity
**Purpose**: Core entity representing work items within projects
**Fields**:
- `task_id` (string, required): Business identifier for the task
- `project_id` (string, required): Technical ID of the parent project
- `title` (string, required): Task title
- `description` (string, required): Task description
- `assignee_id` (string, optional): Technical ID of assigned user
- `priority` (string, required): HIGH, MEDIUM, LOW
- `estimate_hours` (number, optional): Estimated hours to complete
- `logged_hours` (number, optional): Actual hours logged
- `due_date` (string, optional): Task due date (ISO 8601)
- `dependencies` (array of strings, optional): List of task technical IDs this task depends on

**Business Rules**:
- Task must belong to a valid active Project
- Assignee must be a project member or project owner
- Dependencies must be valid tasks within the same project
- Only assignee, project owner, or ADMIN can update task status
- Logged hours cannot exceed estimate_hours * 1.5

**Workflow States**: backlog -> todo -> in_progress -> review -> done
**Critical Transitions**:
- backlog -> todo: Automatic when task is created
- todo -> in_progress: Manual, requires assignee
- in_progress -> review: Manual, only by assignee or manager
- review -> done: Manual, only by project owner or ADMIN
- review -> in_progress: Manual, for rework

### 4. Comment Entity
**Purpose**: Enables collaboration through task comments
**Fields**:
- `comment_id` (string, required): Business identifier for the comment
- `task_id` (string, required): Technical ID of the parent task
- `author_id` (string, required): Technical ID of the comment author
- `content` (string, required): Comment content
- `created_at` (string, required): Comment creation timestamp (ISO 8601)
- `mentions` (array of strings, optional): List of mentioned user technical IDs

**Business Rules**:
- Author must be a project member or have access to the task
- Content must be non-empty and max 1000 characters
- Mentions must be valid active users
- Comments cannot be deleted, only marked as edited

**Workflow States**: initial_state -> posted -> (optional: edited)

### 5. Attachment Entity
**Purpose**: File attachments associated with tasks
**Fields**:
- `attachment_id` (string, required): Business identifier for the attachment
- `task_id` (string, required): Technical ID of the parent task
- `filename` (string, required): Original filename
- `url` (string, required): Storage URL for the file
- `uploaded_by` (string, required): Technical ID of the uploader
- `file_size` (number, optional): File size in bytes
- `content_type` (string, optional): MIME type of the file

**Business Rules**:
- Uploader must have access to the parent task
- File size limit: 10MB per attachment
- Allowed file types: documents, images, archives
- Only uploader or project owner can delete attachments

**Workflow States**: initial_state -> uploaded -> (optional: deleted)

### 6. TimeEntry Entity
**Purpose**: Time tracking for tasks
**Fields**:
- `entry_id` (string, required): Business identifier for the time entry
- `task_id` (string, required): Technical ID of the parent task
- `user_id` (string, required): Technical ID of the user logging time
- `start_time` (string, required): Start timestamp (ISO 8601)
- `end_time` (string, optional): End timestamp (ISO 8601)
- `duration_minutes` (number, required): Duration in minutes
- `description` (string, optional): Description of work performed

**Business Rules**:
- User must be assigned to the task or be project owner
- Duration must be positive and reasonable (max 24 hours per entry)
- Start time cannot be in the future
- End time must be after start time if provided
- Time entries update the task's logged_hours automatically

**Workflow States**: initial_state -> logged -> (optional: approved/rejected)

## Workflow Requirements

### Task Workflow (Primary Focus)
**States**: backlog -> todo -> in_progress -> review -> done

**Transition Rules**:
1. **backlog -> todo**: Automatic when task is created with assignee
2. **todo -> in_progress**: Manual, requires assignee to start work
3. **in_progress -> review**: Manual, only assignee or manager can trigger
4. **review -> done**: Manual, only project owner or ADMIN can approve
5. **review -> in_progress**: Manual, for rework requests
6. **Any state -> backlog**: Manual, only project owner or ADMIN (reset)

**Processors Required**:
- `TaskAssignmentProcessor`: Handles task assignment and notification
- `TaskProgressProcessor`: Updates progress and calculates metrics
- `TaskCompletionProcessor`: Finalizes task and updates project statistics

**Criteria Required**:
- `TaskTransitionCriterion`: Validates state transitions based on user roles
- `TaskDependencyCriterion`: Ensures dependencies are met before progression

## API Requirements

### Core CRUD Operations
All entities must support:
- GET /api/{entity}s - List with pagination and filtering
- GET /api/{entity}s/{id} - Get by technical ID
- POST /api/{entity}s - Create new entity
- PUT /api/{entity}s/{id} - Update entity
- DELETE /api/{entity}s/{id} - Delete entity

### Special Endpoints
- POST /api/tasks/{id}/transition - Manual state transitions
- GET /api/projects/{id}/tasks - Get all tasks for a project
- POST /api/tasks/{id}/comments - Add comment to task
- POST /api/tasks/{id}/attachments - Upload attachment
- POST /api/tasks/{id}/time-entries - Log time entry

### Filtering and Search
- Tasks: by project, assignee, status, priority, due_date
- Projects: by owner, status, date_range
- Comments: by task, author, date_range
- Time entries: by user, task, date_range

## Permission Matrix

| Role | Users | Projects | Tasks | Comments | Attachments | Time Entries |
|------|-------|----------|-------|----------|-------------|--------------|
| ADMIN | CRUD | CRUD | CRUD | CRUD | CRUD | CRUD |
| MANAGER | R | CRUD (owned) | CRUD (in projects) | CRUD | CRUD | CRUD |
| MEMBER | R (self) | R | RU (assigned) | CRUD | RU (own) | CRUD (own) |

## Success Criteria

1. All 6 entities implemented with proper validation
2. Task workflow fully functional with role-based transitions
3. API endpoints support all required operations
4. Code passes all quality checks (mypy, black, isort, flake8, bandit)
5. Proper error handling and logging throughout
6. Integration with Cyoda framework patterns maintained
7. Real-time collaboration features ready for WebSocket integration
